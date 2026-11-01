"""Funções compartilhadas pelos scripts da skill gerar-artes.

Usa só a biblioteca padrão. Não é um comando: é importado pelos outros scripts da pasta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

PASTA_SCRIPTS = Path(__file__).resolve().parent
PASTA_SKILL = PASTA_SCRIPTS.parent
PASTA_FONTES = PASTA_SKILL / "fontes"
RAIZ = PASTA_SKILL.parent.parent

STATUS_ORDEM = ["rascunho", "em_revisao", "texto_aprovado", "arte_pronta", "aprovado", "agendado", "publicado"]
TAMANHOS = {"4:5": (1080, 1350), "1:1": (1080, 1080)}
LAYOUTS = ("capa", "texto", "lista", "cartoes", "imagem", "citacao", "cta")
POSICOES_LOGO = ("superior-esquerda", "superior-direita", "inferior-esquerda", "inferior-direita")
CORES_OBRIGATORIAS = ("fundo", "texto", "destaque", "suave", "fundo_escuro", "texto_sobre_escuro")
AUTOR = "gerar-artes"


class ErroUsuario(Exception):
    """Erro esperado: a mensagem em PT-BR explica o que a pessoa ou o agente deve fazer."""

    def __init__(self, mensagem: str, codigo: int = 1):
        super().__init__(mensagem)
        self.codigo = codigo


def saida_utf8() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def executar(principal) -> None:
    """Roda a função principal, mostra ERRO: em português e devolve o código de saída."""
    saida_utf8()
    try:
        codigo = principal()
    except ErroUsuario as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        codigo = erro.codigo
    except KeyboardInterrupt:
        print("Interrompido.", file=sys.stderr)
        codigo = 130
    except Exception:
        import traceback
        print("ERRO inesperado: falha do programa, não do seu conteúdo. Detalhes abaixo; se persistir, avise quem mantém o projeto.", file=sys.stderr)
        traceback.print_exc()
        codigo = 3
    sys.exit(codigo or 0)


def aviso(nivel: str, codigo: str, mensagem: str, slide: int | None = None) -> dict:
    """Aviso da arte. `atencao` impede marcar como pronta; `info` só informa."""
    return {"nivel": nivel, "codigo": codigo, "slide": slide, "mensagem": mensagem}


# ---------------------------------------------------------------- arquivos

def ler_json(caminho: Path):
    caminho = Path(caminho)
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ErroUsuario(f"Arquivo não encontrado: {caminho}")
    except json.JSONDecodeError as erro:
        raise ErroUsuario(f"JSON inválido em {caminho} (linha {erro.lineno}, coluna {erro.colno}): {erro.msg}")


def gravar_json(caminho: Path, dados) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f".{caminho.name}.{os.getpid()}.tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporario, caminho)


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def caminho_dentro(base: Path, relativo, rotulo: str = "O caminho") -> Path:
    """Resolve `relativo` a partir de `base` e recusa o que sair da pasta da marca."""
    if not isinstance(relativo, str) or not relativo.strip():
        raise ErroUsuario(f"{rotulo} está vazio ou não é um texto.")
    base_real = Path(base).resolve()
    alvo = (base_real / relativo).resolve()
    if alvo != base_real and base_real not in alvo.parents:
        raise ErroUsuario(
            f"{rotulo} '{relativo}' aponta para fora da pasta da marca. "
            "Copie o arquivo para dentro de marcas/<marca>/assets/ e aponte para lá."
        )
    return alvo


def hoje() -> str:
    return date.today().isoformat()


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slug(texto: str, limite: int = 40) -> str:
    base = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base[:limite].strip("-") or "ajuste"


# ---------------------------------------------------------------- linha de comando em português

class _AjudaPT(argparse.RawDescriptionHelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        return super()._format_usage(usage, actions, groups, prefix if prefix is not None else "uso: ")


def _traduzir_erro(mensagem: str) -> str:
    regras = [
        (r"the following arguments are required: (.*)", r"faltam argumentos obrigatórios: \g<1>"),
        (r"unrecognized arguments: (.*)", r"argumentos não reconhecidos: \g<1>"),
        (r"argument (.*): expected one argument", r"o argumento \g<1> precisa de um valor"),
        (r"argument (.*): invalid choice: (.*) \(choose from (.*)\)", r"o argumento \g<1> não aceita \g<2>; escolha entre: \g<3>"),
        (r"argument (.*): invalid int value: (.*)", r"o argumento \g<1> espera um número inteiro, não \g<2>"),
        (r"argument (.*): not allowed with argument (.*)", r"os argumentos \g<1> e \g<2> não podem ser usados juntos"),
        (r"argument (.*): (.*)", r"argumento \g<1>: \g<2>"),
    ]
    for padrao, troca in regras:
        if re.fullmatch(padrao, mensagem, re.S):
            return re.sub(padrao, troca, mensagem, flags=re.S)
    return mensagem


class ParserPT(argparse.ArgumentParser):
    """ArgumentParser com ajuda e erros em português."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", _AjudaPT)
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "argumentos"
        self._optionals.title = "opções"
        self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="mostra esta ajuda e sai")

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"ERRO: {_traduzir_erro(message)}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------- marca e lote

def adicionar_args_comuns(parser) -> None:
    parser.add_argument("--marca", help="pasta da marca dentro de marcas/ (minúsculas, números e hífen)")
    parser.add_argument("--lote", help="pasta do lote dentro de marcas/<marca>/conteudo/ (AAAA-MM-DD-nome)")
    parser.add_argument(
        "--raiz",
        help="avançado: pasta raiz do projeto; as marcas ficam em <raiz>/marcas (padrão: a pasta onde o projeto está instalado)",
    )
    parser.add_argument(
        "--pasta-marcas",
        help="avançado: pasta que contém as marcas, no lugar de <raiz>/marcas (também vale a variável ESTUDIO_MARCAS)",
    )


def pasta_das_marcas(valor: str | None = None, raiz: str | None = None) -> Path:
    if valor and raiz:
        raise ErroUsuario("Use só um dos dois: --raiz ou --pasta-marcas.")
    de_raiz = str(Path(raiz).expanduser() / "marcas") if raiz else None
    base = valor or de_raiz or os.environ.get("ESTUDIO_MARCAS") or str(RAIZ / "marcas")
    pasta = Path(base).expanduser().resolve()
    if not pasta.is_dir():
        raise ErroUsuario(f"A pasta das marcas não existe: {pasta}. Rode a skill configurar-marca primeiro.")
    return pasta


def resolver_marca(base: Path, slug_marca: str | None = None) -> tuple[str, Path]:
    existentes = sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
    if slug_marca:
        if not re.fullmatch(r"[a-z0-9-]+", slug_marca):
            raise ErroUsuario("O nome da marca deve ter só minúsculas, números e hífen.")
        if slug_marca not in existentes:
            lista = ", ".join(existentes) or "nenhuma"
            raise ErroUsuario(f"Marca '{slug_marca}' não encontrada em {base}. Marcas disponíveis: {lista}.")
        return slug_marca, base / slug_marca
    reais = [m for m in existentes if m != "exemplo"]
    if len(reais) == 1:
        return reais[0], base / reais[0]
    if not reais:
        raise ErroUsuario(
            "Nenhuma marca encontrada além do exemplo. Rode a skill configurar-marca "
            "ou use --marca exemplo para testar."
        )
    raise ErroUsuario("Há mais de uma marca. Escolha uma com --marca: " + ", ".join(reais) + ".")


def resolver_lote(pasta_marca: Path, lote: str | None = None) -> tuple[str, Path]:
    base = pasta_marca / "conteudo"
    lotes = sorted(p.name for p in base.iterdir() if p.is_dir() and (p / "posts").is_dir()) if base.is_dir() else []
    if lote:
        if lote not in lotes:
            lista = ", ".join(lotes) or "nenhum"
            raise ErroUsuario(f"Lote '{lote}' não encontrado em {base}. Lotes com posts: {lista}.")
        return lote, base / lote
    if len(lotes) == 1:
        return lotes[0], base / lotes[0]
    if not lotes:
        raise ErroUsuario(f"Não há lotes com posts em {base}. Rode antes as skills planejar-conteudo e criar-conteudo.")
    raise ErroUsuario("Há mais de um lote. Escolha um com --lote: " + ", ".join(lotes) + ".")


def contexto_padrao(args) -> tuple[Path, str, Path, str, Path]:
    """Devolve (pasta_marcas, slug_marca, pasta_marca, nome_lote, pasta_lote)."""
    base = pasta_das_marcas(args.pasta_marcas, getattr(args, "raiz", None))
    slug_marca, pasta_marca = resolver_marca(base, args.marca)
    nome_lote, pasta_lote = resolver_lote(pasta_marca, args.lote)
    return base, slug_marca, pasta_marca, nome_lote, pasta_lote


def listar_posts(pasta_lote: Path) -> dict:
    posts = {}
    for arquivo in sorted((pasta_lote / "posts").glob("*.json")):
        posts[arquivo.stem] = (arquivo, ler_json(arquivo))
    return posts


def selecionar_ids(posts: dict, pedidos: list[str] | None) -> list[str]:
    if not pedidos:
        return list(posts)
    ids = []
    for pedido in pedidos:
        for parte in str(pedido).split(","):
            parte = parte.strip()
            if not parte:
                continue
            if parte not in posts:
                raise ErroUsuario(f"Post '{parte}' não existe neste lote. Posts: {', '.join(posts) or 'nenhum'}.")
            if parte not in ids:
                ids.append(parte)
    return ids


# ---------------------------------------------------------------- cores

def cor_rgb(valor) -> tuple[int, int, int]:
    texto = str(valor).strip().lstrip("#")
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", texto):
        raise ValueError(valor)
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(v) for v in rgb)


def misturar(a, b, t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))  # type: ignore[return-value]


def luminancia(rgb) -> float:
    def canal(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def contraste(a, b) -> float:
    la, lb = luminancia(a), luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)


# ---------------------------------------------------------------- visual.json

def carregar_visual(pasta_marca: Path) -> dict:
    """Lê e valida o visual.json e devolve a configuração pronta para o gerador."""
    caminho = pasta_marca / "visual.json"
    if not caminho.is_file():
        raise ErroUsuario(f"Falta o arquivo {caminho}. Rode antes a skill configurar-marca.")
    v = ler_json(caminho)
    if not isinstance(v, dict):
        raise ErroUsuario("visual.json deve ser um objeto JSON.")
    if v.get("versao_esquema", 1) != 1:
        raise ErroUsuario(f"visual.json usa versao_esquema {v.get('versao_esquema')}, que esta skill não conhece (esperado: 1).")

    avisos: list[dict] = []
    brutas = v.get("cores")
    if not isinstance(brutas, dict):
        raise ErroUsuario("visual.json: falta o bloco 'cores'.")
    cores = {}
    for chave in CORES_OBRIGATORIAS:
        if chave not in brutas:
            raise ErroUsuario(f"visual.json: falta cores.{chave}.")
        try:
            cores[chave] = cor_rgb(brutas[chave])
        except ValueError:
            raise ErroUsuario(f"visual.json: cores.{chave} inválida ({brutas[chave]!r}). Use o formato #RRGGBB.")

    proporcao = v.get("proporcao_padrao") or "4:5"
    if proporcao not in TAMANHOS:
        raise ErroUsuario(f"visual.json: proporcao_padrao deve ser '4:5' ou '1:1' (veio {proporcao!r}).")

    def caminho_fonte(chave: str):
        relativo = (v.get("fontes") or {}).get(chave)
        if not relativo:
            return None
        alvo = caminho_dentro(pasta_marca, relativo, f"visual.json: fontes.{chave}")
        if not alvo.is_file():
            raise ErroUsuario(
                f"visual.json: a fonte '{relativo}' não existe. Copie o arquivo para lá "
                "ou troque o valor por null para usar a fonte livre que acompanha a skill."
            )
        return alvo

    fonte_titulo, fonte_texto = caminho_fonte("titulo"), caminho_fonte("texto")

    logo_cfg = None
    logo = v.get("logo")
    if isinstance(logo, dict):
        posicao = logo.get("posicao") or "superior-esquerda"
        if posicao not in POSICOES_LOGO:
            raise ErroUsuario(f"visual.json: logo.posicao deve ser uma destas: {', '.join(POSICOES_LOGO)}.")
        try:
            largura = int(logo.get("largura_px") or 140)
        except (TypeError, ValueError):
            raise ErroUsuario("visual.json: logo.largura_px deve ser um número inteiro.")
        if not 40 <= largura <= 400:
            avisos.append(aviso("info", "logo_largura", f"logo.largura_px={largura} fora de 40–400; usando {min(max(largura, 40), 400)}."))
            largura = min(max(largura, 40), 400)
        arquivos = {}
        for tema, chave in (("claro", "fundo_claro"), ("escuro", "fundo_escuro")):
            relativo = logo.get(chave)
            if not relativo:
                continue
            alvo = caminho_dentro(pasta_marca, relativo, f"visual.json: logo.{chave}")
            if alvo.is_file():
                arquivos[tema] = alvo
            else:
                avisos.append(aviso("atencao", "logo_ausente", f"O arquivo do logo para {chave.replace('_', ' ')} ({relativo}) não existe; a arte sai sem essa versão do logo."))
        if arquivos:
            logo_cfg = {"arquivos": arquivos, "posicao": posicao, "largura_px": largura}
        else:
            avisos.append(aviso("atencao", "logo_ausente", "O visual.json pede um logo, mas nenhum arquivo foi encontrado; as artes saem sem logo."))
    else:
        avisos.append(aviso("info", "sem_logo", "visual.json sem logo: as artes saem sem logo."))

    avatar = None
    if v.get("avatar"):
        alvo = caminho_dentro(pasta_marca, v["avatar"], "visual.json: avatar")
        if alvo.is_file():
            avatar = alvo
        else:
            avisos.append(aviso("info", "avatar_ausente", f"O avatar {v['avatar']} não existe; o último slide sai sem foto."))

    tipografia = {"titulo": (44, 56), "apoio": (24, 30)}
    extra = v.get("tipografia")
    if isinstance(extra, dict):
        for chave in ("titulo", "apoio"):
            par = extra.get(chave)
            if par is None:
                continue
            try:
                minimo, maximo = int(par[0]), int(par[1])
            except (TypeError, ValueError, IndexError, KeyError):
                raise ErroUsuario(f"visual.json: tipografia.{chave} deve ser [menor, maior], em pixels. Ex.: [44, 56].")
            if not 20 <= minimo <= maximo <= 110:
                raise ErroUsuario(f"visual.json: tipografia.{chave} deve estar entre 20 e 110 px, com menor <= maior.")
            tipografia[chave] = (minimo, maximo)

    return {
        "nome_exibicao": str(v.get("nome_exibicao") or "").strip(),
        "arroba": str(v.get("arroba") or "").strip(),
        "proporcao_padrao": proporcao,
        "cores": cores,
        "fonte_titulo": fonte_titulo,
        "fonte_texto": fonte_texto,
        "logo": logo_cfg,
        "avatar": avatar,
        "numeracao": bool(v.get("numeracao", False)),
        "rodape": bool(v.get("rodape", False)),
        "tipografia": tipografia,
        "avisos": avisos,
    }


def proporcao_do_post(post: dict, cfg: dict) -> str:
    proporcao = post.get("proporcao") or cfg["proporcao_padrao"]
    if proporcao not in TAMANHOS:
        raise ErroUsuario(f"Post '{post.get('id')}': proporcao deve ser '4:5' ou '1:1' (veio {proporcao!r}).")
    return proporcao


# ---------------------------------------------------------------- posts

def pode_gerar(status: str, formato: str) -> tuple[bool, str]:
    """Diz se um post com este status pode ter artes geradas."""
    if formato == "reel":
        return False, "reel é só roteiro; não tem artes"
    if status == "publicado":
        return False, "já foi publicado; crie um novo post em vez de alterar a arte"
    if status in ("rascunho", "em_revisao"):
        return False, "o texto ainda não foi aprovado pela pessoa (status " + status + ")"
    return True, ""


def invalidar_aprovacao(post: dict) -> bool:
    """Post aprovado ou agendado cujas artes mudaram: volta para arte_pronta, sem aprovação nem agendamento (como no publicador)."""
    if post.get("status") not in ("aprovado", "agendado"):
        return False
    aprovacao = post.get("aprovacao")
    antigo = str(aprovacao.get("hash", "")) if isinstance(aprovacao, dict) else ""
    agendado = post.get("agendado_para")
    post["status"] = "arte_pronta"
    post["aprovacao"] = None
    post["agendado_para"] = None
    evento = f"aprovação invalidada: as artes mudaram depois do ok da pessoa (hash antigo {antigo[:12]})"
    if agendado:
        evento += f"; o agendamento para {agendado} foi cancelado"
    registrar_historico(post, evento + "; o post voltou para arte_pronta e precisa de nova aprovação")
    return True


def registrar_historico(post: dict, evento: str) -> None:
    post.setdefault("historico", [])
    if not isinstance(post["historico"], list):
        post["historico"] = []
    post["historico"].append({"data": agora_iso(), "evento": evento, "por": AUTOR})


# ---------------------------------------------------------------- conferência das artes

def assinatura_slide(slide: dict, proporcao: str) -> str:
    """Impressão digital do que muda o desenho do slide (texto, itens, layout e proporção)."""
    base = {
        "layout": slide.get("layout"), "titulo": slide.get("titulo") or "", "texto": slide.get("texto") or "",
        "itens": [str(i) for i in (slide.get("itens") or [])], "proporcao": proporcao,
    }
    return hashlib.sha256(json.dumps(base, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def assinatura_visual(pasta_marca: Path) -> str:
    """Impressão digital do visual da marca: o visual.json (sem depender da formatação) e os arquivos que ele usa."""
    caminho = pasta_marca / "visual.json"
    if not caminho.is_file():
        return ""
    h = hashlib.sha256()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return ""
    h.update(json.dumps(dados, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if isinstance(dados, dict):
        logo = dados.get("logo") if isinstance(dados.get("logo"), dict) else {}
        fontes = dados.get("fontes") if isinstance(dados.get("fontes"), dict) else {}
        for relativo in (fontes.get("titulo"), fontes.get("texto"), logo.get("fundo_claro"), logo.get("fundo_escuro"), dados.get("avatar")):
            if isinstance(relativo, str) and relativo:
                try:
                    alvo = caminho_dentro(pasta_marca, relativo)
                except ErroUsuario:
                    continue
                if alvo.is_file():
                    h.update(relativo.encode("utf-8"))
                    h.update(sha256_arquivo(alvo).encode("ascii"))
    return h.hexdigest()


def verificar_artes(pasta_marca: Path, pasta_lote: Path, pid: str, post: dict) -> dict:
    """Compara as artes que estão no disco com o post e com o manifesto.

    Devolve {"manifesto": bool, "gerais": [...], "slides": {n: [...]}, "atencao": [avisos do manifesto]}.
    Qualquer item em `gerais` ou `slides` quer dizer que a arte não bate com o texto atual do post.
    """
    pasta = pasta_lote / "artes" / pid
    resultado: dict = {"manifesto": False, "gerais": [], "slides": {}, "atencao": []}
    arquivo = pasta / "manifesto.json"
    slides = [s for s in (post.get("slides") or []) if isinstance(s, dict)]
    if not arquivo.is_file():
        resultado["gerais"].append("não há manifesto.json: as artes ainda não foram geradas (ou foram feitas por outro meio).")
        return resultado
    try:
        manifesto = ler_json(arquivo)
    except ErroUsuario as erro:
        resultado["gerais"].append(str(erro))
        return resultado
    resultado["manifesto"] = True
    proporcao = manifesto.get("proporcao") or post.get("proporcao")
    if post.get("proporcao") and manifesto.get("proporcao") and post["proporcao"] != manifesto["proporcao"]:
        resultado["gerais"].append(f"a proporção do post ({post['proporcao']}) mudou depois da arte ({manifesto['proporcao']}).")
    registrados = {item.get("n"): item for item in manifesto.get("slides", []) if isinstance(item, dict)}
    visual_atual = assinatura_visual(pasta_marca)
    for slide in slides:
        n = slide.get("n")
        problemas: list[str] = []
        png = pasta / f"{int(n):02d}.png" if isinstance(n, int) else None
        item = registrados.get(n)
        if png is None or not png.is_file():
            problemas.append("falta a arte deste slide.")
        elif item is None:
            problemas.append("a arte não está no manifesto.")
        else:
            if item.get("sha256") != sha256_arquivo(png):
                problemas.append("o arquivo da arte mudou depois do manifesto.")
            if item.get("conteudo_sha256") != assinatura_slide(slide, str(proporcao)):
                problemas.append("o texto, os itens ou o layout do slide mudaram depois da arte.")
            if item.get("visual_sha256") != visual_atual:
                problemas.append("o visual da marca (visual.json, logo, fonte ou avatar) mudou depois desta arte: gere de novo com --refazer.")
            for imagem in item.get("imagens") or []:
                origem = imagem.get("arquivo")
                alvo = (pasta_marca / origem) if origem else None
                if alvo is None or not alvo.is_file():
                    problemas.append(f"a imagem usada ({origem}) não está mais no lugar.")
                elif imagem.get("sha256") != sha256_arquivo(alvo):
                    problemas.append(f"a imagem {origem} foi trocada depois da arte.")
        if problemas:
            resultado["slides"][n] = problemas
    numeros = {s.get("n") for s in slides}
    sobras = sorted(p.name for p in pasta.glob("[0-9][0-9].png") if int(p.stem) not in numeros)
    if sobras:
        resultado["gerais"].append("há artes de slides que não existem mais no post: " + ", ".join(sobras) + ".")
    resultado["atencao"] = [a for a in manifesto.get("avisos", []) if a.get("nivel") == "atencao"]
    return resultado
