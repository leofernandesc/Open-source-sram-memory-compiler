# Leaf cells Xschem

**Status em 08/10/2026:** as cinco variantes físicas, a coluna de 32 linhas,
a linha WL de 8 bits e a coluna integrada G7 passaram DRC completo, LVS único
e nova PEX. A qualificação **elétrica G7 continua aberta**: Ceff da bitcell,
C_BL e C_WL devem ser caracterizadas novamente usando inicialização nos nós
da latch (`.t0`), seguida pelas matrizes integradas de leitura e escrita.
Os resultados integrados `60/60` de 07/10 são históricos, supersedidos pela
revisão física, e os smokes corrigidos em TT de 08/10 usam cargas provisórias.

Contrato de nomes para a etapa 2:

| Célula | Pinos externos | Controle | Estado |
|---|---|---|---|
| `bitcell_6t.sch` | `BL`, `BLB`, `WL`, `VDD`, `VSS` | `WL` | captura canônica da bitcell |
| `sense_amp.sch` | `BL`, `BLB`, `SA_OUT`, `SA_OUTB`, `SCLK`, `VDD`, `VSS` | `SCLK` | latch de 7 transistores; G2/G4 screening e variante física 1,5× com DRC/LVS/PEX; leitura integrada `60/60` histórica de 07/10 |
| `precharge.sch` | `BL`, `BLB`, `PRECH`, `VDD`, `VSS` | `PRECH` ativo-baixo | captura/topologia de freeze; leaf física final `Wpre=2,52 µm` com DRC/LVS/PEX e Ceff PVT `60/60` |
| `wl_driver.sch` | `WL_IN`, `WL`, `VDD`, `VSS` | `WL_IN` | dois inversores; variante física integrada reforçada com PEX; slews/timing de 07/10 históricos |
| `write_driver.sch` | `DATA`, `DATA_B`, `BL`, `BLB`, `WE`, `VDD`, `VSS` | `WE` | esquema congelado; variante física `Wout=5,04 µm` com DRC/LVS/PEX; escrita integrada G7 `60/60` histórica de 07/10 |
| `vsource_drive.sym` | `p`, `m` | `p` como saída | fonte de estímulo do testbench hierárquico |

`sram_6t.sch` permanece como captura legada para comparação. Gerar símbolos
`.sym` depois de conferir a conectividade no Xschem. A presença de um `.sch`
ou de um smoke PASS não significa DRC/LVS nem qualificação da leaf.

O estado e os gates de fechamento estão em
[`docs/phase1_leaf_cell_closure.md`](../docs/phase1_leaf_cell_closure.md).

## Write driver

`write_driver.sch` usa dois ramos tri-state complementares e um inversor interno
para gerar `WE_B`. Com `WE=1`, o driver força `BL=DATA` e `BLB=DATA_B`; com
`WE=0`, ambos os caminhos de pull-up/pull-down ficam desabilitados.

O netlist headless do Xschem foi gerado sem o curto `DATA_B–BLB` da versão
anterior e sem redes de controle abertas. O smoke standalone em `tt`, 1,8 V e
50 fF por bitline observou os dois sentidos de escrita e, durante `WE=0`,
deriva de apenas `3,391/1,459 mV` em 3 ns. Um sweep integrado com a bitcell em
`tt/ss/ff`, 1,8 V, 27 °C, dois sentidos e `WPD=0,84/1,26 µm` resultou em
`12/12` trocas de estado; o cruzamento de `Q=VDD/2` ocorreu entre
`0,148–0,212 ns` após a subida de `WL`.

Os testes posteriores em 65 fF + 17 fF de WL fecharam G3 e G4 com o driver
real. `Wdriver=0,84 µm` permanece o sizing do schematic freeze pré-layout;
para a revisão histórica G7 de 07/10 foi usada a variante física reforçada
`Wout=5,04 µm`, integrada com o precharge final, com resultado `60/60` naquele
PEX. Esse resultado não fecha a matriz elétrica da revisão física de 08/10.

## Testbench hierárquico de leitura

Abra o testbench visual no container SKY130A:

```bash
cd /home/designer/shared
export PDK=sky130A
export PDK_ROOT=/opt/pdks
xschem cells/tb_bitcell_6t_read.sch
```

`bitcell_6t.sch` é uma leaf cell, mas contém um smoke test marcado
`only_toplevel=true`. Quando aberta diretamente, ela carrega os modelos
SKY130A, usa `WPU/WPD/WACC=0,42/1,26/0,60 µm`, aplica pré-carga e um pulso de WL e grava
`bitcell_6t.raw`. Quando instanciada, esse smoke test é omitido e os estímulos
vêm do testbench hierárquico.

O arquivo `tb_bitcell_6t_read.sch` instancia `bitcell_6t.sym`, duas chaves
ideais de pré-carga e os capacitores de 5 fF em `BL` e `BLB`. A pré-carga é
desligada em 10 ns e permanece desligada durante a leitura, de 20 a 30 ns.
O símbolo tem parâmetros `WPU`, `WPD` e `WACC`: seus padrões e os do testbench
são `0,42/1,26/0,60 µm`, o sizing congelado para a etapa pré-layout.

As fontes do testbench usam `vsource_drive.sym`, que declara o terminal
positivo como saída para que o ERC do Xschem reconheça `WL` e `PRE` como redes
dirigidas. O retorno elétrico usa uma única rede `GND`, conectada ao pino `VSS`
da bitcell, evitando o curto artificial entre `GND` e `VSS` causado por duas
redes de referência distintas.

O botão de simulação do Xschem executa o testbench hierárquico com o corner
`tt`. O bloco de controle inicializa `Q=1` e `QB=0`, mede as bitlines em 21 ns
e mede os nós internos como `v(xbitcell.Q)` e `v(xbitcell.QB)`. A simulação
grava `tb_bitcell_6t_read.raw` no diretório de simulações do Xschem para
inspeção das formas de onda. O deck externo
`sims/tb_bitcell_6t_read.spice` usa os mesmos estímulos para o sweep dos cinco
corners e dos dois estados armazenados.
