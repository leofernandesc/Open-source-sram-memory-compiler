# Orçamento pré-layout da capacitância de wordline

Status em 07/10/2026: **baseline pré-layout congelada; G6 físico concluído e
matrizes integradas G7 concluídas, com recuperação de escrita ainda fora da
janela de 4 ns**. A bitcell e o `wl_driver` já possuem layout
com Magic DRC `0` e Netgen LVS único. A coluna 32× também já foi construída,
verificada e extraída; os valores deste documento permanecem como referência
histórica da wordline e **não** devem ser tratados como capacitâncias PEX.

Este documento fecha um bound de engenharia para a carga da wordline antes do
layout. O objetivo é substituir o antigo smoke arbitrário de `50 fF` por uma
carga derivada dos gates das oito bitcells da linha e de uma restrição física
de roteamento. O valor continua sendo pré-layout e deve ser substituído pelo
PEX no G7 após o fechamento físico G6.

## Capacitância dos gates de acesso

`sims/run_wordline_capacitance.py` mede por AC pequena-sinal a capacitância de
gate do NMOS de acesso `WACC=0,60 µm`, com `WL=0`, nos cinco corners,
`1,62/1,80 V`, `-40/27/125 °C`, dois estados de Q e as duas orientações
source/drain.

- `120/120 PASS`;
- `Cgate,max = 0,541868469 fF`;
- pior ponto: `ff/1,80 V/-40 °C`, Q=0;
- uma linha de 8 bits contém 16 gates de acesso:
  `Cgate,row,max = 16 × 0,541868469 = 8,669895504 fF`.

No bench integrado, os dois gates da célula selecionada já estão presentes no
netlist. Logo, a parcela adicional das outras sete células é:

```text
Cgate,extra = 14 × 0,541868469
            = 7,586158566 fF
```

## Bound pré-layout do fio

Para schematic freeze, a WL é orçada em `metal1`, largura mínima `0,14 µm`,
com até `5,0 µm` de extensão horizontal por bit e oito bits por linha. O corner
de capacitância máxima do `sky130A.tech` fornece:

- `defaultareacap(metal1) = 35,7 aF/µm²`;
- `defaultperimeter(metal1) = 49,59 aF/µm`;
- `defaultsidewall(metal1) = 37,6 aF/µm`;
- `metal1 -> metal2 defaultoverlap = 313 aF/µm²`;
- dois vizinhos laterais;
- 16 cruzamentos M1–M2, pois a WL cruza `BL` e `BLB` dos oito bits;
- margem adicional de engenharia de 20%.

O bound é:

```text
Cwire_per_um = (35,7×0,14 + 2×49,59 + 2×37,6) aF/µm
             = 0,179378 fF/µm

Ccross_M1_M2 = 313×0,14×0,14 aF
             = 0,0061348 fF por cruzamento

CWL_wire = 1,20 × (40×0,179378 + 16×0,0061348)
          = 8,727932160 fF
```

## Bound e ponto de screening

```text
CWL,row,max = Cgate,row,max + CWL_wire
            = 8,669895504 + 8,727932160
            = 17,397827664 fF

CWL,extra,max = Cgate,extra + CWL_wire
              = 7,586158566 + 8,727932160
              = 16,314090726 fF
```

Os benches integrados usam a bitcell selecionada explicitamente. Por isso o
capacitor lumped adicional adotado é **17 fF**, acima do bound
`CWL,extra,max=16,314090726 fF`. O antigo smoke de `50 fF` continua válido
apenas como stress test conservador e não como estimativa física da linha.

O bound `CWL,row,max=17,397827664 fF` e o capacitor lumped adicional de `17 fF`
ficam preservados como baseline pré-layout. A linha física representativa de
8 bits em `layout/row_8_wl` fecha DRC/LVS/PEX e mede `C_WL,PEX,max=98,914001 fF`
em `sims/row_8_wl_pex_capacitance_pvt.csv` (`60/60 PASS`). A bitcell selecionada
contribui até `8,988801 fF`; a carga adicional aplicada nos benches integrados
é `89,925201 fF`. A extração WLOFF de `361,100284 fF` da coluna curto-circuita
32 WLs e permanece somente como diagnóstico de stress.

A requalificação integrada usa o PEX do WL driver reforçado. As matrizes PVT
completas terminaram: leitura `60/60 PASS` e escrita `56/60 PASS`, com quatro
falhas de recuperação de bitline na janela de 4 ns. Slew, atraso e largura
efetiva de WL foram considerados nos resultados integrados; o read-disturb
passou na matriz de leitura. O gate G7 continua aberto pelas quatro falhas de
recuperação, confirmadas pelo diagnóstico de 5 ns como cruzamentos entre
`4,03137` e `4,18573 ns`.
