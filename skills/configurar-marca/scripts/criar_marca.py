#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cria a pasta de uma marca nova (marcas/<slug>/) a partir dos modelos da skill configurar-marca.

Cria os seis arquivos da marca (marca.md, regras.md, padrao-visual.md, visual.json, estrategia.json e
feedback.md) e as pastas assets/logo, assets/fotos e assets/fontes. Os campos que ainda precisam da
entrevista ficam marcados com [PREENCHER]. Não sobrescreve nada: se a marca já existe, para.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _marca_comum as c  # noqa: E402

ARQUIVOS_DA_MARCA = ["marca.md", "regras.md", "padrao-visual.md", "visual.json", "estrategia.json", "feedback.md"]
PASTAS_DE_ASSETS = ["assets/logo", "assets/fotos", "assets/fontes"]


def nome_padrao(slug: str) -> str:
    return slug.replace("-", " ").title()


def normalizar_arroba(valor: str | None) -> str:
    if not valor or not valor.strip():
        return ""
    arroba = "@" + valor.strip().lstrip("@")
    if not c.RE_ARROBA.match(arroba):
        raise c.ErroUso(f"@ inválido: {valor!r}. Use letras, números, ponto ou sublinhado, com até 30 caracteres.")
    return arroba


def preencher(texto: str, valores: dict[str, str], json_: bool) -> str:
    for chave, valor in valores.items():
        if json_:
            valor = json.dumps(valor, ensure_ascii=False)[1:-1]  # escapa aspas e barras para caber num JSON
        texto = texto.replace("{{" + chave + "}}", valor)
    return texto


def montar_parser() -> c.ParserPT:
    parser = c.criar_parser(
        "criar_marca.py",
        "Cria marcas/<slug>/ a partir dos modelos da skill configurar-marca, com os seis arquivos da marca "
        "e as pastas de assets. Não sobrescreve nada.",
        ["python -X utf8 skills/configurar-marca/scripts/criar_marca.py --marca ana-souza --nome \"Ana Souza\" --arroba \"@ana.souza\"",
         "python -X utf8 skills/configurar-marca/scripts/criar_marca.py --marca ana-souza --simular"],
        "Saída: 0 = marca criada; 2 = nome inválido ou marca já existente.",
    )
    parser.add_argument("--marca", required=True, metavar="SLUG",
                        help="nome da pasta: minúsculas, números e hífen (ex.: ana-souza)")
    parser.add_argument("--nome", help="nome que aparece nos arquivos e nas artes (padrão: derivado do SLUG)")
    parser.add_argument("--arroba", help="@ do Instagram, entre aspas (\"@perfil\") ou sem o @; pode ficar vazio por enquanto")
    parser.add_argument("--raiz", metavar="PASTA",
                        help="avançado: pasta raiz do projeto (por padrão, a pasta onde este script está instalado)")
    parser.add_argument("--simular", action="store_true", help="mostra o que seria criado, sem criar nada")
    return parser


def main(argv: list[str] | None = None) -> int:
    c.configurar_saida()
    args = montar_parser().parse_args(argv)
    try:
        slug = args.marca
        if not c.slug_valido(slug):
            raise c.ErroUso(f"Nome de marca inválido: {slug!r}. Use de 2 a 40 caracteres: minúsculas, números e hífen "
                            "(sem espaço, acento ou hífen no começo e no fim). Exemplo: ana-souza.")
        if slug == c.MARCA_EXEMPLO:
            raise c.ErroUso("'exemplo' é o nome da marca fictícia que acompanha o projeto. Escolha outro nome.")
        raiz = c.pasta_raiz(args.raiz)
        destino = raiz / "marcas" / slug
        if destino.exists():
            raise c.ErroUso(f"A marca '{slug}' já existe em {c.mostrar_caminho(destino, raiz)}. Nada foi alterado. "
                            "Para continuar a configuração, edite os arquivos dela; para outra marca, escolha outro nome.")
        arroba = normalizar_arroba(args.arroba)
        nome = (args.nome or "").strip() or nome_padrao(slug)
        valores = {"NOME": nome, "SLUG": slug, "ARROBA": arroba, "DATA": c.hoje()}

        modelos = {}
        for arquivo in ARQUIVOS_DA_MARCA + ["assets-leia-me.md"]:
            texto, erro = c.ler_texto(c.PASTA_MODELOS / arquivo)
            if erro:
                raise c.ErroUso(f"Modelo {arquivo} não pôde ser lido ({erro}). A instalação da skill está incompleta.")
            modelos[arquivo] = preencher(texto, valores, arquivo.endswith(".json"))
    except c.ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    mostrar = c.mostrar_caminho(destino, raiz)
    if args.simular:
        print(f"Simulação: nada foi criado. Seria criada a marca '{slug}' em {mostrar}/ com:")
    else:
        for arquivo in ARQUIVOS_DA_MARCA:
            c.escrever_texto(destino / arquivo, modelos[arquivo])
        for pasta in PASTAS_DE_ASSETS:
            (destino / pasta).mkdir(parents=True, exist_ok=True)
        c.escrever_texto(destino / "assets" / "LEIA-ME.md", modelos["assets-leia-me.md"])
        print(f"Marca '{slug}' criada em {mostrar}/ com:")
    for arquivo in ARQUIVOS_DA_MARCA:
        print(f"  {arquivo}")
    for pasta in PASTAS_DE_ASSETS:
        print(f"  {pasta}/")
    print("  assets/LEIA-ME.md")
    print("Campos que ainda precisam da entrevista estão marcados com [PREENCHER].")
    return 0


if __name__ == "__main__":
    sys.exit(main())
