# Avaliação pré-layout de C_BL

Status em 07/10/2026: **baseline pré-layout preservada; G6 físico concluído; coluna G7 reforçada extraída e requalificação integrada concluída, com G7 aberto por quatro falhas de recuperação de escrita**.
As cinco leaf cells já possuem layout com Magic DRC `0` e Netgen LVS único.
Os valores deste documento continuam sendo o orçamento histórico usado para o
schematic freeze e para os screenings de 65 fF; eles **não** são PEX. A coluna
física 32× já fornece agora o valor pós-layout real usado pelo G7.

As capacitâncias de terminal da bitcell, precharge e entrada do sense
amplifier foram caracterizadas com o modelo SKY130A em PVT. A entrada do novo
`cells/sense_amp.sch` é maior que a da topologia anterior; o orçamento antigo
de `49,696512 fF` não é mais válido. `Cwire_cell` foi uma hipótese física
pré-layout. Agora que o layout existe, o próximo passo é substituí-la pela
extração parasitária, sem rebatizar os bounds abaixo como valores medidos de
PEX.

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

## Transição para o G7 pós-layout

O screening pré-layout em `65 fF` e o bound `62,409659 fF` ficam preservados
como baseline de engenharia que sustentou o freeze. A coluna física original
`layout/column_32_full` mediu `422,651867 fF`, com teto `486,049647 fF`; esses
valores foram substituídos após o reforço dos periféricos. A coluna
`layout/column_32_full_g7`, integrada com sense 1,5×, precharge `W=2,10 µm` e
write `Wout=5,04 µm`, passou DRC hierárquico/flat, LVS único e PEX. Sua
varredura PVT passou `120/120`, com `C_BL,PEX,max=452,580954 fF` em
`ss/1,62 V/125 °C`, Q=1, BL. O teto corrente é `1,15 × C_BL,PEX = 520,468097 fF`.

Resultado da matriz integrada em 06/10/2026: leitura `60/60 PASS`; escrita
`56/60 PASS`, `4/60 FAIL`. As falhas ocorrem em `sf` e `ss`, 1,62 V/−40 °C,
nos dois sentidos: o flip completa, mas BL/BLB ficam abaixo de `VDD−0,1 V` ao
fim da janela de recuperação de 4 ns. A repetição focal com 30 ns passou
`4/4`; o cruzamento medido foi `4,031–4,186 ns`, confirmando recuperação tardia.
G7 segue aberto porque esse tempo excede a janela de 4 ns. O diagnóstico focal
de 5 ns concluiu `4/4 PASS`, com os mesmos cruzamentos entre `4,03137` e
`4,18573 ns`. Ele confirma recuperação após o limite, sem alterar o critério
original nem promover os casos a PASS do gate.

### Evidência histórica de leaf PEX e surrogate

Antes da coluna física existir, o G7 usou os máximos de leaf PEX abaixo para
construir um surrogate conservador. Esses números continuam úteis como
histórico, mas não substituem mais a extração da coluna completa.

Os sweeps de pequena-sinal em `1 MHz` fecharam:

| Parcela leaf PEX | Máximo observado por bitline |
|---|---:|
| bitcell 6T, WL desabilitada | `8,592457 fF/célula` |
| precharge desligado | `6,525894 fF` |
| write driver com `WE=0` | `26,721160 fF` |
| entrada do sense | `28,101193 fF` |

O **surrogate conservador** usado nessa etapa combinava o bound pré-layout de
fio `1,061862 fF/célula` com os máximos leaf PEX:

```text
C_BL,surrogate(32)
  = 32 × (8,592457 + 1,061862)
    + 6,525894 + 26,721160 + 28,101193
  ≈ 370,286455 fF

1,15 × C_BL,surrogate ≈ 425,829423 fF
```

Os valores de stress usam o termo de fio antes do arredondamento exibido na
tabela pré-layout. Esse `425,829423 fF` é somente histórico; o teto atual é
`520,468097 fF`. No canto `ss/1,62 V/125 °C`, o sense físico 1,5× passa ambos
os estados com `t_res=0,22060/0,23257 ns`, e a escrita física passa ambos os
sentidos, com recuperação de bitline dentro do limite. A matriz completa
encontrou quatro falhas de recuperação em `sf/ss`, 1,62 V/−40 °C; a repetição
focal confirmou cruzamento entre `4,031–4,186 ns`, fora da janela original de
4 ns. G7 permanece aberto até fechar a recuperação dentro do contrato vigente.
