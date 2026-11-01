"""Funções compartilhadas pelos scripts da skill pesquisar-referencias."""
import argparse
import csv
import io
import math
import os
import re
import sys
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

COLUNAS_CSV = ["perfil", "nicho", "tipo", "data", "seguidores", "posts_semana",
               "mediana_views", "pct_cta", "alavanca"]
TIPOS = ("pessoal", "marca")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HANDLE = re.compile(r"[a-z0-9._]{1,30}")
NAO_MEDIDO = {"", "naomedido", "nd", "n/d", "na", "n/a", "-", "—", "–"}
MULTIPLICADOR = {"mil": 1e3, "k": 1e3, "mi": 1e6, "m": 1e6, "milhao": 1e6, "milhoes": 1e6,
                 "bi": 1e9, "b": 1e9}
PAGINAS_NAO_PERFIL = {"p", "reel", "reels", "tv", "stories", "explore", "accounts", "direct"}


class ErroUso(Exception):
    pass


class ErroDados(Exception):
    pass


def configurar_saida():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


TRADUCOES_ARGPARSE = [
    ("the following arguments are required:", "faltam estes argumentos obrigatórios:"),
    ("unrecognized arguments:", "argumentos não reconhecidos:"),
    ("expected one argument", "falta o valor depois da opção"),
    ("ambiguous option:", "opção ambígua:"),
]


class _Formatador(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        for original, traducao in TRADUCOES_ARGPARSE:
            message = message.replace(original, traducao)
        if "--perfil" in message:
            message += ('. No PowerShell, o @ precisa de aspas: --perfil "@handle". '
                        "Também vale escrever o handle sem o @")
        self.print_usage(sys.stderr)
        self.exit(2, f"Erro: {message}\n")


def criar_parser(descricao):
    p = _Parser(description=descricao, formatter_class=_Formatador, add_help=False)
    try:
        p._optionals.title = "opções"
    except AttributeError:
        pass
    p.add_argument("-h", "--help", action="help", help="mostra esta ajuda e sai")
    return p


def sem_acento(texto):
    base = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in base if not unicodedata.combining(c))


def chave(texto):
    return re.sub(r"\s+", " ", sem_acento(texto).lower()).strip()


def normalizar_handle(texto):
    t = (texto or "").strip()
    achado = re.search(r"instagram\.com/([^/?#\s]+)", t, re.I)
    if achado:
        h = achado.group(1)
        if h.lower() in PAGINAS_NAO_PERFIL:
            raise ErroDados("o link é de um post ou de outra página do Instagram, não de um "
                            "perfil; passe o @ do perfil ou o link do perfil")
    else:
        h = t
    h = h.strip().lstrip("@").rstrip("/").lower()
    if not HANDLE.fullmatch(h):
        raise ErroDados(f"perfil inválido: {texto!r} (use letras, números, ponto e sublinhado)")
    return h


def normalizar_nicho(texto):
    n = re.sub(r"[^a-z0-9]+", "-", sem_acento(texto or "").lower()).strip("-")
    if not SLUG.fullmatch(n):
        raise ErroDados(f"nicho inválido: {texto!r} (um rótulo curto, como nutricao ou financas)")
    return n


def ler_numero(texto):
    """Converte '100 mil', '1,5 mi', '9.000', '4,5' ou '50%' em float; 'não medido' vira None."""
    s = re.sub(r"\s+", "", sem_acento("" if texto is None else str(texto)).lower().replace("%", ""))
    if s in NAO_MEDIDO:
        return None
    achado = re.fullmatch(r"([\d.,]+)(milhoes|milhao|mil|mi|bi|k|m|b)?", s)
    if not achado:
        raise ErroDados(f"número não reconhecido: {texto!r}")
    corpo, sufixo = achado.groups()
    if "," in corpo and "." in corpo:
        if corpo.rfind(",") > corpo.rfind("."):
            corpo = corpo.replace(".", "").replace(",", ".")
        else:
            corpo = corpo.replace(",", "")
    elif "," in corpo:
        corpo = corpo.replace(",", ".")
    elif sufixo is None and re.fullmatch(r"\d{1,3}(\.\d{3})+", corpo):
        corpo = corpo.replace(".", "")
    try:
        valor = float(corpo)
    except ValueError:
        raise ErroDados(f"número não reconhecido: {texto!r}")
    return valor * MULTIPLICADOR.get(sufixo, 1)


def arredondar(valor):
    return None if valor is None else int(math.floor(valor + 0.5))


def formatar_decimal(valor, casas=1):
    """Texto com até `casas` casas decimais e ponto: 7.5, 8 (nunca 8.0). Meio arredonda para cima."""
    d = Decimal(str(valor)).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    texto = format(d, "f")
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


def raiz_projeto(arg=None):
    if arg:
        pasta = Path(arg).expanduser().resolve()
        if not (pasta / "marcas").is_dir():
            raise ErroUso(f"não achei a pasta marcas/ dentro de {pasta}")
        return pasta
    atual = Path.cwd()
    if (atual / "marcas").is_dir():
        return atual
    aqui = Path(__file__).resolve().parents[3]
    if (aqui / "marcas").is_dir():
        return aqui
    raise ErroUso("não achei a pasta marcas/. Rode o comando a partir da raiz do projeto.")


def listar_marcas(raiz):
    pasta = raiz / "marcas"
    if not pasta.is_dir():
        return []
    return sorted(p.name for p in pasta.iterdir() if p.is_dir() and SLUG.fullmatch(p.name))


def resolver_marca(raiz, marca=None):
    todas = listar_marcas(raiz)
    if marca:
        if marca not in todas:
            opcoes = ", ".join(todas) or "nenhuma"
            raise ErroUso(f"marca {marca!r} não existe em marcas/. Opções: {opcoes}")
        return marca
    reais = [m for m in todas if m != "exemplo"]
    if len(reais) == 1:
        return reais[0]
    if not reais:
        raise ErroUso("nenhuma marca encontrada além de 'exemplo'. Rode a skill configurar-marca "
                      "ou use --marca exemplo para testar.")
    raise ErroUso("há várias marcas: " + ", ".join(reais) + ". Use --marca <slug>.")


MSG_TRAVADO_GRAVAR = ("não consegui gravar {nome}: o arquivo está aberto em outro programa "
                      "(provavelmente o Excel) ou sem permissão de escrita. Feche o arquivo no Excel "
                      "e rode de novo. Nada foi alterado")
MSG_TRAVADO_LER = ("não consegui ler {nome}: o arquivo está bloqueado por outro programa "
                   "(provavelmente o Excel). Feche o arquivo no Excel e rode de novo")


def nome_coluna(nome):
    original = (nome or "").strip()
    padrao = re.sub(r"[\s-]+", "_", original.lower())
    return padrao if padrao in COLUNAS_CSV else original


def ler_csv(caminho):
    """Lê um CSV do projeto e devolve (colunas, linhas, notas).

    Aceita vírgula, ponto e vírgula (Excel em português) ou tabulação, com BOM, em UTF-8 ou
    ANSI, e cabeçalho com maiúsculas. As colunas do contrato voltam em minúsculas; linhas
    em branco são ignoradas. As notas dizem o que foi preciso ajustar na leitura.
    """
    if not caminho.exists():
        return [], [], []
    try:
        bruto = caminho.read_bytes()
    except PermissionError:
        raise ErroDados(MSG_TRAVADO_LER.format(nome=caminho.name))
    notas = []
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texto = bruto.decode("cp1252")
        except UnicodeDecodeError:
            raise ErroDados(f"{caminho.name} não está em UTF-8 nem em ANSI. Salve como CSV UTF-8 "
                            "no Excel e rode de novo")
        notas.append(f"{caminho.name} estava em ANSI (Excel); gravei de volta em UTF-8.")
    linhas_texto = texto.splitlines()
    separador = None
    if linhas_texto and re.fullmatch(r"sep=.", linhas_texto[0], re.I):
        separador = linhas_texto[0][-1]
        texto = "\n".join(linhas_texto[1:])
    primeira = next((l for l in texto.splitlines() if l.strip()), "")
    if separador is None:
        contagens = {s: primeira.count(s) for s in (",", ";", "\t")}
        separador = max(contagens, key=contagens.get) if any(contagens.values()) else ","
    if separador != ",":
        nome_sep = "tabulação" if separador == "\t" else "ponto e vírgula"
        notas.append(f"{caminho.name} estava separado por {nome_sep} (Excel em português); gravei "
                     "de volta com vírgula, como o projeto espera.")
    celulas = [r for r in csv.reader(io.StringIO(texto, newline=""), delimiter=separador)
               if any(x.strip() for x in r)]
    if not celulas:
        return [], [], notas
    validos = [(i, n) for i, n in ((i, nome_coluna(h)) for i, h in enumerate(celulas[0])) if n]
    linhas = [{n: (r[i].strip() if i < len(r) else "") for i, n in validos} for r in celulas[1:]]
    return [n for _, n in validos], linhas, notas


def gravar_csv(caminho, campos, linhas):
    """Grava via arquivo temporário e troca no fim; limpa o temporário e explica se o arquivo estiver travado."""
    temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with temporario.open("w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=campos, lineterminator="\n", extrasaction="ignore")
            escritor.writeheader()
            for linha in linhas:
                escritor.writerow({x: linha.get(x, "") for x in campos})
        os.replace(temporario, caminho)
    except PermissionError:
        raise ErroDados(MSG_TRAVADO_GRAVAR.format(nome=caminho.name))
    except OSError as e:
        raise ErroDados(f"não consegui gravar {caminho.name}: {e.strerror or e}. Nada foi alterado")
    finally:
        try:
            temporario.unlink()
        except OSError:
            pass
