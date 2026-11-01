#!/usr/bin/env python3
"""Coleta as métricas do perfil e dos posts do Instagram e grava em marcas/<marca>/metricas/.

Rode sempre a partir da raiz do projeto (no macOS e no Linux, use python3):

    python -X utf8 skills/publicar-instagram/scripts/metricas.py coletar [--marca M] [--dias 90] [--limite 200] [--simular]

Cada coleta ACRESCENTA linhas (nada se apaga), formando a história dos números:
    metricas/perfil.csv   coletado_em,seguidores,seguindo,publicacoes
    metricas/posts.csv    coletado_em,media_id,post_id,publicado_em,tipo,curtidas,comentarios,alcance,
                          salvamentos,compartilhamentos,visualizacoes,interacoes,permalink
O post_id liga a mídia ao post deste projeto pelo media_id do publicados.csv. Valor que a Meta não
informa fica vazio (nunca zero). Com --simular, lê tudo na Meta mas não grava arquivo nenhum.
Os nomes das métricas e as fontes estão em skills/publicar-instagram/referencias/metricas.md.

Código de saída: 0 = ok; 1 = erro; 3 = coleta parcial (limite de chamadas da Meta).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _instagram as ig  # noqa: E402
import credenciais  # noqa: E402
from _comum import (ErroUso, abrir_log, agora, anexar_csv, aplicar_raiz, escolher_marca, executar,  # noqa: E402
                    interpretar_data, iso, normalizar_csv, opcao_raiz, pasta_marca, proteger_saida, registros_publicados)

COLUNAS_PERFIL = ["coletado_em", "seguidores", "seguindo", "publicacoes"]
COLUNAS_POSTS = ["coletado_em", "media_id", "post_id", "publicado_em", "tipo", "curtidas", "comentarios", "alcance",
                 "salvamentos", "compartilhamentos", "visualizacoes", "interacoes", "permalink"]
METRICAS = (("reach", "alcance"), ("saved", "salvamentos"), ("shares", "compartilhamentos"),
            ("views", "visualizacoes"), ("total_interactions", "interacoes"))
CAMPOS_PERFIL = "user_id,username,followers_count,follows_count,media_count"
CAMPOS_MIDIA = "id,media_type,media_product_type,permalink,timestamp,like_count,comments_count"
CAMPOS_MIDIA_SEM_PRODUTO = "id,media_type,permalink,timestamp,like_count,comments_count"
ESPACO_META = 0.5
POR_PAGINA = 25
MAX_PAGINAS = 40
PERMISSOES_SEGUIDAS = 3
_ultima = [0.0]


class LimiteMeta(Exception):
    """A Meta devolveu erro de taxa: parar de chamar."""


def chamar_meta(token: str, caminho: str, params: dict | None = None) -> dict:
    """ig.chamar com espaçamento mínimo. Taxa e token viram exceção; o resto volta em r['_erro']."""
    r: dict = {}
    for tentativa in range(2):
        espera = ESPACO_META - (time.monotonic() - _ultima[0])
        if espera > 0:
            time.sleep(espera)
        r = ig.chamar(token, caminho, params)
        _ultima[0] = time.monotonic()
        erro = r.get("_erro")
        if not erro:
            return r
        tipo = ig.tipo_erro(erro)
        if tipo in ("taxa", "bloqueio"):
            raise LimiteMeta(ig.descrever(erro))
        if tipo == "token":
            raise ErroUso(ig.descrever(erro))
        if tipo != "transitorio" or tentativa:
            return r
        time.sleep(ESPACO_META * 4)
    return r


def numero(valor):
    """Inteiro >= 0 ou None."""
    if isinstance(valor, bool):
        return None
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return n if 0 <= n <= 10 ** 12 else None


def listar_midias(token: str, ig_id: str, dias: int, limite: int) -> list[dict]:
    """Mídias recentes (da mais nova para a mais velha) até `dias` e `limite`, seguindo a paginação."""
    corte = agora() - timedelta(days=dias)
    params = {"fields": CAMPOS_MIDIA, "limit": POR_PAGINA}
    midias: list[dict] = []
    for _ in range(MAX_PAGINAS):
        r = chamar_meta(token, f"{ig_id}/media", params)
        erro = r.get("_erro")
        if erro and params["fields"] == CAMPOS_MIDIA and erro.get("codigo") == 100:
            params = {**params, "fields": CAMPOS_MIDIA_SEM_PRODUTO}
            continue
        if erro:
            raise ErroUso(f"não consegui listar as mídias: {ig.descrever(erro)}")
        dados = [m for m in (r.get("data") or []) if isinstance(m, dict)]
        recentes = 0
        for m in dados:
            quando = interpretar_data(m.get("timestamp"))
            if quando is None or quando < corte:
                continue
            recentes += 1
            midias.append(m)
            if len(midias) >= limite:
                return midias
        depois = ((r.get("paging") or {}).get("cursors") or {}).get("after")
        if not dados or not recentes or not depois or (not (r.get("paging") or {}).get("next") and len(dados) < POR_PAGINA):
            break
        params = {**params, "after": depois}
    return midias


def tipo_do_projeto(m: dict) -> str:
    """Mesmo vocabulário do campo 'formato' dos posts: carrossel, post_unico, reel (ou video)."""
    produto = str(m.get("media_product_type") or "").upper()
    tipo = str(m.get("media_type") or "").upper()
    if produto == "REELS":
        return "reel"
    return {"CAROUSEL_ALBUM": "carrossel", "IMAGE": "post_unico", "VIDEO": "video"}.get(tipo, tipo.lower())


def valores_insights(r: dict) -> dict:
    saida = {}
    for item in r.get("data") or []:
        if not isinstance(item, dict):
            continue
        valores = item.get("values")
        valor = valores[0].get("value") if isinstance(valores, list) and valores and isinstance(valores[0], dict) else None
        if valor is None and isinstance(item.get("total_value"), dict):
            valor = item["total_value"].get("value")
        if item.get("name") and numero(valor) is not None:
            saida[item["name"]] = numero(valor)
    return saida


def buscar_insights(token: str, media_id: str) -> tuple[dict, str]:
    """(valores por métrica da Meta, situação): ok, vazio (sem dado) ou permissao."""
    todas = [m for m, _ in METRICAS]
    r = chamar_meta(token, f"{media_id}/insights", {"metric": ",".join(todas)})
    erro = r.get("_erro")
    if not erro:
        valores = valores_insights(r)
        return valores, ("ok" if valores else "vazio")
    if ig.tipo_erro(erro) == "permissao":
        return {}, "permissao"
    valores: dict = {}
    for metrica in todas:  # uma métrica que a mídia não aceita derruba o pedido inteiro: tenta uma a uma
        r = chamar_meta(token, f"{media_id}/insights", {"metric": metrica})
        if r.get("_erro"):
            if ig.tipo_erro(r["_erro"]) == "permissao":
                return valores, "permissao"
            continue
        valores.update(valores_insights(r))
    return valores, ("ok" if valores else "vazio")


def linha_da_midia(m: dict, coletado_em: str, liga: dict) -> dict | None:
    media_id = str(m.get("id") or "")
    quando = interpretar_data(m.get("timestamp"))
    if not re.fullmatch(r"\d{5,30}", media_id) or quando is None:
        return None
    permalink = str(m.get("permalink") or "")
    return {"coletado_em": coletado_em, "media_id": media_id, "post_id": liga.get(media_id, ""),
            "publicado_em": iso(quando.astimezone()), "tipo": tipo_do_projeto(m),
            "curtidas": numero(m.get("like_count")), "comentarios": numero(m.get("comments_count")),
            "permalink": permalink if permalink.startswith(("http://", "https://")) else ""}


def coletar(args) -> int:
    marca = escolher_marca(args.marca)
    if not 1 <= args.dias <= 365 or not 1 <= args.limite <= 1000:
        raise ErroUso("--dias deve ficar entre 1 e 365 e --limite entre 1 e 1000")
    aviso_renovacao = ""
    if not args.simular:
        proteger_saida(abrir_log(marca, "coletar-metricas"))
        aviso_renovacao = credenciais.renovar_se_preciso(marca)
        if aviso_renovacao:
            print(aviso_renovacao)
    env = credenciais.carregar_instagram(marca)
    token = env["IG_ACCESS_TOKEN"]
    aviso = "" if aviso_renovacao else credenciais.aviso_validade(env, marca)
    if aviso:
        print(aviso)
    try:
        r = chamar_meta(token, "me", {"fields": CAMPOS_PERFIL})
        if r.get("_erro") and ig.tipo_erro(r["_erro"]) == "outro":
            r = chamar_meta(token, "me", {"fields": "user_id,username"})
        ig.exigir(r, "Não consegui ler o perfil")
        eu = ig.primeiro(r)
        ig_id = str(env.get("IG_USER_ID") or eu.get("user_id") or eu.get("id") or "")
        if not re.fullmatch(r"\d{3,30}", ig_id):
            raise ErroUso("não achei o id da conta. Rode: credenciais.py verificar")
        arroba = credenciais.arroba_da_marca(marca)
        if not arroba:
            print(f"AVISO: marcas/{marca}/visual.json não tem a 'arroba'; não consigo conferir se o token é desta marca. "
                  "A coleta segue, mas publicar é recusado sem ela.")
        elif arroba != str(eu.get("username") or "").lower():
            raise ErroUso(f"o token é da conta @{eu.get('username')}, mas esta marca usa @{arroba} (visual.json). "
                          "Nada foi coletado")
        midias = listar_midias(token, ig_id, args.dias, args.limite)
    except LimiteMeta as e:
        raise ErroUso(f"a Meta limitou as chamadas ({e}). Parei sem gravar nada; tente de novo mais tarde") from None

    coletado_em = iso(agora())
    liga = {l["media_id"]: l["post_id"] for l in registros_publicados(marca) if l.get("media_id") and l.get("post_id")}
    itens = [l for l in (linha_da_midia(m, coletado_em, liga) for m in midias) if l]
    for item in itens:
        item.update({coluna: None for _, coluna in METRICAS})
    com = sem = sem_permissao = seguidas = 0
    desistiu, limite = False, None
    for n, item in enumerate(itens):
        if desistiu:
            continue
        try:
            valores, situacao = buscar_insights(token, item["media_id"])
        except LimiteMeta as e:
            limite = (str(e), len(itens) - n)
            break
        if situacao == "permissao":
            sem_permissao += 1
            seguidas += 1
            desistiu = not com and seguidas >= PERMISSOES_SEGUIDAS
            continue
        seguidas = 0
        if valores:
            com += 1
            for metrica, coluna in METRICAS:
                item[coluna] = valores.get(metrica)
        else:
            sem += 1
    linhas = itens

    perfil = {"coletado_em": coletado_em, "seguidores": numero(eu.get("followers_count")),
              "seguindo": numero(eu.get("follows_count")), "publicacoes": numero(eu.get("media_count"))}
    print(f"@{eu.get('username')}: " + (f"{perfil['seguidores']} seguidores, {perfil['seguindo']} seguindo, "
                                        f"{perfil['publicacoes']} publicações. " if perfil["seguidores"] is not None
                                        else "a Meta não informou os seguidores. ")
          + f"{len(linhas)} mídia(s) dos últimos {args.dias} dias.")
    print(f"Insights: {com} com dados, {sem} sem dados na Meta (normal nos posts muito novos, que levam até 48 h).")
    if sem_permissao:
        print(f"ATENÇÃO: {sem_permissao} mídia(s) sem permissão de insights. Falta instagram_business_manage_insights no "
              "token; sem ela, alcance, salvamentos e compartilhamentos ficam vazios.")
    if limite:
        print(f"ATENÇÃO: a Meta limitou as chamadas ({limite[0]}). Parei aqui; {limite[1]} mídia(s) ficam sem insights "
              "nesta coleta e entram na próxima.")
    ligadas = sum(1 for l in linhas if l["post_id"])
    if args.simular:
        for l in linhas[:5]:
            print(f"  - {l['publicado_em'][:10]} | {l['tipo']} | curtidas {l['curtidas']} | alcance {l['alcance']} | "
                  f"{l['post_id'] or 'fora do projeto'}")
        print("Simulação: nenhum arquivo foi gravado.")
    else:
        pasta = pasta_marca(marca) / "metricas"
        try:
            # aceita colunas extras, maiúsculas, BOM e ';' do Excel sem perder dados (veja normalizar_csv)
            cols_perfil = normalizar_csv(pasta / "perfil.csv", COLUNAS_PERFIL, ["coletado_em", "seguidores"])
            cols_posts = normalizar_csv(pasta / "posts.csv", COLUNAS_POSTS, ["coletado_em", "media_id"])
            anexar_csv(pasta / "perfil.csv", cols_perfil, [perfil])
            anexar_csv(pasta / "posts.csv", cols_posts, linhas)
        except (OSError, csv.Error) as e:
            raise ErroUso(f"não consegui gravar em metricas/ ({e}). Se o CSV está aberto no Excel, feche e rode de novo") from None
        print(f"Gravado em marcas/{marca}/metricas/: perfil.csv (+1 linha) e posts.csv (+{len(linhas)} linhas, "
              f"{ligadas} ligadas a posts deste projeto).")
    return 3 if limite else 0


def main(argv=None) -> int:
    proteger_saida()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcao_raiz(p)
    sub = p.add_subparsers(dest="comando", required=True)
    c = sub.add_parser("coletar", help="coleta perfil e posts e acrescenta nos CSVs")
    c.add_argument("--marca", help="slug da marca (pode omitir se houver só uma além de 'exemplo')")
    opcao_raiz(c, subcomando=True)
    c.add_argument("--dias", type=int, default=90, help="quantos dias para trás (padrão 90)")
    c.add_argument("--limite", type=int, default=200, help="máximo de mídias (padrão 200)")
    c.add_argument("--simular", action="store_true", help="lê na Meta mas não grava arquivos")
    a = p.parse_args(argv)
    aplicar_raiz(a)
    return coletar(a)


if __name__ == "__main__":
    executar(main)
