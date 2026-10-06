# Estado importado: wordline driver e write driver

## Procedência e alcance

Os esquemáticos, netlists, layouts, decks de extração, scripts de caracterização
e CSVs aqui referenciados foram comparados com a branch de Danilo
`feat/sram-6t-cell`, commit `8c16199`. Os esquemáticos, netlists e árvores Magic
já estavam no diretório de trabalho e coincidem byte a byte com essa fonte. Os
roteiros e resultados listados foram incorporados agora e tiveram apenas os
caminhos de arquivo adaptados à organização atual.

Os números abaixo são resultados registrados por Danilo. Nenhuma simulação,
DRC ou LVS foi reexecutada nesta incorporação. O checkout contém arquivos de
layout e PEX, mas não os logs DRC/LVS citados no relatório de fechamento.

O escopo deste resumo é `wl_driver` e `write_driver`. A bitcell e o decoder
dinâmico não foram alterados. O relatório histórico
[`relatorio_validacao_bitcell_6t_sky130.md`](relatorio_validacao_bitcell_6t_sky130.md)
continua preservado como registro da etapa anterior; as afirmações antigas
sobre os drivers devem ser lidas como históricas.

## Wordline driver

O esquemático atual, [`cells/wordline_driver/wl_driver.sch`](../cells/wordline_driver/wl_driver.sch),
tem dois inversores CMOS em cascata, portanto preserva a polaridade entre
`WL_IN` e `WL`. O primeiro estágio usa `W=0,42 µm`, o segundo `W=0,84 µm`, e
ambos usam `L=0,15 µm`. O netlist correspondente está em
[`cells/wordline_driver/wl_driver.spice`](../cells/wordline_driver/wl_driver.spice).

O smoke histórico do driver reporta operação em `tt/1,8 V/27 °C` e
`ss/1,62 V/−40 °C`. No ponto `ss/1,62 V/−40 °C`, com carga de stress de
`50 fF`, o CSV registra `WL_HIGH=1,57306 V`, `WL_LOW=0,00055377 V` e atraso
entre cruzamentos de 50% de `0,66536 ns`. Esse ponto de 50 fF é stress, não a
estimativa física da linha.

O orçamento pré-layout importado calcula `CWL,row,max=17,39783 fF` para uma
linha de oito bits e usa `17 fF` adicionais no bench integrado, pois os dois
gates da célula selecionada já estão explícitos no circuito. A derivação e os
limites estão em [`cwl_pre_layout_estimate.md`](cwl_pre_layout_estimate.md).
São valores de screening pré-layout; a carga extraída da linha integrada
continua pendente.

## Write driver

O esquemático atual,
[`cells/write_driver/write_driver.sch`](../cells/write_driver/write_driver.sch),
é um driver diferencial tri-state de dez MOSFETs. `WE` habilita os dois ramos;
com `WE=0`, os caminhos de pull-up e pull-down ficam desligados. Com `WE=1`,
`BL=DATA` e `BLB=DATA_B`, assumindo entradas complementares. O netlist está em
[`cells/write_driver/write_driver.spice`](../cells/write_driver/write_driver.spice).

O screening integrado registrado usa a bitcell com `WPD=1,26 µm`, o driver
transistor-level e `65 fF` por bitline. O arquivo
[`sims/bitcell_write_driver_65ff_pvt.csv`](../sims/bitcell_write_driver_65ff_pvt.csv)
contém `60/60` mudanças de estado bem-sucedidas nos casos testados; o rerun
de `10 ps` no canto selecionado também registra os dois estados como
sucedidos. O screening G4 de mismatch registra `20/20` casos de escrita PASS
no arquivo [`sims/g4_write_ss_sf_1p62_m40_n5.csv`](../sims/g4_write_ss_sf_1p62_m40_n5.csv).
Esses resultados são triagem elétrica registrada, não sign-off pós-layout.

### Carga do write driver

O sweep de capacitância desligada, usando o netlist Xschem e `WE=0`, registra
`120/120 PASS` e máximo de `4,03313 fF` por bitline no CSV
[`sims/write_driver_capacitance_pvt.csv`](../sims/write_driver_capacitance_pvt.csv).
O orçamento pré-layout de `C_BL` usa esse valor. O relatório de fechamento de
Danilo também registra um máximo de `26,72116 fF` no leaf PEX do driver; esse
valor é uma medição pós-extração reportada e deve ser confirmado no rerun local
do sweep com `--pex` antes de ser usado como resultado reproduzido nesta branch.

## Layout, extração e verificação física

Cada diretório contém layouts roteados e achatados, scripts Magic, netlists de
comparação, extração `.ext` e netlists PEX:

- [`layout/wl_driver`](../layout/wl_driver)
- [`layout/write_driver`](../layout/write_driver)

O fechamento G6 de Danilo reporta Magic DRC `0` e Netgen `Circuits match
uniquely` para ambos. Para `wl_driver`, o LVS reportado corresponde a 4
dispositivos e 5 nets; para `write_driver`, 10 dispositivos e 12 nets. Como os
logs não vieram junto dos artefatos locais, este estado é **reportado**, não
verificado novamente neste checkout. A requalificação elétrica com parasitas
PEX permanece pendente.

## Roteiros e resultados disponíveis

| Uso | Roteiro/resultado |
|---|---|
| Smoke PVT isolado do `wl_driver` | [`run_leaf_peripheral_smoke.py`](../sims/run_leaf_peripheral_smoke.py); agora aceita `--blocks wl_driver` e usa `17,4 fF` como estimativa de linha e `50 fF` como stress. |
| Capacitância dos gates de acesso para carga da WL | [`run_wordline_capacitance.py`](../sims/run_wordline_capacitance.py) e [`wordline_access_gate_capacitance_pvt.csv`](../sims/wordline_access_gate_capacitance_pvt.csv), `120/120 PASS` reportados. |
| Capacitância desligada do write driver | [`run_write_driver_capacitance.py`](../sims/run_write_driver_capacitance.py), [`write_driver_capacitance_pvt.csv`](../sims/write_driver_capacitance_pvt.csv); inclui suporte a `--pex`. |
| Transição da bitcell com driver de escrita | [`run_bitcell_write_driver_smoke.py`](../sims/run_bitcell_write_driver_smoke.py) e CSVs `bitcell_write_driver_*.csv`; é um deck transistor-level de screening. |
| Limite de tensão de WL para escrita | [`run_bitcell_write_margin.py`](../sims/run_bitcell_write_margin.py) e [`bitcell_write_margin_wlvm.csv`](../sims/bitcell_write_margin_wlvm.csv); usa bitlines ideais e não modela o driver. |
| Leitura integrada com o driver real de WL | [`run_integrated_column_read.py`](../sims/run_integrated_column_read.py), `integrated_column_read_*.csv` e `postfreeze_integrated_read_*.csv`. |
| Escrita integrada com os drivers reais de WL e bitline | [`run_integrated_column_write.py`](../sims/run_integrated_column_write.py), `integrated_column_write_*.csv` e `postfreeze_integrated_write_*.csv`. |
| Harness G1/G4 de regressão e mismatch | [`run_g1_revalidation.py`](../sims/run_g1_revalidation.py), [`summarize_g1_revalidation.py`](../sims/summarize_g1_revalidation.py) e [`run_g4_dynamic_mismatch.py`](../sims/run_g4_dynamic_mismatch.py). |

Os CSVs integrados importados registram `60/60 PASS` para leitura e `60/60
PASS` para escrita no screening de `65 fF`. A regressão de leitura G4 registra
`36/36 PASS` nos quatro arquivos `g4_read_*.csv`; a de escrita registra
`20/20 PASS` em `g4_write_ss_sf_1p62_m40_n5.csv`. Os dois arquivos
`g4_seed_repro_a.csv` e `g4_seed_repro_b.csv` registram a mesma falha antiga:
o setup medido foi `3,66 ps`, abaixo do limite de `25 ps`, embora ngspice tenha
retornado código zero. O rerun posterior `g4_sclk2p84_seed7007.csv` registra
`50,02 ps` de setup e PASS. Mantive os CSVs antigos para que a evolução do
critério continue rastreável.

Os runners integrados geram decks transitórios e incluem a extração dos leafs
por Xschem. Os caminhos de esquemático foram ajustados às pastas atuais. A
opção integrada `--pex` ainda depende também dos PEX de bitcell e pré-carga;
esses PEX não estão presentes nesta árvore local. Os testes PEX isolados do
`wl_driver` e do `write_driver` têm artefatos disponíveis.

## Próximos passos recomendados

1. Abrir e conferir no Xschem os dois esquemáticos e seus netlists, verificando
   nomes e ordem dos pinos. O `write_driver.sch` contém um smoke de bancada
   próprio com `50 fF`; trate-o como caso de stress.
2. Começar pelo `wl_driver`: rodar o smoke em TT para `17,4 fF` e `50 fF`, e
   comparar `WL_HIGH`, `WL_LOW` e atraso. Depois ampliar para SS e FF e, em
   seguida, aos extremos de tensão e temperatura usados no sweep.
3. Repetir o smoke da wordline com `--pex`. Comparar a resposta extraída com a
   estimativa lumped de `17,4 fF`; a medição de um leaf não representa ainda a
   interconexão completa da linha física.
4. Conferir se o nível alto e o tempo útil de WL atendem leitura e escrita na
   integração; o ponto de partida disponível é o runner integrado de leitura.
   O decoder dinâmico pode permanecer fora do bench: essa etapa valida a carga
   vista a partir de `WL_IN`.
5. Validar o `write_driver` com `WE=1` para os dois valores de `DATA`, e com
   `WE=0` confirmando que BL/BLB ficam isoladas. Em seguida medir a
   capacitância desligada com o schematic e com `--pex`.
6. Rodar a integração de escrita em `65 fF` por bitline, começando por TT e
   pelos casos críticos SS/FF, verificando escrita dos dois estados, janela de
   WL e recuperação das bitlines. Expandir ao conjunto PVT só depois desses
   casos estarem entendidos.
7. Quando os PEX de bitcell e pré-carga estiverem disponíveis, habilitar
   `--pex` nos runners integrados e requalificar leitura e escrita. O passo
   final requer a coluna física e sua carga extraída; os CSVs atuais usam
   capacitores lumped pré-layout.
