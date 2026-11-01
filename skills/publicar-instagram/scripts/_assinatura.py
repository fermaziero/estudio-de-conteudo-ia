"""Assinatura das aprovações: HMAC-SHA256 com uma chave que fica fora do projeto.

A janela de confirmação protege o COMANDO `aprovar`, mas o arquivo do post é texto: sem uma assinatura, alguém poderia
gravar à mão `status: "aprovado"` e um hash calculado (o hash não tem chave). Por isso, depois da confirmação da pessoa,
o `aprovar` assina a aprovação com uma chave aleatória deste computador, e todos os comandos que agem sobre um post
aprovado (simular, agendar, publicar, agendados, conferir) conferem a assinatura. Sem assinatura válida, o post vale
como não aprovado.

A chave (32 bytes aleatórios, em hexadecimal) fica em ~/.config/estudio-de-conteudo/<marca>/aprovacao.key (ou na pasta
de ESTUDIO_CONFIG), com permissão só do dono, e é criada na primeira aprovação. Nunca é impressa nem copiada para o
projeto. Se ela sumir (computador novo, arquivo apagado), as aprovações antigas perdem a validade e a pessoa aprova de
novo.

Limite honesto: quem tem controle total do computador pode ler a chave e assinar sozinho. As regras do projeto proíbem
isso; a assinatura impede o contorno por texto (editar o JSON), não o de quem executa código na máquina da pessoa.

Não é um script para rodar; é importado pelo publicar.py.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from _comum import ErroUso, pasta_config, registrar_segredos, restringir_permissao

CONTEXTO = "estudio-de-conteudo-ia/aprovacao/v1"
CAMPOS = ("hash", "frase", "data", "por")
MENSAGEM_REAPROVAR = "aprovação sem assinatura válida: rode `aprovar` de novo; ele abre a janela para você confirmar"

MOTIVO_CHAVE = {
    "ausente": "este computador ainda não tem a chave de aprovação, que é criada na primeira aprovação feita aqui",
    "defeituosa": "a chave de aprovação deste computador está com defeito: arquivo cortado ou alterado",
    "ilegivel": "não consegui ler a chave de aprovação: arquivo em uso ou sem permissão",
}


class Veredito(NamedTuple):
    """valida: a assinatura confere. definitiva: a chave foi lida e a assinatura falta ou não confere (não é problema
    passageiro com a chave), então o chamador pode derrubar a aprovação com segurança."""
    valida: bool
    motivo: str = ""
    definitiva: bool = False


def arquivo_chave(marca: str) -> Path:
    return pasta_config(marca) / "aprovacao.key"


def carregar_chave(marca: str) -> tuple[bytes | None, str]:
    """(chave, estado). Estado: ok, ausente, defeituosa ou ilegivel. Registra a chave no filtro de segredos."""
    try:
        texto = arquivo_chave(marca).read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None, "ausente"
    except UnicodeDecodeError:
        return None, "defeituosa"
    except OSError:
        return None, "ilegivel"
    try:
        chave = bytes.fromhex(texto)
    except ValueError:
        return None, "defeituosa"
    if len(chave) != 32:
        return None, "defeituosa"
    registrar_segredos([texto, chave.hex()])
    return chave, "ok"


def esperar_outra_criacao(marca: str) -> bytes | None:
    """Arquivo vazio = outra execução está no meio de criar a chave (duas aprovações começaram juntas). Espera até 2 s
    por ela e devolve a chave dela; se o arquivo tem conteúdo que não vale, ou o tempo acaba, devolve None."""
    for _ in range(20):
        chave, _estado = carregar_chave(marca)
        if chave is not None:
            return chave
        try:
            if arquivo_chave(marca).stat().st_size > 0:
                return None
        except OSError:
            return None
        time.sleep(0.1)
    return None


def chave_ou_criar(marca: str) -> tuple[bytes, str]:
    """A chave da marca; cria na primeira aprovação. Devolve (chave, situação): existente, criada ou substituida."""
    chave, estado = carregar_chave(marca)
    if chave is not None:
        return chave, "existente"
    arq = arquivo_chave(marca)
    if estado == "ilegivel":
        raise ErroUso(MOTIVO_CHAVE["ilegivel"] + ". Feche o programa que a usa e rode de novo; nada foi alterado")
    situacao = "criada"
    if estado == "defeituosa":
        chave = esperar_outra_criacao(marca)
        if chave is not None:
            return chave, "existente"
        # nada se apaga: o arquivo com defeito fica de lado e uma chave nova assume
        arq.replace(arq.with_name(f"aprovacao.key.defeituosa-{datetime.now():%Y%m%d-%H%M%S}"))
        situacao = "substituida"
    arq.parent.mkdir(parents=True, exist_ok=True)
    restringir_permissao(arq.parent)
    chave = secrets.token_bytes(32)
    try:
        descritor = os.open(arq, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:  # outra execução criou a chave neste instante: usa a dela
        outra = esperar_outra_criacao(marca)
        if outra is not None:
            return outra, "existente"
        raise ErroUso("não consegui criar a chave de aprovação: já existe um arquivo com esse nome que ainda não está "
                      "pronto ou não serve. Rode de novo em alguns segundos") from None
    try:
        with os.fdopen(descritor, "w", encoding="ascii", newline="\n") as f:
            f.write(chave.hex() + "\n")
    except BaseException:
        arq.unlink(missing_ok=True)
        raise
    restringir_permissao(arq)
    registrar_segredos([chave.hex()])
    return chave, situacao


def mensagem(post_id: str, hash_: str, frase: str, data: str, por: str) -> bytes:
    """O que é assinado: id do post, hash da versão, frase, data e quem aprovou, em JSON canônico (sem ambiguidade)."""
    corpo = {"contexto": CONTEXTO, "id": post_id, "hash": hash_, "frase": frase, "data": data, "por": por}
    return json.dumps(corpo, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def assinar(chave: bytes, post_id: str, aprovacao: dict) -> str:
    """HMAC-SHA256 (hexadecimal) sobre os campos hash, frase, data e por da aprovação e o id do post."""
    return hmac.new(chave, mensagem(post_id, *(aprovacao[c] for c in CAMPOS)), hashlib.sha256).hexdigest()


def verificar(marca: str, post_id: str, aprovacao) -> Veredito:
    """Confere a assinatura de `aprovacao` para este post com a chave deste computador."""
    if not isinstance(aprovacao, dict):
        return Veredito(False, "o post não tem aprovação registrada")
    chave, estado = carregar_chave(marca)
    if chave is None:
        return Veredito(False, MOTIVO_CHAVE[estado])
    assinatura = aprovacao.get("assinatura")
    if not isinstance(assinatura, str) or not assinatura:
        return Veredito(False, "a aprovação não tem assinatura", True)
    if not all(isinstance(aprovacao.get(c), str) and aprovacao.get(c) for c in CAMPOS):
        return Veredito(False, "o registro da aprovação está incompleto", True)
    try:
        esperada = assinar(chave, post_id, aprovacao)
    except ValueError:  # texto com caracteres que o JSON/UTF-8 não representa (UnicodeError é um ValueError)
        return Veredito(False, "o registro da aprovação tem caracteres que não consigo assinar", True)
    if not hmac.compare_digest(esperada.encode("ascii"), assinatura.encode("utf-8")):
        return Veredito(False, "a assinatura não confere com este registro: ele foi alterado, ou a aprovação veio de "
                               "outro post, de outra versão ou de outro computador", True)
    return Veredito(True)
