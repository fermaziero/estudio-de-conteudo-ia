#!/usr/bin/env python3
"""Valida os posts de um lote contra o contrato do projeto (docs/arquitetura.md).

Rode sempre a partir da raiz do projeto:

    python -X utf8 skills/criar-conteudo/scripts/validar_posts.py --marca <marca> --lote <lote>
    python -X utf8 skills/criar-conteudo/scripts/validar_posts.py --marca <marca> --post <id>

No macOS e no Linux, use python3.

Código de saída: 0 = sem erros; 1 = há erros nos posts; 2 = problema de uso
(marca, lote ou post não encontrados). Este script só lê arquivos: não altera nada.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

RAIZ_PADRAO = Path(__file__).resolve().parents[3]

FORMATOS = ("carrossel", "post_unico", "reel")
PROPORCOES = ("4:5", "1:1")
ETAPAS = ("atracao", "relacionamento", "conversao")
STATUS = ("rascunho", "em_revisao", "texto_aprovado", "arte_pronta", "aprovado", "agendado", "publicado", "erro")
PAPEIS = ("capa", "conteudo", "cta")
LAYOUTS = ("capa", "texto", "lista", "cartoes", "imagem", "citacao", "cta")
TIPOS_IMAGEM = ("foto", "gerada")
VEREDITOS = ("aprovar", "ajustar", "refazer")

CAMPOS_POST = (
    "versao_esquema", "id", "lote", "titulo_interno", "pilar", "formato", "proporcao", "etapa_funil",
    "objetivo", "de_onde_vem", "chamada", "slides", "roteiro", "legenda", "hashtags", "fontes",
    "fontes_legenda_internas", "confirmar", "revisao", "status", "historico", "aprovacao",
    "agendado_para", "publicacao",
)
CAMPOS_PODEM_SER_NULOS = ("roteiro", "revisao", "aprovacao", "agendado_para", "publicacao")
CAMPOS_SLIDE = ("n", "papel", "layout", "titulo", "texto", "itens", "imagem", "texto_alternativo", "fonte_interna")

LIMITE_LEGENDA = 2200
MAX_HASHTAGS = 5
MAX_PALAVRAS_CAPA = 12
MAX_PALAVRAS_TITULO_CTA = 10
MAX_PALAVRAS_APOIO_CTA = 15
MAX_PALAVRAS_SLIDE = 60
MAX_PRIMEIRA_LINHA = 125

RE_ID = re.compile(r"^[a-z0-9-]{3,80}$")
RE_LOTE = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_SLUG_MARCA = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_ROTULO_FONTE = re.compile(r"\bfontes?\s*:", re.IGNORECASE)
RE_HASHTAG = re.compile(r"(?<![\w&])#(\w+)")
RE_URL_NO_TEXTO = re.compile(r"https?://", re.IGNORECASE)
RE_MODELO_NAO_PREENCHIDO = re.compile(r"<[^<>\n]{1,120}>")
RE_COMENTE_PALAVRA = re.compile(r"(?i:comente)\s+[\"“'‘]?[A-ZÀ-ÖØ-Ý0-9]{3,}\b")
RE_PROMPT_SEM_TEXTO = re.compile(r"\bsem\s+(?:qualquer\s+|nenhum\s+)?(?:texto|letras|palavras|escrita)", re.IGNORECASE)
RE_TEMPO_ROTEIRO = re.compile(r"^\d+\s*[-–]\s*\d+\s*s$")
RE_DADO = re.compile(
    r"\d+(?:[.,]\d+)?\s*%"
    r"|R\$\s*\d"
    r"|\b(?:19|20)\d{2}\b"
    r"|\b\d{1,3}(?:\.\d{3})+\b"
    r"|\b\d+\s*(?:mil|milhões|milhão|bilhões|bilhão)\b"
    r"|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"
    r"|\bdia\s+\d{1,2}\b",
    re.IGNORECASE,
)
SENSIVEIS = (
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("CNPJ", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
    ("e-mail", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("telefone", re.compile(r"(?:\+55\s?)?\(\d{2}\)\s?9?\d{4}-?\d{4}")),
)

LAYOUT_DO_PAPEL = {"capa": "capa", "cta": "cta"}


class ErroDeUso(Exception):
    """Problema com os argumentos ou com as pastas (código de saída 2)."""


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------

@dataclass
class Msg:
    nivel: str  # "erro" ou "aviso"
    campo: str
    texto: str


class Coletor:
    def __init__(self) -> None:
        self.msgs: list[Msg] = []
        self.pendencias: list[str] = []

    def erro(self, campo: str, texto: str) -> None:
        self.msgs.append(Msg("erro", campo, texto))

    def aviso(self, campo: str, texto: str) -> None:
        self.msgs.append(Msg("aviso", campo, texto))

    @property
    def erros(self) -> list[Msg]:
        return [m for m in self.msgs if m.nivel == "erro"]

    @property
    def avisos(self) -> list[Msg]:
        return [m for m in self.msgs if m.nivel == "aviso"]


@dataclass
class ResultadoPost:
    arquivo: Path
    rotulo: str
    coletor: Coletor
    dados: dict | None = None


@dataclass
class ResultadoLote:
    marca: str
    lote: str
    pasta_lote: Path
    posts: list[ResultadoPost] = field(default_factory=list)
    gerais: Coletor = field(default_factory=Coletor)

    @property
    def total_erros(self) -> int:
        return len(self.gerais.erros) + sum(len(p.coletor.erros) for p in self.posts)

    @property
    def total_avisos(self) -> int:
        return len(self.gerais.avisos) + sum(len(p.coletor.avisos) for p in self.posts)

    @property
    def total_pendencias(self) -> int:
        return sum(len(p.coletor.pendencias) for p in self.posts)


@dataclass
class Contexto:
    raiz: Path
    marca: str
    pasta_marca: Path
    lote: str
    pasta_lote: Path
    pilares: list[str] | None
    ids: dict[str, list[Path]]
    hoje: date


# ---------------------------------------------------------------------------
# Pastas, marca e lote
# ---------------------------------------------------------------------------

def listar_marcas(raiz: Path) -> list[str]:
    base = raiz / "marcas"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def resolver_marca(raiz: Path, marca: str | None) -> tuple[str, Path]:
    base = raiz / "marcas"
    if marca:
        if not RE_SLUG_MARCA.match(marca):
            raise ErroDeUso(f"Nome de marca inválido: {marca!r}. Use o slug da pasta (minúsculas, números e hífen).")
        pasta = base / marca
        if not pasta.is_dir():
            existentes = ", ".join(listar_marcas(raiz)) or "nenhuma"
            raise ErroDeUso(f"Marca '{marca}' não encontrada em marcas/. Marcas existentes: {existentes}.")
        return marca, pasta
    reais = [m for m in listar_marcas(raiz) if m != "exemplo"]
    if len(reais) == 1:
        return reais[0], base / reais[0]
    if len(reais) > 1:
        raise ErroDeUso("Há mais de uma marca. Informe qual com --marca <slug>. Opções: " + ", ".join(reais) + ".")
    raise ErroDeUso(
        "Nenhuma marca encontrada além de 'exemplo'. Para testar o fluxo, use --marca exemplo. "
        "Para criar a sua, use a skill configurar-marca."
    )


def listar_lotes(pasta_marca: Path) -> list[str]:
    base = pasta_marca / "conteudo"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))


def resolver_lote(pasta_marca: Path, lote: str) -> tuple[str, Path]:
    nome = Path(lote.replace("\\", "/")).name
    pasta = pasta_marca / "conteudo" / nome
    if not pasta.is_dir():
        existentes = ", ".join(listar_lotes(pasta_marca)) or "nenhum"
        raise ErroDeUso(f"Lote '{nome}' não encontrado em marcas/{pasta_marca.name}/conteudo/. Lotes existentes: {existentes}.")
    return nome, pasta


def arquivos_de_posts(pasta_lote: Path) -> list[Path]:
    pasta = pasta_lote / "posts"
    if not pasta.is_dir():
        return []
    return sorted(pasta.glob("*.json"), key=chave_natural)


def chave_natural(caminho: Path) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", caminho.name)]


_ERROS_JSON = (
    ("Expecting property name enclosed in double quotes", "esperava um nome entre aspas duplas (vírgula sobrando no fim de uma lista?)"),
    ("Expecting ',' delimiter", "faltou uma vírgula (ou uma aspa de fechamento)"),
    ("Expecting ':' delimiter", "faltaram os dois-pontos depois do nome"),
    ("Expecting value", "faltou um valor"),
    ("Extra data", "sobrou texto depois do fim do JSON"),
    ("Unterminated string", "texto sem aspas de fechamento"),
    ("Invalid control character", "quebra de linha ou tabulação dentro de um texto (use \\n)"),
    ("Invalid \\escape", "barra invertida inválida dentro de um texto"),
)


def ler_json(caminho: Path):
    """Devolve (dados, mensagem_de_erro)."""
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        detalhe = next((destino for origem, destino in _ERROS_JSON if e.msg.startswith(origem)), e.msg)
        return None, f"JSON inválido (linha {e.lineno}, coluna {e.colno}): {detalhe}"
    except UnicodeDecodeError:
        return None, "o arquivo não está em UTF-8"
    except OSError as e:
        return None, f"não consegui ler o arquivo: {e.strerror or e}"


def carregar_pilares(pasta_marca: Path) -> tuple[list[str] | None, str | None]:
    arquivo = pasta_marca / "estrategia.json"
    if not arquivo.is_file():
        return None, "estrategia.json não encontrado na pasta da marca; sem ele não dá para conferir o pilar. Use a skill configurar-marca."
    dados, problema = ler_json(arquivo)
    if problema:
        return None, f"estrategia.json: {problema}"
    pilares = dados.get("pilares") if isinstance(dados, dict) else None
    if not isinstance(pilares, list):
        return None, "estrategia.json: falta a lista `pilares`."
    ids = [p.get("id") for p in pilares if isinstance(p, dict) and isinstance(p.get("id"), str)]
    if not ids:
        return None, "estrategia.json: a lista `pilares` não tem nenhum pilar com `id`."
    return ids, None


def indexar_ids(pasta_marca: Path) -> dict[str, list[Path]]:
    """Mapeia cada id (nome do arquivo e campo `id`) para os arquivos que o usam, em todos os lotes da marca."""
    indice: dict[str, list[Path]] = {}
    for nome_lote in listar_lotes(pasta_marca):
        for arq in arquivos_de_posts(pasta_marca / "conteudo" / nome_lote):
            chaves = {arq.stem}
            dados, _ = ler_json(arq)
            if isinstance(dados, dict) and isinstance(dados.get("id"), str):
                chaves.add(dados["id"])
            for chave in chaves:
                indice.setdefault(chave, [])
                if arq not in indice[chave]:
                    indice[chave].append(arq)
    return indice


# ---------------------------------------------------------------------------
# Auxiliares de texto
# ---------------------------------------------------------------------------

def palavras(texto: str) -> int:
    return sum(1 for t in texto.split() if re.search(r"\w", t))


SIMBOLOS_COM_GLIFO = {"→"}
CARACTERES_INVISIVEIS = {"️", "︎", "‍"}


def simbolos_sem_glifo(texto: str) -> list[str]:
    """Emojis e símbolos (setas, estrelas, ✓…) que a fonte que acompanha a skill gerar-artes não desenha.

    A fonte cobre letras latinas com acento, pontuação, aspas, travessões, •, →, €, ®, ™, © e ½. O resto, de U+2190 em diante,
    sai como quadradinho na arte."""
    achados: list[str] = []
    for ch in texto:
        if ord(ch) >= 0x2190 and ch not in SIMBOLOS_COM_GLIFO and ch not in CARACTERES_INVISIVEIS and ch not in achados:
            achados.append(ch)
    return achados


def tamanho_instagram(texto: str) -> int:
    """Conta como o Instagram, em unidades UTF-16 (um emoji vale 2)."""
    return len(texto.encode("utf-16-le", errors="surrogatepass")) // 2


def legenda_com_hashtags(legenda: str, hashtags: list) -> str:
    """Monta a legenda como o publicador: o texto, uma linha em branco e as hashtags da lista que ainda não estão nele."""
    existentes = {t.casefold() for t in RE_HASHTAG.findall(legenda)}
    novas = []
    for h in hashtags:
        if not isinstance(h, str):
            continue
        tag = re.sub(r"\s+", "", h).lstrip("#")
        if tag and tag.casefold() not in existentes:
            novas.append("#" + tag)
            existentes.add(tag.casefold())
    return legenda.strip() + ("\n\n" + " ".join(novas) if novas else "")


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto).casefold()
    t = re.sub(r"\s+", " ", t).strip()
    return t.rstrip(" .!?…:;,-–—\"'”’)")


def eh_inteiro(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def eh_data(v) -> bool:
    if not isinstance(v, str) or not RE_DATA.match(v):
        return False
    try:
        date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _data_hora(v):
    """Interpreta data e hora ISO 8601 (aceita 'Z' no fim). Devolve o datetime ou None."""
    if not isinstance(v, str) or "T" not in v:
        return None
    texto = v.strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def data_hora_com_fuso(v) -> bool:
    dt = _data_hora(v)
    return dt is not None and dt.tzinfo is not None


def eh_data_ou_hora(v) -> bool:
    """Registros de histórico aceitam AAAA-MM-DD ou data e hora ISO 8601 (as skills de publicação gravam com hora)."""
    return eh_data(v) or _data_hora(v) is not None


def url_valida(v) -> bool:
    if not isinstance(v, str):
        return False
    p = urlparse(v.strip())
    return p.scheme in ("http", "https") and bool(p.netloc) and " " not in v.strip()


def caminho_relativo_seguro(s: str) -> bool:
    if not s or "\\" in s or s.startswith("/") or re.match(r"^[A-Za-z]:", s):
        return False
    return ".." not in s.split("/")


def percorrer_textos(obj, caminho=""):
    """Gera (caminho, texto) para toda string do objeto."""
    if isinstance(obj, str):
        yield caminho, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from percorrer_textos(v, f"{caminho}.{k}" if caminho else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from percorrer_textos(v, f"{caminho}[{i}]")


def textos_do_slide(slide: dict) -> list[str]:
    partes = []
    for chave in ("titulo", "texto"):
        if isinstance(slide.get(chave), str):
            partes.append(slide[chave])
    if isinstance(slide.get("itens"), list):
        partes.extend(i for i in slide["itens"] if isinstance(i, str))
    return partes


# ---------------------------------------------------------------------------
# Validação de um post
# ---------------------------------------------------------------------------

def texto_obrigatorio(c: Coletor, campo: str, valor) -> bool:
    if not isinstance(valor, str):
        c.erro(campo, "deve ser um texto")
        return False
    if not valor.strip():
        c.erro(campo, "está vazio")
        return False
    return True


def opcao_valida(c: Coletor, campo: str, valor, opcoes: tuple) -> bool:
    if not isinstance(valor, str) or valor not in opcoes:
        c.erro(campo, f"valor inválido ({valor!r}); use um destes: {', '.join(opcoes)}")
        return False
    return True


def lista_de_textos(c: Coletor, campo: str, valor) -> bool:
    if not isinstance(valor, list):
        c.erro(campo, "deve ser uma lista (use [] quando não houver itens)")
        return False
    ok = True
    for i, item in enumerate(valor):
        if not isinstance(item, str) or not item.strip():
            c.erro(f"{campo}[{i}]", "deve ser um texto não vazio")
            ok = False
    return ok


def validar_post(d, arquivo: Path, ctx: Contexto) -> Coletor:
    c = Coletor()
    if not isinstance(d, dict):
        c.erro("(arquivo)", "o conteúdo deve ser um objeto JSON, entre chaves { }")
        return c

    for campo in CAMPOS_POST:
        if campo not in d:
            extra = " (use null quando não se aplica)" if campo in CAMPOS_PODEM_SER_NULOS else ""
            c.erro(campo, "campo ausente" + extra)
    for campo in d:
        if campo not in CAMPOS_POST:
            c.aviso(campo, "campo desconhecido; confira se não é erro de digitação (as outras skills ignoram este campo)")

    for caminho, texto in percorrer_textos(d):
        trecho = RE_MODELO_NAO_PREENCHIDO.search(texto)
        if trecho:
            c.erro(caminho, f"ainda tem um trecho do modelo sem preencher: {trecho.group(0)!r}")

    if "versao_esquema" in d and not (eh_inteiro(d["versao_esquema"]) and d["versao_esquema"] == 1):
        c.erro("versao_esquema", "deve ser o número 1")

    _validar_identificacao(c, d, arquivo, ctx)

    for campo in ("titulo_interno", "objetivo", "de_onde_vem", "chamada"):
        if campo in d:
            texto_obrigatorio(c, campo, d[campo])

    if "pilar" in d:
        if not texto_obrigatorio(c, "pilar", d["pilar"]):
            pass
        elif ctx.pilares is not None and d["pilar"] not in ctx.pilares:
            c.erro("pilar", f"o pilar {d['pilar']!r} não existe em estrategia.json. Pilares da marca: {', '.join(ctx.pilares)}")

    if "formato" in d:
        opcao_valida(c, "formato", d["formato"], FORMATOS)
    if "proporcao" in d:
        opcao_valida(c, "proporcao", d["proporcao"], PROPORCOES)
    if "etapa_funil" in d:
        opcao_valida(c, "etapa_funil", d["etapa_funil"], ETAPAS)

    if "slides" in d:
        _validar_slides(c, d, ctx)
    if "roteiro" in d:
        _validar_roteiro(c, d)
    if "legenda" in d:
        _validar_legenda(c, d)
    if "hashtags" in d:
        _validar_hashtags(c, d)
    if "fontes" in d:
        _validar_fontes(c, d, ctx)
    if "fontes_legenda_internas" in d:
        lista_de_textos(c, "fontes_legenda_internas", d["fontes_legenda_internas"])
    if "confirmar" in d:
        _validar_confirmar(c, d)

    _validar_dados_sensiveis(c, d)
    _validar_ciclo(c, d)
    return c


def _validar_identificacao(c: Coletor, d: dict, arquivo: Path, ctx: Contexto) -> None:
    if "id" in d:
        i = d["id"]
        if not isinstance(i, str) or not RE_ID.match(i):
            c.erro("id", "deve ter de 3 a 80 caracteres: só letras minúsculas sem acento, números e hífen")
        else:
            if i != arquivo.stem:
                c.erro("id", f"o id {i!r} deve ser igual ao nome do arquivo ({arquivo.stem}.json)")
            for chave in {i, arquivo.stem}:
                outros = [p for p in ctx.ids.get(chave, []) if p.resolve() != arquivo.resolve()]
                if outros:
                    onde = ", ".join(mostrar_caminho(p, ctx.raiz) for p in outros)
                    c.erro("id", f"o id {chave!r} também é usado em: {onde}. O id é único dentro da marca.")
                    break
    if "lote" in d:
        if not isinstance(d["lote"], str):
            c.erro("lote", "deve ser um texto")
        elif d["lote"] != ctx.lote:
            c.erro("lote", f"é {d['lote']!r}, mas o arquivo está na pasta do lote {ctx.lote!r}")


def mostrar_caminho(caminho: Path, raiz: Path) -> str:
    try:
        return caminho.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return str(caminho)


def _validar_slides(c: Coletor, d: dict, ctx: Contexto) -> None:
    slides = d["slides"]
    formato = d.get("formato")
    if not isinstance(slides, list):
        c.erro("slides", "deve ser uma lista de slides")
        return
    total = len(slides)

    if formato == "carrossel" and not 2 <= total <= 10:
        c.erro("slides", f"um carrossel tem de 2 a 10 slides (tem {total}). Com um slide só, use o formato post_unico")
    elif formato == "post_unico" and total != 1:
        c.erro("slides", f"post_unico tem exatamente 1 slide (tem {total}). Para vários slides, use carrossel")
    elif formato == "reel" and total > 1:
        c.erro("slides", f"reel não tem artes de carrossel: deixe `slides` vazio ou só com a capa (tem {total}). O roteiro vai em `roteiro`")
    elif formato not in FORMATOS and not 0 <= total <= 10:
        c.erro("slides", f"são permitidos até 10 slides (tem {total})")

    for pos, slide in enumerate(slides):
        _validar_slide(c, slide, pos, total, formato, d, ctx)


def _validar_slide(c: Coletor, s, pos: int, total: int, formato, post: dict, ctx: Contexto) -> None:
    rot = f"slide {pos + 1}"
    if not isinstance(s, dict):
        c.erro(rot, "cada slide deve ser um objeto JSON, entre chaves { }")
        return
    for campo in CAMPOS_SLIDE:
        if campo not in s:
            c.erro(f"{rot} › {campo}", "campo ausente")
    for campo in s:
        if campo not in CAMPOS_SLIDE:
            c.aviso(f"{rot} › {campo}", "campo desconhecido; confira se não é erro de digitação")

    if "n" in s:
        if not eh_inteiro(s["n"]):
            c.erro(f"{rot} › n", "deve ser um número inteiro")
        elif s["n"] != pos + 1:
            c.erro(f"{rot} › n", f"é {s['n']}, mas era esperado {pos + 1}. A numeração começa em 1 e não pode ter buracos nem repetição")

    papel = s.get("papel")
    if "papel" in s and opcao_valida(c, f"{rot} › papel", papel, PAPEIS):
        if pos == 0 and papel != "capa":
            c.erro(f"{rot} › papel", "o primeiro slide deve ter o papel capa")
        if pos > 0 and papel == "capa":
            c.erro(f"{rot} › papel", "só o primeiro slide pode ser a capa")
        if formato == "carrossel":
            if pos == total - 1 and total > 1 and papel != "cta":
                c.erro(f"{rot} › papel", "o último slide do carrossel deve ter o papel cta")
            if pos < total - 1 and papel == "cta":
                c.erro(f"{rot} › papel", "só o último slide do carrossel pode ter o papel cta")
        elif papel == "cta":
            c.erro(f"{rot} › papel", "o papel cta só vale no último slide de um carrossel. Em post único e reel, a chamada fica na legenda")
    else:
        papel = None

    layout = s.get("layout")
    if "layout" in s and opcao_valida(c, f"{rot} › layout", layout, LAYOUTS):
        if papel in LAYOUT_DO_PAPEL and layout != LAYOUT_DO_PAPEL[papel]:
            c.aviso(f"{rot} › layout", f"o slide tem papel {papel} mas layout {layout}; o gerador de artes espera o layout {papel}")
        if papel == "conteudo" and layout in LAYOUT_DO_PAPEL:
            c.aviso(f"{rot} › layout", f"o layout {layout} é reservado para o papel {layout}; um slide de conteúdo usa texto, lista, cartoes, imagem ou citacao")
    else:
        layout = None

    if "titulo" in s and texto_obrigatorio(c, f"{rot} › titulo", s["titulo"]) and papel == "capa":
        n = palavras(s["titulo"])
        if n > MAX_PALAVRAS_CAPA:
            c.erro(f"{rot} › titulo", f"a capa tem {n} palavras; o limite é {MAX_PALAVRAS_CAPA}. Encurte o título da capa")
    if "texto" in s and not isinstance(s["texto"], str):
        c.erro(f"{rot} › texto", "deve ser um texto (pode ser vazio: \"\")")

    itens = s.get("itens") if "itens" in s else None
    if "itens" in s:
        if lista_de_textos(c, f"{rot} › itens", itens):
            if layout in ("lista", "cartoes") and not 2 <= len(itens) <= 5:
                c.erro(f"{rot} › itens", f"o layout {layout} pede de 2 a 5 itens (tem {len(itens)})")
            elif layout not in ("lista", "cartoes") and layout is not None and itens:
                c.aviso(f"{rot} › itens", f"só os layouts lista e cartoes usam `itens`; no layout {layout} eles serão ignorados")

    if "imagem" in s:
        _validar_imagem(c, s["imagem"], rot, layout, ctx)

    if "texto_alternativo" in s:
        if not isinstance(s["texto_alternativo"], str):
            c.erro(f"{rot} › texto_alternativo", "deve ser um texto")
        elif not s["texto_alternativo"].strip():
            c.aviso(f"{rot} › texto_alternativo", "está vazio; descreva o slide para quem usa leitor de tela")
    if "fonte_interna" in s and not isinstance(s["fonte_interna"], str):
        c.erro(f"{rot} › fonte_interna", "deve ser um texto (pode ser vazio: \"\")")

    juntos = " ".join(textos_do_slide(s))
    if palavras(juntos) > MAX_PALAVRAS_SLIDE:
        c.aviso(rot, f"tem {palavras(juntos)} palavras; slide com muito texto cansa. Uma ideia por slide")
    achou_dado = RE_DADO.search(juntos)
    if achou_dado and not (isinstance(s.get("fonte_interna"), str) and s["fonte_interna"].strip()):
        c.aviso(f"{rot} › fonte_interna", f"o slide traz um dado ({achou_dado.group(0).strip()!r}) mas `fonte_interna` está vazia")
    if RE_ROTULO_FONTE.search(juntos):
        c.erro(rot, "o texto da arte não pode ter \"Fonte:\". A fonte fica só em `fontes` e `fonte_interna`")
    if RE_URL_NO_TEXTO.search(juntos):
        c.aviso(rot, "o texto da arte tem um endereço de site; fontes ficam só nos campos internos")
    sem_glifo = simbolos_sem_glifo(juntos)
    if sem_glifo:
        c.aviso(rot, f"tem emoji ou símbolo que a fonte das artes não desenha ({' '.join(sem_glifo)}): sai como quadradinho. Troque por palavras")

    if papel == "capa" and isinstance(s.get("texto"), str) and s["texto"].strip():
        c.aviso(f"{rot} › texto", "a capa tem texto de apoio; o padrão recomendado é capa só com o título (confira o padrao-visual.md da marca)")
    if papel == "cta":
        if isinstance(s.get("titulo"), str) and palavras(s["titulo"]) > MAX_PALAVRAS_TITULO_CTA:
            c.aviso(f"{rot} › titulo", f"o último slide tem {palavras(s['titulo'])} palavras; o título já é a chamada, com cerca de 8 palavras")
        if isinstance(s.get("texto"), str) and palavras(s["texto"]) > MAX_PALAVRAS_APOIO_CTA:
            c.aviso(f"{rot} › texto", "o apoio do último slide deve ter no máximo uma linha curta, ou ficar vazio")


def _validar_imagem(c: Coletor, img, rot: str, layout, ctx: Contexto) -> None:
    campo = f"{rot} › imagem"
    if img is None:
        if layout == "imagem":
            c.erro(campo, "o layout imagem precisa do objeto `imagem` (tipo, arquivo, descricao)")
        return
    if not isinstance(img, dict):
        c.erro(campo, "deve ser null ou um objeto com tipo, arquivo e descricao")
        return
    tipo = img.get("tipo")
    if not opcao_valida(c, f"{campo}.tipo", tipo, TIPOS_IMAGEM):
        tipo = None
    texto_obrigatorio(c, f"{campo}.descricao", img.get("descricao"))
    arquivo = img.get("arquivo")
    if tipo == "foto":
        if not isinstance(arquivo, str) or not arquivo.strip():
            c.erro(f"{campo}.arquivo", "foto precisa do caminho do arquivo (relativo à pasta da marca ou do lote)")
    elif arquivo is not None and not isinstance(arquivo, str):
        c.erro(f"{campo}.arquivo", "deve ser um texto (caminho relativo) ou vazio enquanto a imagem não existe")
    if isinstance(arquivo, str) and arquivo.strip():
        if not caminho_relativo_seguro(arquivo):
            c.erro(f"{campo}.arquivo", "use caminho relativo com barras normais (/), sem unidade de disco e sem \"..\"")
        elif not (ctx.pasta_marca / arquivo).is_file() and not (ctx.pasta_lote / arquivo).is_file():
            c.aviso(f"{campo}.arquivo", f"arquivo não encontrado (procurei em marcas/{ctx.marca}/ e na pasta do lote): {arquivo}")
    if tipo == "gerada":
        prompt = img.get("prompt")
        if texto_obrigatorio(c, f"{campo}.prompt", prompt):
            frases = [f for f in re.split(r"(?<=[.!?])\s+", prompt.strip()) if f.strip()]
            if not RE_PROMPT_SEM_TEXTO.search(frases[-1]):
                c.aviso(f"{campo}.prompt", "o pedido da imagem deve terminar com \"Sem texto, sem letras, sem logos.\" (a IA não escreve texto nem desenha logo dentro da imagem)")
    elif tipo == "foto" and img.get("prompt"):
        c.aviso(f"{campo}.prompt", "prompt só vale para imagem gerada")


def _validar_roteiro(c: Coletor, d: dict) -> None:
    roteiro = d["roteiro"]
    if d.get("formato") == "reel":
        if not isinstance(roteiro, list) or not roteiro:
            c.erro("roteiro", "reel precisa do roteiro: lista de blocos {\"tempo\", \"fala\", \"tela\"}")
            return
        for i, bloco in enumerate(roteiro, start=1):
            rot = f"roteiro {i}"
            if not isinstance(bloco, dict):
                c.erro(rot, "cada bloco deve ser um objeto com tempo, fala e tela")
                continue
            for chave in ("tempo", "fala", "tela"):
                if chave not in bloco:
                    c.erro(f"{rot} › {chave}", "campo ausente")
            if "tempo" in bloco:
                if not texto_obrigatorio(c, f"{rot} › tempo", bloco["tempo"]):
                    pass
                elif not RE_TEMPO_ROTEIRO.match(bloco["tempo"].strip()):
                    c.aviso(f"{rot} › tempo", f"{bloco['tempo']!r} foge do formato \"0-3s\"")
            if "fala" in bloco:
                texto_obrigatorio(c, f"{rot} › fala", bloco["fala"])
            if "tela" in bloco and not isinstance(bloco["tela"], str):
                c.erro(f"{rot} › tela", "deve ser um texto (pode ser vazio: \"\")")
    elif roteiro is not None:
        c.aviso("roteiro", "só reel usa roteiro; neste formato o campo deve ser null")


def _validar_legenda(c: Coletor, d: dict) -> None:
    legenda = d["legenda"]
    if not texto_obrigatorio(c, "legenda", legenda):
        return
    tamanho = tamanho_instagram(legenda)
    if tamanho > LIMITE_LEGENDA:
        c.erro("legenda", f"tem {tamanho} caracteres; o limite do Instagram é {LIMITE_LEGENDA}")
    if RE_ROTULO_FONTE.search(legenda):
        c.erro("legenda", "a legenda não pode ter \"Fonte:\". A fonte fica só em `fontes` e `fontes_legenda_internas`")
    if RE_URL_NO_TEXTO.search(legenda):
        c.aviso("legenda", "tem um endereço de site; links na legenda não são clicáveis e fontes ficam só nos campos internos")
    primeira = legenda.strip().splitlines()[0] if legenda.strip() else ""
    if len(primeira) > MAX_PRIMEIRA_LINHA:
        c.aviso("legenda", f"a primeira linha tem {len(primeira)} caracteres; o gancho deve caber em cerca de {MAX_PRIMEIRA_LINHA}, que é o que aparece antes do \"mais\"")
    chamada = d.get("chamada")
    if isinstance(chamada, str) and chamada.strip() and not normalizar(legenda).endswith(normalizar(chamada)):
        c.aviso("legenda", "não termina com a mesma chamada do campo `chamada`")
    hashtags_no_texto = RE_HASHTAG.findall(legenda)
    if hashtags_no_texto:
        lista = d.get("hashtags") if isinstance(d.get("hashtags"), list) else []
        repetidas = {h.lstrip("#").casefold() for h in lista if isinstance(h, str)} & {h.casefold() for h in hashtags_no_texto}
        if repetidas:
            c.erro("legenda", "repete hashtags que já estão em `hashtags`: " + ", ".join(sorted("#" + h for h in repetidas)))
        else:
            c.aviso("legenda", "tem hashtag no texto; deixe as hashtags só no campo `hashtags`")
        total = len({h.casefold() for h in hashtags_no_texto} | {h.lstrip("#").casefold() for h in lista if isinstance(h, str)})
        if total > MAX_HASHTAGS:
            c.erro("hashtags", f"somando as do texto, são {total} hashtags; o máximo é {MAX_HASHTAGS}")
    hashtags = d.get("hashtags")
    if isinstance(hashtags, list):
        total_final = tamanho_instagram(legenda_com_hashtags(legenda, hashtags))
        if tamanho <= LIMITE_LEGENDA < total_final:
            c.erro("legenda", f"com as hashtags que o publicador acrescenta, a legenda chega a {total_final} caracteres e passa de {LIMITE_LEGENDA}")
    if RE_COMENTE_PALAVRA.search(legenda) or (isinstance(chamada, str) and RE_COMENTE_PALAVRA.search(chamada)):
        c.aviso("chamada", "usa \"Comente PALAVRA\". Isso só vale se a marca tiver resposta automática por direct (veja \"Chamadas disponíveis\" em marca.md)")


def _validar_hashtags(c: Coletor, d: dict) -> None:
    hashtags = d["hashtags"]
    if not isinstance(hashtags, list):
        c.erro("hashtags", "deve ser uma lista (use [] para nenhuma)")
        return
    if len(hashtags) > MAX_HASHTAGS:
        c.erro("hashtags", f"tem {len(hashtags)} hashtags; o máximo é {MAX_HASHTAGS}")
    vistas = set()
    for i, h in enumerate(hashtags):
        campo = f"hashtags[{i}]"
        if not isinstance(h, str) or not h.strip():
            c.erro(campo, "deve ser um texto não vazio")
            continue
        limpa = h[1:] if h.startswith("#") else h
        if h.startswith("#"):
            c.aviso(campo, "escreva a hashtag sem o # (quem publica acrescenta)")
        if not re.fullmatch(r"\w+", limpa):
            c.erro(campo, f"{h!r} só pode ter letras, números e _ (sem espaço nem pontuação)")
        if limpa.casefold() in vistas:
            c.aviso(campo, f"{h!r} está repetida")
        vistas.add(limpa.casefold())


def _validar_fontes(c: Coletor, d: dict, ctx: Contexto) -> None:
    fontes = d["fontes"]
    if not isinstance(fontes, list):
        c.erro("fontes", "deve ser uma lista (use [] quando não houver fonte)")
        return
    for i, f in enumerate(fontes, start=1):
        rot = f"fontes {i}"
        if not isinstance(f, dict):
            c.erro(rot, "cada fonte deve ser um objeto com nome, url e data")
            continue
        for chave in ("nome", "url", "data"):
            if chave not in f:
                c.erro(f"{rot} › {chave}", "campo ausente")
        if "nome" in f:
            texto_obrigatorio(c, f"{rot} › nome", f["nome"])
        if "url" in f and not url_valida(f["url"]):
            c.erro(f"{rot} › url", "deve ser um endereço http:// ou https:// (caminho de arquivo não vale)")
        if "data" in f:
            if not eh_data(f["data"]):
                c.erro(f"{rot} › data", "deve ser a data da consulta no formato AAAA-MM-DD")
            elif date.fromisoformat(f["data"]) > ctx.hoje:
                c.aviso(f"{rot} › data", "a data da consulta está no futuro")
    slides = d.get("slides") if isinstance(d.get("slides"), list) else []
    com_dado = any(
        isinstance(s, dict) and RE_DADO.search(" ".join(textos_do_slide(s))) for s in slides
    ) or (isinstance(d.get("legenda"), str) and RE_DADO.search(d["legenda"]))
    internas = d.get("fontes_legenda_internas")
    if com_dado and not fontes and not (isinstance(internas, list) and internas):
        c.aviso("fontes", "o texto tem números ou datas, mas o post não registra nenhuma fonte (`fontes` ou `fontes_legenda_internas`)")


def _validar_confirmar(c: Coletor, d: dict) -> None:
    confirmar = d["confirmar"]
    if not isinstance(confirmar, list):
        c.erro("confirmar", "deve ser uma lista (use [] quando não há pendência)")
        return
    for i, item in enumerate(confirmar):
        campo = f"confirmar[{i}]"
        if not isinstance(item, str) or not item.strip():
            c.erro(campo, "deve ser um texto não vazio")
            continue
        sem_acento = unicodedata.normalize("NFD", item).encode("ascii", "ignore").decode().upper()
        if not sem_acento.startswith("NAO VERIFICADO:"):
            c.aviso(campo, "deve começar com \"NÃO VERIFICADO: \"")
        c.pendencias.append(item)


def _validar_dados_sensiveis(c: Coletor, d: dict) -> None:
    visiveis = []
    for chave in ("chamada", "legenda"):
        if isinstance(d.get(chave), str):
            visiveis.append((chave, d[chave]))
    if isinstance(d.get("slides"), list):
        for pos, s in enumerate(d["slides"], start=1):
            if isinstance(s, dict):
                visiveis.append((f"slide {pos}", " ".join(textos_do_slide(s))))
    if isinstance(d.get("roteiro"), list):
        for pos, b in enumerate(d["roteiro"], start=1):
            if isinstance(b, dict):
                visiveis.append((f"roteiro {pos}", " ".join(str(b.get(k, "")) for k in ("fala", "tela"))))
    for campo, texto in visiveis:
        for nome, padrao in SENSIVEIS:
            achado = padrao.search(texto)
            if achado:
                c.aviso(campo, f"parece conter {nome} ({achado.group(0)}); confira se há autorização registrada em regras.md")


def _validar_ciclo(c: Coletor, d: dict) -> None:
    status = d.get("status")
    if "status" in d:
        opcao_valida(c, "status", status, STATUS)

    if "revisao" in d and d["revisao"] is not None:
        r = d["revisao"]
        if not isinstance(r, dict):
            c.erro("revisao", "deve ser null ou um objeto com data, veredito e pontos")
        else:
            if not eh_data_ou_hora(r.get("data")):
                c.erro("revisao.data", "deve ser uma data AAAA-MM-DD (ou data e hora ISO 8601)")
            opcao_valida(c, "revisao.veredito", r.get("veredito"), VEREDITOS)
            if not isinstance(r.get("pontos"), list):
                c.erro("revisao.pontos", "deve ser uma lista de textos (pode ser vazia)")
            else:
                lista_de_textos(c, "revisao.pontos", r["pontos"])
                if r.get("veredito") in ("ajustar", "refazer") and not r["pontos"]:
                    c.aviso("revisao.pontos", f"o veredito {r['veredito']} precisa listar o que ajustar ou o motivo")

    if "historico" in d:
        h = d["historico"]
        if not isinstance(h, list):
            c.erro("historico", "deve ser uma lista de eventos")
        else:
            if not h:
                c.aviso("historico", "está vazio; registre pelo menos a criação do post")
            for i, ev in enumerate(h, start=1):
                rot = f"historico {i}"
                if not isinstance(ev, dict):
                    c.erro(rot, "cada evento deve ser um objeto com data, evento e por")
                    continue
                if not eh_data_ou_hora(ev.get("data")):
                    c.erro(f"{rot} › data", "deve ser uma data AAAA-MM-DD (ou data e hora ISO 8601)")
                for chave in ("evento", "por"):
                    texto_obrigatorio(c, f"{rot} › {chave}", ev.get(chave))

    aprovacao = d.get("aprovacao")
    if "aprovacao" in d and aprovacao is not None:
        if not isinstance(aprovacao, dict):
            c.erro("aprovacao", "deve ser null ou um objeto com por, frase, data e hash")
        else:
            for chave in ("por", "frase", "hash"):
                texto_obrigatorio(c, f"aprovacao.{chave}", aprovacao.get(chave))
            if not eh_data_ou_hora(aprovacao.get("data")):
                c.erro("aprovacao.data", "deve ser uma data AAAA-MM-DD (ou data e hora ISO 8601)")

    if "agendado_para" in d and d["agendado_para"] is not None and not data_hora_com_fuso(d["agendado_para"]):
        c.erro("agendado_para", "deve ser data e hora ISO 8601 com fuso, por exemplo 2026-11-05T18:00:00-03:00")

    publicacao = d.get("publicacao")
    if "publicacao" in d and publicacao is not None:
        if not isinstance(publicacao, dict):
            c.erro("publicacao", "deve ser null ou um objeto com media_id, permalink e publicado_em")
        else:
            texto_obrigatorio(c, "publicacao.media_id", publicacao.get("media_id"))
            permalink = publicacao.get("permalink")
            if not isinstance(permalink, str) or (permalink.strip() and not url_valida(permalink)):
                c.erro("publicacao.permalink", "deve ser um endereço http:// ou https:// (ou vazio, quando a API não devolveu o link)")
            if not data_hora_com_fuso(publicacao.get("publicado_em")):
                c.erro("publicacao.publicado_em", "deve ser data e hora ISO 8601 com fuso")

    if status in ("aprovado", "agendado", "publicado") and "aprovacao" in d and aprovacao is None:
        c.erro("aprovacao", f"o status {status} exige o registro da aprovação (por, frase, data e hash)")
    if status == "agendado" and "agendado_para" in d and d["agendado_para"] is None:
        c.erro("agendado_para", "o status agendado exige a data e a hora do agendamento")
    if status == "publicado" and "publicacao" in d and publicacao is None:
        c.erro("publicacao", "o status publicado exige media_id, permalink e publicado_em")


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------

def validar_lote(raiz: Path, marca: str, pasta_marca: Path, lote: str, pasta_lote: Path,
                 so_arquivo: Path | None = None, hoje: date | None = None) -> ResultadoLote:
    resultado = ResultadoLote(marca=marca, lote=lote, pasta_lote=pasta_lote)
    m = RE_LOTE.match(lote)
    data_ok = bool(m)
    if m:
        try:
            date.fromisoformat(m.group(1))
        except ValueError:
            data_ok = False
    if not data_ok:
        resultado.gerais.erro("lote", f"o nome da pasta do lote deve ser AAAA-MM-DD-slug (ex.: 2026-11-03-semana-1); a pasta se chama {lote!r}")

    pilares, problema = carregar_pilares(pasta_marca)
    if problema:
        resultado.gerais.erro("estrategia.json", problema)

    arquivos = [so_arquivo] if so_arquivo else arquivos_de_posts(pasta_lote)
    if not arquivos:
        resultado.gerais.erro("posts", "nenhum arquivo posts/*.json encontrado neste lote")
        return resultado

    ctx = Contexto(
        raiz=raiz, marca=marca, pasta_marca=pasta_marca, lote=lote, pasta_lote=pasta_lote,
        pilares=pilares, ids=indexar_ids(pasta_marca), hoje=hoje or date.today(),
    )
    for arq in arquivos:
        dados, problema = ler_json(arq)
        if problema:
            coletor = Coletor()
            coletor.erro("(arquivo)", problema)
            resultado.posts.append(ResultadoPost(arq, f"posts/{arq.name}", coletor, None))
            continue
        coletor = validar_post(dados, arq, ctx)
        resultado.posts.append(ResultadoPost(arq, f"posts/{arq.name}", coletor, dados if isinstance(dados, dict) else None))
    return resultado


def localizar_post(pasta_marca: Path, valor: str, lote: str | None) -> tuple[Path, str]:
    """Aceita o id do post ou o caminho do arquivo. Devolve (arquivo, nome do lote)."""
    caminho = Path(valor)
    if caminho.is_file():
        return caminho.resolve(), caminho.resolve().parent.parent.name
    id_post = caminho.name[:-5] if caminho.name.endswith(".json") else valor
    lotes = [Path(lote.replace("\\", "/")).name] if lote else listar_lotes(pasta_marca)
    achados = [(pasta_marca / "conteudo" / nome / "posts" / f"{id_post}.json", nome) for nome in lotes]
    achados = [(p, n) for p, n in achados if p.is_file()]
    if not achados:
        raise ErroDeUso(f"Post '{id_post}' não encontrado em marcas/{pasta_marca.name}/conteudo/*/posts/.")
    if len(achados) > 1:
        raise ErroDeUso(f"O id '{id_post}' existe em mais de um lote ({', '.join(n for _, n in achados)}). Informe --lote.")
    return achados[0][0].resolve(), achados[0][1]


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

def imprimir(resultado: ResultadoLote, estrito: bool) -> None:
    print(f"Marca: {resultado.marca} · Lote: {resultado.lote}")
    for m in resultado.gerais.msgs:
        print(f"  {m.nivel.upper():<6} {m.campo}: {m.texto}")
    for p in resultado.posts:
        c = p.coletor
        falhou = bool(c.erros) or (estrito and bool(c.avisos))
        print(f"{'FALHA' if falhou else 'OK':<5} {p.rotulo}")
        for m in c.msgs:
            print(f"  {m.nivel.upper():<6} {m.campo}: {m.texto}")
        for item in c.pendencias:
            print(f"  PENDENTE confirmar: {item}")
    partes = [f"{len(resultado.posts)} post(s) verificado(s)", f"{resultado.total_erros} erro(s)", f"{resultado.total_avisos} aviso(s)"]
    if resultado.total_pendencias:
        partes.append(f"{resultado.total_pendencias} pendência(s) em confirmar[] (o post não é publicado até resolver)")
    print("Resumo: " + ", ".join(partes) + ".")


class _AjudaPT(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


_TRADUCOES = (
    (r"the following arguments are required", "faltam argumentos obrigatórios"),
    (r"unrecognized arguments", "argumentos não reconhecidos"),
    (r"expected one argument", "falta o valor da opção"),
    (r"invalid choice", "valor inválido"),
    (r"ambiguous option", "opção ambígua"),
    (r"\bargument (?=-)", "opção "),
)


class ParserPT(argparse.ArgumentParser):
    """ArgumentParser com a ajuda e as mensagens de erro em português."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", _AjudaPT)
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "argumentos"
        self._optionals.title = "opções"
        self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="mostra esta ajuda e sai")

    def error(self, message):
        for origem, destino in _TRADUCOES:
            message = re.sub(origem, destino, message)
        self.print_usage(sys.stderr)
        self.exit(2, f"ERRO: {message}\n")


def montar_parser() -> argparse.ArgumentParser:
    parser = ParserPT(
        prog="validar_posts.py",
        description="Valida os posts de um lote contra o contrato do projeto (docs/arquitetura.md). "
                    "Só lê arquivos; não altera nada. Mostra o arquivo e o campo de cada problema.",
        epilog="Exemplos:\n"
               "  python -X utf8 skills/criar-conteudo/scripts/validar_posts.py --marca exemplo --lote 2026-11-03-exemplo\n"
               "  python -X utf8 skills/criar-conteudo/scripts/validar_posts.py --marca exemplo --post 2026-11-03-1-contas-separadas\n"
               "Saída: 0 = sem erros; 1 = há erros nos posts; 2 = marca, lote ou post não encontrados.",
    )
    parser.add_argument("--marca", help="slug da pasta da marca em marcas/. Se houver só uma marca além de 'exemplo', é usada sem perguntar")
    parser.add_argument("--lote", help="nome do lote (AAAA-MM-DD-slug), em marcas/<marca>/conteudo/")
    parser.add_argument("--post", help="id do post (ou caminho do arquivo .json) para validar só ele")
    parser.add_argument("--estrito", action="store_true", help="trata os avisos como erros")
    parser.add_argument("--raiz", help="avançado: pasta raiz do projeto (por padrão, a pasta onde este script está instalado)")
    return parser


def preparar_saida() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    preparar_saida()
    args = montar_parser().parse_args(argv)
    raiz = Path(args.raiz).resolve() if args.raiz else RAIZ_PADRAO
    try:
        if not args.lote and not args.post:
            raise ErroDeUso("Informe --lote <lote> para validar o lote inteiro ou --post <id> para validar um post.")
        marca, pasta_marca = resolver_marca(raiz, args.marca)
        if args.post:
            arquivo, nome_lote = localizar_post(pasta_marca, args.post, args.lote)
            lote, pasta_lote = nome_lote, arquivo.parent.parent
            resultado = validar_lote(raiz, marca, pasta_marca, lote, pasta_lote, so_arquivo=arquivo)
        else:
            lote, pasta_lote = resolver_lote(pasta_marca, args.lote)
            resultado = validar_lote(raiz, marca, pasta_marca, lote, pasta_lote)
    except ErroDeUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    imprimir(resultado, args.estrito)
    falhou = resultado.total_erros > 0 or (args.estrito and resultado.total_avisos > 0)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
