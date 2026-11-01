"""Confirmação por uma pessoa, fora do agente de IA.

Ações que o agente não pode decidir sozinho passam por aqui: aprovar a publicação de uma versão, publicar de novo um post
que já saiu e afirmar que um post não foi ao ar. Uma janela local mostra o resumo, com os botões Aprovar e Cancelar. Sem
janela (sem tkinter ou sem tela), pergunta no terminal, mas só se houver um terminal interativo e a pessoa digitar o id do
post. Sem nenhum dos dois, recusa e manda a pessoa rodar o comando num terminal.

Não existe opção de linha de comando nem variável de ambiente que pule esta confirmação. Os testes automáticos trocam a
função `confirmar_com_a_pessoa` do publicar.py dentro do próprio processo.
Não é um script para rodar; é importado pelo publicar.py.
"""

from __future__ import annotations

import os
import sys

from _comum import Recusa

ESPERA_S = 300
MENSAGEM_SEM_PESSOA = ("esta ação precisa da confirmação de uma pessoa, numa janela ou num terminal interativo, e aqui "
                       "não há nenhum dos dois: rode este comando você mesma, num terminal. Nada foi alterado")


class SemJanela(Exception):
    """tkinter ausente ou sem tela para mostrar a janela."""


def _janela(titulo: str, linhas: list[tuple[str, str]], botao: str, espera_s: int) -> bool:
    try:
        import tkinter as tk
        janela = tk.Tk()
    except Exception as e:  # sem tkinter (ImportError) ou sem tela (TclError)
        raise SemJanela(type(e).__name__) from None
    resultado = {"ok": False}

    def aprovar():
        resultado["ok"] = True
        janela.destroy()

    def cancelar(_evento=None):
        janela.destroy()

    try:
        janela.title(titulo)
        try:
            janela.attributes("-topmost", True)
        except Exception:
            pass
        janela.protocol("WM_DELETE_WINDOW", cancelar)
        tk.Label(janela, text=titulo, font=("TkDefaultFont", 12, "bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, padx=18, pady=(16, 2), sticky="w")
        tk.Label(janela, justify="left", anchor="w", wraplength=600,
                 text=f"Confira o que será registrado. Só clique em \"{botao}\" se for você, a pessoa responsável pelo perfil, "
                      f"decidindo. A janela se fecha sozinha, sem registrar nada, em {espera_s // 60} minutos.").grid(
            row=1, column=0, columnspan=2, padx=18, pady=(0, 10), sticky="w")
        linha = 2
        for rotulo, valor in linhas:
            tk.Label(janela, text=f"{rotulo}:", font=("TkDefaultFont", 9, "bold"), anchor="ne").grid(
                row=linha, column=0, sticky="ne", padx=(18, 8), pady=2)
            tk.Label(janela, text=valor, anchor="w", justify="left", wraplength=480).grid(
                row=linha, column=1, sticky="w", padx=(0, 18), pady=2)
            linha += 1
        quadro = tk.Frame(janela)
        quadro.grid(row=linha, column=0, columnspan=2, pady=16)
        botao_cancelar = tk.Button(quadro, text="Cancelar", width=14, command=cancelar)
        botao_ok = tk.Button(quadro, text=botao, width=26, command=aprovar)
        botao_cancelar.pack(side="left", padx=8)
        botao_ok.pack(side="left", padx=8)
        janela.bind("<Escape>", cancelar)
        botao_cancelar.focus_set()  # o foco inicial é o Cancelar: apertar Enter ou espaço sem querer não aprova
        janela.after(espera_s * 1000, cancelar)
    except Exception as e:
        try:
            janela.destroy()
        except Exception:
            pass
        raise SemJanela(type(e).__name__) from None
    janela.mainloop()
    return resultado["ok"]


def _terminal(titulo: str, linhas: list[tuple[str, str]], id_post: str) -> bool:
    print()
    print("=" * 64)
    print(titulo.upper())
    for rotulo, valor in linhas:
        print(f"  {rotulo}: {valor}")
    print("Para confirmar, digite o id do post e aperte Enter. Para cancelar, aperte só Enter.")
    sys.stdout.write("> ")
    sys.stdout.flush()
    resposta = sys.stdin.readline()
    return resposta.strip() == id_post


def terminal_interativo() -> bool:
    """Há um terminal de verdade lendo o teclado? No Windows, o dispositivo NUL também diz que é terminal
    (isatty() verdadeiro), então confere se a entrada é mesmo um console."""
    try:
        if sys.stdin is None or not sys.stdin.isatty():
            return False
    except (AttributeError, ValueError):
        return False
    if os.name == "nt" and sys.stdin is sys.__stdin__:
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.GetStdHandle.restype = ctypes.c_void_p
            modo = ctypes.c_uint()
            return bool(kernel.GetConsoleMode(ctypes.c_void_p(kernel.GetStdHandle(-10)), ctypes.byref(modo)))
        except Exception:
            return False
    return True


def pedir(titulo: str, linhas: list[tuple[str, str]], id_post: str, botao: str = "Aprovar", espera_s: int = ESPERA_S) -> bool:
    """True só se a pessoa confirmou. Levanta Recusa se não houver como perguntar a uma pessoa."""
    try:
        return _janela(titulo, linhas, botao, espera_s)
    except SemJanela:
        pass
    if terminal_interativo():
        return _terminal(titulo, linhas, id_post)
    raise Recusa(MENSAGEM_SEM_PESSOA)
