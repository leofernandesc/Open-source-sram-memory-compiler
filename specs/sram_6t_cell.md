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

O ponto de partida elétrico é `L=0.15 um`, `nf=1`, com sizing por função:

| Dispositivos | Função | W (um) | Razão |
|---|---|---:|---:|
| M1, M3 | pull-up PMOS | 0.21 | gamma = 0.70 em relação ao acesso |
| M2, M4 | pull-down NMOS | 0.42 | beta = 1.40 em relação ao acesso |
| M5, M6 | acesso NMOS | 0.30 | referência |

Esses valores são apenas o ponto de partida; estabilidade de leitura,
writability, leakage e área deverão ser medidos antes de congelar o
dimensionamento. Os valores devem permanecer parametrizados na captura para
permitir uma varredura posterior.

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
- escrita: ambos os nós internos devem cruzar `0.9 V` dentro da janela de
  escrita, com `BL=0 V`, `BLB=1.8 V` e `WL=1.8 V`;
- SNM de retenção e leitura, além de write margin, serão medidos em simulação
  e não podem ser inferidos apenas das razões beta/gamma.

## Estado de validação

| Item | Estado |
|---|---|
| Topologia e conexões lógicas | capturadas no `cells/sram_6t.sch` |
| Sizing inicial | corrigido para beta=1.40 e gamma=0.70 |
| Toolchain SKY130A | disponível no container `isaiassh/unic-cass-tools:1.1.0`; `ngspice 44.2`, `xschem`, `magic` e `netgen` confirmados |
| Netlist Xschem | pendente: captura ainda não foi netlisted no container SKY130A |
| Smoke transitório | executado em `tt` com modelo contínuo e sizing provisório `WPU=WACC=0.42 um` |
| Sizing original `WPU=0.21 um`, `WACC=0.30 um` | pendente: o runtime contínuo rejeitou esses valores; não está aprovado |
| Layout, DRC e LVS | pendentes |

## Leaf cells da etapa 2

O contrato de captura Xschem está centralizado em `cells/README.md`:

- `sram_6t.sch`: bitcell 6T existente;
- `sense_amp.sch`: rascunho estrutural do latch diferencial (`SCLK`);
- `precharge.sch`: PMOS de pré-carga e equalização (`PRECH` ativo-baixo);
- `wl_driver.sch`: buffer de wordline em dois estágios;
- `write_driver.sch`: rascunho do driver diferencial de escrita (`DATA`,
  `DATA_B`, `WE`).

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
