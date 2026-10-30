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

Tabela do sizing inicial de captura, preservada como histórico; o sizing
canônico vigente (`WPU/WPD/WACC=0,42/1,26/0,60 µm`) está resumido na tabela de
estado atual ao final deste documento.

| Dispositivos | Função | W (um) | Razão |
|---|---|---:|---:|
| M1, M3 | pull-up PMOS | 0.42 | gamma = 0.70 em relação ao acesso |
| M2, M4 | pull-down NMOS | 0.84 | beta = 1.40 em relação ao acesso |
| M5, M6 | acesso NMOS | 0.60 | referência |

Na captura inicial, esse candidato passou pela primeira caracterização de
Hold/Read SNM nos corners `tt/ff/ss/fs/sf`; a WLVM nominal foi medida em
testbench ideal. Esse estado foi supersedido pelo schematic freeze de
05/10/2026 e pelo fechamento físico G6/G7 requalificado em 08/10. Os parâmetros congelados estão na
captura; a qualificação integrada pós-layout e seus limites estão resumidos na
tabela de estado atual desta especificação.

A leitura transitória com bitlines capacitivas reprovou o limite provisório
de excursão máxima do nó baixo em 28/40 casos para `WPD=0.84 µm`. A exploração
de `WPD=1.05 µm` e `1.26 µm` passou esse gate em 40/40 casos, mantendo os demais
tamanhos. `WPD=1.26 µm` foi selecionado para closure após também ser o único
sizing testado que atingiu a meta nominal de Read SNM de `0.4 V`; foi congelado
e aplicado ao esquemático em 05/10/2026. `WPD=1.05 µm` permanece apenas
exploratório.

O teste de escrita com bitlines ideais full-swing, `WL=1.8 V` por 10 ns e
verificação após `WL` descer passou em 30/30 combinações de corner, sentido
de escrita e sizing (`WPD=0.84/1.05/1.26 µm`). Esse resultado é funcional:
não caracteriza write margin, resistência do driver ou tempo mínimo.

A margem dinâmica por WLVM também foi medida por busca binária para
`WPD=0.84/1.05 µm`, pulso de 10 ns, cinco corners e ambos os sentidos. O pior
caso foi `0.619/0.605 V`, respectivamente. Essa comparação usa drivers ideais
e não define critério independente de aceite WLVM. A revisão G7 de 07/10 registrou escrita integrada `60/60` com PEX;
a requalificação de 08/10 ainda requer as novas cargas e a matriz completa.

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
- leitura: alvo integrado provisório de pelo menos `200 mV` antes da
  amostragem do sense, sem aumento do nó armazenando `0` superior a `0.2 V`;
  `150 mV` é mantido como piso efetivo de mismatch após `800/800` decisões
  sem falha, reservando `50 mV` de guarda pré-layout para incerteza/ruído de
  entrada. Essa guarda é uma alocação de engenharia, não sign-off de ruído;
- Read SNM no ponto nominal (`tt`, `VDD=1.8 V`, temperatura nominal):
  `>= 0.4 V` como recomendação de engenharia do projeto;
- escrita: ambos os nós internos devem cruzar `0.9 V` dentro da janela de
  escrita, com `BL=0 V`, `BLB=1.8 V` e `WL=1.8 V`;
- janela inferior de WL: `1.30 ×` o pior tempo de flip completo medido, onde
  flip completo exige os dois nós internos em `90%/10%` de `VDD`;
- `C_BL` para schematic freeze: estimativa conservadora pré-layout derivada da
  profundidade da coluna e das cargas de célula/fio/precharge/write-driver/mux/sense;
  o orçamento corrigido é `20.004/26.062/38.178/62.410 fF` para 4/8/16/32 linhas,
  sob a constraint de `metal2`, `0.14 µm`, `<=5.0 µm/linha` e +20% no fio. A
  revalidação elétrica usa `65 fF` como ponto conservador de screening;
- `C_BL` pós-layout: substituída pelo valor extraído por PEX, com teto de
  requalificação de `1.15 × C_BL_extraído`; PEX não é pré-requisito do
  schematic freeze;
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
| Faixa de alimentação | qualificação contínua em `1.62–1.80 V`; `1.95 V` permanece somente limite estático/auditoria do modelo 01v8; `1.98 V` não é qualificável com o modelo atual |
| Read disturb PVT, 50 fF | `WPD=1.05 µm`: 72/90, pior pico `0.230218 V`; `WPD=1.26 µm`: 90/90, pior pico `0.194778 V`; ambos exploratórios |
| Sizing canônico congelado | `WPU/WPD/WACC=0.42/1.26/0.60 µm`; aplicado em `cells/bitcell_6t.sch` e `.sym`; G1/G2/G3/G4 fechados para screening pré-layout |
| SNM PVT | `WPD=1.05 µm`: mínimo Hold/Read `581.312/289.261 mV`; `WPD=1.26 µm`: `577.761/312.029 mV`; meta de 0,4 V nominal. DC-SNM PVT continua fora do gate; leitura dinâmica G7 pós-layout foi requalificada `60/60` |
| Escrita PVT full-swing | `WPD=1.26 µm`: 90/90 smoke tests pré-layout; G7 pós-layout atual passou `60/60`, recuperação máxima `3,978840 ns` com o limite PEX de `597,056241 fF` |
| Fuga em hold PVT | `WPD=1.26 µm`: 90/90 estados estáveis; na faixa qualificada 1,62–1,80 V, pior corrente total `20,0676 nA/célula` e potência VDD `36,1079 nW/célula` em `fs/1,80 V/125 °C`; 1,95 V permanece auditoria |
| Tensão terminal na leitura | em `VDD=1.95 V`, 30/30 condições excederam 1.95 V; maior pico `2.056858 V` em `sf/125 °C`; impede qualificação desse ponto com o modelo atual |
| SNM com mismatch | `sf_mm`, 200 seeds de Read a 1.62 V/125 °C: mínimo `269.936 mV`; 200 seeds de Hold a 1.62 V/–40 °C: mínimo `541.229 mV`; critério estatístico/yield pendente |
| Write driver | netlist Xschem corrigido; smoke standalone confirma escrita complementar e isolamento com `WE=0`; sweep integrado nominal passou `12/12`; em `1.62 V`, `WPD=1.26 µm` passou `30/30` em cinco corners e três temperaturas |
| Janela inferior de WL | G1 65 fF: `0.41496 ns` no rerun crítico; integração com `17 fF` extras de WL elevou o pior full-flip para `0.37283 ns`, portanto `WL_min(+30%)=0.484679 ns`. A campanha integrada de escrita usou `WL_IN=3.2 ns` e passou `60/60`. |
| Escrita full-swing | 30/30 smoke tests aprovados |
| WLVM | triagem ideal histórica: mínimo `0.619 V` em `WPD=0.84 µm`, `0.605 V` em `1.05 µm`; não há gate independente de WLVM. G7 atual passou `60/60`, com WE em `2,20 ns`, WL_IN em `3,40 ns` e margem WL30 mínima de `79,696 ps` |
| Carga de bitline pré-layout | orçamento corrigido: `Ccell_access,max=0.452619 fF`, `Cprecharge,max=0.908533 fF`, `Cwrite,max=4.033129 fF`, `Csense,max=9.004605 fF` e fio `1.061862 fF/célula`; `C_BL,max=62.409659 fF` em 32 linhas; usar 65 fF para revalidação pré-layout |
| Schematic Freeze | **concluído em 05/10/2026**: G4 dinâmico fechado como engineering screening; timing de freeze `SCLK=2.84 ns`; potência permanece referência sem teto macro aprovado. O G7 atual foi requalificado com PEX e cargas `.t0`. |
| Layout, DRC e LVS | Cinco leafs, coluna 32×, WL 8 bits e coluna G7 com DRC completo zero, LVS único e PEX. C_BL/C_WL e Ceff foram repetidas com saídas latch `.t0`; leitura e escrita integradas passaram `60/60`. **G7/Fase 1 fechados** no escopo da célula e leafs físicas. |
| Verificação manual de DRC/LVS (08/10) | Magic gráfico da bitcell: `Total DRC errors found: 0`; coluna G7 hierárquica/flat: DRC `0/0`; Netgen manual com setup SKY130A carregado: `Circuits match uniquely`, `212` MOS (`136` NMOS, `76` PMOS) e `82` redes por lado. A execução anterior com `/dev/null` é histórica. Persistem avisos de MOS como *placeholders/black boxes* e propriedades ausentes, limitando o aceite à correspondência estrutural. Log local: `layout/column_32_full_g7_wpre2p52_final/lvs_sky130_manual.log` (ignorado pelo Git). Consulte [o roteiro](../docs/validacao_manual_drc_lvs_sky130a.md). |

## Leaf cells da etapa 2

O contrato de captura Xschem está centralizado em `cells/README.md`:

- `bitcell_6t.sch`: bitcell 6T canônica;
- `sense_amp.sch`: latch diferencial de sete transistores com conectividade
  netlistada, chaves PMOS de amostragem `W=2,0 µm`; resposta determinística,
  mismatch, setup e integração PVT em 65 fF já caracterizados para screening
  pré-layout; ruído/yield de produção não é reivindicado;
- `precharge.sch`: três PMOS de pré-carga/equalização com conectividade
  netlistada; capacitância de entrada já caracterizada;
- `wl_driver.sch`: buffer de wordline em dois estágios;
- `write_driver.sch`: driver diferencial tri-state (`DATA`, `DATA_B`, `WE`),
  com netlist, integração PVT e G4 mismatch verificados; sizing atual preservado
  no schematic freeze pré-layout.

Os sinais de coluna são `BL` e `BLB`; os controles são `WL`, `SCLK` e `WE`; e
as alimentações são `VDD` e `VSS`. Schematic freeze, G6 e G7 estão
requalificados, e a Fase 1 está `CLOSED_ENGINEERING_QUALIFICATION` para a
bitcell e suas leafs físicas. O decoder 2→4 foi alterado para uma arquitetura
dinâmica e tem um netlist SPICE candidato em `cells/row_decoder_2to4.spice`.
Simulação, sizing, captura Xschem, layout/DRC/LVS e integração da macro 4×8
continuam planejados para a Fase 2. Essa realocação do decoder altera o
planejamento original do entregável de periféricos e permanece pendente de
validação formal pela equipe/orientadores. Evidências, critérios e limitações da Fase 1:
[`docs/phase1_leaf_cell_closure.md`](../docs/phase1_leaf_cell_closure.md). Para a
conferência manual Magic/Netgen, consulte
[`docs/validacao_manual_drc_lvs_sky130a.md`](../docs/validacao_manual_drc_lvs_sky130a.md).

## Escopo posterior à Fase 1

Yield de produção, ruído estatístico completo, DC-SNM PVT e teto de potência
macro não foram reivindicados e seguem fora do escopo da Fase 1. No planejamento
atual, a Fase 2 abrange o decodificador 2→4 e a integração macro 4×8; essa
realocação permanece pendente de validação formal pela equipe/orientadores. Os resultados de
screening pré-layout continuam identificados como tal nas tabelas históricas
deste documento.
