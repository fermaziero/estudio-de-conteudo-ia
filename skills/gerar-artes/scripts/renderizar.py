#!/usr/bin/env python3
"""Gera as artes (PNG) dos posts de um lote, a partir de posts/<id>.json e do visual.json da marca.

O texto é desenhado pelo código, com quebra de linha e ajuste de tamanho dentro de uma área segura.
Se o texto não couber nem no menor tamanho permitido, o script falha dizendo qual slide e quanto falta;
ele nunca corta texto. Nada é apagado: a versão anterior vai para artes/<id>/_antes-<motivo>/.

Uso (a partir da raiz do projeto):
    python -X utf8 skills/gerar-artes/scripts/renderizar.py --marca minha-marca --lote 2026-11-03-semana-1
    python -X utf8 skills/gerar-artes/scripts/renderizar.py --marca minha-marca --lote L --post ID --slide 3 --motivo "texto mais curto"
    python -X utf8 skills/gerar-artes/scripts/renderizar.py --marca minha-marca --lote L --post ID --slide 1 --variante faixa
    python -X utf8 skills/gerar-artes/scripts/renderizar.py --marca minha-marca --lote L --post ID --slide 4 --encaixe conter

Código de saída: 0 = tudo certo (avisos podem ter sido mostrados); 1 = nada para gerar ou pedido inválido;
2 = algum post não pôde ser gerado (por exemplo, texto que não cabe).
"""
from __future__ import annotations

import math
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageChops, ImageDraw, ImageFont  # noqa: E402

import galeria  # noqa: E402
from _comum import (  # noqa: E402
    AUTOR, PASTA_FONTES, ErroUsuario, ParserPT, adicionar_args_comuns, agora_iso, assinatura_slide, assinatura_visual, caminho_dentro, carregar_visual, contexto_padrao, executar,
    gravar_json, hoje, invalidar_aprovacao, ler_json, listar_posts, pode_gerar, proporcao_do_post, registrar_historico, selecionar_ids,
    sha256_arquivo, slug,
)
from _layouts import Contexto, ErroSlide, ImagemSlide, renderizar_slide  # noqa: E402

VARIANTES = ("degrade", "faixa")
TEMAS = ("claro", "escuro", "destaque")


# ---------------------------------------------------------------- ajustes por slide

def caminho_ajustes(pasta_artes: Path) -> Path:
    return pasta_artes / "ajustes.json"


def ler_ajustes(pasta_artes: Path) -> dict:
    caminho = caminho_ajustes(pasta_artes)
    if not caminho.is_file():
        return {"versao_esquema": 1, "slides": {}}
    dados = ler_json(caminho)
    if not isinstance(dados, dict):
        raise ErroUsuario(f"{caminho} deve ser um objeto JSON (veja referencias/layouts.md, seção Ajustes por slide). Apague o arquivo para voltar ao padrão.")
    if not isinstance(dados.get("slides"), dict):
        dados["slides"] = {}
    dados.setdefault("versao_esquema", 1)
    return dados


def interpretar_foco(texto: str):
    if texto.strip().lower() == "auto":
        return None
    try:
        x, y = (float(p.replace(",", ".")) for p in texto.replace(";", " ").split())
    except ValueError:
        raise ErroUsuario("--foco deve ser dois números de 0 a 1, separados por espaço. Ex.: --foco \"0.5 0.3\" (x: esquerda a direita; y: topo a base) ou 'auto'.")
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise ErroUsuario("--foco: os dois números devem estar entre 0 e 1.")
    return [round(x, 3), round(y, 3)]


def aplicar_ajustes_da_linha_de_comando(args, ajustes: dict) -> bool:
    """Aplica ao dicionário de ajustes o que foi pedido por --variante, --tema, --foco e --encaixe. Devolve True se pediram algo."""
    pedidos = {"variante": args.variante, "tema": args.tema, "foco": args.foco, "encaixe": args.encaixe}
    if not any(v is not None for v in pedidos.values()):
        return False
    if len(args.post or []) != 1 or args.slide is None:
        raise ErroUsuario("--variante, --tema, --foco e --encaixe valem para um slide só: informe --post e --slide.")
    atual = ajustes["slides"].setdefault(str(args.slide), {})
    if args.variante is not None:
        if args.variante == "auto":
            atual.pop("variante", None)
        else:
            atual["variante"] = args.variante
    if args.tema is not None:
        if args.tema == "auto":
            atual.pop("tema", None)
        else:
            atual["tema"] = args.tema
    if args.encaixe is not None:
        if args.encaixe == "auto":
            atual.pop("encaixe", None)
        else:
            atual["encaixe"] = args.encaixe
    if args.foco is not None:
        foco = interpretar_foco(args.foco)
        if foco is None:
            atual.pop("foco", None)
        else:
            atual["foco"] = foco
    if not atual:
        ajustes["slides"].pop(str(args.slide), None)
    return True


# ---------------------------------------------------------------- dados do post

def resolver_imagem(slide: dict, pasta_marca: Path, pasta_lote: Path, id_post: str) -> ImagemSlide | None:
    bruto = slide.get("imagem")
    if not isinstance(bruto, dict) or not bruto:
        return None
    tipo = bruto.get("tipo") if bruto.get("tipo") in ("foto", "gerada") else "gerada"
    descricao = str(bruto.get("descricao") or "")
    candidatos: list[Path] = []
    if tipo == "gerada":
        candidatos.append(pasta_lote / "artes" / id_post / "imagens" / f"slide-{int(slide['n']):02d}.png")
    arquivo = bruto.get("arquivo")
    if arquivo:
        for base in (pasta_marca, pasta_lote):
            candidatos.append(caminho_dentro(base, arquivo, f"slide {slide['n']}: imagem.arquivo"))
    for candidato in candidatos:
        if candidato.is_file():
            try:
                origem = candidato.relative_to(pasta_marca).as_posix()
            except ValueError:
                origem = candidato.name
            return ImagemSlide(candidato, tipo, descricao, origem)
    return ImagemSlide(None, tipo, descricao)


def checar_post(arquivo: Path, post: dict) -> list[str]:
    problemas = []
    if post.get("id", arquivo.stem) != arquivo.stem:
        problemas.append(f"o campo id ('{post.get('id')}') não é igual ao nome do arquivo ('{arquivo.stem}').")
    slides = post.get("slides")
    if not isinstance(slides, list) or not slides:
        problemas.append("o post não tem 'slides'.")
        return problemas
    numeros = []
    for i, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            problemas.append(f"o item {i} de 'slides' não é um objeto.")
            continue
        numeros.append(slide.get("n"))
    if numeros != list(range(1, len(slides) + 1)):
        problemas.append(f"'n' dos slides deve ir de 1 a {len(slides)} sem buracos e em ordem (veio {numeros}).")
    return problemas


# ---------------------------------------------------------------- escrita

def _iguais(imagem: Image.Image, caminho: Path) -> bool:
    try:
        with Image.open(caminho) as antiga:
            antiga = antiga.convert("RGB")
            return antiga.size == imagem.size and ImageChops.difference(antiga, imagem).getbbox() is None
    except Exception:
        return False


def _salvar_temporario(imagem: Image.Image, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.name}.{os.getpid()}.tmp")
    imagem.save(temporario, format="PNG")
    return temporario


def _gravar_png(imagem: Image.Image, destino: Path) -> None:
    os.replace(_salvar_temporario(imagem, destino), destino)


def gravar_visao_geral(pasta_lote: Path, pid: str, pasta_artes: Path, slides: list[dict]) -> Path | None:
    """Uma imagem só com todos os slides pequenos (mais ou menos o tamanho de um celular) para a conferência visual."""
    pngs = [(s["n"], pasta_artes / f"{s['n']:02d}.png") for s in slides if (pasta_artes / f"{s['n']:02d}.png").is_file()]
    if not pngs:
        return None
    colunas = min(len(pngs), 4)
    linhas = math.ceil(len(pngs) / colunas)
    largura, vao, rotulo = 300, 14, 30
    with Image.open(pngs[0][1]) as primeira:
        altura = round(largura * primeira.height / primeira.width)
    folha = Image.new("RGB", (vao + colunas * (largura + vao), vao + linhas * (altura + rotulo + vao)), (214, 217, 222))
    desenho = ImageDraw.Draw(folha)
    fonte = ImageFont.truetype(str(PASTA_FONTES / "Manrope-Bold.ttf"), 20)
    for i, (n, png) in enumerate(pngs):
        x, y = vao + (i % colunas) * (largura + vao), vao + (i // colunas) * (altura + rotulo + vao)
        with Image.open(png) as arte:
            folha.paste(arte.convert("RGB").resize((largura, altura), Image.Resampling.LANCZOS), (x, y))
        desenho.text((x + largura // 2, y + altura + rotulo // 2 + 1), f"slide {n}", font=fonte, fill=(40, 46, 54), anchor="mm")
    destino = pasta_lote / "_conferencia" / f"{pid}.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    _gravar_png(folha, destino)
    return destino


def _pasta_antes(pasta_artes: Path, motivo: str) -> Path:
    base = f"_antes-{slug(motivo)}"
    pasta, k = pasta_artes / base, 2
    while pasta.exists():
        pasta = pasta_artes / f"{base}-{k}"
        k += 1
    return pasta


# ---------------------------------------------------------------- um post

def processar_post(pid: str, arquivo: Path, post: dict, cfg: dict, contextos: dict, pasta_marca: Path, pasta_lote: Path,
                   args, ajustes_cli: bool) -> dict:
    resultado = {"id": pid, "ok": False, "erros": [], "avisos": [], "linhas": [], "mudou": False}
    problemas = checar_post(arquivo, post)
    if problemas:
        resultado["erros"] = [f"Post '{pid}': {p}" for p in problemas]
        return resultado
    try:
        proporcao = proporcao_do_post(post, cfg)
    except ErroUsuario as erro:
        resultado["erros"] = [str(erro)]
        return resultado
    if proporcao not in contextos:
        contextos[proporcao] = Contexto(cfg, proporcao)
    ctx = contextos[proporcao]

    slides = sorted(post["slides"], key=lambda s: s["n"])
    total = len(slides)
    pasta_artes = pasta_lote / "artes" / pid
    ajustes = ler_ajustes(pasta_artes)
    if ajustes_cli:
        aplicar_ajustes_da_linha_de_comando(args, ajustes)
    if args.slide is not None and args.slide not in [s["n"] for s in slides]:
        resultado["erros"] = [f"Post '{pid}' não tem o slide {args.slide} (vai de 1 a {total})."]
        return resultado
    alvo = [s for s in slides if args.slide is None or s["n"] == args.slide]
    parcial = args.slide is not None

    renderizados: dict[int, tuple] = {}
    for slide in alvo:
        n = slide["n"]
        try:
            imagem = resolver_imagem(slide, pasta_marca, pasta_lote, pid)
            img, meta, avisos = renderizar_slide(ctx, slide, total, ajustes["slides"].get(str(n), {}), imagem)
        except (ErroSlide, ErroUsuario) as erro:
            resultado["erros"].append(f"Post '{pid}' - {erro}")
            continue
        renderizados[n] = (img, meta, avisos, imagem)
    if resultado["erros"]:
        resultado["erros"].append(f"Nada foi gravado para o post '{pid}'. Corrija os pontos acima e rode de novo.")
        return resultado

    estados: dict[int, str] = {}
    for n, (img, _, _, _) in renderizados.items():
        png = pasta_artes / f"{n:02d}.png"
        estados[n] = "novo" if not png.is_file() else ("igual" if _iguais(img, png) else "alterado")
    obsoletos = []
    if not parcial and pasta_artes.is_dir():
        obsoletos = [p for p in sorted(pasta_artes.glob("[0-9][0-9].png")) if int(p.stem) not in renderizados]

    for n, (_, meta, avisos, _) in renderizados.items():
        resultado["linhas"].append(_linha_do_slide(n, meta, estados[n]))
        for a in avisos:
            resultado["avisos"].append(a)
    resultado["avisos_marca"] = ctx.avisos
    houve_mudanca = any(e != "igual" for e in estados.values()) or bool(obsoletos)
    resultado["mudou"] = houve_mudanca
    resultado["resumo"] = {
        "slides": len(renderizados), "novos": sum(e == "novo" for e in estados.values()),
        "alterados": sum(e == "alterado" for e in estados.values()), "iguais": sum(e == "igual" for e in estados.values()),
        "obsoletos": len(obsoletos), "proporcao": proporcao, "tamanho": [ctx.W, ctx.H],
    }
    if args.simular:
        resultado["ok"] = True
        return resultado

    primeira_vez = not any(pasta_artes.glob("[0-9][0-9].png")) if pasta_artes.is_dir() else True
    motivo = args.motivo or f"refeito-{hoje()}"
    pasta_artes.mkdir(parents=True, exist_ok=True)
    # primeiro grava tudo em arquivos temporários: se algo falhar, as artes atuais continuam intactas
    temporarios: dict[int, Path] = {}
    try:
        for n, (img, _, _, _) in renderizados.items():
            if estados[n] != "igual":
                temporarios[n] = _salvar_temporario(img, pasta_artes / f"{n:02d}.png")
    except Exception:
        for temporario in temporarios.values():
            temporario.unlink(missing_ok=True)
        raise
    antigos = [pasta_artes / f"{n:02d}.png" for n, e in estados.items() if e == "alterado"] + obsoletos
    if antigos:
        backup = _pasta_antes(pasta_artes, motivo)
        backup.mkdir(parents=True)
        for antigo in antigos:
            shutil.move(str(antigo), str(backup / antigo.name))
        if (pasta_artes / "manifesto.json").is_file():
            shutil.copy2(pasta_artes / "manifesto.json", backup / "manifesto.json")
        resultado["backup"] = backup.relative_to(pasta_lote).as_posix()
    for n, temporario in temporarios.items():
        os.replace(temporario, pasta_artes / f"{n:02d}.png")
    if ajustes_cli:
        gravar_json(caminho_ajustes(pasta_artes), ajustes)

    gravar_manifesto(pid, post, ctx, pasta_marca, pasta_lote, pasta_artes, renderizados, slides, proporcao)
    visao = gravar_visao_geral(pasta_lote, pid, pasta_artes, slides)
    if visao is not None:
        resultado["visao_geral"] = visao.relative_to(pasta_lote).as_posix()
    if houve_mudanca:
        atualizar_post(arquivo, post, primeira_vez, sorted(n for n, e in estados.items() if e != "igual"), len(obsoletos), motivo, total, proporcao)
    resultado["ok"] = True
    return resultado


def _linha_do_slide(n: int, meta: dict, estado: str) -> str:
    fontes = ", ".join(f"{k.replace('_', ' ')} {v}px" for k, v in (meta.get("fonte_px") or {}).items())
    variante = f"/{meta['variante']}" if meta.get("variante") else ""
    logo = meta.get("logo")
    extra = f" | logo {logo['versao'].replace('fundo_', '')}" if logo else ""
    contraste = f" | contraste {meta['contraste_minimo']}:1" if meta.get("contraste_minimo") else ""
    return f"  {n:02d}.png {meta.get('layout', '?')}{variante} ({meta.get('tema', '?')}) [{estado}] {fontes}{contraste}{extra}"


def gravar_manifesto(pid: str, post: dict, ctx: Contexto, pasta_marca: Path, pasta_lote: Path, pasta_artes: Path,
                     renderizados: dict, slides: list[dict], proporcao: str) -> None:
    anterior = {}
    caminho = pasta_artes / "manifesto.json"
    if caminho.is_file():
        try:
            anterior = {item.get("n"): item for item in ler_json(caminho).get("slides", []) if isinstance(item, dict)}
        except ErroUsuario:
            anterior = {}
    itens = []
    visual_atual = assinatura_visual(pasta_marca)
    for slide in slides:
        n = slide["n"]
        png = pasta_artes / f"{n:02d}.png"
        if n in renderizados:
            _, meta, avisos, imagem = renderizados[n]
            entrada = {
                "n": n, "arquivo": png.name, "sha256": sha256_arquivo(png), "conteudo_sha256": assinatura_slide(slide, proporcao),
                "visual_sha256": visual_atual, "dimensoes": [ctx.W, ctx.H], "layout": meta.get("layout"), "tema": meta.get("tema"),
                "variante": meta.get("variante"), "fonte_px": meta.get("fonte_px"), "linhas": meta.get("linhas"),
                "contraste_minimo": meta.get("contraste_minimo"), "logo": meta.get("logo"), "imagens": [],
                "avisos": [{k: v for k, v in a.items() if k != "slide"} for a in avisos],
            }
            if imagem is not None and imagem.caminho is not None and meta.get("imagem"):
                entrada["imagens"].append({
                    "tipo": imagem.tipo, "arquivo": imagem.origem, "sha256": sha256_arquivo(imagem.caminho), **meta["imagem"],
                })
            itens.append(entrada)
        elif n in anterior and png.is_file() and anterior[n].get("sha256") == sha256_arquivo(png):
            itens.append(anterior[n])
        elif png.is_file():
            itens.append({"n": n, "arquivo": png.name, "sha256": sha256_arquivo(png), "dimensoes": [ctx.W, ctx.H], "layout": slide.get("layout"),
                          "imagens": [], "avisos": [{"nivel": "atencao", "codigo": "manifesto_incompleto",
                                                     "mensagem": f"Slide {n}: manifesto reconstruído; refaça este slide para registrar os detalhes."}]})
    avisos = [{k: v for k, v in a.items()} for a in ctx.avisos if a.get("nivel") == "atencao"]
    for item in itens:
        for a in item.get("avisos", []):
            avisos.append({**a, "slide": item["n"]})
    gravar_json(caminho, {
        "versao_esquema": 1, "post_id": pid, "lote": pasta_lote.name, "gerado_em": agora_iso(), "gerador": AUTOR,
        "proporcao": proporcao, "dimensoes": [ctx.W, ctx.H], "slides": itens, "avisos": avisos,
    })


def atualizar_post(arquivo: Path, post: dict, primeira_vez: bool, numeros: list[int], obsoletos: int, motivo: str,
                   total: int, proporcao: str) -> None:
    if primeira_vez:
        registrar_historico(post, f"artes geradas: {total} slide(s) em {proporcao}")
    else:
        extra = f"; {obsoletos} arte(s) antiga(s) sobrando guardada(s)" if obsoletos else ""
        registrar_historico(post, f"artes refeitas ({motivo}): slides {', '.join(map(str, numeros)) or 'nenhum'}{extra}")
    invalidar_aprovacao(post)
    gravar_json(arquivo, post)


# ---------------------------------------------------------------- escolha dos posts

def escolher_posts(posts: dict, pedidos: list[str] | None, args) -> tuple[list[str], list[tuple[str, str]]]:
    ids = selecionar_ids(posts, pedidos)
    explicito = bool(pedidos)
    escolhidos: list[str] = []
    pulados: list[tuple[str, str]] = []
    for pid in ids:
        post = posts[pid][1]
        status, formato = post.get("status") or "rascunho", post.get("formato")
        ok, motivo = pode_gerar(status, formato)
        if not ok:
            if explicito:
                raise ErroUsuario(f"Post '{pid}': {motivo}.")
            pulados.append((pid, motivo))
            continue
        if status in ("aprovado", "agendado") and not args.refazer_aprovado:
            texto = "já foi aprovado/agendado; refazer a arte invalida a aprovação. Se a pessoa pediu mesmo, rode de novo com --refazer-aprovado"
            if explicito:
                raise ErroUsuario(f"Post '{pid}': {texto}.")
            if args.refazer:
                pulados.append((pid, texto))
                continue
        if explicito or status == "texto_aprovado" or (args.refazer and status in ("arte_pronta", "erro", "aprovado", "agendado")):
            escolhidos.append(pid)
        else:
            pulados.append((pid, f"status {status}: as artes já foram geradas; use --refazer (lote todo) ou --post ID (um post)"))
    return escolhidos, pulados


def principal() -> int:
    parser = ParserPT(
        description="Gera as artes (PNG 1080x1350 ou 1080x1080) dos posts de um lote, com texto desenhado pelo código.",
        epilog="Exemplos (a partir da raiz do projeto):" + __doc__.split("Uso (a partir da raiz do projeto):")[1],
    )
    adicionar_args_comuns(parser)
    parser.add_argument("--post", action="append", help="id do post (pode repetir ou separar por vírgula). Sem isto: todos os posts com status texto_aprovado")
    parser.add_argument("--slide", type=int, help="refaz só este slide (exige um --post)")
    parser.add_argument("--refazer", action="store_true", help="inclui os posts que já têm artes (arte_pronta ou erro)")
    parser.add_argument("--refazer-aprovado", action="store_true", help="permite refazer posts aprovados ou agendados (a aprovação deixa de valer)")
    parser.add_argument("--motivo", help="por que está refazendo; vira o nome da pasta _antes-<motivo> com a versão anterior")
    parser.add_argument("--variante", choices=(*VARIANTES, "auto"), help="só capa com imagem: degrade (texto sobre degradê) ou faixa (imagem em cima, faixa de cor embaixo). Fica salvo em ajustes.json")
    parser.add_argument("--tema", choices=(*TEMAS, "auto"), help="tema do slide: claro, escuro ou destaque (cor de destaque no fundo). Fica salvo em ajustes.json")
    parser.add_argument("--foco", help="ponto da imagem que deve ficar no centro do corte, 'x y' de 0 a 1 (ex.: \"0.5 0.3\"), ou 'auto'. Fica salvo em ajustes.json")
    parser.add_argument("--encaixe", choices=("cobrir", "conter", "auto"), help="layout imagem: cobrir (preenche a área e corta as sobras) ou conter (mostra a imagem inteira sobre um cartão neutro; bom para prints e logos). Fica salvo em ajustes.json")
    parser.add_argument("--simular", action="store_true", help="faz tudo menos gravar: mostra se o texto cabe e o que mudaria")
    parser.add_argument("--sem-galeria", action="store_true", help="não atualiza a galeria.html")
    args = parser.parse_args()

    if args.slide is not None and len(args.post or []) != 1:
        raise ErroUsuario("--slide exige exatamente um --post.")
    _, slug_marca, pasta_marca, nome_lote, pasta_lote = contexto_padrao(args)
    cfg = carregar_visual(pasta_marca)
    posts = listar_posts(pasta_lote)
    if not posts:
        raise ErroUsuario(f"O lote {nome_lote} não tem posts em {pasta_lote / 'posts'}.")
    escolhidos, pulados = escolher_posts(posts, args.post, args)
    for pid, motivo in pulados:
        print(f"Pulado: {pid} ({motivo}).")
    if not escolhidos:
        raise ErroUsuario("Nada para gerar: nenhum post com status texto_aprovado (o texto precisa da aprovação da pessoa). Os motivos estão nas linhas \"Pulado\" acima; para refazer artes que já existem, use --refazer (lote todo) ou --post <id>.")

    ajustes_cli = any(v is not None for v in (args.variante, args.tema, args.foco, args.encaixe))
    contextos: dict = {}
    resultados = []
    prefixo = "SIMULAÇÃO (nada será gravado). " if args.simular else ""
    print(f"{prefixo}Marca: {slug_marca} | lote: {nome_lote} | posts: {len(escolhidos)}")
    for pid in escolhidos:
        arquivo, post = posts[pid]
        resultado = processar_post(pid, arquivo, post, cfg, contextos, pasta_marca, pasta_lote, args, ajustes_cli)
        resultados.append(resultado)
        if resultado["ok"]:
            r = resultado["resumo"]
            partes = [f"{r['novos']} nova(s)", f"{r['alterados']} alterada(s)", f"{r['iguais']} igual(is)"]
            print(f"\nOK  {pid}: {r['slides']} slide(s) {r['tamanho'][0]}x{r['tamanho'][1]} ({', '.join(partes)})")
            for linha in resultado["linhas"]:
                print(linha)
            if resultado.get("backup"):
                print(f"  versão anterior guardada em: {resultado['backup']}/")
            if resultado.get("visao_geral"):
                print(f"  visão geral (todos os slides, tamanho de celular): {resultado['visao_geral']}")
        else:
            print(f"\nFALHOU  {pid}")
            for erro in resultado["erros"]:
                print(f"  ERRO: {erro}")
    vistos: set = set()
    mostrar_info = ("capa_com_apoio", "capa_longa", "imagem_ignorada", "imagem_pequena", "logo_pouco_contraste", "tema_trocado")
    for resultado in resultados:
        for a in list(resultado.get("avisos_marca", [])) + resultado["avisos"]:
            if a["nivel"] == "info" and a["codigo"] not in mostrar_info:
                continue
            do_slide = a.get("slide") is not None and a["codigo"] != "tema_trocado"
            texto = f"[{resultado['id']}] {a['mensagem']}" if do_slide else a["mensagem"]
            if texto in vistos:
                continue
            vistos.add(texto)
            print(f"{'ATENÇÃO' if a['nivel'] == 'atencao' else 'aviso'}: {texto}")
    falhas = [r for r in resultados if not r["ok"]]
    if not args.simular and not args.sem_galeria and any(r["ok"] for r in resultados):
        destino = galeria.gerar(pasta_marca, slug_marca, nome_lote, pasta_lote)
        print(f"\nGaleria atualizada: {destino}")
    if falhas:
        print(f"\n{len(falhas)} post(s) com erro. Veja as mensagens acima.")
        return 2
    return 0


if __name__ == "__main__":
    executar(principal)
