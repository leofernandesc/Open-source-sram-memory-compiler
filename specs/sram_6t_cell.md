# Célula SRAM 6T — especificação inicial

## Escopo

Capturar no Xschem uma célula SRAM single-port 6T para SKY130A, formada por:

- dois inversores CMOS cruzados;
- dois transistores NMOS de acesso controlados por `WL`;
- alimentação nominal `VDD = 1.8 V`;
- sinais externos `BL`, `BLB`, `WL`, `VDD` e `VSS`;
- nós internos `Q` e `QB`.

## 1. Topologia definida

### 1.1 Bitcell 6T single-port

A célula de armazenamento é uma SRAM 6T de uma porta, composta por:

- dois inversores CMOS cruzados, `MNL/MPL` e `MNR/MPR`, formando o biestável;
- dois NMOS de acesso, `MAL` e `MAR`, conectados respectivamente a `BL` e
  `BLB`, ambos comandados por `WL`;
- bulk dos PMOS em `VDD` e bulk dos NMOS em `VSS`;
- nós internos complementares `Q` e `QB`.

O comportamento arquitetural é `1RW`: uma operação por vez na porta única. A
leitura usa as duas bitlines pré-carregadas e a escrita força níveis
complementares em `BL/BLB`. A política de colisão leitura/escrita ainda será
definida no modelo funcional da macro.

### 1.2 Amplificador de leitura

O bloco de leitura será um sense amplifier diferencial do tipo *voltage-latch*:

- entradas diferenciais: `BL` e `BLB`;
- habilitação de avaliação: `SCLK`;
- alimentação: `VDD` e `VSS`;
- saídas diferenciais: `SA_OUT` e `SA_OUTB`;
- par de habilitação e transistores de isolamento entre as bitlines e o latch.

O sense amplifier pertence à periferia da coluna e não à geometria da
bitcell. A bitcell deve, portanto, expor `BL/BLB` com carga e direção
compatíveis com esse latch. A decisão de pré-carga/equalização e a temporização
relativa entre `WL` e `SCLK` serão congeladas na etapa de arquitetura da coluna.

### 1.3 Regras de sizing da topologia

Como requisitos iniciais de estabilidade e writability:

\[
\beta = \frac{(W/L)_{pull-down}}{(W/L)_{acesso}} \geq 1.2\text{--}1.5
\]

\[
\gamma = \frac{(W/L)_{pull-up}}{(W/L)_{acesso}} < 1.0
\]

Essas razões são metas de projeto, não prova de funcionamento. Devem ser
confirmadas por SNM de retenção/leitura, read disturb, write margin e leakage
nos corners do SKY130A.

## Inventário de dispositivos

| Instância | Tipo | D | G | S | B | Função |
|---|---|---|---|---|---|---|
| M1 | `pfet_01v8` | Q | QB | VDD | VDD | pull-up de Q |
| M2 | `nfet_01v8` | Q | QB | VSS | VSS | pull-down de Q |
| M3 | `pfet_01v8` | QB | Q | VDD | VDD | pull-up de QB |
| M4 | `nfet_01v8` | QB | Q | VSS | VSS | pull-down de QB |
| M5 | `nfet_01v8` | Q | WL | BL | VSS | acesso de BL |
| M6 | `nfet_01v8` | QB | WL | BLB | VSS | acesso de BLB |

O sizing candidato é `L=0.15 um`, `nf=1`, com as larguras originais escaladas
por dois para selecionar bins válidos do SKY130A sem alterar as razões:

| Dispositivos | Função | W (um) | Razão |
|---|---|---:|---:|
| M1, M3 | pull-up PMOS | 0.42 | gamma = 0.70 em relação ao acesso |
| M2, M4 | pull-down NMOS | 0.84 | beta = 1.40 em relação ao acesso |
| M5, M6 | acesso NMOS | 0.60 | referência |

O candidato passou pela primeira caracterização de Hold/Read SNM nos corners
`tt/ff/ss/fs/sf`; a WLVM nominal foi medida em testbench ideal. Ainda faltam
critérios e escrita com driver real, além de leakage e Monte Carlo, antes do
congelamento. Os valores permanecem parametrizados na captura.

A leitura transitória com bitlines capacitivas reprovou o limite provisório
de excursão máxima do nó baixo em 28/40 casos para `WPD=0.84 µm`. A exploração
de `WPD=1.05 µm` e `1.26 µm` passou esse gate em 40/40 casos, mantendo os demais
tamanhos. Essas variantes seguem experimentais até a medição de write margin;
nenhuma foi aplicada ao esquemático.

O teste de escrita com bitlines ideais full-swing, `WL=1.8 V` por 10 ns e
verificação após `WL` descer passou em 30/30 combinações de corner, sentido
de escrita e sizing (`WPD=0.84/1.05/1.26 µm`). Esse resultado é funcional:
não caracteriza write margin, resistência do driver ou tempo mínimo.

A margem dinâmica por WLVM também foi medida por busca binária para
`WPD=0.84/1.05 µm`, pulso de 10 ns, cinco corners e ambos os sentidos. O pior
caso foi `0.619/0.605 V`, respectivamente. Como a especificação ainda não
define um WLVM mínimo e os drivers são ideais, isso permanece comparação
exploratória, não critério de aprovação.

## Critérios da primeira captura

1. Os seis dispositivos devem usar símbolos `sky130_fd_pr` e bulk explícito.
2. `Q` e `QB` devem estar cruzados nos gates dos inversores.
3. `BL` e `BLB` devem conectar somente aos drains/sources dos transistores de acesso.
4. A célula deve ser simétrica visualmente e sem pinos de alimentação implícitos.
5. A simulação inicial deve verificar retenção, leitura e escrita em `tt`, a 1.8 V.

## Critérios elétricos provisórios

Até que a caracterização seja executada, os seguintes valores são metas de
aceite, não resultados medidos:

- retenção: `Q/QB` permanecem nos estados complementares com `WL=0 V`;
- leitura: diferença de bitline de pelo menos `100 mV` durante a janela de
  leitura, sem aumento do nó armazenando `0` superior a `0.2 V`;
- Read SNM no ponto nominal (`tt`, `VDD=1.8 V`, temperatura nominal):
  `>= 0.4 V` como recomendação de engenharia do projeto;
- escrita: ambos os nós internos devem cruzar `0.9 V` dentro da janela de
  escrita, com `BL=0 V`, `BLB=1.8 V` e `WL=1.8 V`;
- janela inferior de WL: `1.30 ×` o pior tempo de flip completo medido, onde
  flip completo exige os dois nós internos em `90%/10%` de `VDD`;
- `C_BL` final: derivada da profundidade da coluna, parasita de fio por PEX e
  cargas de precharge/mux/sense, com teto de `1.15 × C_BL_extraído`; `50 fF`
  permanece somente condição de triagem pré-layout;
- SNM de retenção e leitura, além de write margin, serão medidos em simulação
  e não podem ser inferidos apenas das razões beta/gamma.

## Estado de validação

| Item | Estado |
|---|---|
| Topologia e conexões lógicas | capturadas no `cells/bitcell_6t.sch` |
| Sizing inicial | corrigido para beta=1.40 e gamma=0.70 |
| Toolchain SKY130A | disponível no container `isaiassh/unic-cass-tools:1.1.0`; `ngspice 44.2`, `xschem`, `magic` e `netgen` confirmados |
| Netlist Xschem | captura hierárquica netlistada; netlist canônico alinhado à ordem `VDD BL BLB VSS WL` |
| Smoke transitório | executado em `tt` com `WPU/WPD/WACC=0.42/0.84/0.60 um` |
| Hold/Read SNM | cinco corners medidos; piores casos `646.567/288.342 mV` em `sf` |
| Read disturb | `0.42/0.84/0.60 µm`: 12/40 no limite provisório de 0.20 V; `WPD=1.05/1.26 µm`: 40/40, exploração apenas |
| SNM nominal vs. meta de 0,4 V | `WPD=0.84`: `0.349 V` FAIL; `1.05`: `0.388 V` FAIL; `1.26`: `0.414 V` PASS em `tt/1.8 V` |
| PVT provisório | `VDD=1.62/1.80/1.95 V`, `T=-40/27/125 °C`, cinco corners; `1.98 V` fora do limite de 1.95 V documentado para os modelos 01v8 |
| Read disturb PVT, 50 fF | `WPD=1.05 µm`: 72/90, pior pico `0.230218 V`; `WPD=1.26 µm`: 90/90, pior pico `0.194778 V`; ambos exploratórios |
| SNM PVT | `WPD=1.05 µm`: mínimo Hold/Read `581.312/289.261 mV`; `WPD=1.26 µm`: `577.761/312.029 mV`; a meta de 0,4 V vale no ponto nominal, enquanto limite PVT/Hold permanece pendente |
| Escrita PVT full-swing | `WPD=1.26 µm`: 90/90 smoke tests; margem dinâmica não medida |
| Fuga em hold PVT | `WPD=1.26 µm`: 90/90 estados estáveis; pior corrente total `21.759 nA` em `fs/1.95 V/125 °C`; orçamento pendente |
| Tensão terminal na leitura | em `VDD=1.95 V`, 30/30 condições excederam 1.95 V; maior pico `2.056858 V` em `sf/125 °C`; impede qualificação desse ponto com o modelo atual |
| SNM com mismatch | `sf_mm`, 200 seeds de Read a 1.62 V/125 °C: mínimo `269.936 mV`; 200 seeds de Hold a 1.62 V/–40 °C: mínimo `541.229 mV`; critério estatístico/yield pendente |
| Write driver | netlist Xschem corrigido; smoke standalone confirma escrita complementar e isolamento com `WE=0`; sweep integrado nominal passou `12/12`; em `1.62 V`, `WPD=1.26 µm` passou `30/30` em cinco corners e três temperaturas |
| Janela inferior de WL | pior flip completo `90/10%` = `0.3216 ns` em `ss/1.62 V/-40 °C`, 0→1; +30% => `0.418 ns` provisórios com `50 fF` |
| Escrita full-swing | 30/30 smoke tests aprovados |
| WLVM | mínimo `0.619 V` em `WPD=0.84 µm`, `0.605 V` em `1.05 µm`; critério de aceite pendente |
| Schematic Freeze | bloqueado: `WPD=1.26 µm` é o único sizing testado que atende Read SNM nominal >=0.4 V, mas ainda faltam carga PEX, limite superior de WL/read disturb dinâmico, qualificação do alvo +10% de VDD, leakage/mismatch e revisão de arquitetura |
| Layout, DRC e LVS | pendentes |

## Leaf cells da etapa 2

O contrato de captura Xschem está centralizado em `cells/README.md`:

- `bitcell_6t.sch`: bitcell 6T canônica;
- `sense_amp.sch`: rascunho estrutural do latch diferencial (`SCLK`);
- `precharge.sch`: PMOS de pré-carga e equalização (`PRECH` ativo-baixo);
- `wl_driver.sch`: buffer de wordline em dois estágios;
- `write_driver.sch`: driver diferencial tri-state (`DATA`, `DATA_B`, `WE`),
  com netlist e smoke funcional verificados; sizing ainda não congelado.

Os sinais de coluna foram padronizados como `BL` e `BLB`; os controles como
`WL`, `SCLK` e `WE`; e as alimentações como `VDD` e `VSS`. Os símbolos `.sym`
serão gerados somente após a inspeção de conectividade dos `.sch` no Xschem.
Até lá, esses arquivos são drafts de captura e não constituem views aprovadas.

## Limites atuais

O toolchain é executado no container `isaiassh/unic-cass-tools:1.1.0`, que
contém SKY130A em `/opt/pdks/sky130A`. A captura Xschem, a bancada de leitura
com bitlines não ideais, a caracterização completa e as verificações físicas
continuam pendentes. Resultados obtidos com o modelo contínuo e dimensões
alternativas não substituem a validação da célula parametrizada no fluxo PDK.
