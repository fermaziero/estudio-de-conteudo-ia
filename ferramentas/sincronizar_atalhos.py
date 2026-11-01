"""Gera os atalhos das skills para o Claude Code e o Codex.

A fonte única de cada skill é skills/<nome>/SKILL.md. Este script copia o
frontmatter (name e description) para:
  .claude/skills/<nome>/SKILL.md   (o Claude Code procura skills aqui)
  .agents/skills/<nome>/SKILL.md   (o Codex procura skills aqui)
O corpo do atalho só manda o agente ler a skill original.

Uso:
  python -X utf8 ferramentas/sincronizar_atalhos.py           gera ou atualiza
  python -X utf8 ferramentas/sincronizar_atalhos.py --checar  só confere (saída 1 se estiver desatualizado)
"""

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SKILLS = RAIZ / "skills"
DESTINOS = [RAIZ / ".claude" / "skills", RAIZ / ".agents" / "skills"]
MARCA = "<!-- Atalho gerado por ferramentas/sincronizar_atalhos.py. Não edite aqui: edite skills/{nome}/SKILL.md e rode o script de novo. -->"
NOME_VALIDO = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def ler_frontmatter(arquivo):
    texto = arquivo.read_text(encoding="utf-8")
    partes = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", texto, re.S)
    if not partes:
        raise ValueError("sem frontmatter (o arquivo precisa começar com --- e ter name e description)")
    bloco = partes.group(1)
    nome = re.search(r"^name:\s*(.+?)\s*$", bloco, re.M)
    descricao = re.search(r"^description:\s*(.*)$", bloco, re.M)
    if not nome:
        raise ValueError("frontmatter sem o campo name")
    if not descricao:
        raise ValueError("frontmatter sem o campo description")
    return bloco, nome.group(1).strip().strip("'\""), descricao


def conteudo_atalho(bloco, nome):
    return (
        f"---\n{bloco}\n---\n\n"
        f"{MARCA.format(nome=nome)}\n\n"
        f"# {nome}\n\n"
        f"Esta skill fica em `skills/{nome}/`. Antes de qualquer outra ação, leia `skills/{nome}/SKILL.md` "
        f"inteiro e siga as instruções de lá. Os caminhos citados nela são relativos à raiz do projeto.\n"
    )


def coletar_skills():
    problemas, skills = [], {}
    if not PASTA_SKILLS.is_dir():
        return {}, ["pasta skills/ não encontrada"]
    for pasta in sorted(p for p in PASTA_SKILLS.iterdir() if p.is_dir()):
        arquivo = pasta / "SKILL.md"
        if not arquivo.is_file():
            problemas.append(f"skills/{pasta.name}: falta o SKILL.md")
            continue
        try:
            bloco, nome, _ = ler_frontmatter(arquivo)
        except ValueError as erro:
            problemas.append(f"skills/{pasta.name}/SKILL.md: {erro}")
            continue
        if nome != pasta.name:
            problemas.append(f"skills/{pasta.name}/SKILL.md: name '{nome}' diferente do nome da pasta")
            continue
        if not NOME_VALIDO.match(nome) or len(nome) > 64:
            problemas.append(f"skills/{pasta.name}: nome inválido (use minúsculas, números e hífen, até 64 caracteres)")
            continue
        skills[nome] = conteudo_atalho(bloco, nome)
    return skills, problemas


def atalhos_existentes(destino):
    if not destino.is_dir():
        return {}
    encontrados = {}
    for pasta in destino.iterdir():
        arquivo = pasta / "SKILL.md"
        if pasta.is_dir() and arquivo.is_file():
            encontrados[pasta.name] = arquivo
    return encontrados


def main():
    parser = argparse.ArgumentParser(description="Gera ou confere os atalhos das skills em .claude/skills e .agents/skills.")
    parser.add_argument("--checar", action="store_true", help="só confere; não grava nada")
    args = parser.parse_args()

    skills, problemas = coletar_skills()
    for problema in problemas:
        print(f"ERRO: {problema}")

    desatualizados, gravados, removidos = [], [], []
    for destino in DESTINOS:
        rotulo = destino.relative_to(RAIZ).as_posix()
        existentes = atalhos_existentes(destino)
        for nome, conteudo in skills.items():
            alvo = destino / nome / "SKILL.md"
            atual = alvo.read_text(encoding="utf-8") if alvo.is_file() else None
            if atual == conteudo:
                continue
            if args.checar:
                desatualizados.append(f"{rotulo}/{nome}")
                continue
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding="utf-8", newline="\n")
            gravados.append(f"{rotulo}/{nome}")
        for nome, arquivo in existentes.items():
            if nome in skills:
                continue
            gerado = MARCA.split("{nome}")[0] in arquivo.read_text(encoding="utf-8")
            if not gerado:
                print(f"AVISO: {rotulo}/{nome} não foi gerado por este script; deixei como está.")
                continue
            if args.checar:
                desatualizados.append(f"{rotulo}/{nome} (skill não existe mais)")
                continue
            arquivo.unlink()
            try:
                arquivo.parent.rmdir()
            except OSError:
                pass
            removidos.append(f"{rotulo}/{nome}")

    if args.checar:
        if desatualizados:
            print("Atalhos desatualizados: " + ", ".join(desatualizados))
            print("Rode: python -X utf8 ferramentas/sincronizar_atalhos.py")
        elif not problemas:
            print(f"OK: {len(skills)} skill(s), atalhos em dia.")
        return 1 if (desatualizados or problemas) else 0

    for item in gravados:
        print(f"gravado: {item}/SKILL.md")
    for item in removidos:
        print(f"removido: {item}/SKILL.md")
    print(f"Pronto: {len(skills)} skill(s) sincronizada(s).")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
