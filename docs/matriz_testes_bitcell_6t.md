# Matriz de testes e decisões — bitcell SRAM 6T SKY130A

> **Estado corrente em 08/10/2026: `CLOSED_ENGINEERING_QUALIFICATION`.** As cinco
> leafs, a coluna física 32×, a linha WL de 8 bits e a coluna G7 têm DRC/LVS/PEX
> requalificados. As PVTs usam os nós de latch `.t0`; `C_BL,PEX,max=519,179340 fF`,
> o limite integrado é `597,056241 fF` e `CWL_EXTRA=93,351918 fF`. Leitura passou
> `60/60` (ΔBL min `0,334350 V`, setup min `804,60 ps`, `t_res` max `0,246350 ns`,
> disturb max `0,196491 V`); escrita passou `60/60` (recuperação max `3,978840 ns`,
> margem WL30 min `79,696 ps`). Casos críticos refinados com passo de 1 ps também
> passaram. A Fase 1 cobre a bitcell e suas leafs físicas. O decoder 2→4 foi
> atualizado para dinâmico e há um candidato SPICE; sua simulação/qualificação
> e a macro 4×8 permanecem na Fase 2. As matrizes e conclusões de 07/10 abaixo
> são históricas.

| Gate corrente | Evidência | Estado |
|---|---|---|
| G1–G4 / schematic freeze | Screening pré-layout de engenharia preservado | **Fechado** |
| G6 / G7 físico | Cinco leafs, abutment normal/espelhado, coluna 32× e linha 8-bit WL; DRC completo `0`, LVS único, PEX | **Fechado** |
| Conferência manual de DRC/LVS — 08/10 | Bitcell: `Total DRC errors found: 0` na console gráfica; coluna G7 hierárquica/flat: `0/0` no Magic; Netgen com setup SKY130A: `Circuits match uniquely`, `212` MOS e `82` redes por circuito | **Corroborada manualmente**; setup SKY130A lido e match estrutural repetido. Avisos persistentes de MOS *placeholders* e propriedades ausentes impedem afirmar validação completa dos dispositivos; log manual local ignorado pelo Git |
| PVT de capacitância | Bitcell 120/120; precharge 60/60; coluna 120/120; WL row/cell 60/60 cada; sense 360/360; write driver 120/120 | **Fechado**, hashes PEX conferidos |
| Leitura G7 | CSV 60 condições e refinamento crítico de 1 ps | **60/60 PASS** |
| Escrita G7 | Residual CBL por PVT/estado/dado e lado; WL_IN 3,40 ns | **60/60 PASS** |
| Decoder dinâmico / macro 4×8 | Candidato transistor-level em `cells/row_decoder_2to4.spice`; ainda sem evidência elétrica/física | **Fase 2**, qualificação e integração pendentes |

Os smokes e PVTs que inicializaram pelos taps resistivos permanecem inválidos
para aceite e estão preservados como históricos. Yield de produção, ruído
estatístico completo, DC-SNM-PVT e teto de potência macro permanecem fora do
escopo da Fase 1.

A conferência manual, os comandos reproduzíveis e a ressalva sobre os
*placeholders* MOS no Netgen estão em
[`validacao_manual_drc_lvs_sky130a.md`](validacao_manual_drc_lvs_sky130a.md).

> **Registro histórico de 07/10/2026 — supersedido:** parte dos registros abaixo descreve a matriz
> histórica que usava 50 fF e o sense amplifier anterior. O contrato técnico
> corrente usa qualificação contínua em `1,62–1,80 V`, mantém `1,95 V` somente
> como auditoria/limite estático do modelo e não qualifica `1,98 V` com os
> modelos `01v8` atuais. O orçamento de coluna foi recalculado com o sense
> atual e com a capacitância de saída do write driver desligado; o teto
> pré-layout de 32 linhas é `62,409659 fF`. O ponto conservador de revalidação
> elétrica é `65 fF`. O schematic freeze e o G6 físico estão concluídos: as
> cinco leaf cells têm layout, Magic DRC `0` e Netgen LVS com
> `Circuits match uniquely`; a bitcell também passou abutment em gap zero nas
> orientações normal e espelhada horizontalmente. No G7, a coluna física 32×
> revisada também passou Magic DRC `0`, Netgen LVS único e extração RC.
> `C_BL,PEX,max=453,588405 fF`, definindo teto de requalificação de
> `521,626665 fF`. As matrizes integradas pós-layout passaram `60/60` em leitura
> e `60/60` em escrita; recuperação máxima da escrita `3,49470 ns` dentro da
> janela de 4 ns. G7 está fechado no escopo de engenharia. A seção 6 mantém as
> extrações e resultados anteriores como histórico.
> A definição atual das leaf
> cells, as simulações selecionadas e os limites de escopo estão em
> [`phase1_leaf_cell_closure.md`](phase1_leaf_cell_closure.md). Use-a como
> estado corrente; os valores anteriores permanecem evidência histórica.

**Data do levantamento:** 07/10/2026
**Escopo:** testes elétricos pré-layout, falhas de bancada/netlist registradas e estado das verificações físicas.
**Registro geral de 07/10/2026 — supersedido:** naquela revisão, Schematic Freeze, G6 físico e G7 pós-layout foram considerados concluídos. O estado atual está no aviso de 08/10 no início deste documento.

## 1. Ambiente e convenções

Os testes registrados foram executados no container `isaiassh/unic-cass-tools:1.1.0`, com `PDK=sky130A`, `PDK_ROOT=/opt/pdks`, biblioteca contínua `/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice` e ngspice 44.2. Os dados e scripts citados estão em `sims/`.

Os cantos de processo são `tt`, `ff`, `ss`, `fs` e `sf`. O sizing canônico congelado no esquemático é `WPU/WPD/WACC = 0,42/1,26/0,60 µm`, `L=0,15 µm`, `nf=1`. `WPD=0,84 µm` permanece baseline histórica e `WPD=1,05 µm` variante exploratória.

Neste documento, **PASS** quer dizer que o caso cumpriu o teste e o limite específico usado pelo script; não implica automaticamente aprovação de arquitetura, confiabilidade ou fabricação. **MARGIN_FAIL** indica que o limite interno provisório não foi atendido, ainda que a célula não tenha invertido o estado.

### 1.1 Resumo consolidado das conquistas

| Conquista / decisão | Valor usado ou medido | Motivo do uso | Teste / evidência | Situação registrada em 07/10 (histórica) |
|---|---|---|---|---|
| Baseline histórica | `WPU/WPD/WACC=0,42/0,84/0,60 µm`, `L=0,15 µm` | Referência para comparar variantes. | Read-disturb nominal `12/40 PASS`; Read SNM nominal `0,348804 V`. | **Não atende** os gates de leitura e não é mais o sizing canônico. |
| Sizing canônico congelado | `WPU/WPD/WACC=0,42/1,26/0,60 µm`, β=`2,10` | Aumentar o pull-down reduz a elevação do nó baixo durante leitura e foi o único candidato que passou a meta nominal de Read SNM. | G1 `60/60` read + `60/60` write em 65 fF; G2 `60/60`; G3 `60/60`; G4 read/write mismatch fechado como screening. Regressão pós-aplicação: Read SNM `0,414349 V`, read-disturb crítico `0,1781393 V`. | **Aplicado e congelado** no `bitcell_6t.sch/.sym`; G6 e G7 pós-layout concluídos no escopo de engenharia. |
| Fechamento físico G6 | cinco leafs: `bitcell_6t`, `sense_amp`, `precharge`, `wl_driver`, `write_driver` | Confirmar que a revisão congelada possui implementação física consistente antes da extração parasitária. | Magic flat DRC `0` e Netgen LVS `Circuits match uniquely` nas cinco leafs; bitcell com abutment gap zero normal e espelhado horizontalmente, ambos DRC `0`. | **G6 fechado em 05/10/2026**; seguido pelo G7 pós-layout, também fechado em 07/10/2026. |
| Write driver corrigido | Schematic freeze e variante física reforçada `Wout=5,04 µm`; `WE_B` interno; saída diferencial tri-state | Remover o curto `DATA_B–BLB` e garantir isolamento das bitlines quando `WE=0`. | Netlist Xschem PASS; smoke standalone complementar; variante física com DRC/LVS/PEX e matriz integrada pós-layout `60/60 PASS`. | Carga final qualificada em G7; os smoke tests de 50 fF permanecem apenas como evidência histórica de conectividade/funcionalidade. |
| Escrita integrada com driver real demonstrada | `1,8 V`, `tt/ss/ff`, 27 °C, 50 fF, ambos os sentidos, WPD `0,84/1,26 µm` | Verificar que o driver corrigido realmente troca a bitcell e não apenas bitlines isoladas. | `12/12` trocas; cruzamento de `Q=VDD/2` entre `0,148–0,212 ns`. | PASS de triagem funcional histórica; a margem de escrita foi posteriormente qualificada em G7 com PEX, `60/60` e carga acima do teto. |
| Limite inferior provisório de WL obtido | regra `1,30×` o pior flip completo `90/10%` | Garantir tempo para a escrita completar no pior caso medido com 30% de margem de engenharia. | G1 65 fF completo: pior screening `full_flip=0,3194 ns` (`WL_min=0,41522 ns`) em `ss/1,62 V/-40 °C`; rerun de 10 ps em ambos os sentidos: `0,3192 ns` e `WL_min=0,41496 ns`. G7 usou WL física/PEX com entrada de 1 ns e mediu a largura efetiva. | Valores G1 são baseline pré-layout. Em G7 a largura efetiva foi `1,00475–1,04705 ns`; limite mínimo calculado máximo `0,871819 ns`; todas as escritas passaram e a margem mínima antes da queda foi `0,34274 ns`. |
| Organização da coluna explicitada | uma palavra por linha física; `Nrows=4/8/16/32`; `Cmux=0` | A profundidade da macro define quantas células carregam cada BL/BLB; a arquitetura atual não usa mux de coluna. | Parcela de dreno pela aproximação de `0,2 fF/célula`: `0,8/1,6/3,2/6,4 fF`. | Base do orçamento pré-layout; as parcelas de célula, fio, precharge e sense já estão consolidadas em `docs/cbl_pre_layout_estimate.md`. |
| Regra de carga da bitline formalizada | baseline pré-layout `62,409659 fF`; coluna G7 final `C_BL,PEX,max=453,588404713 fF`; teto G7 `521,626665420 fF` | Separar a carga física medida do screening e estabelecer o bound de requalificação em 1,15× do maior C_BL,PEX. | Pós-layout final: `sims/column_32_full_g7_wpre2p52_final_pex_capacitance_codex_20261007.csv`, `120/120 PASS`. | Baseline pré-layout preservada como histórico; PEX final da coluna e teto de requalificação concluídos. |
| Sense amplifier atual | latch regenerativo diferencial de sete transistores; dispositivos PMOS de amostragem `W=2,0 µm`; variante física G7 1,5× | Registrar a topologia do schematic freeze e a variante física usada na qualificação pós-layout. | Screening G2/G4 registrado nas linhas históricas; variante 1,5× com DRC/LVS/PEX e matriz integrada de leitura `60/60 PASS`, `t_res,max=0,23209 ns`. | G7 de leitura fechado para os critérios de engenharia; ruído estatístico completo/yield não reivindicados. |
| Contrato de tensão | nominal `1,80 V`; qualificação contínua `1,62–1,80 V`; auditoria em `1,95 V` | Manter a qualificação dentro da estratégia válida dos dispositivos/modelos `01v8`. | Em `1,95 V`, `30/30` condições tiveram pelo menos um terminal acima de 1,95 V; pior `2,056858 V`. | `1,95 V` é somente auditoria/limite estático; `1,98 V` não é qualificável com os modelos `01v8` atuais. |
| Mismatch de SNM iniciado | `N=200`, seeds `1001–1200`, `.lib sf_mm` | Medir dispersão por mismatch local sem confundir com variação global de processo. | Read: `269,936/300,933/11,038/330,733 mV`; Hold: `541,229/569,536/10,442/600,905 mV` (`min/média/σ_pop/máx`). | Evidência estatística exploratória. Yield de produção e mismatch estatístico completo de escrita/read-disturb não foram reivindicados e estão fora do escopo G7/Fase 1. |
| Fuga estática quantificada | na faixa qualificada `1,62–1,80 V`, pior soma das fontes `20,0676 nA/célula`; potência da fonte VDD `36,1079 nW/célula` | Criar uma referência de leakage antes de definir orçamento da macro e periféricos. | `60/60` estados estáveis em 1,62/1,80 V; pior ponto `fs/1,80 V/125 °C`. Uma macro 32×8 teria referência **bitcell-only** de ~`9,244 µW` de potência VDD se todas as 256 células fossem aproximadas por esse pior caso. | Referência medida, não orçamento de aceite; exclui periféricos. O antigo máximo `21,759 nA` em 1,95 V permanece apenas como auditoria fora da faixa qualificada. |

## 2. Por que estes valores foram usados

Os rótulos abaixo distinguem **especificação/arquitetura**, **recomendação de engenharia**, **gate provisório** e **hipótese de screening**. Os números marcados como recomendação não são apresentados como limites universais extraídos da literatura.

| Parâmetro | Valores usados | Natureza do valor | Justificativa e limite da escolha |
|---|---|---|---|
| Alimentação nominal | 1,80 V | Especificação do projeto / nominal do domínio `01v8` | Ponto nominal usado para comparação de sizing e para o gate de Read SNM. |
| Faixa de qualificação contínua | 1,62–1,80 V | **Contrato técnico corrente** | É a faixa de qualificação elétrica adotada com a estratégia atual de dispositivos/modelos `01v8`. |
| Auditoria de limite do modelo | 1,95 V | **Auditoria, não ponto qualificado** | Mantido para verificar stress/limite estático; apresentou excedências transitórias. `1,98 V` fica fora da qualificação com o model set atual. |
| Temperatura | −40 / 27 / 125 °C | Cobertura PVT de projeto | Extremos escolhidos para cobrir frio/quente e 27 °C como referência nominal. A cobertura em simulação não certifica, por si só, a validade dos modelos em toda a faixa. |
| Cantos | `tt/ff/ss/fs/sf` | Cobertura do model set | Incluem os cinco cantos de processo presentes na biblioteca SKY130 usada. |
| Carga de bitline | baseline `62,409659 fF`/screening `65 fF`; pós-layout final `C_BL,PEX,max=453,588405 fF`; teto `521,626665 fF` | Baseline histórica + **medição PEX** | A coluna final passou `120/120` casos PVT e substitui as extrações anteriores como referência de G7. |
| Estados armazenados | Q=1/QB=0 e Q=0/QB=1 | Cobertura funcional | Verificam as duas polaridades, inclusive a assimetria entre BL e BLB e os dois sentidos de escrita. |
| Excursão do nó baixo em leitura | ≤0,20 V | **Gate provisório** | Limite interno da especificação/testbench para expor read-disturb. Não é um limite universal do SKY130 nem um critério formal aprovado por arquitetura. |
| Diferencial de bitline | ≥200 mV antes da amostragem; piso efetivo de mismatch =150 mV | **Meta provisória de G2** | `100 mV` falhou `20/500`; no sweep 110–150 mV, `140 mV` ainda teve 1/500 falha e `150 mV` passou 500/500. Somado ao sweep anterior, `150 mV` acumula `800/800`; o alvo integrado sobe para `200 mV`, deixando `50 mV` de guarda pré-layout. Não é claim de yield de produção. |
| Read SNM nominal | ≥0,40 V em `tt`, 1,8 V | **Recomendação de engenharia** | Gate nominal para comparar os sizings testados; não é apresentado como limite universal da literatura nem como critério PVT/yield. |
| Janela inferior de WL | `1,30 ×` pior tempo de flip completo | **Recomendação de engenharia** | Flip completo exige Q/QB em 90%/10% de VDD. Com o pior caso medido de `0,3216 ns`, resulta em `0,4181 ns` provisórios; o valor deve ser revalidado após a carga física ser conhecida. |
| Janela superior de WL | sem limite universal independente congelado | Limite dependente do circuito integrado, carga PEX, read-disturb e timing do sense | A WL física representativa de 8 bits foi extraída e usada nos benches finais; leitura e escrita passaram `60/60`, com read-disturb máximo `0,1796454 V` e slew medido. Não se cria um critério separado de “dynamic SNM”. |
| Sizing exploratório | WPU=0,42; WPD=0,84/1,05/1,26; WACC=0,60 µm | Exploração de projeto | Mantém pull-up e acesso constantes e aumenta o pull-down para reduzir read-disturb. Isso muda β de 1,40 para 1,75 e 2,10; o efeito sobre escrita também precisa ser avaliado. |
| Amostragem mismatch | N=200; seeds 1001–1200 | Triagem estatística | Permite repetição determinística e cobre dois pontos críticos selecionados. Não representa um sweep estatístico de toda a matriz nem define yield. |

## 3. Resultados elétricos

### 3.1 Smoke test e bancada de leitura

| Teste | Condições/valores | Resultado | O que prova (e o que não prova) | Evidência |
|---|---|---|---|---|
| Smoke test manual de retenção/escrita | `tt`, 1,8 V, estímulos ideais; sizing provisório uniforme de 0,42 µm | Retenção de Q=1/QB=0 e escrita para Q=0/QB=1 observadas | Confirma execução e operação funcional básica. As bitlines ideais não permitem medir diferencial real de leitura ou margens. | [`tb_bitcell_6t.spice`](../sims/tb_bitcell_6t.spice); detalhes em [`relatório de validação`](relatorio_validacao_bitcell_6t_sky130.md) §5.1 |
| Leitura manual inicial | `tt`, 1,8 V, 5 fF/bitline, sizing uniforme provisório 0,42 µm | Em 21 ns, BL≈1,83618 V, BLB≈0 V, Δ≈1,83618 V e Q mínimo≈1,7737 V | Demonstra descarga diferencial em uma bancada e sizing específicos. Não é sweep PVT nem resultado do sizing canônico atual. | [`tb_bitcell_6t_read.spice`](../sims/tb_bitcell_6t_read.spice) |
| Correção da sequência PRE/WL | Na primeira versão PRE era reativado junto com WL em 20 ns | Medição anterior de Δ≈1,084 mV em 29 ns e queda do nó de 0,8468 V descartadas | O estímulo não mantinha a pré-carga desligada durante a leitura; esses números não devem ser usados como resultado válido. O deck foi corrigido e a métrica de bitline passou a ser observada em 21 ns. | [`tb_bitcell_6t_read.spice`](../sims/tb_bitcell_6t_read.spice); relatório §5.2 |

### 3.2 Read disturb nominal e exploração de sizing

Condições comuns: `VDD=1,8 V`, temperatura nominal do ngspice (27 °C), cinco cantos, `CBL=CBLB=5/10/20/50 fF`, dois estados e pulso de WL de 10 ns. São 40 simulações por sizing. O gate automatizado inclui pré-carga, Δ de bitline, nível alto, pico do nó baixo e recuperação após WL.

| WPU/WPD/WACC (µm) | Read-disturb PASS | Maior pico do nó que armazena 0 | Resultado do gate provisório ≤0,20 V | Evidência |
|---|---:|---:|---|---|
| 0,42/0,84/0,60 (canônico) | 12/40; 28 `MARGIN_FAIL` | 0,230547 V (`ff`, 50 fF) | Reprovado | [`bitcell_read_sweep.csv`](../sims/bitcell_read_sweep.csv) |
| 0,42/1,05/0,60 (exploratório) | 40/40 | 0,185621 V (`ff`, 50 fF) | Aprovado nominalmente | [`bitcell_read_sweep_wpd1p05.csv`](../sims/bitcell_read_sweep_wpd1p05.csv) |
| 0,42/1,26/0,60 (exploratório) | 40/40 | 0,156793 V (`ff`, 50 fF) | Aprovado nominalmente | [`bitcell_read_sweep_wpd1p26.csv`](../sims/bitcell_read_sweep_wpd1p26.csv) |

Os 40 casos do sizing canônico mantiveram a lógica e passaram os outros gates do script (pré-carga, diferencial, nível alto e recuperação); os 28 casos falharam especificamente o limite provisório de pico do nó baixo. Nenhum desses 40 casos apresentou inversão lógica. Portanto, os 12/40 não significam que a célula falhou funcionalmente em 28 operações: significam margem insuficiente perante o limite de excursão escolhido.

### 3.3 Curva borboleta e SNM

O método varre em DC a VTC dos inversores e calcula o menor quadrado inscrito na curva borboleta, nos modos hold e read. SNM nominal: `VDD=1,8 V`, 27 °C, cinco cantos, `L=0,15 µm`, passo DC de 1 mV. Os valores abaixo são mínimos entre os cinco cantos.

| WPU/WPD/WACC (µm) | Hold SNM mínimo | Read SNM mínimo | Corner do mínimo | Interpretação |
|---|---:|---:|---|---|
| 0,42/0,84/0,60 | 646,567 mV | 288,342 mV | `sf` | Referência canônica; o gate nominal de 0,4 V foi adotado posteriormente. |
| 0,42/1,05/0,60 | 642,994 mV | 332,353 mV | `sf` | Leitura melhora relativamente ao canônico; variante não congelada. |
| 0,42/1,26/0,60 | 635,192 mV | 360,472 mV | `sf` | Read SNM melhora entre os sizings testados, enquanto Hold SNM cai um pouco; sem limite formal, isto é comparação, não aprovação. |

Dados: [`SNM canônico`](../sims/bitcell_snm_summary.csv), [`SNM WPD=1,05`](../sims/bitcell_snm_summary_wpd1p05.csv), [`SNM WPD=1,26`](../sims/bitcell_snm_summary_wpd1p26.csv) e curvas VTC correspondentes em `sims/bitcell_snm_curves*.csv`.

**Baseline histórica — WPD=0,84 µm:**

![Curva borboleta SNM — baseline histórica WPD=0,84 µm](assets/bitcell_6t_snm_butterfly.png)

**Variante exploratória — WPD=1,05 µm:**

![Curva borboleta SNM — variante WPD=1,05 µm](assets/bitcell_6t_snm_wpd1p05.png)

**Sizing canônico congelado — WPD=1,26 µm:**

![Curva borboleta SNM — sizing canônico WPD=1,26 µm](assets/bitcell_6t_snm_wpd1p26.png)

As duas primeiras figuras permanecem como comparação histórica. A terceira
corresponde ao sizing canônico congelado `0,42/1,26/0,60 µm`; os valores são
pré-layout. O G7 requalificou leitura e escrita dinâmica com PEX; essas curvas
DC não constituem uma campanha de SNM PVT pós-layout, fora do escopo desta fase.

Para o novo gate **nominal** de `Read SNM >= 0,40 V`, usa-se o ponto `tt/1,8 V/27 °C`, e não o mínimo entre corners: `WPD=0,84` resulta em `0,348804 V` (FAIL), `1,05` em `0,388060 V` (FAIL) e `1,26` em `0,414349 V` (PASS). Isso não transforma os resultados de `ff/sf` abaixo de 0,4 V em PASS de PVT; o critério aqui é explicitamente nominal.

### 3.4 Matriz PVT de leitura e SNM

Para cada sizing foram usados cinco cantos × três VDD × três temperaturas × dois estados = 90 casos de leitura, com 50 fF por bitline. SNM mede hold e read nos 45 pontos PVT, totalizando 90 resultados por sizing. 50 fF representa o extremo da carga testada na varredura nominal, e não uma extração do layout.

| WPD | Leitura PVT | Maior pico do nó baixo | Menor Hold SNM | Menor Read SNM | Situação |
|---:|---:|---:|---:|---:|---|
| 1,05 µm | 72/90 PASS | 0,230218 V (`ff`, 1,95 V, 125 °C) | 581,312 mV (`sf`, 1,62 V, −40 °C) | 289,261 mV (`sf`, 1,62 V, 125 °C) | Falha 18 casos no limite de pico provisório. |
| 1,26 µm | 90/90 PASS | 0,194778 V (`ff`, 1,95 V, 125 °C) | 577,761 mV (`sf`, 1,62 V, −40 °C) | 312,029 mV (`sf`, 1,62 V, 125 °C) | Passa o gate elétrico de read-disturb usado; margem de apenas 5,222 mV para 0,20 V e inclui pontos de 1,95 V reprovados na auditoria terminal abaixo. Não é sign-off PVT. |

Há agora uma meta de `Read SNM >=0,4 V` apenas no ponto nominal. Ainda não há
limite mínimo de Hold SNM, gate PVT de SNM ou critério estatístico/yield; por
isso os mínimos entre corners continuam comparativos e não escolhem o sizing
isoladamente.

Evidências: [`leitura PVT WPD=1,05`](../sims/bitcell_read_pvt_wpd1p05_50ff.csv), [`leitura PVT WPD=1,26`](../sims/bitcell_read_pvt_wpd1p26_50ff.csv), [`SNM PVT WPD=1,05`](../sims/bitcell_snm_pvt_wpd1p05.csv), [`SNM PVT WPD=1,26`](../sims/bitcell_snm_pvt_wpd1p26.csv).

### 3.5 Escrita: smoke full-swing e WLVM

| Teste | Valores usados | Resultado | Limitação / decisão | Evidência |
|---|---|---|---|---|
| Escrita full-swing nominal | 5 cantos × 3 sizings (`WPD=0,84/1,05/1,26`) × 2 sentidos = 30; BL/BLB ideais complementares; WL=1,8 V por 10 ns; amostra 5 ns após WL cair | 30/30 PASS | Demonstra chaveamento sob drive ideal, não write margin, resistência/corrente do driver nem tempo mínimo. | [`bitcell_write_smoke_sweep.csv`](../sims/bitcell_write_smoke_sweep.csv) |
| Escrita full-swing PVT | 5 cantos × 3 tensões × 3 temperaturas × 2 sentidos = 90; WPD=1,26 µm; fontes ideais | 90/90 PASS | PASS funcional não é margem de escrita real; os pontos a 1,95 V também precisam ser lidos à luz da auditoria de terminais. | [`bitcell_write_pvt_wpd1p26.csv`](../sims/bitcell_write_pvt_wpd1p26.csv) |
| WLVM nominal — screening ideal histórico | `VDD=1,8 V`, 5 cantos, 2 sentidos, WPD=0,84 e 1,05 µm; WL reduzido por busca binária em 7 iterações (~14 mV); pulso de 10 ns; bitlines ideais | 20 combinações registradas; pior WLVM=0,619 V para WPD=0,84 e 0,605 V para WPD=1,05, ambos em `fs` | Não define critério independente de WLVM e não inclui driver/carga reais; não foi usado como gate de freeze. A escrita integrada real foi qualificada em G7 com carga PEX, `60/60`. | [`bitcell_write_margin_wlvm.csv`](../sims/bitcell_write_margin_wlvm.csv) |
| Write driver — timing nominal | WPD=1,26 µm, 1,8 V, `tt/ss/ff`, 27 °C, ambos os sentidos, 50 fF | 6/6 PASS; pior flip completo 90/10% = 0,288 ns; +30% = 0,375 ns | Screening de timing, ainda com carga arbitrária. | [`bitcell_write_driver_timing_nominal.csv`](../sims/bitcell_write_driver_timing_nominal.csv) |
| Write driver — baixa tensão | WPD=1,26 µm, 1,62 V, 5 cantos × 3 temperaturas × 2 sentidos, 50 fF | 30/30 PASS; pior flip completo = 0,3216 ns em `ss/-40 °C`, 0→1; +30% = **0,4181 ns** | Define o limite inferior **provisório** de WL enquanto a carga final não vem do PEX. | [`bitcell_write_driver_timing_1p62.csv`](../sims/bitcell_write_driver_timing_1p62.csv) |

### 3.6 Fuga estática em hold

Condições: candidato exploratório WPD=1,26 µm; cinco cantos × 3 tensões × 3 temperaturas × dois estados = 90 simulações; `WL=0`, `BL=BLB=VDD`; medição média entre 80 e 100 ns. Os estados ficaram estáveis em 90/90 casos. O máximo histórico da soma das fontes foi **21,759 nA** em `fs`, 1,95 V, 125 °C, mas 1,95 V não pertence à faixa qualificada. Restringindo a `1,62–1,80 V`, os `60/60` casos permaneceram estáveis e o pior ponto foi `fs`, 1,80 V, 125 °C: **20,0676 nA/célula** de soma das fontes e **36,1079 nW/célula** medidos na fonte VDD. Escalar esse pior caso para 256 células dá ~**9,244 µW** de referência VDD bitcell-only para 32×8; isso não inclui periféricos nem constitui orçamento de aceite.

Evidência: [`bitcell_leakage_pvt_wpd1p26.csv`](../sims/bitcell_leakage_pvt_wpd1p26.csv).

### 3.7 Auditoria de sobretensão nos terminais MOS

Durante leitura pré-layout, foram medidos `|VGS|`, `|VGD|`, `|VDS|` e `|VBS|` nos seis MOS. A bancada usa bitlines de 50 fF e borda ideal de WL de 50 ps. O primeiro 1 ns foi excluído para não contar o salto de inicialização `.ic`/UIC. O valor de comparação de 1,95 V corresponde ao domínio usado pelos modelos `01v8`; esta auditoria é um alerta de compatibilidade do estímulo/modelo, não certificação de confiabilidade.

| VDD | Condições PVT/estado | Métricas terminal acima de 1,95 V | Maior módulo | Resultado |
|---:|---:|---:|---:|---|
| 1,62 V | 30 condições × 24 métricas=720 | 0/720 | 1,714736 V | Sem excedência nesta bancada. |
| 1,80 V | 30 condições × 24 métricas=720 | 0/720 | 1,901264 V | Sem excedência nesta bancada. |
| 1,85 V | 30 condições × 24 métricas=720 | 4/720 | 1,953102 V | Já há excedência pontual. |
| 1,95 V | 30 condições × 24 métricas=720 | 330/720; todas as 30 condições têm ao menos uma excedência | 2,056858 V (`sf`, 125 °C, Q=0, `PD_L`, VGS, 20,05 ns) | Reprovado para a bancada/borda de WL usadas. Os PASS funcionais em 1,95 V não qualificam esse ponto. |

Sensibilidade exploratória no ponto `sf/1,95 V/125 °C`: aumentar a borda ideal de WL de 50 ps para 200/500/1000 ps reduziu o maior pico de 2,056858 V para **1,989012 / 1,965104 / 1,957151 V**, respectivamente, mas nenhum atingiu 1,95 V. As bordas não modelam um driver real e não resolvem a qualificação.

Evidências: [`auditoria 1,62 V`](../sims/bitcell_read_terminal_audit_1p62.csv), [`auditorias 1,80/1,85 V`](../sims/bitcell_read_terminal_audit_1p8_1p85.csv), [`auditoria 1,95 V`](../sims/bitcell_read_terminal_audit_wpd1p26_1p95.csv), [`slew 200 ps`](../sims/bitcell_terminal_slew_sf_1p95_125_200ps.csv), [`500 ps`](../sims/bitcell_terminal_slew_sf_1p95_125_500ps.csv), [`1000 ps`](../sims/bitcell_terminal_slew_sf_1p95_125_1000ps.csv). A referência dos limites de dispositivo usada na auditoria está na [documentação SKY130 de detalhes dos dispositivos](https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html).

### 3.8 Monte Carlo/mismatch de SNM

Foram executadas 200 amostras com seeds reprodutíveis 1001–1200 em cada um de dois pontos escolhidos como triagem crítica. A biblioteca usa `sf_mm` para ativar variação mismatch; o deck compara VTCs de dois inversores independentes (com transistor de acesso ligado no modo read). Isso mede uma distribuição exploratória de SNM, **não** uma simulação completa de mismatch do circuito 6T com write driver, leitura dinâmica ou toda a matriz PVT.

| Modo | Ponto | N | SNM mínimo / média / desvio padrão / máximo |
|---|---|---:|---:|
| Read | `sf_mm`, 1,62 V, 125 °C | 200 | 269,936 / 300,933 / 11,038 / 330,733 mV |
| Hold | `sf_mm`, 1,62 V, −40 °C | 200 | 541,229 / 569,536 / 10,442 / 600,905 mV |

Uma repetição de quatro amostras produziu hash CSV idêntico, apoiando a reprodutibilidade das seeds. A meta nominal de 0,4 V não é um critério de yield para esta distribuição. A qualificação G7 determinística pós-layout está concluída; uma campanha estatística ampliada de mismatch/yield permanece trabalho posterior, fora do escopo desta fase.

Evidências: [`mismatch Read`](../sims/bitcell_read_snm_mismatch_sf_1p62_125.csv), [`mismatch Hold`](../sims/bitcell_hold_snm_mismatch_sf_1p62_minus40.csv), [`script`](../sims/run_bitcell_snm_mismatch.py).

## 4. Erros encontrados e correções/limites

| Erro ou risco encontrado | Efeito | Correção ou estado atual |
|---|---|---|
| Símbolos SKY130 no netlist Xschem foram emitidos como instâncias `X... sky130_fd_pr__...`, mas o deck isolado não carregava a biblioteca | ngspice reportou `Unknown subckt`/`unknown subckt` | Foi incluída a biblioteca SKY130 no contexto standalone e preparado smoke test local. A execução hierárquica foi também confirmada no relatório. |
| A folha isolada não tinha análise transitória | Aviso `No job (tran, ac, op etc.) defined` | Foi adicionado bloco `STANDALONE_TEST` com estímulos e `.tran`; o aviso significava ausência de análise, não falha dos modelos. |
| W originais menores (0,21 µm PMOS e 0,30 µm acesso) não selecionavam bins válidos do modelo contínuo usado | Xschem/ngspice reportou que não encontrou modelo válido | As larguras foram escaladas mantendo razões beta/gamma no sizing candidato `0,42/0,84/0,60 µm`. A escolha precisa ser revista se mudar o modelo/bin ou a estratégia de sizing. |
| PRE voltava a ligar quando WL subia na primeira bancada | Resultado de Δ/queda de nó não representava leitura sem pré-carga ativa | Sequência corrigida; valores antigos invalidados, como descrito na §3.1. |
| Limite de read-disturb aplicado ao sizing canônico | 28/40 casos nominais excederam 0,20 V; pior 0,230547 V | Identificado com sweep incluindo ambos os estados e a faixa de cargas. WPD maiores foram testados apenas como exploração, sem alterar o schematic canônico. |
| O valor de 1,98 V foi proposto para PVT | Fora do domínio publicado dos modelos MOS `01v8` usados | Não usado para qualificação. A faixa de alimentação precisa ser decidida/justificada; 1,95 V também mostrou picos terminais acima do limite de comparação. |
| Tentativa inicial de usar `cells/write_driver.sch` | O netlist Xschem headless falhava com `Net shorted: DATA_B - BLB` e nós abertos/sem drive | Corrigido para driver tri-state diferencial. O smoke standalone confirma complementaridade/isolamento; a triagem integrada antiga passou 12/12. A margem quantitativa foi fechada posteriormente em G7 com PEX: `60/60 PASS`, recuperação máxima `3,49470 ns`. |
| Tentativa inicial de VNC | Docker falhou ao publicar porta 80 já ocupada (`port is already allocated`) | Foi usada a execução local com X11; na tentativa VNC foram consideradas portas alternativas 8081/5902/8889. Não afeta a validade elétrica dos sweeps. |

## 5. Conquistas comprovadas até 02/10/2026

- Netlist e smoke funcional inicial foram obtidos com os modelos SKY130 após carregar a biblioteca e adicionar uma análise ao modo standalone.
- A bancada de leitura passou a desligar a pré-carga durante WL e a testar duas polaridades e quatro cargas de bitline.
- O gate de leitura expõe corretamente que o sizing canônico não atende o limite de excursão adotado, em vez de classificar como PASS apenas porque não houve inversão lógica.
- Aumentar WPD reduziu read-disturb nominal; WPD=1,26 também passou 90/90 leituras na matriz testada, mas com margem estreita e pontos de 1,95 V posteriormente reprovados na auditoria de terminais.
- Foram produzidas curvas borboleta/SNM, matriz PVT exploratória, teste de fuga, auditoria terminal e duas distribuições mismatch de 200 amostras, com CSVs associados.
- Os testes de escrita ideal foram mantidos corretamente como smoke tests; não foram confundidos com write margin de driver real.
- O `write_driver.sch` foi corrigido e netlistado sem curto/redes de controle abertas. Em `tt`, 1,8 V e 50 fF, o smoke standalone mostrou escrita complementar nos dois sentidos e deriva de `3,391/1,459 mV` durante 3 ns com `WE=0`.
- O sweep integrado do write driver com a bitcell passou `12/12` casos em `tt/ss/ff`, 1,8 V, 27 °C, ambos os sentidos e `WPD=0,84/1,26 µm`; o cruzamento de `Q=VDD/2` ocorreu entre `0,148–0,212 ns`. É triagem funcional, não write margin.
- Com a meta de engenharia de Read SNM nominal `>=0,4 V`, `WPD=1,26 µm` é o único sizing testado que passa em `tt/1,8 V` (`0,414349 V`).
- Para `WPD=1,26 µm` e `VDD=1,62 V`, o sweep de cinco corners × três temperaturas × dois sentidos passou `30/30`; pior flip completo `90/10%` = `0,3216 ns`, resultando em WL mínimo provisório de `0,4181 ns` após +30%.
- A organização de coluna ficou explícita para as macros suportadas: uma palavra por linha física, `Nrows=4/8/16/32` e nenhum mux de coluna (`Cmux=0`). Isso permite separar a contribuição de dreno da carga de fio/precharge/sense e evita tratar 50 fF como requisito arquitetural.
- A matriz agora separa valores medidos, gates provisórios, recomendações de engenharia e hipóteses de screening; em especial, ±10% de VDD, 15% de folga sobre PEX, +30% no pulso e o alvo de 100 mV não são atribuídos às fontes como números universais.

## 6. Registro histórico de fechamento em 07/10 (supersedido)

O texto e os números desta seção descrevem a conclusão registrada em
07/10/2026; a atualização de 08/10 no início deste arquivo reabriu a
qualificação elétrica do G7.

Estado consolidado dos gates:

1. A matriz pós-layout cobre a faixa qualificada `1,62–1,80 V`; a leitura passou `60/60`. `1,95 V` permanece somente auditoria/limite estático, e `1,98 V` não integra a qualificação com os modelos `01v8` atuais.
2. Manter `62,409659 fF`, `65 fF` e os `17 fF` adicionais de WL apenas como baseline histórica pré-layout. A referência corrente é `C_BL,PEX,max=453,588405 fF`, teto G7 `521,626665 fF`, e WL física de linha `98,914001 fF`, dos quais `89,925201 fF` entram como carga extra na bancada integrada.
3. G2 integrado pré-layout: em `65 fF + 17 fF` de WL, `SCLK=2,79 ns` passou `60/60` determinístico. G4 mismatch mostrou margem insuficiente para uma seed real (`3,66 ps` de setup em seed 7007); `SCLK=2,84 ns` foi adotado como timing ativo de freeze. No rerun crítico pós-aplicação, `2/2` passaram com setup mínimo `78,46 ps`, `ΔV>=360,848 mV` e `t_res<=0,07144 ns`.
4. G3 de escrita integrada pré-layout passou `60/60` com `WE=2,20 ns`, `WL_IN` assertada em `3,20 ns` e largura de `1,0 ns`; esses valores permanecem evidência histórica e foram substituídos pela matriz pós-layout como referência corrente.
5. G4 está fechado como **engineering screening**: read crítico `ss_mm/1,62 V/-40 °C` `10/10` PASS em `SCLK=2,84 ns`, `ff_mm/1,80 V/125 °C` `10/10`, smoke all-corner `10/10`; write `ss_mm/sf_mm` `20/20` e demais selecionados `6/6`. Não há claim de yield de produção. Potência permanece referência sem teto macro aprovado.
6. **G6 e G7 fechados no escopo de engenharia:** a coluna final fecha DRC/LVS/PEX e mede `C_BL,PEX,max=453,588405 fF`; teto `521,626665 fF`. Sense `1,5×`, precharge `Wpre=2,52 µm`, write `Wout=5,04 µm` e WL driver `1,68/5,04 µm` têm DRC `0`, LVS único e RC PEX. A linha física de 8 bits mede `98,914001 fF`; `WLOFF=361,100284 fF` permanece stress diagnóstico. Leitura e escrita passaram `60/60` cada. A leitura teve `t_res,max=0,23209 ns`, read-disturb `0,1796454 V`, setup mínimo `566,03 ps` e diferencial mínimo `0,276681 V`. A escrita recuperou as bitlines em até `3,49470 ns` e manteve margem mínima de WL de `0,34274 ns`, dentro das janelas de `0,25 ns` de resolução e 4 ns de recuperação. Os benches usaram cargas equivalentes no teto PEX ou acima dele e registram hashes dos netlists. Yield/ruído estatístico e teto de potência macro permanecem fora deste gate.

O resumo de desenvolvimento em [`relatorio_validacao_bitcell_6t_sky130.md`](relatorio_validacao_bitcell_6t_sky130.md) contém contexto adicional das bancadas e do esquemático. Os artefatos CSV e scripts listados aqui são as evidências detalhadas deste documento.
