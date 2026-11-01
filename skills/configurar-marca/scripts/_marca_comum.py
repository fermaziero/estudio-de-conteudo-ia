# -*- coding: utf-8 -*-
"""Funções compartilhadas pelos scripts da skill configurar-marca.

Este arquivo não é um script: os vizinhos desta pasta o importam.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from datetime import date, datetime
from pathlib import Path

PASTA_SCRIPTS = Path(__file__).resolve().parent
PASTA_SKILL = PASTA_SCRIPTS.parent
PASTA_MODELOS = PASTA_SKILL / "modelos"
RAIZ_PADRAO = PASTA_SKILL.parent.parent  # skills/configurar-marca -> skills -> raiz do projeto

MARCA_EXEMPLO = "exemplo"
RE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_ARROBA = re.compile(r"^@[A-Za-z0-9._]{1,30}$")
EXT_IMAGEM = {".png", ".jpg", ".jpeg", ".webp"}
EXT_FONTE = {".ttf", ".otf"}
CABECALHO_FEEDBACK = ["Data", "O que a pessoa disse (literal)", "O que mudou", "Arquivo"]
ACENTOS_PT = "áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ"


class ErroUso(Exception):
    """Pedido que não dá para atender (marca inexistente, argumento inválido...). Sai com código 2."""


# ---------------------------------------------------------------------------
# Terminal e argumentos
# ---------------------------------------------------------------------------

def configurar_saida() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


class _AjudaPT(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


_TRADUCOES = (
    (r"the following arguments are required", "faltam argumentos obrigatórios"),
    (r"unrecognized arguments", "argumentos não reconhecidos"),
    (r"expected one argument", "falta o valor da opção"),
    (r"invalid choice", "valor inválido"),
    (r"choose from", "escolha entre"),
    (r"ambiguous option", "opção ambígua"),
    (r"not allowed with argument", "não pode ser usado junto com a opção"),
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
        self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS,
                          help="mostra esta ajuda e sai")

    def error(self, message):
        for origem, destino in _TRADUCOES:
            message = re.sub(origem, destino, message)
        self.print_usage(sys.stderr)
        self.exit(2, f"ERRO: {message}\n")


def criar_parser(prog: str, descricao: str, exemplos: list[str], saidas: str = "") -> ParserPT:
    epilogo = "Exemplos:\n" + "\n".join(f"  {e}" for e in exemplos)
    epilogo += "\n" + (saidas or "Saída: 0 = deu certo; 1 = há problemas a corrigir; 2 = pedido que não dá para atender.")
    return ParserPT(prog=prog, description=descricao, epilog=epilogo)


def opcoes_marca_e_raiz(parser: ParserPT, marca_obrigatoria: bool = False) -> None:
    ajuda = "nome (slug) da pasta da marca em marcas/. Se houver só uma marca além de 'exemplo', ela é usada sem perguntar"
    parser.add_argument("--marca", required=marca_obrigatoria, metavar="SLUG", help=ajuda)
    parser.add_argument("--raiz", metavar="PASTA",
                        help="avançado: pasta raiz do projeto (por padrão, a pasta onde este script está instalado)")


def pasta_raiz(arg: str | None) -> Path:
    return Path(arg).expanduser().resolve() if arg else RAIZ_PADRAO


# ---------------------------------------------------------------------------
# Marcas
# ---------------------------------------------------------------------------

def slug_valido(valor: str) -> bool:
    return bool(RE_SLUG.match(valor)) and 2 <= len(valor) <= 40


def listar_marcas(raiz: Path) -> list[str]:
    base = raiz / "marcas"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def resolver_marca(raiz: Path, marca: str | None) -> tuple[str, Path]:
    """Devolve (slug, pasta). Se --marca faltar, usa a única marca além de 'exemplo'."""
    base = raiz / "marcas"
    if marca:
        if not RE_SLUG.match(marca):
            raise ErroUso(f"Nome de marca inválido: {marca!r}. Use o nome da pasta (minúsculas, números e hífen).")
        pasta = base / marca
        if not pasta.is_dir():
            existentes = ", ".join(listar_marcas(raiz)) or "nenhuma"
            raise ErroUso(f"Marca '{marca}' não encontrada em marcas/. Marcas existentes: {existentes}.")
        return marca, pasta
    reais = [m for m in listar_marcas(raiz) if m != MARCA_EXEMPLO]
    if len(reais) == 1:
        return reais[0], base / reais[0]
    if len(reais) > 1:
        raise ErroUso("Há mais de uma marca. Informe qual com --marca <slug>. Opções: " + ", ".join(reais) + ".")
    raise ErroUso("Nenhuma marca encontrada além de 'exemplo'. Para testar o fluxo, use --marca exemplo. "
                  "Para criar a sua, use a skill configurar-marca.")


def mostrar_caminho(caminho: Path, raiz: Path) -> str:
    try:
        return caminho.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return str(caminho)


def caminho_dentro(base: Path, relativo) -> tuple[Path | None, str | None]:
    """Resolve um caminho relativo dentro de 'base'. Devolve (caminho, None) ou (None, mensagem)."""
    if not isinstance(relativo, str) or not relativo.strip():
        return None, "o caminho está vazio"
    texto = relativo.strip()
    if texto.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:", texto):
        return None, "o caminho precisa ser relativo à pasta da marca (sem C:\\, sem / no começo)"
    partes = [p for p in re.split(r"[\\/]+", texto) if p]
    if ".." in partes:
        return None, "o caminho não pode usar '..' (sair da pasta da marca)"
    alvo = (base / Path(*partes)).resolve()
    try:
        alvo.relative_to(base.resolve())
    except ValueError:
        return None, "o caminho aponta para fora da pasta da marca"
    return alvo, None


# ---------------------------------------------------------------------------
# Arquivos
# ---------------------------------------------------------------------------

def hoje() -> str:
    return date.today().isoformat()


def data_valida(valor) -> bool:
    if not isinstance(valor, str) or not RE_DATA.match(valor):
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def ler_texto(caminho: Path) -> tuple[str | None, str | None]:
    try:
        return caminho.read_text(encoding="utf-8-sig"), None
    except FileNotFoundError:
        return None, "arquivo não encontrado"
    except UnicodeDecodeError:
        return None, "o arquivo não está salvo em UTF-8 (salve de novo como UTF-8)"
    except OSError as e:
        return None, f"não consegui ler o arquivo ({e.strerror or e})"


_ERROS_JSON = (
    ("Expecting property name enclosed in double quotes", "esperava um nome entre aspas duplas (vírgula sobrando no fim de uma lista?)"),
    ("Expecting ',' delimiter", "faltou uma vírgula (ou uma aspa de fechamento)"),
    ("Expecting ':' delimiter", "faltou os dois-pontos depois do nome"),
    ("Expecting value", "faltou um valor"),
    ("Extra data", "sobrou texto depois do fim do JSON"),
    ("Unterminated string", "texto sem aspas de fechamento"),
    ("Invalid control character", "quebra de linha ou tabulação dentro de um texto (use \\n)"),
    ("Invalid \\escape", "barra invertida inválida dentro de um texto"),
)


def ler_json(caminho: Path) -> tuple[object | None, str | None]:
    texto, erro = ler_texto(caminho)
    if erro:
        return None, erro
    try:
        return json.loads(texto), None
    except json.JSONDecodeError as e:
        detalhe = next((destino for origem, destino in _ERROS_JSON if e.msg.startswith(origem)), e.msg)
        return None, f"JSON inválido (linha {e.lineno}, coluna {e.colno}): {detalhe}"


def escrever_texto(caminho: Path, texto: str) -> None:
    """Grava em UTF-8 com quebras de linha LF, de forma atômica (arquivo temporário + troca)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(caminho.parent), prefix=".tmp-", suffix=caminho.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.replace(tmp, caminho)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def escrever_json(caminho: Path, dados) -> None:
    escrever_texto(caminho, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def guardar_versao(arquivo: Path, motivo: str) -> Path:
    """Copia o arquivo para _antes-<motivo>/ ao lado dele, com data e hora no nome. Nada se apaga."""
    destino_dir = arquivo.parent / f"_antes-{motivo}"
    destino_dir.mkdir(exist_ok=True)
    carimbo = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    destino = destino_dir / f"{arquivo.stem}.{carimbo}{arquivo.suffix}"
    n = 1
    while destino.exists():
        n += 1
        destino = destino_dir / f"{arquivo.stem}.{carimbo}-{n}{arquivo.suffix}"
    shutil.copy2(arquivo, destino)
    return destino


# ---------------------------------------------------------------------------
# Texto e tabelas markdown
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto))
    base = "".join(ch for ch in base if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", base)).strip()


def secoes(texto: str, nivel: int = 2) -> list[tuple[str, int, list[str]]]:
    """Cabeçalhos do nível dado: lista de (título, linha 1-based, linhas do corpo)."""
    prefixo = "#" * nivel + " "
    resultado: list[tuple[str, int, list[str]]] = []
    for n, linha in enumerate(texto.splitlines(), 1):
        if linha.startswith(prefixo):
            resultado.append((linha[len(prefixo):].strip(), n, []))
        elif resultado:
            resultado[-1][2].append(linha)
    return resultado


def celulas_tabela(linha: str) -> list[str]:
    corpo = linha.strip()
    if corpo.startswith("|"):
        corpo = corpo[1:]
    if corpo.endswith("|") and not corpo.endswith("\\|"):
        corpo = corpo[:-1]
    return [p.strip().replace("\\|", "|") for p in re.split(r"(?<!\\)\|", corpo)]


def eh_separador_tabela(linha: str) -> bool:
    return bool(re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?", linha.strip()))


def encontrar_tabelas(linhas: list[str]) -> list[dict]:
    """Acha as tabelas markdown. Cada uma: inicio e fim (índices 0-based, fim exclusivo), cabecalho e
    linhas [(índice, células)]."""
    tabelas = []
    i = 0
    while i < len(linhas):
        if linhas[i].strip().startswith("|"):
            j = i
            while j < len(linhas) and linhas[j].strip().startswith("|"):
                j += 1
            bloco = linhas[i:j]
            if len(bloco) >= 2 and eh_separador_tabela(bloco[1]):
                tabelas.append({
                    "inicio": i,
                    "fim": j,
                    "cabecalho": celulas_tabela(bloco[0]),
                    "linhas": [(i + 2 + k, celulas_tabela(linha)) for k, linha in enumerate(bloco[2:])],
                })
            i = j
        else:
            i += 1
    return tabelas


def eh_tabela_de_feedback(tabela: dict) -> bool:
    return [normalizar(x) for x in tabela["cabecalho"]] == [normalizar(x) for x in CABECALHO_FEEDBACK]


# ---------------------------------------------------------------------------
# Cores
# ---------------------------------------------------------------------------

def hex_para_rgb(valor: str) -> tuple[int, int, int]:
    return int(valor[1:3], 16), int(valor[3:5], 16), int(valor[5:7], 16)


def rgb_para_hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(round(max(0, min(255, canal)))) for canal in rgb)


def _linear(canal: float) -> float:
    canal /= 255
    return canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4


def luminancia(rgb) -> float:
    r, g, b = (_linear(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b) -> float:
    """Razão de contraste WCAG entre duas cores RGB (de 1 a 21)."""
    la, lb = luminancia(a), luminancia(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def formatar_numero(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def ajustar_contraste(rgb, fundos, minimo: float) -> tuple[int, int, int]:
    """Mantém matiz e saturação e procura o brilho mais próximo do original que dê o contraste mínimo
    com todos os fundos."""
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in rgb))
    melhor, melhor_menor = tuple(int(x) for x in rgb), -1.0
    for passo in range(0, 101):
        for sinal in ((1,) if passo == 0 else (1, -1)):
            novo_v = v + sinal * passo / 100
            if novo_v < 0.03 or novo_v > 1.0:
                continue
            cand = tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, novo_v))
            menor = min(contraste(cand, f) for f in fundos)
            if menor >= minimo:
                return cand
            if menor > melhor_menor:
                melhor, melhor_menor = cand, menor
    return melhor


def nome_aproximado(rgb) -> str:
    """Nome simples, em português, só para a conversa com a pessoa (não é um nome oficial de cor)."""
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in rgb))
    if v < 0.12:
        return "preto"
    if s < 0.10:
        if v > 0.93:
            return "branco"
        return "cinza escuro" if v < 0.4 else "cinza" if v < 0.75 else "cinza claro"
    graus = h * 360
    faixas = ((15, "vermelho", "avermelhado"), (45, "laranja", "amarronzado"), (70, "amarelo", "amarelado"),
              (100, "verde-limão", "esverdeado"), (160, "verde", "esverdeado"), (190, "verde-água", "esverdeado"),
              (255, "azul", "azulado"), (290, "roxo", "arroxeado"), (335, "rosa", "arroxeado"),
              (361, "vermelho", "avermelhado"))
    _, base, adjetivo = next(f for f in faixas if graus < f[0])
    if s < 0.25:
        tom = " escuro" if v < 0.4 else " claro" if v >= 0.75 else ""
        return f"cinza{tom} {adjetivo}"
    if 15 <= graus < 50 and v < 0.6 and s > 0.35:
        return "marrom"
    if base in ("vermelho", "rosa") and v < 0.5:
        return "vinho"
    if 35 <= graus < 55 and s >= 0.5 and v >= 0.55:
        return "dourado"
    if base == "azul" and v < 0.35:
        return "azul-marinho"
    if v < 0.35:
        return base + " bem escuro"
    if v < 0.6:
        return base + " escuro"
    if v > 0.85 and s < 0.45:
        return base + " claro"
    return base


# ---------------------------------------------------------------------------
# Imagens e fontes (Pillow)
# ---------------------------------------------------------------------------

def importar_pillow():
    """Devolve (Image, ImageDraw, ImageFont) ou None se o Pillow não estiver instalado."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    return Image, ImageDraw, ImageFont


MSG_SEM_PILLOW = "o Pillow (biblioteca de imagens) não está instalado. Instale com: python -m pip install -r requirements.txt"


def abrir_imagem(caminho: Path):
    """Abre e carrega a imagem. Devolve (imagem, None) ou (None, mensagem)."""
    mod = importar_pillow()
    if mod is None:
        return None, MSG_SEM_PILLOW
    Image = mod[0]
    try:
        with Image.open(caminho) as teste:
            teste.verify()
        imagem = Image.open(caminho)
        imagem.load()
        return imagem, None
    except Exception:  # formato desconhecido, arquivo corrompido, imagem gigante...
        return None, "não é uma imagem válida (o arquivo pode estar corrompido ou ter outro formato)"


def pixels_rgba(imagem, lado: int = 160) -> list[tuple[int, int, int, int]]:
    copia = imagem.convert("RGBA")
    copia.thumbnail((lado, lado))
    dados = copia.tobytes()
    return list(zip(dados[0::4], dados[1::4], dados[2::4], dados[3::4]))


def tem_transparencia(imagem) -> bool:
    if imagem.mode in ("RGBA", "LA") or (imagem.mode == "P" and "transparency" in imagem.info):
        return imagem.convert("RGBA").getchannel("A").getextrema()[0] < 250
    return False


def glifos_ausentes(fonte, texto: str) -> list[str]:
    """Caracteres do texto que a fonte não sabe desenhar (compara com o desenho do 'caractere ausente')."""
    Image, ImageDraw, _ = importar_pillow()

    def desenho(ch: str) -> bytes:
        tela = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(tela).text((20, 20), ch, font=fonte, fill=255)
        return tela.tobytes()

    referencia = desenho("\uffff")
    ausentes = []
    for ch in sorted(set(texto) - set(" \t\n")):
        if ord(ch) > 127 and desenho(ch) == referencia:
            ausentes.append(ch)
    return ausentes


FONTES_DO_SISTEMA = ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "Arial Bold.ttf", "Helvetica.ttc",
                     "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "NotoSans-Bold.ttf")


def candidatas_de_fonte(extras=(), raiz: Path = RAIZ_PADRAO) -> list[str]:
    """Fontes a tentar, da mais para a menos preferida: as indicadas, as que acompanham a skill gerar-artes
    (se houver) e as do sistema."""
    lista = [str(x) for x in extras if x]
    pasta_artes = raiz / "skills" / "gerar-artes"
    if pasta_artes.is_dir():
        achadas = sorted(p for p in pasta_artes.rglob("*") if p.suffix.lower() in EXT_FONTE)
        achadas.sort(key=lambda p: ("bold" not in p.name.lower(), p.name))
        lista += [str(p) for p in achadas]
    lista += list(FONTES_DO_SISTEMA)
    return lista


# ---------------------------------------------------------------------------
# Segredos (para recusar e avisar; o valor nunca é mostrado)
# ---------------------------------------------------------------------------

IGNORAR_LINHA = "checar-segredos: ignorar"
SEGREDOS = [
    ("token do Instagram", re.compile(r"\bIG(?:AA|QV)[A-Za-z0-9_\-]{20,}")),
    ("token da Meta/Facebook", re.compile(r"\bEAA[A-Za-z0-9]{30,}")),
    ("chave de acesso AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("chave de API (sk-)", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("credencial do projeto com valor", re.compile(
        r"\b(?:IG_ACCESS_TOKEN|ARMAZENAMENTO_CHAVE_SECRETA|ARMAZENAMENTO_CHAVE_ID)\s*[=:]\s*[\"']?[A-Za-z0-9/+_\-.]{12,}")),
]


def achar_segredo(texto: str) -> str | None:
    """Nome do tipo de segredo que o texto parece conter, ou None. Nunca devolve o valor."""
    for rotulo, rx in SEGREDOS:
        if rx.search(texto):
            return rotulo
    return None
