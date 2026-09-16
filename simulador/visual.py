# -*- coding: utf-8 -*-
"""Interface grafica do simulador.

A interface le a lista de eventos produzida pelo motor e desenha a tela a
partir dela. Ela nao conhece as classes de camada, nao as instancia e nao
chama nenhum metodo delas: se este arquivo fosse apagado, o simulador
continuaria funcionando em modo texto.

Cada requisito de visualizacao do enunciado tem um lugar proprio na tela:

    V1  mapa da rede ................ `_desenhar_mapa`
    V2  pilhas de camadas ........... `_desenhar_pilhas`
    V3  unidade de dados desenhada .. `_desenhar_unidade`
    V4  os dois pares de enderecos .. `_atualizar_enderecos`
    V5  controle de execucao ........ `_passo_adiante`, `_alternar_execucao`
    V6  registro de eventos ......... `_preencher_registro`, `_salvar_registro`
    V7  alternancia entre pilhas .... `_trocar_modo_pilha`
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from . import cenarios, config, relatorio
from .eventos import Evento
from .motor import Fluxo, Motor, ResultadoSimulacao
from .rede import ErroTopologia, Topologia

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------

FUNDO = "#eef1f5"
PAPEL = "#ffffff"
TINTA = "#1b1f24"
SUAVE = "#5b6672"
BORDA = "#c6cedb"
DESTAQUE = "#1f5fa8"
ERRO = "#b3261e"
SUCESSO = "#1d7a46"
TELA = "#fbfcfe"

CORES_CAMADA: dict[int, str] = {
    7: "#c9d9f0", 6: "#d3d0ee", 5: "#dccdea", 4: "#f0d6cf",
    3: "#cfe6d6", 2: "#f4e3c3", 1: "#dfe3e8",
}
NOMES_CAMADA: dict[int, str] = {
    7: "Aplicacao", 6: "Apresentacao", 5: "Sessao", 4: "Transporte",
    3: "Rede", 2: "Enlace", 1: "Fisica",
}

# Agrupamento do requisito V7: as camadas 5 a 7 viram uma so na pilha TCP/IP.
GRUPOS_TCPIP: list[tuple[str, tuple[int, ...]]] = [
    ("Aplicacao", (7, 6, 5)),
    ("Transporte", (4,)),
    ("Rede", (3,)),
    ("Enlace", (2,)),
    ("Fisica", (1,)),
]

FONTE = ("Segoe UI", 9)
FONTE_TITULO = ("Segoe UI", 9, "bold")
FONTE_MONO = ("Consolas", 9)
FONTE_MONO_P = ("Consolas", 8)

DESTINO_LIVRE = "outro endereco..."


class JanelaPrincipal:
    """Janela unica do simulador."""

    # -----------------------------------------------------------------
    # Construcao
    # -----------------------------------------------------------------

    def __init__(self) -> None:
        self.raiz = tk.Tk()
        self.raiz.title(config.NOME_PROGRAMA)
        self.raiz.geometry("1380x880")
        self.raiz.minsize(1120, 720)
        self.raiz.configure(background=FUNDO)

        self.topologia: Topologia | None = None
        self.motor: Motor | None = None
        self.resultado: ResultadoSimulacao | None = None
        self.cenario_atual: cenarios.Cenario | None = None
        self.indice: int = -1
        self.executando: bool = False
        self._tarefa: str | None = None
        self._erro_topologia: str = ""

        self._configurar_estilo()
        self._carregar_topologia_inicial()
        self._construir()
        self._popular_campos()
        self._limpar_tela()

        if self._erro_topologia:
            self.raiz.after(200, lambda: messagebox.showerror(
                "Topologia", self._erro_topologia, parent=self.raiz))

    def _configurar_estilo(self) -> None:
        estilo = ttk.Style()
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure(".", background=FUNDO, foreground=TINTA, font=FONTE)
        estilo.configure("TFrame", background=FUNDO)
        estilo.configure("TLabelframe", background=FUNDO, bordercolor=BORDA)
        estilo.configure("TLabelframe.Label", background=FUNDO,
                         foreground=DESTAQUE, font=FONTE_TITULO)
        estilo.configure("TLabel", background=FUNDO)
        estilo.configure("Suave.TLabel", foreground=SUAVE)
        estilo.configure("Mono.TLabel", font=FONTE_MONO, background=PAPEL)
        estilo.configure("TButton", padding=(8, 3))
        estilo.configure("Acao.TButton", padding=(10, 4), font=FONTE_TITULO)
        estilo.configure("TCheckbutton", background=FUNDO)
        estilo.configure("TRadiobutton", background=FUNDO)
        estilo.configure("Treeview", rowheight=20, fieldbackground=PAPEL,
                         background=PAPEL, font=FONTE_MONO_P)
        estilo.configure("Treeview.Heading", font=FONTE_TITULO)

    def _carregar_topologia_inicial(self) -> None:
        try:
            self.topologia = Topologia()
            self.motor = Motor(self.topologia)
        except ErroTopologia as erro:
            self._erro_topologia = str(erro)
            self.topologia = None
            self.motor = None
        self._atualizar_titulo()

    def _atualizar_titulo(self) -> None:
        """Escreve na barra de titulo qual rede esta carregada.

        Assim, substituir `topologia.json` ao lado do executavel se torna
        visivel sem precisar abrir nenhuma janela auxiliar.
        """
        rede = self.topologia.nome if self.topologia else "nenhuma rede carregada"
        self.raiz.title(f"{config.NOME_PROGRAMA} {config.VERSAO}  -  "
                        f"rede: {rede}  -  {config.AUTORIA}")

    # -----------------------------------------------------------------
    # Montagem da tela
    # -----------------------------------------------------------------

    def _construir(self) -> None:
        raiz = ttk.Frame(self.raiz, padding=8)
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(1, weight=1)

        self._construir_controles(raiz)

        corpo = ttk.PanedWindow(raiz, orient="horizontal")
        corpo.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        esquerda = ttk.Frame(corpo)
        esquerda.columnconfigure(0, weight=1)
        esquerda.rowconfigure(0, weight=1)
        corpo.add(esquerda, weight=3)

        direita = ttk.Frame(corpo)
        direita.columnconfigure(0, weight=1)
        direita.rowconfigure(0, weight=3)
        direita.rowconfigure(1, weight=2)
        corpo.add(direita, weight=2)

        self._construir_mapa(esquerda)
        self._construir_unidade(esquerda)
        self._construir_enderecos(esquerda)
        self._construir_pilhas(direita)
        self._construir_registro(direita)
        self._construir_rodape(raiz)

    # -- barra de controles ---------------------------------------------

    def _construir_controles(self, pai: ttk.Frame) -> None:
        caixa = ttk.LabelFrame(pai, text="Configuracao da simulacao", padding=8)
        caixa.grid(row=0, column=0, sticky="ew")
        for coluna in (1, 3, 5, 9):
            caixa.columnconfigure(coluna, weight=1)

        # --- linha 1: cenario, origem, destino
        ttk.Label(caixa, text="Cenario").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.var_cenario = tk.StringVar()
        self.combo_cenario = ttk.Combobox(caixa, textvariable=self.var_cenario,
                                          state="readonly", width=42)
        self.combo_cenario.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(0, 6))
        self.combo_cenario.bind("<<ComboboxSelected>>", self._ao_escolher_cenario)

        ttk.Button(caixa, text="Carregar cenario",
                   command=self._carregar_cenario).grid(row=0, column=4, padx=(0, 12))

        ttk.Label(caixa, text="Origem").grid(row=0, column=5, sticky="w", padx=(0, 4))
        self.var_origem = tk.StringVar()
        self.combo_origem = ttk.Combobox(caixa, textvariable=self.var_origem,
                                         state="readonly", width=8)
        self.combo_origem.grid(row=0, column=6, sticky="w", padx=(0, 10))

        ttk.Label(caixa, text="Destino").grid(row=0, column=7, sticky="w", padx=(0, 4))
        self.var_destino = tk.StringVar()
        self.combo_destino = ttk.Combobox(caixa, textvariable=self.var_destino,
                                          state="readonly", width=20)
        self.combo_destino.grid(row=0, column=8, sticky="w", padx=(0, 6))
        self.combo_destino.bind("<<ComboboxSelected>>", self._ao_escolher_destino)

        self.var_ip = tk.StringVar()
        self.entrada_ip = ttk.Entry(caixa, textvariable=self.var_ip,
                                    width=14, font=FONTE_MONO)
        self.entrada_ip.grid(row=0, column=9, sticky="w")

        # --- linha 2: processos e mensagem
        ttk.Label(caixa, text="Processos").grid(row=1, column=0, sticky="w",
                                                padx=(0, 4), pady=(6, 0))
        self.var_proc_origem = tk.StringVar()
        self.combo_proc_origem = ttk.Combobox(caixa, textvariable=self.var_proc_origem,
                                              state="readonly", width=14)
        self.combo_proc_origem.grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(caixa, text="→").grid(row=1, column=2, pady=(6, 0))
        self.var_proc_destino = tk.StringVar()
        self.combo_proc_destino = ttk.Combobox(caixa, textvariable=self.var_proc_destino,
                                               state="readonly", width=14)
        self.combo_proc_destino.grid(row=1, column=3, sticky="w", pady=(6, 0))

        ttk.Label(caixa, text="Mensagem").grid(row=1, column=4, sticky="e",
                                               padx=(0, 4), pady=(6, 0))
        self.var_mensagem = tk.StringVar()
        ttk.Entry(caixa, textvariable=self.var_mensagem, font=FONTE_MONO).grid(
            row=1, column=5, columnspan=4, sticky="ew", pady=(6, 0))
        self.rotulo_tamanho = ttk.Label(caixa, text="0 B", style="Suave.TLabel")
        self.rotulo_tamanho.grid(row=1, column=9, sticky="w", padx=(6, 0), pady=(6, 0))
        self.var_mensagem.trace_add("write", self._ao_mudar_mensagem)

        # --- linha 3: falhas
        falhas = ttk.Frame(caixa)
        falhas.grid(row=2, column=0, columnspan=10, sticky="ew", pady=(8, 0))

        self.var_derrubar = tk.BooleanVar(value=False)
        ttk.Checkbutton(falhas, text="Derrubar enlace", variable=self.var_derrubar,
                        command=self._atualizar_mapa_estatico).pack(side="left")
        self.var_enlace_queda = tk.StringVar()
        self.combo_queda = ttk.Combobox(falhas, textvariable=self.var_enlace_queda,
                                        state="readonly", width=10)
        self.combo_queda.pack(side="left", padx=(4, 16))
        self.combo_queda.bind("<<ComboboxSelected>>",
                              lambda _e: self._atualizar_mapa_estatico())

        self.var_injetar = tk.BooleanVar(value=False)
        ttk.Checkbutton(falhas, text="Injetar erro de bit no enlace",
                        variable=self.var_injetar).pack(side="left")
        self.var_enlace_erro = tk.StringVar()
        self.combo_erro = ttk.Combobox(falhas, textvariable=self.var_enlace_erro,
                                       state="readonly", width=10)
        self.combo_erro.pack(side="left", padx=(4, 16))

        ttk.Button(falhas, text="Simular", style="Acao.TButton",
                   command=self._simular).pack(side="left", padx=(4, 0))

        ttk.Separator(falhas, orient="vertical").pack(side="left", fill="y", padx=14)

        ttk.Label(falhas, text="Pilha exibida:").pack(side="left", padx=(0, 6))
        self.var_pilha = tk.StringVar(value="OSI")
        ttk.Radiobutton(falhas, text="OSI (7 camadas)", value="OSI",
                        variable=self.var_pilha,
                        command=self._trocar_modo_pilha).pack(side="left")
        ttk.Radiobutton(falhas, text="TCP/IP (5 a 7 agrupadas)", value="TCPIP",
                        variable=self.var_pilha,
                        command=self._trocar_modo_pilha).pack(side="left", padx=(6, 0))

        # --- linha 4: execucao
        execucao = ttk.Frame(caixa)
        execucao.grid(row=3, column=0, columnspan=10, sticky="ew", pady=(8, 0))

        # Os rotulos sao escritos por extenso, sem simbolos, para que os
        # tutoriais possam nomear cada botao sem ambiguidade.
        self.botao_anterior = ttk.Button(execucao, text="Voltar passo",
                                         command=self._passo_atras, state="disabled")
        self.botao_anterior.pack(side="left")
        self.botao_proximo = ttk.Button(execucao, text="Avancar passo",
                                        command=self._passo_adiante, state="disabled")
        self.botao_proximo.pack(side="left", padx=(4, 12))
        self.botao_executar = ttk.Button(execucao, text="Executar",
                                         command=self._alternar_execucao,
                                         state="disabled")
        self.botao_executar.pack(side="left")
        self.botao_reiniciar = ttk.Button(execucao, text="Reiniciar",
                                          command=self._reiniciar, state="disabled")
        self.botao_reiniciar.pack(side="left", padx=(4, 12))
        self.botao_fim = ttk.Button(execucao, text="Ir ao fim",
                                    command=self._ir_ao_fim, state="disabled")
        self.botao_fim.pack(side="left", padx=(0, 16))

        ttk.Label(execucao, text="Velocidade").pack(side="left", padx=(0, 4))
        self.var_velocidade = tk.StringVar(
            value=config.VELOCIDADES[config.VELOCIDADE_PADRAO][0])
        ttk.Combobox(execucao, textvariable=self.var_velocidade, state="readonly",
                     width=12,
                     values=[rotulo for rotulo, _ in config.VELOCIDADES]).pack(
            side="left")

        self.rotulo_passo = ttk.Label(execucao, text="passo 0 de 0",
                                      style="Suave.TLabel")
        self.rotulo_passo.pack(side="right")

    # -- mapa -------------------------------------------------------------

    def _construir_mapa(self, pai: ttk.Frame) -> None:
        caixa = ttk.LabelFrame(pai, text="V1  Mapa da rede", padding=6)
        caixa.grid(row=0, column=0, sticky="nsew")
        caixa.columnconfigure(0, weight=1)
        caixa.rowconfigure(0, weight=1)

        self.mapa = tk.Canvas(caixa, background=TELA, highlightthickness=1,
                              highlightbackground=BORDA, height=320)
        self.mapa.grid(row=0, column=0, sticky="nsew")
        self.mapa.bind("<Configure>", lambda _e: self._redesenhar_mapa())

    # -- unidade de dados --------------------------------------------------

    def _construir_unidade(self, pai: ttk.Frame) -> None:
        caixa = ttk.LabelFrame(pai, text="V3  Unidade de dados corrente", padding=6)
        caixa.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        caixa.columnconfigure(0, weight=1)

        self.rotulo_unidade = ttk.Label(caixa, text="-", font=FONTE_TITULO)
        self.rotulo_unidade.grid(row=0, column=0, sticky="w")

        self.desenho = tk.Canvas(caixa, background=TELA, height=92,
                                 highlightthickness=1, highlightbackground=BORDA)
        self.desenho.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.desenho.bind("<Configure>", lambda _e: self._redesenhar_unidade())

    # -- enderecos ---------------------------------------------------------

    def _construir_enderecos(self, pai: ttk.Frame) -> None:
        caixa = ttk.LabelFrame(pai, text="V4  Os dois pares de enderecos", padding=6)
        caixa.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        caixa.columnconfigure(0, weight=1)
        caixa.columnconfigure(1, weight=1)

        logicos = tk.Frame(caixa, background="#e4efe7", highlightthickness=1,
                           highlightbackground=BORDA)
        logicos.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        tk.Label(logicos, text="Enderecos logicos  (camada 3, fim a fim)",
                 background="#e4efe7", foreground=SUCESSO,
                 font=FONTE_TITULO).pack(anchor="w", padx=8, pady=(6, 0))
        self.rotulo_logicos = tk.Label(logicos, text="-", background="#e4efe7",
                                       font=("Consolas", 11, "bold"))
        self.rotulo_logicos.pack(anchor="w", padx=8)
        self.rotulo_logicos_nota = tk.Label(
            logicos, text="inserido na origem, nao muda ate o destino",
            background="#e4efe7", foreground=SUAVE, font=("Segoe UI", 8))
        self.rotulo_logicos_nota.pack(anchor="w", padx=8, pady=(0, 6))

        fisicos = tk.Frame(caixa, background="#fbeddc", highlightthickness=1,
                           highlightbackground=BORDA)
        fisicos.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(fisicos, text="Enderecos fisicos  (camada 2, salto a salto)",
                 background="#fbeddc", foreground="#8a5a12",
                 font=FONTE_TITULO).pack(anchor="w", padx=8, pady=(6, 0))
        self.rotulo_fisicos = tk.Label(fisicos, text="-", background="#fbeddc",
                                       font=("Consolas", 11, "bold"))
        self.rotulo_fisicos.pack(anchor="w", padx=8)
        self.rotulo_fisicos_nota = tk.Label(
            fisicos, text="substituido a cada enlace", background="#fbeddc",
            foreground=SUAVE, font=("Segoe UI", 8))
        self.rotulo_fisicos_nota.pack(anchor="w", padx=8, pady=(0, 6))

    # -- pilhas ------------------------------------------------------------

    def _construir_pilhas(self, pai: ttk.Frame) -> None:
        self.caixa_pilhas = ttk.LabelFrame(
            pai, text="V2  Pilhas de camadas  /  V7  alternancia OSI - TCP/IP",
            padding=6)
        self.caixa_pilhas.grid(row=0, column=0, sticky="nsew")
        self.caixa_pilhas.columnconfigure(0, weight=1)
        self.caixa_pilhas.rowconfigure(0, weight=1)

        self.pilhas = tk.Canvas(self.caixa_pilhas, background=TELA,
                                highlightthickness=1, highlightbackground=BORDA)
        self.pilhas.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(self.caixa_pilhas, orient="horizontal",
                              command=self.pilhas.xview)
        barra.grid(row=1, column=0, sticky="ew")
        self.pilhas.configure(xscrollcommand=barra.set)
        self.pilhas.bind("<Configure>", lambda _e: self._redesenhar_pilhas())

    # -- registro ----------------------------------------------------------

    def _construir_registro(self, pai: ttk.Frame) -> None:
        caixa = ttk.LabelFrame(pai, text="V6  Registro de eventos", padding=6)
        caixa.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        caixa.columnconfigure(0, weight=1)
        caixa.rowconfigure(0, weight=1)

        self.registro = tk.Text(caixa, wrap="none", font=FONTE_MONO_P,
                                background=PAPEL, foreground=TINTA,
                                highlightthickness=1, highlightbackground=BORDA,
                                state="disabled", height=10)
        self.registro.grid(row=0, column=0, sticky="nsew")

        vertical = ttk.Scrollbar(caixa, orient="vertical",
                                 command=self.registro.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(caixa, orient="horizontal",
                                   command=self.registro.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.registro.configure(yscrollcommand=vertical.set,
                                xscrollcommand=horizontal.set)

        self.registro.tag_configure("atual", background="#fff2b8")
        self.registro.tag_configure("erro", foreground=ERRO)
        self.registro.tag_configure("sucesso", foreground=SUCESSO)
        self.registro.tag_configure("futuro", foreground="#9aa7b4")

    # -- rodape ------------------------------------------------------------

    def _construir_rodape(self, pai: ttk.Frame) -> None:
        caixa = ttk.LabelFrame(pai, text="Custo do empilhamento e acoes", padding=6)
        caixa.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        caixa.columnconfigure(0, weight=1)

        self.rotulo_eficiencia = tk.Label(
            caixa, text="Execute uma simulacao para ver o quadro numerico.",
            background=FUNDO, font=FONTE_MONO, justify="left", anchor="w")
        self.rotulo_eficiencia.grid(row=0, column=0, sticky="w")

        acoes = ttk.Frame(caixa)
        acoes.grid(row=0, column=1, sticky="e")
        ttk.Button(acoes, text="Salvar registro",
                   command=self._salvar_registro).pack(side="left", padx=2)
        ttk.Button(acoes, text="Exportar relatorio HTML",
                   command=self._exportar_html).pack(side="left", padx=2)
        ttk.Button(acoes, text="Tabelas de encaminhamento",
                   command=self._abrir_tabelas).pack(side="left", padx=2)
        ttk.Button(acoes, text="Trocar topologia",
                   command=self._trocar_topologia).pack(side="left", padx=2)
        ttk.Button(acoes, text="Convencoes",
                   command=self._abrir_convencoes).pack(side="left", padx=2)

    # -----------------------------------------------------------------
    # Preenchimento dos campos
    # -----------------------------------------------------------------

    def _popular_campos(self) -> None:
        self.combo_cenario["values"] = [c.rotulo for c in cenarios.CENARIOS]
        self.var_cenario.set(cenarios.CENARIOS[1].rotulo)   # E2, o caso central

        if self.topologia is None:
            return

        computadores = sorted(self.topologia.computadores())
        self.combo_origem["values"] = computadores
        destinos = [f"{nome}  {self.topologia.dispositivos[nome].ip_principal}"
                    for nome in computadores] + [DESTINO_LIVRE]
        self.combo_destino["values"] = destinos

        processos = sorted(self.topologia.processos)
        self.combo_proc_origem["values"] = processos
        self.combo_proc_destino["values"] = processos

        enlaces = [s.id for s in self.topologia.enlaces_comutaveis()]
        self.combo_queda["values"] = enlaces
        self.combo_erro["values"] = enlaces

        self._carregar_cenario()

    def _ao_escolher_cenario(self, _evento: Any = None) -> None:
        self._carregar_cenario()

    def _ao_escolher_destino(self, _evento: Any = None) -> None:
        escolha = self.var_destino.get()
        if escolha == DESTINO_LIVRE:
            self.entrada_ip.configure(state="normal")
            self.entrada_ip.focus_set()
        else:
            self.entrada_ip.configure(state="normal")
            self.var_ip.set(escolha.split()[-1] if escolha else "")
            self.entrada_ip.configure(state="readonly")

    def _ao_mudar_mensagem(self, *_args: Any) -> None:
        octetos = len(self.var_mensagem.get().encode(config.CODIFICACAO))
        self.rotulo_tamanho.configure(text=f"{octetos} B")

    def _cenario_selecionado(self) -> cenarios.Cenario | None:
        rotulo = self.var_cenario.get()
        for cenario in cenarios.CENARIOS:
            if cenario.rotulo == rotulo:
                return cenario
        return None

    def _carregar_cenario(self) -> None:
        """Preenche os campos com os parametros do cenario escolhido."""
        cenario = self._cenario_selecionado()
        if cenario is None or self.topologia is None:
            return
        self.cenario_atual = cenario
        parametros = cenario.montar(self.topologia)
        principal: Fluxo = parametros["fluxos"][0]

        self.var_origem.set(principal.origem)
        alvo = self.topologia.dispositivo_por_ip(principal.destino_ip)
        if alvo is not None:
            self.var_destino.set(f"{alvo.nome}  {alvo.ip_principal}")
        else:
            self.var_destino.set(DESTINO_LIVRE)
        self.var_ip.set(principal.destino_ip)
        self._ao_escolher_destino()

        self.var_proc_origem.set(principal.processo_origem)
        self.var_proc_destino.set(principal.processo_destino)
        self.var_mensagem.set(principal.texto)

        quedas = parametros.get("enlaces_derrubados") or []
        self.var_derrubar.set(bool(quedas))
        self.var_enlace_queda.set(quedas[0] if quedas else
                                  (self.combo_queda["values"] or [""])[0])

        erro = parametros.get("enlace_com_erro", "")
        self.var_injetar.set(bool(erro))
        self.var_enlace_erro.set(erro or (self.combo_erro["values"] or [""])[0])

        self._limpar_tela()
        self._atualizar_mapa_estatico()

    # -----------------------------------------------------------------
    # Execucao
    # -----------------------------------------------------------------

    def _simular(self) -> None:
        """Monta e executa a simulacao a partir dos campos da tela."""
        if self.topologia is None or self.motor is None:
            messagebox.showerror("Topologia", self._erro_topologia
                                 or "Nenhuma topologia carregada.",
                                 parent=self.raiz)
            return

        self._parar_execucao()
        cenario = self._cenario_selecionado()
        parametros = cenario.montar(self.topologia) if cenario else {"fluxos": []}

        # Um cenario de fluxos concorrentes e executado como esta definido; os
        # demais usam os campos da tela, que o usuario pode ter alterado.
        if len(parametros.get("fluxos", [])) > 1:
            fluxos = parametros["fluxos"]
        else:
            fluxo = self._montar_fluxo()
            if fluxo is None:
                return
            fluxos = [fluxo]

        quedas = [self.var_enlace_queda.get()] if self.var_derrubar.get() else []
        erro = self.var_enlace_erro.get() if self.var_injetar.get() else ""

        try:
            self.resultado = self.motor.executar(
                fluxos, enlaces_derrubados=quedas, enlace_com_erro=erro,
                observacao=parametros.get("observacao", ""),
            )
        except Exception as excecao:                      # pragma: no cover
            messagebox.showerror("Falha na simulacao",
                                 f"{type(excecao).__name__}: {excecao}",
                                 parent=self.raiz)
            return

        self.cenario_atual = cenario
        self.indice = -1
        self._preencher_registro()
        self._atualizar_eficiencia()
        self._habilitar_controles(True)
        self._mostrar_passo()

    def _montar_fluxo(self) -> Fluxo | None:
        """Le os campos da tela e valida o endereco de destino."""
        assert self.topologia is not None
        origem = self.var_origem.get()
        if origem not in self.topologia.dispositivos:
            messagebox.showwarning("Origem",
                                   "Escolha um computador de origem.",
                                   parent=self.raiz)
            return None

        ip_destino = self.var_ip.get().strip()
        from .pdu import ip_valido
        if not ip_valido(ip_destino):
            messagebox.showwarning(
                "Endereco de destino",
                f"O endereco {ip_destino!r} nao e um endereco logico valido.\n\n"
                "Use quatro numeros de 0 a 255 separados por ponto, "
                "por exemplo 10.0.3.10.",
                parent=self.raiz)
            return None

        texto = self.var_mensagem.get()
        if not texto:
            messagebox.showwarning("Mensagem", "Digite a mensagem a enviar.",
                                   parent=self.raiz)
            return None

        return Fluxo(
            origem=origem,
            destino_ip=ip_destino,
            texto=texto,
            processo_origem=self.var_proc_origem.get() or "navegador",
            processo_destino=self.var_proc_destino.get() or "servidorWeb",
        )

    def _habilitar_controles(self, ligado: bool) -> None:
        estado = "normal" if ligado else "disabled"
        for botao in (self.botao_anterior, self.botao_proximo,
                      self.botao_executar, self.botao_reiniciar, self.botao_fim):
            botao.configure(state=estado)

    # -- navegacao ---------------------------------------------------------

    def _total_passos(self) -> int:
        return len(self.resultado.registro) if self.resultado else 0

    def _passo_adiante(self) -> None:
        if self.indice + 1 >= self._total_passos():
            self._parar_execucao()
            return
        self.indice += 1
        self._mostrar_passo()

    def _passo_atras(self) -> None:
        if self.indice <= 0:
            self.indice = -1
        else:
            self.indice -= 1
        self._parar_execucao()
        self._mostrar_passo()

    def _ir_ao_fim(self) -> None:
        self._parar_execucao()
        self.indice = self._total_passos() - 1
        self._mostrar_passo()

    def _reiniciar(self) -> None:
        self._parar_execucao()
        self.indice = -1
        self._mostrar_passo()

    def _alternar_execucao(self) -> None:
        if self.executando:
            self._parar_execucao()
        else:
            if self.indice + 1 >= self._total_passos():
                self.indice = -1
            self.executando = True
            self.botao_executar.configure(text="Pausar")
            self._passo_continuo()

    def _passo_continuo(self) -> None:
        if not self.executando:
            return
        if self.indice + 1 >= self._total_passos():
            self._parar_execucao()
            return
        self._passo_adiante()
        self._tarefa = self.raiz.after(self._intervalo(), self._passo_continuo)

    def _parar_execucao(self) -> None:
        self.executando = False
        if self._tarefa is not None:
            self.raiz.after_cancel(self._tarefa)
            self._tarefa = None
        self.botao_executar.configure(text="Executar")

    def _intervalo(self) -> int:
        for rotulo, milissegundos in config.VELOCIDADES:
            if rotulo == self.var_velocidade.get():
                return milissegundos
        return config.VELOCIDADES[config.VELOCIDADE_PADRAO][1]

    # -----------------------------------------------------------------
    # Atualizacao da tela
    # -----------------------------------------------------------------

    def _evento_atual(self) -> Evento | None:
        if self.resultado is None or self.indice < 0:
            return None
        if self.indice >= len(self.resultado.registro):
            return None
        return self.resultado.registro[self.indice]

    def _mostrar_passo(self) -> None:
        evento = self._evento_atual()
        self.rotulo_passo.configure(
            text=f"passo {self.indice + 1} de {self._total_passos()}")
        self._redesenhar_mapa()
        self._redesenhar_pilhas()
        self._redesenhar_unidade()
        self._atualizar_enderecos(evento)
        self._destacar_registro()

    def _limpar_tela(self) -> None:
        self.resultado = None
        self.indice = -1
        self.rotulo_unidade.configure(text="-")
        self.rotulo_logicos.configure(text="-")
        self.rotulo_fisicos.configure(text="-")
        self.rotulo_passo.configure(text="passo 0 de 0")
        self.registro.configure(state="normal")
        self.registro.delete("1.0", "end")
        self.registro.configure(state="disabled")
        self._habilitar_controles(False)
        self._redesenhar_mapa()
        self._redesenhar_pilhas()
        self._redesenhar_unidade()

    def _atualizar_mapa_estatico(self) -> None:
        self._redesenhar_mapa()

    # -- V1: mapa ----------------------------------------------------------

    def _redesenhar_mapa(self) -> None:
        tela = self.mapa
        tela.delete("all")
        if self.topologia is None:
            tela.create_text(20, 20, anchor="nw", text=self._erro_topologia,
                             fill=ERRO, font=FONTE, width=400)
            return

        largura = max(tela.winfo_width(), 320)
        altura = max(tela.winfo_height(), 220)
        margem_x, margem_y = 52, 34

        def ponto(dispositivo) -> tuple[float, float]:
            x, y = dispositivo.posicao
            return (margem_x + x * (largura - 2 * margem_x),
                    margem_y + y * (altura - 2 * margem_y))

        evento = self._evento_atual()
        percorridos = evento.caminho if evento else []
        enlace_ativo = evento.enlace if evento else None
        derrubados = set()
        if self.var_derrubar.get() and self.var_enlace_queda.get():
            derrubados.add(self.var_enlace_queda.get())
        if self.resultado:
            derrubados.update(self.resultado.enlaces_derrubados)

        # --- enlaces
        for segmento in self.topologia.segmentos:
            membros = [(nome, self.topologia.dispositivos[nome], iface)
                       for nome, iface in segmento.membros]
            caido = segmento.id in derrubados
            no_caminho = self._segmento_no_caminho(segmento, percorridos)
            em_uso = bool(enlace_ativo) and self._segmento_liga(segmento, enlace_ativo)

            if caido:
                cor, espessura, tracejado = ERRO, 2, (6, 4)
            elif em_uso:
                cor, espessura, tracejado = "#d97706", 5, ()
            elif no_caminho:
                cor, espessura, tracejado = DESTAQUE, 3.5, ()
            else:
                cor, espessura, tracejado = "#93a1b3", 1.6, ()

            if segmento.tipo == "lan":
                if segmento.posicao is not None:
                    centro = (margem_x + segmento.posicao[0] * (largura - 2 * margem_x),
                              margem_y + segmento.posicao[1] * (altura - 2 * margem_y))
                else:
                    centro = self._centro(membros, ponto)
                for _nome, dispositivo, iface in membros:
                    x, y = ponto(dispositivo)
                    tela.create_line(x, y, centro[0], centro[1], fill=cor,
                                     width=espessura, dash=tracejado or None)
                    self._rotulo_interface(tela, (x, y), centro, iface)
                tela.create_oval(centro[0] - 4, centro[1] - 4,
                                 centro[0] + 4, centro[1] + 4,
                                 fill=cor, outline=cor)
                self._rotulo_rede(tela, centro, segmento.rotulo, segmento.prefixo)
            else:
                (_n1, d1, i1), (_n2, d2, i2) = membros[0], membros[1]
                p1, p2 = ponto(d1), ponto(d2)
                tela.create_line(*p1, *p2, fill=cor, width=espessura,
                                 dash=tracejado or None)
                meio = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
                texto = f"custo {segmento.custo}"
                if caido:
                    texto += "  (derrubado)"
                tela.create_text(meio[0], meio[1] - 10, text=texto,
                                 fill=ERRO if caido else SUAVE,
                                 font=("Segoe UI", 8, "bold" if caido else "normal"))
                self._rotulo_interface(tela, p1, p2, i1)
                self._rotulo_interface(tela, p2, p1, i2)

        # --- dispositivos
        for dispositivo in self.topologia.dispositivos.values():
            x, y = ponto(dispositivo)
            ativo = bool(evento) and evento.dispositivo == dispositivo.nome
            visitado = dispositivo.nome in percorridos
            roteador = dispositivo.tipo == "roteador"

            if ativo:
                preenchimento, contorno, espessura = "#ffe9a8", "#b45309", 3
            elif visitado:
                preenchimento, contorno, espessura = "#dbeafe", DESTAQUE, 2
            else:
                preenchimento, contorno, espessura = PAPEL, "#93a1b3", 1.4

            if roteador:
                raio = 22
                tela.create_oval(x - raio, y - raio, x + raio, y + raio,
                                 fill=preenchimento, outline=contorno,
                                 width=espessura)
            else:
                meia = 22
                tela.create_rectangle(x - meia, y - 16, x + meia, y + 16,
                                      fill=preenchimento, outline=contorno,
                                      width=espessura)
            tela.create_text(x, y, text=dispositivo.rotulo,
                             font=("Segoe UI", 10, "bold"), fill=TINTA)
            tela.create_text(x, y + 28, text=dispositivo.ip_principal,
                             font=("Consolas", 7), fill=SUAVE)

        # --- legenda
        if evento is not None and evento.unidade is not None and evento.unidade.quadro:
            tela.create_text(10, altura - 10, anchor="sw",
                             text=f"quadro corrente: {evento.unidade.quadro}",
                             font=FONTE_MONO, fill="#b45309")

    @staticmethod
    def _centro(membros, ponto) -> tuple[float, float]:
        pontos = [ponto(dispositivo) for _n, dispositivo, _i in membros]
        return (sum(p[0] for p in pontos) / len(pontos),
                sum(p[1] for p in pontos) / len(pontos))

    @staticmethod
    def _rotulo_rede(tela: tk.Canvas, centro, rotulo: str, prefixo: str) -> None:
        """Escreve o nome e o prefixo da rede local sobre um fundo opaco.

        O fundo evita que o texto se confunda com os enlaces que passam atras.
        """
        x, y = centro[0], centro[1] - 24
        largura = max(len(rotulo), len(prefixo)) * 5.2 + 10
        tela.create_rectangle(x - largura / 2, y - 12, x + largura / 2, y + 12,
                              fill=TELA, outline=BORDA, width=1)
        tela.create_text(x, y - 5, text=rotulo, fill=SUCESSO,
                         font=("Segoe UI", 8, "bold"))
        tela.create_text(x, y + 6, text=prefixo, fill=SUAVE,
                         font=("Consolas", 7))

    @staticmethod
    def _rotulo_interface(tela: tk.Canvas, origem, destino, nome: str) -> None:
        """Escreve o nome da interface junto ao dispositivo, sobre o enlace."""
        dx, dy = destino[0] - origem[0], destino[1] - origem[1]
        comprimento = max((dx * dx + dy * dy) ** 0.5, 1)
        fator = 34 / comprimento
        tela.create_text(origem[0] + dx * fator, origem[1] + dy * fator,
                         text=nome, font=("Consolas", 7), fill="#475569")

    def _segmento_no_caminho(self, segmento, caminho: list[str]) -> bool:
        presentes = [nome for nome, _ in segmento.membros if nome in caminho]
        if len(presentes) < 2:
            return False
        for anterior, seguinte in zip(caminho, caminho[1:]):
            if anterior in presentes and seguinte in presentes:
                return True
        return False

    @staticmethod
    def _segmento_liga(segmento, par: tuple[str, str]) -> bool:
        return segmento.contem(par[0]) and segmento.contem(par[1])

    # -- V2 e V7: pilhas ---------------------------------------------------

    def _trocar_modo_pilha(self) -> None:
        self._redesenhar_pilhas()

    def _redesenhar_pilhas(self) -> None:
        tela = self.pilhas
        tela.delete("all")
        if self.topologia is None:
            return

        evento = self._evento_atual()
        envolvidos = self._dispositivos_em_cena()
        if not envolvidos:
            tela.create_text(14, 14, anchor="nw",
                             text="Escolha um cenario e pressione Simular.",
                             fill=SUAVE, font=FONTE)
            return

        tcpip = self.var_pilha.get() == "TCPIP"
        largura_caixa, altura_linha, espaco = 102, 26, 6
        topo = 44

        for coluna, nome in enumerate(envolvidos):
            dispositivo = self.topologia.dispositivos[nome]
            x = 12 + coluna * (largura_caixa + espaco)
            centro = x + largura_caixa / 2
            ativo_aqui = evento is not None and evento.dispositivo == nome

            tela.create_text(centro, 13, text=nome, font=("Segoe UI", 10, "bold"),
                             fill=DESTAQUE if ativo_aqui else TINTA)
            tipo = "7 camadas" if dispositivo.tipo == "computador" else "3 camadas"
            tela.create_text(centro, 25, text=tipo, font=("Segoe UI", 7), fill=SUAVE)
            # A acao corrente fica sobre a coluna do proprio dispositivo, para
            # nao invadir a coluna vizinha.
            if ativo_aqui and evento is not None:
                tela.create_text(
                    centro, 37, text=evento.acao, font=("Segoe UI", 8, "bold"),
                    fill=ERRO if evento.estado == "erro" else "#b45309")

            linhas = self._linhas_da_pilha(dispositivo.numero_camadas, tcpip)
            for posicao, (rotulo, camadas) in enumerate(linhas):
                y = topo + posicao * altura_linha
                ativa = (ativo_aqui and evento is not None
                         and evento.numero_camada in camadas)
                cor = CORES_CAMADA.get(max(camadas), "#e5e7eb")
                if ativa:
                    contorno, espessura = "#b45309", 3
                    if evento is not None and evento.estado == "erro":
                        contorno = ERRO
                    cor = "#ffe9a8" if evento.estado != "erro" else "#fadbd8"
                else:
                    contorno, espessura = BORDA, 1

                tela.create_rectangle(x, y, x + largura_caixa, y + altura_linha - 4,
                                      fill=cor, outline=contorno, width=espessura)
                numeracao = (str(max(camadas)) if len(camadas) == 1
                             else f"{min(camadas)}-{max(camadas)}")
                meio = y + (altura_linha - 4) / 2
                tela.create_text(x + 6, meio, anchor="w", text=numeracao,
                                 font=("Consolas", 8, "bold"), fill=SUAVE)
                tela.create_text(x + largura_caixa - 6, meio, anchor="e",
                                 text=rotulo,
                                 font=("Segoe UI", 8, "bold" if ativa else "normal"),
                                 fill=TINTA)

        largura_total = 12 + len(envolvidos) * (largura_caixa + espaco) + 12
        altura_total = topo + 7 * altura_linha + 16
        tela.configure(scrollregion=(0, 0, largura_total, altura_total))

    @staticmethod
    def _linhas_da_pilha(numero_camadas: int,
                         tcpip: bool) -> list[tuple[str, tuple[int, ...]]]:
        """Devolve as linhas a desenhar, de cima para baixo.

        Um roteador tem apenas as camadas 1 a 3, e o agrupamento TCP/IP nao o
        altera: agrupar as camadas 5 a 7 nao muda nada em quem nao as possui.
        """
        if tcpip:
            grupos = [(rotulo, camadas) for rotulo, camadas in GRUPOS_TCPIP
                      if min(camadas) <= numero_camadas]
            return [(rotulo, tuple(c for c in camadas if c <= numero_camadas))
                    for rotulo, camadas in grupos]
        return [(NOMES_CAMADA[n], (n,))
                for n in range(numero_camadas, 0, -1)]

    def _dispositivos_em_cena(self) -> list[str]:
        """Dispositivos cuja pilha deve aparecer: os do percurso da mensagem."""
        if self.resultado is None or self.topologia is None:
            return []
        vistos: list[str] = []
        for fluxo in self.resultado.fluxos:
            for nome in fluxo.caminho:
                if nome not in vistos:
                    vistos.append(nome)
        if not vistos:
            for evento in self.resultado.registro:
                if evento.dispositivo not in vistos:
                    vistos.append(evento.dispositivo)
        return vistos

    # -- V3: unidade de dados ----------------------------------------------

    def _redesenhar_unidade(self) -> None:
        tela = self.desenho
        tela.delete("all")
        evento = self._evento_atual()

        if evento is None or evento.unidade is None:
            self.rotulo_unidade.configure(text="-")
            tela.create_text(12, 12, anchor="nw", font=FONTE, fill=SUAVE,
                             text="A unidade de dados aparece aqui a cada passo.")
            return

        unidade = evento.unidade
        rotulos = [unidade.unidade]
        if unidade.quadro:
            rotulos.append(f"quadro {unidade.quadro}")
        if unidade.pacote:
            rotulos.append(f"pacote {unidade.pacote}")
        if unidade.total_segmentos > 1:
            rotulos.append(f"segmento {unidade.numero_segmento}"
                           f" de {unidade.total_segmentos}")
        rotulos.append(f"{evento.tamanho} octetos")
        self.rotulo_unidade.configure(text="   |   ".join(rotulos))

        blocos = unidade.blocos()
        largura = max(tela.winfo_width(), 400) - 24
        total = max(sum(b["tamanho"] for b in blocos), 1)
        minimo = 46
        # Reparte a largura em proporcao ao tamanho, garantindo um minimo
        # legivel para os cabecalhos pequenos.
        fixos = sum(minimo for b in blocos if b["tamanho"] * largura / total < minimo)
        restante = max(largura - fixos, 60)
        resto_total = sum(b["tamanho"] for b in blocos
                          if b["tamanho"] * largura / total >= minimo) or 1

        x = 12
        altura = 44
        y = 22
        for bloco in blocos:
            proporcional = bloco["tamanho"] * largura / total
            passo = minimo if proporcional < minimo else max(
                minimo, bloco["tamanho"] * restante / resto_total)
            cor = CORES_CAMADA.get(bloco["camada"], "#e5e7eb")
            if bloco["tipo"] == "dados":
                cor = "#d7f0df"
            elif bloco["tipo"] == "finalizador":
                cor = "#f7e3c8"
            tela.create_rectangle(x, y, x + passo, y + altura, fill=cor,
                                  outline="#64748b", width=1.2)
            tela.create_text(x + passo / 2, y + 14, text=bloco["rotulo"],
                             font=("Segoe UI", 9, "bold"), fill=TINTA)
            tela.create_text(x + passo / 2, y + 31,
                             text=f"{bloco['tamanho']} B",
                             font=("Consolas", 8), fill=SUAVE)
            x += passo + 2

        tela.create_text(12, 10, anchor="nw",
                         text="cabecalhos a esquerda dos dados; "
                              "finalizador da camada 2 a direita",
                         font=("Segoe UI", 8), fill=SUAVE)
        if evento.estado == "erro":
            tela.create_text(12, y + altura + 6, anchor="nw", text=evento.descricao,
                             font=("Segoe UI", 8, "bold"), fill=ERRO)

    # -- V4: enderecos -----------------------------------------------------

    def _atualizar_enderecos(self, evento: Evento | None) -> None:
        if evento is None or evento.unidade is None:
            self.rotulo_logicos.configure(text="-")
            self.rotulo_fisicos.configure(text="-")
            return

        unidade = evento.unidade
        if unidade.logicos:
            self.rotulo_logicos.configure(
                text=f"{unidade.logicos[0]}  →  {unidade.logicos[1]}")
        else:
            self.rotulo_logicos.configure(text="ainda nao inseridos (camada 3)")

        if unidade.fisicos:
            self.rotulo_fisicos.configure(
                text=f"{unidade.fisicos[0]}\n→  {unidade.fisicos[1]}")
            enlace = unidade.metadados.get("rotulo_enlace", "")
            self.rotulo_fisicos_nota.configure(
                text=f"validos apenas no enlace {enlace}" if enlace
                else "substituido a cada enlace")
        else:
            self.rotulo_fisicos.configure(text="fora de um enlace no momento")
            self.rotulo_fisicos_nota.configure(text="substituido a cada enlace")

    # -- V6: registro ------------------------------------------------------

    def _preencher_registro(self) -> None:
        self.registro.configure(state="normal")
        self.registro.delete("1.0", "end")
        if self.resultado is not None:
            for evento in self.resultado.registro:
                self.registro.insert("end", evento.linha + "\n")
        self.registro.configure(state="disabled")

    def _destacar_registro(self) -> None:
        self.registro.configure(state="normal")
        for marca in ("atual", "erro", "sucesso", "futuro"):
            self.registro.tag_remove(marca, "1.0", "end")
        if self.resultado is not None:
            for posicao, evento in enumerate(self.resultado.registro, start=1):
                intervalo = (f"{posicao}.0", f"{posicao}.end")
                if posicao - 1 > self.indice:
                    self.registro.tag_add("futuro", *intervalo)
                elif evento.estado == "erro":
                    self.registro.tag_add("erro", *intervalo)
                elif evento.estado == "sucesso":
                    self.registro.tag_add("sucesso", *intervalo)
        if self.indice >= 0:
            linha = self.indice + 1
            self.registro.tag_add("atual", f"{linha}.0", f"{linha}.end")
            self.registro.see(f"{linha}.0")
        self.registro.configure(state="disabled")

    def _salvar_registro(self) -> None:
        if self.resultado is None:
            messagebox.showinfo("Registro", "Execute uma simulacao primeiro.",
                                parent=self.raiz)
            return
        caminho = filedialog.asksaveasfilename(
            parent=self.raiz, title="Salvar registro de eventos",
            defaultextension=".txt", initialfile=config.ARQUIVO_REGISTRO_PADRAO,
            initialdir=config.diretorio_base(),
            filetypes=[("Texto", "*.txt"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            self.resultado.registro.salvar(caminho, cabecalho=self._cabecalho_registro())
        except OSError as erro:
            messagebox.showerror("Registro", f"Nao foi possivel salvar:\n{erro}",
                                 parent=self.raiz)
            return
        messagebox.showinfo("Registro", f"Registro salvo em:\n{caminho}",
                            parent=self.raiz)

    def _cabecalho_registro(self) -> list[str]:
        assert self.resultado is not None
        nome = self.cenario_atual.rotulo if self.cenario_atual else "personalizado"
        return [
            f"{config.NOME_PROGRAMA} {config.VERSAO} - {config.AUTORIA}",
            f"Cenario: {nome}",
            f"Rede: {self.topologia.nome if self.topologia else '-'}",
            *self.resultado.resumo_texto(),
        ]

    # -- acoes do rodape ---------------------------------------------------

    def _atualizar_eficiencia(self) -> None:
        if self.resultado is None or self.topologia is None:
            return
        comparativo = cenarios.comparativo_eficiencia(self.topologia)
        linhas = [
            "  ".join([
                f"dados {self.resultado.octetos_dados} B",
                f"transmitido {self.resultado.octetos_transmitidos} B",
                f"quadros {self.resultado.total_quadros}",
                f"eficiencia {self.resultado.eficiencia:.1%}",
                f"sobrecarga {self.resultado.sobrecarga:.1%}",
            ]),
            f"referencia:  E1 um enlace {comparativo['E1_eficiencia']:.1%}"
            f"   |   E2 quatro enlaces {comparativo['E2_eficiencia']:.1%}",
        ]
        if not self.resultado.entregue:
            motivos = "; ".join(f.motivo for f in self.resultado.fluxos if f.motivo)
            linhas.append(f"mensagem nao entregue - {motivos}")
        self.rotulo_eficiencia.configure(
            text="\n".join(linhas),
            foreground=TINTA if self.resultado.entregue else ERRO)

    def _exportar_html(self) -> None:
        if self.resultado is None or self.topologia is None:
            messagebox.showinfo("Relatorio", "Execute uma simulacao primeiro.",
                                parent=self.raiz)
            return
        caminho = filedialog.asksaveasfilename(
            parent=self.raiz, title="Exportar relatorio",
            defaultextension=".html", initialfile=config.ARQUIVO_RELATORIO_PADRAO,
            initialdir=config.diretorio_base(),
            filetypes=[("Pagina HTML", "*.html"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            relatorio.salvar(caminho, self.resultado, self.cenario_atual,
                             self.topologia)
        except OSError as erro:
            messagebox.showerror("Relatorio", f"Nao foi possivel salvar:\n{erro}",
                                 parent=self.raiz)
            return
        if messagebox.askyesno("Relatorio",
                               f"Relatorio salvo em:\n{caminho}\n\nAbrir agora?",
                               parent=self.raiz):
            try:
                os.startfile(caminho)                       # noqa: S606
            except OSError:
                pass

    def _abrir_tabelas(self) -> None:
        if self.topologia is None:
            return
        janela = tk.Toplevel(self.raiz)
        janela.title("Tabelas de encaminhamento")
        janela.geometry("620x520")
        janela.configure(background=FUNDO)
        janela.transient(self.raiz)

        aviso = ("Tabelas calculadas sobre os enlaces ativos no momento. "
                 "Custo 0 indica rede diretamente conectada.")
        ttk.Label(janela, text=aviso, style="Suave.TLabel",
                  wraplength=580).pack(anchor="w", padx=10, pady=(10, 4))

        caderno = ttk.Notebook(janela)
        caderno.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for nome in sorted(self.topologia.dispositivos):
            dispositivo = self.topologia.dispositivos[nome]
            quadro = ttk.Frame(caderno, padding=6)
            caderno.add(quadro, text=nome)
            colunas = ("destino", "proximo", "interface", "custo", "via")
            arvore = ttk.Treeview(quadro, columns=colunas, show="headings",
                                  height=12)
            for coluna, titulo, largura in zip(
                    colunas,
                    ("Rede de destino", "Proximo salto", "Interface", "Custo", "Via"),
                    (150, 130, 80, 60, 90)):
                arvore.heading(coluna, text=titulo)
                arvore.column(coluna, width=largura, anchor="w")
            for entrada in self.topologia.tabela_encaminhamento(nome):
                arvore.insert("", "end", values=entrada.como_linha())
            arvore.pack(fill="both", expand=True)
            ttk.Label(quadro, style="Suave.TLabel",
                      text=("Computador: encaminha pela rota padrao."
                            if dispositivo.tipo == "computador"
                            else "Roteador: rotas por menor custo (Dijkstra).")
                      ).pack(anchor="w", pady=(6, 0))

    def _abrir_convencoes(self) -> None:
        janela = tk.Toplevel(self.raiz)
        janela.title("Convencoes de simulacao")
        janela.geometry("520x400")
        janela.configure(background=FUNDO)
        janela.transient(self.raiz)

        ttk.Label(janela, wraplength=480, style="Suave.TLabel",
                  text=("Estes sao os numeros que determinam o resultado de uma "
                        "execucao. Todos estao reunidos em simulador/config.py.")
                  ).pack(anchor="w", padx=12, pady=(12, 6))

        arvore = ttk.Treeview(janela, columns=("parametro", "valor"),
                              show="headings", height=14)
        arvore.heading("parametro", text="Parametro")
        arvore.heading("valor", text="Valor")
        arvore.column("parametro", width=280, anchor="w")
        arvore.column("valor", width=200, anchor="w")
        for parametro, valor in config.resumo_convencoes():
            arvore.insert("", "end", values=(parametro, valor))
        arvore.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _trocar_topologia(self) -> None:
        """Carrega outro arquivo de topologia, sem reiniciar o programa."""
        caminho = filedialog.askopenfilename(
            parent=self.raiz, title="Escolher arquivo de topologia",
            initialdir=config.diretorio_base(),
            filetypes=[("Topologia JSON", "*.json"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            nova = Topologia(caminho)
        except ErroTopologia as erro:
            messagebox.showerror("Topologia", str(erro), parent=self.raiz)
            return

        self._parar_execucao()
        self.topologia = nova
        self.motor = Motor(nova)
        self._erro_topologia = ""
        self._atualizar_titulo()
        self._popular_campos()
        self._limpar_tela()
        messagebox.showinfo(
            "Topologia",
            f"Rede carregada: {nova.nome}\n"
            f"{len(nova.computadores())} computadores, "
            f"{len(nova.roteadores())} roteadores, "
            f"{len(nova.segmentos)} segmentos.",
            parent=self.raiz)

    # -----------------------------------------------------------------
    # Laco principal
    # -----------------------------------------------------------------

    def executar(self) -> None:
        self.raiz.mainloop()
