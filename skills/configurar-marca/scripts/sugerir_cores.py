#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sugere a paleta de cores da marca a partir do logo.

Lê o logo (por padrão, o de fundo claro definido em visual.json), encontra as cores mais presentes e
monta as seis cores que o gerador de artes usa: fundo, texto, destaque, suave, fundo_escuro e
texto_sobre_escuro, todas com contraste de leitura conferido.

Por padrão só mostra a sugestão e não altera nada. Depois que a pessoa disser que está de acordo, rode de
novo com --aplicar: a versão anterior do visual.json é guardada em _antes-cores/ e só o campo "cores" muda.
"""
from __future__ import annotations

import colorsys
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _marca_comum as c  # noqa: E402

CHAVES_CORES = ["fundo", "texto", "destaque", "suave", "fundo_escuro", "texto_sobre_escuro"]
FUNCAO_DAS_CORES = {
    "fundo": "fundo das artes claras",
    "texto": "texto principal sobre o fundo claro",
    "destaque": "cor de destaque (títulos, marcações)",
    "suave": "texto de apoio sobre o fundo claro",
    "fundo_escuro": "fundo das artes escuras (último slide)",
    "texto_sobre_escuro": "texto sobre o fundo escuro",
}
# Exemplos para quando o logo não tem cor própria. Não vêm do logo: a pessoa escolhe.
EXEMPLOS_DE_DESTAQUE = [("azul", "#1F5FBF"), ("verde-água", "#0E7C66"), ("laranja", "#C2410C")]


@dataclass
class CorDoLogo:
    rgb: tuple[float, float, float]
    peso: float
    h: float
    s: float
    v: float

    @property
    def cromatica(self) -> bool:
        return self.s >= 0.25 and self.v >= 0.15

    @property
    def hex(self) -> str:
        return c.rgb_para_hex(self.rgb)


def distancia(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def distancia_de_matiz(a: float, b: float) -> float:
    d = abs(a - b)
    return min(d, 1 - d)


def cores_do_logo(pixels) -> list[CorDoLogo]:
    """Agrupa os pixels opacos em poucas cores, da mais para a menos presente. Ignora o branco de fundo e os
    tons quase brancos que aparecem na borda suavizada do desenho."""
    baldes: dict[tuple[int, int, int], list[float]] = {}
    for r, g, b, a in pixels:
        if a < 128 or min(r, g, b) >= 238 or (max(r, g, b) >= 205 and max(r, g, b) - min(r, g, b) <= 60):
            continue
        soma = baldes.setdefault((r >> 4, g >> 4, b >> 4), [0, 0, 0, 0])
        soma[0] += r
        soma[1] += g
        soma[2] += b
        soma[3] += 1
    total = sum(s[3] for s in baldes.values())
    if total == 0:
        return []
    grupos: list[list[float]] = []
    for soma in sorted(baldes.values(), key=lambda s: -s[3]):
        cor = (soma[0] / soma[3], soma[1] / soma[3], soma[2] / soma[3])
        for grupo in grupos:
            if distancia(cor, (grupo[0] / grupo[3], grupo[1] / grupo[3], grupo[2] / grupo[3])) < 45:
                for i in range(4):
                    grupo[i] += soma[i]
                break
        else:
            grupos.append(list(soma))
    resultado = []
    for g in sorted(grupos, key=lambda x: -x[3]):
        peso = g[3] / total
        if peso < 0.01:
            continue
        rgb = (g[0] / g[3], g[1] / g[3], g[2] / g[3])
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in rgb))
        resultado.append(CorDoLogo(rgb, peso, h, s, v))
    return resultado


def escolher_papeis(cores: list[CorDoLogo]) -> tuple[CorDoLogo | None, CorDoLogo | None]:
    """Primária (a mais presente com cor) e destaque (uma cor secundária viva, se houver; senão, a primária)."""
    cromaticas = [x for x in cores if x.cromatica]
    if not cromaticas:
        return None, None
    primaria = cromaticas[0]
    minimo = 0.03 if primaria.v < 0.45 else 0.08
    candidatas = [x for x in cromaticas[1:]
                  if x.peso >= minimo and distancia_de_matiz(x.h, primaria.h) >= 25 / 360 and x.s >= 0.45 and x.v >= 0.35]
    destaque = max(candidatas, key=lambda x: x.s * x.v * x.peso ** 0.5) if candidatas else primaria
    return primaria, destaque


def hsv_para_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def montar_paleta(cores: list[CorDoLogo], destaque_forcado: str | None):
    """Devolve (paleta {chave: (r, g, b)}, notas sobre como foi montada)."""
    notas: list[str] = []
    primaria, destaque = escolher_papeis(cores)
    forcado = c.hex_para_rgb(destaque_forcado) if destaque_forcado else None

    if primaria is not None:
        familia_h = primaria.h
        familia_s = min(primaria.s, 0.8)
    elif forcado is not None:
        familia_h, familia_s, _ = colorsys.rgb_to_hsv(*(x / 255 for x in forcado))
        familia_s = min(familia_s, 0.8)
    else:
        familia_h = None
        familia_s = 0.0
        notas.append("O logo não tem uma cor de destaque (é preto, branco ou cinza). Usei tons neutros; veja abaixo "
                     "exemplos de cor de destaque para a pessoa escolher, se quiser.")

    if familia_h is None:
        fundo = (247, 247, 245)
        fundo_escuro = (22, 22, 22)
        texto = (27, 27, 27)
        suave = c.ajustar_contraste((110, 110, 110), [fundo], 4.6)
    else:
        fundo = hsv_para_rgb(familia_h, 0.04, 0.975)
        if primaria is not None and primaria.v < 0.45:
            fundo_escuro = hsv_para_rgb(primaria.h, min(primaria.s, 0.85), max(0.10, min(primaria.v, 0.22)))
            notas.append("O fundo escuro segue o tom escuro do próprio logo.")
        else:
            fundo_escuro = hsv_para_rgb(familia_h, min(familia_s + 0.2, 0.7), 0.17)
        texto = c.ajustar_contraste(hsv_para_rgb(familia_h, 0.30, 0.15), [fundo], 12)
        suave = c.ajustar_contraste(hsv_para_rgb(familia_h, 0.20, 0.42), [fundo], 4.6)

    if forcado is not None:
        destaque_rgb = forcado
        notas.append("A cor de destaque é a que a pessoa informou; não foi alterada.")
    elif destaque is not None:
        base = tuple(int(round(x)) for x in destaque.rgb)
        destaque_rgb = c.ajustar_contraste(base, [fundo, fundo_escuro], 3.0)
        if destaque_rgb != base:
            notas.append(f"A cor de destaque do logo ({c.rgb_para_hex(base)}) foi clareada ou escurecida um pouco para ter "
                         "contraste suficiente sobre os dois fundos.")
    else:
        dominante = cores[0].rgb if cores else (90, 90, 90)
        destaque_rgb = c.ajustar_contraste(tuple(int(round(x)) for x in dominante), [fundo, fundo_escuro], 3.0)
    paleta = {"fundo": fundo, "texto": texto, "destaque": destaque_rgb, "suave": suave,
              "fundo_escuro": fundo_escuro, "texto_sobre_escuro": (255, 255, 255)}
    return paleta, notas


def conferir_contrastes(paleta: dict) -> list[tuple[str, str, float, float]]:
    pares = [("texto", "fundo", 4.5), ("suave", "fundo", 4.5), ("destaque", "fundo", 3.0),
             ("texto_sobre_escuro", "fundo_escuro", 4.5), ("destaque", "fundo_escuro", 3.0)]
    return [(f, b, c.contraste(paleta[f], paleta[b]), m) for f, b, m in pares]


def achar_logo(marca_dir: Path, visual, valor: str | None) -> tuple[Path | None, str | None]:
    if valor:
        caminho = Path(valor).expanduser()
        if not caminho.is_absolute():
            caminho = marca_dir / valor
        return (caminho, None) if caminho.is_file() else (None, f"não encontrei o arquivo {valor}")
    if isinstance(visual, dict) and isinstance(visual.get("logo"), dict):
        caminho, erro = c.caminho_dentro(marca_dir, visual["logo"].get("fundo_claro"))
        if not erro and caminho.is_file():
            return caminho, None
    pasta = marca_dir / "assets" / "logo"
    if pasta.is_dir():
        imagens = sorted((p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in c.EXT_IMAGEM),
                         key=lambda p: ("claro" not in p.name.lower(), p.name))
        if imagens:
            return imagens[0], None
    return None, "não encontrei um logo em assets/logo/"


def montar_parser() -> c.ParserPT:
    parser = c.criar_parser(
        "sugerir_cores.py",
        "Sugere a paleta de cores da marca a partir do logo, com contraste de leitura conferido. "
        "Sem --aplicar, só mostra a sugestão e não altera nada.",
        ["python -X utf8 skills/configurar-marca/scripts/sugerir_cores.py --marca minha-marca",
         "python -X utf8 skills/configurar-marca/scripts/sugerir_cores.py --marca minha-marca --destaque \"#0E7490\"",
         "python -X utf8 skills/configurar-marca/scripts/sugerir_cores.py --marca minha-marca --aplicar"],
        "Saída: 0 = sugestão feita (ou aplicada); 1 = não deu para sugerir (sem logo, imagem inválida...); 2 = marca não encontrada.",
    )
    c.opcoes_marca_e_raiz(parser)
    parser.add_argument("--logo", metavar="ARQUIVO",
                        help="logo a analisar (relativo à pasta da marca, ou caminho completo). Padrão: o logo de fundo claro do visual.json")
    parser.add_argument("--destaque", metavar="#RRGGBB",
                        help="usa esta cor, informada pela pessoa, como cor de destaque, e monta o resto em volta dela. "
                             "Escreva entre aspas (o # começa um comentário em alguns terminais) ou sem o #")
    parser.add_argument("--aplicar", action="store_true",
                        help="grava a paleta em visual.json (guarda a versão anterior em _antes-cores/). Use só depois do ok da pessoa")
    return parser


def main(argv: list[str] | None = None) -> int:
    c.configurar_saida()
    args = montar_parser().parse_args(argv)
    raiz = c.pasta_raiz(args.raiz)
    try:
        slug, marca_dir = c.resolver_marca(raiz, args.marca)
        if args.destaque:
            args.destaque = args.destaque.strip()
            if re.fullmatch(r"[0-9A-Fa-f]{6}", args.destaque):
                args.destaque = "#" + args.destaque
            if not c.RE_HEX.match(args.destaque):
                raise c.ErroUso(f"Cor inválida: {args.destaque!r}. Use o formato #RRGGBB, por exemplo \"#0E7490\" ou 0E7490.")
    except c.ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    arquivo_visual = marca_dir / "visual.json"
    visual, erro_visual = c.ler_json(arquivo_visual)
    if args.aplicar and (erro_visual or not isinstance(visual, dict)):
        print(f"ERRO: não dá para aplicar: visual.json {erro_visual or 'não é um objeto JSON'}.", file=sys.stderr)
        return 1

    cores: list[CorDoLogo] = []
    logo, erro_logo = achar_logo(marca_dir, visual, args.logo)
    if logo is not None:
        imagem, erro = c.abrir_imagem(logo)
        if erro:
            print(f"ERRO: {c.mostrar_caminho(logo, raiz)}: {erro}.", file=sys.stderr)
            return 1
        cores = cores_do_logo(c.pixels_rgba(imagem))
        print(f"Marca: {slug}")
        print(f"Logo analisado: {c.mostrar_caminho(logo, raiz)}")
        if not cores and not args.destaque:
            print("ERRO: não achei cores no logo (a imagem é toda clara ou transparente). Aponte o logo para fundo claro "
                  "com --logo ou informe a cor de destaque com --destaque.", file=sys.stderr)
            return 1
    elif args.destaque:
        print(f"Marca: {slug}")
        print(f"Sem logo para analisar ({erro_logo}); a paleta parte só da cor informada.")
    else:
        print(f"ERRO: {erro_logo}. Coloque o logo em assets/logo/ (veja a skill configurar-marca) ou informe a cor "
              "de destaque com --destaque.", file=sys.stderr)
        return 1

    if cores:
        print("\nCores encontradas no logo (da mais para a menos presente):")
        for i, cor in enumerate(cores[:6], 1):
            print(f"  {i}. {cor.hex}  {c.nome_aproximado(cor.rgb):<22} {round(cor.peso * 100):>3}% do desenho")

    paleta, notas = montar_paleta(cores, args.destaque.upper() if args.destaque else None)
    print("\nPaleta sugerida:")
    for chave in CHAVES_CORES:
        print(f"  {chave:<19} {c.rgb_para_hex(paleta[chave])}  {c.nome_aproximado(paleta[chave]):<22} {FUNCAO_DAS_CORES[chave]}")
    for nota in notas:
        print(f"  Obs.: {nota}")

    print("\nContraste de leitura (quanto maior, melhor):")
    ok_geral = True
    for frente, fundo, razao, minimo in conferir_contrastes(paleta):
        ok = razao >= minimo
        ok_geral = ok_geral and ok
        print(f"  {frente} sobre {fundo}: {c.formatar_numero(razao)}:1 (mínimo {c.formatar_numero(minimo)}:1)  "
              f"{'OK' if ok else 'ATENÇÃO: abaixo do mínimo'}")
    if not ok_geral:
        print("  Obs.: alguma cor ficou abaixo do mínimo recomendado. Isso acontece quando a pessoa impõe uma cor de "
              "destaque; o validar_marca.py vai repetir o aviso.")

    if not args.destaque and not any(x.cromatica for x in cores):
        print("\nExemplos de cor de destaque, se a pessoa quiser uma (não vêm do logo):")
        for nome, hexa in EXEMPLOS_DE_DESTAQUE:
            ajustada = c.ajustar_contraste(c.hex_para_rgb(hexa), [paleta["fundo"], paleta["fundo_escuro"]], 3.0)
            print(f"  {nome:<11} {c.rgb_para_hex(ajustada)}")
        print("  Para usar uma delas: rode de novo com --destaque <cor>.")

    if not args.aplicar:
        print("\nNada foi gravado. Mostre a paleta à pessoa; com o ok dela, rode de novo com --aplicar.")
        return 0

    copia = c.guardar_versao(arquivo_visual, "cores")
    visual["cores"] = {chave: c.rgb_para_hex(paleta[chave]) for chave in CHAVES_CORES}
    c.escrever_json(arquivo_visual, visual)
    print(f"\nPaleta gravada em {c.mostrar_caminho(arquivo_visual, raiz)}.")
    print(f"Versão anterior guardada em {c.mostrar_caminho(copia, raiz)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
