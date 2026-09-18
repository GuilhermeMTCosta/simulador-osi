# -*- coding: utf-8 -*-
"""Ponto de entrada do simulador.

    python main.py            abre a interface grafica
    python main.py --texto    executa os sete cenarios no terminal

Qualquer falha inesperada e mostrada em uma caixa de mensagem, para a janela
nao fechar sozinha.
"""

from __future__ import annotations

import os
import sys
import traceback

# Permite executar este arquivo de qualquer pasta, sem depender do diretorio
# de trabalho corrente e sem nenhum caminho absoluto escrito no codigo.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _modo_texto() -> int:
    """Executa os sete cenarios e imprime o registro de cada um."""
    from simulador import cenarios
    from simulador.rede import ErroTopologia, Topologia

    try:
        topologia = Topologia()
    except ErroTopologia as erro:
        print(erro)
        return 1

    for cenario in cenarios.CENARIOS:
        resultado = cenarios.executar(topologia, cenario.identificador)
        print("=" * 78)
        print(cenario.rotulo)
        print("-" * 78)
        for linha in resultado.registro.linhas():
            print(linha)
        print("-" * 78)
        print("caminho: " + " -> ".join(resultado.caminho))
        for linha in resultado.resumo_texto():
            print(linha)
        print()
    return 0


def _relatar_falha(excecao: BaseException) -> None:
    """Mostra a falha ao usuario sem deixar a janela fechar sozinha."""
    detalhe = "".join(traceback.format_exception(excecao))
    try:
        import tkinter as tk
        from tkinter import messagebox

        auxiliar = tk.Tk()
        auxiliar.withdraw()
        messagebox.showerror(
            "Simulador do Modelo OSI",
            "O programa encontrou um erro inesperado.\n\n"
            f"{type(excecao).__name__}: {excecao}\n\n"
            "Detalhes tecnicos:\n" + detalhe[-1200:],
        )
        auxiliar.destroy()
    except Exception:                                    # pragma: no cover
        print(detalhe)
        input("Pressione Enter para fechar...")


def main() -> int:
    if "--texto" in sys.argv or "-t" in sys.argv:
        return _modo_texto()

    from simulador.visual import JanelaPrincipal

    JanelaPrincipal().executar()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as excecao:                     # noqa: BLE001
        _relatar_falha(excecao)
        sys.exit(1)
