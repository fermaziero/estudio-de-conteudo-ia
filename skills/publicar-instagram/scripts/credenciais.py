#!/usr/bin/env python3
"""Credenciais do Instagram e do armazenamento de imagens de uma marca.

Rode sempre a partir da raiz do projeto (no macOS e no Linux, use python3):

    python -X utf8 skills/publicar-instagram/scripts/credenciais.py configurar [--marca M] [--modelo]
        abre uma janela local para colar o token e as chaves (nada passa pelo chat) e grava em
        ~/.config/estudio-de-conteudo/<marca>/ com permissão restrita. --modelo só cria os arquivos
        vazios para a pessoa preencher num editor de texto.
    python -X utf8 skills/publicar-instagram/scripts/credenciais.py verificar [--marca M] [--completo]
        confere conta, permissões, validade do token, cota de publicação e armazenamento, sem mostrar
        segredo. Com --completo, sobe uma imagem neutra de teste, confere a URL pública como navegador
        e como o robô da Meta, cria um contêiner SEM publicar e apaga a imagem.
    python -X utf8 skills/publicar-instagram/scripts/credenciais.py renovar [--marca M] [--se-faltar-dias N]
        renova o token de longa duração (precisa ter mais de 24 horas e não ter vencido).

A pasta base das credenciais pode ser trocada com a variável de ambiente ESTUDIO_CONFIG.
Código de saída: 0 = tudo certo; 1 = há problema ou recusa.
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _armazenamento as arm  # noqa: E402
import _instagram as ig  # noqa: E402
from _comum import (ErroUso, Recusa, aplicar_raiz, atualizar_env, escolher_marca, executar, ler_env,  # noqa: E402
                    opcao_raiz, pasta_config, proteger_saida, registrar_segredos, restringir_permissao)

VALIDADE_DIAS = 60
AVISO_DIAS = 10

MODELO_INSTAGRAM = """# Estúdio de Conteúdo com IA - credenciais do Instagram.
# Este arquivo é só seu: nunca cole o conteúdo dele em chat, e-mail ou commit.
# O token é o gerado no painel do app da Meta (veja docs/instagram-api.md).
IG_ACCESS_TOKEN=
IG_USER_ID=
IG_TOKEN_VALIDO_ATE=
"""

MODELO_ARMAZENAMENTO = """# Estúdio de Conteúdo com IA - armazenamento temporário das imagens (compatível com S3).
# Este arquivo é só seu: nunca cole o conteúdo dele em chat, e-mail ou commit.
# Guia: docs/armazenamento-imagens.md
ARMAZENAMENTO_ENDPOINT=
ARMAZENAMENTO_REGIAO=auto
ARMAZENAMENTO_BUCKET=
ARMAZENAMENTO_CHAVE_ID=
ARMAZENAMENTO_CHAVE_SECRETA=
ARMAZENAMENTO_URL_PUBLICA=
"""


def arquivo_instagram(marca: str) -> Path:
    return pasta_config(marca) / "instagram.env"


def parece_token(texto: str) -> bool:
    return texto.startswith("IG") and len(texto) > 50 and not any(c.isspace() for c in texto)


def carregar_instagram(marca: str) -> dict:
    """Lê o instagram.env ou recusa com a instrução de como configurar."""
    arq = arquivo_instagram(marca)
    comando = f"python -X utf8 skills/publicar-instagram/scripts/credenciais.py configurar --marca {marca}"
    if not arq.is_file():
        raise Recusa(f"o Instagram desta marca ainda não está configurado. Rode: {comando}")
    env = ler_env(arq)
    if not env.get("IG_ACCESS_TOKEN"):
        raise Recusa(f"o token do Instagram está vazio. Rode: {comando}")
    return env


def dias_restantes(env: dict) -> int | None:
    try:
        return (date.fromisoformat(env.get("IG_TOKEN_VALIDO_ATE", "")) - date.today()).days
    except ValueError:
        return None


def aviso_validade(env: dict, marca: str) -> str:
    dias = dias_restantes(env)
    if dias is None:
        return ("ATENÇÃO: o arquivo do token não tem a data de validade (IG_TOKEN_VALIDO_ATE vazia), então não sei quando "
                "ele vence e a renovação automática não consegue se programar. Se o token tem mais de 24 horas, rode "
                f"credenciais.py renovar --marca {marca} (descobre e grava a data certa). Se foi gerado hoje, rode "
                "credenciais.py configurar e informe 'Token gerado em', ou preencha IG_TOKEN_VALIDO_ATE com a data de hoje "
                "mais 60 dias (AAAA-MM-DD).")
    if dias < 0:
        return (f"ATENÇÃO: o token venceu em {env['IG_TOKEN_VALIDO_ATE']} (data estimada). Se a Meta recusar, gere outro "
                f"token e rode credenciais.py configurar --marca {marca}.")
    if dias <= AVISO_DIAS:
        return f"ATENÇÃO: o token vence em {dias} dia(s) (data estimada). Rode: credenciais.py renovar --marca {marca}"
    return ""


def renovar_se_preciso(marca: str, dias: int = AVISO_DIAS) -> str:
    """Usado pela rotina: renova quando faltam `dias` ou menos. Nunca levanta erro. Devolve uma frase."""
    try:
        env = carregar_instagram(marca)
    except ErroUso:
        return ""  # sem credenciais, quem chamou já recusa com a instrução de configurar
    restantes = dias_restantes(env)
    if restantes is None:
        # Sem a data não dá para saber se falta pouco. Renovar descobre a data real (a Meta devolve a validade nova).
        try:
            novo, segundos = ig.renovar_token(env["IG_ACCESS_TOKEN"])
        except (ig.ErroMeta, ErroUso) as e:
            return ("ATENÇÃO: o arquivo do token não tem a data de validade (IG_TOKEN_VALIDO_ATE vazia) e a tentativa de "
                    f"descobri-la renovando o token falhou: {e}. Se o token foi gerado há menos de 24 horas, isso se "
                    f"resolve sozinho nas próximas rodadas; senão, rode credenciais.py configurar --marca {marca} e informe "
                    "'Token gerado em'.")
        valido = date.today() + timedelta(seconds=segundos or VALIDADE_DIAS * 86400)
        atualizar_env(arquivo_instagram(marca), {"IG_ACCESS_TOKEN": novo, "IG_TOKEN_VALIDO_ATE": valido.isoformat()})
        return f"validade do token descoberta ao renová-lo; vale até {valido.isoformat()}"
    if restantes > dias:
        return ""
    try:
        novo, segundos = ig.renovar_token(env["IG_ACCESS_TOKEN"])
    except (ig.ErroMeta, ErroUso) as e:
        situacao = f"faltam {restantes} dia(s)" if restantes >= 0 else f"a data estimada de validade já passou há {-restantes} dia(s)"
        return f"ATENÇÃO: {situacao} e a renovação automática falhou: {e}"
    valido = date.today() + timedelta(seconds=segundos or VALIDADE_DIAS * 86400)
    atualizar_env(arquivo_instagram(marca), {"IG_ACCESS_TOKEN": novo, "IG_TOKEN_VALIDO_ATE": valido.isoformat()})
    return f"token renovado automaticamente; vale até {valido.isoformat()}"


# ---------------------------------------------------------------- configurar

CAMPOS_JANELA = (
    ("INSTAGRAM", "Instagram", None, False, ""),
    ("IG_ACCESS_TOKEN", "Token de acesso do Instagram", None, True, ""),
    ("IG_TOKEN_GERADO_EM", "Token gerado em (AAAA-MM-DD)", None, False, "hoje"),
    ("ARMAZENAMENTO", "Armazenamento das imagens", None, False, ""),
    ("ARMAZENAMENTO_ENDPOINT", "Endereço (endpoint) do armazenamento", None, False, ""),
    ("ARMAZENAMENTO_REGIAO", "Região", None, False, "auto"),
    ("ARMAZENAMENTO_BUCKET", "Nome do bucket", None, False, ""),
    ("ARMAZENAMENTO_CHAVE_ID", "Access Key ID", None, False, ""),
    ("ARMAZENAMENTO_CHAVE_SECRETA", "Secret Access Key", None, True, ""),
    ("ARMAZENAMENTO_URL_PUBLICA", "URL pública das imagens", None, False, ""),
)


def validar_novos(novos: dict, atual_ig: dict, atual_arm: dict) -> list[str]:
    problemas = []
    token = novos.get("IG_ACCESS_TOKEN", "")
    if token:
        if token.startswith("EA"):
            problemas.append("esse token parece ser do login do Facebook; esta skill usa a API do Instagram com login "
                             "do Instagram (o token começa com IG)")
        elif not parece_token(token):
            problemas.append("o token do Instagram não parece válido (deve começar com IG, sem espaços)")
    gerado = novos.get("IG_TOKEN_GERADO_EM", "")
    if gerado:
        try:
            if date.fromisoformat(gerado) > date.today():
                problemas.append("a data de geração do token está no futuro")
        except ValueError:
            problemas.append("a data de geração do token deve ser AAAA-MM-DD")
    junto = {**atual_arm, **{k: v for k, v in novos.items() if k in arm.CAMPOS and v}}
    algum = any(novos.get(c) for c in arm.CAMPOS if c != "ARMAZENAMENTO_REGIAO") or bool(atual_arm.get("ARMAZENAMENTO_BUCKET"))
    if algum:
        problemas += arm.problemas_config(junto)
    if not token and not atual_ig.get("IG_ACCESS_TOKEN") and not algum:
        problemas.append("nada para gravar: cole pelo menos o token do Instagram")
    return problemas


def pedir_em_janela(atual: dict, marca: str, validar) -> dict:
    """Janela local com campos mascarados. Devolve só o que a pessoa preencheu ({} se cancelou)."""
    import tkinter as tk
    from tkinter import messagebox

    janela = tk.Tk()
    janela.title(f"Credenciais - {marca}")
    janela.attributes("-topmost", True)
    tk.Label(janela, justify="left", text="Cole os valores (Ctrl+V) e clique em Salvar.\n"
             "Campo secreto em branco mantém o valor atual. Nada disso passa pelo chat.").grid(
        row=0, column=0, columnspan=2, padx=18, pady=(16, 8), sticky="w")
    entradas, linha = {}, 1
    for nome, rotulo, _, oculto, padrao in CAMPOS_JANELA:
        if nome in ("INSTAGRAM", "ARMAZENAMENTO"):
            tk.Label(janela, text=rotulo, font=("TkDefaultFont", 10, "bold")).grid(
                row=linha, column=0, columnspan=2, padx=18, pady=(10, 2), sticky="w")
        else:
            tk.Label(janela, text=rotulo).grid(row=linha, column=0, sticky="e", padx=(18, 8), pady=3)
            campo = tk.Entry(janela, width=58, show="•" if oculto else "")
            if nome == "IG_TOKEN_GERADO_EM":
                campo.insert(0, date.today().isoformat())
            elif not oculto and (atual.get(nome) or padrao):
                campo.insert(0, atual.get(nome) or padrao)
            campo.grid(row=linha, column=1, padx=(0, 18), pady=3)
            entradas[nome] = campo
        linha += 1
    resultado: dict = {}

    def salvar(_=None):
        valores = {n: c.get().strip() for n, c in entradas.items()}
        valores = {n: v for n, v in valores.items() if v}
        problemas = validar(valores)
        if problemas:
            messagebox.showerror("Confira", "\n".join(f"- {p}" for p in problemas), parent=janela)
            return
        resultado.update(valores)
        janela.destroy()

    tk.Button(janela, text="Salvar", command=salvar).grid(row=linha, column=0, columnspan=2, pady=14)
    janela.bind("<Return>", salvar)
    campo_inicial = entradas.get("IG_ACCESS_TOKEN")
    if campo_inicial:
        campo_inicial.focus_force()
    janela.mainloop()
    return resultado


def gravar_modelos(marca: str) -> list[Path]:
    criados = []
    pasta = pasta_config(marca)
    pasta.mkdir(parents=True, exist_ok=True)
    restringir_permissao(pasta)
    for arq, modelo in ((arquivo_instagram(marca), MODELO_INSTAGRAM), (arm.arquivo_env(marca), MODELO_ARMAZENAMENTO)):
        if not arq.is_file():
            arq.write_text(modelo, encoding="utf-8")
            restringir_permissao(arq)
            criados.append(arq)
    return criados


def configurar(args) -> int:
    marca = escolher_marca(args.marca)
    atual_ig, atual_arm = ler_env(arquivo_instagram(marca)), ler_env(arm.arquivo_env(marca))
    atual = {**atual_ig, **atual_arm}
    novos: dict = {}
    usar_janela = not args.modelo
    if usar_janela:
        try:
            novos = pedir_em_janela(atual, marca, lambda v: validar_novos(v, atual_ig, atual_arm))
            if not novos:
                print("Cancelado: nada foi gravado.")
                return 1
        except Exception as e:  # sem tkinter ou sem tela
            print(f"Não consegui abrir a janela ({type(e).__name__}). Vou criar os arquivos para você preencher.")
            usar_janela = False
    if not usar_janela:
        criados = gravar_modelos(marca)
        print("Arquivos de credenciais (abra num editor de texto, como o Bloco de Notas ou o TextEdit, cole os valores e salve):")
        print(f"  {arquivo_instagram(marca)}")
        print(f"  {arm.arquivo_env(marca)}")
        if not criados:
            print("Eles já existiam; nada foi alterado.")
        print("Preencha também IG_TOKEN_VALIDO_ATE (AAAA-MM-DD): se o token foi gerado hoje, é a data de hoje mais 60 dias. "
              "Sem ela, a renovação automática só passa a funcionar depois do primeiro 'renovar'.")
        print("Depois rode: python -X utf8 skills/publicar-instagram/scripts/credenciais.py verificar "
              f"--marca {marca}")
        return 0

    registrar_segredos(novos.get(k, "") for k in ("IG_ACCESS_TOKEN", "ARMAZENAMENTO_CHAVE_SECRETA", "ARMAZENAMENTO_CHAVE_ID"))
    if novos.get("IG_ACCESS_TOKEN"):
        gerado = date.fromisoformat(novos.get("IG_TOKEN_GERADO_EM") or date.today().isoformat())
        atualizar_env(arquivo_instagram(marca), {
            "IG_ACCESS_TOKEN": novos["IG_ACCESS_TOKEN"], "IG_USER_ID": "",
            "IG_TOKEN_VALIDO_ATE": (gerado + timedelta(days=VALIDADE_DIAS)).isoformat()}, MODELO_INSTAGRAM)
        print(f"Token do Instagram gravado em {arquivo_instagram(marca)} (não mostrado).")
    do_arm = {k: v for k, v in novos.items() if k in arm.CAMPOS}
    if do_arm:
        do_arm.setdefault("ARMAZENAMENTO_REGIAO", atual_arm.get("ARMAZENAMENTO_REGIAO") or "auto")
        atualizar_env(arm.arquivo_env(marca), do_arm, MODELO_ARMAZENAMENTO)
        print(f"Dados do armazenamento gravados em {arm.arquivo_env(marca)} (chaves não mostradas).")
    print("Agora rode: python -X utf8 skills/publicar-instagram/scripts/credenciais.py verificar "
          f"--marca {marca} --completo")
    return 0


# ---------------------------------------------------------------- verificar

def imagem_de_teste() -> bytes:
    from PIL import Image
    imagem = Image.new("RGB", (1080, 1350), (128, 128, 128))
    destino = io.BytesIO()
    imagem.save(destino, "JPEG", quality=90)
    return destino.getvalue()


def sonda_permissao(info: dict | None) -> str:
    if not info:
        return "OK"
    tipo = ig.tipo_erro(info)
    if tipo == "permissao":
        return "FALTA a permissão no token"
    if tipo == "token":
        return "token inválido ou vencido"
    return f"não consegui confirmar ({ig.descrever(info)[:120]})"


def verificar(args) -> int:
    marca = escolher_marca(args.marca)
    problemas = 0
    env = carregar_instagram(marca)
    token = env["IG_ACCESS_TOKEN"]
    print(f"Marca: {marca}")
    print("== Instagram ==")
    print(f"Arquivo do token: {arquivo_instagram(marca)} (token presente; não é mostrado)")
    if not token.startswith("IG"):
        print("PROBLEMA: o token não começa com IG. Esta skill usa a API do Instagram com login do Instagram.")
        problemas += 1
    restantes = dias_restantes(env)
    if restantes is not None:
        print(f"Validade do token (estimada): {env['IG_TOKEN_VALIDO_ATE']} (faltam {restantes} dia(s))")
    aviso = aviso_validade(env, marca)
    if aviso:
        print(aviso)
    try:
        conta = ig.perfil(token)
    except ig.ErroMeta as e:
        print(f"PROBLEMA: {e}")
        return 1
    ig_id = str(conta.get("user_id") or conta.get("id") or "")
    print(f"Conta: @{conta.get('username')} (id {ig_id}), tipo {conta.get('account_type', 'desconhecido')}")
    if ig_id and env.get("IG_USER_ID") != ig_id:
        atualizar_env(arquivo_instagram(marca), {"IG_USER_ID": ig_id}, MODELO_INSTAGRAM)
        print("IG_USER_ID gravado.")
    arroba = arroba_da_marca(marca)
    if not arroba:
        print(f"PROBLEMA: marcas/{marca}/visual.json não tem a 'arroba' (por exemplo \"@meuperfil\"). Sem ela a skill não "
              "consegue conferir que o token é da conta certa e se recusa a publicar.")
        problemas += 1
    elif arroba != str(conta.get("username") or "").lower():
        print(f"PROBLEMA: a arroba em visual.json (@{arroba}) é diferente da conta do token (@{conta.get('username')}). "
              "Confira se o token é da marca certa.")
        problemas += 1
    usados, total, erro_cota = ig.cota(token, ig_id)
    print(f"Publicar (permissão instagram_business_content_publish): {sonda_permissao(erro_cota)}"
          + (f"; cota usada nas últimas 24 h: {usados} de {total}" if erro_cota is None else ""))
    if erro_cota:
        problemas += 1
    r = ig.chamar(token, f"{ig_id}/insights", {"metric": "reach", "period": "day", "metric_type": "total_value"})
    situacao = sonda_permissao(r.get("_erro"))
    print(f"Métricas (permissão instagram_business_manage_insights): {situacao}")
    if situacao.startswith("FALTA"):
        print("  Sem ela a coleta de métricas não traz alcance, salvamentos e compartilhamentos.")

    print("== Armazenamento de imagens ==")
    arq = arm.arquivo_env(marca)
    cfg = ler_env(arq)
    falhas = arm.problemas_config(cfg) if arq.is_file() else [
        "ainda não configurado (é necessário para publicar; a coleta de métricas funciona sem ele)"]
    if falhas:
        print("PROBLEMA: " + "; ".join(falhas))
        print(f"  Rode: python -X utf8 skills/publicar-instagram/scripts/credenciais.py configurar --marca {marca}")
        problemas += 1
    else:
        print(f"Configurado: bucket {cfg['ARMAZENAMENTO_BUCKET']}, região {cfg['ARMAZENAMENTO_REGIAO']}, "
              f"URL pública {cfg['ARMAZENAMENTO_URL_PUBLICA']} (chaves não mostradas)")
        if args.completo:
            problemas += teste_completo(marca, token, ig_id)
        else:
            print("Teste de envio não feito. Para provar o caminho inteiro, rode de novo com --completo.")
    print("RESULTADO: " + ("há problema(s) a resolver." if problemas else "tudo certo."))
    return 1 if problemas else 0


def arroba_da_marca(marca: str) -> str:
    from _comum import ler_json, pasta_marca
    try:
        valor = str(ler_json(pasta_marca(marca) / "visual.json").get("arroba") or "")
    except (OSError, ValueError, AttributeError):
        return ""
    valor = valor.strip().lstrip("@").lower()
    return "" if valor in ("", "perfil", "seuperfil", "seu_perfil") else valor


def teste_completo(marca: str, token: str, ig_id: str) -> int:
    """Sobe uma imagem neutra, testa a URL pública, cria um contêiner sem publicar e apaga a imagem."""
    print("-- Teste completo (nada será publicado) --")
    try:
        a = arm.Armazenamento.carregar(marca)
        jpeg = imagem_de_teste()
    except (ErroUso, ImportError) as e:
        print(f"PROBLEMA: {e}")
        return 1
    chave = a.chave_nova("teste", "teste-armazenamento.jpg")
    problemas = 0
    url = a.url_publica(chave)
    try:
        a.enviar_jpeg(jpeg, chave)
        print(f"Imagem de teste enviada ({len(jpeg)} bytes).")
        falhas = arm.conferir_url(url, len(jpeg))
        if falhas:
            print("PROBLEMA: a URL pública não abre direito: " + "; ".join(falhas))
            print("  Veja docs/armazenamento-imagens.md, seção 'Se a URL não abrir'.")
            problemas += 1
        else:
            print("OK: a URL pública abre como JPEG para navegador e para o robô de prévia da Meta.")
            conteiner = ig.criar_conteiner(token, ig_id, {"image_url": url})
            ig.aguardar_conteiner(token, conteiner)
            print("OK: a Meta baixou a imagem e o token pode criar posts. Contêiner criado e NÃO publicado "
                  "(expira sozinho em 24 h).")
    except (RuntimeError, ValueError, ig.ErroMeta) as e:
        print(f"PROBLEMA: {e}")
        problemas += 1
    finally:
        try:
            a.apagar(chave)
            depois = a.status_publico(url)
            print(f"Imagem de teste apagada; a URL agora responde {depois}.")
            if depois == 200:
                print("ATENÇÃO: a imagem continua acessível depois de apagada (cache na borda). "
                      "Confira o cache do domínio em docs/armazenamento-imagens.md.")
        except RuntimeError as e:
            print(f"ATENÇÃO: não consegui apagar a imagem de teste ({e}). A regra de ciclo de vida do bucket "
                  "limpa depois; se não existir, crie-a (docs/armazenamento-imagens.md).")
    return problemas


# ---------------------------------------------------------------- renovar

def renovar(args) -> int:
    marca = escolher_marca(args.marca)
    env = carregar_instagram(marca)
    restantes = dias_restantes(env)
    if args.se_faltar_dias is not None and restantes is not None and restantes > args.se_faltar_dias:
        print(f"Não precisa renovar agora: faltam {restantes} dia(s) (limite pedido: {args.se_faltar_dias}).")
        return 0
    novo, segundos = ig.renovar_token(env["IG_ACCESS_TOKEN"])
    valido = date.today() + timedelta(seconds=segundos or VALIDADE_DIAS * 86400)
    atualizar_env(arquivo_instagram(marca), {"IG_ACCESS_TOKEN": novo, "IG_TOKEN_VALIDO_ATE": valido.isoformat()},
                  MODELO_INSTAGRAM)
    print(f"Token renovado; vale até {valido.isoformat()} (novo token gravado; não é mostrado).")
    return 0


def main(argv=None) -> int:
    proteger_saida()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcao_raiz(p)
    sub = p.add_subparsers(dest="comando", required=True)
    c = sub.add_parser("configurar", help="grava o token e as chaves numa janela local")
    c.add_argument("--marca")
    c.add_argument("--modelo", action="store_true", help="só cria os arquivos vazios para preencher num editor")
    v = sub.add_parser("verificar", help="confere conta, permissões, token, cota e armazenamento")
    v.add_argument("--marca")
    v.add_argument("--completo", action="store_true", help="também testa o envio da imagem e a criação de contêiner")
    r = sub.add_parser("renovar", help="renova o token de longa duração")
    r.add_argument("--marca")
    r.add_argument("--se-faltar-dias", type=int, help="só renova se faltarem N dias ou menos")
    for sp in (c, v, r):
        opcao_raiz(sp, subcomando=True)
    a = p.parse_args(argv)
    aplicar_raiz(a)
    return {"configurar": configurar, "verificar": verificar, "renovar": renovar}[a.comando](a)


if __name__ == "__main__":
    executar(main)
