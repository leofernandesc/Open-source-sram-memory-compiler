# Matriz de testes e decisões — bitcell SRAM 6T SKY130A

**Data do levantamento:** 02/10/2026
**Escopo:** testes elétricos pré-layout, falhas de bancada/netlist registradas e estado das verificações físicas.
**Estado geral:** caracterização exploratória em andamento; **Schematic Freeze bloqueado**. Este documento consolida evidências já salvas no repositório. Não declara sign-off.

## 1. Ambiente e convenções

Os testes registrados foram executados no container `isaiassh/unic-cass-tools:1.1.0`, com `PDK=sky130A`, `PDK_ROOT=/opt/pdks`, biblioteca contínua `/opt/pdks/sky130A/libs.tech/combined/continuous/sky130.lib.spice` e ngspice 44.2. Os dados e scripts citados estão em `sims/`.

Os cantos de processo são `tt`, `ff`, `ss`, `fs` e `sf`. O sizing canônico que permanece no esquemático é `WPU/WPD/WACC = 0,42/0,84/0,60 µm`, `L=0,15 µm`, `nf=1`. `WPD=1,05 µm` e `1,26 µm` foram variantes de exploração e **não foram aplicadas** ao esquemático.

Neste documento, **PASS** quer dizer que o caso cumpriu o teste e o limite específico usado pelo script; não implica automaticamente aprovação de arquitetura, confiabilidade ou fabricação. **MARGIN_FAIL** indica que o limite interno provisório não foi atendido, ainda que a célula não tenha invertido o estado.

### 1.1 Resumo consolidado das conquistas

| Conquista / decisão | Valor usado ou medido | Motivo do uso | Teste / evidência | Estado atual |
|---|---|---|---|---|
| Baseline canônico caracterizado | `WPU/WPD/WACC=0,42/0,84/0,60 µm`, `L=0,15 µm` | É o sizing que permanece no esquemático e serve de referência para comparar as variantes. | Read-disturb nominal `12/40 PASS`; Read SNM nominal `0,348804 V`. | **Não atende** os gates provisórios de leitura; continua canônico somente porque nenhum sizing novo foi congelado. |
| Candidato exploratório de leitura identificado | `WPU/WPD/WACC=0,42/1,26/0,60 µm`, β=`2,10` | Aumentar o pull-down reduz a elevação do nó que armazena `0` durante leitura. | `40/40` no sweep nominal; `90/90` no PVT/50 fF; Read SNM nominal `0,414349 V`. | É o único sizing testado que atende a meta nominal de `0,4 V`, mas **não está congelado nem aplicado** ao esquemático canônico. |
| Write driver corrigido | `Wdriver=0,84 µm`; `WE_B` interno; saída diferencial tri-state | Remover o curto `DATA_B–BLB` e garantir isolamento das bitlines quando `WE=0`. | Netlist Xschem PASS; smoke standalone complementar; deriva em `WE=0` de `3,391/1,459 mV` em 3 ns com 50 fF. | Funcional para triagem; resistência, corrente e carga final ainda não estão qualificadas. |
| Escrita integrada com driver real demonstrada | `1,8 V`, `tt/ss/ff`, 27 °C, 50 fF, ambos os sentidos, WPD `0,84/1,26 µm` | Verificar que o driver corrigido realmente troca a bitcell e não apenas bitlines isoladas. | `12/12` trocas; cruzamento de `Q=VDD/2` entre `0,148–0,212 ns`. | PASS de triagem funcional, não write margin. |
| Limite inferior provisório de WL obtido | pior flip completo `90/10% = 0,3216 ns`; regra `1,30×`; resultado `0,4181 ns` | Garantir tempo para a escrita completar no pior caso já testado com 30% de margem de engenharia. | WPD=1,26 µm, `1,62 V`, cinco corners × três temperaturas × dois sentidos = `30/30 PASS`; pior em `ss/-40 °C`, `0→1`. | Válido apenas como limite **pré-layout** com 50 fF; deve ser revisto com carga final. |
| Organização da coluna explicitada | uma palavra por linha física; `Nrows=4/8/16/32`; `Cmux=0` | A profundidade da macro define quantas células carregam cada BL/BLB; a arquitetura atual não usa mux de coluna. | Parcela de dreno pela aproximação de `0,2 fF/célula`: `0,8/1,6/3,2/6,4 fF`. | Base para estimativa pré-layout de `C_BL`; fio, precharge e sense ainda precisam ser adicionados. |
| Regra de carga da bitline formalizada | `C_BL=Nrows×(0,2 fF+Cwire/célula)+Cprecharge+Cmux+Csense`; teto final `1,15×C_BL,PEX` | Separar a carga física da coluna da hipótese de screening de 50 fF e reservar 15% de folga sobre a extração. | Fórmula registrada nas especificações; 50 fF continua sendo usado apenas para triagem elétrica. | O teto pré-layout ainda precisa ser fechado; a confirmação por PEX é **pós-freeze**. |
| Limite de tensão do modelo auditado | nominal `1,80 V`; alvo de engenharia `1,62–1,98 V`; auditoria em `1,95 V` | O sweep ±10% é recomendação de engenharia, mas o conjunto atual `01v8` não qualifica automaticamente o extremo superior. | Em `1,95 V`, `30/30` condições tiveram pelo menos um terminal acima de 1,95 V; pior `2,056858 V`. | `1,95/1,98 V` **não estão qualificados** com a bancada/modelos atuais. |
| Mismatch de SNM iniciado | `N=200`, seeds `1001–1200`, `.lib sf_mm` | Medir dispersão por mismatch local sem confundir com variação global de processo. | Read: `269,936/300,933/11,038/330,733 mV`; Hold: `541,229/569,536/10,442/600,905 mV` (`min/média/σ_pop/máx`). | Evidência estatística exploratória; ainda falta critério de yield e mismatch de escrita/read-disturb. |
| Fuga estática quantificada | pior soma das fontes `21,759 nA`; corrente de VDD ≈`21,751 nA` | Criar uma referência de leakage antes de definir orçamento da macro e periféricos. | `90/90` estados estáveis; pior ponto `fs/1,95 V/125 °C`. | Medido, mas sem orçamento de aceite; o ponto de 1,95 V não é qualificado pelo gate de tensão. |

## 2. Por que estes valores foram usados

Os rótulos abaixo distinguem **especificação/arquitetura**, **recomendação de engenharia**, **gate provisório** e **hipótese de screening**. Os números marcados como recomendação não são apresentados como limites universais extraídos da literatura.

| Parâmetro | Valores usados | Natureza do valor | Justificativa e limite da escolha |
|---|---|---|---|
| Alimentação nominal | 1,80 V | Especificação do projeto / nominal do domínio `01v8` | Ponto nominal usado para comparação de sizing e para o gate de Read SNM. |
| Faixa alvo de engenharia | 1,62–1,98 V (±10%) | **Recomendação de engenharia** | O extremo de 1,98 V não pode ser qualificado com o conjunto atual de modelos `01v8`; 1,95 V foi usado somente como stress/model-limit e apresentou excedências transitórias. |
| Alimentação de triagem executada | 1,62 / 1,80 / 1,95 V | Cobertura efetivamente simulada | 1,62 V corresponde a −10% do nominal; 1,80 V é nominal; 1,95 V foi o teto usado nos testes existentes e não substitui o ponto +10%. |
| Temperatura | −40 / 27 / 125 °C | Cobertura PVT de projeto | Extremos escolhidos para cobrir frio/quente e 27 °C como referência nominal. A cobertura em simulação não certifica, por si só, a validade dos modelos em toda a faixa. |
| Cantos | `tt/ff/ss/fs/sf` | Cobertura do model set | Incluem os cinco cantos de processo presentes na biblioteca SKY130 usada. |
| Carga de bitline | `C_BL = Nrows × (0,2 fF + Cwire/célula) + Cprecharge + Cmux + Csense`; sweep pré-layout 5/10/20/50 fF | Regra de engenharia + **screening** | A parcela só de dreno é 0,8/1,6/3,2/6,4 fF para 4/8/16/32 linhas e `Cmux=0` na arquitetura atual. O valor final é confirmado por PEX pós-freeze, com teto de `1,15 × C_BL,PEX`; 50 fF não é requisito. |
| Estados armazenados | Q=1/QB=0 e Q=0/QB=1 | Cobertura funcional | Verificam as duas polaridades, inclusive a assimetria entre BL e BLB e os dois sentidos de escrita. |
| Excursão do nó baixo em leitura | ≤0,20 V | **Gate provisório** | Limite interno da especificação/testbench para expor read-disturb. Não é um limite universal do SKY130 nem um critério formal aprovado por arquitetura. |
| Diferencial de bitline | ≥100 mV em 21 ns | **Meta preliminar de engenharia** | Usado como alvo de leitura enquanto offset/noise do sense amplifier não são caracterizados. O testbench mede a diferença em 21 ns, com WL iniciado em 20 ns. |
| Read SNM nominal | ≥0,40 V em `tt`, 1,8 V | **Recomendação de engenharia** | Gate nominal para comparar os sizings testados; não é apresentado como limite universal da literatura nem como critério PVT/yield. |
| Janela inferior de WL | `1,30 ×` pior tempo de flip completo | **Recomendação de engenharia** | Flip completo exige Q/QB em 90%/10% de VDD. Com o pior caso medido de `0,3216 ns`, resulta em `0,4181 ns` provisórios; o valor deve ser revalidado após a carga física ser conhecida. |
| Janela superior de WL | ainda não congelada | Método de engenharia pendente | Deve ser limitada por read-disturb/excursão da bitline e estabilidade dinâmica no canto rápido; não há limiar inventado de “dynamic SNM” neste documento. |
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

Dados: [`SNM canônico`](../sims/bitcell_snm_summary.csv), [`SNM WPD=1,05`](../sims/bitcell_snm_summary_wpd1p05.csv), [`SNM WPD=1,26`](../sims/bitcell_snm_summary_wpd1p26.csv) e curvas VTC correspondentes em `sims/bitcell_snm_curves*.csv`. Figuras: [`borboleta canônica`](assets/bitcell_6t_snm_butterfly.png), [`WPD=1,05`](assets/bitcell_6t_snm_wpd1p05.png), [`WPD=1,26`](assets/bitcell_6t_snm_wpd1p26.png).

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
| WLVM nominal | `VDD=1,8 V`, 5 cantos, 2 sentidos, WPD=0,84 e 1,05 µm; WL reduzido por busca binária em 7 iterações (~14 mV); pulso de 10 ns; bitlines ideais | 20 combinações registradas; pior WLVM=0,619 V para WPD=0,84 e 0,605 V para WPD=1,05, ambos em `fs` | Projeto ainda não define WLVM mínimo. Não inclui driver resistivo, carga de coluna, PVT estendida nem sizing 1,26 µm. A métrica não libera freeze. | [`bitcell_write_margin_wlvm.csv`](../sims/bitcell_write_margin_wlvm.csv) |
| Write driver — timing nominal | WPD=1,26 µm, 1,8 V, `tt/ss/ff`, 27 °C, ambos os sentidos, 50 fF | 6/6 PASS; pior flip completo 90/10% = 0,288 ns; +30% = 0,375 ns | Screening de timing, ainda com carga arbitrária. | [`bitcell_write_driver_timing_nominal.csv`](../sims/bitcell_write_driver_timing_nominal.csv) |
| Write driver — baixa tensão | WPD=1,26 µm, 1,62 V, 5 cantos × 3 temperaturas × 2 sentidos, 50 fF | 30/30 PASS; pior flip completo = 0,3216 ns em `ss/-40 °C`, 0→1; +30% = **0,4181 ns** | Define o limite inferior **provisório** de WL enquanto a carga final não vem do PEX. | [`bitcell_write_driver_timing_1p62.csv`](../sims/bitcell_write_driver_timing_1p62.csv) |

### 3.6 Fuga estática em hold

Condições: candidato exploratório WPD=1,26 µm; cinco cantos × 3 tensões × 3 temperaturas × dois estados = 90 simulações; `WL=0`, `BL=BLB=VDD`; medição média entre 80 e 100 ns. Os estados ficaram estáveis em 90/90 casos. Maior soma das correntes de VDD, BL e BLB: **21,759 nA** em `fs`, 1,95 V, 125 °C, Q=1. Corrente da fonte VDD no caso mais crítico: aproximadamente **21,751 nA**, equivalente a **42,414 nW** para a célula. Ainda falta um orçamento de fuga aprovado; a soma das fontes não deve ser confundida com corrente de VDD apenas e não inclui periféricos.

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

Uma repetição de quatro amostras produziu hash CSV idêntico, apoiando a reprodutibilidade das seeds. A meta nominal de 0,4 V não é um critério de yield para esta distribuição; ainda falta definir o gate estatístico e executar mismatch de margem de escrita/read disturb nos demais pontos relevantes.

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
| Tentativa inicial de usar `cells/write_driver.sch` | O netlist Xschem headless falhava com `Net shorted: DATA_B - BLB` e nós abertos/sem drive | Corrigido para driver tri-state diferencial. O netlist agora passa; smoke standalone confirma complementaridade/isolamento e o sweep integrado trocou a bitcell em 12/12 casos. Write margin quantitativo continua pendente porque carga/tempo/limite ainda não são requisitos fechados. |
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

## 6. Pendências e decisão de freeze

**O esquemático não está congelado.** A geometria e verificação física também não foram concluídas. O estado de layout consultado não contém `cells/bitcell_6t.mag`; DRC e LVS ainda não foram executados.

Bloqueios/gates pendentes:

1. A faixa-alvo agora é `1,62–1,98 V` (±10% de 1,8 V), mas `1,98 V` ainda não pode ser qualificado com o modelo `01v8` atual; resolver essa incompatibilidade antes de declarar cobertura completa de tensão.
2. Fechar um **teto pré-layout** de `C_BL` a partir de `Nrows`, contribuição de dreno, estimativa conservadora de fio e cargas de precharge/sense. Com esse teto, revalidar o WL mínimo provisório de `0,4181 ns` e fechar a janela superior por read-disturb/excursão da bitline e estabilidade dinâmica. Os 50 fF atuais continuam apenas como screening.
3. Caracterizar o sense amplifier para confirmar se a meta preliminar de `100 mV` cobre offset/noise e cabe no objetivo de acesso `<2,5 ns`.
4. Definir orçamento de leakage e completar mismatch/yield para escrita/read disturb com driver real e a carga pré-layout adotada para o freeze.
5. Com os gates elétricos pré-layout fechados, escolher e aplicar o sizing canônico, revisar borboleta/read disturb e então declarar Schematic Freeze.
6. **Pós-freeze:** desenhar `bitcell_6t.mag`, executar Magic DRC, extrair SPICE/PEX e executar Netgen LVS. Fixar então `C_BL,max = 1,15 × C_BL,PEX` e repetir a caracterização elétrica; se a extração violar os gates, reabrir o sizing/freeze. Validar ainda orientação MX/tiling e a matriz 4×8 completa; orientação MX não garante automaticamente compartilhamento de poços, taps ou alimentação.

O resumo de desenvolvimento em [`relatorio_validacao_bitcell_6t_sky130.md`](relatorio_validacao_bitcell_6t_sky130.md) contém contexto adicional das bancadas e do esquemático. Os artefatos CSV e scripts listados aqui são as evidências detalhadas deste documento.
