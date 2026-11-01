"""Armazenamento temporário das imagens, compatível com S3 (Cloudflare R2, entre outros).

A Meta só publica uma imagem que ela consiga baixar por uma URL pública. Este módulo sobe o JPEG com
uma URL pré-assinada (AWS Signature V4, só com a biblioteca padrão), confere a URL pública como
navegador e como o robô de prévia da Meta, e apaga o objeto depois.
Detalhes e fontes: docs/armazenamento-imagens.md. Não é um script para rodar; é importado pelos outros.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from _comum import Recusa, ler_env, mascarar, pasta_config

CAMPOS = ("ARMAZENAMENTO_ENDPOINT", "ARMAZENAMENTO_REGIAO", "ARMAZENAMENTO_BUCKET",
          "ARMAZENAMENTO_CHAVE_ID", "ARMAZENAMENTO_CHAVE_SECRETA", "ARMAZENAMENTO_URL_PUBLICA")
HOSTS_LOCAIS = ("127.0.0.1", "localhost", "::1")
BUCKET_RE = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")
# Só chaves que o próprio script cria: prefixo ig/, sem '..', sem barra inicial, sem caminho absoluto.
CHAVE_RE = re.compile(r"ig/[A-Za-z0-9][A-Za-z0-9._-]{0,120}(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,120}){1,3}")


def chave_valida(chave) -> bool:
    return isinstance(chave, str) and len(chave) <= 400 and CHAVE_RE.fullmatch(chave) is not None


AGENTE_NAVEGADOR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
AGENTE_META = "facebookexternalhit/1.1"
LIMITE_JPEG = 8 * 1024 * 1024
TEMPO_LEITURA = 20
TENTATIVAS_URL = 3
PAUSAS_URL = (2, 5)
CABECALHOS_OBJETO = {"Content-Type": "image/jpeg", "Cache-Control": "no-store"}


def arquivo_env(marca: str) -> Path:
    return pasta_config(marca) / "armazenamento.env"


def problemas_config(cfg: dict) -> list[str]:
    """Confere o formato dos seis campos. Não mostra valores secretos."""
    faltando = [c for c in CAMPOS if not cfg.get(c)]
    if faltando:
        return [f"falta preencher {', '.join(faltando)}"]
    problemas = []
    for campo, nome in (("ARMAZENAMENTO_ENDPOINT", "o endereço do armazenamento"),
                        ("ARMAZENAMENTO_URL_PUBLICA", "a URL pública")):
        p = urllib.parse.urlsplit(cfg[campo])
        local = p.scheme == "http" and p.hostname in HOSTS_LOCAIS
        if not (p.hostname and (p.scheme == "https" or local)):
            problemas.append(f"{nome} precisa começar com https://")
        elif p.username or p.password or p.query or p.fragment:
            problemas.append(f"{nome} não pode ter usuário, senha, '?' nem '#'")
        elif campo == "ARMAZENAMENTO_ENDPOINT" and p.path not in ("", "/"):
            problemas.append("o endereço do armazenamento deve ser só o domínio (sem pasta no final)")
        elif not cfg[campo].isascii():
            problemas.append(f"{nome} deve usar só caracteres ASCII (a Meta recomenda; troque o domínio por sua forma com 'xn--')")
    if not BUCKET_RE.fullmatch(cfg["ARMAZENAMENTO_BUCKET"]):
        problemas.append("o nome do bucket deve ter de 3 a 63 caracteres: minúsculas, números, hífen e ponto")
    if not re.fullmatch(r"[a-z0-9-]{3,40}", cfg["ARMAZENAMENTO_REGIAO"]):
        problemas.append("a região deve ser como 'auto' (Cloudflare R2) ou 'us-east-1' (S3)")
    return problemas


class Armazenamento:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.endpoint = urllib.parse.urlsplit(cfg["ARMAZENAMENTO_ENDPOINT"].rstrip("/"))
        self.bucket = cfg["ARMAZENAMENTO_BUCKET"]
        self.regiao = cfg["ARMAZENAMENTO_REGIAO"]
        self.base_publica = cfg["ARMAZENAMENTO_URL_PUBLICA"].rstrip("/")

    @classmethod
    def carregar(cls, marca: str) -> "Armazenamento":
        arq = arquivo_env(marca)
        if not arq.is_file():
            raise Recusa(f"o armazenamento de imagens não está configurado. Rode: "
                         f"python -X utf8 skills/publicar-instagram/scripts/credenciais.py configurar --marca {marca}")
        cfg = ler_env(arq)
        problemas = problemas_config(cfg)
        if problemas:
            raise Recusa("armazenamento com problema: " + "; ".join(problemas) +
                         f". Corrija com: python -X utf8 skills/publicar-instagram/scripts/credenciais.py "
                         f"configurar --marca {marca}")
        return cls(cfg)

    def chave_nova(self, post_id: str, nome: str) -> str:
        """Caminho do objeto: nunca reaproveitado e difícil de adivinhar (o bucket é público por URL)."""
        return f"ig/{datetime.now(timezone.utc):%Y-%m-%d}/{post_id}-{secrets.token_hex(6)}/{nome}"

    def url_publica(self, chave: str) -> str:
        return f"{self.base_publica}/{chave}"

    def _requisicao(self, metodo: str, chave: str, corpo: bytes | None = None, cabecalhos: dict | None = None):
        host = self.endpoint.netloc
        url = url_assinada(metodo, host, f"/{self.bucket}/{chave}", self.cfg["ARMAZENAMENTO_CHAVE_ID"],
                           self.cfg["ARMAZENAMENTO_CHAVE_SECRETA"], regiao=self.regiao, cabecalhos=cabecalhos,
                           esquema=self.endpoint.scheme)
        return urllib.request.Request(url, data=corpo, method=metodo, headers=cabecalhos or {})

    def _executar(self, req, metodo: str, chave: str) -> int:
        from _instagram import abridor_para
        try:
            with abridor_para(req.full_url).open(req, timeout=120) as r:
                return r.status
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"o armazenamento respondeu {e.code} em {metodo} {chave}: "
                               f"{explicar_erro(e.code, e.read().decode('utf-8', 'replace'))}") from None
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            raise RuntimeError(f"não consegui falar com o armazenamento ({type(e).__name__}: "
                               f"{mascarar(getattr(e, 'reason', e))})") from None

    def enviar_jpeg(self, dados: bytes, chave: str) -> str:
        if not chave_valida(chave):
            raise ValueError("chave de objeto inválida (só valem chaves que começam com ig/, sem '..')")
        if dados[:3] != b"\xff\xd8\xff":
            raise ValueError("o arquivo a enviar não é JPEG")
        if len(dados) > LIMITE_JPEG:
            raise ValueError("o JPEG passa de 8 MB")
        self._executar(self._requisicao("PUT", chave, dados, dict(CABECALHOS_OBJETO)), "PUT", chave)
        return self.url_publica(chave)

    def apagar(self, chave: str) -> None:
        if not chave_valida(chave):
            raise RuntimeError(f"a chave '{mascarar(str(chave))[:60]}' não é uma chave deste script (só apago chaves "
                               "ig/... sem '..'), então não apaguei")
        self._executar(self._requisicao("DELETE", chave), "DELETE", chave)

    def status_publico(self, url: str) -> int | None:
        from _instagram import abridor_para
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": AGENTE_NAVEGADOR})
            with abridor_para(url).open(req, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except (urllib.error.URLError, OSError, http.client.HTTPException):
            return None


# ---------------------------------------------------------------- assinatura SigV4 (URL pré-assinada)

def _hmac(chave: bytes, texto: str) -> bytes:
    return hmac.new(chave, texto.encode("utf-8"), hashlib.sha256).digest()


def _q(texto: str, seguro: str = "-_.~") -> str:
    return urllib.parse.quote(texto, safe=seguro)


def url_assinada(metodo: str, host: str, caminho: str, chave_id: str, segredo: str, regiao: str = "auto",
                 expira: int = 600, cabecalhos: dict | None = None, quando: datetime | None = None,
                 esquema: str = "https") -> str:
    """URL pré-assinada AWS SigV4 (assinatura na query string, payload 'UNSIGNED-PAYLOAD').

    Os cabeçalhos assinados precisam ir iguais na requisição, ou o armazenamento responde 403.
    """
    quando = quando or datetime.now(timezone.utc)
    amz_data = quando.strftime("%Y%m%dT%H%M%SZ")
    dia = quando.strftime("%Y%m%d")
    escopo = f"{dia}/{regiao}/s3/aws4_request"
    cab = {k.lower(): " ".join(str(v).split()) for k, v in (cabecalhos or {}).items()}
    cab["host"] = host
    assinados = ";".join(sorted(cab))
    params = {"X-Amz-Algorithm": "AWS4-HMAC-SHA256", "X-Amz-Credential": f"{chave_id}/{escopo}",
              "X-Amz-Date": amz_data, "X-Amz-Expires": str(expira), "X-Amz-SignedHeaders": assinados}
    consulta = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(params.items()))
    uri = _q(caminho, seguro="/-_.~")
    canonica = "\n".join([metodo, uri, consulta, "".join(f"{k}:{cab[k]}\n" for k in sorted(cab)), assinados,
                          "UNSIGNED-PAYLOAD"])
    a_assinar = "\n".join(["AWS4-HMAC-SHA256", amz_data, escopo, hashlib.sha256(canonica.encode("utf-8")).hexdigest()])
    chave = _hmac(_hmac(_hmac(_hmac(("AWS4" + segredo).encode("utf-8"), dia), regiao), "s3"), "aws4_request")
    assinatura = hmac.new(chave, a_assinar.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{esquema}://{host}{uri}?{consulta}&X-Amz-Signature={assinatura}"


def explicar_erro(status: int, corpo: str) -> str:
    codigo = re.search(r"<Code>([^<]+)</Code>", corpo)
    codigo = codigo.group(1) if codigo else ""
    dicas = {"SignatureDoesNotMatch": "a assinatura não confere: confira a chave secreta, a região e o relógio do computador",
             "InvalidAccessKeyId": "a chave de acesso (Access Key ID) não existe",
             "AccessDenied": "a chave não tem permissão neste bucket (precisa de 'Object Read & Write' nele)",
             "NoSuchBucket": "o bucket não existe: confira o nome e o endereço",
             "RequestTimeTooSkewed": "o relógio do computador está errado"}
    return dicas.get(codigo) or (f"erro {codigo}" if codigo else "sem detalhe")


# ---------------------------------------------------------------- conferência da URL pública

def _ler_como(url: str, agente: str, tamanho: int | None) -> str | None:
    """Baixa a URL com conexão nova. Devolve None se veio um JPEG completo; senão, o problema.

    Confere o começo (FFD8FF) e o fim (FFD9) do arquivo em vez do tamanho exato: uma borda que otimiza imagens
    pode entregar um JPEG válido com outro tamanho, e isso não impede a Meta de baixar.
    """
    from _instagram import abridor_para
    req = urllib.request.Request(url, headers={"User-Agent": agente})
    try:
        with abridor_para(url).open(req, timeout=TEMPO_LEITURA) as r:
            corpo = r.read()
            tipo = r.headers.get("Content-Type", "")
            completo = corpo[:3] == b"\xff\xd8\xff" and corpo.rstrip(b"\x00").endswith(b"\xff\xd9")
            if r.status != 200 or not tipo.startswith("image/jpeg") or not completo:
                return f"status {r.status}, tipo {tipo or 'vazio'}, {len(corpo)} bytes, JPEG {'completo' if completo else 'incompleto'}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        return f"{type(e).__name__} {mascarar(getattr(e, 'reason', e))}"
    return None


def conferir_url(url: str, tamanho: int | None = None) -> list[str]:
    """Testa como navegador e como o robô de prévia da Meta antes de criar o contêiner.

    A borda às vezes trava uma leitura por dezenas de segundos: cada agente tem até TENTATIVAS_URL
    leituras, cada uma com conexão nova, e só conta o problema da última. Devolve a lista de problemas.
    """
    problemas = []
    for agente in (AGENTE_NAVEGADOR, AGENTE_META):
        for tentativa in range(TENTATIVAS_URL):
            problema = _ler_como(url, agente, tamanho)
            if problema is None:
                break
            if tentativa < TENTATIVAS_URL - 1:
                time.sleep(PAUSAS_URL[tentativa])
        else:
            problemas.append(f"{agente.split('/')[0]}: {problema} ({TENTATIVAS_URL} tentativas)")
    return problemas
