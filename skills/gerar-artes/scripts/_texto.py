"""Texto nativo das artes: fontes, destaques com **asteriscos**, quebra de linha e ajuste de tamanho.

Quem desenha o texto é o código (Pillow), nunca a IA. Tudo é medido em pixels de uma arte de 1080 px
de largura (1x); o desenho acontece em 2x (S) e a imagem final é reduzida, o que deixa as bordas suaves.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import ImageFont

S = 2

_ESPACO = re.compile(r"[ \t]+")


class SemEspaco(Exception):
    """O texto não cabe nem no menor tamanho permitido."""

    def __init__(self, sobra: float, excesso_x: float, blocos):
        super().__init__("texto não cabe")
        self.sobra = sobra
        self.excesso_x = excesso_x
        self.blocos = blocos


class Fontes:
    """Abre as fontes por papel: titulo (negrito), texto (regular) e forte (extra negrito)."""

    PESOS = {"titulo": 700, "texto": 400, "forte": 800}

    def __init__(self, titulo: Path, texto: Path, forte: Path | None = None):
        self.caminhos = {"titulo": Path(titulo), "texto": Path(texto), "forte": Path(forte or titulo)}
        self._cache: dict = {}
        self._notdef: dict = {}

    def obter(self, papel: str, px: float) -> ImageFont.FreeTypeFont:
        chave = (papel, round(px * S))
        if chave not in self._cache:
            fonte = ImageFont.truetype(str(self.caminhos[papel]), chave[1])
            try:
                eixos = fonte.get_variation_axes()
            except (OSError, AttributeError):
                eixos = None
            if eixos:
                valores = []
                for eixo in eixos:
                    nome = eixo["name"].decode("utf-8", "ignore") if isinstance(eixo["name"], bytes) else str(eixo["name"])
                    valores.append(self.PESOS[papel] if nome.lower() == "weight" else eixo["default"])
                try:
                    fonte.set_variation_by_axes(valores)
                except OSError:
                    pass
            self._cache[chave] = fonte
        return self._cache[chave]

    def largura(self, papel: str, px: float, texto: str) -> float:
        return self.obter(papel, px).getlength(texto) / S

    def ausentes(self, texto: str, papel: str = "texto") -> list[str]:
        """Caracteres do texto que a fonte não desenha (aparecem como quadradinho)."""
        fonte = self.obter(papel, 40)
        if papel not in self._notdef:
            self._notdef[papel] = (fonte.getlength("\U0010FFFF"), fonte.getbbox("\U0010FFFF"))
        faltam = []
        for letra in dict.fromkeys(texto):
            if letra.isspace() or ord(letra) < 32 or letra in faltam:
                continue
            if (fonte.getlength(letra), fonte.getbbox(letra)) == self._notdef[papel]:
                faltam.append(letra)
        return faltam


# ---------------------------------------------------------------- marcação

def texto_limpo(texto: str) -> str:
    """Tira os asteriscos de destaque."""
    return str(texto or "").replace("**", "")


def tipografar(linha: str) -> str:
    """Aspas retas viram aspas curvas e o apóstrofo no meio da palavra vira ’. Só no desenho; o post continua igual."""
    saida: list[str] = []
    ultimo = ""
    i = 0
    while i < len(linha):
        c = linha[i]
        if linha.startswith("**", i):
            saida.append("**")
            i += 2
            continue
        if c == '"':
            abre = ultimo == "" or ultimo.isspace() or ultimo in "([{\u2014\u2013-\u201c"
            c = "\u201c" if abre else "\u201d"
        elif c == "'" and ultimo.isalnum() and linha[i + 1:i + 2].isalnum():
            c = "\u2019"
        saida.append(c)
        ultimo = c
        i += 1
    return "".join(saida)


def analisar(texto: str) -> list[list[list[tuple[str, bool]]]]:
    """Divide em parágrafos > palavras > pedaços (texto, destaque). `**trecho**` vira destaque."""
    paragrafos = []
    for linha in str(texto or "").replace("\r\n", "\n").split("\n"):
        if linha.count("**") % 2:
            linha = linha.replace("**", "")
        linha = tipografar(linha)
        palavras, atual, destaque = [], [], False
        for parte in re.split(r"(\*\*)", linha):
            if parte == "**":
                destaque = not destaque
                continue
            for pedaco in re.split(r"([ \t]+)", parte):
                if pedaco == "":
                    continue
                if _ESPACO.fullmatch(pedaco):
                    if atual:
                        palavras.append(atual)
                        atual = []
                else:
                    atual.append((pedaco, destaque))
        if atual:
            palavras.append(atual)
        paragrafos.append(palavras)
    while paragrafos and not paragrafos[-1]:
        paragrafos.pop()
    return paragrafos


def _guloso(medidas: list[float], espaco: float, largura: float) -> list[list[int]]:
    linhas, atual, usado = [], [], 0.0
    for i, m in enumerate(medidas):
        extra = m if not atual else espaco + m
        if atual and usado + extra > largura + 0.01:
            linhas.append(atual)
            atual, usado = [i], m
        else:
            atual.append(i)
            usado += extra
    if atual:
        linhas.append(atual)
    return linhas


def _balanceado(medidas: list[float], espaco: float, largura: float) -> list[list[int]]:
    """Mesmo número de linhas do modo guloso, com linhas de tamanho parecido (bom para títulos)."""
    base = _guloso(medidas, espaco, largura)
    n = len(base)
    menor = max(medidas) if medidas else 0.0
    if n < 2 or menor > largura:
        return base
    baixo, alto = menor, largura
    for _ in range(18):
        meio = (baixo + alto) / 2
        if len(_guloso(medidas, espaco, meio)) <= n:
            alto = meio
        else:
            baixo = meio
    return _guloso(medidas, espaco, alto)


class BlocoTexto:
    """Um bloco de texto já quebrado em linhas, com altura conhecida e pronto para desenhar."""

    def __init__(self, fontes: Fontes, texto: str, papel: str, px: int, largura: float,
                 leading: float = 1.3, balancear=False):
        self.fontes, self.texto, self.papel, self.px, self.largura = fontes, texto, papel, int(px), float(largura)
        self.leading_px = round(self.px * leading)
        self.antes = 0
        self.extra = 0
        self.rotulo = papel
        self.tag = None
        self.espaco = fontes.largura(papel, self.px, " ")
        self.linhas: list[dict] = []
        self.excesso = 0.0
        self.palavra_longa = ""
        for palavras in analisar(texto):
            if not palavras:
                self.linhas.append({"palavras": [], "medidas": [], "largura": 0.0, "altura": round(self.leading_px * 0.55)})
                continue
            medidas = [self._medir(p) for p in palavras]
            maior = max(medidas)
            if maior - self.largura > self.excesso:
                self.excesso = maior - self.largura
                self.palavra_longa = "".join(t for t, _ in palavras[medidas.index(maior)])
            indices = _guloso(medidas, self.espaco, self.largura)
            if balancear == "auto":
                if len(indices) >= 2 and self._largura_linha(indices[-1], medidas) < 0.28 * self.largura:
                    indices = _balanceado(medidas, self.espaco, self.largura)
            elif balancear:
                indices = _balanceado(medidas, self.espaco, self.largura)
            for linha in indices:
                self.linhas.append({
                    "palavras": [palavras[i] for i in linha],
                    "medidas": [medidas[i] for i in linha],
                    "largura": self._largura_linha(linha, medidas),
                    "altura": self.leading_px,
                })
        self.altura = sum(linha["altura"] for linha in self.linhas)

    def _papel_pedaco(self, destaque: bool) -> str:
        return "titulo" if (destaque and self.papel == "texto") else self.papel

    def _medir(self, palavra) -> float:
        return sum(self.fontes.largura(self._papel_pedaco(d), self.px, t) for t, d in palavra)

    def _largura_linha(self, indices, medidas) -> float:
        return sum(medidas[i] for i in indices) + self.espaco * (len(indices) - 1)

    @property
    def n_linhas(self) -> int:
        return sum(1 for linha in self.linhas if linha["palavras"])

    @property
    def largura_maxima(self) -> float:
        return max((linha["largura"] for linha in self.linhas), default=0.0)

    def base_primeira_linha(self) -> float:
        """Distância do topo do bloco até a linha de base da primeira linha."""
        asc, desc = (v / S for v in self.fontes.obter(self.papel, self.px).getmetrics())
        return (self.leading_px - (asc + desc)) / 2 + asc

    def desenhar(self, d, x: float, y: float, cor, cor_destaque=None, alinhar: str = "esq", caixa: float | None = None) -> None:
        asc, desc = (v / S for v in self.fontes.obter(self.papel, self.px).getmetrics())
        cor_destaque = cor_destaque or cor
        topo = y
        for linha in self.linhas:
            if linha["palavras"]:
                base = topo + (self.leading_px - (asc + desc)) / 2 + asc
                xx = x
                if alinhar == "centro":
                    xx = x + ((caixa or self.largura) - linha["largura"]) / 2
                for i, palavra in enumerate(linha["palavras"]):
                    if i:
                        xx += self.espaco
                    for trecho, destaque in palavra:
                        fonte = self.fontes.obter(self._papel_pedaco(destaque), self.px)
                        d.text((round(xx * S), round(base * S)), trecho, font=fonte,
                               fill=cor_destaque if destaque else cor, anchor="ls")
                        xx += fonte.getlength(trecho) / S
            topo += linha["altura"]


def ajustar_pilha(fontes: Fontes, especs: list[dict], altura_max: float, largura_padrao: float):
    """Acha o maior tamanho em que todos os blocos cabem juntos.

    Cada spec: texto, papel, faixa=(menor, maior) em px, leading, balancear, largura, antes (espaço antes
    do bloco), extra (altura somada depois dele). Os tamanhos andam juntos entre o menor e o maior.
    Devolve (blocos, altura_total, posição 0..1 na faixa). Levanta SemEspaco se nem o menor couber.
    """
    ativos = [e for e in especs if str(e.get("texto") or "").strip()]
    if not ativos:
        return [], 0.0, 1.0
    passos = max(1, max(e["faixa"][1] - e["faixa"][0] for e in ativos))
    ultimo = None
    for k in range(passos, -1, -1):
        blocos = []
        for e in ativos:
            menor, maior = e["faixa"]
            px = round(menor + (maior - menor) * k / passos)
            bloco = BlocoTexto(fontes, e["texto"], e["papel"], px, e.get("largura", largura_padrao),
                               e.get("leading", 1.3), e.get("balancear", False))
            bloco.antes = e.get("antes", 0)
            bloco.extra = e.get("extra", 0)
            bloco.rotulo = e.get("rotulo", e["papel"])
            bloco.tag = e.get("tag")
            blocos.append(bloco)
        total = sum(b.altura + b.extra for b in blocos) + sum(b.antes for b in blocos[1:])
        excesso = max(b.excesso for b in blocos)
        ultimo = (blocos, total, excesso)
        if total <= altura_max and excesso <= 0:
            return blocos, total, k / passos
    blocos, total, excesso = ultimo
    raise SemEspaco(total - altura_max, excesso, blocos)
