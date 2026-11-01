#!/usr/bin/env python3
"""Gera o lote.md: o resumo legível dos posts de um lote, para a pessoa ler e aprovar o texto.

Rode sempre a partir da raiz do projeto:

    python -X utf8 skills/criar-conteudo/scripts/montar_lote.py --marca <marca> --lote <lote>

No macOS e no Linux, use python3.

O lote.md é gerado a partir de posts/*.json e pode ser refeito a qualquer momento: não o edite à mão.
Antes de gerar, o script roda a mesma validação do validar_posts.py e para se houver erros
(use --forcar para gerar mesmo assim). Código de saída: 0 = gerado; 1 = há erros nos posts;
2 = problema de uso (marca ou lote não encontrados).
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validar_posts as vp  # noqa: E402  (script vizinho, na mesma pasta)

ROTULO_STATUS = {
    "rascunho": "Rascunho",
    "em_revisao": "Em revisão",
    "texto_aprovado": "Texto aprovado",
    "arte_pronta": "Arte pronta",
    "aprovado": "Aprovado",
    "agendado": "Agendado",
    "publicado": "Publicado",
    "erro": "Erro (veja o histórico)",
}
ROTULO_ETAPA = {"atracao": "Atração", "relacionamento": "Relacionamento", "conversao": "Conversão"}
ROTULO_FORMATO = {"carrossel": "Carrossel", "post_unico": "Post único", "reel": "Reel (só roteiro)"}
ROTULO_PAPEL = {"capa": "capa", "conteudo": "conteúdo", "cta": "chamada final"}
ROTULO_LAYOUT = {"capa": "capa", "texto": "texto", "lista": "lista", "cartoes": "cartões", "imagem": "imagem",
                 "citacao": "citação", "cta": "chamada final"}
ROTULO_VEREDITO = {"aprovar": "aprovar", "ajustar": "ajustar", "refazer": "refazer"}


def celula(texto) -> str:
    return re.sub(r"\s+", " ", str(texto)).replace("|", "\\|").strip()


def milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def uma_linha(texto) -> str:
    return re.sub(r"\s*\n\s*", " / ", str(texto).strip())


def cerca(texto: str) -> str:
    maior = max((len(m) for m in re.findall(r"`+", texto)), default=0)
    return "`" * max(3, maior + 1)


def nome_da_marca(pasta_marca: Path, slug: str) -> str:
    arquivo = pasta_marca / "visual.json"
    if arquivo.is_file():
        dados, _ = vp.ler_json(arquivo)
        if isinstance(dados, dict) and isinstance(dados.get("nome_exibicao"), str) and dados["nome_exibicao"].strip():
            return dados["nome_exibicao"].strip()
    return slug


def descricao_formato(d: dict) -> str:
    formato = d.get("formato")
    rotulo = ROTULO_FORMATO.get(formato, str(formato))
    slides = d.get("slides") if isinstance(d.get("slides"), list) else []
    partes = [rotulo]
    if formato == "carrossel":
        partes.append(f"{len(slides)} slides")
    if formato == "reel" and isinstance(d.get("roteiro"), list):
        partes.append(f"{len(d['roteiro'])} blocos")
    partes.append(f"proporção {d.get('proporcao')}")
    return " · ".join(partes)


def resumo_revisao(d: dict) -> str:
    r = d.get("revisao")
    if not isinstance(r, dict):
        return "ainda não revisado"
    return f"{ROTULO_VEREDITO.get(r.get('veredito'), r.get('veredito'))} ({r.get('data')})"


def bloco_slide(s: dict) -> list[str]:
    papel = ROTULO_PAPEL.get(s.get("papel"), s.get("papel"))
    layout = ROTULO_LAYOUT.get(s.get("layout"), s.get("layout"))
    linhas = [f"**Slide {s.get('n')} · {papel}** (modelo de página: {layout})"]
    if s.get("titulo"):
        linhas.append(f"- **Título:** {uma_linha(s['titulo'])}")
    if str(s.get("texto", "")).strip():
        linhas.append(f"- **Apoio:** {uma_linha(s['texto'])}")
    itens = s.get("itens")
    if isinstance(itens, list) and itens:
        linhas.append("- **Itens:**")
        linhas += [f"  {i}. {uma_linha(item)}" for i, item in enumerate(itens, start=1)]
    img = s.get("imagem")
    if isinstance(img, dict):
        tipo = "foto" if img.get("tipo") == "foto" else "gerada por IA, sem texto"
        detalhe = f"- **Imagem ({tipo}):** {uma_linha(img.get('descricao', ''))}"
        if img.get("tipo") == "foto" and img.get("arquivo"):
            detalhe += f" · arquivo: `{img['arquivo']}`"
        linhas.append(detalhe)
    if str(s.get("texto_alternativo", "")).strip():
        linhas.append(f"- *Texto alternativo (acessibilidade):* {uma_linha(s['texto_alternativo'])}")
    return linhas


def bloco_roteiro(d: dict) -> list[str]:
    roteiro = d.get("roteiro")
    if not isinstance(roteiro, list) or not roteiro:
        return []
    linhas = ["### Roteiro do vídeo", "", "| Tempo | O que se fala | O que aparece na tela |", "|---|---|---|"]
    for bloco in roteiro:
        if isinstance(bloco, dict):
            linhas.append(f"| {celula(bloco.get('tempo', ''))} | {celula(bloco.get('fala', ''))} | {celula(bloco.get('tela', ''))} |")
    return linhas + [""]


def bloco_post(posicao: int, d: dict) -> list[str]:
    titulo = d.get("titulo_interno") or d.get("id")
    linhas = [f"## {posicao}. {titulo}", ""]
    linhas += [
        f"- **Id:** `{d.get('id')}`",
        f"- **Formato:** {descricao_formato(d)}",
        f"- **Pilar:** {d.get('pilar')} · **Etapa do funil:** {ROTULO_ETAPA.get(d.get('etapa_funil'), d.get('etapa_funil'))}",
        f"- **O que a pessoa leva:** {uma_linha(d.get('objetivo', ''))}",
        f"- **De onde vem:** {uma_linha(d.get('de_onde_vem', ''))}",
        f"- **Chamada para ação:** {uma_linha(d.get('chamada', ''))}",
        f"- **Status:** {ROTULO_STATUS.get(d.get('status'), d.get('status'))}",
    ]
    rev = d.get("revisao")
    linhas.append(f"- **Revisão independente:** {resumo_revisao(d)}")
    if isinstance(rev, dict):
        pontos = [re.sub(r"^\s*\d+[.)]\s+", "", uma_linha(p)) for p in rev.get("pontos", []) if isinstance(p, str)]
        linhas += [f"  {i}. {texto}" for i, texto in enumerate(pontos, start=1)]
    if d.get("agendado_para"):
        linhas.append(f"- **Agendado para:** {d['agendado_para']}")
    pub = d.get("publicacao")
    if isinstance(pub, dict):
        linhas.append(f"- **Publicado em:** {pub.get('publicado_em')} · {pub.get('permalink')}")
    linhas.append("")

    slides = [s for s in d.get("slides", []) if isinstance(s, dict)] if isinstance(d.get("slides"), list) else []
    if d.get("formato") == "reel":
        linhas += bloco_roteiro(d)
        if slides:
            linhas += ["### Capa do vídeo", ""]
            for s in slides:
                linhas += bloco_slide(s) + [""]
    else:
        linhas += ["### Texto de cada slide", ""]
        for s in slides:
            linhas += bloco_slide(s) + [""]

    legenda = str(d.get("legenda", "")).strip()
    linhas += [f"### Legenda ({milhar(len(legenda))} de {milhar(vp.LIMITE_LEGENDA)} caracteres)", ""]
    marca = cerca(legenda)
    linhas += [f"{marca}text", legenda, marca, ""]
    hashtags = [h if h.startswith("#") else f"#{h}" for h in d.get("hashtags", []) if isinstance(h, str)]
    linhas += [("Hashtags: " + " ".join(hashtags)) if hashtags else "Hashtags: nenhuma", ""]

    pendencias = [p for p in d.get("confirmar", []) if isinstance(p, str)]
    linhas += ["### Pendências antes de publicar", ""]
    linhas += [f"- {p}" for p in pendencias] if pendencias else ["Nenhuma."]
    if pendencias:
        linhas += ["", "*Com pendência aberta, o post não pode ser publicado.*"]
    linhas.append("")

    fontes = [f for f in d.get("fontes", []) if isinstance(f, dict)]
    internas = [t for t in d.get("fontes_legenda_internas", []) if isinstance(t, str)]
    por_slide = [(s.get("n"), s["fonte_interna"]) for s in slides if str(s.get("fonte_interna", "")).strip()]
    linhas += ["### Fontes (uso interno: não aparecem na arte nem na legenda)", ""]
    if fontes or internas or por_slide:
        linhas += [f"- {f.get('nome')} · consultada em {f.get('data')} · {f.get('url')}" for f in fontes]
        linhas += [f"- Slide {n}: {uma_linha(t)}" for n, t in por_slide]
        linhas += [f"- Legenda: {uma_linha(t)}" for t in internas]
    else:
        linhas.append("Nenhuma fonte registrada.")
    linhas.append("")

    historico = [h for h in d.get("historico", []) if isinstance(h, dict)]
    linhas += ["### Histórico", ""]
    linhas += [f"- {h.get('data')} · {h.get('por')} · {uma_linha(h.get('evento', ''))}" for h in historico] or ["Sem eventos."]
    linhas.append("")
    return linhas


def montar_markdown(nome_marca: str, lote: str, posts: list[dict], hoje: date, ficticia: bool = False) -> str:
    linhas = [
        f"# Lote {lote} · {nome_marca}",
        "",
        f"> Gerado em {hoje.isoformat()} a partir de `posts/*.json`. Não edite este arquivo: peça o ajuste ao agente "
        "(ou edite o JSON do post) e gere o lote de novo.",
        "",
    ]
    if ficticia:
        linhas += [
            "> Exemplo fictício: a marca, as pessoas, os números e as frases deste lote não existem. "
            "Ele serve para testar o fluxo inteiro sem dados reais.",
            "",
        ]
    linhas += [
        "## Resumo",
        "",
        "| # | Post | Formato | Pilar | Etapa do funil | Status | Revisão | Pendências |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, d in enumerate(posts, start=1):
        pend = len([p for p in d.get("confirmar", []) if isinstance(p, str)])
        linhas.append(
            f"| {i} | {celula(d.get('titulo_interno', d.get('id')))} | {celula(descricao_formato(d))} | {celula(d.get('pilar'))} | "
            f"{ROTULO_ETAPA.get(d.get('etapa_funil'), d.get('etapa_funil'))} | {ROTULO_STATUS.get(d.get('status'), d.get('status'))} | "
            f"{celula(resumo_revisao(d))} | {pend if pend else 'nenhuma'} |"
        )
    linhas += [
        "",
        "## Como aprovar o texto",
        "",
        "Leia cada post abaixo. Depois responda no chat com o que decidiu, por exemplo: "
        "\"aprovo o texto do post 1 e quero ajustar o post 2: troque a capa por...\". "
        "Só depois do seu ok as artes são geradas. Nada é publicado sem a sua aprovação.",
        "",
        "---",
        "",
    ]
    for i, d in enumerate(posts, start=1):
        linhas += bloco_post(i, d)
        linhas += ["---", ""]
    return "\n".join(linhas).rstrip() + "\n"


def montar_parser() -> vp.ParserPT:
    parser = vp.ParserPT(
        prog="montar_lote.py",
        description="Gera o lote.md de um lote: o resumo legível dos posts, para a pessoa ler e aprovar o texto. "
                    "Antes de gerar, valida os posts como o validar_posts.py.",
        epilog="Exemplo:\n"
               "  python -X utf8 skills/criar-conteudo/scripts/montar_lote.py --marca exemplo --lote 2026-11-03-exemplo\n"
               "Saída: 0 = gerado; 1 = há erros nos posts; 2 = marca ou lote não encontrados.",
    )
    parser.add_argument("--marca", help="slug da pasta da marca em marcas/. Se houver só uma marca além de 'exemplo', é usada sem perguntar")
    parser.add_argument("--lote", required=True, help="nome do lote (AAAA-MM-DD-slug), em marcas/<marca>/conteudo/")
    parser.add_argument("--saida", help="arquivo de saída (padrão: lote.md dentro da pasta do lote)")
    parser.add_argument("--simular", action="store_true", help="mostra o resultado na tela sem gravar nada")
    parser.add_argument("--forcar", action="store_true", help="gera mesmo que a validação encontre erros")
    parser.add_argument("--raiz", help="avançado: pasta raiz do projeto (por padrão, a pasta onde este script está instalado)")
    return parser


def main(argv: list[str] | None = None) -> int:
    vp.preparar_saida()
    args = montar_parser().parse_args(argv)
    raiz = Path(args.raiz).resolve() if args.raiz else vp.RAIZ_PADRAO
    try:
        marca, pasta_marca = vp.resolver_marca(raiz, args.marca)
        lote, pasta_lote = vp.resolver_lote(pasta_marca, args.lote)
    except vp.ErroDeUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2

    resultado = vp.validar_lote(raiz, marca, pasta_marca, lote, pasta_lote)
    if resultado.total_erros and not args.forcar:
        vp.imprimir(resultado, estrito=False)
        print("\nNão gerei o lote.md porque há erros. Corrija os posts e rode de novo (ou use --forcar).", file=sys.stderr)
        return 1

    posts = [p.dados for p in resultado.posts if p.dados is not None]
    if not posts:
        print("ERRO: nenhum post legível neste lote.", file=sys.stderr)
        return 1
    texto = montar_markdown(nome_da_marca(pasta_marca, marca), lote, posts, date.today(), ficticia=(marca == "exemplo"))

    if args.simular:
        print(texto)
        return 0
    destino = Path(args.saida) if args.saida else pasta_lote / "lote.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8", newline="\n")
    print(f"lote.md gerado com {len(posts)} post(s): {vp.mostrar_caminho(destino, raiz)}")
    if resultado.total_erros:
        print(f"Atenção: o lote tem {resultado.total_erros} erro(s) de validação. Rode validar_posts.py.")
    elif resultado.total_avisos:
        print(f"Há {resultado.total_avisos} aviso(s) de validação; rode validar_posts.py para ver.")
    if resultado.total_pendencias:
        print(f"Há {resultado.total_pendencias} pendência(s) em confirmar[]: o texto pode ser aprovado, mas o post só é publicado depois de resolvê-las.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
