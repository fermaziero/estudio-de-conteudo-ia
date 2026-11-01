"""Cliente mínimo da API do Instagram com login do Instagram (host graph.instagram.com).

Só usa a biblioteca padrão. O token vai no cabeçalho Authorization (nunca na URL), exceto na
renovação, em que a Meta documenta o token como parâmetro; a URL nunca é impressa.
Fontes oficiais e data de conferência: referencias/limites-instagram.md.
Não é um script para rodar; é importado pelos outros.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from _comum import Incerto, ErroUso, mascarar

VERSAO_API = "v26.0"
BASE_OFICIAL = "https://graph.instagram.com"
HOSTS_LOCAIS = ("127.0.0.1", "localhost", "::1")
AGENTE = "estudio-de-conteudo-ia/1.0"
PAUSAS_ESPERA = (2, 4, 8, 10)
ESPERA_MAX = 300

DICAS = {
    2207001: "Erro no servidor do Instagram. Tente de novo em alguns minutos.",
    2207003: "A Meta demorou demais para baixar a imagem. Confira se a URL pública abre rápido e tente de novo.",
    2207004: "A imagem passa de 8 MB.",
    2207005: "Formato de imagem não aceito: o Instagram só aceita JPEG.",
    2207006: "Mídia não encontrada. Confira o token e as permissões; se persistir, crie um contêiner novo.",
    2207008: "Contêiner inexistente ou expirado. Tente de novo; se persistir, crie um contêiner novo.",
    2207009: "Proporção da imagem fora do aceito (entre 4:5 e 1,91:1).",
    2207010: "Legenda longa demais (máximo de 2.200 caracteres, 30 hashtags e 20 menções).",
    2207020: "O contêiner expirou (vale 24 horas). Crie um novo.",
    2207027: "A mídia ainda não está pronta. Espere o status FINISHED antes de publicar.",
    2207028: "Quantidade de itens do carrossel inválida (a Meta indica de 2 a 10).",
    2207032: "A Meta não conseguiu criar o contêiner. Tente de novo.",
    2207040: "Menções demais na legenda (máximo de 20).",
    2207042: "Limite diário de publicações da conta atingido. Tente de novo amanhã.",
    2207050: "A conta do Instagram está inativa, restrita ou em verificação. Abra o app do Instagram e resolva as pendências.",
    2207052: "A Meta não conseguiu baixar a imagem da URL pública. Confira se ela abre sem login e sem bloqueio de robôs.",
}
LIMITES_TAXA = (4, 17, 32, 613, 80002)


class ErroMeta(ErroUso):
    """Falha da API da Meta. `info` guarda o erro normalizado; a mensagem já é segura para a tela."""

    def __init__(self, mensagem: str, info: dict | None = None):
        super().__init__(mensagem)
        self.info = info or {}


class _SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_ABRIDOR = urllib.request.build_opener(_SemRedirecionamento)
_ABRIDOR_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SemRedirecionamento)


def abridor_para(url: str):
    host = urllib.parse.urlsplit(url).hostname
    return _ABRIDOR_LOCAL if host in HOSTS_LOCAIS else _ABRIDOR


def base_url() -> str:
    """Endereço da API. A variável ESTUDIO_INSTAGRAM_TESTE só vale para servidor falso neste computador."""
    teste = os.environ.get("ESTUDIO_INSTAGRAM_TESTE", "").strip()
    if teste:
        p = urllib.parse.urlsplit(teste)
        if p.scheme == "http" and p.hostname in HOSTS_LOCAIS:
            return teste.rstrip("/")
    return BASE_OFICIAL


def _erro_http(e: urllib.error.HTTPError) -> dict:
    bruto = e.read().decode("utf-8", "replace")
    try:
        erro = json.loads(bruto).get("error", {})
    except (ValueError, AttributeError):
        erro = {"message": bruto[:300]}
    if not isinstance(erro, dict):
        erro = {"message": str(erro)[:300]}
    return {"_erro": {"status": e.code, "mensagem": erro.get("message"), "tipo": erro.get("type"),
                      "codigo": erro.get("code"), "subcodigo": erro.get("error_subcode"),
                      "transitorio": erro.get("is_transient"), "incerto": e.code >= 500}}


def chamar(token: str, caminho: str, params: dict | None = None, dados: dict | None = None,
           timeout: int = 60, versao: bool = True, token_na_url: bool = False) -> dict:
    """GET (com params) ou POST (com dados em formulário). Erros voltam em {"_erro": ...}, sem o token.

    Queda de rede, tempo esgotado ou resposta que não é JSON voltam como erro 'incerto': a Meta pode ter
    feito o pedido ou não.
    """
    caminho = str(caminho)
    if ".." in caminho.split("/") or any(c in caminho for c in ("?", "#", "\\", "\r", "\n", " ")):
        raise ErroUso("caminho de API inválido (um id vindo de um arquivo está com defeito); nada foi enviado à Meta")
    prefixo = f"/{VERSAO_API}" if versao else ""
    consulta = dict(params or {})
    cabecalhos = {"User-Agent": AGENTE, "Accept": "application/json"}
    if token_na_url:
        consulta["access_token"] = token
    else:
        cabecalhos["Authorization"] = f"Bearer {token}"
    url = f"{base_url()}{prefixo}/{caminho.lstrip('/')}" + ("?" + urllib.parse.urlencode(consulta) if consulta else "")
    corpo = urllib.parse.urlencode(dados).encode("utf-8") if dados is not None else None
    req = urllib.request.Request(url, data=corpo, method="POST" if corpo is not None else "GET", headers=cabecalhos)
    try:
        with abridor_para(url).open(req, timeout=timeout) as r:
            resposta = json.loads(r.read().decode("utf-8"))
        return resposta if isinstance(resposta, dict) else {"_erro": {"incerto": True, "mensagem": "resposta inesperada"}}
    except urllib.error.HTTPError as e:
        return _erro_http(e)
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as e:
        return {"_erro": {"incerto": True, "mensagem": mascarar(f"{type(e).__name__}: {getattr(e, 'reason', e)}")}}


def primeiro(resposta: dict) -> dict:
    """Algumas respostas vêm como objeto e outras dentro de {"data": [objeto]}."""
    dados = resposta.get("data")
    if isinstance(dados, list):
        return dados[0] if dados and isinstance(dados[0], dict) else {}
    return resposta


def tipo_erro(info: dict) -> str:
    codigo, sub = info.get("codigo"), info.get("subcodigo")
    if codigo == 9 and sub == 2207042:
        return "cota"
    if info.get("status") == 429 or codigo in LIMITES_TAXA:
        return "taxa"
    if codigo == 190 or info.get("status") == 401:
        return "token"
    if codigo == 10 or (isinstance(codigo, int) and 200 <= codigo <= 299):
        return "permissao"
    if codigo == 368:
        return "bloqueio"
    if info.get("incerto") or info.get("transitorio") or codigo in (1, 2) or (info.get("status") or 0) >= 500:
        return "transitorio"
    return "outro"


def descrever(info: dict) -> str:
    tipo = tipo_erro(info)
    sub = info.get("subcodigo")
    base = {"token": "O token do Instagram venceu ou é inválido. Gere outro e rode credenciais.py configurar.",
            "permissao": "Falta uma permissão no token (veja docs/instagram-api.md).",
            "taxa": "A Meta limitou as chamadas por excesso de uso. Espere um pouco e tente de novo.",
            "bloqueio": "A Meta bloqueou temporariamente a ação por política. Espere e tente de novo mais tarde.",
            "cota": DICAS[2207042]}.get(tipo)
    texto = base or DICAS.get(sub) or "A Meta recusou o pedido."
    partes = []
    if info.get("mensagem"):
        partes.append(mascarar(info["mensagem"])[:200])
    if info.get("codigo"):
        partes.append(f"código {info['codigo']}" + (f", subcódigo {sub}" if sub else ""))
    elif info.get("status"):
        partes.append(f"HTTP {info['status']}")
    return f"{texto} (Meta: {'; '.join(partes)})" if partes else texto


def exigir(resposta: dict, o_que: str) -> dict:
    """Devolve a resposta ou levanta ErroMeta com mensagem em português."""
    info = resposta.get("_erro")
    if info:
        raise ErroMeta(f"{o_que}: {descrever(info)}", info)
    return resposta


# ---------------------------------------------------------------- conta e cota

def perfil(token: str, campos: str = "user_id,username,account_type,followers_count,follows_count,media_count") -> dict:
    r = chamar(token, "me", {"fields": campos})
    if r.get("_erro") and tipo_erro(r["_erro"]) == "outro" and campos != "user_id,username":
        r = chamar(token, "me", {"fields": "user_id,username"})
    exigir(r, "Não consegui ler a conta do Instagram")
    return primeiro(r)


def cota(token: str, ig_id: str) -> tuple[int | None, int | None, dict | None]:
    r = chamar(token, f"{ig_id}/content_publishing_limit", {"fields": "config,quota_usage"})
    if r.get("_erro"):
        return None, None, r["_erro"]
    d = primeiro(r)
    return d.get("quota_usage"), (d.get("config") or {}).get("quota_total"), None


# ---------------------------------------------------------------- contêineres e publicação

def criar_conteiner(token: str, ig_id: str, dados: dict) -> str:
    r = chamar(token, f"{ig_id}/media", dados=dados)
    erro = r.get("_erro")
    if erro and "alt_text" in dados and "alt_text" in (erro.get("mensagem") or ""):
        dados = {k: v for k, v in dados.items() if k != "alt_text"}
        r = chamar(token, f"{ig_id}/media", dados=dados)
    exigir(r, "A Meta recusou o contêiner")
    if not r.get("id"):
        raise ErroMeta("A Meta respondeu sem o id do contêiner")
    return str(r["id"])


def aguardar_conteiner(token: str, conteiner: str) -> str:
    """Espera o status FINISHED. ERROR e EXPIRED viram ErroMeta."""
    inicio, n = time.time(), 0
    while True:
        r = chamar(token, conteiner, {"fields": "status_code,status"})
        estado = r.get("status_code")
        if estado in ("FINISHED", "PUBLISHED"):
            return estado
        if estado in ("ERROR", "EXPIRED"):
            raise ErroMeta(f"O contêiner {conteiner} terminou em {estado}: {mascarar(r.get('status') or 'sem detalhe')}")
        erro = r.get("_erro")
        if erro and not erro.get("incerto") and tipo_erro(erro) != "transitorio":
            raise ErroMeta(f"Não consegui consultar o contêiner {conteiner}: {descrever(erro)}", erro)
        if time.time() - inicio > ESPERA_MAX:
            raise ErroMeta(f"O contêiner {conteiner} continuou em '{estado}' depois de {ESPERA_MAX} s")
        time.sleep(PAUSAS_ESPERA[min(n, len(PAUSAS_ESPERA) - 1)])
        n += 1


def permalink(token: str, media_id: str) -> str:
    r = chamar(token, media_id, {"fields": "permalink"})
    return str(r.get("permalink") or "")


def midia_recente(token: str, ig_id: str, legenda: str, desde=None) -> dict | None:
    """Acha, entre as últimas mídias, a que começa com esta legenda (e é posterior a `desde`)."""
    from _comum import interpretar_data
    r = chamar(token, f"{ig_id}/media", {"fields": "id,permalink,timestamp,caption", "limit": 10})
    inicio = " ".join(legenda.split())[:80]
    for m in r.get("data") or []:
        quando = interpretar_data(m.get("timestamp"))
        if desde is not None and quando is not None and quando < desde:
            continue
        if " ".join((m.get("caption") or "").split()).startswith(inicio):
            return m
    return None


def publicar_conteiner(token: str, ig_id: str, conteiner: str, legenda: str, desde) -> str:
    """Publica e devolve o media_id. Levanta Incerto se não der para saber se foi ao ar."""
    r = chamar(token, f"{ig_id}/media_publish", dados={"creation_id": conteiner})
    if r.get("id"):
        return str(r["id"])
    erro = r.get("_erro") or {}
    situacao = chamar(token, conteiner, {"fields": "status_code"}).get("status_code")
    if situacao == "PUBLISHED":
        achado = midia_recente(token, ig_id, legenda, desde)
        if achado:
            return str(achado["id"])
        raise Incerto(f"o contêiner {conteiner} consta como PUBLISHED, mas não achei o post na lista recente")
    if erro.get("incerto") or erro.get("transitorio") or situacao is None or tipo_erro(erro) == "transitorio":
        raise Incerto(f"resposta sem clareza da Meta ({descrever(erro) if erro else 'sem erro'}); "
                      f"status do contêiner: {situacao}")
    raise ErroMeta(f"A Meta recusou a publicação: {descrever(erro)}", erro)


# ---------------------------------------------------------------- token

def renovar_token(token: str) -> tuple[str, int]:
    """Renova o token de longa duração. Devolve (novo token, segundos de validade)."""
    r = chamar(token, "refresh_access_token", {"grant_type": "ig_refresh_token"}, versao=False, token_na_url=True)
    exigir(r, "A Meta não renovou o token (ele precisa ter mais de 24 horas e não pode ter vencido)")
    if not r.get("access_token"):
        raise ErroMeta("A Meta respondeu sem o novo token")
    try:
        segundos = int(r.get("expires_in") or 0)
    except (TypeError, ValueError):
        segundos = 0
    return str(r["access_token"]), segundos
