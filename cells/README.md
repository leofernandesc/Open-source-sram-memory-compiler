# Leaf cells Xschem

Contrato de nomes para a etapa 2:

| Célula / artefato | Pinos externos | Controle | Estado |
|---|---|---|---|
| `bitcell_6t/bitcell_6t.sch` | `BL`, `BLB`, `WL`, `VDD`, `VSS` | `WL` | captura canônica da bitcell |
| `row_decoder/row_decoder.sch` | `A0`, `A1`, `PCLK`, `DEC0`–`DEC3`, `VDD`, `VSS` | `PCLK` | rascunho do decoder dinâmico 2-to-4 |
| `sense_amp/sense_amp.sch` | `BL`, `BLB`, `SA_OUT`, `SA_OUTB`, `SCLK`, `VDD`, `VSS` | `SCLK` | rascunho estrutural |
| `precharge/precharge.sch` | `BL`, `BLB`, `PRECH`, `VDD`, `VSS` | `PRECH` ativo-baixo | rascunho estrutural |
| `wordline_driver/wl_driver.sch` | `WL_IN`, `WL`, `VDD`, `VSS` | `WL_IN` | rascunho estrutural |
| `write_driver/write_driver.sch` | `DATA`, `DATA_B`, `BL`, `BLB`, `WE`, `VDD`, `VSS` | `WE` | rascunho estrutural |
| `sims/bitcell_6t/vsource_drive.sym` | `p`, `m` | `p` como saída | fonte de estímulo do testbench hierárquico |

`bitcell_6t/sram_6t.sch` permanece como captura legada para comparação. Os arquivos devem gerar símbolos `.sym` somente depois de a conectividade
ser verificada pelo Xschem. A presença de um `.sch` nesta etapa não significa que a
célula já passou por netlist, DRC, LVS ou simulação.

## Testbench hierárquico de leitura

Abra o testbench visual no container SKY130A:

```bash
cd /home/designer/shared
export PDK=sky130A
export PDK_ROOT=/opt/pdks
xschem sims/bitcell_6t/tb_bitcell_6t_read.sch
```

`bitcell_6t/bitcell_6t.sch` é uma leaf cell, mas contém um smoke test marcado
`only_toplevel=true`. Quando aberta diretamente, ela carrega os modelos
SKY130A, usa `WPU=WPD=WACC=0.42 µm`, aplica pré-carga e um pulso de WL e grava
`bitcell_6t.raw`. Quando instanciada, esse smoke test é omitido e os estímulos
vêm do testbench hierárquico.

O arquivo `sims/bitcell_6t/tb_bitcell_6t_read.sch` instancia
`cells/bitcell_6t/bitcell_6t.sym`, duas chaves ideais de pré-carga e os capacitores de 5 fF em `BL` e `BLB`. A pré-carga é
desligada em 10 ns e permanece desligada durante a leitura, de 20 a 30 ns.
O símbolo tem parâmetros `WPU`, `WPD` e `WACC`: seus padrões são os valores
alvo 0,21/0,42/0,30 µm; o testbench usa explicitamente 0,42/0,42/0,42 µm,
único sizing desta etapa aceito pelos modelos contínuos instalados.

As fontes do testbench usam
`sims/bitcell_6t/vsource_drive.sym`, que declara o terminal positivo como saída para que o ERC do Xschem reconheça `WL` e `PRE` como redes
dirigidas. O retorno elétrico usa uma única rede `GND`, conectada ao pino `VSS`
da bitcell, evitando o curto artificial entre `GND` e `VSS` causado por duas
redes de referência distintas.

O botão de simulação do Xschem executa o testbench hierárquico com o corner
`tt`. O bloco de controle inicializa `Q=1` e `QB=0`, mede as bitlines em 21 ns
e mede os nós internos como `v(xbitcell.Q)` e `v(xbitcell.QB)`. A simulação
grava `tb_bitcell_6t_read.raw` no diretório de simulações do Xschem para
inspeção das formas de onda. O deck externo
`sims/bitcell_6t/tb_bitcell_6t_read.spice` usa os mesmos estímulos para o
sweep dos cinco corners e dos dois estados armazenados.
