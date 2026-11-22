# Fase 3 · Primeiro protótipo StrongARM do sense 3 em TT

**Veredito · `STRONGARM_FUNCTIONAL_WITH_RISK`.** Um StrongARM SKY130 de 11 MOS, com SCLK nominal, forneceu D e Q corretos em c15, c16 e c17 e recuperou os quatro nós reinicializados. A subida histórica de SCLK produziu cerca de **397–398 ps** de condução simultânea entre tail e reset pelo marcador de 1 µA. Esse intervalo concentrou cerca de **95% da carga de canal da cauda durante a avaliação**. Há fundamento para avançar em avaliação esquemática com impedâncias representativas antes de qualquer layout. C continua com `FAIL` em TT. [Análise e waveforms](../build/phase3/sense3_strongarm_tt_20261121/analysis.json)

## A. Topologia e dimensionamento

Comparador diferencial StrongARM convencional de cauda única, com reset nos dois nós intermediários e nos dois nós regenerativos. Em SCLK baixo, os quatro PMOS de reset conduzem para VDD e a cauda NMOS corta o retorno direto. Em SCLK alto, a cauda conduz e a diferença de descarga em DI_BL e DI_BLB polariza o latch cruzado. NTAIL fica condicionado por seus caminhos de transistor e pelas capacitâncias do circuito. O estado de NTAIL não é imposto por uma fonte. [Topologia convencional, Fig. 17.7.1 de Schinkel et al.](https://people.engr.tamu.edu/spalermo/ecen689/Schinkel_Nauta_ISSCC07_Double-Tail_SenseAmp.pdf) · [Netlist do candidato](../build/phase3/sense3_strongarm_tt_20261121/strongarm.spice)

| Função | MOS e conexões | W/L (µm) | Justificativa inicial |
| --- | --- | --- | --- |
| Entrada | XIN_BL / XIN_BLB, gates BL / BLB, drenos DI_BL / DI_BLB, fontes NTAIL | 0,65 / 0,15 (NMOS) | Par casado de largura de referência do projeto. Limita a carga dos gates das bitlines e fornece transcondutância na janela de modo comum alto. |
| Tail | XTAIL entre NTAIL e VSS, gate SCLK | 0,98 / 0,15 (NMOS) | Ponto de partida da cauda de C, com retorno comum às duas entradas. |
| Regeneração NMOS | XLN_SAB entre SAB e DI_BL, gate SA. XLN_SA entre SA e DI_BLB, gate SAB | 0,98 / 0,15 | Par casado com largura dos NMOS regenerativos de C. |
| Regeneração PMOS | XLP_SAB entre VDD e SAB, gate SA. XLP_SA entre VDD e SA, gate SAB | 1,89 / 0,15 | Largura de referência de C para restaurar a saída oposta à descarga. |
| Reset | XR_DI_BL, XR_DI_BLB, XR_SAB, XR_SA. Cada um conecta seu nó a VDD, SCLK no gate | 0,84 / 0,15 (PMOS) | Quatro dispositivos casados. Largura intermediária para recarregar nós de pequena carga sem usar a força do pull-up regenerativo no reset. |

Todos os MOS do núcleo usam `sky130_fd_pr__nfet_01v8` ou `sky130_fd_pr__pfet_01v8`, com bulk NMOS em VSS e bulk PMOS em VDD. Os tamanhos formam um único ponto inicial. Nenhum ajuste foi feito após observar o resultado.

**Mapeamento físico.** BL maior descarrega DI_BL mais cedo e leva SAB a baixo, com SA alto. BLB maior descarrega DI_BLB e leva SA a baixo, com SAB alto. Dois `buf_1` não inversores isolam as saídas internas. DOUT vem de SA e dirige A1 do mesmo tipo de mux de C (`mux2_1 _40_`). A0 recebe Q e o seletor é READ_Q arquivado. D alimenta um `dfxtp_2` com o clock local arquivado de `_62_.Y`, correspondente à captura na descida pública. Q é calculado pelo FF da bancada. A saída complementar do buffer fica observada, sem consumidor equivalente. Assim, BL > BLB entrega D alto e BLB > BL entrega D baixo sem inverter a interpretação. [Netlist digital de C](phase3_revisao_arquitetural_sense_sky130_20261121.md#b-conectividade-efetiva-de-c) · [Deck com mux e FF](../build/phase3/sense3_strongarm_tt_20261121/run/bench.spice)

## B. Compatibilidade e preflight

**`READY`.** A bancada é esquemática, com 59 ns no recorte de 188–247 ns da referência C de 250 ns. Foi mantido o histórico de c15–c17. O replay tem 3.708 nós temporais, com as amostras originais e interpolação apenas para delimitar o intervalo de replay e entre os pontos. BL/BLB são os terminais dos samplers de C (`rc8210/rc8222`). SCLK vem do gate do tail `rc8585`. `rc6338`, `rc6243` e `rc8510` fornecem a captura, READ_Q e a referência de PRECH. O único clock que comanda o núcleo é SCLK. PRECH é observável da referência. A bancada não inclui o array, WL física, drivers de bitline ou PRECH com carga ativa. O SCLK ideal de replay também fixa a forma de onda contra a mudança de carga do novo núcleo.

O bulk e a conectividade dos 11 MOS foram conferidos. Os quatro nós reinicializados têm pull-ups próprios e a retenção é dinâmica quando estes desligam. A alimentação de 1,8 V segue o ponto constante do recorte histórico. Foi confirmado o PEX C `12c41d1a…`, o waveform TT histórico `7f6c050f…`, o gate histórico `VALIDATED` e o fecho de 319 modelos instalados. Os subcircuitos auxiliares vieram da biblioteca SKY130 HD instalada. Gear/KLU, TT, 27 °C e passo máximo de 25 ps foram mantidos. O deck e as condições foram selados no preflight. [Recibo de preflight](../build/phase3/sense3_strongarm_tt_20261121/preflight.json) · [Controle arquivado](phase3_precondicionamento_sense3_tt_20261120.md)

| Condição de entrada na abertura, eixo histórico | c15 | c16 | c17 |
| --- | ---: | ---: | ---: |
| Modo comum em SCLK20 (V) | 1,869 | 1,873 | 1,870 |
| BLB−BL em SCLK20 (mV) | −30,5 | +15,1 | +19,9 |
| Modo comum em SCLK50 (V) | 1,556 | 1,631 | 1,622 |
| BLB−BL no primeiro tail de 1 µA (mV) | −194,8 | +139,5 | +150,5 |
| Captura→SCLK↓80, janela observada (ns) | 4,013 | 4,012 | 4,011 |

Extremos reproduzidos nos terminais de entrada: **BL −0,039 a 1,885 V** e **BLB −0,042 a 1,881 V**. O par NMOS vê modo comum alto no começo da avaliação, com a diagonal de descarga determinada pelo diferencial. As excursões foram mantidas. A compatibilidade prévia era uma triagem de amplitude e polarização com base no modelo de 1,8 V. Depois do run, os máximos de VGS positivos foram 1,659 e 1,623 V no par. No núcleo, os maiores módulos de VGS, VDS e VGD foram 1,810, 1,883 e 1,845 V. O limite de magnitude de 1,95 V é uma referência de validade dos modelos, usada na triagem. Essas medições cobrem a trajetória ensaiada. Faixa garantida de modo comum, condições de missão e confiabilidade seguem abertas. [Modelos SKY130 1,8 V](https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html) · [Trajetória e polarização por dispositivo](../build/phase3/sense3_strongarm_tt_20261121/analysis.json)

## C. Execução e decisão funcional

Foi executado um único transiente, via container `sram-xschem`, em `/work/build/phase3/sense3_strongarm_tt_20261121/run`:

```sh
timeout --kill-after=5s 120s stdbuf -o0 -e0 /opt/ngspice/ngspice-44.2/bin/ngspice -n -b bench.spice
```

Tempo **51,634 s**, retorno **0**, **16.747 amostras** até 59 ns. Tensões e correntes têm os mesmos timestamps, finitos e monotônicos. O maior erro frente ao replay foi ~2,83 µV no clock de captura durante a interpolação. Em SCLK e BL/BLB ficou abaixo de 0,30 µV. SHA-256 do deck `890509a30cd4d01c23f4744ef1f563bedc849166382f17d58f53dd8422001636`, do waveform `faaf39510d9af3cae60b00962ade399112eafff108b50bdcd6da9a787f6ae2b6` e das correntes `310dd5f5a719f9187921b91041450ad167ad5cc2cbc9b70b017e119f215d14c7`. [Comando](../build/phase3/sense3_strongarm_tt_20261121/attempt.json) · [Recibo de simulação](../build/phase3/sense3_strongarm_tt_20261121/simulation.json) · [Log](../build/phase3/sense3_strongarm_tt_20261121/run/ngspice.log)

| Ciclo | Bit | SA/SAB na captura | D na captura | Par e D corretos desde (ns) | Margem conjunta até captura (ns) | Q após captura |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| c15 | 1 | Alto / baixo | 1,80008 V | 194,578 | 5,480 | 1 |
| c16 | 0 | Baixo / alto | −52 µV | 214,791 | 5,267 | 0 |
| c17 | 0 | Baixo / alto | −48 µV | 234,765 | 5,293 | 0 |

Critério de validade contínua: bandas 20/80% de 1,8 V no par e em D até a captura local de 200,058/220,058/240,058 ns. D já estava alto no início da observação de c15. A decisão nesse ciclo é confirmada pelo par complementar, com margem conjunta de 5,480 ns. Em c16 e c17, DI_BLB estava cerca de 19/79 mV abaixo de DI_BL quando o par e D entraram juntos nas bandas corretas. D entrou na banda baixa cerca de 385/358 ps após SCLK50. Q cruzou a banda baixa após a captura de c16, cerca de 176 ps depois no primeiro ponto válido sustentado. Em c17, Q já estava baixo e permaneceu nessa banda. Esses tempos incluem o caminho físico esquemático dos buffers, mux e FF. As margens são observações até a captura, sem representar setup ou frequência garantidos. [Waveform e correntes](../build/phase3/sense3_strongarm_tt_20261121/measurements.csv) · [Gráfico](../build/phase3/sense3_strongarm_tt_20261121/strongarm_tt_resultado.png)

## D. Avaliação elétrica e comparação com C

| Observável | c15 | c16 | c17 |
| --- | ---: | ---: | ---: |
| Pico de corrente do tail na avaliação (µA) | 90,7 | 93,0 | 93,0 |
| Carga de canal do tail na avaliação (fC) | 17,64 | 18,36 | 18,27 |
| Sobreposição tail/reset na subida, marcador 1 µA (ps) | 397,3 | 396,8 | 398,1 |
| Carga de tail durante essa sobreposição (fC) | 16,73 | 17,55 | 17,47 |
| Sobreposição na descida e reset, marcador 1 µA (ps) | 95,7 | 97,4 | 99,7 |
| Quatro nós de reset altos a partir de (ns) | 204,303 | 224,300 | 244,297 |
| PRECH histórico ↓80% (ns) | 204,290 | 224,290 | 244,288 |

A sobreposição é a interseção dos intervalos com `|Id|` acima de 1 µA em XTAIL e em ao menos um PMOS de reset, com cruzamentos interpolados. Ela ficou nas transições e não persistiu na fase alta estável. O marcador descreve a atividade observada e não é um limite de corrente. A proporção contabiliza a carga da cauda durante a simultaneidade. A parcela fornecida diretamente pelos resets permanece indeterminada. A duração e as correntes medidas justificam examinar a alimentação compartilhada, mesmo com as decisões corretas. No reset, o maior pico individual entre os quatro PMOS foi aproximadamente 68 µA. Os quatro nós recuperaram a faixa alta pouco depois do marcador PRECH↓80% histórico e antes da próxima avaliação. O esquema sem array observa a sequência nominal, sem medir contenção ou recuperação do PRECH ativo de C.

O maior `|I|` das fontes que reproduzem BL/BLB na avaliação foi ~5,8 µA, com carga absoluta de até ~1,1 fC em uma entrada. A fonte de SCLK entregou carga líquida de ~9,4 fC durante a avaliação. Sua demanda chegou a ~14–15 µA na subida e até ~34 µA na descida. Esses valores caracterizam a demanda no terminal fixado pela fonte ideal. A tensão de kickback sobre uma bitline real, o disturb e o slew sob carga compartilhada seguem sem medição. Nas saídas houve excursões breves do buffer complementar até 1,947 V e −0,148 V, com saída complementar sem carga funcional. Elas ficaram fora da janela de captura e merecem conferência com carga e parasitas representativos. [Medições por fase, cruzamentos e excursões](../build/phase3/sense3_strongarm_tt_20261121/analysis.json)

| Aspecto | Latch de sete MOS de C | StrongARM esquemático |
| --- | --- | --- |
| Regeneração em TT | Samplers PMOS compartilham a abertura com o tail. c16/c17 invertem a polaridade e entregam D alto. | Par NMOS desenvolve diferencial nos nós intermediários. c16/c17 resolvem e sustentam D baixo com a fase histórica. |
| Reset | Recuperação de SA/SAB pela pré-carga de BL/BLB através dos samplers. | Quatro reset PMOS comandados localmente por SCLK. Há sobreposição com o tail nas rampas. |
| Bitlines | Ligação condutiva durante amostragem e acoplamentos extraídos. | Entradas nos gates e demanda capacitiva medida sob replay ideal. Kickback em carga real segue aberto. |
| Captura e integração | Mux, FF e ramo de clock já fazem parte de C. | Mesmas funções do mux e FF em células reais, com buffers de saída. Carga e layout do núcleo, retorno compartilhado e oito colunas seguem pendentes. |
| Complexidade | Sete MOS no sense antes da carga de saída. | Onze MOS no núcleo e buffers auxiliares. Área e potência comparáveis dependem de implementação física e fixture com a mesma fronteira. |

## E. Próxima decisão e preservação

O protótipo demonstrou ambas as polaridades e recuperação em TT. A decisão c16 corrigida foi seguida por c17 correto. Nenhum bloqueio de modo comum foi demonstrado para o replay ensaiado. O principal risco elétrico medido é a sobreposição de condução durante a subida lenta do SCLK nominal. Excursões nas saídas e demanda de carga em BL/BLB e SCLK também precisam de uma bancada com impedâncias defensáveis.

**Próximo gate recomendado:** repetir a comparação em bancada esquemática com fontes de BL/BLB e SCLK de impedância representativa, pré-carga ativa e carga de saída equivalente, preservando as fases históricas. Exigir os três bits corretos até captura e verificar a sobreposição, o kickback e a recuperação no novo ambiente antes de layout. Nenhuma etapa posterior foi executada.

C permanece como referência física na branch `integration/phase3-danilo-ss`, HEAD `8e1d961`. O checkpoint recuperável, o latch original e o v2 foram preservados. C continua em `FAIL` TT e `PASS` SS no escopo ensaiado, com FF integrado pendente. Monte Carlo SNM `tt_mm` experimental concluído e com homologação pendente. Qualificação `NOT_CHARACTERIZED`, Liberty pendente. Foram um candidato, um preflight, um transiente e zero alterações físicas, sem commit, push ou merge.
