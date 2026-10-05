# Avaliação pré-layout de C_BL

Status: **orçamento pré-layout recalculado, com validação elétrica pendente**.
As capacitâncias de terminal da bitcell, precharge e entrada do sense
amplifier foram caracterizadas com o modelo SKY130A em PVT. A entrada do novo
`cells/sense_amp.sch` é maior que a da topologia anterior; o orçamento antigo
de `49,696512 fF` não é mais válido. `Cwire_cell` continua sendo uma hipótese
física a verificar no layout.

## Modelo e convenções

Para cada bitline (`BL` ou `BLB`), a regra original registrada em
`specs/technical_specification.md` é:

```text
C_BL(N) = N × (0,2 fF + Cwire_cell) + Cprecharge + Cwrite + Cmux + Csense
```

`Cmux = 0` na arquitetura atual: uma palavra por linha física e sem mux de
coluna. `N` é 4, 8, 16 ou 32. A aproximação de `0,2 fF/célula` foi substituída
para o orçamento de freeze pela capacitância efetiva medida no terminal do
transistor de acesso da bitcell.

## Caracterização elétrica dos termos de dispositivo

O script `sims/run_cbl_device_capacitance.py` usa análise AC de pequena-sinal
em `1 MHz` e calcula `Ceff = |Im(I)|/(2*pi*f)`. Foram varridos cinco corners,
`1,62/1,80 V`, `-40/27/125 °C` e, quando aplicável, as duas orientações do
dispositivo e os dois estados DC. O sweep terminou com `270/270 PASS`.

| Parcela | Máximo PVT por bitline | Pior condição |
|---|---:|---|
| Terminal da célula, `WACC=0,60 µm` | `0,452619 fF/célula` | `fs`, 1,62 V, 125 °C, estado 1 |
| `Cprecharge`, 3 PMOS `W=0,42 µm`, desligados | `0,908533 fF` | `tt`, 1,62 V, 125 °C |
| `Cwrite`, `write_driver` tri-state com `WE=0` | `4,033129 fF` | `ss`, 1,62 V, 125 °C, `DATA=0`, BLB |
| `Csense`, latch com chave PMOS `W=2,0 µm`, `SCLK=0`, BL/BLB em VDD | `9,004605 fF` | `sf`, 1,80 V, 125 °C, BL |

O sense amplifier anterior usava isolamento NMOS de `0,42 µm`; seus
`0,324590 fF` eram válidos só para aquela topologia. A nova medição usa o
netlist extraído por Xschem do latch de sete transistores em
`cells/sense_amp.sch`. O sweep de pequena-sinal em `1 MHz`, com ambas as
bitlines em VDD e `SCLK=0`, terminou `60/60 PASS`; o intervalo foi
`7,853676–9,004605 fF`. Ainda é necessário verificar a dependência dessa
capacitância com a excursão da bitline e com a fase de avaliação. Uma triagem
adicional em `tt/1,80 V/27 °C`, com uma bitline descarregada em `0/100/200 mV`,
ambas as orientações e ambos os pinos sondados, passou `12/12` e encontrou
`7,802682–8,380972 fF` (`sims/sense_input_capacitance_excursion_tt.csv`).
Esse ponto nominal não é bound PVT de excursão.

Com os máximos PVT, o orçamento pré-layout passa a ser:

```text
C_BL(N) = N × (0,452619 fF + Cwire_cell)
          + 0,908533 fF + 4,033129 fF + 9,004605 fF
        = Cfixed(N) + N × Cwire_cell
```

| Nrows | `Cfixed` sem fio | Teto paramétrico |
|---:|---:|---|
| 4  | `15,756743 fF` | `15,756743 fF + 4×Cwire_cell` |
| 8  | `17,567219 fF` | `17,567219 fF + 8×Cwire_cell` |
| 16 | `21,188171 fF` | `21,188171 fF + 16×Cwire_cell` |
| 32 | `28,430075 fF` | `28,430075 fF + 32×Cwire_cell` |

Esses valores são por uma bitline; `BL` e `BLB` não devem ser somadas ao
comparar com o capacitor usado em um bench de uma única bitline.

## Bound pré-layout de fio

Para o freeze, a bitline fica orçada em `metal2`, largura mínima `0,14 µm`,
com segmento vertical de no máximo `5,0 µm` por linha. O cálculo usa o corner
de capacitância máxima do `sky130A.tech` do Magic:

- `defaultareacap(metal2) = 23,5 aF/µm²`;
- `defaultperimeter(metal2) = 46,03 aF/µm`;
- `defaultsidewall(metal2) = 40,2 aF/µm`;
- acoplamento lateral contabilizado em **dois vizinhos**;
- cruzamento `metal2 -> metal1 = 313 aF/µm²`, usando uma interseção mínima
  `0,14 × 0,14 µm²` por linha;
- margem adicional de engenharia de `20%` aplicada ao termo de fio.

O bound resultante é:

```text
Cwire_per_um = (23,5×0,14 + 2×46,03 + 2×40,2) aF/µm
             = 0,17575 fF/µm

Ccross_M2_M1 = 313×0,14×0,14 aF
             = 0,006135 fF por linha

Cwire_cell_budget = 1,20 × (5,0×0,17575 + 0,006135)
                  = 1,061862 fF/célula
```

Aplicando esse orçamento:

| Nrows | `C_BL,max` pré-layout por bitline |
|---:|---:|
| 4  | `20,004191 fF` |
| 8  | `26,062115 fF` |
| 16 | `38,177963 fF` |
| 32 | `62,409659 fF` |

O caso de 32 linhas **não** é coberto pelos antigos screenings de `50 fF` ou
`60 fF`. O novo ponto conservador de triagem é `65 fF`, que deixa
`2,590341 fF` de folga sobre o bound pré-layout de 32 linhas. Não é um valor
PEX. Se o
layout exigir segmento maior que `5,0 µm/linha`, outra camada ou uma
vizinhança que aumente a capacitância além desse bound, o gate deve ser
reaberto.

## Evidência por parcela e dado que falta

| Parcela | Evidência no checkout | Estado e dado necessário |
|---|---|---|
| `Nrows` | `specs/technical_specification.md` define 4/8/16/32 linhas; `memory/memory-ip/run_state.md` registra uma palavra por linha física. | Resolvido para as quatro configurações. |
| Terminal da célula | `sims/cbl_device_capacitance_pvt.csv`, `270/270 PASS`. | Fechado em `0,452619 fF/célula` como máximo do sweep esquemático PVT; será substituído/confirmado por PEX pós-layout. |
| `Cwire_cell` | Corner máximo do extractor Magic + constraint `metal2`, `0,14 µm`, `<=5,0 µm/linha`, dois vizinhos e +20%. | Orçamento pré-layout `<=1,061862 fF/célula`; validar a geometria no layout e substituir por PEX. |
| `Cprecharge` | Netlist corrigido de `cells/precharge.sch` e sweep PVT de pequena-sinal. | Fechado em `0,908533 fF` como máximo esquemático PVT por bitline; função/timing do precharge continua sendo gate separado. |
| `Cwrite` | `sims/write_driver_capacitance_pvt.csv`, `120/120 PASS`, usando o netlist extraído de `cells/write_driver.sch` com `WE=0`, ambos os dados e BL/BLB. | Máximo observado `4,033129 fF` por bitline; deve permanecer no orçamento enquanto o write driver estiver conectado diretamente à coluna. |
| `Csense` | `sims/sense_input_capacitance_pvt.csv`, `60/60 PASS`, usando o netlist do `cells/sense_amp.sch`. | Máximo observado `9,004605 fF` em BL/BLB pré-carregadas; verificar dependência do ponto de operação e offset/timing. |
| `Cmux` | Arquitetura de uma palavra por linha e sem mux de coluna na especificação atual. | `0 fF` enquanto a arquitetura não mudar. |

## Screening não usado como bound

`50 fF` e `60 fF` permanecem apenas como resultados históricos de screening.
O próximo screening usa `65 fF` para 32 linhas. O bound pré-layout depende da validade
do orçamento de fio e do máximo de `Csense` ao longo da excursão de leitura.

## Condição para fechar o gate

O orçamento de `62,409659 fF` só pode fechar o gate pré-layout depois que
leitura, escrita e temporização forem reavaliadas nessa carga e a variação de
`Csense` com a excursão da bitline for verificada. Após o schematic freeze e
layout, substituir a estimativa por `C_BL,PEX` e requalificar até
`1,15 × C_BL,PEX`.
