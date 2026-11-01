"""Leitura dos dados da marca e cálculo dos indicadores do painel.

As regras de cálculo (janelas, maturidade, tamanho mínimo de amostra) estão nas
constantes abaixo e descritas em referencias/painel.md. Nada aqui inventa número:
dado ausente vira None e aparece como "não medido".
"""
from __future__ import annotations

import math
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from _comum import (
    NAO_MEDIDO,
    fmt_data,
    fmt_data_curta,
    fmt_dec,
    fmt_int,
    fmt_pct,
    fmt_sinal,
    ler_data,
    ler_json_arquivo,
    ler_momento,
    ler_numero,
    ler_tabela,
    normalizar_coluna,
    plural,
)

VERSAO_MODELO = 1

DIAS_AVISO_DADOS = 7
HORAS_MATURIDADE = 48
JANELA_KPI_DIAS = 28
MIN_ESPAN_TENDENCIA = 14
N_AMOSTRA_MINIMA = 3
N_AMOSTRA_OK = 5
N_MIN_RANKING = 6
LIMITE_CONCENTRACAO = 0.5
INDICE_ACIMA = 1.25
INDICE_ABAIXO = 0.75
DIAS_REF_ANTIGAS = 90
SEMANAS_GRAFICO = 8
SEMANAS_RITMO = 4
RAZAO_RITMO_ATENCAO = 0.6
RAZAO_ROTINA_ATENCAO = 0.7
MIN_POSTS_CLASSIFICADOS_MIX = 6
DIFERENCA_MIX_ALERTA = 20

FORMATOS = ("carrossel", "post_unico", "reel")
NOMES_FORMATO = {"carrossel": "Carrossel", "post_unico": "Post único", "reel": "Reel"}
ETAPAS = ("atracao", "relacionamento", "conversao")
NOMES_ETAPA = {"atracao": "Atração", "relacionamento": "Relacionamento", "conversao": "Conversão"}
METRICAS = ("alcance", "visualizacoes", "curtidas", "comentarios", "salvamentos", "compartilhamentos")
SEM_CLASSIFICACAO = "_sem"

EXTRAS_PERFIL = {
    "alcance": ("alcance", "alcance_conta", "alcance_30d", "alcance_7d", "reach"),
    "visualizacoes": ("visualizacoes", "visualizacoes_conta", "visualizacoes_30d", "visualizacoes_7d", "views"),
    "visitas_perfil": ("visitas_perfil", "visitas_ao_perfil", "visitas_perfil_30d", "visitas_perfil_7d", "profile_views"),
    "seguidores_ganhos": ("seguidores_ganhos", "novos_seguidores", "seguidores_novos", "follows"),
    "seguidores_perdidos": ("seguidores_perdidos", "deixaram_de_seguir", "unfollows"),
}
ROTULOS_EXTRAS = {
    "alcance": "Alcance da conta",
    "visualizacoes": "Visualizações da conta",
    "visitas_perfil": "Visitas ao perfil",
    "seguidores_ganhos": "Seguidores ganhos",
    "seguidores_perdidos": "Seguidores perdidos",
}

UNIDADES_INDICADOR = {
    "seguidores": "seguidores",
    "posts_por_semana": "posts por semana",
    "alcance_medio": "contas alcançadas por post",
    "salvamentos_medio": "salvamentos por post",
    "comentarios_medio": "comentários por post",
    "compartilhamentos_medio": "compartilhamentos por post",
    "manual": "",
}
CAMPO_DO_INDICADOR = {
    "alcance_medio": "alcance",
    "salvamentos_medio": "salvamentos",
    "comentarios_medio": "comentarios",
    "compartilhamentos_medio": "compartilhamentos",
}

NOMES_INDICADOR = {
    "seguidores": "seguidores",
    "posts_por_semana": "posts por semana",
    "alcance_medio": "alcance médio por post",
    "salvamentos_medio": "salvamentos médios por post",
    "comentarios_medio": "comentários médios por post",
    "compartilhamentos_medio": "compartilhamentos médios por post",
    "manual": "número informado pela pessoa",
}

ROTULOS_STATUS_META = {
    "atingida": "Atingida",
    "no_caminho": "No caminho",
    "atencao": "Atenção",
    "critico": "Crítico",
    "prazo_vencido": "Prazo vencido",
    "nao_medido": "Não medido",
    "sem_ritmo": "Sem base para o ritmo",
    "amostra_pequena": "Amostra pequena",
}


class Contexto:
    def __init__(self, hoje: date, fuso: timezone):
        self.hoje = hoje
        self.fuso = fuso
        self.avisos: list[str] = []

    def aviso(self, texto: str) -> None:
        if texto not in self.avisos:
            self.avisos.append(texto)


def semana_inicio(d: date) -> date:
    return d - timedelta(days=d.weekday())


def normalizar_formato(texto) -> str | None:
    t = normalizar_coluna(str(texto or ""))
    if not t:
        return None
    if any(k in t for k in ("carrossel", "carousel", "album", "sidecar")):
        return "carrossel"
    if "reel" in t or "video" in t:
        return "reel"
    if any(k in t for k in ("post_unico", "image", "imagem", "foto", "unico", "single")):
        return "post_unico"
    return None


def rotulo_amostra(n: int) -> str | None:
    if n == 0:
        return "sem posts maduros"
    if n < N_AMOSTRA_MINIMA:
        return "amostra mínima"
    if n < N_AMOSTRA_OK:
        return "amostra pequena"
    return None


def media(valores: list[float]):
    return statistics.fmean(valores) if valores else None


def mediana(valores: list[float]):
    return statistics.median(valores) if valores else None


def valor_indicador_texto(ind: str, v, sinal: bool = False) -> str:
    if v is None:
        return NAO_MEDIDO
    casas = 0 if ind in ("seguidores", "alcance_medio") or (ind == "manual" and float(v).is_integer()) else 1
    if sinal:
        return fmt_sinal(v, casas)
    return fmt_int(v) if casas == 0 else fmt_dec(v, casas)


def serializar(obj):
    if isinstance(obj, dict):
        return {str(k): serializar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serializar(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat(timespec="minutes")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, float):
        return round(obj, 6)
    return obj


def carregar_perfil(pasta: Path, ctx: Contexto) -> dict:
    t = ler_tabela(pasta / "metricas" / "perfil.csv")
    for a in t.avisos:
        ctx.aviso(f"perfil.csv: {a}")
    pontos: list[dict] = []
    for r in t.linhas:
        onde = f"perfil.csv linha {r['_linha']}"
        dt, _ = ler_momento(r.get("coletado_em"), ctx.fuso)
        if dt is None:
            ctx.aviso(f"{onde}: 'coletado_em' vazio ou inválido; linha ignorada.")
            continue
        if dt.date() > ctx.hoje:
            ctx.aviso(f"{onde}: a data de coleta {dt.date()} está no futuro; linha ignorada.")
            continue
        ponto = {
            "dt": dt,
            "dia": dt.date(),
            "seguidores": ler_numero(r.get("seguidores"), inteiro=True, avisos=ctx.avisos, onde=onde),
            "seguindo": ler_numero(r.get("seguindo"), inteiro=True, avisos=ctx.avisos, onde=onde),
            "publicacoes": ler_numero(r.get("publicacoes"), inteiro=True, avisos=ctx.avisos, onde=onde),
            "extras": {},
        }
        for nome, apelidos in EXTRAS_PERFIL.items():
            for ap in apelidos:
                if ap in r:
                    ponto["extras"][nome] = ler_numero(r[ap], inteiro=True, avisos=ctx.avisos, onde=f"{onde} ({ap})")
                    break
        pontos.append(ponto)
    pontos.sort(key=lambda p: p["dt"])
    por_dia: dict[date, dict] = {}
    for p in pontos:
        if p["dia"] in por_dia:
            ctx.aviso(f"perfil.csv: mais de uma coleta em {fmt_data(p['dia'])}; valeu a última do dia.")
        por_dia[p["dia"]] = p
    pontos = [por_dia[d] for d in sorted(por_dia)]
    if t.existe and t.linhas and "seguidores" not in t.colunas:
        ctx.aviso("perfil.csv: não tem a coluna 'seguidores'; a evolução de seguidores fica como não medido.")
    return {"existe": t.existe, "linhas": len(t.linhas), "pontos": pontos}


def carregar_snapshots(pasta: Path, ctx: Contexto) -> dict:
    t = ler_tabela(pasta / "metricas" / "posts.csv")
    for a in t.avisos:
        ctx.aviso(f"posts.csv: {a}")
    ausentes = [c for c in ("alcance", "salvamentos", "compartilhamentos", "comentarios", "visualizacoes") if t.linhas and c not in t.colunas]
    for c in ausentes:
        ctx.aviso(f"posts.csv: não tem a coluna '{c}'; esse indicador fica como não medido.")
    por_chave: dict[str, dict] = {}
    ultima_coleta: date | None = None
    primeira_coleta: date | None = None
    for r in t.linhas:
        onde = f"posts.csv linha {r['_linha']}"
        coletado, _ = ler_momento(r.get("coletado_em"), ctx.fuso)
        if coletado is None:
            ctx.aviso(f"{onde}: 'coletado_em' vazio ou inválido; linha ignorada.")
            continue
        if coletado.date() > ctx.hoje:
            ctx.aviso(f"{onde}: a data de coleta {coletado.date()} está no futuro; linha ignorada.")
            continue
        publicado, _ = ler_momento(r.get("publicado_em"), ctx.fuso)
        media_id = r.get("media_id", "")
        permalink = r.get("permalink", "")
        chave = media_id or permalink or (f"{publicado.isoformat()}|{r.get('tipo', '')}" if publicado else "")
        if not chave:
            ctx.aviso(f"{onde}: sem media_id, permalink nem data de publicação; linha ignorada.")
            continue
        snap = {
            "media_id": media_id,
            "post_id": r.get("post_id", ""),
            "publicado": publicado,
            "coletado": coletado,
            "tipo": r.get("tipo", ""),
            "permalink": permalink,
        }
        for m in METRICAS + ("interacoes",):
            snap[m] = ler_numero(r.get(m), inteiro=True, avisos=ctx.avisos, onde=f"{onde} ({m})")
        if ultima_coleta is None or coletado.date() > ultima_coleta:
            ultima_coleta = coletado.date()
        if primeira_coleta is None or coletado.date() < primeira_coleta:
            primeira_coleta = coletado.date()
        atual = por_chave.get(chave)
        if atual is None:
            por_chave[chave] = {"chave": chave, "ultimo": snap, "n_coletas": 1}
        else:
            atual["n_coletas"] += 1
            if snap["coletado"] >= atual["ultimo"]["coletado"]:
                atual["ultimo"] = snap
    return {
        "existe": t.existe,
        "linhas": len(t.linhas),
        "posts": list(por_chave.values()),
        "ultima_coleta": ultima_coleta,
        "primeira_coleta": primeira_coleta,
    }


def carregar_publicados(pasta: Path, ctx: Contexto) -> dict:
    t = ler_tabela(pasta / "publicacao" / "publicados.csv")
    for a in t.avisos:
        ctx.aviso(f"publicados.csv: {a}")
    itens: list[dict] = []
    for r in t.linhas:
        publicado, _ = ler_momento(r.get("publicado_em"), ctx.fuso)
        itens.append(
            {
                "publicado": publicado,
                "post_id": r.get("post_id", ""),
                "lote": r.get("lote", ""),
                "formato": r.get("formato", ""),
                "media_id": r.get("media_id", ""),
                "permalink": r.get("permalink", ""),
            }
        )
    ultima = max((i["publicado"].date() for i in itens if i["publicado"]), default=None)
    return {"existe": t.existe, "linhas": len(t.linhas), "itens": itens, "ultima": ultima}


def carregar_posts_projeto(pasta: Path, ctx: Contexto) -> dict:
    indice: dict[str, dict] = {}
    base = pasta / "conteudo"
    if not base.is_dir():
        return {"existe": False, "indice": indice}
    for lote in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")):
        pasta_posts = lote / "posts"
        if not pasta_posts.is_dir():
            continue
        for arq in sorted(pasta_posts.glob("*.json")):
            dados, erro = ler_json_arquivo(arq)
            nome = f"conteudo/{lote.name}/posts/{arq.name}"
            if erro or not isinstance(dados, dict):
                ctx.aviso(f"{nome}: {erro or 'não é um objeto JSON'}; post ignorado no cruzamento.")
                continue
            pid = str(dados.get("id") or arq.stem)
            if pid in indice:
                ctx.aviso(f"{nome}: o id '{pid}' já existe em outro lote; valeu o primeiro.")
                continue
            indice[pid] = {
                "id": pid,
                "lote": str(dados.get("lote") or lote.name),
                "titulo": str(dados.get("titulo_interno") or "").strip(),
                "pilar": str(dados.get("pilar") or "").strip() or None,
                "formato": normalizar_formato(dados.get("formato")),
                "etapa": str(dados.get("etapa_funil") or "").strip() or None,
                "chamada": bool(str(dados.get("chamada") or "").strip()),
                "status": str(dados.get("status") or ""),
            }
    return {"existe": True, "indice": indice}


def carregar_referencias(pasta: Path, ctx: Contexto) -> dict:
    t = ler_tabela(pasta / "referencias" / "referencias.csv")
    for a in t.avisos:
        ctx.aviso(f"referencias.csv: {a}")
    itens: list[dict] = []
    for r in t.linhas:
        onde = f"referencias.csv linha {r['_linha']}"
        perfil = r.get("perfil", "")
        if not perfil:
            ctx.aviso(f"{onde}: sem o campo 'perfil'; linha ignorada.")
            continue
        dt, _ = ler_momento(r.get("data"), ctx.fuso)
        pct = ler_numero(r.get("pct_cta"), avisos=ctx.avisos, onde=onde)
        if pct is not None and pct > 100:
            ctx.aviso(f"{onde}: pct_cta {pct:g} é maior que 100; tratado como não medido.")
            pct = None
        itens.append(
            {
                "perfil": perfil,
                "nicho": r.get("nicho", ""),
                "tipo": r.get("tipo", ""),
                "data": dt.date() if dt else None,
                "seguidores": ler_numero(r.get("seguidores"), inteiro=True, avisos=ctx.avisos, onde=onde),
                "posts_semana": ler_numero(r.get("posts_semana"), avisos=ctx.avisos, onde=onde),
                "mediana_views": ler_numero(r.get("mediana_views"), inteiro=True, avisos=ctx.avisos, onde=onde),
                "pct_cta": pct,
                "alavanca": r.get("alavanca", ""),
            }
        )
    ultima = max((i["data"] for i in itens if i["data"]), default=None)
    return {"existe": t.existe, "linhas": len(t.linhas), "itens": itens, "ultima": ultima}


def seguidores_na_data(serie: list[tuple[date, int]], dia: date | None) -> tuple[int | None, bool]:
    """Seguidores na última coleta até o dia. O segundo valor diz se é aproximação (sem coleta recente antes do dia)."""
    if not serie or dia is None:
        return None, False
    antes = [(d, v) for d, v in serie if d <= dia]
    if not antes:
        return serie[0][1], True
    d, v = antes[-1]
    return v, (dia - d).days > 14


def analisar_seguidores(perfil: dict, hoje: date) -> dict:
    serie = [(p["dia"], p["seguidores"]) for p in perfil["pontos"] if p["seguidores"] is not None]
    extras: dict[str, dict] = {}
    for nome in EXTRAS_PERFIL:
        for p in reversed(perfil["pontos"]):
            if p["extras"].get(nome) is not None:
                extras[nome] = {"valor": p["extras"][nome], "dia": p["dia"]}
                break
    if not serie:
        return {"disponivel": False, "serie": [], "n_coletas": 0, "extras": extras}
    dia_atual, atual = serie[-1]
    dia_ini, inicial = serie[0]
    janela = {"dias": None, "saldo": None, "ritmo_semana": None, "dia_ref": None}
    candidatos = [(d, v) for d, v in serie[:-1] if (dia_atual - d).days >= MIN_ESPAN_TENDENCIA]
    if candidatos:
        d_ref, v_ref = min(candidatos, key=lambda x: abs((dia_atual - x[0]).days - JANELA_KPI_DIAS))
        span = (dia_atual - d_ref).days
        janela = {"dias": span, "saldo": atual - v_ref, "ritmo_semana": (atual - v_ref) / span * 7, "dia_ref": d_ref}
    return {
        "disponivel": True,
        "serie": [{"dia": d, "valor": v} for d, v in serie],
        "n_coletas": len(serie),
        "atual": atual,
        "dia_atual": dia_atual,
        "inicial": inicial,
        "dia_inicial": dia_ini,
        "saldo_total": atual - inicial,
        "dias_total": (dia_atual - dia_ini).days,
        "janela": janela,
        "extras": extras,
    }


def unificar_posts(snaps: dict, publicados: dict, projeto: dict, serie: list[tuple[date, int]], ctx: Contexto) -> list[dict]:
    pub_por_media = {i["media_id"]: i for i in publicados["itens"] if i["media_id"]}
    pub_por_post = {i["post_id"]: i for i in publicados["itens"] if i["post_id"]}
    usados: set[int] = set()
    posts: list[dict] = []
    sem_json: list[str] = []

    def montar(snap: dict | None, pub: dict | None, n_coletas: int, chave: str) -> dict:
        post_id = (snap or {}).get("post_id") or (pub or {}).get("post_id") or ""
        proj = projeto["indice"].get(post_id) if post_id else None
        if post_id and proj is None:
            sem_json.append(post_id)
        publicado = (snap or {}).get("publicado") or (pub or {}).get("publicado")
        pub_dia = publicado.date() if publicado else None
        tipo = (snap or {}).get("tipo", "")
        formato = (proj or {}).get("formato") or normalizar_formato((pub or {}).get("formato")) or normalizar_formato(tipo)
        titulo = (proj or {}).get("titulo") or post_id
        if not titulo:
            titulo = f"Post de {fmt_data_curta(pub_dia)}" if pub_dia else "Post sem data"
        coletado = (snap or {}).get("coletado")
        if snap is None:
            estado, idade_h = "sem_metricas", None
        elif publicado is None:
            estado, idade_h = "sem_data", None
        else:
            idade_h = (coletado - publicado).total_seconds() / 3600
            if idade_h < 0:
                ctx.aviso(f"Post {post_id or chave}: a coleta é anterior à publicação; ignorado nas médias.")
                estado = "sem_data"
            else:
                estado = "maduro" if idade_h >= HORAS_MATURIDADE else "imaturo"
        p = {
            "chave": chave,
            "media_id": (snap or {}).get("media_id") or (pub or {}).get("media_id", ""),
            "post_id": post_id,
            "do_projeto": bool(post_id),
            "titulo": titulo,
            "permalink": (snap or {}).get("permalink") or (pub or {}).get("permalink", ""),
            "publicado": publicado,
            "pub_dia": pub_dia,
            "coletado": coletado,
            "n_coletas": n_coletas,
            "tipo": tipo,
            "formato": formato,
            "pilar": (proj or {}).get("pilar"),
            "etapa": (proj or {}).get("etapa"),
            "chamada": (proj or {}).get("chamada") if proj else None,
            "lote": (proj or {}).get("lote") or (pub or {}).get("lote", ""),
            "estado": estado,
            "idade_h": idade_h,
        }
        for m in METRICAS + ("interacoes",):
            p[m] = (snap or {}).get(m)
        sf, aprox = seguidores_na_data(serie, pub_dia)
        p["seguidores_na_data"] = sf
        p["seguidores_aprox"] = aprox
        p["alcance_rel"] = (p["alcance"] / sf) if (p["alcance"] is not None and sf) else None
        trio = (p["salvamentos"], p["compartilhamentos"], p["comentarios"])
        p["interacao_valor"] = (sum(trio) / p["alcance"]) if (None not in trio and p["alcance"]) else None
        return p

    for item in snaps["posts"]:
        snap = item["ultimo"]
        pub = pub_por_media.get(snap["media_id"]) if snap["media_id"] else None
        if pub is None and snap["post_id"]:
            pub = pub_por_post.get(snap["post_id"])
        if pub is not None:
            usados.add(id(pub))
        posts.append(montar(snap, pub, item["n_coletas"], item["chave"]))
    for pub in publicados["itens"]:
        if id(pub) in usados:
            continue
        chave = pub["media_id"] or pub["post_id"] or pub["permalink"] or f"pub-{len(posts)}"
        posts.append(montar(None, pub, 0, chave))

    if sem_json:
        unicos = sorted(set(sem_json))
        ctx.aviso(
            f"{plural(len(unicos), 'post_id')} sem arquivo em conteudo/<lote>/posts/ "
            f"({', '.join(unicos[:4])}{'…' if len(unicos) > 4 else ''}): o pilar e a etapa desses posts ficam sem classificação."
        )
    posts.sort(key=lambda p: (p["publicado"] or datetime.min.replace(tzinfo=ctx.fuso)))
    return posts


def estatisticas(posts: list[dict]) -> dict:
    maduros = [p for p in posts if p["estado"] == "maduro"]
    e: dict = {
        "n_posts": len(posts),
        "n_maduros": len(maduros),
        "n_imaturos": sum(1 for p in posts if p["estado"] == "imaturo"),
        "n_sem_metricas": sum(1 for p in posts if p["estado"] in ("sem_metricas", "sem_data")),
        "amostra": rotulo_amostra(len(maduros)),
    }
    for m in METRICAS:
        vals = [p[m] for p in maduros if p[m] is not None]
        e[m] = {
            "n": len(vals),
            "media": media(vals),
            "mediana": mediana(vals),
            "soma": sum(vals) if vals else None,
        }
    for m in ("salvamentos", "compartilhamentos", "comentarios"):
        pares = [(p[m], p["alcance"]) for p in maduros if p[m] is not None and p["alcance"]]
        den = sum(a for _, a in pares)
        e["taxa_" + m] = {"n": len(pares), "valor": (sum(x for x, _ in pares) / den) if den else None}
    comp = [p for p in maduros if p["interacao_valor"] is not None]
    den = sum(p["alcance"] for p in comp)
    e["interacao_valor"] = {
        "n": len(comp),
        "valor": (sum(p["salvamentos"] + p["compartilhamentos"] + p["comentarios"] for p in comp) / den) if den else None,
    }
    rel = [p["alcance_rel"] for p in maduros if p["alcance_rel"] is not None]
    e["alcance_rel"] = {"n": len(rel), "media": media(rel), "mediana": mediana(rel)}
    alc = [p["alcance"] for p in maduros if p["alcance"] is not None]
    e["concentracao"] = (max(alc) / sum(alc)) if (len(alc) >= N_AMOSTRA_MINIMA and sum(alc) > 0) else None
    return e


CHAVES_INDICE = (
    ("alcance_rel", "mediana"),
    ("taxa_salvamentos", "valor"),
    ("taxa_compartilhamentos", "valor"),
    ("taxa_comentarios", "valor"),
    ("interacao_valor", "valor"),
)


def indices_contra_conta(stats: dict, conta: dict) -> dict:
    saida = {}
    for k, campo in CHAVES_INDICE:
        g, c = stats[k][campo], conta[k][campo]
        saida[k] = (g / c) if (g is not None and c) else None
    return saida


def montar_grupos(posts: list[dict], ordem: list[tuple[str, str]], chave_fn, conta: dict, nome_sem: str) -> list[dict]:
    por_id: dict[str, list[dict]] = {}
    for p in posts:
        por_id.setdefault(chave_fn(p) or SEM_CLASSIFICACAO, []).append(p)
    ids_conhecidos = [i for i, _ in ordem]
    extras = sorted(k for k in por_id if k not in ids_conhecidos and k != SEM_CLASSIFICACAO)
    sequencia = list(ordem) + [(k, f"{k} (fora da estratégia)") for k in extras]
    if SEM_CLASSIFICACAO in por_id:
        sequencia.append((SEM_CLASSIFICACAO, nome_sem))
    grupos = []
    for gid, nome in sequencia:
        itens = por_id.get(gid, [])
        s = estatisticas(itens)
        grupos.append(
            {
                "id": gid,
                "nome": nome,
                "chaves": [p["chave"] for p in itens],
                "stats": s,
                "indices": indices_contra_conta(s, conta),
            }
        )
    return grupos


def analisar_ritmo(posts: list[dict], fim: date | None, inicio_dados: date | None, estrategia: dict, so_projeto: bool = False) -> dict:
    if fim is None or inicio_dados is None or not any(p["pub_dia"] for p in posts):
        return {"disponivel": False}
    dias_pub = [p["pub_dia"] for p in posts if p["pub_dia"] and p["pub_dia"] <= fim]
    primeiro = min([inicio_dados] + dias_pub)
    w_ultima = semana_inicio(fim)
    w_primeira = semana_inicio(primeiro)
    semanas: list[dict] = []
    w = w_ultima
    while w >= w_primeira and len(semanas) < SEMANAS_GRAFICO:
        fim_sem = w + timedelta(days=6)
        doc = [p for p in posts if p["pub_dia"] and w <= p["pub_dia"] <= fim_sem and p["pub_dia"] <= fim]
        completa = fim_sem <= fim
        parcial_inicio = w < primeiro
        por_formato = {f: sum(1 for p in doc if p["formato"] == f) for f in FORMATOS}
        semanas.append(
            {
                "inicio": w,
                "n_projeto": sum(1 for p in doc if p["do_projeto"]),
                "n_fora": sum(1 for p in doc if not p["do_projeto"]),
                "total": len(doc),
                "completa": completa,
                "elegivel": completa and not parcial_inicio,
                "por_formato": por_formato,
                "parcial_inicio": parcial_inicio,
                "sem_formato": sum(1 for p in doc if p["formato"] not in FORMATOS),
            }
        )
        w -= timedelta(days=7)
    semanas.reverse()
    elegiveis = [s for s in semanas if s["elegivel"]][-SEMANAS_RITMO:]
    meta = (estrategia.get("ritmo") or {}).get("posts_por_semana")
    r: dict = {
        "disponivel": True,
        "so_projeto": so_projeto,
        "semanas": semanas,
        "n_semanas_media": len(elegiveis),
        "media_recente": None,
        "meta": meta,
        "razao": None,
        "status": "sem_base",
        "por_formato_real": {f: None for f in FORMATOS},
        "por_formato_plano": (estrategia.get("ritmo") or {}).get("formatos") or {},
        "anterior": None,
    }
    if len(elegiveis) >= 2:
        r["media_recente"] = media([s["total"] for s in elegiveis])
        for f in FORMATOS:
            r["por_formato_real"][f] = media([s["por_formato"][f] for s in elegiveis])
        todas_el = [s for s in semanas if s["elegivel"]]
        ant = todas_el[-2 * SEMANAS_RITMO : -SEMANAS_RITMO]
        if len(ant) >= 2:
            r["anterior"] = media([s["total"] for s in ant])
        if meta:
            r["razao"] = r["media_recente"] / meta
            r["status"] = "ok" if r["razao"] >= 1 else ("atencao" if r["razao"] >= RAZAO_ROTINA_ATENCAO else "critico")
        else:
            r["status"] = "sem_meta"
    return r


def janela_stats(posts: list[dict], campo: str, ini: date, fim: date, agregado=media) -> dict:
    vals = [p[campo] for p in posts if p["estado"] == "maduro" and p["pub_dia"] and ini <= p["pub_dia"] <= fim and p.get(campo) is not None]
    n = len(vals)
    return {
        "valor": agregado(vals),
        "n": n,
        "conc": (max(vals) / sum(vals)) if (n >= N_AMOSTRA_MINIMA and sum(vals) > 0) else None,
        "desvio": statistics.stdev(vals) if n >= 2 else None,
    }


def taxa_na_janela(posts: list[dict], ini: date, fim: date) -> tuple[float | None, int]:
    sel = [p for p in posts if p["estado"] == "maduro" and p["pub_dia"] and ini <= p["pub_dia"] <= fim and p["interacao_valor"] is not None]
    den = sum(p["alcance"] for p in sel)
    num = sum(p["salvamentos"] + p["compartilhamentos"] + p["comentarios"] for p in sel)
    return ((num / den) if den else None, len(sel))


def diferenca_confiavel(a: dict, b: dict) -> tuple[bool, str]:
    """Diz se a diferença entre as médias de duas janelas é mais que a variação normal entre posts.

    Exige 5 posts maduros em cada janela, nenhum post com mais da metade do total e uma diferença
    maior que 1 erro-padrão. Quando falha, devolve o motivo em português.
    """
    if a["valor"] is None or b["valor"] is None or a["n"] < N_AMOSTRA_OK or b["n"] < N_AMOSTRA_OK:
        return False, f"preciso de {N_AMOSTRA_OK} posts maduros em cada janela de 4 semanas (hoje: {a['n']} e {b['n']})"
    if (a["conc"] or 0) > LIMITE_CONCENTRACAO or (b["conc"] or 0) > LIMITE_CONCENTRACAO:
        return False, "um único post concentra mais da metade do total em uma das janelas, e isso distorce a média"
    erro = math.sqrt((a["desvio"] or 0) ** 2 / a["n"] + (b["desvio"] or 0) ** 2 / b["n"])
    if abs(a["valor"] - b["valor"]) <= erro:
        return False, "a diferença entre as duas janelas é menor que a variação normal entre um post e outro"
    return True, ""


def calcular_kpis(posts: list[dict], fim: date | None) -> dict:
    if fim is None:
        return {}
    ini_a, fim_a = fim - timedelta(days=JANELA_KPI_DIAS - 1), fim
    ini_b, fim_b = fim - timedelta(days=2 * JANELA_KPI_DIAS - 1), fim - timedelta(days=JANELA_KPI_DIAS)

    a = janela_stats(posts, "alcance", ini_a, fim_a)
    a0 = janela_stats(posts, "alcance", ini_b, fim_b)
    delta_alcance = None
    if diferenca_confiavel(a, a0)[0] and a0["valor"]:
        delta_alcance = (a["valor"] - a0["valor"]) / a0["valor"]
    t, nt = taxa_na_janela(posts, ini_a, fim_a)
    t0, nt0 = taxa_na_janela(posts, ini_b, fim_b)
    delta_taxa = ((t - t0) / t0) if (t is not None and t0 and nt >= N_AMOSTRA_OK and nt0 >= N_AMOSTRA_OK) else None
    r = janela_stats(posts, "alcance_rel", ini_a, fim_a, mediana)
    r0 = janela_stats(posts, "alcance_rel", ini_b, fim_b, mediana)
    delta_rel = ((r["valor"] - r0["valor"]) / r0["valor"]) if (r["valor"] is not None and r0["valor"] and r["n"] >= N_AMOSTRA_OK and r0["n"] >= N_AMOSTRA_OK) else None
    return {
        "janela": {"ini": ini_a, "fim": fim_a, "ini_anterior": ini_b, "fim_anterior": fim_b},
        "alcance_medio": {"valor": a["valor"], "n": a["n"], "anterior": a0["valor"], "n_anterior": a0["n"], "concentracao": a["conc"], "delta": delta_alcance},
        "interacao_valor": {"valor": t, "n": nt, "anterior": t0, "n_anterior": nt0, "concentracao": None, "delta": delta_taxa},
        "alcance_rel": {"valor": r["valor"], "n": r["n"], "anterior": r0["valor"], "n_anterior": r0["n"], "concentracao": None, "delta": delta_rel},
    }


def avaliar_meta(meta: dict, seg: dict, ritmo: dict, posts: list[dict], fim: date | None, hoje: date) -> dict:
    ind = meta["indicador"]
    base, alvo = meta["base"], meta["alvo"]
    prazo = ler_data(meta["prazo"])
    atual = tendencia = None
    n_base = None
    nota = ""
    if ind == "seguidores":
        if seg["disponivel"]:
            atual = seg["atual"]
            tendencia = seg["janela"]["ritmo_semana"]
            n_base = seg["n_coletas"]
            if tendencia is None:
                nota = "Poucas coletas para medir o ritmo: preciso de duas coletas com pelo menos 14 dias de diferença."
    elif ind == "posts_por_semana":
        if ritmo.get("media_recente") is not None:
            atual = ritmo["media_recente"]
            n_base = ritmo["n_semanas_media"]
            if ritmo.get("so_projeto"):
                nota = "Conta só os posts publicados por este projeto: sem coleta de posts, não sei dos posts de fora."
    elif ind in CAMPO_DO_INDICADOR and fim is not None:
        campo = CAMPO_DO_INDICADOR[ind]
        ini_a, ini_b = fim - timedelta(days=JANELA_KPI_DIAS - 1), fim - timedelta(days=2 * JANELA_KPI_DIAS - 1)
        j = janela_stats(posts, campo, ini_a, fim)
        j0 = janela_stats(posts, campo, ini_b, fim - timedelta(days=JANELA_KPI_DIAS))
        n_base = j["n"]
        if j["n"] >= N_AMOSTRA_MINIMA:
            atual = j["valor"]
            confiavel, motivo = diferenca_confiavel(j, j0)
            if confiavel:
                tendencia = (j["valor"] - j0["valor"]) / (JANELA_KPI_DIAS / 7)
            else:
                nota = f"Para medir o ritmo: {motivo}."
            if j["conc"] and j["conc"] > LIMITE_CONCENTRACAO:
                nota += f" Um único post concentra {fmt_pct(j['conc'], 0)} do total desta média: ela é instável."
        else:
            nota = (
                f"Nenhum post maduro nos últimos {JANELA_KPI_DIAS} dias."
                if j["n"] == 0
                else f"Só {plural(j['n'], 'post maduro', 'posts maduros')} nos últimos {JANELA_KPI_DIAS} dias: poucos para medir."
            )
    elif ind == "manual":
        atual = meta.get("atual")
        if atual is None:
            nota = "Valor informado pela pessoa: ainda não foi registrado no campo 'atual' da meta."

    sentido = 1 if alvo >= base else -1
    status = "nao_medido"
    necessario = None
    semanas_rest = None
    if prazo is not None:
        semanas_rest = max((prazo - hoje).days, 0) / 7
    if atual is None:
        status = "amostra_pequena" if (ind in CAMPO_DO_INDICADOR and n_base is not None and n_base > 0) else "nao_medido"
    elif sentido * (atual - alvo) >= 0:
        status = "atingida"
    elif prazo is not None and prazo < hoje:
        status = "prazo_vencido"
    else:
        semanas_calc = max((prazo - hoje).days, 1) / 7 if prazo else None
        necessario = (alvo - atual) / semanas_calc if semanas_calc else None
        if ind == "posts_por_semana":
            razao = atual / alvo if alvo else 0
            status = "atencao" if razao >= RAZAO_ROTINA_ATENCAO else "critico"
            necessario = None
        elif tendencia is None or necessario is None:
            status = "sem_ritmo"
        else:
            razao = (sentido * tendencia) / abs(necessario)
            status = "no_caminho" if razao >= 1 else ("atencao" if razao >= RAZAO_RITMO_ATENCAO else "critico")
    progresso = None
    if atual is not None and base != alvo:
        progresso = (atual - base) / (alvo - base)
    return {
        "id": meta["id"],
        "descricao": meta["descricao"],
        "indicador": ind,
        "unidade": UNIDADES_INDICADOR.get(ind, ""),
        "base": base,
        "alvo": alvo,
        "prazo": prazo,
        "atual": atual,
        "atual_em": meta.get("atual_em"),
        "progresso": progresso,
        "falta": (alvo - atual) if atual is not None else None,
        "semanas_restantes": semanas_rest,
        "ritmo_necessario": necessario,
        "ritmo_recente": tendencia,
        "n_base": n_base,
        "status": status,
        "status_rotulo": ROTULOS_STATUS_META[status],
        "nota": nota,
    }


def montar_movimentos(movs: list[dict], seg: dict, ritmo: dict, posts: list[dict], fim: date | None, hoje: date) -> list[dict]:
    saida = []
    for mv in movs:
        ate = ler_data(mv["ate"])
        ind = str(mv["indicador"]).strip()
        atual = None
        if ind in NOMES_INDICADOR and ind != "manual":
            sonda = {"id": "movimento", "descricao": str(mv["o_que"]), "indicador": ind, "base": 0, "alvo": 1, "prazo": mv["ate"]}
            atual = avaliar_meta(sonda, seg, ritmo, posts, fim, hoje)["atual"]
        saida.append(
            {
                "o_que": str(mv["o_que"]),
                "indicador": ind,
                "indicador_nome": NOMES_INDICADOR.get(ind, ind),
                "mede_sozinho": ind in NOMES_INDICADOR and ind != "manual",
                "ate": ate,
                "dias": (ate - hoje).days if ate else None,
                "atual": atual,
                "atual_texto": valor_indicador_texto(ind, atual) if atual is not None else None,
            }
        )
    return saida


def analisar_funil(grupos_etapa: list[dict], conta: dict, estrategia: dict) -> dict:
    chaves = {
        "atracao": ("alcance_rel", "mediana", "alcance relativo, mediana (alcance ÷ seguidores)"),
        "relacionamento": ("taxa_salvamentos", "valor", "salvamentos ÷ alcance"),
        "conversao": ("taxa_comentarios", "valor", "comentários ÷ alcance (aproximação: cliques e conversas não são medidos)"),
    }
    plano = estrategia.get("funil") or {}
    etapas = []
    por_id = {g["id"]: g for g in grupos_etapa}
    for e in ETAPAS:
        g = por_id.get(e)
        k, campo, rotulo = chaves[e]
        n = g["stats"]["n_maduros"] if g else 0
        valor = g["stats"][k][campo] if g else None
        base_conta = conta[k][campo]
        indice = (valor / base_conta) if (valor is not None and base_conta) else None
        etapas.append(
            {
                "id": e,
                "nome": NOMES_ETAPA[e],
                "plano": plano.get(e, ""),
                "metrica": rotulo,
                "chave_stat": k,
                "valor": valor,
                "conta": base_conta,
                "indice": indice,
                "n_maduros": n,
                "n_posts": g["stats"]["n_posts"] if g else 0,
                "amostra": rotulo_amostra(n),
            }
        )
    aptas = [x for x in etapas if x["indice"] is not None and x["n_maduros"] >= N_AMOSTRA_MINIMA]
    gargalo = None
    if len(aptas) >= 2:
        pior = min(aptas, key=lambda x: x["indice"])
        if pior["indice"] <= INDICE_ABAIXO:
            gargalo = pior["id"]
    return {"etapas": etapas, "gargalo": gargalo}


def montar_referencias(refs: dict, conta: dict, seguidores_atual: int | None, ritmo: dict, posts: list[dict], hoje: date) -> dict:
    maduros = [p for p in posts if p["estado"] == "maduro" and p["na_janela"]]
    vis_all = [p["visualizacoes"] for p in maduros if p["visualizacoes"] is not None]
    vis_reel = [p["visualizacoes"] for p in maduros if p["visualizacoes"] is not None and p["formato"] == "reel"]
    com_json = [p for p in posts if p["na_janela"] and p["chamada"] is not None]
    pct_cta = (100 * sum(1 for p in com_json if p["chamada"]) / len(com_json)) if com_json else None

    def linha(rotulo: str, vis: list[int]) -> dict:
        mv = mediana(vis)
        return {
            "rotulo": rotulo,
            "seguidores": seguidores_atual,
            "posts_semana": ritmo.get("media_recente"),
            "mediana_views": mv,
            "n_views": len(vis),
            "views_por_seguidor": (mv / seguidores_atual) if (mv is not None and seguidores_atual) else None,
            "pct_cta": pct_cta,
            "n_cta": len(com_json),
        }

    proprios = [linha("Você (todos os formatos)", vis_all)]
    if len(vis_reel) >= N_AMOSTRA_MINIMA:
        l2 = linha("Você (só reels)", vis_reel)
        l2["posts_semana"] = ritmo.get("por_formato_real", {}).get("reel")
        l2["pct_cta"] = None
        l2["n_cta"] = 0
        proprios.append(l2)
    itens = []
    for r in refs["itens"]:
        itens.append(
            {
                **r,
                "views_por_seguidor": (r["mediana_views"] / r["seguidores"]) if (r["mediana_views"] is not None and r["seguidores"]) else None,
                "idade_dias": (hoje - r["data"]).days if r["data"] else None,
                "antiga": bool(r["data"] and (hoje - r["data"]).days > DIAS_REF_ANTIGAS),
            }
        )
    return {"existe": refs["existe"], "proprios": proprios, "itens": itens}


def montar_fontes(perfil: dict, snaps: dict, publicados: dict, refs: dict, estrategia: dict, hoje: date) -> list[dict]:
    def idade(d: date | None):
        return (hoje - d).days if d else None

    ult_perfil = perfil["pontos"][-1]["dia"] if perfil["pontos"] else None
    fontes = [
        {"id": "perfil", "arquivo": "metricas/perfil.csv", "existe": perfil["existe"], "linhas": perfil["linhas"], "ultima": ult_perfil, "rotulo_data": "última coleta"},
        {"id": "posts", "arquivo": "metricas/posts.csv", "existe": snaps["existe"], "linhas": snaps["linhas"], "ultima": snaps["ultima_coleta"], "rotulo_data": "última coleta"},
        {"id": "publicados", "arquivo": "publicacao/publicados.csv", "existe": publicados["existe"], "linhas": publicados["linhas"], "ultima": publicados["ultima"], "rotulo_data": "última publicação"},
        {"id": "referencias", "arquivo": "referencias/referencias.csv", "existe": refs["existe"], "linhas": refs["linhas"], "ultima": refs["ultima"], "rotulo_data": "última análise"},
        {"id": "estrategia", "arquivo": "estrategia.json", "existe": True, "linhas": None, "ultima": ler_data(estrategia.get("atualizado_em")), "rotulo_data": "atualizada em"},
    ]
    for f in fontes:
        f["idade_dias"] = idade(f["ultima"])
    return fontes


def ultima_leitura(pasta: Path) -> dict | None:
    base = pasta / "metricas" / "leituras"
    if not base.is_dir():
        return None
    achados = []
    for arq in base.glob("*.md"):
        d = ler_data(arq.stem[:10])
        if d:
            achados.append((d, arq.name))
    if not achados:
        return None
    d, nome = max(achados)
    return {"data": d, "arquivo": f"leituras/{nome}"}


def nome_da_marca(pasta: Path, slug: str) -> tuple[str, str]:
    dados, erro = ler_json_arquivo(pasta / "visual.json")
    if not erro and isinstance(dados, dict):
        nome = str(dados.get("nome_exibicao") or "").strip()
        arroba = str(dados.get("arroba") or "").strip()
        if nome or arroba:
            return nome or arroba, arroba
    return slug, ""


def gerar_alertas(m: dict) -> list[dict]:
    alertas: list[dict] = []

    def add(sev: str, texto: str, ancora: str = "") -> None:
        alertas.append({"nivel": sev, "texto": texto, "ancora": ancora})

    d = m["dados"]
    if d["idade_dias"] is None:
        add("alta", "Ainda não há nenhuma coleta de métricas. Sem ela o painel só mostra o plano.", "dados")
    elif d["desatualizado"]:
        add("alta", f"A última coleta tem {d['idade_dias']} dias (limite de {DIAS_AVISO_DADOS}). Colete de novo antes de decidir.", "dados")

    for meta in m["metas"]:
        r = meta["status"]
        nome = meta["descricao"]
        if meta["indicador"] == "posts_por_semana" and r in ("critico", "atencao") and m["ritmo"].get("razao") is not None:
            continue
        if r == "critico":
            add("alta", f"Meta '{nome}' está fora do ritmo necessário.", "metas")
        elif r == "prazo_vencido":
            add("alta", f"Meta '{nome}' venceu em {fmt_data(meta['prazo'])} sem atingir o alvo.", "metas")
        elif r == "atencao":
            add("media", f"Meta '{nome}' está abaixo do ritmo necessário.", "metas")
        elif r in ("nao_medido",):
            add("baixa", f"Meta '{nome}' ainda não tem medição.", "metas")

    rit = m["ritmo"]
    if rit.get("disponivel") and rit.get("razao") is not None:
        txt = (
            f"Publicação em {fmt_dec(rit['media_recente'], 1)} posts por semana, "
            f"{fmt_pct(rit['razao'], 0)} da meta de {fmt_dec(rit['meta'], 0 if float(rit['meta']).is_integer() else 1)}."
        )
        if rit["status"] == "critico":
            add("alta", txt, "ritmo")
        elif rit["status"] == "atencao":
            add("media", txt, "ritmo")

    g = m["grupos"]
    classificados = [p for p in m["posts"] if p["na_janela"] and p["pilar"]]
    if len(classificados) >= MIN_POSTS_CLASSIFICADOS_MIX:
        for gp in g["pilar"]:
            if gp["id"] == SEM_CLASSIFICACAO or gp.get("peso") is None or gp.get("fatia_real") is None:
                continue
            dif = gp["fatia_real"] * 100 - gp["peso"]
            if abs(dif) >= DIFERENCA_MIX_ALERTA:
                sentido = "acima" if dif > 0 else "abaixo"
                add("media", f"O pilar '{gp['nome']}' está {abs(dif):.0f} pontos percentuais {sentido} do peso planejado ({gp['peso']:g}%).", "grupos")
    com_etapa = [p for p in m["posts"] if p["na_janela"] and p["etapa"]]
    if len(com_etapa) >= MIN_POSTS_CLASSIFICADOS_MIX:
        for e in ETAPAS:
            if not any(p["etapa"] == e for p in com_etapa):
                add("media", f"Nenhum post de {NOMES_ETAPA[e].lower()} no período: o funil fica sem essa etapa.", "funil")
    garg = m["funil"]["gargalo"]
    if garg:
        et = next(x for x in m["funil"]["etapas"] if x["id"] == garg)
        add("media", f"Hipótese: a etapa de {et['nome'].lower()} rende menos que a média da conta ({fmt_dec(et['indice'], 2)}× em {et['metrica'].split(' (')[0]}).", "funil")

    conta = g["conta"]
    if conta["n_maduros"] < N_MIN_RANKING:
        if conta["n_maduros"] == 0:
            add("media", "Nenhum post maduro ainda: não há como comparar grupos.", "grupos")
        else:
            add("media", f"Só {plural(conta['n_maduros'], 'post maduro', 'posts maduros')}: trate qualquer diferença entre grupos como pista, não como regra.", "grupos")
    imaturos = conta["n_imaturos"]
    if imaturos:
        add("info", f"{plural(imaturos, 'post')} com menos de {HORAS_MATURIDADE} horas de vida ficam fora das médias até a próxima coleta.", "posts")
    for grupo_tipo in ("pilar", "formato", "etapa"):
        for gp in g[grupo_tipo]:
            c = gp["stats"]["concentracao"]
            if c is not None and c > LIMITE_CONCENTRACAO and gp["stats"]["n_maduros"] >= N_AMOSTRA_MINIMA:
                add("baixa", f"Em '{gp['nome']}', um único post concentra {fmt_pct(c, 0)} do alcance: a média engana.", "grupos")

    if m["qualidade"]["sem_json"]:
        add("baixa", f"{plural(m['qualidade']['sem_json'], 'post')} do projeto sem classificação de pilar ou etapa.", "grupos")
    ref_antigas = [r for r in m["referencias"]["itens"] if r["antiga"]]
    if ref_antigas:
        add("baixa", f"{plural(len(ref_antigas), 'referência')} com mais de {DIAS_REF_ANTIGAS} dias: vale atualizar a análise.", "referencias")
    vencidos = [mv for mv in m["movimentos"] if mv["dias"] is not None and mv["dias"] < 0]
    if vencidos:
        add("baixa", f"{plural(len(vencidos), 'movimento')} da estratégia passou do prazo: vale decidir se foi concluído.", "metas")
    if m["estrategia"]["status"] == "rascunho":
        add("info", "A estratégia está em rascunho: as metas valem como sugestão até a pessoa aprovar.", "metas")

    ordem = {"alta": 0, "media": 1, "baixa": 2, "info": 3}
    alertas.sort(key=lambda a: ordem[a["nivel"]])
    return alertas


def construir_modelo(pasta: Path, raiz: Path, slug: str, estrategia: dict, hoje: date, fuso: timezone, janela_dias: int, agora: datetime) -> tuple[dict, list[str]]:
    ctx = Contexto(hoje, fuso)
    perfil = carregar_perfil(pasta, ctx)
    snaps = carregar_snapshots(pasta, ctx)
    publicados = carregar_publicados(pasta, ctx)
    projeto = carregar_posts_projeto(pasta, ctx)
    refs = carregar_referencias(pasta, ctx)

    seg = analisar_seguidores(perfil, hoje)
    serie = [(x["dia"], x["valor"]) for x in seg["serie"]]
    posts = unificar_posts(snaps, publicados, projeto, serie, ctx)

    datas_coleta = [d for d in (perfil["pontos"][-1]["dia"] if perfil["pontos"] else None, snaps["ultima_coleta"]) if d]
    primeiras = [perfil["pontos"][0]["dia"]] if perfil["pontos"] else []
    primeiras += [snaps["primeira_coleta"]] if snaps["primeira_coleta"] else []
    ultima_coleta = max(datas_coleta) if datas_coleta else None
    ultimas_pub = [p["pub_dia"] for p in posts if p["pub_dia"]]
    fim = max([d for d in [ultima_coleta] + ultimas_pub if d and d <= hoje], default=None)
    inicio_dados = min(primeiras + [p["pub_dia"] for p in posts if p["pub_dia"]], default=None)

    for p in posts:
        p["na_janela"] = bool(fim and p["pub_dia"] and fim - timedelta(days=janela_dias - 1) <= p["pub_dia"] <= fim)

    na_janela = [p for p in posts if p["na_janela"]]
    conta = estatisticas(na_janela)
    ritmo = analisar_ritmo(posts, fim, inicio_dados, estrategia, so_projeto=not snaps["posts"])

    ordem_pilares = [(p["id"], p["nome"]) for p in estrategia["pilares"]]
    g_pilar = montar_grupos(na_janela, ordem_pilares, lambda p: p["pilar"], conta, "Sem classificação")
    pesos = {p["id"]: p["peso"] for p in estrategia["pilares"]}
    descricoes = {p["id"]: p["descricao"] for p in estrategia["pilares"]}
    classif = [p for p in na_janela if p["pilar"]]
    for gp in g_pilar:
        gp["peso"] = pesos.get(gp["id"])
        gp["descricao"] = descricoes.get(gp["id"], "")
        n = sum(1 for k in gp["chaves"])
        gp["fatia_real"] = (n / len(classif)) if (classif and gp["id"] != SEM_CLASSIFICACAO) else None
        gp["n_classificados_total"] = len(classif)

    ordem_formatos = [(f, NOMES_FORMATO[f]) for f in FORMATOS]
    g_formato = montar_grupos(na_janela, ordem_formatos, lambda p: p["formato"], conta, "Formato não identificado")
    plano_f = (estrategia.get("ritmo") or {}).get("formatos") or {}
    for gf in g_formato:
        gf["plano_semana"] = plano_f.get(gf["id"])
        gf["real_semana"] = ritmo.get("por_formato_real", {}).get(gf["id"]) if ritmo.get("disponivel") else None

    ordem_etapas = [(e, NOMES_ETAPA[e]) for e in ETAPAS]
    g_etapa = montar_grupos(na_janela, ordem_etapas, lambda p: p["etapa"], conta, "Sem classificação")
    funil = analisar_funil(g_etapa, conta, estrategia)
    com_etapa = [p for p in na_janela if p["etapa"]]
    for ge in g_etapa:
        ge["plano"] = (estrategia.get("funil") or {}).get(ge["id"], "")
        ge["fatia_real"] = (len(ge["chaves"]) / len(com_etapa)) if (com_etapa and ge["id"] != SEM_CLASSIFICACAO) else None

    maduros = [p for p in na_janela if p["estado"] == "maduro"]

    def ranking(campo: str) -> dict:
        com = [p for p in maduros if p[campo] is not None]
        if len(maduros) < N_MIN_RANKING or len(com) < N_MIN_RANKING:
            return {"campo": campo, "disponivel": False, "n": len(com), "melhores": [], "piores": []}
        ordem = sorted(com, key=lambda p: p[campo], reverse=True)
        return {"campo": campo, "disponivel": True, "n": len(com), "melhores": [p["chave"] for p in ordem[:3]], "piores": [p["chave"] for p in ordem[-3:][::-1]]}

    kpis = calcular_kpis(posts, fim)
    metas = [avaliar_meta(mt, seg, ritmo, posts, fim, hoje) for mt in estrategia["metas"]]
    movimentos = montar_movimentos(estrategia["movimentos"], seg, ritmo, posts, fim, hoje)
    fontes = montar_fontes(perfil, snaps, publicados, refs, estrategia, hoje)
    idade = (hoje - ultima_coleta).days if ultima_coleta else None
    nome, arroba = nome_da_marca(pasta, slug)
    sem_json = len({p["post_id"] for p in posts if p["post_id"] and p["pilar"] is None and p["etapa"] is None and p["post_id"] not in projeto["indice"]})
    com_metrica_ausente = [p for p in maduros if p["salvamentos"] is None or p["alcance"] is None]

    modelo: dict = {
        "versao_modelo": VERSAO_MODELO,
        "marca": {"slug": slug, "nome": nome, "arroba": arroba, "exemplo": slug == "exemplo"},
        "gerado_em": agora.strftime("%Y-%m-%d %H:%M"),
        "hoje": hoje,
        "fuso": agora.astimezone(fuso).strftime("%z"),
        "janela_dias": janela_dias,
        "estrategia": {
            "status": estrategia["status"],
            "atualizado_em": estrategia["atualizado_em"],
            "objetivo": estrategia["objetivo"],
            "pilares": estrategia["pilares"],
            "ritmo": estrategia["ritmo"],
            "funil": estrategia["funil"],
            "movimentos": estrategia["movimentos"],
        },
        "dados": {
            "ultima_coleta": ultima_coleta,
            "idade_dias": idade,
            "desatualizado": bool(idade is not None and idade > DIAS_AVISO_DADOS),
            "limite_dias": DIAS_AVISO_DADOS,
            "fim_dados": fim,
            "sem_nenhuma_coleta": ultima_coleta is None,
            "fontes": fontes,
            "ultima_leitura": ultima_leitura(pasta),
        },
        "seguidores": seg,
        "kpis": kpis,
        "metas": metas,
        "movimentos": movimentos,
        "ritmo": ritmo,
        "grupos": {"conta": conta, "pilar": g_pilar, "formato": g_formato, "etapa": g_etapa},
        "funil": funil,
        "posts": posts,
        "ranking": {"alcance_rel": ranking("alcance_rel"), "interacao_valor": ranking("interacao_valor")},
        "referencias": montar_referencias(refs, conta, seg.get("atual") if seg["disponivel"] else None, ritmo, posts, hoje),
        "qualidade": {
            "avisos": ctx.avisos,
            "sem_json": sem_json,
            "maduros_com_lacuna": len(com_metrica_ausente),
            "n_maduros": len(maduros),
        },
    }
    modelo["alertas"] = gerar_alertas(modelo)
    return modelo, ctx.avisos
