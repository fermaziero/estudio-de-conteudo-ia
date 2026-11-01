#!/usr/bin/env python3
"""Autoteste da skill publicar-instagram, sem rede real.

Rode a partir da raiz do projeto (no macOS e no Linux, use python3):

    python -X utf8 skills/publicar-instagram/scripts/autoteste.py [filtro]

Sobe um servidor falso neste computador (só no endereço 127.0.0.1) que imita a API do Instagram e um
armazenamento S3 com URL pública, copia os scripts para uma pasta temporária com uma marca fictícia e
roda os comandos de verdade contra ele. Nada toca a Meta, o armazenamento real, as suas marcas ou as
suas credenciais. Todos os dados são inventados. Com [filtro], roda só os testes cujo nome contém o texto.

Código de saída: 0 = tudo passou; 1 = algum teste falhou.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import _armazenamento as arm  # noqa: E402

TOKEN = "IG" + "A" * 60 + "TESTE"
TOKEN_NOVO = "IG" + "B" * 60 + "NOVO"
CHAVE_ID = "CHAVEIDTESTE"
CHAVE_SECRETA = "segredo/de+teste/1234567890"
BUCKET, IG_ID, LOTE = "bucket-teste", "17841400000000001", "2026-11-03-semana-1"
SEGREDOS = (TOKEN, TOKEN_NOVO, CHAVE_SECRETA)

# Driver dos testes do publicar.py. A confirmação de uma pessoa (janela ou terminal) não tem flag nem variável de ambiente
# para ser pulada; aqui ela é trocada DENTRO do processo de teste (monkeypatch), e só aqui.
DRIVER = """
import json, os, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["AUTOTESTE_SCRIPTS"])
modo = os.environ["AUTOTESTE_MODO"]
import publicar
if modo == "sim":
    publicar.confirmar_com_a_pessoa = lambda *a, **k: True
elif modo == "nao":
    publicar.confirmar_com_a_pessoa = lambda *a, **k: False
else:
    sys.modules["tkinter"] = None
    if modo == "terminal":
        class Terminal:
            def isatty(self):
                return True
            def readline(self):
                return os.environ["AUTOTESTE_DIGITADO"] + chr(10)
        sys.stdin = Terminal()
for nome, codigo in json.loads(os.environ["AUTOTESTE_GANCHOS"]).items():
    def envolver(original, codigo):
        def nova(*a, **k):
            resultado = original(*a, **k)
            exec(codigo, {"publicar": publicar, "os": os, "json": json, "Path": Path})
            return resultado
        return nova
    setattr(publicar, nome, envolver(getattr(publicar, nome), codigo))
sys.argv = ["publicar.py"] + sys.argv[1:]
publicar.executar(publicar.main)
"""


# ---------------------------------------------------------------- servidor falso

class Estado:
    def __init__(self):
        self.reset()

    def reset(self):
        self.puts, self.objetos, self.apagados = {}, {}, []
        self.conteineres, self.publicados, self.antigas, self.insights = {}, [], [], {}
        self.chamadas, self.agentes, self.cenario = [], [], {}
        self.token, self.n = TOKEN, 1000

    def novo_id(self):
        self.n += 1
        return f"1790{self.n:010d}"


F = Estado()
TRAVA = threading.Lock()


class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def responder(self, status, corpo, tipo="application/json"):
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(dados)

    def erro(self, status, msg, codigo, sub=None, transitorio=False):
        e = {"message": msg, "type": "OAuthException", "code": codigo, "is_transient": transitorio}
        if sub:
            e["error_subcode"] = sub
        self.responder(status, {"error": e})

    def form(self):
        n = int(self.headers.get("Content-Length") or 0)
        return dict(urllib.parse.parse_qsl(self.rfile.read(n).decode("utf-8"))) if n else {}

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = lambda self: self.despachar()

    def despachar(self):
        p = urllib.parse.urlsplit(self.path)
        with TRAVA:
            F.chamadas.append((self.command, p.path))
        if p.path.startswith(f"/{BUCKET}/"):
            return self.s3(p.path, p.query)
        if p.path.startswith("/pub/"):
            return self.publico(p.path[5:])
        if p.path.startswith("/graph/"):
            return self.graph(re.sub(r"^/v\d+\.\d+", "", p.path[6:]), dict(urllib.parse.parse_qsl(p.query)))
        self.responder(404, {})

    def s3(self, caminho, consulta):
        chave = caminho[len(BUCKET) + 2:]
        params = dict(urllib.parse.parse_qsl(consulta))
        cab = {k.lower(): v for k, v in self.headers.items()}
        assinados = [h for h in params.get("X-Amz-SignedHeaders", "").split(";") if h != "host"]
        usados = {h: cab[h] for h in assinados if h in cab}
        quando = datetime.strptime(params["X-Amz-Date"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        esperado = arm.url_assinada(self.command, self.headers["Host"], caminho, CHAVE_ID, CHAVE_SECRETA, regiao="auto",
                                    expira=int(params["X-Amz-Expires"]), cabecalhos=usados, quando=quando, esquema="http")
        if len(usados) != len(assinados) or esperado.split("X-Amz-Signature=")[1] != params["X-Amz-Signature"]:
            return self.responder(403, b"<Error><Code>SignatureDoesNotMatch</Code></Error>", "application/xml")
        if self.command == "PUT":
            F.objetos[chave] = F.puts[chave] = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            return self.responder(200, b"", "application/xml")
        F.objetos.pop(chave, None)
        F.apagados.append(chave)
        self.responder(204, b"", "application/xml")

    def publico(self, chave):
        agente = self.headers.get("User-Agent", "")
        with TRAVA:
            F.agentes.append(agente)
        if F.cenario.get("robo_bloqueado") and "facebookexternalhit" in agente:
            return self.responder(403, b"bloqueado", "text/plain")
        if chave in F.objetos:
            return self.responder(200, F.objetos[chave], "image/jpeg")
        self.responder(404, b"nao existe", "text/plain")

    def graph(self, caminho, params):
        if caminho == "/refresh_access_token":
            if params.get("access_token") != F.token:
                return self.erro(400, "Invalid OAuth access token", 190)
            F.token = TOKEN_NOVO
            return self.responder(200, {"access_token": TOKEN_NOVO, "token_type": "bearer", "expires_in": 5183944})
        if self.headers.get("Authorization") != f"Bearer {F.token}":
            return self.erro(400, "Invalid OAuth access token", 190)
        alvo, _, resto = caminho.strip("/").partition("/")
        campos = params.get("fields", "").split(",")
        if alvo == "me":
            r = {"user_id": IG_ID, "id": "9999", "username": "marca_teste", "account_type": "BUSINESS",
                 "followers_count": 1234, "follows_count": 56, "media_count": 78}
            return self.responder(200, {k: v for k, v in r.items() if k in campos or k == "id"})
        if alvo == IG_ID and resto == "content_publishing_limit":
            return self.responder(200, {"data": [{"quota_usage": len(F.publicados), "config": {"quota_total": 50, "quota_duration": 86400}}]})
        if alvo == IG_ID and resto == "insights":
            return self.responder(200, {"data": [{"name": "reach", "period": "day", "total_value": {"value": 7}}]})
        if alvo == IG_ID and resto == "media" and self.command == "POST":
            return self.criar_conteiner(self.form())
        if alvo == IG_ID and resto == "media":
            todas = sorted(F.publicados + F.antigas, key=lambda m: m["timestamp"], reverse=True)
            ini = int(params.get("after", 0))
            lim = int(params.get("limit", 25))
            pag = {"cursors": {"after": str(ini + lim)}}
            return self.responder(200, {"data": [{k: v for k, v in m.items() if k in campos or k == "id"} for m in todas[ini:ini + lim]], "paging": pag})
        if alvo == IG_ID and resto == "media_publish":
            return self.publicar(self.form())
        if resto == "insights":
            dados = F.insights.get(alvo)
            pedidas = params.get("metric", "").split(",")
            if dados is None:
                return self.responder(200, {"data": []})
            ruim = [m for m in pedidas if m not in dados]
            if ruim:
                return self.erro(400, f"(#100) The {ruim[0]} metric is not supported for this media", 100)
            return self.responder(200, {"data": [{"name": m, "period": "lifetime", "values": [{"value": dados[m]}]} for m in pedidas]})
        if alvo in F.conteineres:
            if F.cenario.get("queda_status"):
                return self.erro(500, "Service temporarily unavailable", 2, transitorio=True)
            return self.responder(200, {"id": alvo, "status_code": F.conteineres[alvo]["estado"]})
        for m in F.publicados + F.antigas:
            if m["id"] == alvo:
                return self.responder(200, {k: v for k, v in m.items() if k in campos or k == "id"})
        self.erro(400, "Object does not exist", 100)

    def criar_conteiner(self, f):
        cid = F.novo_id()
        c = {"id": cid, "dados": f, "estado": "FINISHED"}
        if "image_url" in f and f["image_url"].split("/pub/", 1)[-1] not in F.objetos:
            return self.erro(400, "Media could not be fetched from this uri", 9004, 2207052)
        if f.get("media_type") == "CAROUSEL" and not all(x in F.conteineres for x in f.get("children", "").split(",")):
            return self.erro(400, "Invalid children", 100, 2207028)
        F.conteineres[cid] = c
        self.responder(200, {"id": cid})

    def publicar(self, f):
        c = F.conteineres.get(f.get("creation_id"))
        if not c:
            return self.erro(400, "Invalid container", 100, 2207008)
        modo = F.cenario.get("publicar")
        if modo == "incerto_publicou_e_queda":
            self.registrar(c)
            F.cenario["queda_status"] = True
            return self.erro(500, "An unexpected error has occurred", 2, transitorio=True)
        self.responder(200, {"id": self.registrar(c)})

    def registrar(self, c):
        mid = F.novo_id()
        F.publicados.append({"id": mid, "caption": c["dados"].get("caption", ""), "permalink": f"https://www.instagram.com/p/FAKE{mid[-5:]}/",
                             "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000"),
                             "media_type": "CAROUSEL_ALBUM" if c["dados"].get("media_type") == "CAROUSEL" else "IMAGE",
                             "media_product_type": "FEED", "like_count": 3, "comments_count": 1})
        c["estado"] = "PUBLISHED"
        return mid


# ---------------------------------------------------------------- projeto fictício

class Ambiente:
    def __init__(self, base: Path, porta: int):
        self.base, self.porta = base, porta
        self.projeto, self.config = base / "projeto", base / "config"
        self.scripts = self.projeto / "skills" / "publicar-instagram" / "scripts"
        self.marca = self.projeto / "marcas" / "teste"

    def novo(self, credenciais=True, token_dias=50):
        F.reset()
        for pasta in (self.projeto, self.config):
            shutil.rmtree(pasta, ignore_errors=True)
        self.scripts.mkdir(parents=True)
        for arquivo in AQUI.glob("*.py"):
            if arquivo.name != "autoteste.py":
                shutil.copy(arquivo, self.scripts / arquivo.name)
        (self.marca / "conteudo" / LOTE / "posts").mkdir(parents=True)
        (self.marca / "visual.json").write_text(json.dumps({"arroba": "@marca_teste"}), encoding="utf-8")
        if credenciais:
            pasta = self.config / "teste"
            pasta.mkdir(parents=True)
            (pasta / "instagram.env").write_text(
                f"IG_ACCESS_TOKEN={TOKEN}\nIG_USER_ID=\nIG_TOKEN_VALIDO_ATE={date.today() + timedelta(days=token_dias)}\n", encoding="utf-8")
            (pasta / "armazenamento.env").write_text(
                f"ARMAZENAMENTO_ENDPOINT=http://127.0.0.1:{self.porta}\nARMAZENAMENTO_REGIAO=auto\nARMAZENAMENTO_BUCKET={BUCKET}\n"
                f"ARMAZENAMENTO_CHAVE_ID={CHAVE_ID}\nARMAZENAMENTO_CHAVE_SECRETA={CHAVE_SECRETA}\n"
                f"ARMAZENAMENTO_URL_PUBLICA=http://127.0.0.1:{self.porta}/pub\n", encoding="utf-8")

    def _env(self, **extra):
        return dict(os.environ, ESTUDIO_CONFIG=str(self.config), PYTHONDONTWRITEBYTECODE="1",
                    ESTUDIO_INSTAGRAM_TESTE=f"http://127.0.0.1:{self.porta}/graph", **extra)

    def _correr(self, comando, rotulo, env, rede):
        antes = len(F.chamadas)
        r = subprocess.run(comando, cwd=str(self.projeto), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, stdin=subprocess.DEVNULL, timeout=300)
        saida = (r.stdout or "") + (r.stderr or "")
        assert rede or len(F.chamadas) == antes, f"{rotulo} não deveria usar a rede"
        for s in SEGREDOS:
            assert s not in saida, f"segredo vazou na saída de {rotulo}"
        chave = self.config / "teste" / "aprovacao.key"
        if chave.is_file():
            segredo = chave.read_text(encoding="ascii", errors="replace").strip()
            assert len(segredo) < 32 or segredo not in saida, f"a chave de aprovação vazou na saída de {rotulo}"
        assert "Traceback" not in saida, f"traceback cru na saída de {rotulo}: {saida[-600:]}"
        return r.returncode, r.stdout or "", r.stderr or ""

    def rodar(self, script, *args, rede=True):
        comando = [sys.executable, "-X", "utf8", str(self.scripts / script), *map(str, args)]
        return self._correr(comando, f"{script} {args}", self._env(), rede)

    def pub(self, *args, modo="semtk", digitado="", ganchos=None, rede=True):
        """Roda o publicar.py por um driver que, DENTRO do processo, troca a confirmação da pessoa (o produto não tem
        flag nem variável de ambiente para isso). modo: 'sim' e 'nao' trocam a função; 'semtk' bloqueia o tkinter e não
        há terminal (o fluxo real recusa); 'terminal' bloqueia o tkinter e simula um terminal onde a pessoa digita
        `digitado`. ganchos: código a executar depois de funções do publicar (simula corridas)."""
        env = self._env(AUTOTESTE_SCRIPTS=str(self.scripts), AUTOTESTE_MODO=modo, AUTOTESTE_DIGITADO=digitado,
                        AUTOTESTE_GANCHOS=json.dumps(ganchos or {}))
        comando = [sys.executable, "-X", "utf8", "-c", DRIVER, *map(str, args)]
        return self._correr(comando, f"publicar.py {args} (modo {modo})", env, rede)

    def criar_post(self, pid, formato="carrossel", n=3, **extra):
        from PIL import Image, ImageDraw
        slides = [{"n": i, "papel": "capa" if i == 1 else ("cta" if i == n and formato == "carrossel" else "conteudo"),
                   "layout": "capa" if i == 1 else "texto", "titulo": f"Título do slide {i}", "texto": "Apoio.", "itens": [],
                   "imagem": None, "texto_alternativo": f"Descrição fictícia {i}", "fonte_interna": "autoral"} for i in range(1, n + 1)]
        post = {"versao_esquema": 1, "id": pid, "lote": LOTE, "titulo_interno": "Post de teste", "pilar": "educativo",
                "formato": formato, "proporcao": "4:5", "etapa_funil": "atracao", "objetivo": "teste", "de_onde_vem": "teste",
                "chamada": "Salve este post", "slides": slides, "roteiro": None,
                "legenda": "Organizar a semana não precisa ser complicado.\n\nSalve este post.", "hashtags": ["organizacao", "produtividade"],
                "fontes": [], "fontes_legenda_internas": [], "confirmar": [], "revisao": {"data": "2026-11-02", "veredito": "aprovar", "pontos": []},
                "status": "arte_pronta", "historico": [{"data": "2026-11-02", "evento": "arte pronta", "por": "teste"}],
                "aprovacao": None, "agendado_para": None, "publicacao": None}
        post.update(extra)
        lote = self.marca / "conteudo" / LOTE
        (lote / "posts" / f"{pid}.json").write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for i in range(1, n + 1):
            im = Image.new("RGB", (1080, 1350), (200, 200, 200))
            ImageDraw.Draw(im).rectangle([80, 80 + i * 50, 900, 300 + i * 50], fill=(90, 90, 90))
            (lote / "artes" / pid).mkdir(parents=True, exist_ok=True)
            im.save(lote / "artes" / pid / f"{i:02d}.png")

    def ler(self, pid):
        return json.loads((self.marca / "conteudo" / LOTE / "posts" / f"{pid}.json").read_text(encoding="utf-8"))

    def gravar(self, pid, post):
        (self.marca / "conteudo" / LOTE / "posts" / f"{pid}.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")

    def aprovado(self, pid, **k):
        self.criar_post(pid, **k)
        code, out, err = self.pub("aprovar", "--post", pid, "--frase", f"pode publicar {pid}", "--por", "Pessoa Teste", modo="sim")
        assert code == 0, out + err

    def csv(self, nome):
        arq = self.marca / nome
        return list(csv.DictReader(arq.open(encoding="utf-8"))) if arq.exists() else []


def agora_iso(minutos=0):
    return (datetime.now(timezone.utc).astimezone().replace(microsecond=0) + timedelta(minutes=minutos)).isoformat()


def hash_documentado(a: Ambiente, pid: str) -> str:
    """Recalcula o hash da versão como referencias/aprovacao-e-hash.md descreve (usado para forjar aprovações nos testes)."""
    p = a.ler(pid)
    excluidos = {"status", "historico", "aprovacao", "agendado_para", "publicacao", "revisao"}
    canonico = json.dumps({k: v for k, v in p.items() if k not in excluidos}, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    texto = "post:" + hashlib.sha256(canonico).hexdigest() + "\n"
    for n in range(1, len(p["slides"]) + 1):
        arte = a.marca / "conteudo" / LOTE / "artes" / pid / f"{n:02d}.png"
        texto += f"arte-{n:02d}:" + hashlib.sha256(arte.read_bytes()).hexdigest() + "\n"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def forjar_aprovacao(a: Ambiente, pid: str, **mudancas) -> None:
    """Escreve à mão uma aprovação com o hash certo e SEM assinatura: o contorno que a assinatura precisa barrar."""
    p = a.ler(pid)
    p.update(status="aprovado", agendado_para=None,
             aprovacao={"por": "Ana", "frase": f"pode publicar {pid}", "data": agora_iso(), "hash": hash_documentado(a, pid)})
    p.update(mudancas)
    a.gravar(pid, p)


REAPROVAR = "aprovação sem assinatura válida: rode `aprovar` de novo; ele abre a janela para você confirmar"


# ---------------------------------------------------------------- testes

TESTES = []


def teste(f):
    TESTES.append(f)
    return f


@teste
def assinatura_confere_com_o_exemplo_oficial_da_aws(a: Ambiente):
    chave = "AKIA" + "IOSFODNN7EXAMPLE"
    segredo = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    url = arm.url_assinada("GET", "examplebucket.s3.amazonaws.com", "/test.txt", chave, segredo, regiao="us-east-1",
                           expira=86400, quando=datetime(2013, 5, 24, tzinfo=timezone.utc))
    assert url.endswith("aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"), url


@teste
def simular_aprovar_e_hash_documentado(a: Ambiente):
    a.novo()
    a.criar_post("post-01")
    code, out, err = a.pub("simular", "--post", "post-01", rede=False)
    assert code == 0 and "PRONTO para a pessoa aprovar" in out and "#organizacao #produtividade" in out, out + err
    assert a.pub("aprovar", "--post", "post-01", "--frase", "pode publicar", "--por", "Ana", modo="sim", rede=False)[0] == 1, "frase sem o id"
    code, out, err = a.pub("aprovar", "--post", "post-01", "--frase", "pode publicar post-01", "--por", "Ana", modo="sim", rede=False)
    assert code == 0, out + err
    p = a.ler("post-01")
    assert p["aprovacao"]["hash"] == hash_documentado(a, "post-01"), "hash diferente do documentado"
    assert p["status"] == "aprovado" and p["aprovacao"]["frase"] == "pode publicar post-01"
    assert re.fullmatch(r"[0-9a-f]{64}", p["aprovacao"]["assinatura"]), "a aprovação sai assinada (HMAC-SHA256 em hexadecimal)"


@teste
def mudanca_depois_do_ok_cancela_a_aprovacao(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    p = a.ler("post-01")
    p["legenda"] += " Mais um trecho."
    a.gravar("post-01", p)
    code, out, err = a.pub("publicar", "--post", "post-01", rede=False)
    assert code == 1 and "perdeu a validade" in err
    p = a.ler("post-01")
    assert p["status"] == "arte_pronta" and p["aprovacao"] is None


@teste
def recusas_sem_tocar_na_rede(a: Ambiente):
    a.novo(credenciais=False)
    a.criar_post("post-reel", formato="reel", n=2)
    a.criar_post("post-pendente", confirmar=["NÃO VERIFICADO: dado"])
    a.criar_post("post-longo", legenda="x" * 2300)
    for pid, trecho in (("post-reel", "Reels não são publicados"), ("post-pendente", "pendência em 'confirmar'"),
                        ("post-longo", "caracteres (máximo 2200")):
        code, out, err = a.pub("simular", "--post", pid, rede=False)
        assert code == 1 and trecho in out, (pid, out)
    a.criar_post("post-ok")
    assert a.pub("publicar", "--post", "post-ok", rede=False)[0] == 1, "sem aprovação não publica"
    code, out, err = a.pub("aprovar", "--post", "post-ok", "--frase", "pode publicar post-ok", "--por", "Ana", modo="sim", rede=False)
    code, out, err = a.pub("publicar", "--post", "post-ok", rede=False)
    assert code == 1 and "ainda não está configurado" in err


@teste
def publicar_carrossel_do_comeco_ao_fim(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    code, out, err = a.pub("publicar", "--post", "post-01")
    assert code == 0 and "PUBLICADO: https://www.instagram.com/p/FAKE" in out, out + err
    assert len(F.publicados) == 1
    assert F.publicados[0]["caption"].endswith("#organizacao #produtividade")
    filhos = [c for c in F.conteineres.values() if c["dados"].get("is_carousel_item") == "true"]
    pai = next(c for c in F.conteineres.values() if c["dados"].get("media_type") == "CAROUSEL")
    assert len(filhos) == 3 and pai["dados"]["children"].split(",") == [c["id"] for c in filhos]
    assert all(c["dados"].get("alt_text") and "caption" not in c["dados"] for c in filhos)
    from PIL import Image
    for k, dados in F.puts.items():
        assert re.fullmatch(r"ig/\d{4}-\d{2}-\d{2}/post-01-[0-9a-f]{12}/0\d\.jpg", k)
        im = Image.open(io.BytesIO(dados))
        assert im.format == "JPEG" and im.size == (1080, 1350)
    assert F.objetos == {} and sorted(F.apagados) == sorted(F.puts), "as imagens precisam ser apagadas"
    assert "Mozilla" in " ".join(F.agentes) and "facebookexternalhit" in " ".join(F.agentes)
    linha = a.csv("publicacao/publicados.csv")[0]
    assert linha["post_id"] == "post-01" and linha["media_id"] == F.publicados[0]["id"] and linha["hash"] == a.ler("post-01")["aprovacao"]["hash"]
    p = a.ler("post-01")
    assert p["status"] == "publicado" and p["publicacao"]["permalink"] == F.publicados[0]["permalink"]
    assert not (a.marca / "publicacao" / "_em_andamento" / "post-01.json").exists()
    code, out, err = a.pub("publicar", "--post", "post-01")
    assert code == 1 and "já foi publicado" in err and len(F.publicados) == 1, "sem duplicata"
    assert a.pub("publicar", "--post", "post-01", "--de-novo", modo="nao")[0] == 1 and len(F.publicados) == 1, "sem a pessoa, não publica de novo"
    assert a.pub("publicar", "--post", "post-01", "--de-novo", modo="sim")[0] == 0 and len(F.publicados) == 2


@teste
def resposta_incerta_trava_e_conferir_resolve(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    F.cenario["publicar"] = "incerto_publicou_e_queda"
    code, out, err = a.pub("publicar", "--post", "post-01")
    assert code == 3 and "SEM RESPOSTA CLARA" in err, out + err
    trava = a.marca / "publicacao" / "_em_andamento" / "post-01.json"
    assert trava.is_file() and len(F.objetos) == 3
    F.cenario.pop("publicar")
    F.cenario.pop("queda_status")
    code, out, err = a.pub("publicar", "--post", "post-01")
    assert code == 1 and "conferir" in err and len(F.publicados) == 1, "a trava impede a duplicata"
    code, out, err = a.pub("conferir", "--post", "post-01")
    assert code == 0 and "FOI ao ar" in out, out + err
    assert not trava.exists() and F.objetos == {} and a.ler("post-01")["status"] == "publicado"
    assert len(a.csv("publicacao/publicados.csv")) == 1


@teste
def url_bloqueada_para_o_robo_da_meta_para_antes_do_conteiner(a: Ambiente):
    a.novo()
    a.aprovado("post-01", formato="post_unico", n=1)
    F.cenario["robo_bloqueado"] = True
    code, out, err = a.pub("publicar", "--post", "post-01")
    assert code == 1 and "não abre direito" in err and not F.conteineres and F.objetos == {}, out + err
    assert a.ler("post-01")["status"] == "erro"


@teste
def agendados_publica_o_que_venceu_e_nao_usa_rede_sem_nada(a: Ambiente):
    a.novo()
    assert a.pub("agendados", rede=False)[1].startswith("Nenhum post agendado")
    a.aprovado("post-a", n=2)
    a.aprovado("post-b", n=2)
    a.aprovado("post-c", n=2)
    for pid, minutos in (("post-a", -20), ("post-b", -300), ("post-c", 120)):
        p = a.ler(pid)
        p.update(status="agendado", agendado_para=agora_iso(minutos))
        a.gravar(pid, p)
    code, out, err = a.pub("agendados")
    assert code == 1 and "post-a: PUBLICADO" in out and "perdeu a janela" in out, out + err
    assert [a.ler(x)["status"] for x in ("post-a", "post-b", "post-c")] == ["publicado", "erro", "agendado"]
    assert len(F.publicados) == 1 and list((a.marca / "publicacao" / "logs").glob("rotina-*.log"))


@teste
def credenciais_verificar_completo_e_renovar(a: Ambiente):
    a.novo(token_dias=3)
    code, out, err = a.rodar("credenciais.py", "verificar", "--marca", "teste", "--completo")
    assert code == 0 and "RESULTADO: tudo certo." in out and "NÃO publicado" in out, out + err
    assert not F.publicados and F.objetos == {} and len(F.conteineres) == 1
    code, out, err = a.rodar("credenciais.py", "renovar", "--marca", "teste")
    assert code == 0 and TOKEN_NOVO in (a.config / "teste" / "instagram.env").read_text(encoding="utf-8")
    F.cenario["robo_bloqueado"] = True
    code, out, err = a.rodar("credenciais.py", "verificar", "--marca", "teste", "--completo")
    assert code == 1 and "facebookexternalhit: HTTP 403" in out


@teste
def metricas_gravam_csv_do_contrato_com_vazios_e_ligacao(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    assert a.pub("publicar", "--post", "post-01")[0] == 0
    novo = F.publicados[0]["id"]
    antiga = {"id": "1789" + "0" * 10 + "1", "caption": "x", "media_type": "IMAGE", "media_product_type": "FEED",
              "permalink": "https://www.instagram.com/p/OLD/", "timestamp": (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S+0000"),
              "like_count": 5, "comments_count": 2}
    F.antigas.append(antiga)
    F.insights[novo] = {"reach": 10, "saved": 1, "shares": 0, "total_interactions": 3}
    code, out, err = a.rodar("metricas.py", "coletar", "--marca", "teste")
    assert code == 0, out + err
    assert (a.marca / "metricas" / "posts.csv").read_text(encoding="utf-8").splitlines()[0] == (
        "coletado_em,media_id,post_id,publicado_em,tipo,curtidas,comentarios,alcance,salvamentos,compartilhamentos,"
        "visualizacoes,interacoes,permalink")
    linhas = {r["media_id"]: r for r in a.csv("metricas/posts.csv")}
    assert linhas[novo]["post_id"] == "post-01" and linhas[novo]["tipo"] == "carrossel" and linhas[novo]["alcance"] == "10"
    assert linhas[novo]["compartilhamentos"] == "0" and linhas[novo]["visualizacoes"] == "", "zero real fica 0; indisponível fica vazio"
    assert linhas[antiga["id"]]["post_id"] == "" and linhas[antiga["id"]]["alcance"] == ""
    assert a.csv("metricas/perfil.csv")[0]["seguidores"] == "1234"
    a.rodar("metricas.py", "coletar", "--marca", "teste")
    assert len(a.csv("metricas/perfil.csv")) == 2 and len(a.csv("metricas/posts.csv")) == 4, "cada coleta acrescenta"


@teste
def rotina_mostrar_nao_altera_nada_e_nomes_sem_acento(a: Ambiente):
    a.novo()
    code, out, err = a.rodar("rotina.py", "mostrar", "--marca", "teste", rede=False)
    nomes = ("EstudioConteudo-teste-coletar-metricas", "com.estudio-de-conteudo.teste.coletar-metricas", "estudio-de-conteudo:teste:coletar-metricas")
    assert code == 0 and "Nada foi criado" in out and any(n in out for n in nomes), out + err
    for nome in re.findall(r"^- (\S+):", out, re.M):
        assert nome.isascii(), nome


@teste
def segredos_sao_mascarados(a: Ambiente):
    import _comum
    _comum.registrar_segredos(["valor-secreto-exato-123"])
    t = _comum.mascarar("x valor-secreto-exato-123 " + TOKEN + " ?X-Amz-Signature=abcdef&X-Amz-Credential=ABC access_token=XYZ123456789")
    for proibido in ("valor-secreto-exato-123", TOKEN, "abcdef", "XYZ123456789"):
        assert proibido not in t, t


@teste
def aprovar_exige_a_confirmacao_de_uma_pessoa(a: Ambiente):
    a.novo()
    a.criar_post("post-01")
    arq = a.marca / "conteudo" / LOTE / "posts" / "post-01.json"
    antes = arq.read_bytes()
    args = ("aprovar", "--post", "post-01", "--frase", "pode publicar post-01", "--por", "Ana")
    code, out, err = a.pub(*args, modo="nao", rede=False)
    assert code == 1 and "não confirmou" in err and arq.read_bytes() == antes, "pessoa cancelou: nada pode ser gravado"
    code, out, err = a.pub(*args, modo="semtk", rede=False)
    assert code == 1 and "rode este comando você mesma, num terminal" in err and arq.read_bytes() == antes
    for digitado in ("outro-id", ""):
        code, out, err = a.pub(*args, modo="terminal", digitado=digitado, rede=False)
        assert code == 1 and arq.read_bytes() == antes, f"digitou {digitado!r}: não pode aprovar"
    code, out, err = a.pub(*args, modo="terminal", digitado="post-01", rede=False)
    assert code == 0 and "APROVADO" in out, out + err
    assert "Frase registrada" in out and "pode publicar post-01" in out, "o resumo mostrado à pessoa traz a frase"
    p = a.ler("post-01")
    assert p["status"] == "aprovado" and "confirmado pela pessoa" in p["historico"][-1]["evento"]
    for flag in ("--sim", "--yes", "--confirmar", "--sem-confirmacao"):
        code, out, err = a.pub(*args, flag, modo="sim", rede=False)
        assert code == 2, f"{flag} não pode existir: nenhuma opção pula a confirmação"


@teste
def id_do_json_com_caminho_nao_chega_ao_disco(a: Ambiente):
    a.novo()
    pasta_fora = a.projeto / "fora"
    pasta_fora.mkdir()
    isca = pasta_fora / "x.json"
    isca.write_text("{}", encoding="utf-8")
    a.criar_post("post-mal")
    p = a.ler("post-mal")
    p["id"] = "../../../../fora/x"
    a.gravar("post-mal", p)
    comandos = (("simular",), ("conferir",), ("publicar",), ("desagendar",), ("agendar", "--quando", agora_iso(120)),
                ("aprovar", "--frase", "pode publicar post-mal", "--por", "Ana"))
    for cmd in comandos:
        code, out, err = a.pub(cmd[0], "--post", "post-mal", *cmd[1:], modo="sim", rede=False)
        assert code == 1 and "campo id do JSON" in err, (cmd, out, err)
        assert isca.read_text(encoding="utf-8") == "{}", f"{cmd[0]} mexeu num arquivo fora do projeto"
    mau = a.marca / "conteudo" / LOTE / "posts" / "Post_Mau.json"
    mau.write_text("{}", encoding="utf-8")
    code, out, err = a.pub("simular", "--post", str(mau), rede=False)
    assert code == 1 and "não segue o padrão de id" in err
    code, out, err = a.pub("situacao", rede=False)
    assert "[o id do JSON difere do nome do arquivo]" in out


@teste
def chaves_da_trava_so_aceitam_o_prefixo_ig(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    pasta = a.marca / "publicacao" / "_em_andamento"
    pasta.mkdir(parents=True)
    boa = "ig/2026-11-05/post-01-abcdef123456/01.jpg"
    ruins = ["../fora/segredo.jpg", "/abs/segredo.jpg", "ig/../x/01.jpg", "outro/prefixo/01.jpg",
             "ig/2026-11-05/../../x.jpg", 42]
    F.objetos[boa] = b"x"
    (pasta / "post-01.json").write_text(json.dumps({"post_id": "post-01", "etapa": "enviando", "inicio": agora_iso(-30),
                                                    "status_anterior": "aprovado", "chaves": [*ruins, boa]}), encoding="utf-8")
    antes = len([c for c in F.chamadas if c[0] == "DELETE"])
    code, out, err = a.pub("conferir", "--post", "post-01")
    assert code == 0, out + err
    apagou = [c for c in F.chamadas if c[0] == "DELETE"][antes:]
    assert len(apagou) == 1 and apagou[0][1].endswith(boa), apagou
    assert out.count("aviso: não apaguei") == len(ruins), out


@teste
def arroba_vazia_recusa_publicar(a: Ambiente):
    a.novo()
    a.criar_post("post-01")
    visual = a.marca / "visual.json"
    senha = "pode publicar post-01"
    for conteudo in ("{}", '{"arroba": ""}', '{"arroba": "@perfil"}'):
        visual.write_text(conteudo, encoding="utf-8")
        code, out, err = a.pub("simular", "--post", "post-01", rede=False)
        assert code == 1 and "falta a 'arroba'" in out, (conteudo, out)
        assert a.pub("aprovar", "--post", "post-01", "--frase", senha, "--por", "Ana", modo="sim", rede=False)[0] == 1
    visual.write_text('{"arroba": "@marca_teste"}', encoding="utf-8")
    assert a.pub("aprovar", "--post", "post-01", "--frase", senha, "--por", "Ana", modo="sim", rede=False)[0] == 0
    visual.write_text("{}", encoding="utf-8")  # a arroba sumiu depois do ok
    code, out, err = a.pub("publicar", "--post", "post-01", rede=False)
    assert code == 1 and "arroba" in out + err and not F.puts and not F.conteineres
    code, out, err = a.rodar("credenciais.py", "verificar", "--marca", "teste")
    assert code == 1 and "não tem a 'arroba'" in out, out


@teste
def simular_so_diz_pronto_quando_aprovar_aceitaria(a: Ambiente):
    a.novo()
    a.criar_post("post-01", status="texto_aprovado")
    args = ("--post", "post-01")
    code, out, err = a.pub("simular", *args, rede=False)
    assert code == 1 and "AINDA NÃO DÁ PARA APROVAR" in out and "arte_pronta" in out, out
    assert "PRONTO para a pessoa aprovar" not in out
    code, out, err = a.pub("aprovar", *args, "--frase", "pode publicar post-01", "--por", "Ana", modo="sim", rede=False)
    assert code == 1 and "arte_pronta" in err
    p = a.ler("post-01")
    p["status"] = "arte_pronta"
    a.gravar("post-01", p)
    code, out, err = a.pub("simular", *args, rede=False)
    assert code == 0 and "PRONTO para a pessoa aprovar" in out
    assert a.pub("aprovar", *args, "--frase", "pode publicar post-01", "--por", "Ana", modo="sim", rede=False)[0] == 0
    code, out, err = a.pub("simular", *args, rede=False)
    assert code == 0 and "JÁ APROVADO nesta versão" in out and "PRONTO para a pessoa aprovar" not in out


@teste
def json_quebrado_vira_mensagem_clara_sem_traceback(a: Ambiente):
    a.novo()
    a.criar_post("post-01")
    arq = a.marca / "conteudo" / LOTE / "posts" / "post-01.json"
    arq.write_text(arq.read_text(encoding="utf-8").rstrip().rstrip("}").rstrip() + ",\n}\n", encoding="utf-8")
    for cmd in (("simular",), ("conferir",), ("publicar",), ("desagendar",), ("agendar", "--quando", agora_iso(120)),
                ("aprovar", "--frase", "pode publicar post-01", "--por", "Ana")):
        code, out, err = a.pub(cmd[0], "--post", "post-01", *cmd[1:], modo="sim", rede=False)
        assert code == 1 and "não é um JSON válido" in err and "linha" in err and "coluna" in err, (cmd, err)
    code, out, err = a.pub("situacao", rede=False)
    assert code == 0 and "ilegível" in out


@teste
def csv_do_excel_e_colunas_extras_nao_perdem_historico(a: Ambiente):
    a.novo()
    pasta = a.marca / "metricas"
    pasta.mkdir()
    cabecalho = ("Coletado_Em;Media_Id;Post_Id;Publicado_Em;Tipo;Curtidas;Comentarios;Alcance;Salvamentos;"
                 "Compartilhamentos;Visualizacoes;Interacoes;Permalink;Nota")
    linha = ("2026-10-01T10:00:00-03:00;1789000000001;;2026-09-30T10:00:00-03:00;post_unico;5;1;100;2;1;300;9;"
             "https://www.instagram.com/p/OLD/;minha nota")
    original = ("﻿" + cabecalho + "\r\n" + linha).encode("utf-8")  # BOM, separador ';', CRLF e sem quebra no fim
    (pasta / "posts.csv").write_bytes(original)
    (pasta / "perfil.csv").write_text("coletado_em,seguidores,seguindo,publicacoes,nota\n2026-10-01T10:00:00-03:00,1000,10,5,ok\n",
                                      encoding="utf-8")
    F.antigas.append({"id": "1789" + "0" * 10 + "2", "caption": "x", "media_type": "IMAGE", "media_product_type": "FEED",
                      "permalink": "https://www.instagram.com/p/NOVA/", "like_count": 4, "comments_count": 0,
                      "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+0000")})
    code, out, err = a.rodar("metricas.py", "coletar", "--marca", "teste")
    assert code == 0 and "ajustei o formato de posts.csv" in out, out + err
    posts = a.csv("metricas/posts.csv")
    assert len(posts) == 2 and posts[0]["media_id"] == "1789000000001" and posts[0]["alcance"] == "100", posts
    assert posts[0]["nota"] == "minha nota" and posts[1]["nota"] == "" and posts[1]["media_id"].endswith("2")
    primeira = (pasta / "posts.csv").read_text(encoding="utf-8").splitlines()[0]
    assert primeira.startswith("coletado_em,media_id,post_id,") and primeira.endswith(",permalink,nota")
    guardados = list(pasta.glob("_antes-formato-csv-*/posts.csv"))
    assert len(guardados) == 1 and guardados[0].read_bytes() == original, "a versão anterior fica guardada intacta"
    assert not list(pasta.glob("_antes-cabecalho-*")), "coluna extra não é motivo para mover o histórico"
    perfil = a.csv("metricas/perfil.csv")
    assert len(perfil) == 2 and perfil[0]["nota"] == "ok" and perfil[1]["nota"] == "" and perfil[1]["seguidores"] == "1234"
    assert not list(pasta.glob("_antes-formato-csv-*/perfil.csv")), "perfil.csv já estava certo: não precisa reescrever"
    # publicados.csv salvo pelo Excel (';' e maiúsculas) ainda barra a duplicata e é normalizado ao receber outro post
    publicacao = a.marca / "publicacao"
    publicacao.mkdir(exist_ok=True)
    (publicacao / "publicados.csv").write_text("Publicado_Em;Post_Id;Lote;Formato;Media_Id;Permalink;Hash\n"
                                               f"2026-10-01T10:00:00-03:00;post-02;{LOTE};carrossel;1789000000009;"
                                               "https://www.instagram.com/p/OLD2/;h\n", encoding="utf-8")
    a.aprovado("post-02")
    code, out, err = a.pub("publicar", "--post", "post-02", rede=False)
    assert code == 1 and "já foi publicado" in err, out + err
    a.aprovado("post-03")
    assert a.pub("publicar", "--post", "post-03")[0] == 0
    linhas = a.csv("publicacao/publicados.csv")
    assert [l["post_id"] for l in linhas] == ["post-02", "post-03"], linhas
    assert (publicacao / "publicados.csv").read_text(encoding="utf-8").startswith("publicado_em,post_id,")


@teste
def agendados_pula_post_desagendado_depois_de_pegar_a_trava(a: Ambiente):
    a.novo()
    a.aprovado("post-a", n=2)
    a.aprovado("post-b", n=2)
    for pid in ("post-a", "post-b"):
        p = a.ler(pid)
        p.update(status="agendado", agendado_para=agora_iso(-5))
        a.gravar(pid, p)
    arq_b = a.marca / "conteudo" / LOTE / "posts" / "post-b.json"
    desagendar = (f"ar = Path({str(arq_b)!r}); d = json.loads(ar.read_text(encoding='utf-8')); d['status'] = 'aprovado'; "
                  "d['agendado_para'] = None; ar.write_text(json.dumps(d), encoding='utf-8')")
    code, out, err = a.pub("agendados", ganchos={"tomar_trava_execucao": desagendar})
    assert code == 0 and "post-b: deixou de estar agendado" in out, out + err
    assert a.ler("post-a")["status"] == "publicado" and a.ler("post-b")["status"] == "aprovado"
    assert len(F.publicados) == 1, "o post desagendado não pode ser publicado"


@teste
def publicado_por_outra_execucao_depois_da_trava_nao_duplica(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    outra = ("publicar.registrar_publicado('teste', {'publicado_em': '2026-11-05T10:00:00-03:00', 'post_id': 'post-01', "
             "'lote': 'l', 'formato': 'carrossel', 'media_id': '1', 'permalink': 'https://x.y/', 'hash': 'h'})")
    code, out, err = a.pub("publicar", "--post", "post-01", ganchos={"criar_trava": outra})
    assert code == 1 and "publicado por outra execução" in err, out + err
    assert not F.puts and not F.conteineres and not F.publicados
    assert not (a.marca / "publicacao" / "_em_andamento" / "post-01.json").exists(), "a trava precisa ser solta"
    assert a.ler("post-01")["status"] == "aprovado"


@teste
def conferir_com_confirmo_tambem_exige_uma_pessoa(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    pasta = a.marca / "publicacao" / "_em_andamento"
    pasta.mkdir(parents=True)
    trava = pasta / "post-01.json"
    F.conteineres["99999"] = {"id": "99999", "dados": {}, "estado": "EXPIRED"}
    trava.write_text(json.dumps({"post_id": "post-01", "etapa": "publicando", "creation_id": "99999", "inicio": agora_iso(-30),
                                 "status_anterior": "aprovado", "chaves": []}), encoding="utf-8")
    code, out, err = a.pub("conferir", "--post", "post-01")
    assert code == 3 and "Não consegui provar" in out and trava.is_file()
    code, out, err = a.pub("conferir", "--post", "post-01", "--confirmo-que-nao-foi-ao-ar", modo="nao")
    assert code == 3 and trava.is_file(), "sem a pessoa, a trava continua"
    code, out, err = a.pub("conferir", "--post", "post-01", "--confirmo-que-nao-foi-ao-ar", modo="semtk")
    assert code == 1 and "num terminal" in err and trava.is_file()
    code, out, err = a.pub("conferir", "--post", "post-01", "--confirmo-que-nao-foi-ao-ar", modo="sim")
    assert code == 0 and not trava.exists() and a.ler("post-01")["status"] == "aprovado"


@teste
def validade_vazia_avisa_e_a_rotina_descobre_a_data(a: Ambiente):
    a.novo()
    env = a.config / "teste" / "instagram.env"
    texto = env.read_text(encoding="utf-8")
    env.write_text("\n".join("IG_TOKEN_VALIDO_ATE=" if l.startswith("IG_TOKEN_VALIDO_ATE") else l for l in texto.splitlines()) + "\n",
                   encoding="utf-8")
    code, out, err = a.rodar("credenciais.py", "verificar", "--marca", "teste")
    assert "não tem a data de validade" in out, out
    code, out, err = a.rodar("metricas.py", "coletar", "--marca", "teste")
    assert code == 0 and "validade do token descoberta" in out, out + err
    depois = env.read_text(encoding="utf-8")
    assert TOKEN_NOVO in depois and f"IG_TOKEN_VALIDO_ATE={date.today() + timedelta(days=59)}" in depois, depois.replace(TOKEN_NOVO, "***")


@teste
def raiz_aponta_para_outro_projeto(a: Ambiente):
    a.novo()
    a.criar_post("post-01")
    env = a._env()
    base = [sys.executable, "-X", "utf8"]
    code, out, err = a._correr(base + [str(AQUI / "publicar.py"), "situacao", "--raiz", str(a.projeto), "--marca", "teste"], "situacao --raiz", env, True)
    assert code == 0 and "post-01 | arte_pronta" in out, out + err
    code, out, err = a._correr(base + [str(AQUI / "publicar.py"), "--raiz", str(a.projeto), "simular", "--post", "post-01", "--marca", "teste"],
                               "simular --raiz", env, False)
    assert code == 0 and "PRONTO para a pessoa aprovar" in out, out + err
    code, out, err = a._correr(base + [str(AQUI / "rotina.py"), "mostrar", "--raiz", str(a.projeto), "--marca", "teste"], "rotina --raiz", env, False)
    assert code == 0 and "--raiz" in out and str(Path(a.projeto).resolve()) in out, out
    code, out, err = a._correr(base + [str(AQUI / "metricas.py"), "coletar", "--simular", "--raiz", str(a.projeto), "--marca", "teste"],
                               "metricas --raiz", env, True)
    assert code == 0 and "nenhum arquivo foi gravado" in out, out + err
    code, out, err = a._correr(base + [str(AQUI / "credenciais.py"), "verificar", "--raiz", str(a.projeto), "--marca", "teste"],
                               "credenciais --raiz", env, True)
    assert code == 0, out + err
    code, out, err = a._correr(base + [str(AQUI / "publicar.py"), "situacao", "--raiz", str(a.base / "nao-existe")], "raiz errada", env, False)
    assert code == 1 and "a pasta não existe" in err


@teste
def rotina_aspas_tipograficas_e_erros_do_powershell(a: Ambiente):
    import rotina
    for c in "'‘’‚‛":
        assert rotina.ps("a" + c + "b") == "'a" + c + c + "b'", repr(c)
    if os.name != "nt":
        return
    caminho = "C:" + chr(92) + "Users" + chr(92) + "Zé ‘a’ ‚b‛ O’Brien" + chr(92) + "pythonw.exe"
    seco = rotina.script_windows("teste", caminho, registrar=False)
    r = rotina.powershell(seco + "Write-Output ('Execute=' + (($acao.Execute.ToCharArray() | ForEach-Object { [int]$_ }) -join ','))")
    assert r.returncode == 0, r.stderr
    assert "Execute=" + ",".join(str(ord(ch)) for ch in caminho) in r.stdout, "o caminho precisa chegar igual ao PowerShell"
    r = rotina.powershell("throw 'falha de teste: ação'")
    assert r.returncode == 1 and "falha de teste: ação" in r.stderr, (r.returncode, r.stderr)
    assert "CLIXML" not in r.stderr + r.stdout


DRIVER_ROTINA = """
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["AUTOTESTE_SCRIPTS"])
import rotina
rotina.sistema = lambda: "linux"
def sem_programa(*a, **k):
    raise FileNotFoundError(2, "No such file or directory", "crontab")
rotina.processo = sem_programa
sys.argv = ["rotina.py"] + sys.argv[1:]
rotina.executar(rotina.main)
"""


@teste
def rotina_sem_crontab_explica_o_que_fazer(a: Ambiente):
    a.novo()
    env = a._env(AUTOTESTE_SCRIPTS=str(a.scripts))
    for comando, codigo_esperado in (("mostrar", 0), ("instalar", 1), ("remover", 1)):
        code, out, err = a._correr([sys.executable, "-X", "utf8", "-c", DRIVER_ROTINA, comando, "--marca", "teste"],
                                   f"rotina {comando} sem crontab", env, False)
        assert code == codigo_esperado and "crontab" in out + err and "WSL" in out + err, (comando, code, out, err)


@teste
def aprovacao_forjada_sem_assinatura_e_recusada(a: Ambiente):
    a.novo()
    a.criar_post("post-01")
    arq = a.marca / "conteudo" / LOTE / "posts" / "post-01.json"
    chave = a.config / "teste" / "aprovacao.key"
    # 1) Ninguém aprovou ainda neste computador (não existe chave): hash certo, status 'aprovado' e nenhuma assinatura.
    forjar_aprovacao(a, "post-01")
    assert not chave.exists()
    antes = arq.read_bytes()
    code, out, err = a.pub("simular", "--post", "post-01", rede=False)
    assert code == 0 and "JÁ APROVADO" not in out and "assinatura INVÁLIDA" in out and REAPROVAR in out, out
    assert "PRONTO para a pessoa aprovar" in out, "o caminho certo continua aberto: aprovar de novo, na janela"
    code, out, err = a.pub("agendar", "--post", "post-01", "--quando", agora_iso(120), rede=False)
    assert code == 1 and REAPROVAR in err, err
    code, out, err = a.pub("publicar", "--post", "post-01", rede=False)
    assert code == 1 and REAPROVAR in err and not F.puts and not F.conteineres and not F.publicados, err
    assert arq.read_bytes() == antes, "sem a chave não dá para provar nada: o arquivo não é alterado"
    assert "post-01 | aprovado [aprovação sem assinatura válida" in a.pub("situacao", rede=False)[1]
    # 2) A rotina também não publica um agendamento forjado.
    forjar_aprovacao(a, "post-01", status="agendado", agendado_para=agora_iso(-5))
    code, out, err = a.pub("agendados", "--simular", rede=False)
    assert "NÃO seria publicado" in out and REAPROVAR in out, out
    code, out, err = a.pub("agendados")
    assert code == 1 and "não publicado" in out and not F.publicados and not F.puts and not F.conteineres, out + err
    # 3) Com uma chave já existente (alguém aprovou outro post de verdade), o forjado cai de vez.
    a.aprovado("post-02")
    assert chave.is_file()
    forjar_aprovacao(a, "post-01")
    code, out, err = a.pub("publicar", "--post", "post-01", rede=False)
    assert code == 1 and REAPROVAR in err and "voltou para 'arte_pronta'" in err and not F.puts, err
    p = a.ler("post-01")
    assert p["status"] == "arte_pronta" and p["aprovacao"] is None and "sem assinatura válida" in p["historico"][-1]["evento"]
    # 4) Assinatura inventada, do tamanho certo: também não vale.
    forjar_aprovacao(a, "post-01")
    p = a.ler("post-01")
    p["aprovacao"]["assinatura"] = "0" * 64
    a.gravar("post-01", p)
    code, out, err = a.pub("agendar", "--post", "post-01", "--quando", agora_iso(120), rede=False)
    assert code == 1 and REAPROVAR in err and "a assinatura não confere" in err, err
    # 5) O caminho legítimo continua funcionando: aprovar de novo, com a pessoa na janela, e publicar.
    assert a.pub("aprovar", "--post", "post-01", "--frase", "pode publicar post-01", "--por", "Ana", modo="sim")[0] == 0
    assert a.pub("publicar", "--post", "post-01")[0] == 0 and len(F.publicados) == 1


@teste
def assinatura_de_outra_versao_ou_de_outro_registro_e_recusada(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    p = a.ler("post-01")
    assert p["status"] == "aprovado" and p["aprovacao"]["assinatura"]
    # Versão 2: o texto muda e alguém escreve o hash novo à mão, aproveitando a assinatura da versão 1.
    p["legenda"] += " Mais um trecho."
    a.gravar("post-01", p)
    p["aprovacao"]["hash"] = hash_documentado(a, "post-01")
    a.gravar("post-01", p)
    code, out, err = a.pub("publicar", "--post", "post-01", rede=False)
    assert code == 1 and REAPROVAR in err and "a assinatura não confere" in err and not F.puts, err
    assert a.ler("post-01")["status"] == "arte_pronta"
    # Mexer em qualquer campo assinado de uma aprovação legítima também a derruba.
    for campo, novo in (("por", "Outra Pessoa"), ("frase", "pode publicar post-02, e todos os outros"), ("data", "2020-01-01T10:00:00-03:00")):
        a.aprovado("post-02")
        q = a.ler("post-02")
        q["aprovacao"][campo] = novo
        a.gravar("post-02", q)
        code, out, err = a.pub("agendar", "--post", "post-02", "--quando", agora_iso(120), rede=False)
        assert code == 1 and "a assinatura não confere" in err, (campo, err)
    # A assinatura de um post não serve a outro: o id entra na conta (e nenhum campo "vaza" para o vizinho).
    import _assinatura as assin
    chave = bytes(range(32))
    base = {"hash": "h", "frase": "pode publicar x", "data": "2026-11-05", "por": "Ana"}
    referencia = assin.assinar(chave, "post-a", base)
    assert assin.assinar(chave, "post-a", dict(base)) == referencia, "a assinatura é determinística"
    assert assin.assinar(chave, "post-b", base) != referencia
    assert assin.assinar(bytes(range(1, 33)), "post-a", base) != referencia
    for campo in base:
        assert assin.assinar(chave, "post-a", {**base, campo: base[campo] + "x"}) != referencia, campo
    assert assin.assinar(chave, "post-a", {**base, "frase": "ab", "data": "c"}) != assin.assinar(chave, "post-a", {**base, "frase": "a", "data": "bc"})


@teste
def chave_de_aprovacao_fica_fora_do_projeto_e_perde_o_efeito_se_sumir(a: Ambiente):
    a.novo()
    a.aprovado("post-01")
    chave = a.config / "teste" / "aprovacao.key"
    texto = chave.read_text(encoding="ascii").strip()
    assert re.fullmatch(r"[0-9a-f]{64}", texto), "32 bytes aleatórios, em hexadecimal"
    if os.name != "nt":
        assert stat.S_IMODE(chave.stat().st_mode) == 0o600
    assert a.projeto not in chave.parents
    for arquivo in a.projeto.rglob("*"):
        if arquivo.is_file():
            assert texto.encode("ascii") not in arquivo.read_bytes(), f"a chave apareceu dentro do projeto: {arquivo}"
    a.aprovado("post-02")
    assert chave.read_text(encoding="ascii").strip() == texto, "a chave é criada uma vez e reaproveitada"
    # Computador novo (a chave não veio junto): as aprovações antigas perdem a validade, sem alterar nenhum arquivo.
    chave.unlink()
    arq1 = a.marca / "conteudo" / LOTE / "posts" / "post-01.json"
    antes = arq1.read_bytes()
    code, out, err = a.pub("simular", "--post", "post-01", rede=False)
    assert "JÁ APROVADO" not in out and "ainda não tem a chave de aprovação" in out and REAPROVAR in out, out
    code, out, err = a.pub("publicar", "--post", "post-01", rede=False)
    assert code == 1 and REAPROVAR in err and arq1.read_bytes() == antes and not chave.exists()
    # A pessoa aprova de novo: nasce uma chave nova; a aprovação feita com a antiga não vale mais.
    code, out, err = a.pub("aprovar", "--post", "post-01", "--frase", "pode publicar post-01", "--por", "Ana", modo="sim", rede=False)
    assert code == 0 and "Criei a chave de aprovação" in out, out + err
    novo = chave.read_text(encoding="ascii").strip()
    assert re.fullmatch(r"[0-9a-f]{64}", novo) and novo != texto
    code, out, err = a.pub("publicar", "--post", "post-02", rede=False)
    assert code == 1 and "a assinatura não confere" in err and a.ler("post-02")["status"] == "arte_pronta", err
    assert a.pub("publicar", "--post", "post-01")[0] == 0
    # Post agendado cuja aprovação perdeu a validade: aprovar de novo basta, sem 'desagendar' antes.
    a.aprovado("post-03")
    p = a.ler("post-03")
    p.update(status="agendado", agendado_para=agora_iso(60))
    a.gravar("post-03", p)
    chave.unlink()
    code, out, err = a.pub("simular", "--post", "post-03", rede=False)
    assert code == 0 and "PRONTO para a pessoa aprovar" in out and "JÁ APROVADO" not in out, out
    code, out, err = a.pub("aprovar", "--post", "post-03", "--frase", "pode publicar post-03", "--por", "Ana", modo="sim", rede=False)
    assert code == 0 and a.ler("post-03")["status"] == "aprovado" and a.ler("post-03")["agendado_para"] is None, out + err
    # Chave com defeito: fica guardada de lado (nada se apaga) e uma nova assume.
    chave.write_text("isto não é uma chave", encoding="utf-8")
    a.criar_post("post-04")
    code, out, err = a.pub("aprovar", "--post", "post-04", "--frase", "pode publicar post-04", "--por", "Ana", modo="sim", rede=False)
    assert code == 0 and "Troquei a chave de aprovação" in out, out + err
    assert list(chave.parent.glob("aprovacao.key.defeituosa-*")) and re.fullmatch(r"[0-9a-f]{64}", chave.read_text(encoding="ascii").strip())


@teste
def primeiras_aprovacoes_ao_mesmo_tempo_ficam_com_uma_chave_so(a: Ambiente):
    a.novo()
    codigo = ("import os, sys; sys.dont_write_bytecode = True; sys.path.insert(0, os.environ['AUTOTESTE_SCRIPTS']); "
              "import _assinatura as s; chave, situacao = s.chave_ou_criar('teste'); print(situacao, chave.hex())")
    env = a._env(AUTOTESTE_SCRIPTS=str(a.scripts))
    processos = [subprocess.Popen([sys.executable, "-X", "utf8", "-c", codigo], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, encoding="utf-8") for _ in range(6)]
    saidas = [p.communicate(timeout=120) for p in processos]
    assert all(p.returncode == 0 for p in processos), saidas
    pares = [s[0].split() for s in saidas]
    assert len({chave for _, chave in pares}) == 1, "todas as execuções precisam usar a mesma chave"
    assert [situacao for situacao, _ in pares].count("criada") == 1, pares
    assert (a.config / "teste" / "aprovacao.key").read_text(encoding="ascii").strip() == pares[0][1]
    # Arquivo vazio = outra execução está no meio de criar a chave: espera por ela em vez de trocar o arquivo.
    codigo = ("import os, sys, threading, time; sys.dont_write_bytecode = True; sys.path.insert(0, os.environ['AUTOTESTE_SCRIPTS']); "
              "import _assinatura as s; arq = s.arquivo_chave('teste'); arq.unlink(); arq.write_text('')\n"
              "def escrever():\n    time.sleep(0.6); arq.write_text('ab' * 32 + chr(10))\n"
              "threading.Thread(target=escrever).start(); chave, situacao = s.chave_ou_criar('teste'); print(situacao, chave.hex())")
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo], env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0 and r.stdout.split() == ["existente", "ab" * 32], (r.stdout, r.stderr)
    assert not list((a.config / "teste").glob("aprovacao.key.defeituosa-*")), "o arquivo da outra execução não pode ser trocado"


@teste
def conferir_nao_devolve_nem_registra_aprovacao_sem_assinatura(a: Ambiente):
    a.novo()
    a.aprovado("post-ok")  # cria a chave deste computador
    a.criar_post("post-01")
    forjar_aprovacao(a, "post-01", status="erro")
    pasta = a.marca / "publicacao" / "_em_andamento"
    pasta.mkdir(parents=True)
    trava = pasta / "post-01.json"
    trava.write_text(json.dumps({"post_id": "post-01", "etapa": "preparando", "inicio": agora_iso(-30),
                                 "status_anterior": "aprovado", "chaves": []}), encoding="utf-8")
    code, out, err = a.pub("conferir", "--post", "post-01")
    assert code == 0 and "NÃO foi ao ar" in out and REAPROVAR in out, out + err
    p = a.ler("post-01")
    assert p["status"] == "arte_pronta" and p["aprovacao"] is None and not trava.exists(), "o forjado não volta para 'aprovado'"
    # Post que foi mesmo ao ar: o conferir registra o link, mas não grava um hash que ninguém assinou.
    a.aprovado("post-02")
    F.cenario["publicar"] = "incerto_publicou_e_queda"
    assert a.pub("publicar", "--post", "post-02")[0] == 3
    F.cenario.pop("publicar")
    F.cenario.pop("queda_status")
    q = a.ler("post-02")
    q["aprovacao"].pop("assinatura")
    a.gravar("post-02", q)
    code, out, err = a.pub("conferir", "--post", "post-02")
    assert code == 0 and "FOI ao ar" in out, out + err
    linha = a.csv("publicacao/publicados.csv")[0]
    assert linha["post_id"] == "post-02" and linha["hash"] == "" and a.ler("post-02")["status"] == "publicado"


def main() -> int:
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    if filtro in ("-h", "--help"):
        print(__doc__)
        return 0
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    ok = falhas = 0
    with tempfile.TemporaryDirectory(prefix="autoteste-estudio-", ignore_cleanup_errors=True) as tmp:
        ambiente = Ambiente(Path(tmp), servidor.server_address[1])
        for t in TESTES:
            if filtro and filtro not in t.__name__:
                continue
            inicio = time.time()
            try:
                t(ambiente)
                print(f"  OK     {t.__name__} ({time.time() - inicio:.0f} s)")
                ok += 1
            except Exception:
                falhas += 1
                print(f"  FALHOU {t.__name__}")
                traceback.print_exc(limit=4)
    servidor.shutdown()
    print(f"\n{ok} passaram, {falhas} falharam. Nenhuma chamada saiu deste computador.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
