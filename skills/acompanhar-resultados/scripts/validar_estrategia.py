"""Valida o estrategia.json de uma marca pelo contrato do projeto.

Uso, a partir da raiz do projeto:
    python -X utf8 skills/acompanhar-resultados/scripts/validar_estrategia.py --marca minha-marca
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import (  # noqa: E402
    ErroUso,
    caminho_curto,
    configurar_saida,
    criar_parser,
    fmt_data,
    ler_data,
    ler_data_arg,
    RE_SLUG,
    ler_json_arquivo,
    raiz_do_projeto,
    resolver_marca,
)

AJUDA = """\
validar_estrategia.py - confere se o estrategia.json de uma marca segue o contrato.

Uso:
  python -X utf8 skills/acompanhar-resultados/scripts/validar_estrategia.py [opções]

Opções:
  --marca NOME     marca a conferir (pasta em marcas/). Se houver só uma marca além
                   de 'exemplo', ela é usada sem perguntar. A marca fictícia 'exemplo'
                   só é usada com --marca exemplo.
  --arquivo CAMINHO
                   confere este arquivo em vez do estrategia.json da marca. Serve para
                   testar uma proposta antes de gravá-la.
  --hoje AAAA-MM-DD
                   data usada nos avisos de prazo vencido (padrão: hoje).
  --raiz PASTA     raiz do projeto (padrão: a pasta que contém skills/).
  --ajuda, -h      mostra esta ajuda.

O que confere: versão do esquema, datas, status, pilares (pesos somam 100), ritmo,
metas (indicador, base, alvo, prazo), funil e movimentos.

Código de saída: 0 = válido (pode haver avisos); 1 = há erros no arquivo;
2 = erro de uso (marca não encontrada, argumento inválido).
"""

STATUS = ("rascunho", "vigente")
INDICADORES = (
    "seguidores",
    "posts_por_semana",
    "alcance_medio",
    "salvamentos_medio",
    "comentarios_medio",
    "compartilhamentos_medio",
    "manual",
)
FORMATOS = ("carrossel", "post_unico", "reel")
CAMPOS_CONHECIDOS = {
    "versao_esquema", "atualizado_em", "status", "objetivo", "pilares", "ritmo", "metas", "funil", "movimentos",
}


def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def _inteiro(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _texto(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _marcadores_de_preenchimento(obj, caminho: str = "") -> list[str]:
    if isinstance(obj, str):
        return [caminho or "(raiz)"] if "[PREENCHER" in obj else []
    achados: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            achados += _marcadores_de_preenchimento(v, f"{caminho}.{k}" if caminho else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            achados += _marcadores_de_preenchimento(v, f"{caminho}[{i}]")
    return achados


def validar_estrategia(e, hoje: date) -> tuple[list[str], list[str]]:
    erros: list[str] = []
    avisos: list[str] = []
    if not isinstance(e, dict):
        return ["O arquivo precisa ser um objeto JSON (começa com { e termina com })."], avisos
    for onde in _marcadores_de_preenchimento(e):
        avisos.append(f"{onde}: ainda tem o texto [PREENCHER]; complete com a pessoa antes de usar.")

    for chave in e:
        if chave not in CAMPOS_CONHECIDOS:
            avisos.append(f"{chave}: campo desconhecido; será ignorado.")

    if e.get("versao_esquema") != 1 or isinstance(e.get("versao_esquema"), bool):
        erros.append("versao_esquema: precisa ser o número 1.")

    atualizado = e.get("atualizado_em")
    if not isinstance(atualizado, str) or ler_data(atualizado) is None:
        erros.append("atualizado_em: precisa ser uma data no formato AAAA-MM-DD.")
    elif ler_data(atualizado) > hoje:
        avisos.append(f"atualizado_em: a data {atualizado} está no futuro.")

    status = e.get("status")
    if status not in STATUS:
        erros.append("status: use 'rascunho' ou 'vigente'.")
    elif status == "rascunho":
        avisos.append("status: 'rascunho'. As metas valem como sugestão até a pessoa aprovar; depois o status vira 'vigente'.")

    if not _texto(e.get("objetivo")):
        erros.append("objetivo: escreva uma frase dizendo o que o perfil precisa gerar nos próximos meses.")

    _validar_pilares(e.get("pilares"), erros)
    _validar_ritmo(e.get("ritmo"), erros, avisos)
    _validar_metas(e.get("metas"), e.get("ritmo"), hoje, erros, avisos)
    _validar_funil(e.get("funil"), erros)
    _validar_movimentos(e.get("movimentos"), hoje, erros, avisos)
    return erros, avisos


def _validar_pilares(pilares, erros: list[str]) -> None:
    if not isinstance(pilares, list) or not pilares:
        erros.append("pilares: precisa ser uma lista com pelo menos um pilar.")
        return
    ids: set[str] = set()
    soma = 0.0
    pesos_ok = True
    for i, p in enumerate(pilares):
        onde = f"pilares[{i}]"
        if not isinstance(p, dict):
            erros.append(f"{onde}: precisa ser um objeto com id, nome, descricao e peso.")
            pesos_ok = False
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not RE_SLUG.match(pid):
            erros.append(f"{onde}.id: o id é um slug: letras minúsculas sem acento, números e hífen entre as palavras (ex.: educativo ou prazo-curto). Sem sublinhado.")
        elif pid in ids:
            erros.append(f"{onde}.id: '{pid}' já foi usado em outro pilar.")
        else:
            ids.add(pid)
        if not _texto(p.get("nome")):
            erros.append(f"{onde}.nome: falta o nome do pilar.")
        if not _texto(p.get("descricao")):
            erros.append(f"{onde}.descricao: falta a descrição do pilar.")
        peso = p.get("peso")
        if not _numero(peso) or peso < 0:
            erros.append(f"{onde}.peso: precisa ser um número maior ou igual a 0.")
            pesos_ok = False
        else:
            soma += peso
    if pesos_ok and abs(soma - 100) > 1e-6:
        erros.append(f"pilares: os pesos somam {soma:g}, mas precisam somar 100.")


def _validar_ritmo(ritmo, erros: list[str], avisos: list[str]) -> None:
    if not isinstance(ritmo, dict):
        erros.append("ritmo: precisa ser um objeto com posts_por_semana e formatos.")
        return
    ppw = ritmo.get("posts_por_semana")
    if not _numero(ppw) or ppw <= 0:
        erros.append("ritmo.posts_por_semana: precisa ser um número maior que zero (decimal vale, como 2.5).")
    formatos = ritmo.get("formatos")
    if not isinstance(formatos, dict):
        erros.append("ritmo.formatos: precisa ser um objeto como {\"carrossel\": 2, \"post_unico\": 1, \"reel\": 0}.")
        return
    soma = 0
    soma_ok = True
    for nome, qtd in formatos.items():
        if nome not in FORMATOS:
            erros.append(f"ritmo.formatos: '{nome}' não existe; use carrossel, post_unico ou reel.")
            soma_ok = False
        elif not _inteiro(qtd) or qtd < 0:
            erros.append(f"ritmo.formatos.{nome}: precisa ser um número inteiro maior ou igual a 0.")
            soma_ok = False
        else:
            soma += qtd
    if soma_ok and _numero(ppw) and ppw > 0 and soma != ppw:
        avisos.append(f"ritmo: os formatos somam {soma} por semana, mas posts_por_semana é {ppw:g}.")


def _validar_metas(metas, ritmo, hoje: date, erros: list[str], avisos: list[str]) -> None:
    if not isinstance(metas, list):
        erros.append("metas: precisa ser uma lista (pode ficar vazia, mas então o painel não mostra metas).")
        return
    if not metas:
        avisos.append("metas: a lista está vazia; o painel não terá o que acompanhar.")
    ids: set[str] = set()
    for i, m in enumerate(metas):
        onde = f"metas[{i}]"
        if not isinstance(m, dict):
            erros.append(f"{onde}: precisa ser um objeto com id, descricao, indicador, base, alvo e prazo.")
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not RE_SLUG.match(mid):
            erros.append(f"{onde}.id: o id é um slug: letras minúsculas sem acento, números e hífen entre as palavras (ex.: seguidores ou posts-por-semana). Sem sublinhado.")
        elif mid in ids:
            erros.append(f"{onde}.id: '{mid}' já foi usado em outra meta.")
        else:
            ids.add(mid)
        if not _texto(m.get("descricao")):
            erros.append(f"{onde}.descricao: falta a descrição da meta.")
        ind = m.get("indicador")
        if ind not in INDICADORES:
            erros.append(f"{onde}.indicador: use um destes: {', '.join(INDICADORES)}.")
        base, alvo = m.get("base"), m.get("alvo")
        for campo, valor in (("base", base), ("alvo", alvo)):
            if not _numero(valor) or valor < 0:
                erros.append(f"{onde}.{campo}: precisa ser um número maior ou igual a 0.")
        if _numero(base) and _numero(alvo) and base == alvo:
            avisos.append(f"{onde}: base e alvo são iguais ({base:g}); não há o que perseguir.")
        prazo = m.get("prazo")
        d = ler_data(prazo) if isinstance(prazo, str) else None
        if d is None:
            erros.append(f"{onde}.prazo: precisa ser uma data no formato AAAA-MM-DD.")
        elif d < hoje:
            avisos.append(f"{onde}.prazo: {fmt_data(d)} já passou. Defina um novo prazo ou encerre a meta.")
        if "atual" in m and (not _numero(m["atual"]) or m["atual"] < 0):
            erros.append(f"{onde}.atual: precisa ser um número maior ou igual a 0.")
        if "atual_em" in m and (not isinstance(m["atual_em"], str) or ler_data(m["atual_em"]) is None):
            erros.append(f"{onde}.atual_em: precisa ser uma data no formato AAAA-MM-DD.")
        if ind == "manual" and "atual" not in m:
            avisos.append(f"{onde}: indicador 'manual' sem o campo 'atual'; o painel mostrará 'não medido' até a pessoa informar o valor.")
        if (
            ind == "posts_por_semana"
            and isinstance(ritmo, dict)
            and _numero(ritmo.get("posts_por_semana"))
            and _numero(alvo)
            and alvo != ritmo["posts_por_semana"]
        ):
            avisos.append(
                f"{onde}: o alvo ({alvo:g} posts por semana) difere de ritmo.posts_por_semana ({ritmo['posts_por_semana']:g})."
            )


def _validar_funil(funil, erros: list[str]) -> None:
    if not isinstance(funil, dict):
        erros.append("funil: precisa ser um objeto com atracao, relacionamento e conversao.")
        return
    for etapa in ("atracao", "relacionamento", "conversao"):
        if not _texto(funil.get(etapa)):
            erros.append(f"funil.{etapa}: falta o texto dizendo o que fazer nessa etapa.")


def _validar_movimentos(movs, hoje: date, erros: list[str], avisos: list[str]) -> None:
    if not isinstance(movs, list):
        erros.append("movimentos: precisa ser uma lista (pode ficar vazia).")
        return
    for i, m in enumerate(movs):
        onde = f"movimentos[{i}]"
        if not isinstance(m, dict):
            erros.append(f"{onde}: precisa ser um objeto com o_que, indicador e ate.")
            continue
        if not _texto(m.get("o_que")):
            erros.append(f"{onde}.o_que: falta dizer o que será feito.")
        if not _texto(m.get("indicador")):
            erros.append(f"{onde}.indicador: falta dizer como saber se funcionou.")
        ate = m.get("ate")
        d = ler_data(ate) if isinstance(ate, str) else None
        if d is None:
            erros.append(f"{onde}.ate: precisa ser uma data no formato AAAA-MM-DD.")
        elif d < hoje:
            avisos.append(f"{onde}.ate: {fmt_data(d)} já passou.")


def main(argv=None) -> int:
    configurar_saida()
    parser = criar_parser("validar_estrategia.py")
    parser.add_argument("--marca")
    parser.add_argument("--arquivo")
    parser.add_argument("--raiz")
    parser.add_argument("--hoje")
    try:
        args = parser.parse_args(argv)
        if args.ajuda:
            print(AJUDA)
            return 0
        raiz = raiz_do_projeto(args.raiz)
        hoje = ler_data_arg(args.hoje, "--hoje") or date.today()
        if args.arquivo:
            caminho = Path(args.arquivo).expanduser()
        else:
            _, pasta = resolver_marca(raiz, args.marca)
            caminho = pasta / "estrategia.json"
    except ErroUso as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2

    dados, problema = ler_json_arquivo(caminho)
    nome = caminho_curto(caminho.resolve(), raiz)
    if problema:
        dica = " Rode a skill configurar-marca para criar a estratégia." if not caminho.exists() else ""
        print(f"Erro em {nome}: {problema}.{dica}", file=sys.stderr)
        return 1

    erros, avisos = validar_estrategia(dados, hoje)
    print(f"Conferindo {nome}")
    for msg in erros:
        print(f"  ERRO   {msg}")
    for msg in avisos:
        print(f"  AVISO  {msg}")
    if erros:
        print(f"Resultado: {len(erros)} erro(s) e {len(avisos)} aviso(s). Corrija os erros antes de usar o arquivo.")
        return 1
    print(f"Resultado: estrategia.json válido ({len(avisos)} aviso(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
