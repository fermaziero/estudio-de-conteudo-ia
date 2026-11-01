#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registra uma linha no feedback.md da marca: data, frase literal da pessoa, o que mudou e em qual arquivo.

Só acrescenta uma linha à tabela; não apaga nem reescreve as anteriores. Aplicar a regra no arquivo certo
(padrao-visual.md, regras.md, marca.md, visual.json...) é trabalho do agente, feito antes ou depois deste
registro. Este script cuida só do histórico, com a tabela sempre bem formada.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _marca_comum as c  # noqa: E402

SEM_ARQUIVO = "—"
LIMITE_ARQUIVO_DE_TEXTO = 10_000


def limpar_celula(texto: str) -> str:
    """Uma linha só, sem barra vertical solta (ela quebraria a tabela)."""
    return re.sub(r"\s*[\r\n]+\s*", " ", texto.strip()).replace("|", "\\|")


def com_aspas(frase: str) -> str:
    f = frase.strip()
    if len(f) > 1 and ((f[0] == '"' and f[-1] == '"') or (f[0] == "“" and f[-1] == "”")):
        return f
    return f'"{f}"'


def texto_do_argumento(valor: str | None, arquivo: str | None, rotulo: str, opcao: str) -> str:
    """Texto vindo direto da linha de comando ou de um arquivo UTF-8 (que protege o texto do terminal)."""
    if valor is not None and arquivo is not None:
        raise c.ErroUso(f"Use {opcao} ou {opcao}-arquivo, não os dois.")
    if arquivo is not None:
        caminho = Path(arquivo).expanduser()
        if caminho.is_file() and caminho.stat().st_size > LIMITE_ARQUIVO_DE_TEXTO:
            raise c.ErroUso(f"{arquivo} é grande demais para ser uma frase de feedback (limite de "
                            f"{LIMITE_ARQUIVO_DE_TEXTO // 1000} mil bytes). Use um arquivo só com a frase.")
        texto, erro = c.ler_texto(caminho)
        if erro:
            raise c.ErroUso(f"Não consegui ler {arquivo}: {erro}.")
    else:
        texto = valor
    if texto is None or not texto.strip():
        dica = " Copie o que ela disse, literalmente." if rotulo == "frase" else             " Se nada mudou nos arquivos, escreva, por exemplo, 'ajuste pontual no post; sem regra nova'."
        raise c.ErroUso(f"Falta o texto de {rotulo} (use {opcao} ou {opcao}-arquivo).{dica}")
    return texto.strip()


def montar_parser() -> c.ParserPT:
    parser = c.criar_parser(
        "registrar_feedback.py",
        "Acrescenta uma linha ao feedback.md da marca: data, frase literal da pessoa, o que mudou e o arquivo "
        "alterado. Não apaga nem reescreve as linhas anteriores.",
        ["python -X utf8 skills/configurar-marca/scripts/registrar_feedback.py --marca minha-marca "
         "--frase \"não gostei de capa com muito texto\" --mudou \"capa só com a chamada, até 12 palavras\" --arquivo padrao-visual.md",
         "python -X utf8 skills/configurar-marca/scripts/registrar_feedback.py --marca minha-marca "
         "--frase \"troca essa foto\" --mudou \"ajuste pontual no post; sem regra nova\" --simular",
         "python -X utf8 skills/configurar-marca/scripts/registrar_feedback.py --marca minha-marca "
         "--frase-arquivo frase.txt --mudou-arquivo mudou.txt --arquivo regras.md"],
        "Saída: 0 = registrado (ou simulado); 1 = o feedback.md não pôde ser lido ou gravado; "
        "2 = marca ou argumentos inválidos.",
    )
    c.opcoes_marca_e_raiz(parser)
    parser.add_argument("--frase", help="o que a pessoa disse, copiado literalmente (sem resumir nem corrigir)")
    parser.add_argument("--frase-arquivo", metavar="ARQUIVO",
                        help="em vez de --frase: arquivo de texto (UTF-8) com a frase. Use quando ela tiver aspas, $, crase, "
                             "barra invertida ou %%, para o terminal não alterar o texto")
    parser.add_argument("--mudou", help="o que mudou por causa do feedback, em uma frase")
    parser.add_argument("--mudou-arquivo", metavar="ARQUIVO", help="em vez de --mudou: arquivo de texto (UTF-8) com o texto")
    parser.add_argument("--arquivo", action="append", metavar="CAMINHO",
                        help="arquivo da marca em que a regra foi aplicada (relativo à pasta da marca). Pode repetir. "
                             "Sem este argumento, vale como ajuste pontual, sem arquivo de regra")
    parser.add_argument("--data", metavar="AAAA-MM-DD", help="data do feedback (padrão: hoje)")
    parser.add_argument("--simular", action="store_true", help="mostra a linha que seria registrada, sem gravar")
    return parser


def main(argv: list[str] | None = None) -> int:
    c.configurar_saida()
    args = montar_parser().parse_args(argv)
    raiz = c.pasta_raiz(args.raiz)
    try:
        slug, marca_dir = c.resolver_marca(raiz, args.marca)
        data = args.data or c.hoje()
        if not c.data_valida(data):
            raise c.ErroUso(f"Data inválida: {data!r}. Use AAAA-MM-DD.")
        frase = texto_do_argumento(args.frase, args.frase_arquivo, "frase", "--frase")
        mudou = texto_do_argumento(args.mudou, args.mudou_arquivo, "o que mudou", "--mudou")
        segredo = c.achar_segredo(frase) or c.achar_segredo(mudou)
        if segredo:
            raise c.ErroUso(f"O texto parece conter {segredo}. Nada foi registrado (e o valor não foi mostrado). "
                            "Peça à pessoa para trocar essa credencial e registre o feedback sem ela.")
        arquivos = []
        for valor in args.arquivo or []:
            caminho, erro = c.caminho_dentro(marca_dir, valor)
            if erro:
                raise c.ErroUso(f"Arquivo {valor!r} inválido: {erro}.")
            if not caminho.is_file():
                raise c.ErroUso(f"O arquivo {valor!r} não existe na pasta da marca. Aplique a regra nele antes de registrar, "
                                "ou omita --arquivo se foi só um ajuste pontual.")
            arquivos.append(caminho.relative_to(marca_dir.resolve()).as_posix())
    except c.ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    arquivo_feedback = marca_dir / "feedback.md"
    texto, erro = c.ler_texto(arquivo_feedback)
    if erro:
        print(f"ERRO: feedback.md: {erro}.", file=sys.stderr)
        return 1
    linhas = texto.split("\n")
    nova = "| {} | {} | {} | {} |".format(
        data, limpar_celula(com_aspas(frase)), limpar_celula(mudou),
        limpar_celula(", ".join(arquivos)) if arquivos else SEM_ARQUIVO)

    tabelas = [t for t in c.encontrar_tabelas(linhas) if c.eh_tabela_de_feedback(t)]
    if tabelas:
        anteriores = [cel[0] for _, cel in tabelas[0]["linhas"]
                      if len(cel) == 4 and c.normalizar(cel[1]) == c.normalizar(frase)]
        if anteriores:
            print(f"AVISO: a pessoa já disse isto antes (registrado em {', '.join(anteriores)}). Se a regra já existia, "
                  "ela não foi aplicada ou ficou vaga: reescreva-a de forma mais clara.")
        linhas.insert(tabelas[0]["fim"], nova)
    else:
        print("AVISO: não achei a tabela no feedback.md; criei uma nova no fim do arquivo.")
        while linhas and linhas[-1] == "":
            linhas.pop()
        linhas += ["", "| " + " | ".join(c.CABECALHO_FEEDBACK) + " |", "|---|---|---|---|", nova]
    resultado = "\n".join(linhas)
    if not resultado.endswith("\n"):
        resultado += "\n"

    mostrar = c.mostrar_caminho(arquivo_feedback, raiz)
    if args.simular:
        print(f"Simulação: nada foi gravado. Seria acrescentada em {mostrar}:")
        print(nova)
        return 0
    try:
        c.escrever_texto(arquivo_feedback, resultado)
    except OSError as e:
        print(f"ERRO: não consegui gravar {mostrar} ({e.strerror or e}).", file=sys.stderr)
        return 1
    print(f"Registrado em {mostrar} (marca {slug}):")
    print(nova)
    print("Confira se a regra também está no arquivo indicado e conte à pessoa, em poucas linhas, o que mudou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
