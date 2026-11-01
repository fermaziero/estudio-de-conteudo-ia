#!/usr/bin/env python3
"""Imagens geradas por IA para as artes: escreve os prompts e importa o resultado.

A IA só faz a imagem (sem texto, sem logo, sem rosto de pessoa real). O texto, as cores e o logo da marca
são colocados depois pelo renderizar.py.

Comandos (a partir da raiz do projeto):
    python -X utf8 skills/gerar-artes/scripts/imagens.py prompts  --marca M --lote L [--post ID] [--todos]
    python -X utf8 skills/gerar-artes/scripts/imagens.py importar --marca M --lote L --post ID --slide N ARQUIVO [--foco "0.5 0.4"]

prompts   escreve artes/<id>/imagens/prompts.md com um prompt para cada slide que precisa de imagem gerada.
importar  copia a imagem que a ferramenta gerou para artes/<id>/imagens/ e recorta para a área do layout.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageOps  # noqa: E402

from _comum import (  # noqa: E402
    ErroUsuario, ParserPT, adicionar_args_comuns, carregar_visual, contexto_padrao, executar, gravar_json, hoje, invalidar_aprovacao,
    listar_posts, pode_gerar, proporcao_do_post, registrar_historico, rgb_hex, selecionar_ids, slug,
)
from _layouts import Contexto, ErroSlide, ImagemSlide, renderizar_slide  # noqa: E402
from renderizar import interpretar_foco, ler_ajustes, caminho_ajustes, resolver_imagem  # noqa: E402

RAZOES = {"1:1": 1.0, "4:5": 0.8, "3:4": 0.75, "2:3": 2 / 3, "9:16": 9 / 16, "5:4": 1.25, "4:3": 4 / 3, "3:2": 1.5, "16:9": 16 / 9}
REGRAS_FIXAS = (
    "Sem nenhum texto na imagem: nada de letras, palavras, números, legendas, marcas d'água ou telas com texto legível. "
    "Sem logotipos nem marcas de empresas. "
    "Sem rostos de pessoas reais ou reconhecíveis (se a cena precisar de pessoas, mostre só mãos, silhuetas ou pessoas de costas, sem identificar ninguém). "
    "Sem ícones, pictogramas, setas, ilustração plana ou vetor: a imagem é realista."
)


def aspecto_proximo(largura: float, altura: float) -> str:
    alvo = largura / altura
    return min(RAZOES, key=lambda nome: abs(math.log(alvo / RAZOES[nome])))


def orientacao(largura: float, altura: float) -> str:
    razao = RAZOES[aspecto_proximo(largura, altura)]
    return "horizontal" if razao > 1.02 else ("vertical" if razao < 0.98 else "quadrada")


def area_da_imagem(cfg: dict, contextos: dict, post: dict, slide: dict, ajuste: dict):
    """Descobre a área que a imagem ocupa no layout. Devolve (área [x,y,w,h], variante, aviso|None)."""
    proporcao = proporcao_do_post(post, cfg)
    if proporcao not in contextos:
        contextos[proporcao] = Contexto(cfg, proporcao)
    ctx = contextos[proporcao]
    previsto = ImagemSlide(None, "gerada", str((slide.get("imagem") or {}).get("descricao") or ""))
    try:
        _, meta, _ = renderizar_slide(ctx, slide, len(post["slides"]), ajuste, previsto, reservar=True)
    except ErroSlide as erro:
        return [0, 0, ctx.W, ctx.H], None, f"Não consegui calcular a área exata ({erro.mensagem}). Usei a arte inteira como referência."
    area = meta.get("area_imagem")
    if not area:
        return None, None, f"O layout '{slide.get('layout')}' não usa imagem."
    return area, meta.get("variante"), None


def montar_prompt(cfg: dict, slide: dict, area: list[int], variante: str | None) -> str:
    imagem = slide.get("imagem") or {}
    o_que = str(imagem.get("descricao") or "").strip() or f"uma imagem que ilustre a ideia: {str(slide.get('titulo', '')).strip()}"
    detalhes = re.sub(r"(?is)\s*sem\s+texto[^.]*\.?\s*$", "", str(imagem.get("prompt") or "")).strip()
    c = cfg["cores"]
    paleta = f"{rgb_hex(c['destaque'])} (cor de destaque), {rgb_hex(c['fundo_escuro'])} (tom escuro) e {rgb_hex(c['fundo'])} (tom claro)"
    largura, altura = area[2], area[3]
    formato = f"{orientacao(largura, altura)}, proporção {aspecto_proximo(largura, altura)}"
    partes = [f"Crie uma imagem realista (fotografia ou render 3D fotorrealista, bem produzida) de: {o_que.rstrip('.')}."]
    if detalhes:
        partes.append(f"Detalhes da cena: {detalhes.rstrip('.')}.")
    partes.append("Estilo: iluminação suave de estúdio, profundidade, materiais e texturas reais, acabamento sofisticado e sóbrio, com bastante espaço livre ao redor do assunto.")
    partes.append(f"Paleta: tons próximos de {paleta}.")
    if slide.get("layout") == "capa" and variante == "degrade":
        partes.append("Composição: assunto principal na metade de cima; deixe o terço de baixo mais simples e escuro, sem detalhes importantes, porque o título será colocado ali depois.")
    else:
        partes.append("Composição: assunto principal no centro, com folga nas bordas, porque a imagem será recortada para caber no layout.")
    partes.append(f"Formato: {formato}.")
    partes.append(REGRAS_FIXAS)
    return " ".join(partes)


def blocos_de_prompt(cfg, contextos, pasta_marca, pasta_lote, slug_marca, nome_lote, pid, post, ajustes, todos):
    saida, notas = [], []
    for slide in sorted(post.get("slides") or [], key=lambda s: s.get("n", 0)):
        imagem = slide.get("imagem")
        if not isinstance(imagem, dict) or not imagem:
            continue
        n = slide["n"]
        if imagem.get("tipo") == "foto":
            existente = resolver_imagem(slide, pasta_marca, pasta_lote, pid)
            if existente is None or existente.caminho is None:
                notas.append(f"Slide {n} usa uma foto aprovada que não foi encontrada ({imagem.get('arquivo') or 'sem arquivo'}). Coloque a foto em assets/fotos/ e aponte no post; não gere foto de pessoa com IA.")
            continue
        pronta = resolver_imagem(slide, pasta_marca, pasta_lote, pid)
        if pronta is not None and pronta.caminho is not None and not todos:
            notas.append(f"Slide {n}: já tem imagem ({pronta.origem}); use --todos para escrever o prompt de novo.")
            continue
        area, variante, aviso_area = area_da_imagem(cfg, contextos, post, slide, ajustes["slides"].get(str(n), {}))
        if area is None:
            notas.append(f"Slide {n}: {aviso_area}")
            continue
        if aviso_area:
            notas.append(f"Slide {n}: {aviso_area}")
        saida.append({"n": n, "slide": slide, "area": area, "variante": variante,
                      "prompt": montar_prompt(cfg, slide, area, variante)})
    return saida, notas


def escrever_prompts(pasta_lote: Path, slug_marca: str, nome_lote: str, pid: str, post: dict, itens: list[dict]) -> Path:
    pasta = pasta_lote / "artes" / pid / "imagens"
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"# Prompts de imagem: {post.get('titulo_interno') or pid}", "",
        f"- Post: `{pid}` | Lote: `{nome_lote}` | Prompts de {hoje()}",
        "- Use a ferramenta de imagem que você tiver (ChatGPT, Gemini, Codex...). Gere uma imagem por prompt e salve o arquivo no computador.",
        "- A IA só cria a imagem. O texto, as cores e o logo da marca são colocados depois pelo código; por isso a imagem não pode ter texto nem logo.",
        "- Se a ferramenta funcionar melhor em inglês, peça ao agente para traduzir o prompt, mantendo todas as proibições.",
        "- Em um mesmo lote, cada imagem deve mostrar uma cena ou um objeto diferente.", "",
        "## Antes de importar, confira cada imagem", "",
        "- Nenhuma letra, número ou palavra (nem em telas, placas, papéis ou rótulos).",
        "- Nenhum logotipo, nem de outras empresas.",
        "- Nenhum rosto de pessoa real ou reconhecível.",
        "- O assunto principal está longe das bordas (a imagem será recortada).", "",
    ]
    for item in itens:
        slide, area = item["slide"], item["area"]
        papel = f"{slide.get('layout')}" + (f", variante {item['variante']}" if item["variante"] else "")
        linhas += [
            f"## Slide {item['n']} ({papel})", "",
            f"- Área da imagem na arte: {area[2]} x {area[3]} px (proporção {aspecto_proximo(area[2], area[3])}, {orientacao(area[2], area[3])}).",
            "- Peça à ferramenta a proporção mais próxima que ela oferecer; o importador recorta o resto.",
            f"- Importar: `python -X utf8 skills/gerar-artes/scripts/imagens.py importar --marca {slug_marca} --lote {nome_lote} --post {pid} --slide {item['n']} CAMINHO_DA_IMAGEM`",
            "", "```text", item["prompt"], "```", "",
        ]
    destino = pasta / "prompts.md"
    novo = "\n".join(linhas) + "\n"
    if destino.is_file() and destino.read_text(encoding="utf-8") != novo:
        backup = pasta / f"_antes-prompts-{hoje()}"
        k = 2
        while backup.exists():
            backup = pasta / f"_antes-prompts-{hoje()}-{k}"
            k += 1
        backup.mkdir()
        shutil.move(str(destino), str(backup / "prompts.md"))
    destino.write_text(novo, encoding="utf-8")
    return destino


def comando_prompts(args) -> int:
    _, slug_marca, pasta_marca, nome_lote, pasta_lote = contexto_padrao(args)
    cfg = carregar_visual(pasta_marca)
    posts = listar_posts(pasta_lote)
    ids = selecionar_ids(posts, args.post)
    contextos: dict = {}
    total = 0
    for pid in ids:
        arquivo, post = posts[pid]
        ok, motivo = pode_gerar(post.get("status") or "rascunho", post.get("formato"))
        if not ok:
            if args.post:
                raise ErroUsuario(f"Post '{pid}': {motivo}.")
            continue
        ajustes = ler_ajustes(pasta_lote / "artes" / pid)
        itens, notas = blocos_de_prompt(cfg, contextos, pasta_marca, pasta_lote, slug_marca, nome_lote, pid, post, ajustes, args.todos)
        for nota in notas:
            print(f"  {pid}: {nota}")
        if itens:
            destino = escrever_prompts(pasta_lote, slug_marca, nome_lote, pid, post, itens)
            total += len(itens)
            print(f"{pid}: {len(itens)} prompt(s) em {destino.relative_to(pasta_lote).as_posix()}")
    if not total:
        print("Nenhum slide precisa de prompt de imagem agora.")
    return 0


# ---------------------------------------------------------------- importar

def cortar_para_area(origem: Path, area: list[int], foco: tuple[float, float]) -> Image.Image:
    try:
        with Image.open(origem) as arquivo:
            arquivo.load()
            img = ImageOps.exif_transpose(arquivo).convert("RGB")
    except Exception as erro:
        raise ErroUsuario(f"Não consegui abrir a imagem {origem.name}: {erro}. Use PNG, JPG ou WebP.")
    largura, altura = area[2], area[3]
    alvo = largura / altura
    iw, ih = img.size
    cw, ch = (ih * alvo, float(ih)) if iw / ih > alvo else (float(iw), iw / alvo)
    esquerda = min(max(foco[0] * iw - cw / 2, 0), iw - cw)
    topo = min(max(foco[1] * ih - ch / 2, 0), ih - ch)
    lado = min(2.0, cw / largura)
    destino = (max(1, round(largura * lado)), max(1, round(altura * lado)))
    return img.resize(destino, Image.Resampling.LANCZOS, box=(esquerda, topo, esquerda + cw, topo + ch), reducing_gap=2.0)


def comando_importar(args) -> int:
    _, slug_marca, pasta_marca, nome_lote, pasta_lote = contexto_padrao(args)
    cfg = carregar_visual(pasta_marca)
    posts = listar_posts(pasta_lote)
    pid = selecionar_ids(posts, [args.post])[0]
    arquivo_post, post = posts[pid]
    ok, motivo_recusa = pode_gerar(post.get("status") or "rascunho", post.get("formato"))
    if not ok:
        raise ErroUsuario(f"Post '{pid}': {motivo_recusa}.")
    if post.get("status") in ("aprovado", "agendado") and not args.refazer_aprovado:
        raise ErroUsuario(f"Post '{pid}': já foi aprovado/agendado; trocar a imagem invalida a aprovação. Se a pessoa pediu mesmo, rode de novo com --refazer-aprovado.")
    slide = next((s for s in post.get("slides") or [] if s.get("n") == args.slide), None)
    if slide is None:
        raise ErroUsuario(f"O post '{pid}' não tem o slide {args.slide}.")
    imagem = slide.get("imagem")
    if not isinstance(imagem, dict) or not imagem:
        raise ErroUsuario(f"O slide {args.slide} não tem o objeto 'imagem' no post. Peça ao criar-conteudo para descrever a imagem antes.")
    if imagem.get("tipo") == "foto":
        raise ErroUsuario(f"O slide {args.slide} usa uma foto aprovada, não uma imagem gerada. Coloque a foto em assets/fotos/ e aponte para ela no post.")
    origem = Path(args.arquivo).expanduser()
    if not origem.is_file():
        raise ErroUsuario(f"Arquivo não encontrado: {origem}")

    ajustes = ler_ajustes(pasta_lote / "artes" / pid)
    ajuste = ajustes["slides"].get(str(args.slide), {})
    foco = interpretar_foco(args.foco) if args.foco else None
    area, variante, aviso_area = area_da_imagem(cfg, {}, post, slide, ajuste)
    if area is None:
        raise ErroUsuario(aviso_area or "Este layout não usa imagem.")
    if aviso_area:
        print(f"Aviso: {aviso_area}")
    foco_usado = tuple(foco) if foco else tuple(ajuste.get("foco") or (0.5, 0.5))

    pasta = pasta_lote / "artes" / pid / "imagens"
    nome = f"slide-{args.slide:02d}"
    final, copia = pasta / f"{nome}.png", pasta / f"{nome}-original{origem.suffix.lower() or '.png'}"
    ja_e_original = origem.resolve() == copia.resolve()
    # 1) valida e recorta sem mexer em nada: se a imagem for inválida, a anterior continua no lugar
    cortada = cortar_para_area(origem, area, foco_usado)
    pasta.mkdir(parents=True, exist_ok=True)
    temporarios = [final.with_name(f".{final.name}.{os.getpid()}.tmp")]
    if not ja_e_original:
        temporarios.append(copia.with_name(f".{copia.name}.{os.getpid()}.tmp"))
    try:
        cortada.save(temporarios[0], format="PNG")
        if not ja_e_original:
            shutil.copy2(origem, temporarios[1])
    except Exception:
        for temporario in temporarios:
            temporario.unlink(missing_ok=True)
        raise
    # 2) só agora a versão anterior é guardada e a nova entra no lugar
    antigos = [final] if ja_e_original else [final, *pasta.glob(f"{nome}-original.*")]
    antigos = [velho for velho in antigos if velho.exists()]
    if antigos:
        motivo = slug(args.motivo or ("novo-enquadramento" if ja_e_original else "nova-imagem"))
        backup = pasta / f"_antes-{motivo}-{nome}"
        k = 2
        while backup.exists():
            backup = pasta / f"_antes-{motivo}-{nome}-{k}"
            k += 1
        backup.mkdir()
        for velho in antigos:
            shutil.move(str(velho), str(backup / velho.name))
        print(f"Versão anterior guardada em {backup.relative_to(pasta_lote).as_posix()}/")
    os.replace(temporarios[0], final)
    if not ja_e_original:
        os.replace(temporarios[1], copia)
    if foco is not None:
        ajuste_novo = ajustes["slides"].setdefault(str(args.slide), {})
        ajuste_novo["foco"] = foco
        gravar_json(caminho_ajustes(pasta_lote / "artes" / pid), ajustes)
    relativo = final.relative_to(pasta_lote).as_posix()
    if imagem.get("arquivo") != relativo:
        imagem["arquivo"] = relativo
        registrar_historico(post, f"imagem gerada importada no slide {args.slide} ({relativo})")
        invalidar_aprovacao(post)
        gravar_json(arquivo_post, post)
    print(f"Imagem importada: {relativo} ({cortada.width}x{cortada.height}, recorte para a área {area[2]}x{area[3]})")
    print(f"Original guardado em: {copia.relative_to(pasta_lote).as_posix()}")
    if cortada.width < area[2]:
        print(f"ATENÇÃO: a imagem é menor que a área ({area[2]}x{area[3]}) e será ampliada; gere uma imagem maior se ficar borrada.")
    print("Confira a imagem antes de seguir: sem texto, sem logo e sem rosto de pessoa real. Depois rode o renderizar.py.")
    return 0


def principal() -> int:
    parser = ParserPT(description="Prompts e importação das imagens geradas por IA para as artes.",
                      epilog="Comandos (a partir da raiz do projeto):" + __doc__.split("Comandos (a partir da raiz do projeto):")[1])
    sub = parser.add_subparsers(dest="comando", required=True, title="comandos")

    p1 = sub.add_parser("prompts", help="escreve artes/<id>/imagens/prompts.md")
    adicionar_args_comuns(p1)
    p1.add_argument("--post", action="append", help="id do post (padrão: todos os posts do lote com texto aprovado)")
    p1.add_argument("--todos", action="store_true", help="escreve também para os slides que já têm imagem importada")
    p1.set_defaults(funcao=comando_prompts)

    p2 = sub.add_parser("importar", help="copia a imagem gerada e recorta para a área do layout")
    adicionar_args_comuns(p2)
    p2.add_argument("--post", required=True, help="id do post")
    p2.add_argument("--slide", type=int, required=True, help="número do slide")
    p2.add_argument("arquivo", help="caminho da imagem gerada (PNG, JPG ou WebP)")
    p2.add_argument("--foco", help="ponto da imagem que deve ficar no centro do corte, 'x y' de 0 a 1 (ex.: \"0.5 0.35\")")
    p2.add_argument("--motivo", help="por que está trocando a imagem (nome da pasta _antes-<motivo> da versão anterior)")
    p2.add_argument("--refazer-aprovado", action="store_true", help="permite trocar a imagem de um post aprovado ou agendado (a aprovação deixa de valer)")
    p2.set_defaults(funcao=comando_importar)

    args = parser.parse_args()
    return args.funcao(args)


if __name__ == "__main__":
    executar(principal)
