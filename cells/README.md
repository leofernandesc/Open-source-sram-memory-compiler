# Leaf cells Xschem

Contrato de nomes para a etapa 2:

| Célula | Pinos externos | Controle | Estado |
|---|---|---|---|
| `bitcell_6t.sch` | `BL`, `BLB`, `WL`, `VDD`, `VSS` | `WL` | captura canônica da bitcell |
| `sense_amp.sch` | `BL`, `BLB`, `SA_OUT`, `SA_OUTB`, `SCLK`, `VDD`, `VSS` | `SCLK` | rascunho estrutural |
| `precharge.sch` | `BL`, `BLB`, `PRECH`, `VDD`, `VSS` | `PRECH` ativo-baixo | rascunho estrutural |
| `wl_driver.sch` | `WL_IN`, `WL`, `VDD`, `VSS` | `WL_IN` | rascunho estrutural |
| `write_driver.sch` | `DATA`, `DATA_B`, `BL`, `BLB`, `WE`, `VDD`, `VSS` | `WE` | rascunho estrutural |
| `vsource_drive.sym` | `p`, `m` | `p` como saída | fonte de estímulo do testbench hierárquico |

`sram_6t.sch` permanece como captura legada para comparação. Os arquivos devem gerar símbolos `.sym` somente depois de a conectividade ser
verificada pelo Xschem. A presença de um `.sch` nesta etapa não significa que a
célula já passou por netlist, DRC, LVS ou simulação.

## Testbench hierárquico de leitura

Abra o testbench visual no container SKY130A:

```bash
cd /home/designer/shared
export PDK=sky130A
export PDK_ROOT=/opt/pdks
xschem cells/tb_bitcell_6t_read.sch
```

O arquivo `tb_bitcell_6t_read.sch` instancia `bitcell_6t.sym`, duas chaves
ideais de pré-carga e os capacitores de 5 fF em `BL` e `BLB`. A sequência
visual é pré-carga de 0 a 10 ns e leitura com `WL` de 20 a 30 ns.

As fontes do testbench usam `vsource_drive.sym`, que declara o terminal
positivo como saída para que o ERC do Xschem reconheça `WL` e `PRE` como redes
dirigidas. O retorno elétrico usa uma única rede `GND`, conectada ao pino `VSS`
da bitcell, evitando o curto artificial entre `GND` e `VSS` causado por duas
redes de referência distintas.

Para a validação elétrica oficial, continue usando o deck externo
`sims/tb_bitcell_6t_read.spice` e o sweep automatizado. O testbench Xschem é a
visão hierárquica para inspeção e edição dos estímulos; ele não substitui o
deck externo validado.
