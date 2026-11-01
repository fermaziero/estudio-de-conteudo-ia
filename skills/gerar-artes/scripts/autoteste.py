#!/usr/bin/env python3
"""Autoteste da skill gerar-artes.

Cria uma marca fictícia numa pasta temporária, gera artes, gera de novo, força um texto que não cabe,
refaz um slide, marca como pronta, confere a galeria e os prompts de imagem. Não mexe na pasta marcas/
do projeto e não precisa de internet. Serve para saber se a instalação (Python e Pillow) está funcionando
e, para quem mantém o projeto, para conferir uma mudança no código.

Uso (a partir da raiz do projeto):
    python -X utf8 skills/gerar-artes/scripts/autoteste.py
    python -X utf8 skills/gerar-artes/scripts/autoteste.py --manter   (guarda a pasta do teste para você olhar as artes)

Código de saída: 0 = tudo certo; 1 = alguma conferência falhou.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from _comum import PASTA_FONTES, PASTA_SCRIPTS, ParserPT, executar  # noqa: E402

LOTE = "2026-01-05-autoteste"
ID = "2026-01-05-1-autoteste"


class Falha(Exception):
    pass


def conferir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise Falha(mensagem)
    print(f"  ok: {mensagem}")


def tamanho(caminho: Path) -> tuple[int, int]:
    with Image.open(caminho) as imagem:
        return imagem.size


def criar_logo(destino: Path, cor_texto, cor_marca) -> None:
    escala = 3
    imagem = Image.new("RGBA", (520 * escala, 160 * escala), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)
    desenho.rounded_rectangle((10 * escala, 20 * escala, 130 * escala, 140 * escala), 28 * escala, fill=cor_marca)
    fonte = ImageFont.truetype(str(PASTA_FONTES / "Manrope-Bold.ttf"), 96 * escala)
    desenho.text((160 * escala, 125 * escala), "teste", font=fonte, fill=cor_texto, anchor="ls")
    imagem.resize((520, 160), Image.Resampling.LANCZOS).save(destino)


def slide(n: int, papel: str, layout: str, titulo: str, texto: str = "", itens: list[str] | None = None) -> dict:
    return {"n": n, "papel": papel, "layout": layout, "titulo": titulo, "texto": texto, "itens": itens or [], "imagem": None,
            "texto_alternativo": titulo, "fonte_interna": "exemplo fictício"}


def criar_marca(raiz: Path) -> Path:
    marca = raiz / "marcas" / "teste"
    (marca / "assets" / "logo").mkdir(parents=True)
    (marca / "conteudo" / LOTE / "posts").mkdir(parents=True)
    criar_logo(marca / "assets/logo/logo-fundo-claro.png", (20, 30, 40, 255), (230, 90, 40, 255))
    criar_logo(marca / "assets/logo/logo-fundo-escuro.png", (255, 255, 255, 255), (255, 140, 90, 255))
    visual = {
        "versao_esquema": 1, "nome_exibicao": "Marca de Teste (fictícia)", "arroba": "@marca.teste", "proporcao_padrao": "4:5",
        "cores": {"fundo": "#F6F4EE", "texto": "#1B2430", "destaque": "#C2410C", "suave": "#566274",
                  "fundo_escuro": "#10222B", "texto_sobre_escuro": "#FFFFFF"},
        "fontes": None,
        "logo": {"fundo_claro": "assets/logo/logo-fundo-claro.png", "fundo_escuro": "assets/logo/logo-fundo-escuro.png",
                 "posicao": "superior-esquerda", "largura_px": 150},
        "avatar": None, "numeracao": False, "rodape": False,
    }
    (marca / "visual.json").write_text(json.dumps(visual, ensure_ascii=False, indent=2), encoding="utf-8")
    post = {
        "versao_esquema": 1, "id": ID, "lote": LOTE, "titulo_interno": "Autoteste", "pilar": "educativo", "formato": "carrossel",
        "proporcao": "4:5", "etapa_funil": "atracao", "objetivo": "Teste", "de_onde_vem": "Exemplo fictício do autoteste",
        "chamada": "Salve este post",
        "slides": [
            slide(1, "capa", "capa", "Sua semana de trabalho cabe em uma página"),
            slide(2, "conteudo", "texto", "A **maioria das semanas** começa sem plano", "Escrever o plano devolve o controle do seu tempo."),
            slide(3, "conteudo", "lista", "Três perguntas antes de abrir o e-mail",
                  itens=["O que precisa ficar pronto até sexta?", "Quem depende de mim para avançar?", "O que posso adiar?"]),
            slide(4, "conteudo", "cartoes", "Como montar a página da semana",
                  itens=["Segunda: escolha as entregas que importam", "Quarta: confira o que mudou", "Sexta: anote o que funcionou"]),
            slide(5, "conteudo", "citacao", "Planejar é decidir o que fica de fora.", "Frase de exemplo (fictícia)"),
            slide(6, "cta", "cta", "Salve este post", "e envie para quem divide a agenda com você"),
        ],
        "roteiro": None, "legenda": "Legenda fictícia.\n\nSalve este post.", "hashtags": [], "fontes": [], "fontes_legenda_internas": [],
        "confirmar": [], "revisao": None, "status": "texto_aprovado", "historico": [], "aprovacao": None,
        "agendado_para": None, "publicacao": None,
    }
    (marca / "conteudo" / LOTE / "posts" / f"{ID}.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    return marca


def rodar(raiz: Path, script: str, *args: str, comando: str | None = None) -> subprocess.CompletedProcess:
    base = [sys.executable, "-X", "utf8", str(PASTA_SCRIPTS / script)]
    if comando:
        base.append(comando)
    base += ["--raiz", str(raiz), "--marca", "teste", "--lote", LOTE, *args]
    return subprocess.run(base, capture_output=True, text=True, encoding="utf-8")


def editar_post(marca: Path, funcao) -> dict:
    caminho = marca / "conteudo" / LOTE / "posts" / f"{ID}.json"
    post = json.loads(caminho.read_text(encoding="utf-8"))
    funcao(post)
    caminho.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    return post


def ler_post(marca: Path) -> dict:
    return editar_post(marca, lambda post: None)


def testar(raiz: Path) -> None:
    marca = criar_marca(raiz)
    lote = marca / "conteudo" / LOTE
    artes = lote / "artes" / ID

    print("1) primeira geração")
    r = rodar(raiz, "renderizar.py")
    conferir(r.returncode == 0, "renderizar.py terminou sem erro" if r.returncode == 0 else f"renderizar.py falhou: {(r.stdout + r.stderr)[-300:]}")
    pngs = sorted(artes.glob("[0-9][0-9].png"))
    conferir(len(pngs) == 6, "6 artes geradas (01.png a 06.png)")
    conferir(all(tamanho(p) == (1080, 1350) for p in pngs), "todas com 1080 x 1350 px")
    manifesto = json.loads((artes / "manifesto.json").read_text(encoding="utf-8"))
    conferir(len(manifesto["slides"]) == 6 and all(len(s["sha256"]) == 64 for s in manifesto["slides"]), "manifesto.json com o sha256 de cada arte")
    conferir((lote / "galeria.html").is_file() and (lote / "_conferencia" / f"{ID}.png").is_file(), "galeria.html e visão geral criadas")

    print("2) gerar de novo não muda nada")
    r = rodar(raiz, "renderizar.py")
    conferir(r.returncode == 0 and "6 igual(is)" in r.stdout, "as 6 artes continuam iguais")
    conferir(not list(artes.glob("_antes-*")), "nenhuma pasta _antes-* criada à toa")

    print("3) texto que não cabe falha e não grava nada")
    antes = (artes / "02.png").read_bytes()
    editar_post(marca, lambda p: p["slides"][1].update(texto="palavra " * 400))
    r = rodar(raiz, "renderizar.py")
    conferir(r.returncode == 2 and "não cabe" in r.stdout, "erro claro (código 2) dizendo que o texto não cabe")
    conferir((artes / "02.png").read_bytes() == antes, "a arte anterior ficou intacta")
    editar_post(marca, lambda p: p["slides"][1].update(texto="Escrever o plano devolve o controle do seu tempo."))

    print("4) refazer um slide guarda a versão anterior")
    def mudar_item(post: dict) -> None:
        post["slides"][2]["itens"][2] = "O que posso adiar sem prejuízo?"
    editar_post(marca, mudar_item)
    r = rodar(raiz, "renderizar.py", "--post", ID, "--slide", "3", "--motivo", "item mais claro")
    conferir(r.returncode == 0 and (artes / "_antes-item-mais-claro" / "03.png").is_file(), "versão anterior guardada em _antes-item-mais-claro/")

    print("5) marcar como pronta")
    r = rodar(raiz, "marcar_pronta.py")
    post = ler_post(marca)
    conferir(r.returncode == 0 and post["status"] == "arte_pronta", "status passou para arte_pronta")
    conferir(any(h["por"] == "gerar-artes" for h in post["historico"]), "eventos registrados no historico")

    print("6) texto mudou depois da arte: a galeria avisa")
    editar_post(marca, lambda p: p["slides"][4].update(titulo="Planejar é escolher o que fica de fora."))
    r = rodar(raiz, "galeria.py")
    conferir(r.returncode == 0 and "desatualizada" in (lote / "galeria.html").read_text(encoding="utf-8"), "galeria marca a arte desatualizada")

    print("7) prompts de imagem")
    editar_post(marca, lambda p: p["slides"][0].update(imagem={
        "tipo": "gerada", "arquivo": "", "descricao": "mesa de trabalho vista de cima", "prompt": "Luz natural. Sem texto, sem letras, sem logos."}))
    r = rodar(raiz, "imagens.py", comando="prompts")
    prompts = artes / "imagens" / "prompts.md"
    conferir(r.returncode == 0 and prompts.is_file() and "Sem nenhum texto na imagem" in prompts.read_text(encoding="utf-8"),
             "prompts.md criado com as proibições (sem texto, sem logo, sem rosto de pessoa real)")

    print("8) visual da marca mudou: a galeria avisa e gerar de novo resolve")
    caminho_visual = marca / "visual.json"
    visual = json.loads(caminho_visual.read_text(encoding="utf-8"))
    visual["cores"]["destaque"] = "#1D4ED8"
    caminho_visual.write_text(json.dumps(visual, ensure_ascii=False, indent=2), encoding="utf-8")
    rodar(raiz, "galeria.py")
    conferir("visual da marca" in (lote / "galeria.html").read_text(encoding="utf-8"), "galeria avisa que o visual mudou depois das artes")
    r = rodar(raiz, "renderizar.py", "--post", ID, "--motivo", "nova cor de destaque")
    conferir(r.returncode == 0 and any(artes.glob("_antes-nova-cor-de-destaque")), "artes refeitas, com a versão anterior guardada")
    rodar(raiz, "galeria.py")
    conferir("visual da marca" not in (lote / "galeria.html").read_text(encoding="utf-8"), "depois de refazer, o aviso some")

    print("9) importar imagem: arquivo inválido não estraga a imagem que já existe")
    gerada = raiz / "gerada.png"
    Image.new("RGB", (1200, 1500), (120, 150, 170)).save(gerada)
    r = rodar(raiz, "imagens.py", "--post", ID, "--slide", "1", str(gerada), comando="importar")
    imagem_final = artes / "imagens" / "slide-01.png"
    arquivo_no_post = ler_post(marca)["slides"][0]["imagem"]["arquivo"]
    conferir(r.returncode == 0 and imagem_final.is_file() and arquivo_no_post.endswith("imagens/slide-01.png"), "imagem importada e caminho gravado no post")
    lixo = raiz / "lixo.png"
    lixo.write_text("isto não é uma imagem", encoding="utf-8")
    antes = imagem_final.read_bytes()
    r = rodar(raiz, "imagens.py", "--post", ID, "--slide", "1", str(lixo), comando="importar")
    conferir(r.returncode == 1 and "Não consegui abrir" in r.stderr, "arquivo inválido: erro claro (código 1)")
    conferir(imagem_final.read_bytes() == antes and not list((artes / "imagens").glob("_antes-*")), "a imagem anterior continua no lugar e nada foi movido")
    conferir(ler_post(marca)["slides"][0]["imagem"]["arquivo"] == arquivo_no_post, "o post continua apontando para a imagem que existe")

    print("10) post aprovado e agendado: refazer exige confirmação e limpa a aprovação")
    editar_post(marca, lambda p: p.update(status="agendado", agendado_para="2026-02-01T10:00:00-03:00",
                                           aprovacao={"por": "pessoa", "frase": "pode publicar", "data": "2026-01-10", "hash": "abc123abc123abc123"}))
    editar_post(marca, lambda p: p["slides"][1].update(texto="Escrever o plano devolve o controle do seu dia."))
    r = rodar(raiz, "renderizar.py", "--post", ID)
    conferir(r.returncode == 1 and "--refazer-aprovado" in r.stderr, "sem --refazer-aprovado, a skill recusa")
    r = rodar(raiz, "renderizar.py", "--post", ID, "--refazer-aprovado", "--motivo", "texto revisado")
    post = ler_post(marca)
    conferir(r.returncode == 0 and post["status"] == "arte_pronta" and post["aprovacao"] is None and post["agendado_para"] is None,
             "o post voltou para arte_pronta, sem aprovação e sem agendamento")
    ultimo = post["historico"][-1]
    conferir("aprovação invalidada" in ultimo["evento"] and "T" in ultimo["data"], "historico registra a invalidação com data e hora")


def principal() -> int:
    parser = ParserPT(description="Autoteste da skill gerar-artes (usa uma marca fictícia numa pasta temporária).")
    parser.add_argument("--manter", action="store_true", help="não apaga a pasta do teste; mostra o caminho para você olhar as artes")
    args = parser.parse_args()
    raiz = Path(tempfile.mkdtemp(prefix="autoteste-gerar-artes-"))
    try:
        testar(raiz)
    except Falha as falha:
        print(f"\nFALHOU: {falha}\nPasta do teste (guardada para você investigar): {raiz}", file=sys.stderr)
        return 1
    if args.manter:
        print(f"\nPasta do teste guardada em: {raiz}")
    else:
        shutil.rmtree(raiz, ignore_errors=True)
    print("\nAUTOTESTE OK: a skill gerar-artes está funcionando.")
    return 0


if __name__ == "__main__":
    executar(principal)
