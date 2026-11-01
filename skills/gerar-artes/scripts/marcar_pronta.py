#!/usr/bin/env python3
"""Marca os posts como arte_pronta, depois que as artes foram geradas e conferidas com os olhos.

Só muda o status se as artes estão em ordem: existe um PNG para cada slide, o sha256 de cada PNG bate com o
manifesto e não há avisos de atenção pendentes. Registra o evento no historico do post.
Quem aprova a versão final é a pessoa, pela skill publicar-instagram; este script não aprova nada.

Uso (a partir da raiz do projeto):
    python -X utf8 skills/gerar-artes/scripts/marcar_pronta.py --marca minha-marca --lote 2026-11-03-semana-1 [--post ID] [--abrir]
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import galeria  # noqa: E402
from _comum import (  # noqa: E402
    ErroUsuario, ParserPT, adicionar_args_comuns, contexto_padrao, executar, gravar_json, listar_posts, registrar_historico,
    selecionar_ids, verificar_artes,
)


def problemas_das_artes(pasta_marca: Path, pasta_lote: Path, pid: str, post: dict, aceitar_avisos: bool) -> list[str]:
    """Tudo o que impede marcar o post como arte_pronta (arte faltando, desatualizada ou com aviso de atenção)."""
    verificacao = verificar_artes(pasta_marca, pasta_lote, pid, post)
    problemas = list(verificacao["gerais"])
    for n, itens in sorted(verificacao["slides"].items()):
        problemas += [f"slide {n}: {item}" for item in itens]
    if not aceitar_avisos:
        problemas += ["aviso pendente: " + str(a.get("mensagem")) for a in verificacao["atencao"]]
    return problemas


def principal() -> int:
    parser = ParserPT(description="Marca os posts como arte_pronta depois da conferência visual das artes.")
    adicionar_args_comuns(parser)
    parser.add_argument("--post", action="append", help="id do post (padrão: todos os posts do lote com status texto_aprovado ou erro)")
    parser.add_argument("--aceitar-avisos", action="store_true", help="marca mesmo com avisos de atenção (só se a pessoa já decidiu conviver com eles)")
    parser.add_argument("--abrir", action="store_true", help="abre a galeria no navegador ao terminar")
    args = parser.parse_args()

    _, slug_marca, pasta_marca, nome_lote, pasta_lote = contexto_padrao(args)
    posts = listar_posts(pasta_lote)
    ids = selecionar_ids(posts, args.post)
    marcados, falhas = [], 0
    for pid in ids:
        arquivo, post = posts[pid]
        status = post.get("status")
        if post.get("formato") == "reel":
            print(f"Pulado: {pid} (reel é só roteiro; não tem artes).")
            continue
        if status == "arte_pronta":
            print(f"{pid}: já está como arte_pronta.")
            continue
        if status not in ("texto_aprovado", "erro"):
            mensagem = f"{pid}: status '{status}'; só posts com texto_aprovado (ou com erro de publicação, depois de refazer a arte) viram arte_pronta."
            if args.post:
                raise ErroUsuario(mensagem)
            print("Pulado: " + mensagem)
            continue
        problemas = problemas_das_artes(pasta_marca, pasta_lote, pid, post, args.aceitar_avisos)
        if problemas:
            falhas += 1
            print(f"NÃO MARCADO  {pid}")
            for problema in problemas:
                print(f"  - {problema}")
            continue
        post["status"] = "arte_pronta"
        registrar_historico(post, f"artes conferidas e prontas para a aprovação da pessoa ({len(post.get('slides') or [])} slide(s))")
        gravar_json(arquivo, post)
        marcados.append(pid)
        print(f"OK  {pid}: status arte_pronta.")
    destino = galeria.gerar(pasta_marca, slug_marca, nome_lote, pasta_lote)
    print(f"Galeria atualizada: {destino}")
    if args.abrir:
        webbrowser.open(destino.as_uri())
    if not marcados and not falhas:
        print("Nenhum post foi alterado.")
    return 2 if falhas else 0


if __name__ == "__main__":
    executar(principal)
