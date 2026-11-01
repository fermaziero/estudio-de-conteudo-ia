#!/usr/bin/env python3
"""Rotina neste computador: publicar os posts agendados e coletar as métricas.

Rode sempre a partir da raiz do projeto (no macOS e no Linux, use python3):

    python -X utf8 skills/publicar-instagram/scripts/rotina.py mostrar  [--marca M]
        só mostra o que seria criado e se já existe (não altera nada)
    python -X utf8 skills/publicar-instagram/scripts/rotina.py instalar [--marca M] [--python CAMINHO]
        cria as duas tarefas: publicar agendados a cada 15 minutos e coletar métricas a cada 4 horas
    python -X utf8 skills/publicar-instagram/scripts/rotina.py remover  [--marca M]

Windows: Agendador de Tarefas. macOS: launchd (agentes do usuário). Linux: cron do usuário.
As tarefas rodam como o usuário atual, sem senha guardada, e só com o computador ligado e a sessão aberta.
O 'instalar' cria algo permanente no sistema: quem roda é a pessoa, depois de ler o 'mostrar'.
Os nomes das tarefas não têm acento (acento no nome já quebrou a criação da rotina no Windows).
"""

from __future__ import annotations

import argparse
import base64
import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comum  # noqa: E402
from _comum import (ErroUso, Recusa, aplicar_raiz, escolher_marca, executar, opcao_raiz, pasta_marca,  # noqa: E402
                    processo, proteger_saida)

PASTA_SCRIPTS = Path(__file__).resolve().parent
TAREFAS = (
    {"id": "publicar-agendados", "script": "publicar.py", "args": ["agendados"], "minutos": 15, "inicio_min": 0,
     "texto": "publica os posts agendados cujo horário chegou", "quando": "a cada 15 minutos"},
    {"id": "coletar-metricas", "script": "metricas.py", "args": ["coletar"], "minutos": 240, "inicio_min": 7,
     "texto": "coleta as métricas do perfil e dos posts", "quando": "a cada 4 horas"},
)


def nome_windows(marca: str, tarefa: dict) -> str:
    return f"EstudioConteudo-{marca}-{tarefa['id']}"


def rotulo_launchd(marca: str, tarefa: dict) -> str:
    return f"com.estudio-de-conteudo.{marca}.{tarefa['id']}"


def marcador_cron(marca: str, tarefa: dict) -> str:
    return f"# estudio-de-conteudo:{marca}:{tarefa['id']}"


def sistema() -> str:
    if os.name == "nt":
        return "windows"
    return "macos" if sys.platform == "darwin" else "linux"


def interpretador(escolhido: str | None) -> str:
    python = Path(escolhido or sys.executable)
    if not python.is_file():
        raise ErroUso(f"interpretador Python não encontrado: {python}")
    if os.name == "nt":
        semjanela = python.with_name("pythonw.exe")
        if semjanela.is_file():
            return str(semjanela)
    return str(python)


def argumentos(marca: str, tarefa: dict) -> list[str]:
    extra = ["--raiz", str(_comum.RAIZ_PERSONALIZADA)] if _comum.RAIZ_PERSONALIZADA else []
    return ["-X", "utf8", str(PASTA_SCRIPTS / tarefa["script"]), *tarefa["args"], "--marca", marca, *extra]


# ---------------------------------------------------------------- Windows

# O PowerShell trata como aspa simples não só o apóstrofo comum, mas também estes quatro caracteres tipográficos.
# Dentro de um texto entre aspas simples, cada um precisa ser dobrado para valer como o próprio caractere.
ASPAS_SIMPLES_PS = "'‘’‚‛"


def ps(texto: str) -> str:
    return "'" + "".join(c * 2 if c in ASPAS_SIMPLES_PS else c for c in texto) + "'"


def script_windows(marca: str, python: str, registrar: bool = True) -> str:
    """Script PowerShell que cria as tarefas (mesma receita das tarefas já usadas em produção)."""
    linhas = [
        "$ErrorActionPreference = 'Stop'",
        "$usuario = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name",
        "$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited",
        "$config = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 90)",
    ]
    for t in TAREFAS:
        argumento = " ".join(f'"{a}"' if " " in a or not a.isascii() else a for a in argumentos(marca, t))
        linhas += [
            f"$acao = New-ScheduledTaskAction -Execute {ps(python)} -Argument {ps(argumento)} -WorkingDirectory {ps(str(_comum.RAIZ))}",
            f"$gatilho = New-ScheduledTaskTrigger -Once -At ((Get-Date).Date.AddMinutes({t['inicio_min']})) "
            f"-RepetitionInterval (New-TimeSpan -Minutes {t['minutos']}) -RepetitionDuration (New-TimeSpan -Days 3650)",
        ]
        if registrar:
            linhas += [
                f"Register-ScheduledTask -TaskName {ps(nome_windows(marca, t))} -Action $acao -Trigger $gatilho "
                f"-Principal $principal -Settings $config -Description {ps('Estudio de Conteudo: ' + t['texto'])} "
                "-Force | Out-Null",
                f"Write-Output {ps('Criada: ' + nome_windows(marca, t))}",
            ]
    return "\n".join(linhas) + "\n"


# Sem isto, uma falha do PowerShell chega como XML (CLIXML) com acentos quebrados. Aqui o erro vira uma frase em UTF-8 na
# saída de erro, sem barra de progresso, e o processo sai com código 1.
PRELUDIO_PS = ("$ProgressPreference = 'SilentlyContinue'\n"
               "try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }\n"
               "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
               "try {\n")
POSLUDIO_PS = ("\n} catch {\n"
               "    [Console]::Error.WriteLine($_.Exception.Message)\n"
               "    exit 1\n"
               "}\n")


def powershell(script: str, timeout: int = 120) -> subprocess.CompletedProcess:
    codificado = base64.b64encode((PRELUDIO_PS + script + POSLUDIO_PS).encode("utf-16-le")).decode("ascii")
    return processo(["powershell", "-NoProfile", "-NonInteractive", "-OutputFormat", "Text", "-EncodedCommand", codificado],
                    text=True, encoding="utf-8-sig", errors="replace", timeout=timeout)


def windows_existe(nome: str) -> bool | None:
    try:
        r = processo(["schtasks", "/Query", "/TN", nome], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.returncode == 0


def windows_instalar(marca: str, python: str) -> None:
    r = powershell(script_windows(marca, python))
    if r.returncode != 0:
        raise ErroUso("o Windows recusou a criação das tarefas: " + (r.stderr or r.stdout).strip()[-400:])
    print((r.stdout or "").strip())


def windows_remover(marca: str) -> None:
    for t in TAREFAS:
        nome = nome_windows(marca, t)
        if windows_existe(nome):
            r = powershell(f"Unregister-ScheduledTask -TaskName {ps(nome)} -Confirm:$false")
            print(f"Removida: {nome}" if r.returncode == 0 else f"Não consegui remover {nome}: {(r.stderr or '').strip()[-200:]}")
        else:
            print(f"Não existia: {nome}")


# ---------------------------------------------------------------- macOS (launchd)

def plist_macos(marca: str, tarefa: dict, python: str) -> dict:
    log = pasta_marca(marca) / "publicacao" / "logs" / f"launchd-{tarefa['id']}.log"
    return {"Label": rotulo_launchd(marca, tarefa), "ProgramArguments": [python, *argumentos(marca, tarefa)],
            "WorkingDirectory": str(_comum.RAIZ), "StartInterval": tarefa["minutos"] * 60, "RunAtLoad": False,
            "StandardOutPath": str(log), "StandardErrorPath": str(log)}


def arquivo_plist(marca: str, tarefa: dict) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{rotulo_launchd(marca, tarefa)}.plist"


def macos_instalar(marca: str, python: str) -> None:
    (pasta_marca(marca) / "publicacao" / "logs").mkdir(parents=True, exist_ok=True)
    for t in TAREFAS:
        arq = arquivo_plist(marca, t)
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_bytes(plistlib.dumps(plist_macos(marca, t, python)))
        alvo = f"gui/{os.getuid()}"
        processo(["launchctl", "bootout", f"{alvo}/{rotulo_launchd(marca, t)}"], capture_output=True)
        r = processo(["launchctl", "bootstrap", alvo, str(arq)], capture_output=True, text=True)
        if r.returncode != 0:
            raise ErroUso(f"o launchctl recusou {arq.name}: {(r.stderr or r.stdout).strip()[-300:]}")
        print(f"Criada: {rotulo_launchd(marca, t)}")


def macos_remover(marca: str) -> None:
    for t in TAREFAS:
        arq = arquivo_plist(marca, t)
        processo(["launchctl", "bootout", f"gui/{os.getuid()}/{rotulo_launchd(marca, t)}"], capture_output=True)
        if arq.is_file():
            arq.unlink()
            print(f"Removida: {rotulo_launchd(marca, t)}")
        else:
            print(f"Não existia: {rotulo_launchd(marca, t)}")


# ---------------------------------------------------------------- Linux (cron)

def linha_cron(marca: str, tarefa: dict, python: str) -> str:
    comando = " ".join(shlex.quote(a) for a in [python, *argumentos(marca, tarefa)])
    agenda = (f"*/{tarefa['minutos']} * * * *" if tarefa["minutos"] < 60
              else f"{tarefa['inicio_min']} */{tarefa['minutos'] // 60} * * *")
    texto = f"cd {shlex.quote(str(_comum.RAIZ))} && {comando} >/dev/null 2>&1".replace("%", "\\%")
    return f"{agenda} {texto} {marcador_cron(marca, tarefa)}"


SEM_CRONTAB = ("o programa 'crontab' não existe neste computador (Linux mínimo ou WSL). Instale o cron e deixe o serviço "
               "rodando (em Debian e Ubuntu: sudo apt install cron), ou agende por outro meio: a rotina é só rodar "
               "'publicar.py agendados' a cada 15 minutos e 'metricas.py coletar' a cada 4 horas. No WSL, prefira "
               "instalar a rotina no Windows, com o Python do Windows. Nada foi alterado")


def crontab_atual() -> list[str]:
    try:
        r = processo(["crontab", "-l"], text=True)
    except OSError:
        raise ErroUso(SEM_CRONTAB) from None
    return r.stdout.splitlines() if r.returncode == 0 else []


def gravar_crontab(linhas: list[str]) -> None:
    try:
        r = processo(["crontab", "-"], input="\n".join(linhas) + "\n", text=True)
    except OSError:
        raise ErroUso(SEM_CRONTAB) from None
    if r.returncode != 0:
        raise ErroUso(f"o crontab recusou a alteração: {r.stderr.strip()[-300:]}")


def linux_instalar(marca: str, python: str) -> None:
    marcadores = {marcador_cron(marca, t) for t in TAREFAS}
    mantidas = [l for l in crontab_atual() if not any(l.rstrip().endswith(m) for m in marcadores)]
    gravar_crontab(mantidas + [linha_cron(marca, t, python) for t in TAREFAS])
    for t in TAREFAS:
        print(f"Criada: {marcador_cron(marca, t)[2:]}")


def linux_remover(marca: str) -> None:
    marcadores = {marcador_cron(marca, t) for t in TAREFAS}
    atual = crontab_atual()
    mantidas = [l for l in atual if not any(l.rstrip().endswith(m) for m in marcadores)]
    if len(mantidas) != len(atual):
        gravar_crontab(mantidas)
        print(f"Removidas {len(atual) - len(mantidas)} linha(s) do cron desta marca.")
    else:
        print("Não havia linhas desta marca no cron.")


# ---------------------------------------------------------------- estado e comandos

def instalada(marca: str) -> bool | None:
    """True se as duas tarefas existem, False se falta alguma, None se não deu para saber."""
    try:
        so = sistema()
        if so == "windows":
            achadas = [windows_existe(nome_windows(marca, t)) for t in TAREFAS]
            return None if None in achadas else all(achadas)
        if so == "macos":
            return all(arquivo_plist(marca, t).is_file() for t in TAREFAS)
        texto = "\n".join(crontab_atual())
        return all(marcador_cron(marca, t) in texto for t in TAREFAS)
    except (OSError, ErroUso, subprocess.SubprocessError):
        return None


def mostrar(args) -> int:
    marca = escolher_marca(args.marca)
    python = interpretador(args.python)
    so = sistema()
    nota_so = ""
    print(f"Sistema: {so} | Marca: {marca} | Python: {python}")
    print("A rotina roda COM O COMPUTADOR LIGADO e a sua sessão aberta. Se ele estiver desligado na hora, o post agendado "
          "ainda sai até 2 h depois; passou disso, não é publicado e fica registrado.\n")
    for t in TAREFAS:
        nome = {"windows": nome_windows, "macos": rotulo_launchd}.get(so, lambda m, x: marcador_cron(m, x)[2:])(marca, t)
        if so == "windows":
            existe = windows_existe(nome)
        elif so == "macos":
            existe = arquivo_plist(marca, t).is_file()
        else:
            try:
                existe = marcador_cron(marca, t) in "\n".join(crontab_atual())
            except ErroUso as e:
                existe, nota_so = None, str(e)
        estado = "não consegui saber" if existe is None else ("JÁ INSTALADA" if existe else "não instalada")
        print(f"- {nome}: {t['quando']}, {t['texto']} [{estado}]")
        print(f"    {python} {' '.join(argumentos(marca, t))}")
    if nota_so:
        print(f"\nAVISO: {nota_so}")
    if so == "macos":
        print("\nAviso do macOS: se o projeto estiver em Documentos, Mesa ou outra pasta protegida, o sistema pode "
              "bloquear a rotina. Prefira uma pasta fora delas ou libere o Python em Ajustes > Privacidade e Segurança.")
    print(f"\nLog das execuções: marcas/{marca}/publicacao/logs/rotina-AAAA-MM.log")
    print("Nada foi criado. Para instalar (quem roda é você, no seu terminal), na raiz do projeto:")
    print(f"  python{'' if so == 'windows' else '3'} -X utf8 skills/publicar-instagram/scripts/rotina.py instalar --marca {marca}")
    return 0


def instalar(args) -> int:
    marca = escolher_marca(args.marca)
    python = interpretador(args.python)
    for t in TAREFAS:
        if not (PASTA_SCRIPTS / t["script"]).is_file():
            raise Recusa(f"não achei {t['script']} ao lado deste script")
    try:
        {"windows": windows_instalar, "macos": macos_instalar, "linux": linux_instalar}[sistema()](marca, python)
    except OSError as e:
        raise ErroUso(f"não achei um programa do sistema que a rotina precisa ({e.filename or e.strerror}). Nada foi criado. "
                      "Veja referencias/rotina.md") from None
    print("Pronto. A rotina só roda com o computador ligado e a sessão aberta.")
    print(f"Para conferir: rotina.py mostrar --marca {marca}. Para tirar: rotina.py remover --marca {marca}.")
    return 0


def remover(args) -> int:
    marca = escolher_marca(args.marca)
    try:
        {"windows": windows_remover, "macos": macos_remover, "linux": linux_remover}[sistema()](marca)
    except OSError as e:
        raise ErroUso(f"não achei um programa do sistema que a rotina precisa ({e.filename or e.strerror}). Nada foi "
                      "removido. Veja referencias/rotina.md") from None
    return 0


def main(argv=None) -> int:
    proteger_saida()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcao_raiz(p)
    sub = p.add_subparsers(dest="comando", required=True)
    for nome, ajuda in (("mostrar", "mostra o que seria criado e o estado atual"),
                        ("instalar", "cria as tarefas (quem roda é a pessoa)"),
                        ("remover", "remove as tarefas")):
        s = sub.add_parser(nome, help=ajuda)
        s.add_argument("--marca", help="slug da marca (pode omitir se houver só uma além de 'exemplo')")
        s.add_argument("--python", help="caminho do interpretador Python (padrão: o que está rodando este script)")
        opcao_raiz(s, subcomando=True)
    a = p.parse_args(argv)
    aplicar_raiz(a)
    return {"mostrar": mostrar, "instalar": instalar, "remover": remover}[a.comando](a)


if __name__ == "__main__":
    executar(main)
