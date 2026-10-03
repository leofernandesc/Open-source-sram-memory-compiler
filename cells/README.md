# Leaf cells Xschem

Contrato de nomes para a etapa 2:

| Célula | Pinos externos | Controle | Estado |
|---|---|---|---|
| `bitcell_6t.sch` | `BL`, `BLB`, `WL`, `VDD`, `VSS` | `WL` | captura canônica da bitcell |
| `sense_amp.sch` | `BL`, `BLB`, `SA_OUT`, `SA_OUTB`, `SCLK`, `VDD`, `VSS` | `SCLK` | latch de 7 transistores netlistado; 330/330 casos determinísticos; offset/ruído/setup pendentes |
| `precharge.sch` | `BL`, `BLB`, `PRECH`, `VDD`, `VSS` | `PRECH` ativo-baixo | conectividade netlistada; capacitância de entrada caracterizada; timing funcional pendente |
| `wl_driver.sch` | `WL_IN`, `WL`, `VDD`, `VSS` | `WL_IN` | dois inversores conectados, sizing provisório; PVT e carga real de WL pendentes |
| `write_driver.sch` | `DATA`, `DATA_B`, `BL`, `BLB`, `WE`, `VDD`, `VSS` | `WE` | netlist e smoke funcional verificados; sizing ainda provisório |
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

Esses resultados fecham somente conectividade, complementaridade e isolamento
funcional do driver. `50 fF`, janela de `10 ns`, borda de `200 ps` e
`Wdriver=0,84 µm` são hipóteses de triagem, não requisitos de write margin.

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
SKY130A, usa `WPU/WPD/WACC=0,42/0,84/0,60 µm`, aplica pré-carga e um pulso de WL e grava
`bitcell_6t.raw`. Quando instanciada, esse smoke test é omitido e os estímulos
vêm do testbench hierárquico.

O arquivo `tb_bitcell_6t_read.sch` instancia `bitcell_6t.sym`, duas chaves
ideais de pré-carga e os capacitores de 5 fF em `BL` e `BLB`. A pré-carga é
desligada em 10 ns e permanece desligada durante a leitura, de 20 a 30 ns.
O símbolo tem parâmetros `WPU`, `WPD` e `WACC`: seus padrões e os do testbench
são `0,42/0,84/0,60 µm`. Esse candidato preserva beta=1,40 e gamma=0,70 e usa
larguras aceitas pelos modelos contínuos instalados.

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
