# Avaliação pré-layout de C_BL

**Revisão física de 08/10/2026:** a coluna G7 reparada passou DRC completo,
LVS único e nova PEX. A caracterização em PVT deu
`C_BL,PEX,max=519,179340 fF` (`120/120`), mas essa primeira rodada inicializou
o estado da bitcell em taps resistivos do lado de acesso. O valor e o teto
`597,056241 fF` são diagnósticos, inválidos para sign-off, e precisam ser
refeitos usando os nós de saída das latches (`.t0`). O G7/Fase 1 seguem abertos.
O status de 07/10 abaixo preserva a revisão anterior. A medição vigente para
aceite depende da PVT corrigida, com `1,15 × C_BL,PEX,max`, seguida por matrizes
integradas de leitura/escrita com as cargas recalculadas.

## Registro histórico de 07/10/2026 — supersedido

Na revisão de 07/10, G6 e G7 haviam sido considerados concluídos. Os valores e
as matrizes daquele registro foram supersedidos pela requalificação de 08/10
descrita no início deste documento.
As cinco leaf cells já possuem layout com Magic DRC `0` e Netgen LVS único.
Os valores deste documento continuam sendo o orçamento histórico usado para o
schematic freeze e para os screenings de 65 fF; eles **não** são PEX. A coluna
física 32× já fornece agora o valor pós-layout real usado pelo G7.

As capacitâncias de terminal da bitcell, precharge e entrada do sense
amplifier foram caracterizadas com o modelo SKY130A em PVT. A entrada do novo
`cells/sense_amp.sch` é maior que a da topologia anterior; o orçamento antigo
de `49,696512 fF` não é mais válido. `Cwire_cell` foi uma hipótese física
pré-layout. A extração parasitária já substituiu esse orçamento como referência
do G7: a coluna física final mede `C_BL,PEX,max=453,588405 fF`, com teto
`521,626665 fF`. Os bounds e screenings abaixo permanecem históricos e não
devem ser confundidos com esses valores medidos de PEX.

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

## Evidência por parcela e limites do orçamento pré-layout

| Parcela | Evidência no checkout | Estado e dado necessário |
|---|---|---|
| `Nrows` | `specs/technical_specification.md` define 4/8/16/32 linhas; `memory/memory-ip/run_state.md` registra uma palavra por linha física. | Resolvido para as quatro configurações. |
| Terminal da célula | `sims/cbl_device_capacitance_pvt.csv`, `270/270 PASS`. | Fechado em `0,452619 fF/célula` como máximo do sweep esquemático PVT. O G7 também requalificou a coluna completa com PEX; esse valor permanece contribuição standalone, não substitui o CBL extraído. |
| `Cwire_cell` | Corner máximo do extractor Magic + constraint `metal2`, `0,14 µm`, `<=5,0 µm/linha`, dois vizinhos e +20%. | Orçamento pré-layout `<=1,061862 fF/célula`; geometria e capacitâncias distribuídas da coluna foram incluídas no PEX final de G7. O total físico medido é a referência corrente. |
| `Cprecharge` | Netlist corrigido de `cells/precharge.sch` e sweep PVT de pequena-sinal. | `0,908533 fF` é o máximo esquemático histórico. A variante física `Wpre=2,52 µm` passou DRC/LVS/PEX, Ceff PVT `60/60` e a qualificação integrada G7. |
| `Cwrite` | `sims/write_driver_capacitance_pvt.csv`, `120/120 PASS`, usando o netlist extraído de `cells/write_driver.sch` com `WE=0`, ambos os dados e BL/BLB. | Máximo observado `4,033129 fF` por bitline; deve permanecer no orçamento enquanto o write driver estiver conectado diretamente à coluna. |
| `Csense` | `sims/sense_input_capacitance_pvt.csv`, `60/60 PASS`, usando o netlist do `cells/sense_amp.sch`. | `9,004605 fF` é a medição AC standalone com BL/BLB pré-carregadas. A variante física 1,5× foi requalificada em leitura integrada com PEX `60/60`; isso não representa análise estatística completa de ruído/yield. |
| `Cmux` | Arquitetura de uma palavra por linha e sem mux de coluna na especificação atual. | `0 fF` enquanto a arquitetura não mudar. |

## Screening não usado como bound — referência histórica de 07/10

`50 fF` e `60 fF` permanecem apenas como resultados históricos de screening.
O screening de `65 fF` para 32 linhas também é histórico. A referência de
07/10 era a coluna física extraída e a requalificação feita no teto de
`521,626665 fF` ou acima dele; em 08/10 esse valor foi supersedido e o novo
teto deve ser calculado com inicialização válida em `.t0`. As parcelas do modelo lumped pré-layout ajudam
na interpretação, mas não substituem o total RC medido.

## Transição para o G7 pós-layout — resultados históricos de 07/10

O screening pré-layout em `65 fF` e o bound `62,409659 fF` ficam preservados
como baseline de engenharia que sustentou o freeze. A coluna física original
`layout/column_32_full` mediu `422,651867 fF`, com teto `486,049647 fF`; esses
valores foram substituídos após o reforço dos periféricos. A coluna
`layout/column_32_full_g7_wpre2p52_final`, integrada com sense 1,5×, precharge
`W=2,52 µm` e write `Wout=5,04 µm`, passou DRC hierárquico/flat, LVS único e
PEX. Sua varredura PVT passou `120/120`, com `C_BL,PEX,max=453,588404713 fF`
em `ss/1,62 V/125 °C`, Q=1, BL. O teto usado em 07/10 era
`1,15 × C_BL,PEX = 521,626665420 fF`.

As matrizes integradas pós-layout passaram `60/60` em leitura e `60/60` em
escrita. O pior `t_res` de leitura foi `0,23209 ns`; o read-disturb máximo foi
`0,1796454 V`. A escrita recuperou BL/BLB em até `3,49470 ns`, dentro da janela
de 4 ns. A qualificação de escrita aplicou carga equivalente entre
`525,653715` e `527,110428 fF`, acima do teto oficial; a de leitura, entre
`521,626665` e `523,083379 fF`. Ambas incluem PEX explícito e hash de cada
netlist no CSV. O critério de 4 ns foi preservado.

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
tabela pré-layout. Esse `425,829423 fF` é somente histórico; as extrações
posteriores `486,049647 fF` e `520,468097 fF` também foram substituídas pela
coluna final, cujo teto é `521,626665 fF`. Na matriz final, o sense passou os
dois estados no pior canto medido com `t_res,max=0,23209 ns`; leitura e escrita
passaram `60/60`. A recuperação máxima da escrita foi `3,49470 ns`, dentro de
4 ns. Os resultados anteriores de `56/60` e dos diagnósticos de 30/5 ns são
históricos e foram supersedidos pela requalificação final.
