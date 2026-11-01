#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere a pasta de uma marca contra o contrato do projeto (docs/arquitetura.md).

Só lê arquivos; não altera nada. Confere: arquivos obrigatórios; seções de marca.md, regras.md e
padrao-visual.md; tabela de feedback.md; campos e tipos de visual.json e estrategia.json (cores hex,
pesos dos pilares somando 100, proporção, datas AAAA-MM-DD, status); logo, avatar, fontes e fotos
(arquivos existem e são imagens ou fontes válidas); e se há segredos esquecidos na pasta.

Erros impedem gerar artes e publicar. Avisos pedem atenção, mas não bloqueiam.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _marca_comum as c  # noqa: E402

ARQUIVOS_OBRIGATORIOS = ["marca.md", "regras.md", "padrao-visual.md", "visual.json", "estrategia.json", "feedback.md"]
AREAS = ["arquivos", "textos", "visual", "estrategia", "assets", "segredos"]

SECOES_MARCA = ["Quem é", "O que oferece", "Para quem", "Diferenciais e provas autorizadas", "Tom de voz",
                "Temas que domina", "Chamadas disponíveis", "Links oficiais", "Fuso horário"]
SECOES_REGRAS = ["O que nunca prometer ou afirmar", "Temas proibidos ou só sob pedido", "Dados que nunca aparecem",
                 "Quem pode ser citado e com qual autorização", "Limites de humor, política e religião"]
SECOES_PADRAO_VISUAL = ["Padrão recomendado", "Capa", "Slides internos", "Último slide", "Fotos", "Logo", "O que evitar"]

# "tipografia" não está no contrato, mas o gerador de artes aceita (tamanhos de letra em px, opcional).
CHAVES_VISUAL = {"versao_esquema", "nome_exibicao", "arroba", "proporcao_padrao", "cores", "fontes", "logo",
                 "avatar", "numeracao", "rodape", "tipografia"}
CHAVES_CORES = ["fundo", "texto", "destaque", "suave", "fundo_escuro", "texto_sobre_escuro"]
CHAVES_LOGO = {"fundo_claro", "fundo_escuro", "posicao", "largura_px"}
POSICOES_LOGO = ["superior-esquerda", "superior-direita", "inferior-esquerda", "inferior-direita"]
PROPORCOES = ["4:5", "1:1"]

CHAVES_ESTRATEGIA = {"versao_esquema", "atualizado_em", "status", "objetivo", "pilares", "ritmo", "metas", "funil",
                     "movimentos"}
INDICADORES = ["seguidores", "posts_por_semana", "alcance_medio", "salvamentos_medio", "comentarios_medio",
               "compartilhamentos_medio", "manual"]
FORMATOS = ["carrossel", "post_unico", "reel"]

RE_FUSO = re.compile(r"^(?:UTC|[A-Z][A-Za-z_]+/[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+)?)$")
RE_PREENCHER = re.compile(r"\[PREENCHER[^\]]*\]")
RE_A_CONFIRMAR = re.compile(r"\(a confirmar\)", re.I)
RE_MODELO = re.compile(r"\{\{[A-Z_]+\}\}")
RE_URL = re.compile(r"https?://[^\s)>\]]*")

EXTENSOES_TEXTO = {".md", ".json", ".csv", ".txt", ".html", ".yml", ".yaml", ".ini", ".cfg", ".py", ".js"}
LIMITE_LEITURA = 2 * 1024 * 1024


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------

@dataclass
class Msg:
    nivel: str  # "erro" ou "aviso"
    campo: str
    texto: str


class Coletor:
    def __init__(self, nome: str) -> None:
        self.nome = nome
        self.msgs: list[Msg] = []
        self.notas: list[str] = []

    def erro(self, campo: str, texto: str) -> None:
        self.msgs.append(Msg("erro", campo, texto))

    def aviso(self, campo: str, texto: str) -> None:
        self.msgs.append(Msg("aviso", campo, texto))

    def nota(self, texto: str) -> None:
        self.notas.append(texto)

    @property
    def erros(self) -> list[Msg]:
        return [m for m in self.msgs if m.nivel == "erro"]

    @property
    def avisos(self) -> list[Msg]:
        return [m for m in self.msgs if m.nivel == "aviso"]


def lista_de_linhas(numeros: list[int]) -> str:
    mostrados = ", ".join(str(n) for n in numeros[:6]) + (" …" if len(numeros) > 6 else "")
    return ("linha " if len(numeros) == 1 else "linhas ") + mostrados


def resumo(texto: str, limite: int = 48) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def ler_ou_reportar(col: Coletor, arquivo: Path, reportar_ausencia: bool) -> str | None:
    if not arquivo.is_file():
        if reportar_ausencia:
            col.erro(arquivo.name, "arquivo obrigatório não encontrado")
        return None
    texto, erro = c.ler_texto(arquivo)
    if erro:
        col.erro(arquivo.name, erro)
        return None
    return texto


def ler_json_ou_reportar(col: Coletor, arquivo: Path, reportar_ausencia: bool):
    if not arquivo.is_file():
        if reportar_ausencia:
            col.erro(arquivo.name, "arquivo obrigatório não encontrado")
        return None
    dados, erro = c.ler_json(arquivo)
    if erro:
        col.erro(arquivo.name, erro)
        return None
    return dados


def eh_numero(v) -> bool:
    """Número de verdade: nem texto, nem true/false, nem NaN ou infinito (que o json do Python aceita)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def dica_de_slug(valor) -> str:
    """Sugestão de id no formato slug (minúsculas, números e hífen) a partir de um valor inválido."""
    if not isinstance(valor, str):
        return ""
    sugestao = c.normalizar(valor).replace(" ", "-")
    return f" Sugestão: '{sugestao}'." if sugestao and c.RE_SLUG.match(sugestao) else ""


def eh_inteiro(v) -> bool:
    return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())


def texto_nao_vazio(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


# ---------------------------------------------------------------------------
# Arquivos e textos
# ---------------------------------------------------------------------------

def checar_arquivos(col: Coletor, marca_dir: Path, slug: str) -> None:
    faltando = [a for a in ARQUIVOS_OBRIGATORIOS if not (marca_dir / a).is_file()]
    for arquivo in faltando:
        col.erro(arquivo, "arquivo obrigatório não encontrado. Use a skill configurar-marca para criá-lo a partir do modelo.")
    if not (marca_dir / "assets").is_dir():
        col.aviso("assets/", "pasta não encontrada. Crie assets/logo/, assets/fotos/ e assets/fontes/ para guardar logo, fotos e fontes.")
    if not c.slug_valido(slug):
        col.aviso("pasta", f"o nome '{slug}' foge do padrão (minúsculas, números e hífen); alguns scripts podem recusá-lo.")
    col.nota(f"{len(ARQUIVOS_OBRIGATORIOS) - len(faltando)} de {len(ARQUIVOS_OBRIGATORIOS)} arquivos obrigatórios")


def checar_marcadores(col: Coletor, texto: str, vigente: bool = False) -> None:
    linhas = texto.splitlines()

    def onde(rx: re.Pattern) -> list[int]:
        return [n for n, linha in enumerate(linhas, 1) if rx.search(linha)]

    modelo = onde(RE_MODELO)
    if modelo:
        col.erro("modelo", f"sobrou um campo {{{{...}}}} do modelo sem preencher ({lista_de_linhas(modelo)}).")
    pendentes = onde(RE_PREENCHER)
    if pendentes:
        texto_msg = (f"{len(pendentes)} campo(s) ainda marcados com [PREENCHER] ({lista_de_linhas(pendentes)}). "
                     "Complete com a pessoa ou escreva 'não definido'.")
        (col.erro if vigente else col.aviso)("pendências", texto_msg)
    confirmar = onde(RE_A_CONFIRMAR)
    if confirmar:
        col.aviso("pendências", f"{len(confirmar)} item(ns) marcados como (a confirmar) ({lista_de_linhas(confirmar)}). "
                                "Confirme com a pessoa e tire a marca.")


def achar_secoes(texto: str, esperadas: list[str]):
    """Devolve ({esperada: (linha, corpo)}, [esperadas na ordem em que aparecem])."""
    achadas: dict[str, tuple[int, list[str]]] = {}
    ordem: list[str] = []
    normais = [(c.normalizar(e), e) for e in esperadas]
    for titulo, linha, corpo in c.secoes(texto):
        t = c.normalizar(titulo)
        for n, esperada in normais:
            if (t == n or t.startswith(n + " ")) and esperada not in achadas:
                achadas[esperada] = (linha, corpo)
                ordem.append(esperada)
                break
    return achadas, ordem


def avisar_secoes_vazias(col: Coletor, achadas: dict) -> None:
    for nome, (linha, corpo) in achadas.items():
        if not any(l.strip() for l in corpo):
            col.aviso(f"seção '{nome}'", f"está vazia (linha {linha}). Escreva o conteúdo ou 'não definido'.")


def checar_marca_md(col: Coletor, texto: str) -> None:
    achadas, ordem = achar_secoes(texto, SECOES_MARCA)
    faltam = [s for s in SECOES_MARCA if s not in achadas]
    for secao in faltam:
        col.erro(f"seção '{secao}'", "não encontrada. A marca.md precisa ter, nesta ordem: " + " · ".join(SECOES_MARCA) + ".")
    if ordem != [s for s in SECOES_MARCA if s in achadas]:
        col.erro("seções", "estão fora de ordem. A ordem certa é: " + " · ".join(SECOES_MARCA) + ".")
    elif not faltam:
        col.nota(f"{len(SECOES_MARCA)} seções na ordem certa")
    avisar_secoes_vazias(col, achadas)

    if "Diferenciais e provas autorizadas" in achadas:
        corpo = achadas["Diferenciais e provas autorizadas"][1]
        for tabela in c.encontrar_tabelas(corpo):
            cab = [c.normalizar(x) for x in tabela["cabecalho"]]
            if "origem" not in cab:
                continue
            posicao = cab.index("origem")
            for _, cel in tabela["linhas"]:
                primeira = cel[0] if cel else ""
                origem = cel[posicao].strip() if len(cel) > posicao else ""
                if primeira and "[PREENCHER" not in primeira and origem in ("", "-", "—", "–"):
                    col.aviso("provas", f"'{resumo(primeira)}' está sem origem. Prova sem origem não entra em post: "
                                        "peça a origem à pessoa ou tire da tabela.")
            break

    if "Fuso horário" in achadas:
        linhas = [l.strip() for l in achadas["Fuso horário"][1] if l.strip()]
        valor = re.sub(r"[`*_]", "", linhas[0]).strip() if linhas else ""
        if valor and "PREENCHER" not in valor and not RE_FUSO.match(valor):
            col.aviso("Fuso horário", f"'{valor}' não parece um fuso no formato Região/Cidade, como America/Sao_Paulo.")

    if "Links oficiais" in achadas:
        for linha in achadas["Links oficiais"][1]:
            for url in RE_URL.findall(linha):
                url = url.rstrip(".,;")
                if not urlparse(url).netloc:
                    col.aviso("Links oficiais", f"o endereço '{resumo(url)}' parece incompleto.")


def checar_regras_md(col: Coletor, texto: str) -> None:
    achadas, _ = achar_secoes(texto, SECOES_REGRAS)
    faltam = [s for s in SECOES_REGRAS if s not in achadas]
    for secao in faltam:
        col.erro(f"seção '{secao}'", "não encontrada. A regras.md precisa ter as seções: " + " · ".join(SECOES_REGRAS) + ".")
    if not faltam:
        col.nota(f"{len(SECOES_REGRAS)} seções obrigatórias")
    avisar_secoes_vazias(col, {k: v for k, v in achadas.items()
                               if k != "Quem pode ser citado e com qual autorização"})
    if "Quem pode ser citado e com qual autorização" in achadas:
        corpo = achadas["Quem pode ser citado e com qual autorização"][1]
        for tabela in c.encontrar_tabelas(corpo):
            cab = [c.normalizar(x) for x in tabela["cabecalho"]]
            if "data" not in cab:
                continue
            posicao = cab.index("data")
            for _, cel in tabela["linhas"]:
                data = cel[posicao] if len(cel) > posicao else ""
                if data and not c.data_valida(data):
                    col.aviso("autorizações", f"data inválida na tabela de autorizações: {data!r}. Use AAAA-MM-DD.")
            break


def checar_padrao_visual_md(col: Coletor, texto: str) -> None:
    if not texto.strip():
        col.erro("padrao-visual.md", "o arquivo está vazio. Ele precisa começar com o padrão recomendado do projeto.")
        return
    achadas, _ = achar_secoes(texto, SECOES_PADRAO_VISUAL)
    if "Padrão recomendado" not in achadas:
        col.erro("seção 'Padrão recomendado'", "não encontrada. O arquivo precisa começar com o padrão recomendado.")
    for secao in SECOES_PADRAO_VISUAL[1:]:
        if secao not in achadas:
            col.aviso(f"seção '{secao}'", "não encontrada (o modelo do projeto tem essa seção).")


def checar_feedback_md(col: Coletor, texto: str) -> None:
    tabelas = [t for t in c.encontrar_tabelas(texto.splitlines()) if c.eh_tabela_de_feedback(t)]
    if not tabelas:
        col.erro("tabela", "não encontrei a tabela de feedback com as colunas: | " + " | ".join(c.CABECALHO_FEEDBACK) + " |")
        return
    registros = 0
    for indice, cel in tabelas[0]["linhas"]:
        registros += 1
        onde = f"linha {indice + 1}"
        if len(cel) != 4:
            col.erro(onde, f"tem {len(cel)} colunas; o certo são 4 (para escrever uma barra vertical dentro do texto, use \\|).")
            continue
        data, frase, mudou, _arquivo = cel
        if not c.data_valida(data):
            col.erro(onde, f"data inválida: {data!r}. Use AAAA-MM-DD.")
        if not frase.strip():
            col.erro(onde, "falta a frase literal da pessoa.")
        if not mudou.strip():
            col.aviso(onde, "falta dizer o que mudou.")
    col.nota(f"{registros} registro(s)")


# ---------------------------------------------------------------------------
# visual.json
# ---------------------------------------------------------------------------

def checar_caminho_json(col: Coletor, campo: str, valor, extensoes: set[str] | None = None) -> bool:
    """Confere só o texto do caminho (a existência do arquivo é conferida na área assets)."""
    if not texto_nao_vazio(valor):
        col.erro(campo, "precisa ser um caminho de arquivo (texto), relativo à pasta da marca.")
        return False
    _, erro = c.caminho_dentro(Path("."), valor)
    if erro:
        col.erro(campo, f"{erro}. Valor: {valor!r}")
        return False
    if "\\" in valor:
        col.aviso(campo, "use / em vez de \\ nos caminhos, para funcionar em qualquer sistema.")
    if extensoes is not None and Path(valor).suffix.lower() not in extensoes:
        col.erro(campo, f"formato não aceito ({Path(valor).suffix or 'sem extensão'}). Aceitos: {', '.join(sorted(extensoes))}.")
        return False
    return True


def checar_visual(col: Coletor, dados) -> dict | None:
    if not isinstance(dados, dict):
        col.erro("visual.json", "o arquivo precisa ser um objeto JSON, começando com { e terminando com }.")
        return None
    for chave in dados:
        if chave not in CHAVES_VISUAL:
            col.aviso(chave, "campo desconhecido (erro de digitação?). Ele será ignorado.")
    for chave in ("versao_esquema", "nome_exibicao", "arroba", "proporcao_padrao", "cores", "numeracao", "rodape"):
        if chave not in dados:
            col.erro(chave, "campo obrigatório ausente.")

    versao = dados.get("versao_esquema")
    if "versao_esquema" in dados and (isinstance(versao, bool) or versao != 1):
        col.erro("versao_esquema", f"valor {versao!r} não reconhecido; esta versão do projeto usa 1.")
    if "nome_exibicao" in dados and not texto_nao_vazio(dados["nome_exibicao"]):
        col.erro("nome_exibicao", "precisa ser um texto não vazio (o nome que aparece no último slide).")
    if "arroba" in dados:
        arroba = dados["arroba"]
        if not isinstance(arroba, str):
            col.erro("arroba", "precisa ser um texto, como @meuperfil.")
        elif arroba == "":
            col.aviso("arroba", "está vazio. O último slide ficará sem o @ até a pessoa informar.")
        elif not c.RE_ARROBA.match(arroba):
            col.erro("arroba", f"{arroba!r} não é um @ válido: use @ seguido de letras, números, ponto ou sublinhado (até 30).")
    if "proporcao_padrao" in dados and dados["proporcao_padrao"] not in PROPORCOES:
        col.erro("proporcao_padrao", f"{dados['proporcao_padrao']!r} não é válida. Use \"4:5\" (1080x1350) ou \"1:1\" (1080x1080).")

    cores = dados.get("cores")
    if "cores" in dados:
        if not isinstance(cores, dict):
            col.erro("cores", "precisa ser um objeto com as seis cores.")
            cores = None
        else:
            validas = {}
            for chave in CHAVES_CORES:
                valor = cores.get(chave)
                if chave not in cores:
                    col.erro(f"cores.{chave}", "cor obrigatória ausente.")
                elif not isinstance(valor, str) or not c.RE_HEX.match(valor):
                    col.erro(f"cores.{chave}", f"{valor!r} não é uma cor válida. Use o formato #RRGGBB, por exemplo #0E7490.")
                else:
                    validas[chave] = c.hex_para_rgb(valor)
            for chave in cores:
                if chave not in CHAVES_CORES:
                    col.aviso(f"cores.{chave}", "cor desconhecida; será ignorada.")
            checar_contrastes(col, validas)
            modelo, _ = c.ler_json(c.PASTA_MODELOS / "visual.json")
            if isinstance(modelo, dict) and isinstance(modelo.get("cores"), dict) and not col.erros:
                if {k: str(v).lower() for k, v in cores.items()} == {k: str(v).lower() for k, v in modelo["cores"].items()}:
                    col.aviso("cores", "ainda são as cores padrão do modelo. Confirme com a pessoa ou sugira uma paleta "
                                       "a partir do logo (sugerir_cores.py).")

    fontes = dados.get("fontes")
    if fontes is not None:
        if not isinstance(fontes, dict):
            col.erro("fontes", "precisa ser null ou um objeto com titulo e texto.")
        else:
            for chave in fontes:
                if chave not in ("titulo", "texto"):
                    col.aviso(f"fontes.{chave}", "campo desconhecido; será ignorado.")
            for chave in ("titulo", "texto"):
                if fontes.get(chave) is not None:
                    checar_caminho_json(col, f"fontes.{chave}", fontes[chave], c.EXT_FONTE)

    logo = dados.get("logo")
    if logo is None:
        col.aviso("logo", "não definido: as artes saem sem logo. Se a pessoa ainda não tem logo, gere um provisório só com "
                          "o nome (gerar_logo_texto.py).")
    elif not isinstance(logo, dict):
        col.erro("logo", "precisa ser um objeto com fundo_claro, fundo_escuro, posicao e largura_px (ou null, para artes sem logo).")
    else:
        for chave in logo:
            if chave not in CHAVES_LOGO:
                col.aviso(f"logo.{chave}", "campo desconhecido; será ignorado.")
        for chave in ("fundo_claro", "fundo_escuro"):
            if chave not in logo:
                col.erro(f"logo.{chave}", "campo obrigatório ausente.")
            else:
                checar_caminho_json(col, f"logo.{chave}", logo[chave])
        if logo.get("posicao") not in POSICOES_LOGO:
            col.erro("logo.posicao", f"{logo.get('posicao')!r} não é válida. Use: {', '.join(POSICOES_LOGO)}.")
        largura = logo.get("largura_px")
        if not eh_inteiro(largura) or largura <= 0:
            col.erro("logo.largura_px", f"{largura!r} não é válida. Use um número inteiro maior que zero (o padrão é 140).")
        elif largura < 40 or largura > 400:
            col.aviso("logo.largura_px", f"{int(largura)} px está fora do intervalo de 40 a 400 px; o gerador de artes usa o limite mais próximo.")

    checar_tipografia(col, dados.get("tipografia"))

    if dados.get("avatar") is not None:
        checar_caminho_json(col, "avatar", dados["avatar"], c.EXT_IMAGEM)

    for chave in ("numeracao", "rodape"):
        if chave in dados:
            if not isinstance(dados[chave], bool):
                col.erro(chave, f"precisa ser true ou false (sem aspas); encontrei {dados[chave]!r}.")
            elif dados[chave]:
                col.aviso(chave, "está ligado, o que contraria o padrão recomendado. Confirme que a pessoa pediu isso "
                                 "(deve haver uma linha em feedback.md).")
    return dados


def checar_tipografia(col: Coletor, tipografia) -> None:
    """Campo opcional aceito pelo gerador: tamanhos de letra [menor, maior] em px, de 20 a 110."""
    if tipografia is None:
        return
    if not isinstance(tipografia, dict):
        col.erro("tipografia", "precisa ser um objeto com titulo e apoio, cada um como [menor, maior] em px.")
        return
    for chave, par in tipografia.items():
        if chave not in ("titulo", "apoio"):
            col.aviso(f"tipografia.{chave}", "campo desconhecido; será ignorado.")
        elif not (isinstance(par, list) and len(par) == 2 and all(eh_inteiro(x) for x in par)
                  and 20 <= par[0] <= par[1] <= 110):
            col.erro(f"tipografia.{chave}", f"{par!r} não é válido. Use [menor, maior] em px, de 20 a 110 (exemplo: [44, 56]).")


def checar_contrastes(col: Coletor, cores: dict) -> None:
    pares = [("texto", "fundo", 4.5), ("suave", "fundo", 4.5), ("destaque", "fundo", 3.0),
             ("texto_sobre_escuro", "fundo_escuro", 4.5), ("destaque", "fundo_escuro", 3.0)]
    for frente, fundo, minimo in pares:
        if frente in cores and fundo in cores:
            razao = c.contraste(cores[frente], cores[fundo])
            if razao < minimo:
                col.aviso(f"cores.{frente}", f"contraste de {c.formatar_numero(razao)}:1 com '{fundo}' "
                                             f"({c.rgb_para_hex(cores[frente])} sobre {c.rgb_para_hex(cores[fundo])}); "
                                             f"o mínimo recomendado é {c.formatar_numero(minimo)}:1. Escolha um tom mais contrastante.")


# ---------------------------------------------------------------------------
# estrategia.json
# ---------------------------------------------------------------------------

def checar_estrategia(col: Coletor, dados, texto_bruto: str) -> None:
    if not isinstance(dados, dict):
        col.erro("estrategia.json", "o arquivo precisa ser um objeto JSON, começando com { e terminando com }.")
        return
    for chave in dados:
        if chave not in CHAVES_ESTRATEGIA:
            col.aviso(chave, "campo desconhecido (erro de digitação?). Ele será ignorado.")
    for chave in ("versao_esquema", "atualizado_em", "status", "objetivo", "pilares", "ritmo", "metas", "funil", "movimentos"):
        if chave not in dados:
            col.erro(chave, "campo obrigatório ausente.")

    versao = dados.get("versao_esquema")
    if "versao_esquema" in dados and (isinstance(versao, bool) or versao != 1):
        col.erro("versao_esquema", f"valor {versao!r} não reconhecido; esta versão do projeto usa 1.")

    status = dados.get("status")
    vigente = status == "vigente"
    if "status" in dados and status not in ("rascunho", "vigente"):
        col.erro("status", f"{status!r} não é válido. Use \"rascunho\" (até a pessoa aprovar) ou \"vigente\".")

    atualizado = dados.get("atualizado_em")
    if "atualizado_em" in dados:
        if not c.data_valida(atualizado):
            col.erro("atualizado_em", f"{atualizado!r} não é uma data válida. Use AAAA-MM-DD.")
            atualizado = None
        elif atualizado > c.hoje():
            col.aviso("atualizado_em", f"{atualizado} está no futuro.")

    if "objetivo" in dados and not texto_nao_vazio(dados["objetivo"]):
        (col.erro if vigente else col.aviso)("objetivo", "está vazio. Escreva uma frase com o que o perfil precisa gerar nos próximos meses.")

    checar_marcadores(col, texto_bruto, vigente)
    checar_pilares(col, dados.get("pilares"), "pilares" in dados, vigente)
    checar_ritmo(col, dados.get("ritmo"), "ritmo" in dados, vigente)
    checar_metas(col, dados.get("metas"), "metas" in dados, vigente, atualizado)

    funil = dados.get("funil")
    if "funil" in dados:
        if not isinstance(funil, dict):
            col.erro("funil", "precisa ser um objeto com atracao, relacionamento e conversao.")
        else:
            for chave in ("atracao", "relacionamento", "conversao"):
                if not texto_nao_vazio(funil.get(chave)):
                    (col.erro if vigente else col.aviso)(f"funil.{chave}", "está vazio. Escreva em uma frase como esta etapa funciona.")
            for chave in funil:
                if chave not in ("atracao", "relacionamento", "conversao"):
                    col.aviso(f"funil.{chave}", "campo desconhecido; será ignorado.")

    movimentos = dados.get("movimentos")
    if "movimentos" in dados:
        if not isinstance(movimentos, list):
            col.erro("movimentos", "precisa ser uma lista.")
        else:
            for i, m in enumerate(movimentos, 1):
                onde = f"movimentos[{i}]"
                if not isinstance(m, dict):
                    col.erro(onde, "precisa ser um objeto com o_que, indicador e ate.")
                    continue
                for chave in ("o_que", "indicador"):
                    if not texto_nao_vazio(m.get(chave)):
                        col.erro(f"{onde}.{chave}", "precisa ser um texto não vazio.")
                if not c.data_valida(m.get("ate")):
                    col.erro(f"{onde}.ate", f"{m.get('ate')!r} não é uma data válida. Use AAAA-MM-DD.")


def checar_pilares(col: Coletor, pilares, presente: bool, vigente: bool) -> None:
    if not presente:
        return
    if not isinstance(pilares, list) or not pilares:
        col.erro("pilares", "precisa ser uma lista com pelo menos um pilar de conteúdo.")
        return
    ids: set[str] = set()
    soma = 0.0
    soma_valida = True
    for i, p in enumerate(pilares, 1):
        onde = f"pilares[{i}]"
        if not isinstance(p, dict):
            col.erro(onde, "precisa ser um objeto com id, nome, descricao e peso.")
            soma_valida = False
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not c.RE_SLUG.match(pid):
            col.erro(f"{onde}.id", f"{pid!r} não é válido: o id é um slug, só com minúsculas, números e hífen, "
                                   f"sem sublinhado nem espaço (exemplo: bastidores-equipe).{dica_de_slug(pid)}")
        elif pid in ids:
            col.erro(f"{onde}.id", f"'{pid}' está repetido. Cada pilar precisa de um id único.")
        else:
            ids.add(pid)
        if not texto_nao_vazio(p.get("nome")):
            col.erro(f"{onde}.nome", "precisa ser um texto não vazio.")
        if not isinstance(p.get("descricao"), str):
            col.erro(f"{onde}.descricao", "precisa ser um texto.")
        elif not p["descricao"].strip():
            col.aviso(f"{onde}.descricao", "está vazia. Diga do que o pilar fala e por que importa para o público.")
        peso = p.get("peso")
        if not eh_numero(peso) or peso < 0 or peso > 100:
            col.erro(f"{onde}.peso", f"{peso!r} não é válido. Use um número de 0 a 100.")
            soma_valida = False
        else:
            soma += peso
    if soma_valida and abs(soma - 100) > 1e-6:
        col.erro("pilares", f"os pesos somam {c.formatar_numero(soma, 0 if float(soma).is_integer() else 1)}; precisam somar 100.")


def checar_ritmo(col: Coletor, ritmo, presente: bool, vigente: bool) -> None:
    if not presente:
        return
    if not isinstance(ritmo, dict):
        col.erro("ritmo", "precisa ser um objeto com posts_por_semana e formatos.")
        return
    posts = ritmo.get("posts_por_semana")
    if not eh_numero(posts) or posts <= 0:
        nao_definido = posts == 0 and not isinstance(posts, bool)
        pendente = " Ainda não foi definido: combine com a pessoa quantos posts por semana ela consegue manter." if nao_definido else ""
        col.erro("ritmo.posts_por_semana", f"{posts!r} não é válido: precisa ser um número maior que zero, e aceita decimal "
                                           f"(exemplos: 3 ou 2.5).{pendente}")
        posts = None
    elif posts > 14:
        col.aviso("ritmo.posts_por_semana", f"{posts:g} posts por semana é muito mais do que a maioria consegue manter. Confirme com a pessoa.")
    formatos = ritmo.get("formatos")
    if not isinstance(formatos, dict):
        col.erro("ritmo.formatos", "precisa ser um objeto com carrossel, post_unico e reel.")
        return
    total = 0
    for chave, valor in formatos.items():
        if chave not in FORMATOS:
            col.erro(f"ritmo.formatos.{chave}", f"formato desconhecido. Use: {', '.join(FORMATOS)}.")
        elif not eh_inteiro(valor) or valor < 0:
            col.erro(f"ritmo.formatos.{chave}", f"{valor!r} não é válido. Use um número inteiro, 0 ou maior.")
        else:
            total += int(valor)
    if posts is not None and total != posts and all(k in FORMATOS for k in formatos):
        col.aviso("ritmo.formatos", f"a soma dos formatos ({total}) é diferente de posts_por_semana ({posts:g}).")


def checar_metas(col: Coletor, metas, presente: bool, vigente: bool, atualizado) -> None:
    if not presente:
        return
    if not isinstance(metas, list):
        col.erro("metas", "precisa ser uma lista (pode estar vazia enquanto a estratégia é rascunho).")
        return
    if not metas:
        (col.erro if vigente else col.aviso)("metas", "nenhuma meta definida. Sem metas, o acompanhamento de resultados fica sem referência.")
    ids: set[str] = set()
    for i, m in enumerate(metas, 1):
        onde = f"metas[{i}]"
        if not isinstance(m, dict):
            col.erro(onde, "precisa ser um objeto com id, descricao, indicador, base, alvo e prazo.")
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not c.RE_SLUG.match(mid):
            col.erro(f"{onde}.id", f"{mid!r} não é válido: o id é um slug, só com minúsculas, números e hífen, "
                                   f"sem sublinhado nem espaço (exemplo: novos-seguidores).{dica_de_slug(mid)}")
        elif mid in ids:
            col.erro(f"{onde}.id", f"'{mid}' está repetido.")
        else:
            ids.add(mid)
        if not texto_nao_vazio(m.get("descricao")):
            col.erro(f"{onde}.descricao", "precisa ser um texto não vazio.")
        if m.get("indicador") not in INDICADORES:
            col.erro(f"{onde}.indicador", f"{m.get('indicador')!r} não é válido. Use: {', '.join(INDICADORES)}.")
        numeros_ok = True
        for chave in ("base", "alvo"):
            v = m.get(chave)
            if not eh_numero(v) or v < 0:
                col.erro(f"{onde}.{chave}", f"{v!r} não é válido. Use um número, 0 ou maior (sem aspas).")
                numeros_ok = False
        if numeros_ok:
            if m["base"] == 0 and m["alvo"] == 0:
                col.aviso(onde, "base e alvo estão em 0. Preencha com a pessoa ou tire a meta.")
            elif m["base"] == m["alvo"]:
                col.aviso(onde, "o alvo é igual à base; a meta não pede nenhuma mudança.")
        prazo = m.get("prazo")
        if not c.data_valida(prazo):
            col.erro(f"{onde}.prazo", f"{prazo!r} não é uma data válida. Use AAAA-MM-DD.")
        elif atualizado and prazo < atualizado:
            col.aviso(f"{onde}.prazo", f"{prazo} é anterior a atualizado_em ({atualizado}); o prazo já passou.")
        # Campos opcionais do contrato: o valor atual que a pessoa informa para um indicador 'manual' e a data dele.
        if "atual" in m and (not eh_numero(m["atual"]) or m["atual"] < 0):
            col.erro(f"{onde}.atual", f"{m['atual']!r} não é válido. Use um número, 0 ou maior (sem aspas).")
        if "atual_em" in m and not c.data_valida(m["atual_em"]):
            col.erro(f"{onde}.atual_em", f"{m['atual_em']!r} não é uma data válida. Use AAAA-MM-DD.")
        if m.get("indicador") == "manual" and "atual" not in m:
            col.aviso(onde, "indicador 'manual' sem o campo 'atual': o acompanhamento mostrará 'não medido' até a pessoa "
                            "informar o valor atual (e a data, em 'atual_em').")


# ---------------------------------------------------------------------------
# assets
# ---------------------------------------------------------------------------

def checar_assets(col: Coletor, marca_dir: Path, visual) -> None:
    if not isinstance(visual, dict):
        col.erro("assets", "não consegui conferir os assets porque o visual.json está ausente ou inválido.")
        return
    if c.importar_pillow() is None:
        col.aviso("Pillow", c.MSG_SEM_PILLOW + ". Sem ele, só confiro se os arquivos existem.")
    cores = {}
    if isinstance(visual.get("cores"), dict):
        for chave in ("fundo", "fundo_escuro"):
            valor = visual["cores"].get(chave)
            if isinstance(valor, str) and c.RE_HEX.match(valor):
                cores[chave] = c.hex_para_rgb(valor)
    logo = visual.get("logo") if isinstance(visual.get("logo"), dict) else {}
    largura_usada = logo.get("largura_px") if eh_inteiro(logo.get("largura_px")) else 140

    for chave, fundo, dica in (("fundo_claro", "fundo", "versão com letras escuras ou coloridas"),
                               ("fundo_escuro", "fundo_escuro", "versão com letras claras ou brancas")):
        caminho_texto = logo.get(chave)
        if not isinstance(caminho_texto, str):
            continue
        caminho, erro = c.caminho_dentro(marca_dir, caminho_texto)
        campo = f"logo.{chave}"
        if erro:
            continue  # o texto do caminho já foi criticado na área visual
        if not caminho.is_file():
            col.erro(campo, f"arquivo não encontrado: {caminho_texto}. Coloque o logo nessa pasta, com esse nome "
                            f"(ou ajuste o caminho em visual.json). Precisa ser a {dica}.")
            continue
        if caminho.suffix.lower() == ".svg":
            col.erro(campo, "SVG não é aceito. Exporte o logo como PNG com fundo transparente.")
            continue
        if caminho.suffix.lower() not in c.EXT_IMAGEM:
            col.erro(campo, f"formato não aceito ({caminho.suffix or 'sem extensão'}). Use PNG (de preferência), JPG ou WebP.")
            continue
        if c.importar_pillow() is None:
            continue
        imagem, erro = c.abrir_imagem(caminho)
        if erro:
            col.erro(campo, f"{caminho_texto}: {erro}.")
            continue
        largura, altura = imagem.size
        minimo = int(largura_usada) * 2
        if largura < minimo:
            col.aviso(campo, f"tem só {largura} px de largura; para ficar nítido, use pelo menos {minimo} px "
                             f"(o dobro da largura usada na arte, {int(largura_usada)} px).")
        if not c.tem_transparencia(imagem):
            col.aviso(campo, "não tem fundo transparente; o logo aparecerá dentro de um retângulo. Prefira PNG com fundo transparente.")
        elif fundo in cores:
            pixels = [p for p in c.pixels_rgba(imagem) if p[3] >= 128]
            if not pixels:
                col.erro(campo, "o logo está vazio ou totalmente transparente.")
            else:
                legiveis = sum(1 for r, g, b, _ in pixels if c.contraste((r, g, b), cores[fundo]) >= 3.0)
                fracao = legiveis / len(pixels)
                if fracao < 0.5:
                    col.aviso(campo, f"quase não aparece sobre o fundo {c.rgb_para_hex(cores[fundo])}: só "
                                     f"{round(fracao * 100)}% do desenho tem contraste suficiente. Use a {dica}.")
        col.nota(f"{chave}: {largura}x{altura} px")

    if logo.get("fundo_claro") and logo.get("fundo_claro") == logo.get("fundo_escuro"):
        col.aviso("logo", "o mesmo arquivo está nos dois campos. Confirme que ele funciona sobre fundo claro e sobre fundo escuro.")

    avatar = visual.get("avatar")
    if isinstance(avatar, str):
        caminho, erro = c.caminho_dentro(marca_dir, avatar)
        if not erro:
            if not caminho.is_file():
                col.erro("avatar", f"arquivo não encontrado: {avatar}.")
            elif c.importar_pillow() is not None:
                imagem, erro = c.abrir_imagem(caminho)
                if erro:
                    col.erro("avatar", f"{avatar}: {erro}.")
                elif max(imagem.size) / max(1, min(imagem.size)) > 1.1:
                    col.aviso("avatar", f"tem proporção {imagem.size[0]}x{imagem.size[1]}; prefira uma imagem quadrada.")

    fontes = visual.get("fontes")
    if isinstance(fontes, dict):
        for chave in ("titulo", "texto"):
            valor = fontes.get(chave)
            if not isinstance(valor, str):
                continue
            caminho, erro = c.caminho_dentro(marca_dir, valor)
            if erro:
                continue
            if not caminho.is_file():
                col.erro(f"fontes.{chave}", f"arquivo não encontrado: {valor}.")
                continue
            mod = c.importar_pillow()
            if mod is None:
                continue
            try:
                fonte = mod[2].truetype(str(caminho), 40)
            except OSError:
                col.erro(f"fontes.{chave}", f"{valor}: a fonte não abre (arquivo corrompido ou formato não suportado).")
                continue
            ausentes = c.glifos_ausentes(fonte, c.ACENTOS_PT)
            if ausentes:
                col.aviso(f"fontes.{chave}", "a fonte não tem estes caracteres do português: " + " ".join(ausentes) +
                                             ". Textos com eles sairiam com quadradinhos.")

    fotos = marca_dir / "assets" / "fotos"
    if fotos.is_dir():
        validas = 0
        for arquivo in sorted(fotos.rglob("*"))[:500]:
            if not arquivo.is_file() or arquivo.name.startswith("."):
                continue
            nome = arquivo.relative_to(marca_dir).as_posix()
            if arquivo.suffix.lower() not in c.EXT_IMAGEM:
                col.aviso(nome, "não é uma imagem (PNG, JPG ou WebP); será ignorado.")
            elif c.importar_pillow() is not None:
                try:
                    with c.importar_pillow()[0].open(arquivo) as im:
                        im.verify()
                    validas += 1
                except Exception:
                    col.aviso(nome, "não é uma imagem válida (o arquivo pode estar corrompido).")
        if c.importar_pillow() is not None:
            col.nota(f"{validas} foto(s) válida(s) em assets/fotos/")


# ---------------------------------------------------------------------------
# segredos
# ---------------------------------------------------------------------------

def checar_segredos(col: Coletor, marca_dir: Path) -> None:
    lidos = 0
    for pasta, subpastas, arquivos in os.walk(marca_dir):
        subpastas[:] = [p for p in subpastas if p not in (".git", "__pycache__", "node_modules")]
        for nome in arquivos:
            caminho = Path(pasta) / nome
            rel = caminho.relative_to(marca_dir).as_posix()
            if nome == ".env" or nome.endswith((".env", ".pem", ".key")):
                col.erro(rel, "arquivo de credencial dentro da pasta da marca. Credenciais ficam fora do projeto, em "
                              "~/.config/estudio-de-conteudo/<marca>/ (veja a skill publicar-instagram). Mova o arquivo.")
                continue
            if caminho.suffix.lower() not in EXTENSOES_TEXTO:
                continue
            try:
                if caminho.stat().st_size > LIMITE_LEITURA:
                    continue
                linhas = caminho.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            lidos += 1
            for numero, linha in enumerate(linhas, 1):
                if c.IGNORAR_LINHA in linha:
                    continue
                for rotulo, rx in c.SEGREDOS:
                    if rx.search(linha):
                        col.erro(f"{rel} linha {numero}", f"parece conter {rotulo} (o valor não é mostrado). "
                                                         "Apague-o do arquivo e gere um novo, porque ele pode ter sido exposto.")
                        break
    col.nota(f"{lidos} arquivo(s) de texto lido(s)")


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def validar(marca_dir: Path, slug: str, areas: list[str]) -> list[Coletor]:
    resultado: list[Coletor] = []
    com_arquivos = "arquivos" in areas

    if com_arquivos:
        col = Coletor("arquivos")
        checar_arquivos(col, marca_dir, slug)
        resultado.append(col)

    if "textos" in areas:
        for nome, funcao in (("marca.md", checar_marca_md), ("regras.md", checar_regras_md),
                             ("padrao-visual.md", checar_padrao_visual_md), ("feedback.md", checar_feedback_md)):
            col = Coletor(nome)
            texto = ler_ou_reportar(col, marca_dir / nome, not com_arquivos)
            if texto is not None:
                funcao(col, texto)
                checar_marcadores(col, texto)
            resultado.append(col)

    visual = None
    if "visual" in areas or "assets" in areas:
        col_visual = Coletor("visual.json")
        visual = ler_json_ou_reportar(col_visual, marca_dir / "visual.json", not com_arquivos)
        if "visual" in areas:
            if visual is not None:
                checar_visual(col_visual, visual)
                texto_bruto, _ = c.ler_texto(marca_dir / "visual.json")
                checar_marcadores(col_visual, texto_bruto or "")
            resultado.append(col_visual)

    if "estrategia" in areas:
        col = Coletor("estrategia.json")
        dados = ler_json_ou_reportar(col, marca_dir / "estrategia.json", not com_arquivos)
        if dados is not None:
            texto_bruto, _ = c.ler_texto(marca_dir / "estrategia.json")
            checar_estrategia(col, dados, texto_bruto or "")
        resultado.append(col)

    if "assets" in areas:
        col = Coletor("assets")
        if visual is None:
            col.erro("assets", "não consegui conferir os assets porque o visual.json está ausente ou inválido "
                               "(rode a área 'visual' para ver o motivo).")
        else:
            checar_assets(col, marca_dir, visual)
        resultado.append(col)

    if "segredos" in areas:
        col = Coletor("segredos")
        checar_segredos(col, marca_dir)
        resultado.append(col)
    return resultado


def imprimir(slug: str, marca_dir: Path, raiz: Path, resultado: list[Coletor], estrito: bool) -> bool:
    print(f"Marca: {slug} · pasta: {c.mostrar_caminho(marca_dir, raiz)}/")
    erros = avisos = 0
    for col in resultado:
        erros += len(col.erros)
        avisos += len(col.avisos)
        falhou = bool(col.erros) or (estrito and bool(col.avisos))
        notas = f"  ({'; '.join(col.notas)})" if col.notas else ""
        print(f"{'FALHA' if falhou else 'OK':<5} {col.nome}{notas}")
        for m in col.msgs:
            print(f"  {m.nivel.upper():<6} {m.campo}: {m.texto}")
    print(f"Resumo: {len(resultado)} área(s) verificada(s), {erros} erro(s), {avisos} aviso(s).")
    falhou = erros > 0 or (estrito and avisos > 0)
    if falhou:
        print("Corrija os erros antes de gerar artes ou publicar." if erros else "Há avisos e o modo --estrito está ligado.")
    return falhou


def montar_parser() -> c.ParserPT:
    parser = c.criar_parser(
        "validar_marca.py",
        "Confere a pasta de uma marca contra o contrato do projeto (docs/arquitetura.md): arquivos obrigatórios, "
        "seções dos textos, campos e tipos de visual.json e estrategia.json, assets (logo, avatar, fontes, fotos) "
        "e segredos esquecidos. Só lê arquivos; não altera nada.",
        ["python -X utf8 skills/configurar-marca/scripts/validar_marca.py --marca exemplo",
         "python -X utf8 skills/configurar-marca/scripts/validar_marca.py --marca minha-marca --so assets",
         "python -X utf8 skills/configurar-marca/scripts/validar_marca.py --marca minha-marca --so visual estrategia --estrito"],
        "Saída: 0 = sem erros; 1 = há erros (ou avisos, com --estrito); 2 = marca não encontrada.",
    )
    c.opcoes_marca_e_raiz(parser)
    parser.add_argument("--so", nargs="+", choices=AREAS, metavar="ÁREA",
                        help="confere só estas áreas: " + ", ".join(AREAS) + " (padrão: todas)")
    parser.add_argument("--estrito", action="store_true", help="trata os avisos como erros")
    return parser


def main(argv: list[str] | None = None) -> int:
    c.configurar_saida()
    args = montar_parser().parse_args(argv)
    raiz = c.pasta_raiz(args.raiz)
    try:
        slug, marca_dir = c.resolver_marca(raiz, args.marca)
    except c.ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    areas = [a for a in AREAS if a in (args.so or AREAS)]
    resultado = validar(marca_dir, slug, areas)
    falhou = imprimir(slug, marca_dir, raiz, resultado, args.estrito)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
