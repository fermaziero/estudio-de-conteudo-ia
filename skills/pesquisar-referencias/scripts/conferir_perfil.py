"""Confere o arquivo de um perfil de referência antes de ele entrar na síntese.

Rode da raiz do projeto (o comando abaixo é uma linha só; no PowerShell, o @ do perfil vai entre aspas):

  python -X utf8 skills/pesquisar-referencias/scripts/conferir_perfil.py --marca minha-marca --perfil "@exemplo.ia"

O perfil pode vir com ou sem @, ou como link do Instagram.

O que ele faz:
  - confere o título, as seções do modelo e a ordem delas;
  - recalcula mediana de views dos reels, posts por semana e % de chamada para ação a
    partir do Anexo e compara com a seção Benchmark;
  - confere o vocabulário do Anexo (formato, chamada, views só em reel, datas);
  - procura citações literais longas e dados pessoais (e-mail, telefone, link);
  - com --registrar, grava a linha em referencias.csv quando não há nenhum erro.

Saída: 0 sem erros (avisos não contam); 1 com erros; 2 se faltou escolher a marca ou o perfil.
"""
import re
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _comum as c  # noqa: E402
import registrar_referencia as reg  # noqa: E402

SECOES = ["numeros", "do que fala", "como fala", "o que mais engaja", "como atrai e converte",
          "o que esta marca pode aproveitar", "limites da coleta", "benchmark",
          "anexo: posts do grid"]
NOMES = {"numeros": "Números", "do que fala": "Do que fala", "como fala": "Como fala",
         "o que mais engaja": "O que mais engaja",
         "como atrai e converte": "Como atrai e converte",
         "o que esta marca pode aproveitar": "O que esta marca pode aproveitar",
         "limites da coleta": "Limites da coleta", "benchmark": "Benchmark",
         "anexo: posts do grid": "Anexo: posts do grid"}
COLUNAS_OBRIGATORIAS = ["#", "data", "formato", "fixado", "tema", "chamada", "views", "curtidas"]
CHAMADAS = ["comente", "link-bio", "contato", "convite", "pergunta", "nenhuma"]
CHAMADAS_QUE_CONTAM = {"comente", "link-bio", "contato"}
FORMATOS = {"reel", "post", "carrossel", "foto", "imagem", "video"}
SEM_VALOR = {"", "-", "—", "–", "nao medido", "n/d"}


def separar_secoes(texto):
    partes, atual, linhas = [], None, []
    for linha in texto.splitlines():
        if linha.startswith("## "):
            if atual is not None:
                partes.append((atual, "\n".join(linhas)))
            atual, linhas = linha[3:].strip(), []
        elif atual is not None:
            linhas.append(linha)
    if atual is not None:
        partes.append((atual, "\n".join(linhas)))
    return partes


def ler_lista_chave_valor(corpo):
    dados = {}
    for linha in corpo.splitlines():
        achado = re.match(r"\s*[-*]\s*([^:]+):\s*(.*)$", linha)
        if achado:
            dados[c.chave(achado.group(1))] = achado.group(2).strip()
    return dados


def ler_tabela(corpo):
    linhas = [l.strip() for l in corpo.splitlines() if l.strip().startswith("|")]
    if len(linhas) < 2:
        return [], []

    def celulas(linha):
        bruto = linha.strip().strip("|").replace("\\|", "\u0000")
        return [x.replace("\u0000", "|").strip() for x in bruto.split("|")]

    cabecalho = [c.chave(x) for x in celulas(linhas[0])]
    dados = []
    for linha in linhas[1:]:
        cs = celulas(linha)
        if all(re.fullmatch(r":?-{2,}:?", x) or x == "" for x in cs):
            continue
        dados.append(dict(zip(cabecalho, cs)))
    return cabecalho, dados


def eh_sim(valor):
    return c.chave(valor) in {"sim", "s", "yes"}


def ler_inteiro_celula(valor, nome, linha, erros):
    v = c.chave(valor)
    if v in SEM_VALOR:
        return None
    if re.fullmatch(r"\d+", v):
        return int(v)
    erros.append(f"Anexo, post {linha}: {nome} deve ser inteiro sem 'mil' ou '—' ({valor!r})")
    return None


def numero_ou_none(texto, nome, erros):
    try:
        return c.ler_numero(texto)
    except c.ErroDados:
        erros.append(f"Benchmark: {nome} não é um número ({texto!r}); use inteiro bruto ou 'não medido'")
        return None


def conferir(texto, handle):
    erros, avisos, info = [], [], {}
    titulo = re.match(r"#\s+@([\w.]+)\s+[—–-]+\s+referência de conteúdo \(coleta de (\d{4}-\d{2}-\d{2})\)",
                      texto.lstrip())
    data_coleta = None
    if not titulo:
        erros.append("Título fora do modelo: '# @handle — referência de conteúdo (coleta de AAAA-MM-DD)'")
    else:
        if titulo.group(1).lower() != handle:
            erros.append(f"O título cita @{titulo.group(1)}, mas o arquivo é de @{handle}")
        try:
            data_coleta = date.fromisoformat(titulo.group(2))
        except ValueError:
            erros.append(f"Data de coleta inválida no título: {titulo.group(2)}")

    secoes = separar_secoes(texto)
    achadas = [(c.chave(t), t, corpo) for t, corpo in secoes]
    chaves = [k for k, _, _ in achadas]
    corpos = {k: corpo for k, _, corpo in achadas}
    for k in SECOES:
        if k not in corpos:
            erros.append(f"Seção ausente: {NOMES[k]}")
        elif not corpos[k].strip():
            erros.append(f"Seção vazia: {NOMES[k]}")
    posicoes = [chaves.index(k) for k in SECOES if k in chaves]
    if posicoes != sorted(posicoes):
        erros.append("As seções estão fora da ordem do modelo")
    for i, k in enumerate(chaves):
        if k.startswith("foco extra") and "como atrai e converte" in chaves and \
                "o que esta marca pode aproveitar" in chaves:
            if not chaves.index("como atrai e converte") < i < chaves.index("o que esta marca pode aproveitar"):
                erros.append("Seção 'Foco extra' fora do lugar: vai entre 'Como atrai e converte' e "
                             "'O que esta marca pode aproveitar'")
        if k == "historico de coletas" and i != len(chaves) - 1:
            erros.append("'Histórico de coletas' deve ser a última seção")

    bench = ler_lista_chave_valor(corpos.get("benchmark", ""))
    chaves_bench = {"seguidores": "seguidores", "posts por semana": "posts por semana",
                    "mediana de views dos reels": "mediana de views dos reels",
                    "% de chamada para acao": "% de chamada para ação", "tipo": "tipo",
                    "nicho": "nicho", "alavanca": "alavanca", "analise": "análise"}
    for k, nome in chaves_bench.items():
        if k not in bench:
            erros.append(f"Benchmark: falta a linha '{nome}'")
    reduzida = c.chave(bench.get("analise", "")).startswith("reduzida")
    if bench.get("analise") and c.chave(bench["analise"]).split(" ")[0] not in {"completa", "reduzida"}:
        erros.append("Benchmark: 'análise' deve começar com 'completa' ou 'reduzida'")
    if bench.get("tipo") and c.chave(bench["tipo"]) not in c.TIPOS:
        erros.append("Benchmark: 'tipo' deve ser pessoal ou marca")
    if bench.get("nicho"):
        try:
            c.normalizar_nicho(bench["nicho"])
        except c.ErroDados as e:
            erros.append(f"Benchmark: {e}")

    seguidores = numero_ou_none(bench.get("seguidores", ""), "seguidores", erros)
    declarado = {
        "posts_semana": numero_ou_none(bench.get("posts por semana", ""), "posts por semana", erros),
        "mediana": numero_ou_none(bench.get("mediana de views dos reels", ""), "mediana de views", erros),
        "pct_cta": numero_ou_none(bench.get("% de chamada para acao", ""), "% de chamada para ação", erros),
    }
    info.update({"seguidores": seguidores, "declarado": declarado, "bench": bench,
                 "data_coleta": data_coleta})

    cabecalho, linhas = ler_tabela(corpos.get("anexo: posts do grid", ""))
    recalculado = {"posts_semana": None, "mediana": None, "pct_cta": None}
    if reduzida:
        for nome, valor in declarado.items():
            if valor is not None:
                erros.append("Análise reduzida: mediana, posts por semana e % de chamada devem ficar "
                             "'não medido'")
                break
    elif not linhas:
        erros.append("Anexo sem tabela de posts (análise completa exige uma linha por post)")
    else:
        faltam = [x for x in COLUNAS_OBRIGATORIAS if x not in cabecalho]
        if faltam:
            erros.append("Anexo: faltam as colunas " + ", ".join(faltam))
        else:
            recalculado = recalcular(corpos["anexo: posts do grid"], linhas, data_coleta, erros, avisos)
            comparar(declarado, recalculado, erros)
            amostra = re.search(r"(\d+)\s+posts do grid", texto)
            if amostra and int(amostra.group(1)) != len(linhas):
                avisos.append(f"A linha de amostra diz {amostra.group(1)} posts, mas o Anexo tem "
                              f"{len(linhas)} linhas")
            if len(linhas) < 20:
                avisos.append(f"Amostra pequena: {len(linhas)} posts (o modelo pede até 36)")
    info["recalculado"] = recalculado

    citacoes(texto, erros)
    dados_pessoais(texto, avisos)
    return erros, avisos, info


def recalcular(corpo_anexo, linhas, data_coleta, erros, avisos):
    reels_grid, nao_fixados, chamadas = [], [], 0
    for i, r in enumerate(linhas, 1):
        rotulo = r.get("#") or str(i)
        formato = c.chave(r.get("formato", ""))
        fixado = eh_sim(r.get("fixado", ""))
        if formato not in FORMATOS:
            erros.append(f"Anexo, post {rotulo}: formato desconhecido ({r.get('formato')!r})")
        views = ler_inteiro_celula(r.get("views", ""), "views", rotulo, erros)
        if views is not None and formato != "reel":
            erros.append(f"Anexo, post {rotulo}: views só existem em reel")
        dia = None
        bruto = c.chave(r.get("data", ""))
        if bruto not in SEM_VALOR:
            try:
                dia = date.fromisoformat(bruto)
            except ValueError:
                erros.append(f"Anexo, post {rotulo}: data inválida ({r.get('data')!r})")
        if dia and data_coleta and dia > data_coleta:
            erros.append(f"Anexo, post {rotulo}: data {dia} depois da coleta")
        palavra = re.match(r"[a-z-]+", c.chave(r.get("chamada", "")))
        tipo_chamada = palavra.group(0) if palavra else ""
        if tipo_chamada not in CHAMADAS:
            erros.append(f"Anexo, post {rotulo}: chamada fora do vocabulário ({r.get('chamada')!r}); "
                         f"use {', '.join(CHAMADAS)}")
        if tipo_chamada in CHAMADAS_QUE_CONTAM:
            chamadas += 1
        if formato == "reel" and not fixado and views is not None:
            reels_grid.append(views)
        if not fixado:
            nao_fixados.append((rotulo, dia))
    if sum(1 for r in linhas if eh_sim(r.get("fixado", ""))) > 3:
        avisos.append("Mais de 3 posts fixados: o Instagram só permite 3")

    fora = []
    achado = re.search(r"reels de fora do grid[^:\n]*:\s*\**\s*(.+)", corpo_anexo, re.I)
    if achado:
        texto = achado.group(1).strip().rstrip("*")
        if c.chave(texto).startswith("nenhum"):
            fora = []
        elif re.search(r"[a-zA-Z]", texto):
            erros.append("Reels de fora do grid: escreva só inteiros separados por vírgula, sem 'mil'")
        else:
            fora = [int(x) for x in re.findall(r"\d+", texto)]
    else:
        avisos.append("Falta a linha 'Reels de fora do grid (views): …' (ou 'nenhum') abaixo da tabela")

    todas = reels_grid + fora
    mediana = c.arredondar(statistics.median(todas)) if todas else None

    posts_semana = None
    if nao_fixados:
        primeiro, ultimo = nao_fixados[0], nao_fixados[-1]
        if primeiro[1] and ultimo[1]:
            dias = abs((primeiro[1] - ultimo[1]).days)
            if dias > 0:
                posts_semana = len(nao_fixados) / (dias / 7)
            else:
                avisos.append("O primeiro e o último post sem fixado têm a mesma data: posts por "
                              "semana fica 'não medido'")
        else:
            erros.append("Faltam as datas das pontas (primeiro e último post sem fixado do Anexo): "
                         "sem elas, posts por semana não pode ser calculado")
    pct = float(c.formatar_decimal(100 * chamadas / len(linhas))) if linhas else None
    return {"posts_semana": posts_semana, "mediana": mediana, "pct_cta": pct}


def comparar(declarado, recalculado, erros):
    nomes = {"mediana": "mediana de views dos reels", "posts_semana": "posts por semana",
             "pct_cta": "% de chamada para ação"}
    tolerancia = {"mediana": lambda calc: 1, "pct_cta": lambda calc: 1,
                  "posts_semana": lambda calc: max(0.5, 0.05 * (calc or 0))}
    for k, nome in nomes.items():
        d, r = declarado[k], recalculado[k]
        if r is None and d is None:
            continue
        if r is None:
            erros.append(f"Benchmark: {nome} está preenchido ({d:g}), mas o Anexo não permite calcular")
        elif d is None:
            erros.append(f"Benchmark: {nome} está 'não medido', mas o Anexo dá {formatar(k, r)}")
        elif abs(d - r) > tolerancia[k](r):
            erros.append(f"Benchmark: {nome} diz {d:g}, mas o Anexo dá {formatar(k, r)}")


def formatar(k, valor):
    if valor is None:
        return "não medido"
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")


def contar_palavras(trecho):
    return len(re.findall(r"\w+", trecho))


def citacoes(texto, erros):
    achados = re.findall(r"[“\"«]([^”\"»\n]{2,400})[”\"»]", texto)
    literais = [a for a in achados if contar_palavras(a) >= 6]
    longos = [a for a in literais if contar_palavras(a) > 15]
    if longos:
        erros.append(f"Citação literal com {contar_palavras(longos[0])} palavras: o limite é 15. "
                     "Parafraseie")
    elif len(literais) > 1:
        erros.append(f"{len(literais)} citações literais de 6 palavras ou mais: o limite é um trecho "
                     "de até 15 palavras por arquivo")


def dados_pessoais(texto, avisos):
    fora_da_tabela = "\n".join(l for l in texto.splitlines() if not l.strip().startswith("|"))
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", fora_da_tabela):
        avisos.append("Há algo parecido com e-mail no arquivo: remova (não registre contatos da bio)")
    if re.search(r"(?<!\d)(?<!\d[.,])(\+?\d{2,3}[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?!\d)(?![.,]\d)",
                 fora_da_tabela):
        avisos.append("Há algo parecido com telefone no arquivo: remova (não registre contatos da bio)")
    if re.search(r"https?://", texto):
        avisos.append("Há um link no arquivo: troque pelo nome do destino (ex.: 'página de links')")
    if re.search(r"fictici", c.sem_acento(texto).lower()):
        avisos.append("O arquivo cita 'fictício' ou 'fictícia': apague o que sobrou do modelo")


def main(argv=None):
    c.configurar_saida()
    p = c.criar_parser(__doc__)
    p.add_argument("--marca", help="slug da marca (pasta em marcas/); opcional se houver uma só")
    p.add_argument("--perfil", required=True,
                   help='handle do perfil, com ou sem @ (no PowerShell: "@handle" entre aspas), ou o link do perfil')
    p.add_argument("--registrar", action="store_true",
                   help="se não houver erro, grava a linha em referencias.csv")
    p.add_argument("--raiz", help="pasta do projeto (padrão: a pasta atual ou a do projeto)")
    a = p.parse_args(argv)
    try:
        raiz = c.raiz_projeto(a.raiz)
        marca = c.resolver_marca(raiz, a.marca)
        handle = c.normalizar_handle(a.perfil)
    except (c.ErroUso, c.ErroDados) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2
    arquivo = raiz / "marcas" / marca / "referencias" / "perfis" / f"{handle}.md"
    if not arquivo.is_file():
        print(f"Erro: não achei {arquivo.relative_to(raiz).as_posix()}", file=sys.stderr)
        return 1
    erros, avisos, info = conferir(arquivo.read_text(encoding="utf-8"), handle)

    print(f"Conferência de @{handle} ({arquivo.relative_to(raiz).as_posix()})")
    for e in erros:
        print(f"ERRO   {e}")
    for w in avisos:
        print(f"AVISO  {w}")
    rec = info["recalculado"]
    if any(v is not None for v in rec.values()):
        print("Recalculado a partir do Anexo:")
        print(f"- mediana de views dos reels: {formatar('mediana', rec['mediana'])}")
        print(f"- posts por semana: {formatar('posts_semana', rec['posts_semana'])}")
        print(f"- % de chamada para ação: {formatar('pct_cta', rec['pct_cta'])}")
    print(f"Resumo: {len(erros)} erro(s), {len(avisos)} aviso(s).")
    if erros:
        return 1
    if a.registrar:
        b = info["bench"]
        try:
            linha = reg.montar_linha(handle, b["nicho"], b["tipo"], info["data_coleta"].isoformat(),
                                     b["seguidores"], b["posts por semana"],
                                     b["mediana de views dos reels"], b["% de chamada para acao"],
                                     b["alavanca"])
            print(reg.registrar(raiz, marca, linha))
        except c.ErroDados as e:
            print(f"Erro ao registrar: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
