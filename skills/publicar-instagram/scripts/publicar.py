#!/usr/bin/env python3
"""Aprova, agenda, publica e confere posts do feed do Instagram (carrossel e post único).

Rode sempre a partir da raiz do projeto (no macOS e no Linux, use python3). Em todos os comandos,
--post aceita o id do post ou o caminho do .json, e --marca pode ser omitido se só houver uma marca:

    python -X utf8 skills/publicar-instagram/scripts/publicar.py simular --post ID
        mostra o que vai sair e roda todas as checagens, sem rede e sem alterar nada
    python -X utf8 skills/publicar-instagram/scripts/publicar.py aprovar --post ID --frase "pode publicar ID" --por "Nome"
        abre uma janela (ou pergunta num terminal interativo) para a PESSOA confirmar; só então grava a aprovação
        (frase literal da pessoa) com o hash da versão, assina com a chave deste computador (guardada fora do projeto)
        e muda o status para 'aprovado'. Nenhuma opção pula a confirmação. Aprovação sem assinatura válida não vale
    python -X utf8 skills/publicar-instagram/scripts/publicar.py agendar --post ID --quando 2026-11-05T18:00:00-03:00
    python -X utf8 skills/publicar-instagram/scripts/publicar.py desagendar --post ID
    python -X utf8 skills/publicar-instagram/scripts/publicar.py publicar --post ID [--de-novo]
        exige status 'aprovado' (ou 'agendado'), assinatura e hash conferidos e 'confirmar' vazio
    python -X utf8 skills/publicar-instagram/scripts/publicar.py agendados [--janela-horas 2] [--simular]
        comando da rotina: publica os agendados cujo horário chegou, dentro da janela de atraso
    python -X utf8 skills/publicar-instagram/scripts/publicar.py conferir --post ID
        resolve uma publicação que terminou sem resposta clara, antes de qualquer nova tentativa
    python -X utf8 skills/publicar-instagram/scripts/publicar.py situacao
        lista os posts da marca com status, agendamento e link

Código de saída: 0 = ok; 1 = recusa ou erro (nada foi publicado, salvo aviso em contrário);
3 = SEM RESPOSTA CLARA da Meta ou pendência que exige conferência (o post pode ter ido ao ar).
Reels não são publicados nesta versão: só 'carrossel' e 'post_unico'.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _armazenamento as arm  # noqa: E402
import _assinatura as assin  # noqa: E402
import _comum  # noqa: E402
import _confirmacao  # noqa: E402
import _instagram as ig  # noqa: E402
import credenciais  # noqa: E402
from _comum import (ID_RE, ErroUso, Incerto, Recusa, abrir_log, acrescentar_historico, agora,  # noqa: E402
                    aplicar_raiz, calcular_hash, dentro_de, escolher_marca, executar, gravar_json, interprete_console,
                    interpretar_data, iso, ler_json, localizar_post, mascarar, opcao_raiz, pasta_artes, pasta_marca, processo,
                    proteger_saida, registrar_publicado, registros_publicados, soltar_trava_execucao,
                    tomar_trava_execucao)

FORMATOS_PUBLICAVEIS = ("carrossel", "post_unico")
PROPORCOES = {"4:5": (4, 5), "1:1": (1, 1)}
MAX_LEGENDA, MAX_HASHTAGS, MAX_MENCOES = 2200, 30, 20
MAX_SLIDES = 10
MIN_LARGURA, MAX_LARGURA = 320, 1440
RAZAO_MIN, RAZAO_MAX = 4 / 5, 1.91
JANELA_PADRAO_HORAS = 2.0
ESPERA_CONFERIR_S = 120
FONTE_RE = re.compile(r"(?i)\bfontes?\s*:")
POR_SCRIPT = "publicar-instagram"
POR_ROTINA = "rotina agendada"


@dataclass
class Contexto:
    marca: str
    caminho: Path

    def __post_init__(self):
        # O id vem do NOME do arquivo e precisa seguir o padrão do contrato. O campo id do JSON é só conferido: se for
        # diferente, recusa antes de montar qualquer caminho (pasta de artes, trava, chaves) com um dado do arquivo.
        if not ID_RE.fullmatch(self.caminho.stem):
            raise Recusa(f"o nome do arquivo do post ('{self.caminho.stem[:60]}') não segue o padrão de id "
                         "(3 a 80 caracteres: minúsculas, números e hífen)")
        self.recarregar()

    @property
    def id(self) -> str:
        return self.caminho.stem

    @property
    def lote(self) -> str:
        return self.caminho.parent.parent.name

    def recarregar(self) -> dict:
        post = ler_json(self.caminho)
        if not isinstance(post, dict):
            raise Recusa(f"o arquivo {self.caminho.name} precisa conter um objeto JSON, entre chaves {{ }}")
        if post.get("id") != self.caminho.stem:
            raise Recusa(f"o campo id do JSON ({ascii(post.get('id'))[:90]}) é diferente do nome do arquivo "
                         f"('{self.caminho.stem}'). Por segurança, nada foi lido, gravado nem apagado")
        self.post = post
        return post


@dataclass
class Analise:
    problemas: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    artes: list = field(default_factory=list)
    hash_atual: str = ""
    legenda_final: str = ""


def carregar_contexto(args) -> Contexto:
    marca = escolher_marca(args.marca)
    return Contexto(marca, localizar_post(marca, args.post))


# ---------------------------------------------------------------- legenda

def tamanho_legenda(texto: str) -> int:
    """Conta em unidades UTF-16, como o Instagram: emoji vale 2."""
    return len(texto.encode("utf-16-le")) // 2


def montar_legenda(post: dict) -> tuple[str, list[str]]:
    """Legenda do post + hashtags da lista (as que ainda não estão no texto). Devolve (texto, tags inválidas)."""
    legenda = str(post.get("legenda") or "").strip()
    existentes = {t.lower() for t in re.findall(r"#(\w+)", legenda)}
    novas, invalidas = [], []
    for h in post.get("hashtags") or []:
        tag = re.sub(r"\s+", "", str(h)).lstrip("#")
        if not re.fullmatch(r"\w+", tag):
            invalidas.append(str(h))
        elif tag.lower() not in existentes:
            novas.append("#" + tag)
            existentes.add(tag.lower())
    return legenda + ("\n\n" + " ".join(novas) if novas else ""), invalidas


# ---------------------------------------------------------------- análise local (sem rede)

def exigir_pillow():
    try:
        from PIL import Image
    except ImportError:
        raise ErroUso("falta a biblioteca Pillow. Instale com: python -m pip install -r requirements.txt") from None
    return Image


def ler_artes(ctx: Contexto, problemas: list, avisos: list) -> list[dict]:
    Image = exigir_pillow()

    post = ctx.post
    slides = post.get("slides")
    if not isinstance(slides, list) or not slides:
        problemas.append("o post não tem slides")
        return []
    numeros = [s.get("n") if isinstance(s, dict) else None for s in slides]
    if not all(type(n) is int for n in numeros) or numeros != list(range(1, len(slides) + 1)):
        problemas.append("os slides precisam estar numerados 1, 2, 3… (números inteiros) sem buracos e em ordem")
        return []
    pasta = pasta_artes(ctx.caminho, ctx.id)
    artes = []
    for n in numeros:
        arq = pasta / f"{n:02d}.png"
        dentro_de(pasta, arq)  # um link para fora da pasta de artes não vale
        if not arq.is_file():
            try:
                nome = arq.relative_to(pasta_marca(ctx.marca)).as_posix()
            except ValueError:
                nome = arq.name
            problemas.append(f"falta a arte {nome}")
            continue
        dados = arq.read_bytes()
        try:
            with Image.open(io.BytesIO(dados)) as im:
                formato, (largura, altura) = im.format, im.size
        except Exception:
            problemas.append(f"{arq.name} não é uma imagem válida")
            continue
        if formato != "PNG":
            problemas.append(f"{arq.name} deveria ser PNG (veio {formato})")
            continue
        artes.append({"n": n, "arquivo": arq, "bytes": dados, "largura": largura, "altura": altura})
    if pasta.is_dir():
        sobrando = sorted(p.name for p in pasta.glob("*.png") if p.name not in {f"{n:02d}.png" for n in numeros})
        if sobrando:
            avisos.append("há artes que não pertencem a nenhum slide e não serão publicadas: " + ", ".join(sobrando))
    return artes


def validar_externo(ctx: Contexto) -> tuple[list[str], list[str]]:
    """Roda o validador de posts da skill criar-conteudo, se existir. Devolve (problemas, avisos)."""
    script = _comum.RAIZ / "skills" / "criar-conteudo" / "scripts" / "validar_posts.py"
    if not script.is_file():
        return [], ["o validador de posts (criar-conteudo) não foi encontrado; usei só as checagens do publicador"]
    comando = [interprete_console(), "-X", "utf8", str(script), "--marca", ctx.marca, "--post", ctx.id]
    if _comum.RAIZ_PERSONALIZADA:
        comando += ["--raiz", str(_comum.RAIZ_PERSONALIZADA)]
    try:
        r = processo(comando, text=True, encoding="utf-8", errors="replace", timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        return [], [f"não consegui rodar o validador de posts ({type(e).__name__})"]
    if r.returncode == 0:
        return [], []
    linhas = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    resumo = " | ".join(mascarar(l) for l in linhas[-6:]) or "sem detalhe"
    if r.returncode == 1:
        return [f"o validador de posts (criar-conteudo) apontou erros: {resumo}"], []
    return [], [f"o validador de posts não conseguiu rodar (código {r.returncode}): {resumo}"]


def analisar(ctx: Contexto, com_validador: bool = True) -> Analise:
    post = ctx.post
    a = Analise()
    p, av = a.problemas, a.avisos

    if post.get("id") != ctx.caminho.stem or not ID_RE.fullmatch(ctx.caminho.stem):
        p.append("o campo id do post precisa ser igual ao nome do arquivo e seguir o padrão "
                 "(3 a 80 caracteres: minúsculas, números e hífen)")
    if not credenciais.arroba_da_marca(ctx.marca):
        p.append(f"falta a 'arroba' em marcas/{ctx.marca}/visual.json (por exemplo \"@meuperfil\"; o valor de exemplo "
                 "'@perfil' não vale). Sem ela a skill não consegue conferir que o token é da conta certa, e por isso "
                 "se recusa a publicar")

    formato = post.get("formato")
    slides = post.get("slides") if isinstance(post.get("slides"), list) else []
    if formato == "reel":
        p.append("Reels não são publicados nesta versão (só 'carrossel' e 'post_unico')")
    elif formato not in FORMATOS_PUBLICAVEIS:
        p.append(f"formato '{formato}' não é publicável (use 'carrossel' ou 'post_unico')")
    elif formato == "post_unico" and len(slides) != 1:
        p.append(f"post_unico precisa ter exatamente 1 slide (tem {len(slides)})")
    elif formato == "carrossel" and not 2 <= len(slides) <= MAX_SLIDES:
        p.append(f"carrossel precisa ter de 2 a {MAX_SLIDES} slides (tem {len(slides)})")

    proporcao = post.get("proporcao")
    if proporcao not in PROPORCOES:
        p.append("a proporção deve ser '4:5' ou '1:1'")

    legenda, invalidas = montar_legenda(post)
    a.legenda_final = legenda
    if not legenda.strip():
        p.append("a legenda está vazia")
    if tamanho_legenda(legenda) > MAX_LEGENDA:
        p.append(f"legenda com {tamanho_legenda(legenda)} caracteres (máximo {MAX_LEGENDA}, contando as hashtags)")
    if len(re.findall(r"#\w+", legenda)) > MAX_HASHTAGS:
        p.append(f"mais de {MAX_HASHTAGS} hashtags na legenda")
    if len(re.findall(r"(?<![\w.])@[\w.]+", legenda)) > MAX_MENCOES:
        p.append(f"mais de {MAX_MENCOES} menções (@) na legenda")
    if FONTE_RE.search(legenda):
        p.append("a legenda tem 'Fonte:'. A fonte fica só nos campos fontes e fonte_interna do post")
    for h in invalidas:
        p.append(f"hashtag inválida: '{h}' (use só letras, números e _)")
    if len(post.get("hashtags") or []) > 5:
        av.append("o contrato recomenda de 0 a 5 hashtags na lista")

    confirmar = post.get("confirmar") or []
    if not isinstance(confirmar, list):
        p.append("o campo 'confirmar' deve ser uma lista")
    else:
        for item in confirmar:
            p.append(f"pendência em 'confirmar': {item}")

    revisao = post.get("revisao")
    if not isinstance(revisao, dict) or revisao.get("veredito") != "aprovar":
        av.append("o post não tem revisão com veredito 'aprovar'; diga isso à pessoa antes de pedir o ok")
    for s in slides:
        if isinstance(s, dict):
            textos = [str(s.get("titulo") or ""), str(s.get("texto") or "")] + [str(i) for i in s.get("itens") or []]
            if any(FONTE_RE.search(t) for t in textos):
                av.append(f"o texto do slide {s.get('n')} tem 'Fonte:' (a fonte não vai na arte)")
            if not str(s.get("texto_alternativo") or "").strip():
                av.append(f"o slide {s.get('n')} está sem texto_alternativo (usarei título e texto como descrição)")

    a.artes = ler_artes(ctx, p, av)
    if a.artes and len(a.artes) == len(slides):
        tamanhos = {(x["largura"], x["altura"]) for x in a.artes}
        if len(tamanhos) > 1:
            p.append("as artes têm tamanhos diferentes: " + ", ".join(f"{l}x{h}" for l, h in sorted(tamanhos)))
        else:
            largura, altura = tamanhos.pop()
            if proporcao in PROPORCOES:
                bl, ba = PROPORCOES[proporcao]
                if abs(largura * ba - altura * bl) > bl + ba:
                    p.append(f"as artes têm {largura}x{altura}, que não é a proporção {proporcao} do post")
            if not RAZAO_MIN - 0.005 <= largura / altura <= RAZAO_MAX:
                p.append(f"proporção {largura}x{altura} fora do aceito pelo Instagram (entre 4:5 e 1,91:1)")
            if largura < MIN_LARGURA:
                p.append(f"arte com {largura} px de largura (mínimo {MIN_LARGURA})")
        a.hash_atual = calcular_hash(post, [x["bytes"] for x in a.artes])

    if com_validador:
        pe, ae = validar_externo(ctx)
        p += pe
        av += ae
    return a


def converter_para_jpeg(png: bytes) -> bytes:
    """PNG -> JPEG sRGB, até 1440 px de largura e 8 MB (limites da Meta)."""
    Image = exigir_pillow()
    with Image.open(io.BytesIO(png)) as original:
        original.load()
        icc = original.info.get("icc_profile")
        if original.mode in ("RGBA", "LA") or (original.mode == "P" and "transparency" in original.info):
            rgba = original.convert("RGBA")
            im = Image.new("RGB", rgba.size, (255, 255, 255))
            im.paste(rgba, mask=rgba.split()[3])
        else:
            im = original.convert("RGB")
    if icc:
        try:
            from PIL import ImageCms
            im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                           ImageCms.createProfile("sRGB"), outputMode="RGB")
        except Exception:
            pass
    if im.width > MAX_LARGURA:
        im = im.resize((MAX_LARGURA, round(im.height * MAX_LARGURA / im.width)), Image.LANCZOS)
    for qualidade in (92, 88, 82, 76, 70):
        saida = io.BytesIO()
        im.save(saida, "JPEG", quality=qualidade, optimize=True, subsampling=0)
        if saida.tell() <= arm.LIMITE_JPEG:
            return saida.getvalue()
    raise ValueError("não consegui deixar o JPEG abaixo de 8 MB")


def kb(n: int) -> str:
    return f"{n / 1024:.0f} KB"


# ---------------------------------------------------------------- atualização do post

def gravar_post(ctx: Contexto, mudancas: dict, evento: str | None = None, por: str = POR_SCRIPT) -> dict:
    """Relê o arquivo, aplica as mudanças e grava de forma atômica."""
    post = ctx.recarregar()
    post.update(mudancas)
    if evento:
        acrescentar_historico(post, evento, por)
    gravar_json(ctx.caminho, post)
    return post


def invalidar_aprovacao(ctx: Contexto, motivo: str) -> None:
    antigo = (ctx.post.get("aprovacao") or {}).get("hash", "")
    gravar_post(ctx, {"status": "arte_pronta", "aprovacao": None, "agendado_para": None},
                f"aprovação invalidada: {motivo} (hash antigo {antigo[:12]})")


def conferir_assinatura(ctx: Contexto) -> assin.Veredito:
    """A aprovação do post só vale com a assinatura feita pelo `aprovar` neste computador (veja _assinatura.py)."""
    return assin.verificar(ctx.marca, ctx.id, ctx.post.get("aprovacao"))


def recusa_sem_assinatura(ctx: Contexto, v: assin.Veredito) -> str:
    """Texto da recusa. Se a chave foi lida e a assinatura falta ou não confere, a aprovação cai como a do hash."""
    texto = f"{assin.MENSAGEM_REAPROVAR}. Motivo: {v.motivo}."
    if ctx.post.get("status") == "publicado":
        return (texto + " O post já foi publicado e 'aprovar' não aceita post publicado: para publicar o mesmo "
                        "conteúdo outra vez, crie um post novo.")
    if v.definitiva:
        invalidar_aprovacao(ctx, f"aprovação sem assinatura válida: {v.motivo}")
        texto += " O post voltou para 'arte_pronta'."
    return texto


def exigir_aprovacao_valida(ctx: Contexto, analise: Analise) -> None:
    """Confere que o post está aprovado, que a aprovação tem a assinatura deste computador e que nada mudou desde então."""
    post = ctx.post
    aprov = post.get("aprovacao")
    if not isinstance(aprov, dict) or not aprov.get("hash"):
        raise Recusa("o post não tem aprovação registrada. Rode 'simular', mostre à pessoa e, com o ok dela, 'aprovar'")
    veredito = conferir_assinatura(ctx)
    if not veredito.valida:
        raise Recusa(recusa_sem_assinatura(ctx, veredito))
    if not analise.hash_atual:
        mostrar_problemas(analise)
        raise Recusa("não consegui calcular o hash do post (veja os problemas acima)")
    if aprov["hash"] != analise.hash_atual:
        invalidar_aprovacao(ctx, "o texto ou as artes mudaram depois do ok da pessoa")
        raise Recusa("o conteúdo mudou depois da aprovação, então o ok perdeu a validade. O post voltou para "
                     "'arte_pronta': rode 'simular', mostre a nova versão e peça um novo ok")


# ---------------------------------------------------------------- comandos sem rede

def mostrar_problemas(a: Analise) -> None:
    for t in a.problemas:
        print(f"  PROBLEMA: {t}")
    for t in a.avisos:
        print(f"  AVISO: {t}")


def confirmar_com_a_pessoa(titulo: str, linhas: list[tuple[str, str]], id_post: str, botao: str = "Aprovar") -> bool:
    """Barreira humana (veja _confirmacao.py): janela local, ou terminal interativo, ou recusa.

    Não existe opção de linha de comando nem variável de ambiente que pule esta confirmação. Os testes automáticos
    substituem esta função dentro do próprio processo.
    """
    return _confirmacao.pedir(titulo, linhas, id_post, botao)


def resumo_texto(texto, limite: int = 280) -> str:
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= limite else texto[:limite].rstrip() + " …"


def avaliar_aprovacao(ctx: Contexto) -> tuple[bool, str]:
    """(o `aprovar` aceitaria este post agora?, motivo da recusa). A mesma regra serve ao simular e ao aprovar."""
    status = ctx.post.get("status")
    if arquivo_trava(ctx.marca, ctx.id).is_file():
        return False, "há uma publicação deste post sem resposta clara. Rode 'conferir' antes de qualquer outra coisa"
    if status == "agendado" and conferir_assinatura(ctx).valida:
        return False, "o post está agendado: rode 'desagendar' antes de aprovar de novo"
    if status == "publicado":
        return False, "o post já foi publicado; para publicar de novo, crie outro post"
    # 'agendado' só chega aqui com a aprovação sem assinatura válida: o agendamento já não vale e o `aprovar` refaz tudo.
    if status not in ("arte_pronta", "erro", "aprovado", "agendado"):
        return False, (f"o status é '{status}'. A aprovação final só vale depois que as artes estão prontas "
                       "(status 'arte_pronta'): termine a skill gerar-artes e marque as artes como prontas antes")
    return True, ""


def cmd_simular(args) -> int:
    ctx = carregar_contexto(args)
    post = ctx.post
    a = analisar(ctx)
    cred_aviso = []
    try:
        env = credenciais.carregar_instagram(ctx.marca)
        av = credenciais.aviso_validade(env, ctx.marca)
        if av:
            cred_aviso.append(av)
    except ErroUso as e:
        cred_aviso.append(f"credenciais do Instagram: {e}")
    try:
        arm.Armazenamento.carregar(ctx.marca)
    except ErroUso as e:
        cred_aviso.append(f"armazenamento de imagens: {e}")

    print(f"POST: {ctx.id}" + (f" ({post.get('titulo_interno')})" if post.get("titulo_interno") else ""))
    print(f"Marca: {ctx.marca} | Lote: {ctx.lote} | Formato: {post.get('formato')} "
          f"({len(post.get('slides') or [])} slide(s), proporção {post.get('proporcao')}) | Status: {post.get('status')}")
    aprov = post.get("aprovacao")
    tem_aprov = bool(isinstance(aprov, dict) and aprov.get("hash"))
    hash_confere = bool(tem_aprov and a.hash_atual and aprov.get("hash") == a.hash_atual)
    assinatura = conferir_assinatura(ctx) if tem_aprov else assin.Veredito(False)
    aprovacao_vale = hash_confere and assinatura.valida
    if tem_aprov:
        linha = (f"Aprovação registrada por {aprov.get('por')} em {aprov.get('data')}; "
                 f"hash {'confere' if hash_confere else 'NÃO CONFERE (o conteúdo mudou)'}")
        if post.get("status") != "publicado":
            linha += "; assinatura " + ("válida" if assinatura.valida else f"INVÁLIDA ({assinatura.motivo})")
        print(linha)
    else:
        print("Aprovação: ainda não registrada")
    if post.get("agendado_para"):
        print(f"Agendado para: {post['agendado_para']}")
    print("\nArtes que vão sair (convertidas para JPEG):")
    for x in a.artes:
        try:
            jpeg = converter_para_jpeg(x["bytes"])
            print(f"  {x['arquivo'].name}: {x['largura']}x{x['altura']} -> JPEG {kb(len(jpeg))}")
        except Exception as e:
            a.problemas.append(f"{x['arquivo'].name}: {e}")
    print(f"\nLegenda final ({tamanho_legenda(a.legenda_final)} caracteres):")
    print("  " + a.legenda_final.replace("\n", "\n  "))
    if post.get("chamada"):
        print(f"\nChamada para ação: {post['chamada']}")
    print("\nChecagens locais:" + (" tudo certo" if not a.problemas and not a.avisos else ""))
    mostrar_problemas(a)
    for t in cred_aviso:
        print(f"  AVISO: {t}")

    # O veredito só diz PRONTO quando o comando `aprovar` aceitaria de fato este post.
    status = post.get("status")
    pode, motivo = avaliar_aprovacao(ctx)
    pub = post.get("publicacao") if isinstance(post.get("publicacao"), dict) else {}
    if a.problemas:
        veredito, codigo = f"NÃO ESTÁ PRONTO: {len(a.problemas)} problema(s) acima.", 1
    elif status == "publicado":
        veredito, codigo = f"JÁ PUBLICADO: {pub.get('permalink') or pub.get('media_id') or 'veja o campo publicacao'}.", 0
    elif status == "agendado" and aprovacao_vale:
        veredito, codigo = f"JÁ APROVADO e AGENDADO para {post.get('agendado_para')}. Nada a aprovar.", 0
    elif status == "aprovado" and aprovacao_vale:
        veredito, codigo = "JÁ APROVADO nesta versão. Falta só publicar ou agendar.", 0
    elif not pode:
        veredito, codigo = f"AINDA NÃO DÁ PARA APROVAR: {motivo}.", 1
    else:
        if tem_aprov and not assinatura.valida:
            aviso_ok = f" O ok anterior não vale: {assin.MENSAGEM_REAPROVAR}."
        elif tem_aprov and not hash_confere:
            aviso_ok = " O ok anterior não vale mais porque o conteúdo mudou."
        else:
            aviso_ok = ""
        veredito, codigo = (f"PRONTO para a pessoa aprovar. Mostre a ela o que está acima e peça: 'pode publicar {ctx.id}'."
                            + aviso_ok, 0)
    print("\n" + veredito)
    print("Nada foi enviado nem publicado. Token, cota e URL pública só são testados em 'credenciais.py verificar "
          "--completo' e na hora de publicar.")
    return codigo


def frase_valida(frase: str, post_id: str) -> str | None:
    frase = " ".join(frase.split())
    if len(frase) < 8:
        return "a frase da pessoa está curta demais; copie a frase literal dela"
    if post_id.lower() not in frase.lower():
        return (f"a frase precisa citar o id do post ({post_id}). Peça à pessoa: 'pode publicar {post_id}'")
    return None


def cmd_aprovar(args) -> int:
    ctx = carregar_contexto(args)
    post = ctx.post
    por = args.por.strip()
    if not por:
        raise Recusa("informe quem aprovou com --por")
    erro = frase_valida(args.frase, ctx.id)
    if erro:
        raise Recusa(erro)
    pode, motivo = avaliar_aprovacao(ctx)
    if not pode:
        raise Recusa(motivo)
    a = analisar(ctx)
    if a.problemas:
        mostrar_problemas(a)
        raise Recusa("o post tem problemas, então não dá para aprovar")
    frase = " ".join(args.frase.split())

    # A chave que assina a aprovação nasce na primeira aprovação. Garantir que ela existe ANTES da janela evita que a
    # pessoa confirme e só então descubra que não dá para gravar a assinatura.
    chave, situacao_chave = assin.chave_ou_criar(ctx.marca)
    if situacao_chave != "existente":
        print(("Criei" if situacao_chave == "criada" else "Troquei") + " a chave de aprovação deste computador em "
              f"{assin.arquivo_chave(ctx.marca)} (fora do projeto). Ela assina cada aprovação; não a copie nem a compartilhe. "
              "Se ela sumir, as aprovações antigas perdem a validade e a pessoa aprova de novo."
              + (" A chave anterior estava com defeito e ficou guardada de lado." if situacao_chave == "substituida" else ""))

    # Barreira humana: o agente prepara o comando, mas quem confirma é a pessoa, numa janela ou num terminal.
    linhas = [("Marca", ctx.marca), ("Post", ctx.id), ("Título interno", resumo_texto(post.get("titulo_interno"), 120)),
              ("Formato", f"{post.get('formato')}, {len(a.artes)} arte(s), proporção {post.get('proporcao')}"),
              ("Início da legenda", resumo_texto(a.legenda_final)),
              ("Agendamento", post.get("agendado_para") or "nenhum (aprovar não agenda; depois use 'agendar' ou 'publicar')"),
              ("Versão (hash)", a.hash_atual[:16]), ("Aprovado por", por), ("Frase registrada", f"\"{frase}\"")]
    print("Aguardando a confirmação da pessoa (uma janela ou uma pergunta no terminal)…")
    if not confirmar_com_a_pessoa("Aprovar a publicação deste post?", linhas, ctx.id, "Aprovar"):
        raise Recusa("a pessoa não confirmou (cancelou ou fechou a janela). Nada foi gravado")

    # A janela pode ter ficado aberta por minutos: confere que nada mudou nesse tempo.
    ctx.recarregar()
    pode, motivo = avaliar_aprovacao(ctx)
    b = analisar(ctx, com_validador=False)
    if not pode or b.problemas or b.hash_atual != a.hash_atual:
        raise Recusa("o post mudou enquanto a janela estava aberta. Nada foi gravado; rode 'simular' e peça a "
                     "confirmação de novo")
    aprov = {"por": por, "frase": frase, "data": iso(agora()), "hash": a.hash_atual}
    aprov["assinatura"] = assin.assinar(chave, ctx.id, aprov)
    gravar_post(ctx, {"status": "aprovado", "aprovacao": aprov, "agendado_para": None},
                f"aprovado por {por} (hash {a.hash_atual[:12]}), confirmado pela pessoa na janela ou no terminal, "
                "e assinado com a chave deste computador", por)
    print(f"APROVADO: {ctx.id} por {por}")
    print(f"  Frase registrada: \"{frase}\"")
    print(f"  Versão aprovada (hash): {a.hash_atual}")
    print("  Aprovação assinada com a chave deste computador (a chave fica fora do projeto e nunca é mostrada).")
    print(f"  Legenda: {tamanho_legenda(a.legenda_final)} caracteres; {len(a.artes)} arte(s).")
    print("Qualquer mudança no texto ou nas artes invalida este ok.")
    return 0


def rotina_instalada(marca: str):
    try:
        import rotina
        return rotina.instalada(marca)
    except Exception:
        return None


def cmd_agendar(args) -> int:
    ctx = carregar_contexto(args)
    post = ctx.post
    quando = interpretar_data(args.quando)
    if quando is None or not re.search(r"\d{2}:\d{2}", args.quando):
        raise Recusa("data inválida em --quando. Use data e hora com o fuso, como 2026-11-05T18:00:00-03:00")
    if post.get("status") != "aprovado":
        raise Recusa(f"só se agenda post 'aprovado' (o status é '{post.get('status')}')")
    a = analisar(ctx)
    exigir_aprovacao_valida(ctx, a)
    if a.problemas:
        mostrar_problemas(a)
        raise Recusa("o post tem problemas, então não dá para agendar")
    if quando <= agora() + timedelta(minutes=1):
        raise Recusa("o horário já passou ou é agora. Para publicar já, use 'publicar'")
    if not re.search(r"(Z|z|[+-]\d{2}:?\d{2})$", args.quando.strip()):
        print(f"AVISO: sem fuso em --quando; usei o fuso deste computador ({iso(quando)[-6:]}).")
    gravar_post(ctx, {"status": "agendado", "agendado_para": iso(quando)}, f"agendado para {iso(quando)}")
    print(f"AGENDADO: {ctx.id} para {iso(quando)}")
    instalada = rotina_instalada(ctx.marca)
    if instalada is False:
        print("ATENÇÃO: a rotina que publica os agendados NÃO está instalada neste computador. Sem ela, nada sai. "
              "Veja: python -X utf8 skills/publicar-instagram/scripts/rotina.py mostrar --marca " + ctx.marca)
    elif instalada is None:
        print("Confira se a rotina está instalada: python -X utf8 skills/publicar-instagram/scripts/rotina.py "
              f"mostrar --marca {ctx.marca}")
    print("O computador precisa estar ligado e com a sessão aberta no horário. Se estiver desligado, o post "
          f"ainda sai até {JANELA_PADRAO_HORAS:g} h depois; passou disso, não é publicado e fica registrado.")
    return 0


def cmd_desagendar(args) -> int:
    ctx = carregar_contexto(args)
    if ctx.post.get("status") != "agendado":
        raise Recusa(f"o post não está agendado (status '{ctx.post.get('status')}')")
    gravar_post(ctx, {"status": "aprovado", "agendado_para": None}, "agendamento cancelado")
    veredito = conferir_assinatura(ctx)
    if veredito.valida:
        print(f"DESAGENDADO: {ctx.id} voltou para 'aprovado' (a aprovação continua valendo para esta versão).")
    else:
        print(f"DESAGENDADO: {ctx.id} voltou para 'aprovado', mas a aprovação dele não vale: {assin.MENSAGEM_REAPROVAR}. "
              f"Motivo: {veredito.motivo}.")
    return 0


def cmd_situacao(args) -> int:
    marca = escolher_marca(args.marca)
    pasta = pasta_marca(marca)
    linhas = []
    for caminho in sorted((pasta / "conteudo").glob("*/posts/*.json")):
        try:
            p = ler_json(caminho)
        except (OSError, ValueError):
            linhas.append((caminho.parent.parent.name, caminho.stem, "ilegível (JSON com defeito; rode simular)", "", ""))
            continue
        if not isinstance(p, dict):
            linhas.append((caminho.parent.parent.name, caminho.stem, "ilegível (não é um objeto JSON)", "", ""))
            continue
        if p.get("status") == "rascunho" and not args.todos:
            continue
        pub = p.get("publicacao") if isinstance(p.get("publicacao"), dict) else {}
        status = str(p.get("status")) + ("" if p.get("id") == caminho.stem else " [o id do JSON difere do nome do arquivo]")
        if p.get("status") in ("aprovado", "agendado") and not assin.verificar(marca, caminho.stem, p.get("aprovacao")).valida:
            status += " [aprovação sem assinatura válida: rode 'aprovar' de novo]"
        linhas.append((caminho.parent.parent.name, caminho.stem, status,
                       str(p.get("agendado_para") or ""), str(pub.get("permalink") or "")))
    if not linhas:
        print("Nenhum post (fora rascunhos) encontrado. Use --todos para incluir os rascunhos.")
    for lote, pid, status, quando, link in linhas:
        extra = f"  agendado para {quando}" if quando else ""
        extra += f"  {link}" if link else ""
        print(f"{lote} | {pid} | {status}{extra}")
    travas = sorted((pasta / "publicacao" / "_em_andamento").glob("*.json"))
    for t in travas:
        print(f"PENDENTE DE CONFERÊNCIA: {t.stem} (publicação sem resposta clara). Rode: publicar.py conferir --post {t.stem}")
    return 0


# ---------------------------------------------------------------- trava por post

def pasta_travas(marca: str) -> Path:
    return pasta_marca(marca) / "publicacao" / "_em_andamento"


def arquivo_trava(marca: str, post_id: str) -> Path:
    if not ID_RE.fullmatch(str(post_id)):
        raise Recusa("id de post inválido para montar o caminho da trava")
    arq = pasta_travas(marca) / f"{post_id}.json"
    dentro_de(pasta_travas(marca), arq)
    return arq


def criar_trava(ctx: Contexto, status_anterior: str) -> None:
    arq = arquivo_trava(ctx.marca, ctx.id)
    arq.parent.mkdir(parents=True, exist_ok=True)
    try:
        with arq.open("x", encoding="utf-8") as f:
            f.write(json.dumps({"post_id": ctx.id, "etapa": "preparando", "inicio": iso(agora()),
                                              "status_anterior": status_anterior, "chaves": []}))
    except FileExistsError:
        raise Recusa(f"já existe uma publicação em andamento ou sem resposta clara deste post ({arq.name}). "
                     f"Rode: python -X utf8 skills/publicar-instagram/scripts/publicar.py conferir --post {ctx.id}") from None


def atualizar_trava(ctx: Contexto, **dados) -> None:
    arq = arquivo_trava(ctx.marca, ctx.id)
    atual = ler_json(arq)
    atual.update(dados)
    gravar_json(arq, atual)


def soltar_trava(ctx: Contexto) -> None:
    arquivo_trava(ctx.marca, ctx.id).unlink(missing_ok=True)


def ja_publicado(ctx: Contexto) -> dict | None:
    for linha in registros_publicados(ctx.marca):
        if linha.get("post_id") == ctx.id:
            return linha
    pub = ctx.post.get("publicacao")
    if isinstance(pub, dict) and pub.get("media_id"):
        return {"publicado_em": pub.get("publicado_em"), "permalink": pub.get("permalink")}
    return None


# ---------------------------------------------------------------- publicação

def preparar_conta(ctx: Contexto, env: dict) -> tuple[str, str, str]:
    """Confere token, conta, arroba da marca e cota. Devolve (token, ig_id, nome de usuário)."""
    arroba = credenciais.arroba_da_marca(ctx.marca)
    if not arroba:
        raise Recusa(f"falta a 'arroba' em marcas/{ctx.marca}/visual.json (por exemplo \"@meuperfil\"). Sem ela não dá para "
                     "conferir que o token é da conta certa, então a publicação é recusada. Nada foi publicado")
    token = env["IG_ACCESS_TOKEN"]
    try:
        conta = ig.perfil(token, "user_id,username")
    except ig.ErroMeta as e:
        raise Recusa(str(e)) from None
    ig_id = str(conta.get("user_id") or conta.get("id") or "")
    if not re.fullmatch(r"\d{3,30}", ig_id):
        raise Recusa("não achei o id da conta do Instagram com esse token")
    if env.get("IG_USER_ID") and env["IG_USER_ID"] != ig_id:
        raise Recusa("o token é de outra conta do Instagram (o IG_USER_ID gravado é diferente). "
                     "Rode credenciais.py configurar para trocar o token")
    if arroba != str(conta.get("username") or "").lower():
        raise Recusa(f"o token é da conta @{conta.get('username')}, mas esta marca usa @{arroba} (visual.json). "
                     "Nada foi publicado")
    usados, total, _ = ig.cota(token, ig_id)
    if total and usados is not None and usados >= total:
        raise Recusa(f"a cota de publicação da Meta acabou ({usados} de {total} nas últimas 24 h)")
    aviso = credenciais.aviso_validade(env, ctx.marca)
    if aviso:
        print(aviso)
    print(f"Conta: @{conta.get('username')}" + (f" | cota nas últimas 24 h: {usados} de {total}" if total else ""))
    return token, ig_id, str(conta.get("username") or "")


def limpar_objetos(a: arm.Armazenamento, chaves: list[str]) -> None:
    for chave in chaves:
        try:
            a.apagar(chave)
        except RuntimeError as e:
            print(f"  aviso: não apaguei {chave} ({e}). A regra de ciclo de vida do bucket apaga depois.")


def registrar_sucesso(ctx: Contexto, media_id: str, link: str, hash_: str, por: str, nota: str = "") -> str:
    publicado_em = iso(agora())
    onde = registrar_publicado(ctx.marca, {"publicado_em": publicado_em, "post_id": ctx.id, "lote": ctx.lote,
                                           "formato": ctx.post.get("formato"), "media_id": media_id,
                                           "permalink": link, "hash": hash_})
    if onde == "reserva":
        print("  aviso: o publicados.csv está aberto em outro programa; o registro foi para publicados-pendentes.jsonl "
              "e entra no CSV na próxima publicação.")
    gravar_post(ctx, {"status": "publicado", "agendado_para": None,
                      "publicacao": {"media_id": media_id, "permalink": link, "publicado_em": publicado_em}},
                f"publicado: {link or media_id}" + (f" ({nota})" if nota else ""), por)
    return publicado_em


def publicar_post(ctx: Contexto, origem: str = "manual", de_novo: bool = False) -> dict:
    """Publica um post aprovado. Levanta Recusa (nada feito), Incerto (pode ter ido ao ar) ou ErroUso (falhou)."""
    por = POR_ROTINA if origem == "agendados" else POR_SCRIPT
    if arquivo_trava(ctx.marca, ctx.id).is_file():
        raise Recusa("há uma publicação deste post sem resposta clara. Rode: python -X utf8 "
                     f"skills/publicar-instagram/scripts/publicar.py conferir --post {ctx.id}")
    status = ctx.post.get("status")
    if origem == "agendados":
        permitidos = ("agendado",)
    else:
        permitidos = ("aprovado", "agendado") + (("publicado",) if de_novo else ())
    if status not in permitidos:
        if status == "publicado":
            raise Recusa("este post já foi publicado. Use --de-novo só se a pessoa pedir outra publicação")
        if origem == "agendados":
            raise Recusa(f"o post deixou de estar agendado (status '{status}')")
        raise Recusa(f"só se publica post 'aprovado' (o status é '{status}')")
    a = analisar(ctx)
    exigir_aprovacao_valida(ctx, a)
    if a.problemas:
        mostrar_problemas(a)
        raise Recusa("o post tem problemas, então não foi publicado")
    anterior = ja_publicado(ctx)
    if anterior and not de_novo:
        raise Recusa(f"este post já foi publicado em {anterior.get('publicado_em')} ({anterior.get('permalink')}). "
                     "Use --de-novo só se a pessoa pedir outra publicação")
    if anterior and de_novo:
        # Publicar de novo o que já está no ar também exige uma pessoa: janela ou terminal, nunca só o agente.
        linhas = [("Post", ctx.id), ("Já publicado em", str(anterior.get("publicado_em") or "data não registrada")),
                  ("Link atual", str(anterior.get("permalink") or "sem link registrado")),
                  ("Início da legenda", resumo_texto(a.legenda_final)),
                  ("O que acontece", "o mesmo conteúdo vai ao ar outra vez, como um post novo; o estúdio não apaga o anterior")]
        print("Aguardando a confirmação da pessoa (uma janela ou uma pergunta no terminal)…")
        if not confirmar_com_a_pessoa("Publicar DE NOVO um post que já está no ar?", linhas, ctx.id, "Publicar de novo"):
            raise Recusa("a pessoa não confirmou a nova publicação. Nada foi publicado")
    env = credenciais.carregar_instagram(ctx.marca)
    armazenamento = arm.Armazenamento.carregar(ctx.marca)
    token, ig_id, usuario = preparar_conta(ctx, env)

    criar_trava(ctx, status)
    try:
        # Corrida: entre as checagens e a trava, outra execução pode ter publicado o post, ou a pessoa pode ter
        # desagendado ou editado. Relê tudo com a trava na mão e confere de novo.
        ctx.recarregar()
        a = analisar(ctx, com_validador=False)
        atual = ctx.post.get("status")
        if atual not in permitidos:
            raise Recusa(f"o status do post mudou para '{atual}' enquanto o comando começava; nada foi enviado")
        exigir_aprovacao_valida(ctx, a)
        if a.problemas:
            mostrar_problemas(a)
            raise Recusa("o post passou a ter problemas enquanto o comando começava; nada foi enviado")
        if not de_novo and ja_publicado(ctx):
            raise Recusa("este post foi publicado por outra execução enquanto este comando começava; nada foi enviado")
    except BaseException:
        soltar_trava(ctx)
        raise
    etapa, chaves = "preparando", []
    inicio = agora()
    try:
        jpegs = [converter_para_jpeg(x["bytes"]) for x in a.artes]
        etapa = "enviando"
        urls = []
        for x, jpeg in zip(a.artes, jpegs):
            chave = armazenamento.chave_nova(ctx.id, f"{x['n']:02d}.jpg")
            chaves.append(chave)
            atualizar_trava(ctx, etapa=etapa, chaves=chaves)
            url = armazenamento.enviar_jpeg(jpeg, chave)
            problemas_url = arm.conferir_url(url, len(jpeg))
            if problemas_url:
                raise ErroUso(f"a URL pública da arte {x['n']:02d} não abre direito ({'; '.join(problemas_url)}). "
                              "Veja docs/armazenamento-imagens.md")
            urls.append(url)
            print(f"  arte {x['n']:02d} enviada e conferida ({kb(len(jpeg))})")
        etapa = "contêineres"
        slides = {s["n"]: s for s in ctx.post["slides"]}
        if len(a.artes) == 1:
            dados = {"image_url": urls[0], "caption": a.legenda_final}
            alt = texto_alternativo(slides[1])
            final = ig.criar_conteiner(token, ig_id, {**dados, **({"alt_text": alt} if alt else {})})
        else:
            filhos = []
            for x, url in zip(a.artes, urls):
                alt = texto_alternativo(slides[x["n"]])
                filho = ig.criar_conteiner(token, ig_id, {"image_url": url, "is_carousel_item": "true",
                                                          **({"alt_text": alt} if alt else {})})
                ig.aguardar_conteiner(token, filho)
                filhos.append(filho)
                print(f"  slide {x['n']:02d} pronto na Meta")
            final = ig.criar_conteiner(token, ig_id, {"media_type": "CAROUSEL", "children": ",".join(filhos),
                                                      "caption": a.legenda_final})
        ig.aguardar_conteiner(token, final)
        atualizar_trava(ctx, etapa="publicando", creation_id=final, chaves=chaves)
        etapa = "publicando"
        media_id = ig.publicar_conteiner(token, ig_id, final, a.legenda_final, inicio - timedelta(minutes=5))
    except Incerto as e:
        gravar_post(ctx, {"status": "erro"}, f"sem resposta clara da Meta ao publicar; aguardando conferência ({mascarar(e)})", por)
        raise
    except BaseException as e:
        if etapa == "publicando" and not isinstance(e, ig.ErroMeta):
            gravar_post(ctx, {"status": "erro"}, f"interrompido ao publicar; aguardando conferência ({mascarar(e)})", por)
            raise Incerto(f"a publicação foi interrompida no meio ({type(e).__name__}); o post PODE ter ido ao ar") from None
        limpar_objetos(armazenamento, chaves)
        soltar_trava(ctx)
        if isinstance(e, KeyboardInterrupt):
            gravar_post(ctx, {"status": "erro"}, "publicação interrompida pela pessoa antes de publicar", por)
            raise
        mensagem = mascarar(e)
        gravar_post(ctx, {"status": "erro"}, f"erro ao publicar (nada foi publicado): {mensagem[:400]}", por)
        if isinstance(e, ErroUso):
            raise
        raise ErroUso(f"não consegui publicar ({type(e).__name__}: {mensagem}). Nada foi publicado") from None

    print(f"  publicado (media_id {media_id})")
    link = ""
    for tentativa in range(3):
        link = ig.permalink(token, media_id)
        if link.startswith(("http://", "https://")):
            break
        time.sleep(2)
    nota = "de novo" if anterior else ("agendado" if origem == "agendados" else "")
    if not link.startswith(("http://", "https://")):
        link = f"https://www.instagram.com/{usuario}/"
        nota = (nota + "; " if nota else "") + "link do post indisponível, registrei o do perfil"
        print("ATENÇÃO: a Meta não devolveu o link do post. Registrei o link do perfil; o post está no ar.")
    registrar_sucesso(ctx, media_id, link, ctx.post["aprovacao"]["hash"], por, nota)
    soltar_trava(ctx)
    limpar_objetos(armazenamento, chaves)
    return {"media_id": media_id, "permalink": link}


def texto_alternativo(slide: dict) -> str:
    alt = str(slide.get("texto_alternativo") or "").strip()
    if not alt:
        alt = " ".join(p for p in (str(slide.get("titulo") or ""), str(slide.get("texto") or "").replace("\n", " ")) if p.strip())
    return alt[:1000]


def cmd_publicar(args) -> int:
    ctx = carregar_contexto(args)
    print(f"Publicando {ctx.id} na marca {ctx.marca}…")
    r = publicar_post(ctx, "manual", args.de_novo)
    print(f"PUBLICADO: {r['permalink'] or r['media_id']}")
    return 0


# ---------------------------------------------------------------- rotina: agendados

def posts_agendados(marca: str) -> list[tuple[datetime | None, Path]]:
    achados = []
    for caminho in sorted((pasta_marca(marca) / "conteudo").glob("*/posts/*.json")):
        try:
            p = ler_json(caminho)
        except (OSError, ValueError):
            continue
        if isinstance(p, dict) and p.get("status") == "agendado":
            achados.append((interpretar_data(p.get("agendado_para")), caminho))
    return sorted(achados, key=lambda t: (t[0] is None, t[0] or agora()))


def cmd_agendados(args) -> int:
    marca = escolher_marca(args.marca)
    if args.janela_horas <= 0:
        raise ErroUso("--janela-horas precisa ser maior que zero")
    janela = timedelta(hours=args.janela_horas)
    agendados = posts_agendados(marca)
    if not agendados:
        print("Nenhum post agendado.")
        return 0
    agora_ = agora()
    vencidos = [(q, c) for q, c in agendados if q is None or q <= agora_]
    if not vencidos:
        print(f"{len(agendados)} agendado(s); nenhum no horário ainda. Próximo: {iso(agendados[0][0])}.")
        return 0
    if args.simular:
        for quando, caminho in vencidos:
            atraso = (agora_ - quando) if quando else None
            situacao = "data ilegível" if quando is None else (
                f"no horário (atraso de {int(atraso.total_seconds() // 60)} min)" if atraso <= janela
                else f"PASSOU DA JANELA de {args.janela_horas:g} h (não seria publicado)")
            try:
                p = ler_json(caminho)
                if isinstance(p, dict) and not assin.verificar(marca, caminho.stem, p.get("aprovacao")).valida:
                    situacao += f" | {assin.MENSAGEM_REAPROVAR}: NÃO seria publicado"
            except (OSError, ValueError):
                pass
            print(f"  [simulação] {caminho.stem}: {situacao}")
        print("Simulação: nada foi publicado.")
        return 0

    log = abrir_log(marca, "agendados")
    proteger_saida(log)
    trava = pasta_marca(marca) / "publicacao" / "execucao.lock"
    tomou, dono = tomar_trava_execucao(trava)
    if not tomou:
        print(f"Outra execução está em andamento (PID {dono.get('pid')}, desde {dono.get('inicio')}); saí sem fazer nada.")
        return 0
    try:
        aviso = credenciais.renovar_se_preciso(marca)
        if aviso:
            print(aviso)
        publicados = falhas = incertos = 0
        for _, caminho in vencidos:
            try:
                ctx = Contexto(marca, caminho)  # relê o arquivo: a lista foi montada antes de pegar a trava
            except (OSError, ValueError, ErroUso) as e:
                print(f"{caminho.stem}: não consegui usar o arquivo do post ({e}); pulei.")
                falhas += 1
                continue
            if ctx.post.get("status") != "agendado":
                print(f"{ctx.id}: deixou de estar agendado (status '{ctx.post.get('status')}'); pulei.")
                continue
            quando = interpretar_data(ctx.post.get("agendado_para"))
            agora_ = agora()
            try:
                if quando is None:
                    gravar_post(ctx, {"status": "erro", "agendado_para": None},
                                "data de agendamento ilegível; post não publicado", POR_ROTINA)
                    print(f"{ctx.id}: data de agendamento ilegível; marcado como erro.")
                    falhas += 1
                    continue
                if quando > agora_:
                    print(f"{ctx.id}: foi reagendado para {iso(quando)}; pulei.")
                    continue
                atraso = agora_ - quando
                if atraso > janela:
                    gravar_post(ctx, {"status": "erro", "agendado_para": None},
                                f"janela de atraso perdida: agendado para {iso(quando)}, verificado em {iso(agora_)} "
                                f"(limite de {args.janela_horas:g} h); não publicado", POR_ROTINA)
                    print(f"{ctx.id}: perdeu a janela de {args.janela_horas:g} h (era para {iso(quando)}); NÃO publicado. "
                          "Peça à pessoa um novo ok e um novo horário.")
                    falhas += 1
                    continue
                print(f"{ctx.id}: no horário (atraso de {int(atraso.total_seconds() // 60)} min); publicando…")
                r = publicar_post(ctx, "agendados")
                print(f"{ctx.id}: PUBLICADO {r['permalink'] or r['media_id']}")
                publicados += 1
            except Incerto as e:
                print(f"{ctx.id}: SEM RESPOSTA CLARA ({e}). Rode: publicar.py conferir --post {ctx.id}")
                incertos += 1
            except ErroUso as e:
                print(f"{ctx.id}: não publicado ({e})")
                falhas += 1
        print(f"Resumo: {publicados} publicado(s), {falhas} com problema, {incertos} sem resposta clara.")
        return 3 if incertos else (1 if falhas else 0)
    finally:
        soltar_trava_execucao(trava)


# ---------------------------------------------------------------- conferir

def cmd_conferir(args) -> int:
    ctx = carregar_contexto(args)
    arq = arquivo_trava(ctx.marca, ctx.id)
    if not arq.is_file():
        print("Nada pendente para este post (não há publicação sem resposta clara).")
        return 0
    try:
        trava = ler_json(arq)
    except (OSError, ValueError):
        trava = {}  # trava vazia ou cortada: foi criada antes de qualquer envio, então nada externo aconteceu
    if not isinstance(trava, dict):
        trava = {}
    env = credenciais.carregar_instagram(ctx.marca)
    armazenamento = arm.Armazenamento.carregar(ctx.marca)
    token = env["IG_ACCESS_TOKEN"]
    ig_id = env.get("IG_USER_ID") or str(ig.perfil(token, "user_id,username").get("user_id") or "")
    if not re.fullmatch(r"\d{3,30}", ig_id):
        raise ErroUso("não achei o id da conta do Instagram. Rode: credenciais.py verificar")
    a = analisar(ctx, com_validador=False)
    assinatura = conferir_assinatura(ctx)
    inicio = interpretar_data(trava.get("inicio")) or agora()
    idade = (agora() - inicio).total_seconds()
    final = trava.get("creation_id")
    chaves = trava.get("chaves") if isinstance(trava.get("chaves"), list) else []  # limpar_objetos só apaga chaves ig/...
    adulterada = bool(final) and not (isinstance(final, str) and re.fullmatch(r"\d{5,30}", final))
    if adulterada:
        print("AVISO: o número do contêiner na trava está com defeito (arquivo alterado?); não vou consultá-lo.")
        final = None
    situacao = ig.chamar(token, final, {"fields": "status_code"}).get("status_code") if final else None
    achado = ig.midia_recente(token, ig_id, a.legenda_final, inicio - timedelta(minutes=5))
    por = POR_SCRIPT

    if situacao == "PUBLISHED" or achado:
        if not achado:
            print(f"O contêiner {final} consta como PUBLISHED, mas o post não apareceu na lista recente. Confira o "
                  "feed do Instagram antes de qualquer coisa; a trava continua.")
            return 3
        hash_ = ctx.post["aprovacao"]["hash"] if assinatura.valida else ""
        nota = "registrado pelo conferir" + ("" if assinatura.valida else "; aprovação sem assinatura válida, hash não registrado")
        registrar_sucesso(ctx, str(achado["id"]), str(achado.get("permalink") or ""), hash_, por, nota)
        limpar_objetos(armazenamento, chaves)
        soltar_trava(ctx)
        print(f"O post FOI ao ar: {achado.get('permalink')}. Registrado no publicados.csv.")
        return 0

    nunca_enviou = not final and not adulterada
    seguro = nunca_enviou or situacao in ("FINISHED", "IN_PROGRESS")
    if seguro and not nunca_enviou and idade < ESPERA_CONFERIR_S:
        print(f"A tentativa é recente ({int(idade)} s) e a Meta pode ainda estar processando. Espere "
              f"{int(ESPERA_CONFERIR_S - idade) + 1} s e rode 'conferir' de novo.")
        return 3
    if not seguro and args.confirmo_que_nao_foi_ao_ar:
        # Afirmar "não está no feed" também exige uma pessoa: janela ou terminal, nunca só o agente.
        linhas = [("Post", ctx.id), ("Início da legenda", resumo_texto(a.legenda_final)),
                  ("Situação na Meta", f"não consegui provar (status do contêiner: {situacao})"),
                  ("O que você confirma", "que abriu o feed do Instagram e este post NÃO está lá. Se confirmar, o post "
                                          "volta para 'aprovado' e pode ser publicado de novo")]
        print("Aguardando a confirmação da pessoa (uma janela ou uma pergunta no terminal)…")
        if not confirmar_com_a_pessoa("O post NÃO está no feed?", linhas, ctx.id, "Confirmo: o post NÃO está no feed"):
            print("A pessoa não confirmou. Nada foi alterado; a trava continua.")
            return 3
    if seguro or args.confirmo_que_nao_foi_ao_ar:
        limpar_objetos(armazenamento, chaves)
        soltar_trava(ctx)
        if assinatura.valida:
            gravar_post(ctx, {"status": "aprovado", "agendado_para": None},
                        f"conferência: o post NÃO foi ao ar (status do contêiner: {situacao}); liberado para nova tentativa", por)
            print(f"O post NÃO foi ao ar (status do contêiner: {situacao}). Está 'aprovado' de novo; só publique de novo "
                  "com o ok da pessoa.")
            return 0
        # Sem assinatura válida não existe aprovação para devolver: o post não volta para 'aprovado'.
        mudancas = {"status": "arte_pronta" if assinatura.definitiva else "erro", "agendado_para": None}
        if assinatura.definitiva:
            mudancas["aprovacao"] = None
        gravar_post(ctx, mudancas, f"conferência: o post NÃO foi ao ar (status do contêiner: {situacao}); "
                                   f"aprovação sem assinatura válida ({assinatura.motivo}), então não volta para 'aprovado'", por)
        print(f"O post NÃO foi ao ar (status do contêiner: {situacao}), mas {assin.MENSAGEM_REAPROVAR}. "
              f"Motivo: {assinatura.motivo}. O post ficou em '{mudancas['status']}'.")
        return 0
    print(f"Não consegui provar que o post NÃO foi ao ar (status do contêiner: {situacao}). Abra o feed do Instagram: "
          "se o post NÃO estiver lá, a pessoa roda 'conferir' de novo com --confirmo-que-nao-foi-ao-ar; "
          "se estiver, me avise para registrar o link.")
    return 3


# ---------------------------------------------------------------- linha de comando

def main(argv=None) -> int:
    proteger_saida()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcao_raiz(p)
    sub = p.add_subparsers(dest="comando", required=True)

    def comando(nome, ajuda, post=True):
        s = sub.add_parser(nome, help=ajuda)
        s.add_argument("--marca", help="slug da marca (pode omitir se houver só uma além de 'exemplo')")
        opcao_raiz(s, subcomando=True)
        if post:
            s.add_argument("--post", required=True, help="id do post ou caminho do .json")
        return s

    comando("simular", "mostra o que vai sair e roda as checagens (sem rede)")
    s = comando("aprovar", "registra a aprovação da pessoa para esta versão")
    s.add_argument("--frase", required=True, help="frase literal da pessoa, citando o id (ex.: 'pode publicar ID')")
    s.add_argument("--por", required=True, help="nome de quem aprovou")
    s = comando("agendar", "agenda um post aprovado")
    s.add_argument("--quando", required=True, help="data e hora ISO com fuso, ex.: 2026-11-05T18:00:00-03:00")
    comando("desagendar", "cancela o agendamento (volta para aprovado)")
    s = comando("publicar", "publica um post aprovado agora")
    s.add_argument("--de-novo", action="store_true", help="publica outra vez um post já publicado (só se a pessoa pedir)")
    s = comando("agendados", "publica os agendados cujo horário chegou (comando da rotina)", post=False)
    s.add_argument("--janela-horas", type=float, default=JANELA_PADRAO_HORAS, help="atraso máximo aceito (padrão 2)")
    s.add_argument("--simular", action="store_true", help="só mostra o que seria feito")
    s = comando("conferir", "resolve uma publicação sem resposta clara")
    s.add_argument("--confirmo-que-nao-foi-ao-ar", action="store_true",
                   help="use só depois de olhar o feed do Instagram e ver que o post NÃO está lá")
    s = comando("situacao", "lista os posts da marca", post=False)
    s.add_argument("--todos", action="store_true", help="inclui rascunhos")
    a = p.parse_args(argv)
    aplicar_raiz(a)
    funcoes = {"simular": cmd_simular, "aprovar": cmd_aprovar, "agendar": cmd_agendar, "desagendar": cmd_desagendar,
               "publicar": cmd_publicar, "agendados": cmd_agendados, "conferir": cmd_conferir, "situacao": cmd_situacao}
    return funcoes[a.comando](a)


if __name__ == "__main__":
    executar(main)
