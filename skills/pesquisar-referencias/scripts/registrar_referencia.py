"""Grava ou substitui a linha de um perfil em marcas/<marca>/referencias/referencias.csv.

Rode da raiz do projeto (o comando abaixo é uma linha só; no PowerShell, o @ do perfil vai entre aspas):

  python -X utf8 skills/pesquisar-referencias/scripts/registrar_referencia.py --marca minha-marca --perfil "@exemplo.ia" --nicho nutricao --tipo pessoal --data 2026-11-03 --seguidores "100 mil" --posts-semana 5 --mediana-views "5 mil" --pct-cta 50 --alavanca "Dica prática em três passos"

Os números do exemplo acima são fictícios.

Colunas do arquivo: perfil, nicho, tipo, data, seguidores, posts_semana, mediana_views,
pct_cta, alavanca. Seguidores e mediana_views entram como inteiros; posts_semana e pct_cta
com até uma casa decimal, com ponto. O script entende o que o Instagram mostra ("100 mil",
"1,5 mi", "9.000", "4,5", "50%") e "não medido" (a célula fica vazia).

O perfil pode vir com ou sem @, ou como link. Se já está no arquivo, a linha é substituída e a
anterior é guardada em referencias/_antes-recoleta/referencias-substituidas.csv. Se o arquivo
foi salvo pelo Excel em português (separado por ponto e vírgula), o script lê assim mesmo e
grava de volta com vírgula. Se o arquivo estiver aberto no Excel, ele pede para fechar e não
altera nada. Use --simular para ver o resultado sem gravar.

Saída: 0 se gravou (ou simulou); 1 se os dados são inválidos ou o arquivo está travado;
2 se faltou escolher a marca ou o perfil.
"""
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _comum as c  # noqa: E402


def _inteiro(texto, nome):
    valor = c.arredondar(c.ler_numero(texto))
    if valor is None:
        return ""
    if valor < 0:
        raise c.ErroDados(f"{nome} fora do intervalo esperado: {texto!r}")
    return str(valor)


def _decimal(texto, nome, maximo=None):
    valor = c.ler_numero(texto)
    if valor is None:
        return ""
    if valor < 0 or (maximo is not None and valor > maximo):
        raise c.ErroDados(f"{nome} fora do intervalo esperado: {texto!r}")
    return c.formatar_decimal(valor)


def montar_linha(perfil, nicho, tipo, data, seguidores, posts_semana, mediana_views, pct_cta,
                 alavanca):
    handle = c.normalizar_handle(perfil)
    tipo = (tipo or "").strip().lower()
    if tipo not in c.TIPOS:
        raise c.ErroDados(f"tipo deve ser um destes: {', '.join(c.TIPOS)}")
    try:
        dia = date.fromisoformat((data or "").strip())
    except ValueError:
        raise c.ErroDados(f"data inválida: {data!r} (use AAAA-MM-DD)")
    if dia > date.today() + timedelta(days=1):
        raise c.ErroDados(f"a data {data} está no futuro")
    alavanca = " ".join((alavanca or "").split())
    if re.sub(r"\s+", "", c.sem_acento(alavanca).lower()) in c.NAO_MEDIDO:
        alavanca = ""
    linha = {
        "perfil": "@" + handle,
        "nicho": c.normalizar_nicho(nicho),
        "tipo": tipo,
        "data": dia.isoformat(),
        "seguidores": _inteiro(seguidores, "seguidores"),
        "posts_semana": _decimal(posts_semana, "posts por semana"),
        "mediana_views": _inteiro(mediana_views, "mediana de views"),
        "pct_cta": _decimal(pct_cta, "% de chamada para ação", maximo=100),
        "alavanca": alavanca,
    }
    if not any(linha[k] for k in ("seguidores", "posts_semana", "mediana_views", "pct_cta")):
        raise c.ErroDados("informe ao menos um número medido (seguidores, posts por semana, "
                          "mediana de views ou % de chamada para ação)")
    if len(linha["alavanca"]) > 140:
        raise c.ErroDados("a alavanca deve ser uma frase curta (até 140 caracteres)")
    return linha


def ajustar_linha_do_excel(linha):
    """Põe números e data de uma linha antiga no formato do projeto; devolve (linha, células mudadas)."""
    nova, mudou = dict(linha), 0
    for coluna, converter in (("seguidores", _inteiro), ("mediana_views", _inteiro),
                              ("posts_semana", _decimal), ("pct_cta", _decimal)):
        original = (nova.get(coluna) or "").strip()
        if not original:
            continue
        try:
            ajustado = converter(original, coluna)
        except c.ErroDados:
            continue
        if ajustado != original:
            nova[coluna], mudou = ajustado, mudou + 1
    data = (nova.get("data") or "").strip()
    achado = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", data)
    if achado:
        try:
            nova["data"] = date(int(achado.group(3)), int(achado.group(2)), int(achado.group(1))).isoformat()
            mudou += 1
        except ValueError:
            pass
    return nova, mudou


def _handle_da_linha(linha):
    return (linha.get("perfil") or "").strip().lower().lstrip("@")


def guardar_anteriores(pasta, substituidas):
    pasta_antes = pasta / "_antes-recoleta"
    padrao = pasta_antes / "referencias-substituidas.csv"
    copias = [{k: r.get(k, "") for k in c.COLUNAS_CSV} for r in substituidas]
    try:
        _, anteriores, _ = c.ler_csv(padrao)
        c.gravar_csv(padrao, c.COLUNAS_CSV, anteriores + copias)
        return padrao, False
    except c.ErroDados:
        alternativo = pasta_antes / f"referencias-substituidas-{datetime.now():%Y%m%d-%H%M%S}.csv"
        c.gravar_csv(alternativo, c.COLUNAS_CSV, copias)
        return alternativo, True


def registrar(raiz, marca, linha, simular=False):
    pasta = raiz / "marcas" / marca / "referencias"
    arquivo = pasta / "referencias.csv"
    campos_atuais, existentes, notas = c.ler_csv(arquivo)
    campos = c.COLUNAS_CSV + [x for x in campos_atuais if x not in c.COLUNAS_CSV]
    linhas, ajustadas = [], 0
    for r in existentes:
        nova, mudou = ajustar_linha_do_excel(r)
        linhas.append(nova)
        ajustadas += mudou
    if ajustadas:
        notas.append(f"Ajustei {ajustadas} célula(s) de outras linhas para o formato do projeto "
                     "(números com vírgula, datas dd/mm/aaaa).")
    alvo = linha["perfil"].lstrip("@")
    indices = [i for i, r in enumerate(linhas) if _handle_da_linha(r) == alvo]
    substituidas = [linhas[i] for i in indices]
    if not indices:
        linhas.append(linha)
    else:
        extras = {k: v for k, v in substituidas[0].items() if k not in c.COLUNAS_CSV}
        linhas[indices[0]] = {**extras, **linha}
        for i in reversed(indices[1:]):
            del linhas[i]
    resumo = ", ".join(f"{k}={linha[k] or 'não medido'}"
                       for k in ("seguidores", "posts_semana", "mediana_views", "pct_cta"))
    acao = "substituído" if substituidas else "novo"
    prefixo = "[simulação] " if simular else ""
    saida = [f"{prefixo}{linha['perfil']} ({acao}) em marcas/{marca}/referencias/referencias.csv "
             f"({len(linhas)} perfis): nicho={linha['nicho']}, {resumo}"]
    if simular:
        return "\n".join(saida + [prefixo + n for n in notas])
    c.gravar_csv(arquivo, campos, linhas)
    if substituidas:
        try:
            destino, alternativo = guardar_anteriores(pasta, substituidas)
        except c.ErroDados as e:
            antigas = " | ".join(",".join(f"{k}={r.get(k, '')}" for k in c.COLUNAS_CSV)
                                 for r in substituidas)
            raise c.ErroDados(f"atualizei {arquivo.name}, mas não consegui guardar a linha anterior "
                              f"({e}). Guarde você mesma: {antigas}")
        if alternativo:
            notas.append("A cópia das linhas antigas estava aberta em outro programa; guardei a "
                         f"linha anterior em {destino.relative_to(raiz).as_posix()}.")
    return "\n".join(saida + notas)


def main(argv=None):
    c.configurar_saida()
    p = c.criar_parser(__doc__)
    p.add_argument("--marca", help="slug da marca (pasta em marcas/); opcional se houver uma só")
    p.add_argument("--perfil", required=True,
                   help='handle do perfil, com ou sem @ (no PowerShell: "@handle" entre aspas), ou o link do perfil')
    p.add_argument("--nicho", required=True, help="rótulo curto do assunto do perfil (ex.: nutricao)")
    p.add_argument("--tipo", required=True, help="pessoal ou marca")
    p.add_argument("--data", default=date.today().isoformat(), help="data da coleta, AAAA-MM-DD (padrão: hoje)")
    p.add_argument("--seguidores", default="", help='ex.: "100 mil"')
    p.add_argument("--posts-semana", default="", help='ex.: 5 ou "4,5" (até uma casa decimal)')
    p.add_argument("--mediana-views", default="", help='mediana de views dos reels, ex.: "5 mil"')
    p.add_argument("--pct-cta", default="",
                   help='porcentagem de posts com chamada para ação, ex.: 50 ou "50%%" (até uma casa decimal)')
    p.add_argument("--alavanca", default="", help="frase curta do que mais dá alcance ao perfil")
    p.add_argument("--simular", action="store_true", help="mostra o que seria gravado, sem gravar")
    p.add_argument("--raiz", help="pasta do projeto (padrão: a pasta atual ou a do projeto)")
    a = p.parse_args(argv)
    try:
        raiz = c.raiz_projeto(a.raiz)
        marca = c.resolver_marca(raiz, a.marca)
    except c.ErroUso as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2
    try:
        linha = montar_linha(a.perfil, a.nicho, a.tipo, a.data, a.seguidores, a.posts_semana,
                             a.mediana_views, a.pct_cta, a.alavanca)
        print(registrar(raiz, marca, linha, a.simular))
    except c.ErroDados as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
