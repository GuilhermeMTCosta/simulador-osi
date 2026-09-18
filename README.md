# Simulador do Modelo OSI

Projeto 1 da disciplina de **Comunicação de Dados**, ministrada pelo
**Prof. Vinícius S. Borges**. Semestre 2026/2.

## Autoria

Grupo 8

- Arthur Benevides - 082230016
- Fernando Montanher - 082230010
- Guilherme Costa - 081240041
- Juan Haddad - 081240043
- Murillo Ando - 082240042

## Como executar

**Dê dois cliques em `SimuladorOSI.exe`.**

Não é preciso instalar nada: nem Python, nem bibliotecas, nem preparação de
ambiente. O programa abre uma janela única e já vem com o cenário E2 carregado.
Basta pressionar **Simular** e depois **Executar**.

Para rodar a partir do código-fonte, com Python 3.10 ou superior:

```
python main.py            abre a interface gráfica
python main.py --texto    executa os sete cenários no terminal
```

O arquivo `executar_codigo_fonte.bat` faz o mesmo com dois cliques e avisa
caso o Python não esteja instalado.

## Descrição

O simulador reproduz o percurso completo de uma mensagem entre dois
computadores de uma rede com três redes locais, quatro roteadores e cinco
computadores. Ele exibe, passo a passo, o encapsulamento na origem, a decisão
de rota em cada roteador, a substituição do par de endereços físicos a cada
enlace e o desencapsulamento no destino.

Cada uma das sete camadas do modelo OSI é uma classe separada com duas
operações de sentido oposto, e nenhuma camada alcança outra que não lhe seja
adjacente. Os roteadores implementam apenas as três primeiras camadas, de modo
que não têm como ler uma porta ou o nome de um processo. A interface gráfica
não conhece as camadas: ela apenas percorre a lista de eventos produzida pelo
núcleo da simulação.

## Estrutura do repositório

```
simulador-osi/
├── SimuladorOSI.exe              Programa pronto para executar
├── topologia.json                Rede simulada, substituível sem recompilar
├── main.py                       Ponto de entrada do código-fonte
├── executar_codigo_fonte.bat     Atalho para rodar o código-fonte
├── requirements.txt              Registro de dependências (não há nenhuma)
├── simulador/                    Código-fonte do simulador
├── tests/                        Testes automatizados dos sete cenários
├── registros/                    Registro de eventos dos sete casos, E1 a E7
└── docs/
    ├── documentacao_projeto.pdf  Como o simulador funciona por dentro
    ├── tutorial_execucao.pdf     Como abrir o programa
    ├── tutorial_uso.pdf          Como operar cada função
    ├── especificacao.pdf         Enunciado da disciplina
    └── guia_de_documentacao.pdf  Guia de documentação da disciplina
```

## Arquivos de código

| Arquivo | O que faz |
|---|---|
| `simulador/config.py` | Convenções de simulação: tamanhos de cabeçalho, limiares e velocidades |
| `simulador/pdu.py` | Unidade de dados de protocolo e construtores de cabeçalho |
| `simulador/camadas.py` | As sete classes de camada, cada uma com `desce` e `sobe` |
| `simulador/dispositivos.py` | Computador (sete camadas) e roteador (três camadas) |
| `simulador/rede.py` | Topologia, enlaces e tabelas de encaminhamento por menor custo |
| `simulador/eventos.py` | Evento e registro de eventos, a fronteira entre núcleo e interface |
| `simulador/motor.py` | Relógio e laço de simulação salto a salto |
| `simulador/cenarios.py` | Os sete casos obrigatórios de validação, E1 a E7 |
| `simulador/visual.py` | Interface gráfica em tkinter |
| `simulador/relatorio.py` | Exportação do resultado em HTML |
| `main.py` | Ponto de entrada; abre a janela ou roda em modo texto |
| `topologia.json` | Dispositivos, interfaces, endereços, enlaces e custos |

## Requisitos de ambiente

- **Executável:** Windows. Nenhum requisito adicional.
- **Código-fonte:** Python 3.10 ou superior, com `tkinter` (já incluído na
  instalação padrão do Python para Windows).
- **Bibliotecas externas:** nenhuma. O simulador usa apenas a biblioteca
  padrão (`tkinter`, `json`, `zlib`, `struct`, `heapq`, `dataclasses`,
  `typing`, `html`, `datetime`).

## Funcionalidades

| O que faz | Onde está implementado |
|---|---|
| Encapsulamento e desencapsulamento nas sete camadas | `simulador/camadas.py` |
| Segmentação na camada 4 e remontagem em ordem no destino | `simulador/camadas.py` (`CamadaTransporte`) |
| Cifra da camada 6, desfeita só na camada 6 do destino | `simulador/camadas.py` (`CamadaApresentacao`) |
| Verificação de erro do quadro por CRC-32 | `simulador/pdu.py`, `simulador/camadas.py` (`CamadaEnlace`) |
| Encaminhamento por menor custo (Dijkstra) e tabelas | `simulador/rede.py` |
| Entrega direta sem roteador na mesma rede | `simulador/camadas.py` (`CamadaRede._decidir`) |
| Reconstrução do quadro a cada salto | `simulador/dispositivos.py` (`Roteador.encaminhar`) |
| Queda de enlace, erro de bit e destino inalcançável | `simulador/motor.py`, acionados pela interface |
| Demultiplexação de fluxos concorrentes pelas portas | `simulador/camadas.py` (`CamadaTransporte.sobe`) |
| Registro de eventos e gravação em arquivo | `simulador/eventos.py` |
| Cálculo da eficiência e da sobrecarga | `simulador/motor.py` (`ResultadoSimulacao`) |
| Mapa, pilhas, unidade de dados e pares de endereços | `simulador/visual.py` |
| Alternância entre a pilha OSI e a pilha TCP/IP | `simulador/visual.py` (`_linhas_da_pilha`) |
| Troca da rede simulada sem recompilar | `simulador/rede.py`, `simulador/config.py` |
| Exportação do resultado em HTML | `simulador/relatorio.py` |

## Cenários de validação

Os sete casos do enunciado estão na lista **Cenário** da tela. Os valores
abaixo são reproduzidos a cada execução e servem para conferir que o programa
funciona na máquina de quem avalia.

| Cenário | Caminho | Quadros | Dados | Transmitido | Eficiência |
|---|---|---|---|---|---|
| E1 Entrega direta | H1 - H2 | 1 | 42 B | 92 B | 45,7 % |
| E2 Entrega indireta | H1 - R1 - R4 - R3 - H4 | 4 | 42 B | 368 B | 11,4 % |
| E3 Demultiplexação | dois fluxos até H4 | 8 | 84 B | 736 B | 11,4 % |
| E4 Falha de enlace | H1 - R1 - R2 - R3 - H4 | 4 | 42 B | 368 B | 11,4 % |
| E5 Destino inalcançável | H1 - R1 (descarte) | 1 | 0 B | 92 B | 0 % |
| E6 Erro de transmissão | H1 - R1 - R4 - R3 (descarte) | 3 | 0 B | 276 B | 0 % |
| E7 Mensagem longa | H1 - R1 - R4 - R3 - H4 | 12 | 100 B | 968 B | 10,3 % |

## Testes automatizados

```
python -m unittest discover -s tests -v
```

São 41 testes que conferem os endereços da topologia, os custos de rota, os
tamanhos de cada cabeçalho, os valores da tabela acima e as cinco restrições
de projeto do enunciado.

## Registros de eventos

A pasta [`registros/`](./registros) traz o registro completo dos sete casos,
de `E1.txt` a `E7.txt`, no formato da Seção 5.1 do enunciado. Cada arquivo
começa com um cabeçalho que informa o cenário, o caminho percorrido e o quadro
numérico da comunicação, seguido de uma linha por ação de cada camada.

Os mesmos registros são reproduzidos pelo programa a qualquer momento, pelo
botão **Salvar registro**, ou pelo terminal com `python main.py --texto`.

## Documentação

- [Tutorial de execução](./docs/tutorial_execucao.pdf) - como abrir o programa
- [Tutorial de uso](./docs/tutorial_uso.pdf) - como operar cada função
- [Documentação técnica](./docs/documentacao_projeto.pdf) - como funciona por dentro

Os três documentos trazem capturas de tela e os valores de referência de cada
cenário, para conferência na máquina de quem avalia.

## Por onde começar

1. Abra o programa e siga o **tutorial de execução**.
2. Reproduza o cenário E2 pelo **tutorial de uso** e confira a eficiência de 11,4 %.
3. Leia a **documentação técnica** para entender a separação entre as camadas e
   as convenções que determinam os números.
