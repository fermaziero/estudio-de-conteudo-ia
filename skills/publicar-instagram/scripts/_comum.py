"""Funções comuns da skill publicar-instagram.

Cuida de pastas e marcas, arquivos de credenciais, JSON e CSV, hash de aprovação,
trava de execução e, principalmente, da proteção de segredos: tudo o que os scripts
imprimem passa por um filtro que mascara tokens, chaves e assinaturas.
Não é um script para rodar; é importado pelos outros.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MARCAS = RAIZ / "marcas"
RAIZ_PERSONALIZADA: Path | None = None  # preenchida por --raiz (só para testes)
MARCA_RE = re.compile(r"[a-z0-9-]{1,60}")
ID_RE = re.compile(r"[a-z0-9-]{3,80}")

STATUS_EDITAVEIS = ("arte_pronta", "erro", "aprovado")
EXCLUIDOS_DO_HASH = ("status", "historico", "aprovacao", "agendado_para", "publicacao", "revisao")

COLUNAS_PUBLICADOS = ["publicado_em", "post_id", "lote", "formato", "media_id", "permalink", "hash"]
CHAVES_SEGREDO = ("IG_ACCESS_TOKEN", "ARMAZENAMENTO_CHAVE_SECRETA", "ARMAZENAMENTO_CHAVE_ID")


class ErroUso(Exception):
    """Problema que a pessoa ou o agente resolve: a mensagem diz como."""


class Recusa(ErroUso):
    """O script se recusou a agir (regra de segurança). Nada externo foi alterado."""


class JsonInvalido(ErroUso, ValueError):
    """Arquivo JSON quebrado (vírgula sobrando, aspas faltando...). A mensagem diz linha e coluna."""


def definir_raiz(pasta) -> Path:
    """Troca a pasta raiz do projeto neste processo (opção --raiz, só para testes)."""
    global RAIZ, MARCAS, RAIZ_PERSONALIZADA
    nova = Path(pasta).expanduser().resolve()
    if not nova.is_dir():
        raise ErroUso(f"--raiz: a pasta não existe: {pasta}")
    RAIZ, MARCAS, RAIZ_PERSONALIZADA = nova, nova / "marcas", nova
    return nova


def opcao_raiz(parser, subcomando: bool = False) -> None:
    """Acrescenta --raiz ao parser (avançado, só para testes). Nos subcomandos o valor só entra se for informado."""
    parser.add_argument("--raiz", default=argparse.SUPPRESS if subcomando else None,
                        help="avançado, só para testes: pasta raiz do projeto (padrão: a pasta onde esta skill está instalada)")


def aplicar_raiz(args) -> None:
    if getattr(args, "raiz", None):
        definir_raiz(args.raiz)


def dentro_de(base, caminho) -> Path:
    """Resolve `caminho` e confere que ele fica dentro de `base`. Devolve o caminho resolvido ou recusa."""
    pasta = Path(base).resolve()
    alvo = Path(caminho).resolve()
    if alvo != pasta and pasta not in alvo.parents:
        raise Recusa("um caminho montado a partir de dados do post sairia da pasta esperada; por segurança, "
                     "nada foi lido, gravado nem apagado")
    return alvo


class Incerto(Exception):
    """A Meta pode ter publicado: não tentar de novo sem conferir."""


# ---------------------------------------------------------------- segredos

_SEGREDOS: set[str] = set()
_PADROES_SEGREDO = [
    (re.compile(r"(?i)\b(access_token|client_secret|fb_exchange_token|input_token)=([^&\s'\"<>]+)"), r"\1=***"),
    (re.compile(r"(?i)X-Amz-(Signature|Credential|Security-Token)=[^&\s'\"<>]+"), r"X-Amz-\1=***"),
    (re.compile(r"(?i)\b(Bearer|OAuth)\s+[A-Za-z0-9._~+/=-]{16,}"), r"\1 ***"),
    (re.compile(r"\b(?:IG|EA)[A-Za-z0-9_-]{40,}"), "***"),
]


def registrar_segredos(valores) -> None:
    for v in valores:
        if isinstance(v, str) and len(v) >= 6:
            _SEGREDOS.add(v)


def mascarar(texto) -> str:
    texto = str(texto)
    for segredo in sorted(_SEGREDOS, key=len, reverse=True):
        texto = texto.replace(segredo, "***")
    for padrao, troca in _PADROES_SEGREDO:
        texto = padrao.sub(troca, texto)
    return texto


class SaidaProtegida:
    """Embrulha stdout/stderr: mascara segredos, aceita saída ausente (pythonw) e copia para o log."""

    def __init__(self, destino, log=None):
        self._destino, self._log = destino, log
        self.encoding = "utf-8"
        self.errors = "replace"

    def write(self, texto):
        texto = mascarar(texto)
        if self._destino is not None:
            try:
                self._destino.write(texto)
            except (OSError, ValueError, UnicodeError):
                pass
        if self._log is not None:
            try:
                self._log.write(texto)
            except (OSError, ValueError, UnicodeError):
                pass
        return len(texto)

    def flush(self):
        for f in (self._destino, self._log):
            try:
                if f is not None:
                    f.flush()
            except (OSError, ValueError):
                pass

    def isatty(self):
        try:
            return bool(self._destino and self._destino.isatty())
        except (OSError, ValueError):
            return False


def proteger_saida(log=None) -> None:
    """Chame uma vez no começo de cada script."""
    for nome in ("stdout", "stderr"):
        atual = getattr(sys, nome)
        if isinstance(atual, SaidaProtegida):
            if log is not None:
                atual._log = log
            continue
        try:
            if atual is not None:
                atual.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
        setattr(sys, nome, SaidaProtegida(atual, log))
    if os.name == "nt":
        try:
            import ctypes
            if sys.stdout.isatty():
                ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass


def abrir_log(marca: str, nome: str):
    """Log mensal da rotina (publicacao/logs/rotina-AAAA-MM.log). Devolve o arquivo aberto ou None."""
    try:
        pasta = pasta_marca(marca) / "publicacao" / "logs"
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo = pasta / f"rotina-{datetime.now():%Y-%m}.log"
        f = arquivo.open("a", encoding="utf-8")
        f.write(f"\n=== {iso(agora())} {nome} ===\n")
        return f
    except OSError:
        return None


# ---------------------------------------------------------------- tempo

def agora() -> datetime:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def interpretar_data(texto) -> datetime | None:
    """ISO 8601 (com 'Z', '+0000' ou sem fuso). Sem fuso, vale o fuso deste computador."""
    if not texto:
        return None
    t = str(texto).strip().replace("Z", "+00:00").replace("z", "+00:00")
    t = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", t)
    t = re.sub(r"(\.\d{6})\d+", r"\1", t)
    t = re.sub(r"\.(\d{1,5})(?=[+-]|$)", lambda m: "." + m.group(1).ljust(6, "0"), t)
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d.astimezone() if d.tzinfo is None else d


# ---------------------------------------------------------------- marcas e pastas

def listar_marcas() -> list[str]:
    if not MARCAS.is_dir():
        return []
    return sorted(p.name for p in MARCAS.iterdir() if p.is_dir() and MARCA_RE.fullmatch(p.name))


def escolher_marca(arg: str | None = None) -> str:
    existentes = listar_marcas()
    if arg:
        if not MARCA_RE.fullmatch(arg):
            raise ErroUso(f"nome de marca inválido: '{arg}' (use minúsculas, números e hífen)")
        if arg not in existentes:
            lista = ", ".join(existentes) or "nenhuma"
            raise ErroUso(f"não existe a marca '{arg}' em marcas/. Marcas encontradas: {lista}")
        return arg
    reais = [m for m in existentes if m != "exemplo"]
    if len(reais) == 1:
        return reais[0]
    if not reais:
        raise ErroUso("nenhuma marca encontrada além de 'exemplo'. Crie a sua com a skill configurar-marca "
                      "(ou use --marca exemplo só para testar o fluxo, sem publicar)")
    raise ErroUso("há mais de uma marca. Escolha uma com --marca: " + ", ".join(reais))


def pasta_marca(marca: str) -> Path:
    return MARCAS / marca


def pasta_config(marca: str) -> Path:
    base = os.environ.get("ESTUDIO_CONFIG")
    base_path = Path(base).expanduser() if base else Path.home() / ".config" / "estudio-de-conteudo"
    return base_path / marca


def localizar_post(marca: str, ref: str) -> Path:
    """Aceita o id do post ou o caminho do arquivo .json."""
    conteudo = pasta_marca(marca) / "conteudo"
    if ref.lower().endswith(".json") or any(s in ref for s in ("/", "\\")):
        caminho = Path(ref).expanduser()
        if not caminho.is_absolute():
            caminho = (Path.cwd() / caminho)
        if not caminho.is_file():
            raise ErroUso(f"arquivo não encontrado: {ref}")
        caminho = caminho.resolve()
        if caminho.parent.name != "posts" or caminho.parent.parent.parent != conteudo.resolve():
            raise ErroUso("o arquivo precisa estar em marcas/<marca>/conteudo/<lote>/posts/")
        return caminho
    if not ID_RE.fullmatch(ref):
        raise ErroUso(f"id de post inválido: '{ref}' (use minúsculas, números e hífen, de 3 a 80 caracteres)")
    achados = sorted(conteudo.glob(f"*/posts/{ref}.json"))
    if not achados:
        raise ErroUso(f"não achei o post '{ref}' em marcas/{marca}/conteudo/*/posts/")
    if len(achados) > 1:
        raise ErroUso(f"o id '{ref}' existe em mais de um lote; passe o caminho do arquivo em --post")
    return dentro_de(conteudo, achados[0])


def pasta_artes(caminho_post: Path, post_id: str) -> Path:
    """artes/<id>/ ao lado de posts/. O id precisa seguir o padrão e a pasta precisa ficar dentro do lote."""
    if not ID_RE.fullmatch(str(post_id)):
        raise Recusa("o id do post não segue o padrão (3 a 80 caracteres: minúsculas, números e hífen)")
    lote = caminho_post.parent.parent
    pasta = lote / "artes" / post_id
    dentro_de(lote, pasta)
    return pasta


# ---------------------------------------------------------------- arquivos

def escrever_atomico(caminho: Path, texto: str | bytes) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    dados = texto if isinstance(texto, bytes) else texto.encode("utf-8")
    tmp.write_bytes(dados)
    for tentativa in range(5):
        try:
            os.replace(tmp, caminho)
            return
        except PermissionError:
            if tentativa == 4:
                raise
            time.sleep(0.4)


def ler_json(caminho: Path):
    """Lê um JSON. Se estiver quebrado, levanta JsonInvalido dizendo o arquivo, a linha e a coluna."""
    caminho = Path(caminho)
    try:
        return json.loads(caminho.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise JsonInvalido(f"o arquivo {caminho.name} não é um JSON válido: {traduzir_erro_json(e.msg)} "
                           f"(linha {e.lineno}, coluna {e.colno}). Abra o arquivo, corrija esse ponto "
                           "(vírgula sobrando ou faltando, aspas, chaves) e rode de novo") from None
    except UnicodeDecodeError:
        raise JsonInvalido(f"o arquivo {caminho.name} não está em UTF-8. Salve-o como UTF-8 e rode de novo") from None


def traduzir_erro_json(msg: str) -> str:
    return {"Expecting value": "esperava um valor (talvez uma vírgula sobrando antes de } ou ])",
            "Expecting property name enclosed in double quotes": "esperava um nome entre aspas duplas (talvez uma vírgula sobrando)",
            "Expecting ',' delimiter": "faltou uma vírgula entre dois itens",
            "Expecting ':' delimiter": "faltaram os dois-pontos depois do nome",
            "Unterminated string starting at": "um texto ficou sem aspas de fechamento",
            "Extra data": "sobrou texto depois do fim do JSON"}.get(msg, msg)


def gravar_json(caminho: Path, dados) -> None:
    escrever_atomico(caminho, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def restringir_permissao(caminho: Path) -> None:
    """Deixa o arquivo ou a pasta legíveis só pelo dono. No Windows, ajusta as permissões com icacls."""
    caminho = Path(caminho)
    try:
        os.chmod(caminho, 0o700 if caminho.is_dir() else 0o600)
    except OSError:
        pass
    if os.name != "nt":
        return
    usuario = os.environ.get("USERNAME")
    if not usuario:
        return
    dominio = os.environ.get("USERDOMAIN")
    conta = f"{dominio}\\{usuario}" if dominio else usuario
    concessao = f"{conta}:(OI)(CI)F" if caminho.is_dir() else f"{conta}:F"
    try:
        r = processo(["icacls", str(caminho), "/grant:r", concessao], timeout=20)
        if r.returncode == 0:
            processo(["icacls", str(caminho), "/inheritance:r"], timeout=20)
    except (OSError, subprocess.SubprocessError):
        pass


def processo(comando: list, **opcoes) -> subprocess.CompletedProcess:
    """subprocess.run que captura a saída e, no Windows, não abre janela de console."""
    if os.name == "nt":
        opcoes.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    opcoes.setdefault("capture_output", True)
    return subprocess.run(comando, **opcoes)


def interprete_console() -> str:
    """Python para rodar scripts filhos: no Windows, troca o pythonw.exe (sem saída) pelo python.exe vizinho."""
    atual = Path(sys.executable)
    if atual.name.lower() == "pythonw.exe" and atual.with_name("python.exe").is_file():
        return str(atual.with_name("python.exe"))
    return sys.executable


def ler_env(caminho: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    caminho = Path(caminho)
    if caminho.is_file():
        for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            valor = valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                valor = valor[1:-1]
            valores[chave.strip()] = valor
    registrar_segredos(valores.get(k, "") for k in CHAVES_SEGREDO)
    return valores


def atualizar_env(caminho: Path, novos: dict[str, str], cabecalho: str = "") -> None:
    """Troca ou acrescenta chaves preservando comentários e a ordem. Grava com permissão restrita."""
    caminho = Path(caminho)
    linhas = caminho.read_text(encoding="utf-8-sig").splitlines() if caminho.is_file() else \
        [l for l in cabecalho.splitlines()]
    pendentes = dict(novos)
    saida = []
    for linha in linhas:
        chave = linha.split("=", 1)[0].strip() if "=" in linha and not linha.lstrip().startswith("#") else None
        if chave in pendentes:
            saida.append(f"{chave}={pendentes.pop(chave)}")
        else:
            saida.append(linha)
    saida += [f"{k}={v}" for k, v in pendentes.items()]
    registrar_segredos(novos.get(k, "") for k in CHAVES_SEGREDO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    restringir_permissao(caminho.parent)
    escrever_atomico(caminho, "\n".join(saida) + "\n")
    restringir_permissao(caminho)


# ---------------------------------------------------------------- CSV

def _tabela(caminho: Path) -> tuple[list[str], list[list[str]], str]:
    """Lê um CSV tolerando BOM e separador ';' (o Excel em português salva assim).
    Devolve (cabeçalho como está no arquivo, linhas de dados sem as vazias, separador)."""
    with Path(caminho).open(encoding="utf-8-sig", newline="") as f:
        texto = f.read()
    primeira = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primeira.count(";") > primeira.count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=separador))
    linhas = [l for l in linhas if any(c.strip() for c in l)]
    return (linhas[0] if linhas else []), linhas[1:], separador


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    """Linhas do CSV como dicionários. Os nomes das colunas saem em minúsculas e sem espaços nas pontas."""
    caminho = Path(caminho)
    if not caminho.is_file():
        return []
    cabecalho, linhas, _ = _tabela(caminho)
    nomes = [c.strip().lower() for c in cabecalho]
    return [{nome: (linha[i] if i < len(linha) else "") for i, nome in enumerate(nomes)} for linha in linhas]


def anexar_csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not caminho.is_file() or caminho.stat().st_size == 0
    precisa_quebra = False
    if not novo:
        with caminho.open("rb") as f:
            f.seek(-1, os.SEEK_END)
            precisa_quebra = f.read(1) not in (b"\n", b"\r")  # arquivo salvo sem a quebra final
    with caminho.open("a", encoding="utf-8", newline="") as f:
        if precisa_quebra:
            f.write("\n")
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n", extrasaction="ignore")
        if novo:
            w.writeheader()
        for linha in linhas:
            w.writerow({c: ("" if linha.get(c) is None else linha.get(c)) for c in colunas})


def _guardar_antes(caminho: Path, motivo: str, mover: bool) -> Path:
    """Guarda a versão atual em _antes-<motivo>-AAAA-MM-DD/ (nada se apaga). Devolve a pasta."""
    destino = caminho.parent / f"_antes-{motivo}-{agora():%Y-%m-%d}"
    destino.mkdir(exist_ok=True)
    alvo = destino / caminho.name
    if alvo.exists():
        alvo = destino / f"{agora():%H%M%S}-{caminho.name}"
    if mover:
        os.replace(caminho, alvo)
    else:
        shutil.copy2(caminho, alvo)
    return destino


def normalizar_csv(caminho: Path, colunas: list[str], obrigatorias: list[str], incompativel: str = "mover") -> list[str]:
    """Prepara um CSV que já existe para receber linhas novas sem perder dados. Devolve as colunas a gravar.

    Aceita separador ';', BOM, maiúsculas e colunas extras (o contrato permite). Se faltar alguma coluna da lista, ela
    entra no fim (as linhas antigas ficam vazias nela). Quando precisa reescrever o arquivo, guarda a versão anterior em
    _antes-formato-csv-AAAA-MM-DD/. Se faltarem as colunas obrigatórias, não é o arquivo certo: guarda tudo em
    _antes-cabecalho-AAAA-MM-DD/ e começa outro (incompativel='mover') ou recusa (incompativel='recusar').
    """
    caminho = Path(caminho)
    if not caminho.is_file() or caminho.stat().st_size == 0:
        return list(colunas)
    cabecalho, linhas, separador = _tabela(caminho)
    nomes = [c.strip().lower() for c in cabecalho]
    if not all(o in nomes for o in obrigatorias):
        if incompativel == "recusar":
            raise Recusa(f"o arquivo {caminho.name} tem um cabeçalho que não reconheço (faltam: "
                         f"{', '.join(o for o in obrigatorias if o not in nomes)}). Corrija ou renomeie o arquivo e "
                         "rode de novo. Nada foi alterado")
        destino = _guardar_antes(caminho, "cabecalho", mover=True)
        print(f"AVISO: {caminho.name} tinha um cabeçalho que não reconheço; a versão antiga foi para {destino.name}/.")
        return list(colunas)
    faltando = [c for c in colunas if c not in nomes]
    novos_nomes = nomes + faltando
    tem_bom = caminho.read_bytes()[:3] == b"\xef\xbb\xbf"
    if separador == "," and not tem_bom and not faltando and nomes == [c.strip() for c in cabecalho]:
        return nomes
    destino = _guardar_antes(caminho, "formato-csv", mover=False)
    tmp = caminho.with_name(caminho.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(novos_nomes)
        for linha in linhas:
            base = list(linha[:len(nomes)]) + [""] * max(0, len(nomes) - len(linha))
            w.writerow(base + [""] * len(faltando) + list(linha[len(nomes):]))
    os.replace(tmp, caminho)
    print(f"AVISO: ajustei o formato de {caminho.name} (separador, maiúsculas ou colunas); nenhum dado foi perdido e a "
          f"versão anterior está em {destino.name}/.")
    return novos_nomes


# ---------------------------------------------------------------- hash de aprovação

def sha256_hex(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def json_canonico(post: dict) -> bytes:
    base = {k: v for k, v in post.items() if k not in EXCLUIDOS_DO_HASH}
    return json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def calcular_hash(post: dict, artes: list[bytes]) -> str:
    """sha256 do post canônico somado ao sha256 de cada arte, em ordem (veja referencias/aprovacao-e-hash.md)."""
    texto = "post:" + sha256_hex(json_canonico(post)) + "\n"
    for n, dados in enumerate(artes, 1):
        texto += f"arte-{n:02d}:" + sha256_hex(dados) + "\n"
    return sha256_hex(texto.encode("utf-8"))


def acrescentar_historico(post: dict, evento: str, por: str) -> None:
    post.setdefault("historico", [])
    if not isinstance(post["historico"], list):
        post["historico"] = []
    post["historico"].append({"data": iso(agora()), "evento": evento, "por": por})


# ---------------------------------------------------------------- publicados.csv

def arquivo_publicados(marca: str) -> Path:
    return pasta_marca(marca) / "publicacao" / "publicados.csv"


def arquivo_pendentes(marca: str) -> Path:
    return pasta_marca(marca) / "publicacao" / "publicados-pendentes.jsonl"


def registros_publicados(marca: str) -> list[dict]:
    """Linhas do publicados.csv e da reserva. Se não der para ler, recusa: sem o registro não há como evitar duplicata."""
    pend = arquivo_pendentes(marca)
    try:
        linhas = ler_csv(arquivo_publicados(marca))
        if pend.is_file():
            for l in pend.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    try:
                        linhas.append(json.loads(l))
                    except ValueError:
                        continue
    except (OSError, csv.Error):
        raise Recusa("não consegui ler publicacao/publicados.csv (ele está aberto em outro programa, como o Excel, "
                     "ou está com defeito). Feche o arquivo, confira-o e rode de novo. Nada foi publicado") from None
    if linhas and "post_id" not in linhas[0]:
        raise Recusa("o arquivo publicacao/publicados.csv tem um cabeçalho que não reconheço (falta a coluna post_id); "
                     "sem ele não dá para evitar uma publicação duplicada. Corrija o arquivo e rode de novo. "
                     "Nada foi publicado")
    return linhas


def registrar_publicado(marca: str, linha: dict) -> str:
    """Grava no publicados.csv. Se o arquivo estiver aberto em outro programa, guarda na reserva .jsonl.
    Devolve 'csv' ou 'reserva'."""
    pend = arquivo_pendentes(marca)
    try:
        colunas = normalizar_csv(arquivo_publicados(marca), COLUNAS_PUBLICADOS, ["post_id", "media_id"], "recusar")
        if pend.is_file():
            antigas = [json.loads(l) for l in pend.read_text(encoding="utf-8").splitlines() if l.strip()]
            anexar_csv(arquivo_publicados(marca), colunas, antigas + [linha])
            pend.unlink()
        else:
            anexar_csv(arquivo_publicados(marca), colunas, [linha])
        return "csv"
    except (OSError, ErroUso, csv.Error):
        pend.parent.mkdir(parents=True, exist_ok=True)
        with pend.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return "reserva"


# ---------------------------------------------------------------- trava de execução

def pid_vivo(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.OpenProcess.restype = ctypes.c_void_p
            h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ctypes.get_last_error() == 5  # acesso negado: o processo existe
            codigo = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(codigo))
            k.CloseHandle(ctypes.c_void_p(h))
            return bool(ok) and codigo.value == 259  # STILL_ACTIVE
        except Exception:
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def tomar_trava_execucao(arquivo: Path, validade_s: int = 90 * 60) -> tuple[bool, dict]:
    """Uma execução da rotina por vez. Devolve (conseguiu, dados do dono atual)."""
    arquivo = Path(arquivo)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    conteudo = json.dumps({"pid": os.getpid(), "inicio": iso(agora())})
    for _ in range(2):
        try:
            with arquivo.open("x", encoding="utf-8") as f:
                f.write(conteudo)
            return True, {}
        except FileExistsError:
            try:
                dono = json.loads(arquivo.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                dono = {}
            inicio = interpretar_data(dono.get("inicio"))
            velha = inicio is None or (agora() - inicio).total_seconds() > validade_s
            if not velha and pid_vivo(int(dono.get("pid") or 0)):
                return False, dono
            try:
                arquivo.unlink()
            except OSError:
                return False, dono
    return False, {}


def soltar_trava_execucao(arquivo: Path) -> None:
    try:
        Path(arquivo).unlink()
    except OSError:
        pass


def executar(principal) -> None:
    """Roda a função principal com tratamento padrão de erros e códigos de saída."""
    try:
        codigo = principal()
    except Recusa as e:
        print(f"RECUSADO: {e}", file=sys.stderr)
        sys.exit(1)
    except ErroUso as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
    except Incerto as e:
        print(f"SEM RESPOSTA CLARA: {e}", file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        print("Interrompido pela pessoa.", file=sys.stderr)
        sys.exit(130)
    except OSError as e:
        onde = f" ({mascarar(e.filename)})" if getattr(e, "filename", None) else ""
        print(f"ERRO: não consegui ler ou gravar um arquivo{onde}: {e.strerror or type(e).__name__}. Confira se ele "
              "existe, se não está aberto em outro programa (como o Excel) e se você tem permissão para ele.",
              file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERRO: um dado está num formato que não consigo usar ({mascarar(e)}). Confira os arquivos da marca e "
              "o comando que você rodou.", file=sys.stderr)
        sys.exit(1)
    sys.exit(codigo or 0)
