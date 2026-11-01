"""Funções comuns dos scripts da skill acompanhar-resultados.

Só biblioteca padrão, Python 3.10 ou mais novo. Este arquivo é importado pelos
outros scripts da pasta; não é feito para rodar sozinho.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PADRAO_SLUG = re.compile(r"^(?=.{1,64}$)[a-z0-9]+(?:-[a-z0-9]+)*$")
NAO_MEDIDO = "não medido"
VAZIOS = {"", "-", "–", "—", "n/d", "nd", "n/a", "na", "null", "none", "nan", "nao medido", "não medido"}

_RE_ISO = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})"
    r"(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?\s*(Z|[+-]\d{2}(?::?\d{2})?)?)?$"
)
_RE_BR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_RE_MILHAR_BR = re.compile(r"^\d{1,3}(\.\d{3})+$")


class ErroUso(Exception):
    """Erro que a pessoa pode corrigir. A mensagem já vem em português, sem traceback."""


def configurar_saida() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


class ParserPT(argparse.ArgumentParser):
    def error(self, message: str):
        m = re.match(r"unrecognized arguments: (.*)", message)
        if m:
            message = f"argumento desconhecido: {m.group(1)}"
        m = re.match(r"argument (\S+): expected one argument", message)
        if m:
            message = f"falta o valor de {m.group(1)}"
        raise ErroUso(f"{message}. Use --ajuda para ver as opções.")


def criar_parser(prog: str) -> ParserPT:
    p = ParserPT(prog=prog, add_help=False)
    p.add_argument("-h", "--help", "--ajuda", dest="ajuda", action="store_true")
    return p


def raiz_do_projeto(arg: str | None = None) -> Path:
    if arg:
        raiz = Path(arg).expanduser().resolve()
        if not raiz.is_dir():
            raise ErroUso(f"A pasta informada em --raiz não existe: {raiz}")
        return raiz
    return Path(__file__).resolve().parents[3]


def listar_marcas(raiz: Path) -> list[str]:
    base = raiz / "marcas"
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and PADRAO_SLUG.match(p.name))


def resolver_marca(raiz: Path, marca: str | None) -> tuple[str, Path]:
    """Devolve (slug, pasta). A marca fictícia 'exemplo' só é usada quando a pessoa pede com --marca exemplo."""
    existentes = listar_marcas(raiz)
    if marca:
        if not PADRAO_SLUG.match(marca):
            raise ErroUso("O nome da marca (--marca) só pode ter letras minúsculas, números e hífen entre as palavras.")
        if marca not in existentes:
            opcoes = ", ".join(existentes) if existentes else "nenhuma"
            raise ErroUso(f"Não encontrei a marca '{marca}' em marcas/. Marcas disponíveis: {opcoes}.")
        return marca, raiz / "marcas" / marca
    suas = [m for m in existentes if m != "exemplo"]
    if len(suas) == 1:
        return suas[0], raiz / "marcas" / suas[0]
    if len(suas) > 1:
        lista = "\n".join(f"  - {m}" for m in suas)
        raise ErroUso(f"Há mais de uma marca. Rode de novo com --marca e uma destas:\n{lista}")
    if "exemplo" in existentes:
        raise ErroUso(
            "Ainda não há marca configurada em marcas/ (só existe a marca fictícia 'exemplo'). "
            "Rode antes a skill configurar-marca para criar a sua. Para ver o exemplo, rode de novo com --marca exemplo."
        )
    raise ErroUso("Nenhuma marca encontrada em marcas/. Rode antes a skill configurar-marca para criar a sua.")


def caminho_curto(caminho: Path, raiz: Path) -> str:
    try:
        return caminho.relative_to(raiz).as_posix()
    except ValueError:
        return str(caminho)


def ler_data_arg(texto: str | None, nome: str) -> date | None:
    if not texto:
        return None
    d = ler_data(texto)
    if d is None:
        raise ErroUso(f"{nome} precisa estar no formato AAAA-MM-DD (recebi '{texto}').")
    return d


def ler_fuso_arg(texto: str | None) -> timezone:
    if not texto:
        return timezone(timedelta(hours=-3))
    m = re.fullmatch(r"([+-])(\d{1,2})(?::?(\d{2}))?", texto.strip())
    if not m:
        raise ErroUso(f"--fuso precisa ter o formato -03:00 (recebi '{texto}').")
    delta = timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0))
    return timezone(-delta if m.group(1) == "-" else delta)


def ler_data(texto) -> date | None:
    if texto is None:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(texto).strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _fuso_do_texto(g: str | None):
    if not g:
        return None
    if g == "Z":
        return timezone.utc
    sinal = -1 if g[0] == "-" else 1
    dig = g[1:].replace(":", "")
    return timezone(sinal * timedelta(hours=int(dig[:2]), minutes=int(dig[2:4] or 0)))


def ler_momento(texto, fuso: timezone) -> tuple[datetime | None, bool]:
    """Lê data ou data com hora. Devolve (momento no fuso informado, tem_hora).

    Data sem hora vira meio-dia no fuso informado: o erro máximo é de 12 horas.
    """
    if texto is None:
        return None, False
    t = str(texto).strip()
    if not t:
        return None, False
    m = _RE_ISO.match(t)
    try:
        if m:
            a, mes, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if m.group(4) is None:
                return datetime(a, mes, d, 12, 0, tzinfo=fuso), False
            tz = _fuso_do_texto(m.group(7)) or fuso
            dt = datetime(a, mes, d, int(m.group(4)), int(m.group(5)), int(m.group(6) or 0), tzinfo=tz)
            return dt.astimezone(fuso), True
        m = _RE_BR.match(t)
        if m:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), 12, 0, tzinfo=fuso), False
    except ValueError:
        return None, False
    return None, False


def normalizar_coluna(nome: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", nome) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", "_", sem_acento.replace("﻿", "").strip().lower())


class Tabela:
    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.existe = False
        self.colunas: list[str] = []
        self.linhas: list[dict] = []
        self.avisos: list[str] = []


def ler_tabela(caminho: Path) -> Tabela:
    """Lê um CSV tolerante: UTF-8 com ou sem BOM, separador vírgula, ponto e vírgula ou tab."""
    t = Tabela(caminho)
    if not caminho.is_file():
        return t
    t.existe = True
    bruto = caminho.read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252", errors="replace")
        t.avisos.append("o arquivo não está em UTF-8; foi lido como Windows-1252. Salve de novo como UTF-8.")
    primeira = next((ln for ln in texto.splitlines() if ln.strip()), None)
    if primeira is None:
        return t
    delim = max((",", ";", "\t"), key=primeira.count)
    if primeira.count(delim) == 0:
        delim = ","
    leitor = csv.reader(io.StringIO(texto), delimiter=delim)
    cabecalho: list[str] | None = None
    for valores in leitor:
        if not any(v.strip() for v in valores):
            continue
        if cabecalho is None:
            cabecalho = [normalizar_coluna(v) for v in valores]
            t.colunas = [c for c in cabecalho if c]
            continue
        linha = {c: (valores[i].strip() if i < len(valores) else "") for i, c in enumerate(cabecalho) if c}
        linha["_linha"] = leitor.line_num
        t.linhas.append(linha)
    return t


def ler_numero(texto, *, inteiro: bool = False, avisos: list[str] | None = None, onde: str = ""):
    """Converte texto em número. Vazio ou inválido vira None (nunca zero)."""
    if texto is None:
        return None
    t = str(texto).strip().replace(" ", "").replace(" ", "")
    if t.lower() in VAZIOS:
        return None

    def problema(motivo: str):
        if avisos is not None:
            avisos.append(f"{onde}: '{texto}' {motivo}; tratado como não medido.")
        return None

    if inteiro and _RE_MILHAR_BR.match(t):
        t = t.replace(".", "")
    elif "," in t and "." not in t:
        t = t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return problema("não é um número")
    if v != v or v in (float("inf"), float("-inf")):
        return problema("não é um número")
    if v < 0:
        return problema("é negativo")
    if inteiro:
        if abs(v - round(v)) > 1e-9:
            return problema("não é um número inteiro")
        return int(round(v))
    return v


def ler_json_arquivo(caminho: Path):
    """Devolve (dados, erro). Erro é texto em português ou None."""
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return None, "o arquivo não existe"
    except json.JSONDecodeError as e:
        return None, f"não é um JSON válido (linha {e.lineno}, coluna {e.colno}): {e.msg}"
    except UnicodeDecodeError:
        return None, "o arquivo não está em UTF-8"


def _separadores_br(txt: str) -> str:
    return txt.replace(",", "\u0001").replace(".", ",").replace("\u0001", ".")


def _arredondar(v, casas: int) -> Decimal:
    d = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    return abs(d) if d == 0 else d


def fmt_int(v) -> str:
    if v is None:
        return NAO_MEDIDO
    return _separadores_br(f"{_arredondar(v, 0):,.0f}")


def fmt_dec(v, casas: int = 1) -> str:
    if v is None:
        return NAO_MEDIDO
    return _separadores_br(f"{_arredondar(v, casas):,.{casas}f}")


def fmt_pct(v, casas: int | None = None) -> str:
    """v em fração: 0,034 vira 3,4%."""
    if v is None:
        return NAO_MEDIDO
    p = v * 100
    if casas is None:
        casas = 0 if abs(p) >= 10 else (1 if abs(p) >= 1 else 2)
    return _separadores_br(f"{_arredondar(p, casas):,.{casas}f}") + "%"


def fmt_sinal(v, casas: int = 0) -> str:
    if v is None:
        return NAO_MEDIDO
    arred = _arredondar(v, casas)
    texto = _separadores_br(f"{abs(arred):,.{casas}f}")
    if arred == 0:
        return texto
    return ("+" if arred > 0 else "-") + texto


def fmt_data(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else NAO_MEDIDO


def fmt_data_curta(d: date | None) -> str:
    return d.strftime("%d/%m") if d else NAO_MEDIDO


def fmt_dias(n: int) -> str:
    if n <= 0:
        return "hoje"
    if n == 1:
        return "ontem"
    return f"há {n} dias"


def plural(n: int, singular: str, plural_: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural_ or singular + 's')}"
