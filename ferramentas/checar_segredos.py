"""Procura segredos e dados pessoais antes de um commit ou de compartilhar o projeto.

Uso:
  python -X utf8 ferramentas/checar_segredos.py                    confere o que o git vai versionar
  python -X utf8 ferramentas/checar_segredos.py --tudo             confere todos os arquivos, inclusive marcas/
  python -X utf8 ferramentas/checar_segredos.py --termos lista.txt também procura estes termos (um por linha),
                                                                   por exemplo nomes de clientes
  python -X utf8 ferramentas/checar_segredos.py --estrito          trata avisos como erro

Saída 1 quando encontra algo grave. Para silenciar uma linha de documentação que
precisa mostrar um padrão, inclua nela o texto: checar-segredos: ignorar
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IGNORAR_LINHA = "checar-segredos: ignorar"
LIMITE_BYTES = 2 * 1024 * 1024
PASTAS_FORA = {".git", "__pycache__", ".venv", "venv", "node_modules"}

GRAVES = [
    ("token do Instagram", re.compile(r"\bIG(?:AA|QV)[A-Za-z0-9_\-]{20,}")),
    ("token da Meta/Facebook", re.compile(r"\bEAA[A-Za-z0-9]{30,}")),
    ("chave de acesso AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("token do GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("chave de API (sk-)", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("token do Slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("token Bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]{20,}=*")),
    ("id de conta", re.compile(r"(?i)(account[_-]?id|id[_-]?da[_-]?conta)[\"']?\s*[:=]\s*[\"']?[0-9a-f]{32}\b")),
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("CNPJ", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")),
]
ATRIBUICAO = re.compile(
    r"(?i)(?<![a-z])(token|secret|secreta|senha|password|api[_-]?key|chave[_-]?secreta|access[_-]?key|client[_-]?secret)"
    r"\w*[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+_\-.]{16,})"
)
PLACEHOLDER = re.compile(r"(?i)(exemplo|example|ficticio|fictício|seu|sua|cole|xxxx|\.\.\.|<|>|aqui|placeholder|fake|falso|teste)")
AVISOS = [
    ("e-mail", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("caminho com nome de usuário", re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s\"'<>]+|/Users/[^/\s\"'<>]+|/home/[^/\s\"'<>]+")),
    ("telefone", re.compile(r"\+55\s?\(?\d{2}\)?\s?9?\d{4}[\-\s]?\d{4}")),
]
EMAILS_OK = re.compile(r"(?i)@(example\.(com|org)|exemplo\.(com|com\.br)|users\.noreply\.github\.com)$|^noreply@|^nao-responda@")
CAMINHOS_OK = re.compile(r"(?i)\\Users\\(<|seu|sua|usuario|voce|você|%USERNAME%)|/(Users|home)/(<|seu|sua|usuario|voce|você|\$USER)")


def mascarar(valor):
    valor = valor.strip()
    if len(valor) <= 8:
        return valor[:2] + "…"
    return f"{valor[:4]}…({len(valor)} caracteres)"


def arquivos_para_checar(tudo):
    if not tudo:
        try:
            saida = subprocess.run(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                cwd=RAIZ, capture_output=True, check=True,
            ).stdout.decode("utf-8", "replace")
            return [RAIZ / nome for nome in saida.split("\0") if nome]
        except (OSError, subprocess.CalledProcessError):
            print("AVISO: git indisponível ou pasta sem repositório; conferindo todos os arquivos.")
    return [
        caminho for caminho in RAIZ.rglob("*")
        if caminho.is_file() and not any(parte in PASTAS_FORA for parte in caminho.relative_to(RAIZ).parts)
    ]


def ler_texto(caminho):
    try:
        if caminho.stat().st_size > LIMITE_BYTES:
            return None
        dados = caminho.read_bytes()
    except OSError:
        return None
    if b"\0" in dados[:8192]:
        return None
    return dados.decode("utf-8", "replace")


def checar_linha(linha, termos):
    achados = []
    for rotulo, padrao in GRAVES:
        for encontro in padrao.finditer(linha):
            achados.append(("GRAVE", rotulo, encontro.group(0)))
    for encontro in ATRIBUICAO.finditer(linha):
        valor = encontro.group(2)
        parece_segredo = re.search(r"\d", valor) and re.search(r"[A-Za-z]", valor) and len(set(valor)) > 4
        if parece_segredo and not PLACEHOLDER.search(valor):
            achados.append(("GRAVE", f"valor em '{encontro.group(1)}'", valor))
    for termo in termos:
        if termo.lower() in linha.lower():
            achados.append(("GRAVE", "termo da sua lista", termo))
    for rotulo, padrao in AVISOS:
        for encontro in padrao.finditer(linha):
            valor = encontro.group(0)
            if rotulo == "e-mail" and EMAILS_OK.search(valor):
                continue
            if rotulo == "caminho com nome de usuário" and CAMINHOS_OK.search(valor):
                continue
            achados.append(("AVISO", rotulo, valor))
    return achados


def main():
    parser = argparse.ArgumentParser(description="Procura segredos e dados pessoais nos arquivos do projeto.")
    parser.add_argument("--tudo", action="store_true", help="confere todos os arquivos, não só os que o git versiona")
    parser.add_argument("--termos", help="arquivo com termos extras para procurar, um por linha")
    parser.add_argument("--estrito", action="store_true", help="avisos também fazem a checagem falhar")
    args = parser.parse_args()

    termos = []
    if args.termos:
        lista = Path(args.termos)
        if not lista.is_file():
            print(f"ERRO: arquivo de termos não encontrado: {lista}")
            return 2
        termos = [t.strip() for t in lista.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]

    graves = avisos = conferidos = 0
    proprio = Path(__file__).resolve()
    for caminho in sorted(arquivos_para_checar(args.tudo)):
        if caminho.resolve() == proprio:
            continue
        texto = ler_texto(caminho)
        if texto is None:
            continue
        conferidos += 1
        relativo = caminho.relative_to(RAIZ).as_posix()
        for numero, linha in enumerate(texto.splitlines(), start=1):
            if IGNORAR_LINHA in linha:
                continue
            for nivel, rotulo, valor in checar_linha(linha, termos):
                print(f"{nivel}: {relativo}:{numero}: {rotulo}: {mascarar(valor)}")
                if nivel == "GRAVE":
                    graves += 1
                else:
                    avisos += 1

    print(f"\n{conferidos} arquivo(s) conferido(s): {graves} grave(s), {avisos} aviso(s).")
    if graves or (args.estrito and avisos):
        print("Corrija antes de commitar ou compartilhar. Credenciais ficam em ~/.config/estudio-de-conteudo/, nunca no projeto.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
