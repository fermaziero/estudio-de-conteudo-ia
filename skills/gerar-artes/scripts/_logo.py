"""Logo oficial da marca: abre o arquivo, tira o fundo liso (quando existir) e ajusta ao tamanho.

O logo nunca é redesenhado nem recolorido. Se o arquivo já tem transparência, só é recortado.
Se tem um fundo de uma cor só (por exemplo, branco), toda a área dessa cor vira transparente (inclusive o miolo
das letras), preservando as bordas suavizadas. Partes do desenho que tenham exatamente a cor do fundo também somem:
o ideal é sempre entregar o PNG já com transparência. Fundo que não é liso (foto, degradê) é mantido e gera um aviso.
Usa só o Pillow.
"""
from __future__ import annotations

from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from _comum import ErroUsuario

LADO_MAXIMO = 1200
TOLERANCIA = 14
_CACHE: dict = {}


def carregar(caminho: Path) -> tuple[Image.Image, list[str]]:
    """Devolve (logo RGBA recortado, observações em português)."""
    caminho = Path(caminho)
    chave = (str(caminho), caminho.stat().st_mtime_ns)
    if chave not in _CACHE:
        _CACHE[chave] = _preparar(caminho)
    logo, notas = _CACHE[chave]
    return logo.copy(), list(notas)


def _preparar(caminho: Path) -> tuple[Image.Image, list[str]]:
    try:
        with Image.open(caminho) as arquivo:
            arquivo.load()
            logo = arquivo.convert("RGBA")
    except Exception as erro:
        raise ErroUsuario(f"Não consegui abrir o logo {caminho.name}: {erro}. Use um PNG (de preferência com fundo transparente).")
    if max(logo.size) > LADO_MAXIMO:
        fator = LADO_MAXIMO / max(logo.size)
        logo = logo.resize((max(1, round(logo.width * fator)), max(1, round(logo.height * fator))), Image.Resampling.LANCZOS)
    notas: list[str] = []
    alfa = logo.getchannel("A")
    if alfa.getextrema()[0] < 250:
        logo.putalpha(alfa.point(lambda v: 0 if v <= 2 else v))
    else:
        sem_fundo = _remover_fundo_liso(logo.convert("RGB"))
        if sem_fundo is None:
            notas.append(
                f"O logo {caminho.name} não tem transparência nem fundo de uma cor só; ele entra como veio. "
                "Prefira um PNG com fundo transparente."
            )
        else:
            logo = sem_fundo
            notas.append(f"O fundo liso do logo {caminho.name} foi removido (o arquivo original não é alterado).")
    caixa = logo.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if caixa is None:
        raise ErroUsuario(f"O logo {caminho.name} não tem pixels visíveis.")
    return logo.crop(caixa), notas


def _remover_fundo_liso(rgb: Image.Image) -> Image.Image | None:
    largura, altura = rgb.size
    px = rgb.load()
    borda: Counter = Counter()
    for x in range(largura):
        borda[px[x, 0]] += 1
        borda[px[x, altura - 1]] += 1
    for y in range(1, altura - 1):
        borda[px[0, y]] += 1
        borda[px[largura - 1, y]] += 1
    fundo, _ = borda.most_common(1)[0]
    perto = sum(n for cor, n in borda.items() if max(abs(cor[i] - fundo[i]) for i in range(3)) <= TOLERANCIA)
    if perto < 0.92 * sum(borda.values()):
        return None

    # Todo pixel da cor do fundo vira transparente, inclusive o miolo das letras (o "o", o "d", o "A").
    r, g, b = ImageChops.difference(rgb, Image.new("RGB", rgb.size, fundo)).split()
    maximo = ImageChops.lighter(ImageChops.lighter(r, g), b)
    externo = maximo.point(lambda v: 255 if v <= TOLERANCIA else 0)
    if externo.histogram()[255] < 0.03 * largura * altura:
        return None

    banda = ImageChops.subtract(externo.filter(ImageFilter.MaxFilter(5)), externo)
    ext, ban = externo.load(), banda.load()
    pontos = [(i % largura, i // largura) for i, v in enumerate(banda.tobytes()) if v]

    referencia: dict = {}
    fila: deque = deque()
    vizinhos = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for x, y in pontos:
        for dx, dy in vizinhos:
            nx, ny = x + dx, y + dy
            if 0 <= nx < largura and 0 <= ny < altura and not ext[nx, ny] and not ban[nx, ny]:
                referencia[(x, y)] = px[nx, ny]
                fila.append((x, y))
                break
    while fila:
        x, y = fila.popleft()
        for dx, dy in vizinhos:
            nx, ny = x + dx, y + dy
            if 0 <= nx < largura and 0 <= ny < altura and ban[nx, ny] and (nx, ny) not in referencia:
                referencia[(nx, ny)] = referencia[(x, y)]
                fila.append((nx, ny))

    saida = rgb.convert("RGBA")
    cores = saida.load()
    alfa = ImageChops.invert(externo)
    opacidade = alfa.load()
    for x, y in pontos:
        pixel = px[x, y]
        ref = referencia.get((x, y))
        if ref is not None:
            direcao = [fundo[i] - ref[i] for i in range(3)]
            norma = sum(v * v for v in direcao)
            if norma >= 30:
                a = sum((fundo[i] - pixel[i]) * direcao[i] for i in range(3)) / norma
                a = min(1.0, max(0.0, a))
                cor = ref
            else:
                a = 1.0 if max(abs(pixel[i] - fundo[i]) for i in range(3)) > TOLERANCIA else 0.0
                cor = pixel
        else:
            a, cor = _cor_para_alfa(pixel, fundo)
        if a < 0.04:
            a = 0.0
        elif a > 0.96:
            a = 1.0
        opacidade[x, y] = round(a * 255)
        cores[x, y] = (cor[0], cor[1], cor[2], 255)
    saida.putalpha(alfa)
    return saida


def _cor_para_alfa(pixel, fundo) -> tuple[float, tuple[int, int, int]]:
    """Plano B para bordas sem cor de referência: o menor alfa que reproduz o pixel."""
    alfa = 0.0
    for i in range(3):
        if pixel[i] > fundo[i]:
            alfa = max(alfa, (pixel[i] - fundo[i]) / max(255 - fundo[i], 1))
        elif pixel[i] < fundo[i]:
            alfa = max(alfa, (fundo[i] - pixel[i]) / max(fundo[i], 1))
    if alfa <= 0:
        return 0.0, pixel
    cor = tuple(min(255, max(0, round(fundo[i] + (pixel[i] - fundo[i]) / alfa))) for i in range(3))
    return alfa, cor  # type: ignore[return-value]


def ajustar(logo: Image.Image, largura_px: int, altura_max: int, escala: int) -> Image.Image:
    """Redimensiona para `largura_px` (em 1x), sem passar de `altura_max`, já na escala de desenho."""
    largura = largura_px * escala
    altura = round(largura * logo.height / logo.width)
    if altura > altura_max * escala:
        altura = altura_max * escala
        largura = round(altura * logo.width / logo.height)
    return logo.resize((max(1, largura), max(1, altura)), Image.Resampling.LANCZOS)


def cor_media(logo: Image.Image) -> tuple[int, int, int]:
    """Cor média dos pixels visíveis, para decidir a variante de logo pelo contraste."""
    pequeno = logo.resize((24, 24), Image.Resampling.BOX)
    pixels = pequeno.load()
    soma = [0.0, 0.0, 0.0]
    peso = 0.0
    for y in range(24):
        for x in range(24):
            r, g, b, a = pixels[x, y]
            soma[0] += r * a
            soma[1] += g * a
            soma[2] += b * a
            peso += a
    if peso <= 0:
        return (128, 128, 128)
    return tuple(round(v / peso) for v in soma)  # type: ignore[return-value]
