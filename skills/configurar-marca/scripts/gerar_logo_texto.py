#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera um logo provisório só com o nome da marca, em texto, para quem ainda não tem logo.

Cria dois PNGs com fundo transparente nos caminhos que o visual.json indica (por padrão,
assets/logo/logo-fundo-claro.png e assets/logo/logo-fundo-escuro.png), usando as cores da marca.
É só o nome escrito: não é um logo desenhado. Quando a pessoa tiver o logo oficial, ela troca os dois
arquivos pelos dela.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _marca_comum as c  # noqa: E402

TAMANHO_INICIAL = 120
LARGURA_MAXIMA = 1200
COR_TEXTO_PADRAO = (28, 31, 34)
COR_DESTAQUE_PADRAO = (14, 116, 144)


def cor_do_visual(visual, chave: str, padrao):
    cores = visual.get("cores") if isinstance(visual, dict) else None
    valor = cores.get(chave) if isinstance(cores, dict) else None
    return c.hex_para_rgb(valor) if isinstance(valor, str) and c.RE_HEX.match(valor) else padrao


def escolher_fonte(texto: str, candidatas: list[str], tamanho: int):
    """Primeira fonte da lista que tem todos os caracteres do texto. Devolve (fonte, nome) ou (None, motivo)."""
    _, _, ImageFont = c.importar_pillow()
    for candidata in candidatas:
        try:
            fonte = ImageFont.truetype(candidata, tamanho)
        except OSError:
            continue
        if not c.glifos_ausentes(fonte, texto):
            return fonte, Path(candidata).name
    try:
        fonte = ImageFont.load_default(size=tamanho)  # Pillow 10.1 ou mais novo
        if not c.glifos_ausentes(fonte, texto):
            return fonte, "fonte padrão do Pillow"
    except (TypeError, OSError):
        pass
    return None, "nenhuma fonte encontrada tem todos os caracteres do nome"


def desenhar(texto: str, candidatas: list[str], cor_principal, cor_final):
    """Desenha o nome em uma linha. Se tiver mais de uma palavra, a última usa a cor_final."""
    Image, ImageDraw, _ = c.importar_pillow()
    tamanho = TAMANHO_INICIAL
    for _ in range(2):
        fonte, nome_fonte = escolher_fonte(texto, candidatas, tamanho)
        if fonte is None:
            return None, nome_fonte
        esq, topo, dir_, base = fonte.getbbox(texto)
        if dir_ - esq <= LARGURA_MAXIMA - 2 * (tamanho // 8):
            break
        tamanho = max(24, int(tamanho * (LARGURA_MAXIMA - 2 * (tamanho // 8)) / (dir_ - esq)))
    margem = max(8, tamanho // 8)
    imagem = Image.new("RGBA", (int(dir_ - esq) + 2 * margem, int(base - topo) + 2 * margem), (0, 0, 0, 0))
    pincel = ImageDraw.Draw(imagem)
    x, y = margem - esq, margem - topo
    palavras = texto.split()
    if len(palavras) >= 2:
        primeira = " ".join(palavras[:-1]) + " "
        pincel.text((x, y), primeira, font=fonte, fill=cor_principal + (255,))
        pincel.text((x + fonte.getlength(primeira), y), palavras[-1], font=fonte, fill=cor_final + (255,))
    else:
        pincel.text((x, y), texto, font=fonte, fill=cor_principal + (255,))
    return imagem, nome_fonte


def montar_parser() -> c.ParserPT:
    parser = c.criar_parser(
        "gerar_logo_texto.py",
        "Gera um logo provisório só com o nome da marca (dois PNGs com fundo transparente, para fundo claro e "
        "para fundo escuro). É só texto, não um logo desenhado: serve até a pessoa ter o logo oficial.",
        ["python -X utf8 skills/configurar-marca/scripts/gerar_logo_texto.py --marca minha-marca",
         "python -X utf8 skills/configurar-marca/scripts/gerar_logo_texto.py --marca minha-marca --texto \"Ana Souza\" --substituir"],
        "Saída: 0 = logos gerados; 1 = não deu para gerar (sem Pillow, sem fonte com os acentos...); "
        "2 = marca não encontrada ou logo já existente (use --substituir).",
    )
    c.opcoes_marca_e_raiz(parser)
    parser.add_argument("--texto", help="texto do logo (padrão: nome_exibicao do visual.json)")
    parser.add_argument("--fonte", metavar="ARQUIVO", help="arquivo de fonte .ttf ou .otf a usar (padrão: a fonte do visual.json, depois uma fonte do sistema)")
    parser.add_argument("--substituir", action="store_true",
                        help="troca logos que já existem (a versão anterior vai para _antes-logo-texto/)")
    parser.add_argument("--simular", action="store_true", help="mostra o que seria gerado, sem gravar nada")
    return parser


def main(argv: list[str] | None = None) -> int:
    c.configurar_saida()
    args = montar_parser().parse_args(argv)
    raiz = c.pasta_raiz(args.raiz)
    try:
        slug, marca_dir = c.resolver_marca(raiz, args.marca)
    except c.ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    if c.importar_pillow() is None:
        print(f"ERRO: {c.MSG_SEM_PILLOW}.", file=sys.stderr)
        return 1

    visual, erro = c.ler_json(marca_dir / "visual.json")
    if erro or not isinstance(visual, dict):
        print(f"ERRO: visual.json {erro or 'não é um objeto JSON'}. Corrija-o antes (validar_marca.py --so visual).", file=sys.stderr)
        return 1
    texto = (args.texto or visual.get("nome_exibicao") or "").strip()
    if not texto or "{{" in texto:
        print("ERRO: não há texto para o logo. Informe com --texto ou preencha nome_exibicao no visual.json.", file=sys.stderr)
        return 1

    logo = visual.get("logo") if isinstance(visual.get("logo"), dict) else {}
    destinos = {}
    for chave, padrao in (("fundo_claro", "assets/logo/logo-fundo-claro.png"), ("fundo_escuro", "assets/logo/logo-fundo-escuro.png")):
        caminho, erro = c.caminho_dentro(marca_dir, logo.get(chave) or padrao)
        if erro or caminho.suffix.lower() != ".png":
            print(f"ERRO: logo.{chave} do visual.json não serve para gravar o logo ({erro or 'precisa terminar em .png'}).", file=sys.stderr)
            return 1
        destinos[chave] = caminho
    existentes = [p for p in destinos.values() if p.exists()]
    if existentes and not args.substituir:
        nomes = ", ".join(c.mostrar_caminho(p, raiz) for p in existentes)
        print(f"ERRO: já existe logo em {nomes}. Nada foi alterado. Use --substituir para trocar "
              "(a versão atual vai para _antes-logo-texto/).", file=sys.stderr)
        return 2

    fundo_escuro = cor_do_visual(visual, "fundo_escuro", (20, 24, 28))
    cor_texto = cor_do_visual(visual, "texto", COR_TEXTO_PADRAO)
    cor_destaque = cor_do_visual(visual, "destaque", COR_DESTAQUE_PADRAO)
    cor_claro = cor_do_visual(visual, "texto_sobre_escuro", (255, 255, 255))
    versoes = {
        "fundo_claro": (cor_texto, cor_destaque),
        "fundo_escuro": (cor_claro, c.ajustar_contraste(cor_destaque, [fundo_escuro], 4.5)),
    }

    fontes_visual = visual.get("fontes") if isinstance(visual.get("fontes"), dict) else {}
    extras = [args.fonte]
    if isinstance(fontes_visual.get("titulo"), str):
        caminho_fonte, erro = c.caminho_dentro(marca_dir, fontes_visual["titulo"])
        if not erro and caminho_fonte.is_file():
            extras.append(str(caminho_fonte))
    candidatas = c.candidatas_de_fonte(extras, raiz)

    imagens = {}
    for chave, (principal, final) in versoes.items():
        imagem, nome_fonte = desenhar(texto, candidatas, principal, final)
        if imagem is None:
            print(f"ERRO: {nome_fonte}. Coloque uma fonte .ttf com acentos em assets/fontes/ e use --fonte, "
                  "ou instale uma fonte comum no computador.", file=sys.stderr)
            return 1
        imagens[chave] = imagem

    print(f"Marca: {slug} · texto do logo: {texto!r} · fonte: {nome_fonte}")
    for chave, caminho in destinos.items():
        largura, altura = imagens[chave].size
        print(f"  {c.mostrar_caminho(caminho, raiz)}  ({largura}x{altura} px, para {chave.replace('_', ' ')})")
    sem_bloco_de_logo = not isinstance(visual.get("logo"), dict)
    if sem_bloco_de_logo:
        print("  O campo logo do visual.json está vazio: ele será preenchido com estes dois arquivos.")
    if args.simular:
        print("Simulação: nada foi gravado.")
        return 0
    for chave, caminho in destinos.items():
        if caminho.exists():
            copia = c.guardar_versao(caminho, "logo-texto")
            print(f"  versão anterior guardada em {c.mostrar_caminho(copia, raiz)}")
        caminho.parent.mkdir(parents=True, exist_ok=True)
        imagens[chave].save(caminho, format="PNG")
    if sem_bloco_de_logo:
        arquivo_visual = marca_dir / "visual.json"
        copia = c.guardar_versao(arquivo_visual, "logo-texto")
        visual["logo"] = {"fundo_claro": destinos["fundo_claro"].relative_to(marca_dir.resolve()).as_posix(),
                          "fundo_escuro": destinos["fundo_escuro"].relative_to(marca_dir.resolve()).as_posix(),
                          "posicao": "superior-esquerda", "largura_px": 140}
        c.escrever_json(arquivo_visual, visual)
        print(f"  visual.json atualizado (versão anterior em {c.mostrar_caminho(copia, raiz)})")
    print("Logos provisórios gravados. É só o nome escrito: avise a pessoa e troque pelos arquivos oficiais quando ela tiver.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
