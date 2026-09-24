# Leaf cells Xschem

Contrato de nomes para a etapa 2:

| Célula | Pinos externos | Controle | Estado |
|---|---|---|---|
| `bitcell_6t.sch` | `BL`, `BLB`, `WL`, `VDD`, `VSS` | `WL` | captura canônica da bitcell |
| `sense_amp.sch` | `BL`, `BLB`, `SA_OUT`, `SA_OUTB`, `SCLK`, `VDD`, `VSS` | `SCLK` | rascunho estrutural |
| `precharge.sch` | `BL`, `BLB`, `PRECH`, `VDD`, `VSS` | `PRECH` ativo-baixo | rascunho estrutural |
| `wl_driver.sch` | `WL_IN`, `WL`, `VDD`, `VSS` | `WL_IN` | rascunho estrutural |
| `write_driver.sch` | `DATA`, `DATA_B`, `BL`, `BLB`, `WE`, `VDD`, `VSS` | `WE` | rascunho estrutural |

`sram_6t.sch` permanece como captura legada para comparação. Os arquivos devem gerar símbolos `.sym` somente depois de a conectividade ser
verificada pelo Xschem. A presença de um `.sch` nesta etapa não significa que a
célula já passou por netlist, DRC, LVS ou simulação.
