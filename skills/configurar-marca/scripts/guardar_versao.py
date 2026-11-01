#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guarda a versão atual de arquivos da marca antes de mudá-los. Nada se apaga.

Copia cada arquivo para uma pasta _antes-<motivo>/ ao lado dele, com data e hora no nome. Rode antes de
reescrever um arquivo que já tem conteúdo aprovado pela pessoa (marca.md, regras.md, visual.json...).
Para só acrescentar uma linha ao feedback.md não precisa: use registrar_feedback.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _marca_comum as c  # noqa: E402


def montar_parser() -> c.ParserPT:
    parser = c.criar_parser(
        "guardar_versao.py",
        "Copia arquivos da marca para _antes-<motivo>/ (ao lado de cada um, com data e hora no nome) antes de "
        "mudá-los. Nada se apaga.",
        ["python -X utf8 skills/configurar-marca/scripts/guardar_versao.py --marca minha-marca --motivo ajuste-tom marca.md",
         "python -X utf8 skills/configurar-marca/scripts/guardar_versao.py --marca minha-marca --motivo novo-logo assets/logo/logo-fundo-claro.png"],
        "Saída: 0 = versões guardadas; 2 = marca, motivo ou arquivo inválido (nada é copiado).",
    )
    c.opcoes_marca_e_raiz(parser)
    parser.add_argument("--motivo", required=True, metavar="MOTIVO",
                        help="por que vai mudar, em poucas palavras com hífen (ex.: ajuste-tom, novo-logo). Vira o nome da pasta _antes-MOTIVO")
    parser.add_argument("arquivos", nargs="+", metavar="ARQUIVO", help="arquivos da marca, relativos à pasta dela (ex.: marca.md)")
    parser.add_argument("--simular", action="store_true", help="mostra o que seria copiado, sem copiar")
    return parser


def main(argv: list[str] | None = None) -> int:
    c.configurar_saida()
    args = montar_parser().parse_args(argv)
    raiz = c.pasta_raiz(args.raiz)
    try:
        slug, marca_dir = c.resolver_marca(raiz, args.marca)
        if not c.slug_valido(args.motivo):
            raise c.ErroUso(f"Motivo inválido: {args.motivo!r}. Use 2 a 40 caracteres: minúsculas, números e hífen (ex.: ajuste-tom).")
        origens = []
        for valor in args.arquivos:
            caminho, erro = c.caminho_dentro(marca_dir, valor)
            if erro:
                raise c.ErroUso(f"Arquivo {valor!r} inválido: {erro}.")
            if not caminho.is_file():
                raise c.ErroUso(f"O arquivo {valor!r} não existe na pasta da marca.")
            if any(parte.startswith("_antes-") for parte in caminho.relative_to(marca_dir.resolve()).parts):
                raise c.ErroUso(f"O arquivo {valor!r} já é uma versão guardada; guarde o arquivo original.")
            origens.append(caminho)
    except c.ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    verbo = "Seria guardado" if args.simular else "Guardado"
    for origem in origens:
        if args.simular:
            destino = origem.parent / f"_antes-{args.motivo}" / f"{origem.stem}.<data-hora>{origem.suffix}"
            print(f"{verbo}: {c.mostrar_caminho(origem, raiz)} -> {c.mostrar_caminho(destino, raiz)}")
        else:
            destino = c.guardar_versao(origem, args.motivo)
            print(f"{verbo}: {c.mostrar_caminho(origem, raiz)} -> {c.mostrar_caminho(destino, raiz)}")
    if args.simular:
        print("Simulação: nada foi copiado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
