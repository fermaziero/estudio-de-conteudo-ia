"""Monta o painel de resultados (HTML autocontido) de uma marca.

Uso, a partir da raiz do projeto:
    python -X utf8 skills/acompanhar-resultados/scripts/montar_painel.py --marca minha-marca
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _analise import (  # noqa: E402
    DIAS_AVISO_DADOS,
    HORAS_MATURIDADE,
    SEM_CLASSIFICACAO,
    construir_modelo,
    serializar,
    valor_indicador_texto,
)
from _comum import (  # noqa: E402
    ErroUso,
    caminho_curto,
    configurar_saida,
    criar_parser,
    fmt_data,
    fmt_dec,
    fmt_dias,
    fmt_int,
    fmt_pct,
    fmt_sinal,
    ler_data_arg,
    ler_fuso_arg,
    ler_json_arquivo,
    plural,
    raiz_do_projeto,
    resolver_marca,
)
from _painel_html import renderizar  # noqa: E402
from validar_estrategia import validar_estrategia  # noqa: E402

VERSAO = "1.0"

AJUDA = """\
montar_painel.py - gera o painel de resultados (um arquivo HTML) de uma marca.

Uso:
  python -X utf8 skills/acompanhar-resultados/scripts/montar_painel.py [opções]

Lê, dentro de marcas/<marca>/:
  estrategia.json                 metas, pilares, ritmo e funil
  metricas/perfil.csv             seguidores ao longo do tempo
  metricas/posts.csv              desempenho de cada post
  publicacao/publicados.csv       posts publicados por este projeto
  referencias/referencias.csv     perfis de referência
  conteudo/<lote>/posts/<id>.json pilar, formato e etapa de cada post do projeto
Escreve:
  metricas/painel.html            abre com duplo clique; funciona sem internet

O que faltar nos arquivos aparece como "não medido", nunca como zero.

Opções:
  --marca NOME       marca (pasta em marcas/). Se houver só uma marca além de
                     'exemplo', ela é usada sem perguntar. A marca fictícia 'exemplo'
                     só é usada com --marca exemplo.
  --simular          calcula e mostra o resumo, mas não grava o painel.html.
  --json             em vez do resumo, imprime todos os números calculados em JSON.
  --saida CAMINHO    grava o painel neste arquivo em vez de metricas/painel.html.
  --janela-dias N    quantos dias de posts entram na comparação por pilar, formato e
                     etapa (padrão: 56, ou seja, 8 semanas).
  --hoje AAAA-MM-DD  usa esta data como "hoje" (padrão: a data do computador).
  --fuso -03:00      fuso para contar o dia de cada post (padrão: -03:00, Brasília).
  --raiz PASTA       raiz do projeto (padrão: a pasta que contém skills/).
  --ajuda, -h        mostra esta ajuda.

Código de saída: 0 = painel montado; 1 = problema nos arquivos (ex.: estrategia.json
inválido ou ausente); 2 = erro de uso (marca não encontrada, argumento inválido).
"""


def formatar_meta(x: dict) -> str:
    ind = x["indicador"]
    atual = valor_indicador_texto(ind, x["atual"])
    alvo = valor_indicador_texto(ind, x["alvo"])
    linha = f"  - {x['descricao']}: {atual} de {alvo} até {fmt_data(x['prazo'])} -> {x['status_rotulo']}"
    partes = []
    if x["ritmo_necessario"] is not None:
        partes.append(f"precisa de {valor_indicador_texto(ind, x['ritmo_necessario'], sinal=True)}/semana")
    if x["ritmo_recente"] is not None:
        partes.append(f"nos últimos 28 dias: {valor_indicador_texto(ind, x['ritmo_recente'], sinal=True)}/semana")
    if x["nota"]:
        partes.append(x["nota"])
    return linha + (" (" + "; ".join(partes) + ")" if partes else "")


def linha_grupo_texto(g: dict) -> str:
    s = g["stats"]
    if s["n_maduros"] == 0:
        return f"  {g['nome']}: {plural(s['n_posts'], 'post')}, nenhum maduro (não medido)"
    amostra = f" [{s['amostra']}]" if s["amostra"] else ""
    return (
        f"  {g['nome']}: n={s['n_maduros']}{amostra}, alcance médio {fmt_int(s['alcance']['media']) if s['alcance']['n'] else 'não medido'}, "
        f"salv/alcance {fmt_pct(s['taxa_salvamentos']['valor'])}, compart/alcance {fmt_pct(s['taxa_compartilhamentos']['valor'])}, "
        f"coment/alcance {fmt_pct(s['taxa_comentarios']['valor'])}"
    )


def resumo_texto(m: dict, destino: str | None, notas: list[str]) -> str:
    L: list[str] = []
    if destino:
        L.append(f"Painel montado: {destino}")
    marca = m["marca"]
    L.append(
        f"Marca: {marca['nome']}{' (dados fictícios)' if marca['exemplo'] else ''} | "
        f"Estratégia: {m['estrategia']['status']} (atualizada em {m['estrategia']['atualizado_em']})"
    )
    d = m["dados"]
    c = m["grupos"]["conta"]
    if d["ultima_coleta"]:
        L.append(
            f"Dados: última coleta {d['ultima_coleta']} ({fmt_dias(d['idade_dias'])}"
            f"{'; ACIMA DO LIMITE DE ' + str(DIAS_AVISO_DADOS) + ' DIAS' if d['desatualizado'] else ''}) | "
            f"{plural(c['n_posts'], 'post')} na janela, {c['n_maduros']} maduros, {c['n_imaturos']} com menos de {HORAS_MATURIDADE} h"
        )
    else:
        L.append("Dados: nenhuma coleta de métricas encontrada.")
    seg = m["seguidores"]
    if seg["disponivel"]:
        j = seg["janela"]
        if j["saldo"] is not None:
            L.append(
                f"SEGUIDORES: {fmt_int(seg['atual'])} ({fmt_sinal(j['saldo'])} em {j['dias']} dias, cerca de {fmt_sinal(j['ritmo_semana'])} por semana; "
                "crescimento líquido: entrou menos saiu)"
            )
        else:
            L.append(f"SEGUIDORES: {fmt_int(seg['atual'])} (poucas coletas para medir o ritmo)")
    else:
        L.append("SEGUIDORES: não medido")
    r = m["ritmo"]
    if r.get("disponivel") and r["media_recente"] is not None:
        meta_txt = f", meta {fmt_dec(r['meta'], 1)} ({fmt_pct(r['razao'], 0)})" if r["meta"] else ""
        so_proj = " [só posts publicados pelo projeto: não há coleta de posts]" if r.get("so_projeto") else ""
        L.append(f"RITMO: {fmt_dec(r['media_recente'], 1)} posts por semana nas últimas {r['n_semanas_media']} semanas completas{meta_txt}{so_proj}")
    else:
        L.append("RITMO: não medido (menos de 2 semanas completas de posts)")
    k = m["kpis"]
    if k:
        L.append(
            f"ÚLTIMOS 28 DIAS (posts maduros): alcance médio {fmt_int(k['alcance_medio']['valor']) if k['alcance_medio']['n'] else 'não medido'} (n={k['alcance_medio']['n']}); "
            f"interação de valor {fmt_pct(k['interacao_valor']['valor']) if k['interacao_valor']['n'] else 'não medido'} (n={k['interacao_valor']['n']}); "
            f"alcance ÷ seguidores {fmt_pct(k['alcance_rel']['valor'], 0) if k['alcance_rel']['n'] else 'não medido'} (n={k['alcance_rel']['n']})"
        )
    L.append("METAS")
    L.extend(formatar_meta(x) for x in m["metas"]) if m["metas"] else L.append("  (nenhuma meta na estratégia)")
    if m["movimentos"]:
        L.append("MOVIMENTOS DA ESTRATÉGIA")
        for mv in m["movimentos"]:
            prazo = f"até {fmt_data(mv['ate'])}" + (" (vencido)" if mv["dias"] is not None and mv["dias"] < 0 else "")
            medida = f"{mv['indicador_nome']}: hoje {mv['atual_texto'] if mv['atual_texto'] is not None else 'não medido'}" if mv["mede_sozinho"] else f"{mv['indicador_nome']} (informado pela pessoa)"
            L.append(f"  - {mv['o_que']} | {prazo} | {medida}")
    if c["n_posts"]:
        L.append(f"DESEMPENHO POR GRUPO (janela de {m['janela_dias']} dias; taxas sobre o alcance)")
        L.append("Pilar")
        L.extend(linha_grupo_texto(g) for g in m["grupos"]["pilar"] if g["stats"]["n_posts"] or g["id"] != SEM_CLASSIFICACAO)
        L.append("Formato")
        L.extend(linha_grupo_texto(g) for g in m["grupos"]["formato"] if g["stats"]["n_posts"])
        L.append("Etapa do funil")
        L.extend(linha_grupo_texto(g) for g in m["grupos"]["etapa"] if g["stats"]["n_posts"] or g["id"] != SEM_CLASSIFICACAO)
        if m["funil"]["gargalo"]:
            et = next(e for e in m["funil"]["etapas"] if e["id"] == m["funil"]["gargalo"])
            L.append(f"  Hipótese de gargalo: {et['nome']} ({fmt_dec(et['indice'], 2)}x a média da conta em {et['metrica']})")
        for campo, tit in (("alcance_rel", "alcance ÷ seguidores"), ("interacao_valor", "interação de valor")):
            rk = m["ranking"][campo]
            por = {p["chave"]: p for p in m["posts"]}
            if rk["disponivel"]:
                fmt = (lambda p: fmt_pct(p[campo], 0)) if campo == "alcance_rel" else (lambda p: fmt_pct(p[campo]))
                L.append(f"Ranking por {tit}: melhores " + "; ".join(f"{por[k_]['titulo']} ({fmt(por[k_])})" for k_ in rk["melhores"]))
                L.append(f"{' ' * (len('Ranking por ' + tit) - 5)}piores " + "; ".join(f"{por[k_]['titulo']} ({fmt(por[k_])})" for k_ in rk["piores"]))
            else:
                L.append(f"Ranking por {tit}: sem posts maduros suficientes (hoje {rk['n']}; mínimo 6)")
    if m["alertas"]:
        L.append("PONTOS DE ATENÇÃO")
        L.extend(f"  [{a['nivel']}] {a['texto']}" for a in m["alertas"])
    if notas:
        L.append("AVISOS SOBRE OS DADOS")
        L.extend(f"  - {n}" for n in notas[:15])
        if len(notas) > 15:
            L.append(f"  ... e mais {len(notas) - 15}")
    return "\n".join(L)


def main(argv=None) -> int:
    configurar_saida()
    parser = criar_parser("montar_painel.py")
    parser.add_argument("--marca")
    parser.add_argument("--raiz")
    parser.add_argument("--hoje")
    parser.add_argument("--fuso")
    parser.add_argument("--saida")
    parser.add_argument("--janela-dias", dest="janela_dias", type=int, default=56)
    parser.add_argument("--simular", action="store_true")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.ajuda:
            print(AJUDA)
            return 0
        if args.janela_dias < 14 or args.janela_dias > 365:
            raise ErroUso("--janela-dias precisa estar entre 14 e 365.")
        raiz = raiz_do_projeto(args.raiz)
        hoje = ler_data_arg(args.hoje, "--hoje") or date.today()
        fuso = ler_fuso_arg(args.fuso)
        slug, pasta = resolver_marca(raiz, args.marca)
    except ErroUso as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2

    arq_estrategia = pasta / "estrategia.json"
    estrategia, problema = ler_json_arquivo(arq_estrategia)
    if problema:
        print(
            f"Erro: não consegui ler {caminho_curto(arq_estrategia, raiz)}: {problema}. "
            "Rode a skill configurar-marca para criar ou corrigir a estratégia.",
            file=sys.stderr,
        )
        return 1
    erros, _ = validar_estrategia(estrategia, hoje)
    if erros:
        print(f"Erro: {caminho_curto(arq_estrategia, raiz)} não segue o contrato. Corrija antes de montar o painel:", file=sys.stderr)
        for e in erros:
            print(f"  - {e}", file=sys.stderr)
        print("Dica: python -X utf8 skills/acompanhar-resultados/scripts/validar_estrategia.py --marca " + slug, file=sys.stderr)
        return 1

    agora = datetime.combine(hoje, datetime.now().time()) if args.hoje else datetime.now()
    modelo, notas = construir_modelo(pasta, raiz, slug, estrategia, hoje, fuso, args.janela_dias, agora)

    destino = None
    if not args.simular:
        caminho = Path(args.saida).expanduser() if args.saida else pasta / "metricas" / "painel.html"
        if caminho.suffix.lower() not in (".html", ".htm"):
            print("Erro: o arquivo de saída (--saida) precisa terminar em .html.", file=sys.stderr)
            return 2
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(renderizar(modelo, VERSAO), encoding="utf-8", newline="\n")
        except OSError as e:
            print(f"Erro: não consegui gravar {caminho}: {e.strerror or e}.", file=sys.stderr)
            return 1
        destino = caminho_curto(caminho.resolve(), raiz)

    if args.json:
        print(json.dumps(serializar(modelo), ensure_ascii=False, indent=2))
    else:
        print(resumo_texto(modelo, destino, notas))
        if args.simular:
            print("\n(modo --simular: nada foi gravado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
