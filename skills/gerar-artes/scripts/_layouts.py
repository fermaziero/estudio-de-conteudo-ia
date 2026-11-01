"""Layouts das artes: capa, texto, lista, cartoes, imagem, citacao e cta.

Cada slide é desenhado em 2x com Pillow, dentro de uma área segura, e reduzido para 1080 px de largura.
O texto é sempre desenhado pelo código; imagens geradas por IA entram só como fundo ou ilustração.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import _logo
from _comum import ErroUsuario, PASTA_FONTES, TAMANHOS, aviso, contraste, luminancia, misturar, slug
from _texto import S, BlocoTexto, Fontes, SemEspaco, ajustar_pilha, texto_limpo

M = 72
RAIO = 28
ALTURA_LOGO_MAX = 110
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
TEMA_PADRAO = {
    "capa": "escuro", "texto": "claro", "lista": "claro", "cartoes": "claro",
    "imagem": "claro", "citacao": "claro", "cta": "escuro",
}


class ErroSlide(Exception):
    """Problema nos dados do slide (layout desconhecido, itens faltando...)."""

    def __init__(self, slide, layout, mensagem: str):
        super().__init__(mensagem)
        self.slide, self.layout, self.mensagem = slide, layout, mensagem

    def __str__(self) -> str:
        return f"Slide {self.slide} (layout {self.layout}): {self.mensagem}"


class NaoCabe(ErroSlide):
    """O texto não cabe na área segura nem no menor tamanho permitido."""

    def __init__(self, slide, layout, causa: SemEspaco):
        self.causa = causa
        blocos = causa.blocos
        if causa.excesso_x > 0:
            palavra = next((b.palavra_longa for b in blocos if b.excesso > 0), "")
            if len(palavra) > 40:
                palavra = palavra[:40] + "..."
            detalhe = (f"a palavra '{palavra}' é mais larga que a área segura em cerca de {causa.excesso_x:.0f} px, "
                       "mesmo no menor tamanho. Troque ou divida a palavra.")
        else:
            maior = max(blocos, key=lambda b: b.leading_px)
            linhas = max(1, round(causa.sobra / maior.leading_px))
            tamanhos = ", ".join(f"{rotulo} {px} px" for rotulo, px in dict.fromkeys((b.rotulo, b.px) for b in blocos))
            detalhe = (f"faltam cerca de {causa.sobra:.0f} px de altura (uns {linhas} linha(s)) mesmo no menor tamanho "
                       f"permitido ({tamanhos}). Encurte o texto; o novo texto precisa do ok da pessoa.")
        super().__init__(slide, layout, "o texto não cabe: " + detalhe)


@dataclass
class ImagemSlide:
    """Imagem de um slide: `caminho` vazio quer dizer que ela foi declarada mas ainda não existe."""
    caminho: Path | None
    tipo: str = "gerada"
    descricao: str = ""
    origem: str = ""
    foco: tuple[float, float] | None = None


# ---------------------------------------------------------------- contexto

def montar_paletas(cfg: dict) -> tuple[dict, list[dict]]:
    c = cfg["cores"]
    avisos = []
    fundo = c["fundo"]
    claro = {
        "nome": "claro", "escuro": False, "logo": "claro",
        "fundo": fundo, "texto": c["texto"], "suave": c["suave"], "destaque": c["destaque"],
        "enfase": c["destaque"] if contraste(c["destaque"], fundo) >= 3.5 else c["texto"],
        "cartao": misturar(fundo, BRANCO, 0.7) if luminancia(fundo) < 0.93 else misturar(fundo, c["texto"], 0.05),
        "borda": misturar(fundo, c["texto"], 0.12),
    }
    if contraste(c["texto"], fundo) < 4.5:
        avisos.append(aviso("atencao", "contraste_baixo",
                            f"As cores 'texto' e 'fundo' do visual.json têm contraste {contraste(c['texto'], fundo):.1f}:1 (o mínimo para leitura no celular é 4,5:1)."))

    esc_fundo, esc_texto = c["fundo_escuro"], c["texto_sobre_escuro"]
    destaque_escuro, t = c["destaque"], 0.0
    while contraste(destaque_escuro, esc_fundo) < 3.5 and t < 1.0:
        t += 0.1
        destaque_escuro = misturar(c["destaque"], BRANCO, t)
    if t > 0:
        avisos.append(aviso("info", "destaque_clareado",
                            "A cor 'destaque' tem pouco contraste sobre o fundo escuro; nos slides escuros ela é usada numa versão mais clara."))
    escuro = {
        "nome": "escuro", "escuro": True, "logo": "escuro",
        "fundo": esc_fundo, "texto": esc_texto, "suave": misturar(esc_texto, esc_fundo, 0.38), "destaque": destaque_escuro,
        "enfase": destaque_escuro, "cartao": misturar(esc_fundo, BRANCO, 0.08), "borda": misturar(esc_fundo, BRANCO, 0.16),
    }
    if contraste(esc_texto, esc_fundo) < 4.5:
        avisos.append(aviso("atencao", "contraste_baixo",
                            f"As cores 'texto_sobre_escuro' e 'fundo_escuro' têm contraste {contraste(esc_texto, esc_fundo):.1f}:1 (mínimo recomendado: 4,5:1)."))

    dest_fundo = c["destaque"]
    dest_texto = max([esc_texto, c["texto"], BRANCO, PRETO], key=lambda cor: contraste(cor, dest_fundo))
    destaque = {
        "nome": "destaque", "escuro": luminancia(dest_fundo) < 0.4, "logo": "escuro" if luminancia(dest_fundo) < 0.4 else "claro",
        "fundo": dest_fundo, "texto": dest_texto, "suave": misturar(dest_texto, dest_fundo, 0.25), "destaque": dest_texto,
        "enfase": dest_texto,
        "cartao": misturar(dest_fundo, PRETO, 0.14) if luminancia(dest_fundo) > 0.2 else misturar(dest_fundo, BRANCO, 0.12),
        "borda": misturar(dest_fundo, dest_texto, 0.25),
    }
    return {"claro": claro, "escuro": escuro, "destaque": destaque}, avisos


def _fonte_variavel(caminho: Path) -> bool:
    try:
        ImageFont.truetype(str(caminho), 20).get_variation_axes()
        return True
    except (OSError, AttributeError):
        return False


class Contexto:
    """Tudo o que vale para todos os slides de um post: tamanho, fontes, paletas e logo."""

    def __init__(self, cfg: dict, proporcao: str):
        self.cfg = cfg
        self.proporcao = proporcao
        self.W, self.H = TAMANHOS[proporcao]
        padrao = {"titulo": PASTA_FONTES / "Manrope-Bold.ttf", "texto": PASTA_FONTES / "Manrope-Regular.ttf",
                  "forte": PASTA_FONTES / "Manrope-ExtraBold.ttf"}
        for arquivo in padrao.values():
            if not arquivo.is_file():
                raise ErroUsuario(f"A fonte que acompanha a skill não foi encontrada: {arquivo}. Restaure a pasta skills/gerar-artes/fontes/.")
        self.fontes = Fontes(cfg["fonte_titulo"] or padrao["titulo"], cfg["fonte_texto"] or padrao["texto"],
                             cfg["fonte_titulo"] or padrao["forte"])
        self.paletas, avisos_paletas = montar_paletas(cfg)
        self.avisos = list(cfg.get("avisos", [])) + avisos_paletas
        for caminho in {cfg["fonte_titulo"], cfg["fonte_texto"]} - {None}:
            if _fonte_variavel(caminho):
                self.avisos.append(aviso(
                    "atencao", "fonte_variavel",
                    f"A fonte {Path(caminho).name} é variável (um arquivo com vários pesos). O Pillow mede a largura das letras sem considerar o peso, "
                    "e o texto pode sair apertado. Use os arquivos estáticos da família (Regular, Bold...) e aponte para eles no visual.json."))
        tm, tM = cfg["tipografia"]["titulo"]
        am, aM = cfg["tipografia"]["apoio"]
        self.tip = {"titulo": (tm, tM), "apoio": (am, aM), "capa": (tm + 4, tM + 6), "item": (am + 2, aM + 4)}
        self._imagens: dict = {}
        self._transparentes: dict = {}
        self._logos: dict = {}
        self.logo_altura = 0
        logo = cfg["logo"]
        if logo:
            for tema, caminho in logo["arquivos"].items():
                base, notas = _logo.carregar(caminho)
                self._logos[tema] = base
                self.avisos += [aviso("info", "logo_preparado", n) for n in notas]
                altura = round(logo["largura_px"] * base.height / base.width)
                self.logo_altura = max(self.logo_altura, min(altura, ALTURA_LOGO_MAX))

    def zona(self) -> dict:
        """Área vertical livre para o conteúdo, descontando o espaço do logo e do rodapé."""
        topo, base = 88, self.H - 88
        logo = self.cfg["logo"]
        if logo and self.logo_altura:
            if logo["posicao"].startswith("superior"):
                topo = M + self.logo_altura + 64
            else:
                base = self.H - (M + self.logo_altura + 56)
        if self.cfg["numeracao"] or self.cfg["rodape"]:
            base = min(base, self.H - 128)
        return {"topo": topo, "base": base}

    def abrir_imagem(self, caminho: Path, fundo=BRANCO) -> Image.Image:
        caminho = Path(caminho)
        chave = (str(caminho), caminho.stat().st_mtime_ns, tuple(fundo))
        if chave not in self._imagens:
            try:
                with Image.open(caminho) as arquivo:
                    arquivo.load()
                    img = ImageOps.exif_transpose(arquivo)
            except Exception as erro:
                raise ErroUsuario(f"Não consegui abrir a imagem {caminho.name} ({type(erro).__name__}). Use JPG, PNG ou WebP.")
            transparente = False
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                transparente = img.getchannel("A").getextrema()[0] < 250
                base = Image.new("RGB", img.size, tuple(fundo))
                base.paste(img, mask=img.getchannel("A"))
                img = base
            else:
                img = img.convert("RGB")
            self._imagens[chave] = img
            self._transparentes[str(caminho)] = transparente
        return self._imagens[chave]

    def tem_transparencia(self, caminho: Path) -> bool:
        if str(caminho) not in self._transparentes:
            self.abrir_imagem(caminho)
        return self._transparentes[str(caminho)]


class Slide:
    def __init__(self, ctx: Contexto, paleta: dict, numero, total: int, layout: str):
        self.ctx, self.paleta, self.n, self.total, self.layout = ctx, paleta, numero, total, layout
        self.W, self.H = ctx.W, ctx.H
        self.im = Image.new("RGB", (self.W * S, self.H * S), paleta["fundo"])
        self.d = ImageDraw.Draw(self.im)
        self.zona = ctx.zona()
        self.largura_util = self.W - 2 * M
        self.avisos: list[dict] = []
        self.meta: dict = {}
        self.contrastes: list[float] = []
        self.logo_caixa: tuple[float, float, float, float] | None = None

    def avisar(self, nivel: str, codigo: str, mensagem: str) -> None:
        self.avisos.append(aviso(nivel, codigo, f"Slide {self.n}: {mensagem}", self.n))

    def ajustar(self, especs: list[dict], altura_max: float, largura: float | None = None):
        try:
            return ajustar_pilha(self.ctx.fontes, especs, altura_max, largura or self.largura_util)
        except SemEspaco as erro:
            raise NaoCabe(self.n, self.layout, erro)

    def texto(self, bloco: BlocoTexto, x: float, y: float, cor, cor_destaque=None) -> None:
        bloco.desenhar(self.d, x, y, cor, cor_destaque)

    def retangulo(self, x0, y0, x1, y1, cor, raio=0, contorno=None) -> None:
        caixa = (round(x0 * S), round(y0 * S), round(x1 * S) - 1, round(y1 * S) - 1)
        if raio:
            self.d.rounded_rectangle(caixa, radius=raio * S, fill=cor, outline=contorno, width=S if contorno else 0)
        else:
            self.d.rectangle(caixa, fill=cor, outline=contorno, width=S if contorno else 0)

    def brilho(self, cx: float, cy: float, raio: float, alfa: float, cor=None) -> None:
        """Mancha de luz suave (radial) para dar profundidade aos fundos escuros."""
        r = round(raio * S)
        # No gradiente do Pillow, o valor 181 marca o meio da borda do quadrado: dali para fora a luz some.
        gradiente = Image.radial_gradient("L").resize((2 * r, 2 * r), Image.Resampling.BICUBIC)
        gradiente = gradiente.point([round(255 * alfa * max(0.0, 1 - v / 181) ** 2) for v in range(256)])
        x0, y0 = round(cx * S) - r, round(cy * S) - r
        ex0, ey0 = max(0, x0), max(0, y0)
        ex1, ey1 = min(self.im.width, x0 + 2 * r), min(self.im.height, y0 + 2 * r)
        if ex1 <= ex0 or ey1 <= ey0:
            return
        recorte = gradiente.crop((ex0 - x0, ey0 - y0, ex1 - x0, ey1 - y0))
        self.im.paste(Image.new("RGB", recorte.size, cor or self.paleta["destaque"]), (ex0, ey0), recorte)

    def degrade_vertical(self, y0: float, y1: float, cor, alfa_max: float) -> None:
        """Camada de cor que vai de transparente (em y0) até `alfa_max` (em y1 e abaixo)."""
        topo, fim = max(0, round(y0 * S)), round(y1 * S)
        altura = self.im.height - topo
        if altura <= 0:
            return
        coluna = Image.new("L", (1, altura))
        pixels = coluna.load()
        for y in range(altura):
            t = min(1.0, max(0.0, y / max(1, fim - topo)))
            pixels[0, y] = round(255 * alfa_max * (t * t * (3 - 2 * t)))
        mascara = coluna.resize((self.im.width, altura))
        self.im.paste(Image.new("RGB", (self.im.width, altura), cor), (0, topo), mascara)

    def checar_contraste(self, cor_texto, cor_fundo, rotulo: str, minimo: float = 4.5) -> float:
        valor = contraste(cor_texto, cor_fundo)
        self.contrastes.append(valor)
        if valor < minimo:
            self.avisar("atencao", "contraste_baixo", f"{rotulo} com contraste {valor:.1f}:1 (mínimo {minimo}:1). Mude as cores ou o tema do slide.")
        return valor

    def pior_contraste_regiao(self, caixa, cor_texto) -> float:
        x0, y0, x1, y1 = (round(v * S) for v in caixa)
        regiao = self.im.crop((x0, y0, x1, y1)).resize((16, 6), Image.Resampling.BOX)
        pixels = regiao.load()
        return min(contraste(cor_texto, pixels[x, y]) for y in range(6) for x in range(16))

    def empilhar(self, blocos: list[BlocoTexto], y: float, cores) -> float:
        """Desenha blocos um abaixo do outro, respeitando o espaço `antes` de cada um."""
        for i, b in enumerate(blocos):
            y += b.antes if i else 0
            cor, destaque = cores(b)
            self.texto(b, M, y, cor, destaque)
            y += b.altura
        return y


# ---------------------------------------------------------------- imagens

def recortar_cobrindo(img: Image.Image, largura: int, altura: int, foco=(0.5, 0.5)) -> Image.Image:
    """Preenche `largura` x `altura` com a imagem (sem distorcer), centrando o corte no ponto de foco."""
    iw, ih = img.size
    alvo = largura / altura
    if iw / ih > alvo:
        cw, ch = ih * alvo, float(ih)
    else:
        cw, ch = float(iw), iw / alvo
    esquerda = min(max(foco[0] * iw - cw / 2, 0), iw - cw)
    topo = min(max(foco[1] * ih - ch / 2, 0), ih - ch)
    return img.resize((largura, altura), Image.Resampling.LANCZOS,
                      box=(esquerda, topo, esquerda + cw, topo + ch), reducing_gap=2.0)


def mascara_arredondada(tamanho: tuple[int, int], raio: int) -> Image.Image:
    mascara = Image.new("L", tamanho, 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, tamanho[0] - 1, tamanho[1] - 1), radius=raio, fill=255)
    return mascara


def _foco(imagem: ImagemSlide, ajuste: dict) -> tuple[float, float]:
    bruto = ajuste.get("foco") or imagem.foco
    if bruto:
        try:
            return (min(max(float(bruto[0]), 0.0), 1.0), min(max(float(bruto[1]), 0.0), 1.0))
        except (TypeError, ValueError, IndexError):
            pass
    return (0.5, 0.4) if imagem.tipo == "foto" else (0.5, 0.5)


def _colar_imagem(s: Slide, imagem: ImagemSlide, ajuste: dict, x: int, y: int, w: int, h: int, raio: int = 0) -> None:
    foco = _foco(imagem, ajuste)
    img = s.ctx.abrir_imagem(Path(imagem.caminho), s.paleta["fundo"])
    recorte = recortar_cobrindo(img, w * S, h * S, foco)
    mascara = mascara_arredondada(recorte.size, raio * S) if raio else None
    s.im.paste(recorte, (x * S, y * S), mascara)
    largura_util_origem = min(img.width, img.height * w / h)
    ampliacao = max(w / largura_util_origem, 1.0)
    if ampliacao > 1.25:
        s.avisar("atencao" if ampliacao > 2 else "info", "imagem_pequena",
                 f"a imagem {Path(imagem.caminho).name} ({img.width}x{img.height}) é ampliada {ampliacao:.1f}x para cobrir a área; pode ficar borrada.")
    s.meta["imagem"] = {"area": [x, y, w, h], "foco": [round(foco[0], 3), round(foco[1], 3)], "ampliacao": round(ampliacao, 2)}


def _modo_encaixe(s: Slide, imagem: ImagemSlide, ajuste: dict) -> str:
    """'cobrir' preenche a área cortando as sobras; 'conter' mostra a imagem inteira sobre um cartão neutro."""
    if ajuste.get("encaixe") in ("cobrir", "conter"):
        return ajuste["encaixe"]
    caminho = Path(imagem.caminho)
    if imagem.tipo == "foto" and ("logo" in caminho.stem.lower() or any(p.lower() in ("logo", "logos") for p in caminho.parts)):
        return "conter"
    return "conter" if imagem.tipo == "foto" and s.ctx.tem_transparencia(caminho) else "cobrir"


def _colar_contida(s: Slide, imagem: ImagemSlide, x: int, y: int, w: int, h: int, raio: int) -> None:
    """Imagem inteira, sem cortar, centralizada num cartão neutro (logos de terceiros, prints, gráficos)."""
    p = s.paleta
    img = s.ctx.abrir_imagem(Path(imagem.caminho), p["cartao"])
    margem = 44
    escala = min((w - 2 * margem) / img.width, (h - 2 * margem) / img.height, 3.0)
    nw, nh = max(1, round(img.width * escala)), max(1, round(img.height * escala))
    altura_cartao = min(h, max(round(h * 0.5), nh + 2 * margem))
    y_cartao = y + (h - altura_cartao) // 2
    s.retangulo(x, y_cartao, x + w, y_cartao + altura_cartao, p["cartao"], raio, p["borda"])
    s.im.paste(img.resize((nw * S, nh * S), Image.Resampling.LANCZOS),
               ((x + (w - nw) // 2) * S, (y_cartao + (altura_cartao - nh) // 2) * S))
    if escala > 2:
        s.avisar("info", "imagem_pequena", f"a imagem {Path(imagem.caminho).name} é ampliada {escala:.1f}x; pode ficar borrada.")
    s.meta["imagem"] = {"area": [x, y, w, h], "modo": "conter", "ampliacao": round(max(escala, 0.01), 2)}


def _imagem_presente(imagem: ImagemSlide | None, reservar: bool) -> bool:
    return imagem is not None and (imagem.caminho is not None or reservar)


def _imagem_faltando(s: Slide, imagem: ImagemSlide | None) -> None:
    if imagem is not None and imagem.caminho is None:
        extra = f" ({imagem.descricao})" if imagem.descricao else ""
        s.avisar("atencao", "imagem_ausente",
                 f"a imagem prevista não foi encontrada{extra}. O slide saiu com fundo sólido; gere o prompt, crie a imagem e importe (ou indique a foto aprovada).")


# ---------------------------------------------------------------- itens (lista e cartões)

def dividir_item(texto: str) -> tuple[str | None, str]:
    """'Título: explicação' vira (título, explicação); sem esse formato, devolve (None, texto)."""
    t = str(texto).strip()
    if "**" in t:
        return None, t
    achado = re.match(r"^([^:\n]{2,48}?):\s+(\S.*)$", t, re.S)
    if achado:
        return achado.group(1).strip(), achado.group(2).strip()
    return None, t


def _itens(s: Slide, slide: dict) -> list[str]:
    itens = [str(i).strip() for i in (slide.get("itens") or []) if str(i).strip()]
    if not itens:
        raise ErroSlide(s.n, s.layout, "este layout precisa de 'itens' (de 2 a 5 textos curtos).")
    return itens


def _especs_titulo(s: Slide, slide: dict) -> list[dict]:
    ctx = s.ctx
    return [
        dict(texto=slide.get("titulo", ""), papel="titulo", faixa=ctx.tip["titulo"], leading=1.2, balancear=True,
             rotulo="título", tag=("titulo", 0)),
        dict(texto=slide.get("texto", ""), papel="texto", faixa=ctx.tip["apoio"], leading=1.42, balancear="auto",
             antes=26, rotulo="apoio", tag=("apoio", 0)),
    ]


def _especs_itens(s: Slide, slide: dict, largura: float, rotulo: str, primeiro_antes: int, entre: int, extra_fim: int = 0) -> list[dict]:
    ctx = s.ctx
    especs = []
    for i, item in enumerate(_itens(s, slide)):
        lead, corpo = dividir_item(item)
        antes = primeiro_antes if i == 0 else entre
        if lead:
            especs.append(dict(texto=lead, papel="titulo", faixa=ctx.tip["item"], leading=1.25, largura=largura, antes=antes,
                               rotulo=f"{rotulo} (título)", tag=("lead", i)))
            especs.append(dict(texto=corpo, papel="texto", faixa=ctx.tip["apoio"], leading=1.4, largura=largura, antes=8,
                               rotulo=f"{rotulo} (texto)", tag=("corpo", i), extra=extra_fim))
        else:
            especs.append(dict(texto=corpo, papel="texto", faixa=ctx.tip["item"], leading=1.38, largura=largura, antes=antes,
                               rotulo=rotulo, tag=("corpo", i), extra=extra_fim))
    return especs


def _separar_itens(blocos: list[BlocoTexto]) -> tuple[list[BlocoTexto], list[list[BlocoTexto]]]:
    cabecalho: list[BlocoTexto] = []
    itens: dict[int, list[BlocoTexto]] = {}
    for b in blocos:
        tipo, indice = b.tag
        if tipo in ("titulo", "apoio"):
            cabecalho.append(b)
        else:
            itens.setdefault(indice, []).append(b)
    return cabecalho, [itens[k] for k in sorted(itens)]


def _resumo(blocos: list[BlocoTexto]) -> tuple[dict, int]:
    """Tamanhos de fonte usados (chaves sem acento, para o manifesto) e total de linhas desenhadas."""
    return {slug(b.rotulo, 30).replace("-", "_"): b.px for b in blocos}, sum(b.n_linhas for b in blocos)


# ---------------------------------------------------------------- layouts

def lay_texto(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    especs = [
        dict(texto=slide.get("titulo", ""), papel="titulo", faixa=ctx.tip["titulo"], leading=1.2, balancear=True, rotulo="título"),
        dict(texto=slide.get("texto", ""), papel="texto", faixa=ctx.tip["apoio"], leading=1.42, balancear="auto", antes=34, rotulo="apoio"),
    ]
    disp = z["base"] - z["topo"]
    blocos, total, _ = s.ajustar(especs, disp)
    s.empilhar(blocos, z["topo"] + (disp - total) * 0.40, lambda b: (p["texto"], p["enfase"]))
    s.checar_contraste(p["texto"], p["fundo"], "O texto")
    s.meta["fonte_px"], s.meta["linhas"] = _resumo(blocos)


def lay_lista(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    coluna = 76
    especs = _especs_titulo(s, slide) + _especs_itens(s, slide, s.largura_util - coluna, "item", primeiro_antes=50, entre=36)
    disp = z["base"] - z["topo"]
    blocos, total, _ = s.ajustar(especs, disp)
    cabecalho, itens = _separar_itens(blocos)
    # sobrando espaço, os itens ganham respiro (até um limite) em vez de ficarem colados no título
    respiro = min(max(disp - total, 0) * 0.55 / max(len(itens), 1), 56)
    total += respiro * len(itens)
    y = s.empilhar(cabecalho, z["topo"] + (disp - total) * 0.38, lambda b: (p["texto"], p["enfase"]))
    for i, grupo in enumerate(itens):
        y += (grupo[0].antes + respiro) if (cabecalho or i) else 0
        numeral = ctx.fontes.obter("forte", round(grupo[0].px * 1.5))
        s.d.text((M * S, round((y + grupo[0].base_primeira_linha()) * S)), str(i + 1), font=numeral, fill=p["enfase"], anchor="ls")
        for k, b in enumerate(grupo):
            y += b.antes if k else 0
            lead = b.tag[0] == "lead"
            s.texto(b, M + coluna, y, p["enfase"] if lead else p["texto"], p["enfase"])
            y += b.altura
    s.checar_contraste(p["texto"], p["fundo"], "O texto")
    s.meta["fonte_px"], s.meta["linhas"] = _resumo(blocos)


def lay_cartoes(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    pad_x, pad_y, vao = 40, 32, 22
    especs = _especs_titulo(s, slide) + _especs_itens(s, slide, s.largura_util - 2 * pad_x, "cartão",
                                                       primeiro_antes=48, entre=vao, extra_fim=2 * pad_y)
    disp = z["base"] - z["topo"]
    blocos, total, _ = s.ajustar(especs, disp)
    cabecalho, itens = _separar_itens(blocos)
    # sobrando espaço, os cartões ficam mais folgados (margem interna e vão), até um limite
    respiro = min(max(disp - total, 0) * 0.55 / max(3 * len(itens), 1), 16)
    pad_y += respiro
    total += 3 * respiro * len(itens)
    y = s.empilhar(cabecalho, z["topo"] + (disp - total) * 0.38, lambda b: (p["texto"], p["enfase"]))
    for i, grupo in enumerate(itens):
        y += (grupo[0].antes + respiro) if (cabecalho or i) else 0
        altura = sum(b.altura for b in grupo) + sum(b.antes for b in grupo[1:]) + 2 * pad_y
        s.retangulo(M, y, s.W - M, y + altura, p["cartao"], RAIO, p["borda"])
        yy = y + pad_y
        for k, b in enumerate(grupo):
            yy += b.antes if k else 0
            lead = b.tag[0] == "lead"
            s.texto(b, M + pad_x, yy, p["enfase"] if lead else p["texto"], p["enfase"])
            yy += b.altura
        y += altura
    s.checar_contraste(p["texto"], p["cartao"], "O texto dos cartões")
    s.meta["fonte_px"], s.meta["linhas"] = _resumo(blocos)


def lay_imagem(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    espaco_minimo, vao = round(0.34 * s.H), 40
    especs = [
        dict(texto=slide.get("titulo", ""), papel="titulo", faixa=ctx.tip["titulo"], leading=1.2, balancear=True, rotulo="título"),
        dict(texto=slide.get("texto", ""), papel="texto", faixa=ctx.tip["apoio"], leading=1.42, balancear="auto", antes=26, rotulo="apoio"),
    ]
    blocos, total, _ = s.ajustar(especs, z["base"] - z["topo"] - espaco_minimo - vao)
    y = s.empilhar(blocos, z["topo"], lambda b: (p["texto"], p["enfase"]))
    x, y_img, w = M, round(y + vao), s.largura_util
    h = round(z["base"] - y_img)
    s.meta["area_imagem"] = [x, y_img, w, h]
    if _imagem_presente(imagem, reservar) and imagem.caminho is not None:
        if _modo_encaixe(s, imagem, ajuste) == "conter":
            _colar_contida(s, imagem, x, y_img, w, h, RAIO)
        else:
            _colar_imagem(s, imagem, ajuste, x, y_img, w, h, RAIO)
            s.meta["imagem"]["modo"] = "cobrir"
    else:
        s.retangulo(x, y_img, x + w, y_img + h, p["cartao"], RAIO, p["borda"])
        if imagem is None:
            s.avisar("atencao", "imagem_ausente", "o layout 'imagem' precisa do objeto 'imagem' no post; o espaço da imagem ficou vazio.")
        _imagem_faltando(s, imagem)
    s.checar_contraste(p["texto"], p["fundo"], "O texto")
    s.meta["fonte_px"], s.meta["linhas"] = _resumo(blocos)


def lay_citacao(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    citacao = re.sub(r'^[\s"“”«]+|[\s"“”»]+$', "", str(slide.get("titulo", "")))
    autoria = str(slide.get("texto", "")).strip()
    if autoria and not re.match(r"^[—–-]", autoria):
        autoria = "— " + autoria
    fonte = ctx.fontes.obter("forte", 190)
    medida = Image.new("L", (190 * S * 2, 190 * S * 2), 0)
    ImageDraw.Draw(medida).text((190 * S // 2, 190 * S), "“", font=fonte, fill=255, anchor="ls")
    tinta = medida.getbbox() or (190 * S // 2, 190 * S - 60, 190 * S // 2, 190 * S)
    glifo_topo, glifo_altura = (tinta[1] - 190 * S) / S, (tinta[3] - tinta[1]) / S
    glifo_esquerda = (tinta[0] - 190 * S // 2) / S
    especs = [
        dict(texto=citacao, papel="titulo", faixa=ctx.tip["titulo"], leading=1.26, balancear=True, rotulo="citação"),
        dict(texto=autoria, papel="texto", faixa=ctx.tip["apoio"], leading=1.4, antes=38, rotulo="autoria"),
    ]
    disp = z["base"] - z["topo"]
    blocos, total, _ = s.ajustar(especs, disp - glifo_altura - 44)
    y = z["topo"] + (disp - (glifo_altura + 44 + total)) * 0.40
    s.d.text((round((M - glifo_esquerda) * S), round((y - glifo_topo) * S)), "“", font=fonte, fill=p["enfase"], anchor="ls")
    s.empilhar(blocos, y + glifo_altura + 44, lambda b: (p["texto"] if b.rotulo == "citação" else p["suave"], p["enfase"]))
    s.checar_contraste(p["texto"], p["fundo"], "O texto")
    s.checar_contraste(p["suave"], p["fundo"], "A autoria", 3.0)
    s.meta["fonte_px"], s.meta["linhas"] = _resumo(blocos)


def lay_cta(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    cfg = ctx.cfg
    if p["escuro"]:
        s.brilho(s.W * 0.92, s.H * 0.06, s.W * 0.95, 0.22)
    avatar, diam = cfg["avatar"], 124
    largura_nome = s.largura_util - (diam + 32 if avatar else 0)
    nome = BlocoTexto(ctx.fontes, cfg["nome_exibicao"], "titulo", 34, largura_nome, 1.2) if cfg["nome_exibicao"] else None
    arroba = BlocoTexto(ctx.fontes, cfg["arroba"], "texto", 28, largura_nome, 1.2) if cfg["arroba"] else None
    texto_cab = (nome.altura if nome else 0) + (arroba.altura if arroba else 0) + (6 if nome and arroba else 0)
    cabecalho = max(diam if avatar else 0, texto_cab)
    folga = 64 if cabecalho else 0
    especs = [
        dict(texto=slide.get("titulo", ""), papel="titulo", faixa=ctx.tip["capa"], leading=1.18, balancear=True, rotulo="chamada"),
        dict(texto=slide.get("texto", ""), papel="texto", faixa=ctx.tip["apoio"], leading=1.4, balancear="auto", antes=28, rotulo="apoio"),
    ]
    disp = z["base"] - z["topo"]
    blocos, total, _ = s.ajustar(especs, disp - cabecalho - folga)
    y = z["topo"] + (disp - (cabecalho + folga + total)) * 0.42
    if cabecalho:
        x_texto = M
        if avatar:
            img = ctx.abrir_imagem(avatar, p["fundo"])
            rosto = ImageOps.fit(img, (diam * S, diam * S), Image.Resampling.LANCZOS, centering=(0.5, 0.35))
            mascara = Image.new("L", rosto.size, 0)
            ImageDraw.Draw(mascara).ellipse((0, 0, rosto.width - 1, rosto.height - 1), fill=255)
            s.im.paste(rosto, (M * S, round((y + (cabecalho - diam) / 2) * S)), mascara)
            x_texto = M + diam + 32
        yy = y + (cabecalho - texto_cab) / 2
        if nome:
            s.texto(nome, x_texto, yy, p["texto"])
            yy += nome.altura + 6
        if arroba:
            s.texto(arroba, x_texto, yy, p["suave"])
        y += cabecalho + folga
    s.empilhar(blocos, y, lambda b: (p["texto"] if b.rotulo == "chamada" else p["suave"], p["enfase"]))
    s.checar_contraste(p["texto"], p["fundo"], "A chamada")
    s.checar_contraste(p["suave"], p["fundo"], "O apoio", 3.0)
    s.meta["fonte_px"], s.meta["linhas"] = _resumo(blocos)


def lay_capa(s: Slide, slide, ajuste, imagem, reservar) -> None:
    ctx, z, p = s.ctx, s.zona, s.paleta
    if str(slide.get("texto", "")).strip():
        s.avisar("info", "capa_com_apoio", "a capa mostra só a chamada (título); o campo 'texto' dela não é desenhado.")
    titulo = slide.get("titulo", "")
    palavras = len(texto_limpo(titulo).split())
    if palavras > 12:
        s.avisar("info", "capa_longa", f"a chamada tem {palavras} palavras; o padrão é até 12.")
    espec = dict(texto=titulo, papel="titulo", faixa=ctx.tip["capa"], leading=1.18, balancear=True, rotulo="chamada")
    tem_imagem = _imagem_presente(imagem, reservar)
    _imagem_faltando(s, imagem)
    variante = ajuste.get("variante")
    if tem_imagem:
        if variante not in ("degrade", "faixa"):
            variante = "faixa" if imagem.tipo == "foto" else "degrade"
    else:
        variante = "tipografica"
    s.meta["variante"] = variante
    H, W, base = s.H, s.W, z["base"]
    cobertura = misturar(p["fundo"], BRANCO, 0.25)

    if variante == "faixa":
        escolhido, erro = None, None
        for fracao in (0.34, 0.38, 0.42, 0.46, 0.50):
            faixa_h = round(H * fracao)
            topo_texto = H - faixa_h + 56
            try:
                blocos, total, k = s.ajustar([espec], base - topo_texto)
            except NaoCabe as falha:
                erro = falha
                continue
            escolhido = (faixa_h, topo_texto, blocos, total)
            if k >= 0.7:
                break
        if escolhido is None:
            raise erro
        faixa_h, topo_texto, blocos, total = escolhido
        s.meta["area_imagem"] = [0, 0, W, H - faixa_h]
        if imagem.caminho is not None:
            _colar_imagem(s, imagem, ajuste, 0, 0, W, H - faixa_h)
        else:
            s.retangulo(0, 0, W, H - faixa_h, cobertura)
        s.retangulo(0, H - faixa_h, W, H, p["fundo"])
        s.texto(blocos[0], M, topo_texto + ((base - topo_texto) - total) / 2, p["texto"], p["enfase"])
        s.checar_contraste(p["texto"], p["fundo"], "A chamada")
    elif variante == "degrade":
        blocos, total, _ = s.ajustar([espec], 0.45 * H)
        y = base - total
        s.meta["area_imagem"] = [0, 0, W, H]
        if imagem.caminho is not None:
            _colar_imagem(s, imagem, ajuste, 0, 0, W, H)
        else:
            s.retangulo(0, 0, W, H, cobertura)
        s.degrade_vertical(y - 0.26 * H, y - 20, p["fundo"], 0.93)
        pior = s.pior_contraste_regiao((M, y, W - M, y + total), p["texto"])
        s.texto(blocos[0], M, y, p["texto"], p["enfase"])
        s.contrastes.append(pior)
        if pior < 4.5:
            s.avisar("atencao", "contraste_baixo",
                     f"a chamada tem contraste {pior:.1f}:1 sobre a imagem. Use a variante 'faixa' ou uma imagem mais escura embaixo.")
    else:
        if p["escuro"]:
            s.brilho(W * 0.9, H * 0.08, W * 1.0, 0.24)
        topo = max(z["topo"], 88)
        blocos, total, _ = s.ajustar([espec], max(0.3 * H, base - topo))
        s.texto(blocos[0], M, topo + ((base - topo) - total) * 0.55, p["texto"], p["enfase"])
        s.checar_contraste(p["texto"], p["fundo"], "A chamada")
    s.meta["fonte_px"] = {"chamada": blocos[0].px}
    s.meta["linhas"] = blocos[0].n_linhas


FUNCOES = {"capa": lay_capa, "texto": lay_texto, "lista": lay_lista, "cartoes": lay_cartoes,
           "imagem": lay_imagem, "citacao": lay_citacao, "cta": lay_cta}


# ---------------------------------------------------------------- acabamento

def _legibilidade_logo(s: Slide, logo: Image.Image, x: int, y: int) -> float:
    """Contraste do logo com o que há embaixo dele, medido por trechos (pega o pior pedaço, não a média)."""
    fundo = s.im.crop((x, y, x + logo.width, y + logo.height)).resize((16, 4), Image.Resampling.BOX)
    tinta = logo.resize((16, 4), Image.Resampling.BOX)
    tp, fp = tinta.load(), fundo.load()
    notas = sorted(contraste(tp[x, y][:3], fp[x, y]) for y in range(4) for x in range(16) if tp[x, y][3] >= 40)
    return notas[len(notas) // 8] if notas else 21.0


def _desenhar_logo(s: Slide) -> None:
    ctx = s.ctx
    cfg = ctx.cfg["logo"]
    if not cfg or not ctx._logos:
        return
    candidatos = {t: _logo.ajustar(base, cfg["largura_px"], ALTURA_LOGO_MAX, S) for t, base in ctx._logos.items()}
    pos = cfg["posicao"]

    def canto(logo: Image.Image) -> tuple[int, int]:
        x = M * S if pos.endswith("esquerda") else s.W * S - M * S - logo.width
        y = M * S if pos.startswith("superior") else s.H * S - M * S - logo.height
        return x, y

    preferido, escolha, melhor = s.paleta["logo"], None, -1.0
    for tema, img in candidatos.items():
        valor = _legibilidade_logo(s, img, *canto(img))
        if tema == preferido and valor >= 3.0:
            escolha, melhor = tema, valor
            break
        if valor > melhor:
            escolha, melhor = tema, valor
    logo = candidatos[escolha]
    lx, ly = canto(logo)
    s.im.paste(logo, (lx, ly), logo)
    s.logo_caixa = (lx / S, ly / S, (lx + logo.width) / S, (ly + logo.height) / S)
    s.meta["logo"] = {"versao": "fundo_claro" if escolha == "claro" else "fundo_escuro", "posicao": pos, "contraste": round(melhor, 2)}
    if melhor < 1.7:
        s.avisar("atencao", "logo_invisivel",
                 f"o logo tem contraste {melhor:.1f}:1 com o que há embaixo dele e quase não aparece. "
                 "Mude o enquadramento (--foco), troque a imagem ou a posição do logo no visual.json; não coloque caixa nem halo atrás do logo.")
    elif melhor < 3.0:
        s.avisar("info", "logo_pouco_contraste",
                 f"o logo tem pouco contraste ({melhor:.1f}:1) com o que há embaixo dele. Confira no celular; se ficar difícil de ver, mude o enquadramento (--foco) ou a imagem.")


def _desenhar_rodape(s: Slide) -> None:
    """Numeração (NN/TT) e rodapé (nome e arroba), só quando o visual.json pede. Nunca por cima do logo."""
    cfg = s.ctx.cfg
    if not (cfg["numeracao"] or cfg["rodape"]):
        return
    fontes, p = s.ctx.fontes, s.paleta
    cor = p["texto"] if s.meta.get("variante") in ("degrade", "faixa") else p["suave"]
    numero = f"{int(s.n):02d}/{s.total:02d}" if cfg["numeracao"] else ""
    nome = cfg["nome_exibicao"]
    arroba = cfg["arroba"]
    linha_base = s.H - 62
    esquerda, direita = float(M), float(s.W - M)
    logo_embaixo = s.logo_caixa is not None and s.logo_caixa[1] > s.H / 2
    if logo_embaixo:
        if s.logo_caixa[0] < s.W / 2:
            esquerda = s.logo_caixa[2] + 32
        else:
            direita = s.logo_caixa[0] - 32

    def escrever(texto: str, x: float, px: int) -> None:
        s.d.text((round(x * S), linha_base * S), texto, font=fontes.obter("texto", px), fill=cor, anchor="ls")

    def cabe(texto: str, px: int, livre: float) -> bool:
        return fontes.largura("texto", px, texto) <= livre

    if cfg["rodape"]:
        opcoes = [" · ".join(v for v in (numero, nome, arroba) if v), " · ".join(v for v in (numero, arroba) if v)]
        if not logo_embaixo and numero:
            opcoes = [" · ".join(v for v in (nome, arroba) if v), arroba]
        for px in (24, 20):
            texto = next((o for o in opcoes if o and cabe(o, px, direita - esquerda)), None)
            if texto:
                break
        if texto is None:
            s.avisar("info", "rodape_nao_coube", "o rodapé não coube ao lado do logo e foi omitido.")
            return
        largura = fontes.largura("texto", px, texto)
        if logo_embaixo and s.logo_caixa[0] >= s.W / 2:
            escrever(texto, esquerda, px)
        elif logo_embaixo:
            escrever(texto, direita - largura, px)
        else:
            escrever(texto, esquerda, px)
            if numero:
                escrever(numero, direita - fontes.largura("texto", px, numero), px)
    elif numero:
        largura = fontes.largura("texto", 24, numero)
        escrever(numero, esquerda if (logo_embaixo and s.logo_caixa[0] >= s.W / 2) else direita - largura, 24)


def _checar_caracteres(s: Slide, slide: dict) -> None:
    fontes = s.ctx.fontes
    todo_texto = " ".join([str(slide.get("titulo") or ""), str(slide.get("texto") or "")] + [str(i) for i in slide.get("itens") or []])
    if re.search(r"(?i)\bfontes?\s*[:\u2013\u2014-]\s", todo_texto):
        s.avisar("atencao", "fonte_na_arte",
                 "o texto cita 'Fonte:'. A fonte fica só no JSON do post (fontes e fonte_interna), nunca na arte nem na legenda.")
    faltam: list[str] = []
    for campo, papel in (("titulo", "titulo"), ("texto", "texto")):
        faltam += [c for c in fontes.ausentes(texto_limpo(slide.get(campo, "")), papel) if c not in faltam]
    for item in slide.get("itens") or []:
        faltam += [c for c in fontes.ausentes(texto_limpo(item), "texto") if c not in faltam]
    if faltam:
        s.avisar("atencao", "caractere_sem_glifo",
                 "a fonte não desenha estes caracteres: " + " ".join(faltam) +
                 ". Eles aparecem como quadradinhos; troque ou remova (emojis e símbolos não entram nas artes).")


def renderizar_slide(ctx: Contexto, slide: dict, total: int, ajuste: dict | None = None,
                     imagem: ImagemSlide | None = None, reservar: bool = False):
    """Desenha um slide. Devolve (imagem 1x, meta, avisos). Levanta ErroSlide ou NaoCabe."""
    ajuste = ajuste or {}
    layout = slide.get("layout")
    if layout not in FUNCOES:
        raise ErroSlide(slide.get("n"), layout, f"layout desconhecido. Use um destes: {', '.join(FUNCOES)}.")
    tema = ajuste.get("tema") or TEMA_PADRAO[layout]
    if tema not in ctx.paletas:
        raise ErroSlide(slide.get("n"), layout, f"tema '{tema}' desconhecido. Use claro, escuro ou destaque.")
    trocou_tema = None
    com_imagem = imagem is not None and layout in ("capa", "imagem") and (imagem.caminho is not None or reservar)
    if not ajuste.get("tema") and ctx._logos and not com_imagem:
        preferido = ctx.paletas[tema]["logo"]
        if preferido not in ctx._logos:
            outro = "escuro" if tema == "claro" else "claro"
            if ctx.paletas[outro]["logo"] in ctx._logos:
                trocou_tema, tema = (tema, outro), outro
    s = Slide(ctx, ctx.paletas[tema], slide.get("n"), total, layout)
    if trocou_tema:
        s.avisos.append(aviso(
            "info", "tema_trocado",
            f"O visual.json só tem o logo para fundo {trocou_tema[1]}: os slides que seriam {trocou_tema[0]}s saíram no tema {trocou_tema[1]} para o logo aparecer. "
            "Para usar os dois temas, adicione o outro logo em logo.fundo_claro e logo.fundo_escuro.", slide.get("n")))
    if imagem is not None and layout not in ("capa", "imagem") and imagem.caminho is not None:
        s.avisar("info", "imagem_ignorada", f"o layout '{layout}' não usa imagem; ela foi ignorada. Use o layout 'imagem' ou 'capa'.")
    FUNCOES[layout](s, slide, ajuste, imagem, reservar)
    _checar_caracteres(s, slide)
    _desenhar_logo(s)
    _desenhar_rodape(s)
    s.meta.update(layout=layout, tema=tema)
    s.meta["contraste_minimo"] = round(min(s.contrastes), 2) if s.contrastes else None
    return s.im.resize((ctx.W, ctx.H), Image.Resampling.LANCZOS), s.meta, s.avisos
