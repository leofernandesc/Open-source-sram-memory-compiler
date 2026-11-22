# Fase 3 · Controle FF de C e célula StrongARM isolada

**Controle FF · `FF_FAILURE_PREEXISTING`.** Bits 6 e 7 já resolvem incorretamente em C original, sem o StrongARM. O ECO virtual é dispensável para produzir os dois erros de c15 nestas condições. **O mesmo controle mostrou que o sense 3 nativo também falha em FF.** Em c16 e c17, C retorna `0xF8` e o ECO retorna `0xF0`.

O núcleo StrongARM de 11 MOS foi implementado em SKY130A, com **DRC zero**, **LVS único**, extração distribuída e **PASS funcional em TT pós-layout** na coluna ativa 4×1. Os ciclos 15–17 retornaram **1, 0, 0** em D e Q, com margem mínima conjunta de **5,046 ns**. A macro C e o ECO virtual permanecem disponíveis como referências.

| Critério | Resultado |
|---|---|
| Controle FF de C nativa, C250 | `FF_FAILURE_PREEXISTING` |
| Origem do erro DATA6/DATA7 | Bits 6 e 7 já resolvem incorretamente em C original, sem o StrongARM. |
| Layout StrongARM isolado | Implementado, 28,770 × 18,195 µm |
| DRC em Magic | PASS, zero no MAG e no GDS reimportado |
| LVS em Netgen | PASS, correspondência única no MAG e no GDS reimportado |
| PEX da folha | Disponível, 11 MOS, 113 R, 84 C, 78 C com valor positivo |
| TT pós-layout isolado | PASS no ensaio 4×1, SCLK histórico |
| Integração na macro 4×8 | Fora do escopo desta rodada |

## 1. Controle FF pareado da macro C

A referência usa o PEX selado de C (`12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`) e o binding C250 instrumentado, sem os 11 MOS do StrongARM nem seus dois buffers. Permaneceram os sete MOS nativos `X102`, `X234`, `X235`, `X351`, `X521`, `X1267` e `X1560`. A comparação de cartões conserva todos os 16.187 R, 12.371 C e os demais 1.742 MOS em ambos os circuitos. A diferença no bench além da substituição consiste nas sondas e nas diretivas de exportação.

O controle utiliza os mesmos seis comandos de escrita, dados, endereços, controles, rampa, registradores, buffers e 250 ns do ECO FF. Condições **SKY130A FF, 1,8 V nominal, 27 °C, Gear/KLU, passo máximo 25 ps**. Foram verificados 319 hashes de modelos. Os diffs e as observações registram a proveniência. [Preflight](../build/phase3/strongarm_isolated_and_native_ff_20261122/FF_native/preflight.json) · [Diff do bench](../build/phase3/strongarm_isolated_and_native_ff_20261122/FF_native/comparison_bench.diff) · [Diff do binding](../build/phase3/strongarm_isolated_and_native_ff_20261122/FF_native/comparison_binding.diff)

O transiente nativo terminou em **50 min 45 s**, com retorno 0 e
**15.511** amostras. O mesmo observador usou 0,36/1,44 V, D no cruzamento de 50% de cada clock local,
Q em início do ciclo +11 ns e DATA em +11 ns e +11,5 ns. A continuidade de D e DATA foi verificada nos mesmos prazos. O transiente com ECO arquivado tem 15.534 amostras.

| Ciclo | Linha / endereço observado | Esperado | C nativa FF, DATA | D / Q nativos | ECO FF, DATA |
|---:|---|---|---|---|---|
| 14 | 1 / 1 | `0xAA` | `0xAA` / `0xAA` | `0xAA` / `0xAA` | `0xAA` / `0xAA` |
| 15 | 2 / 2 | `0x0F` | `0xCF` / `0xCF` | `0xCF` / `0xCF` | `0xCF` / `0xCF` |
| 16 | 3 / 3 | `0xF0` | `0xF8` / `0xF8` | `0xF8` / `0xF8` | `0xF0` / `0xF0` |
| 17 | 3 / 3 | `0xF0` | `0xF8` / `0xF8` | `0xF8` / `0xF8` | `0xF0` / `0xF0` |

As duas observações de DATA aparecem na ordem +11 ns e +11,5 ns. As seis escritas foram observadas nas janelas
em que WL, endereço e WE estavam válidos, com os payloads c2=0xAA, c3=0x55, c4=0x0F, c5=0xF0, c8=0x55, c10=0xAA. A bitcell da linha 3, bit 3, reteve o zero dentro das bandas observadas em c16 e c17.
Em c16 e c17, SA3 está alto em C na captura e D3/Q3 permanecem em aproximadamente 1,801/1,800 V. Com o ECO, D3 fica abaixo de 1 mV e Q3 abaixo de 0,15 mV. Isso localiza a diferença de leitura a montante do registrador de saída. Na linha 2 do ciclo 15, Q/QB internos da bitcell não foram sondados. O diagnóstico ali usa os nós de BL/BLB,
SA/SAB, D/Q e DATA.

| FF | Bit | WL 20/50/80% (ns) | SCLK 20/50/80% (ns) | SCLK20−WL80 (ps) | BLB−BL em SCLK20/50 (mV) | Decisão SA/SAB sustentada (ns) | D / Q na faixa válida |
|---|---:|---|---|---:|---|---|---|
| C nativa | 6 | 192,963 / 193,020 / 193,104 | 193,008 / 193,203 / 193,529 | -96,6 | -7,0 / 282,9 | 1 em 193,592 | 1 / 1 |
| C nativa | 7 | 192,963 / 193,020 / 193,104 | 193,008 / 193,203 / 193,529 | -96,6 | 5,5 / 238,3 | 1 em 193,592 | 1 / 1 |
| ECO virtual | 6 | 192,963 / 193,020 / 193,104 | 193,007 / 193,200 / 193,527 | -97,1 | -6,9 / 276,4 | 1 em 193,559 | 1 / 1 |
| ECO virtual | 7 | 192,963 / 193,020 / 193,104 | 193,007 / 193,200 / 193,527 | -97,1 | 5,5 / 233,5 | 1 em 193,583 | 1 / 1 |

Nos bits 6 e 7, os intervalos amostrais das bordas de WL e SCLK se sobrepõem entre os ensaios. Os deslocamentos interpolados ECO−C de WL/SCLK ficam entre −2,53 e +0,26 ps. O maior deslocamento se dá em SCLK50 e a incerteza de amostragem permite sinais de diferença em ambas as direções. Nas primeiras amostras de comparação ancoradas até SCLK50, o residual entre variantes permanece abaixo de 0,8 mV em SA/SAB e de 0,4 mV em BLB−BL. Em SCLK80 de C (~193,529 ns), já durante a regeneração, a diferença de SA (ECO−C) é de +67/+76 mV, enquanto o residual diferencial de bitline fica abaixo de 0,3 mV. As duas versões convergem à mesma polaridade errada, sustentada em C por cerca de 6,46 ns até a captura. Os JSONs incluem os resíduos em tempo absoluto e os intervalos de interpolação. O marcador SCLK20 situa a fase de abertura em relação a WL. Ele não mede corrente
dos samplers. O diferencial segue evoluindo após a abertura. A decisão válida é a combinação de SA e SAB que
permanece nas bandas até a captura. A comparação sustenta a classificação funcional acima, com causalidade da
relação WL–SCLK ainda em aberto.

[Recibo FF](../build/phase3/strongarm_isolated_and_native_ff_20261122/FF_native/simulation.json) · [Análise pareada](../build/phase3/strongarm_isolated_and_native_ff_20261122/ff_paired.json) · [D/Q por bit e ciclo](../build/phase3/strongarm_isolated_and_native_ff_20261122/ff_paired_lanes.csv) · [Gráfico de c15](../build/phase3/strongarm_isolated_and_native_ff_20261122/ff_c15_pareado.png)


## 2. Núcleo físico StrongARM

O esquema arquivado fixa os 11 MOS de 1,8 V, todos com L=0,15 µm e um finger. O par diferencial NMOS tem W=0,65 µm. Tail e par NMOS do latch usam W=0,98 µm, os dois PMOS do latch usam W=1,89 µm e os quatro PMOS de reset usam W=0,84 µm. Os bulks PMOS vão a VDD e os NMOS a VSS. O reset acontece localmente com SCLK baixo. Na avaliação, BL>BLB produz SA alto e SAB baixo. Os dois `sky130_fd_sc_hd__buf_1` externos foram mantidos na bancada TT, junto ao mux e ao FF existentes. O netlist exportado pelo Xschem reproduz os 11 terminais de instância D/G/S/B, modelo e W/L do esquema arquivado. [Esquema Xschem](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/strongarm_tt_v0.sch) · [Referência elétrica](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/reference.spice)

| Ordem SPICE | Pino | Função | Acesso na folha |
|---:|---|---|---|
| 1 | BL | Entrada diferencial true | M2 |
| 2 | BLB | Entrada diferencial complementar | M2 |
| 3 | SCLK | Habilita avaliação, desativa reset | M3 |
| 4 | VDD | Alimentação e taps de nwell | M3 |
| 5 | VSS | Retorno e guard rings NMOS | M3 |
| 6 | SA | Saída true para buffer e mux | M3 |
| 7 | SAB | Saída complementar | M3 |

A folha usa PCells de um finger, duas fileiras escalonadas, contatos de poço e substrato e rotas LI/M1/M2/M3. BL e BLB ficam na mesma borda física e têm percursos resistivos equivalentes. O tamanho e o acesso de pinos da folha estão documentados no LEF `CLASS BLOCK`. O encaixe por coluna e os retornos compartilhados exigem verificação na geometria de integração. [MAG](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/strongarm_tt_v0.mag) · [GDS](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/strongarm_tt_v0.gds) · [LEF](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/strongarm_tt_v0.lef) · [Imagem do GDS](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/strongarm_tt_v0_layout.png)

### DRC, LVS e PEX

Magic **8.3.684**, deck SKY130A, estilo `drc(full)` euclidiano, retornou zero no layout final. O GDS foi lido de volta em diretório separado e também passou com zero. Netgen **1.5.293**, com `sky130A_setup.tcl`, retornou `Circuits match uniquely.` para ambas as verificações. O LVS identifica os 11 MOS, 10 redes, sete pinos, W/L e conexões de bulk. O PEX final do mesmo MAG usa limiares de saída R/C iguais a zero e `extresist mindelay 0`. A contração da malha resistiva recompõe as mesmas dez redes LVS e associa os 11 MOS aos mesmos terminais e dimensões. As placas dos capacitores estão em grupos com portas ou terminais ativos, inclusive os segmentos anotados como `FLOATING` na listagem do Magic. Uma repetição independente preservou os MOS, resistores e placas dos capacitores. Houve renumeração de cartões C e uma diferença de 0,00001 fF em um deles, no último dígito extraído. O ensaio elétrico usou o PEX congelado. Os arquivos preliminares da extração com poda ficam separados por sufixo `_initial_1ps`. [DRC](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/route.log) · [LVS](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/lvs.log) · [GDS reimportado](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/roundtrip/magic.log) · [LVS do GDS](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/roundtrip/lvs.log) · [Reprodução independente](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/reproduction.log) · [Hashes de regras](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/rule_decks.sha256)

| Porta ou par de redes | Capacitância explícita incidente ou mútua | Resistência DC equivalente |
|---|---:|---:|
| BL | 0,64804 fF | 330,449 Ω até o gate |
| BLB | 0,64793 fF | 330,449 Ω até o gate |
| SCLK | 13,20089 fF | 379,85–390,55 Ω até os cinco gates |
| SA | 12,06283 fF | 95–551 Ω até terminais da rede |
| SAB | 12,69545 fF | 96–551 Ω até terminais da rede |
| SA ↔ SAB | 1,73179 fF | Acoplamento |
| SCLK ↔ SA / SAB | 0,68242 / 1,24744 fF | Acoplamento |
| SCLK ↔ VDD / VSS | 3,30229 / 7,96874 fF | Acoplamento |

Os valores excluem a capacitância intrínseca dos MOS. Somar os valores incidentes de duas portas conta duas vezes a capacitância que as acopla. A carga transitória vista pelo acionador depende também do movimento dos nós acoplados e das tensões dos MOS. [Netlist PEX](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/strongarm_pex.spice) · [Auditoria e inventário PEX](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/signoff/pex_audit.json)

## 3. TT pós-layout na coluna 4×1

O PEX verificado substituiu somente o núcleo StrongARM esquemático. A bancada mantém as quatro bitcells, BL/BLB ativas, write driver, pré-carga, equalização, buffers, mux, FF, fontes históricas de controle, SCLK e trilhos da bancada anterior. A comparação do bench confirma mudanças limitadas aos nomes das sondas internas. Foi executado um transiente **TT, 1,8 V, 27 °C, 169 ns, 25 ps máximo, Gear/KLU**, ngspice 44.2, com retorno 0 em **61,83 s** e **37.620 amostras**. As quatro escritas estabeleceram Q/QB corretamente antes das leituras e as células mantiveram o estado. [Diff e preflight](../build/phase3/strongarm_isolated_and_native_ff_20261122/postlayout/preflight.json) · [Recibo](../build/phase3/strongarm_isolated_and_native_ff_20261122/postlayout/simulation.json)

| Ciclo | Linha | D na captura (V) | Q após captura (V) | Q/QB da célula, antes → depois | Captura (ns, eixo C250) | Margem conjunta SA/SAB e D | Resultado |
|---:|---:|---:|---:|---|---:|---:|---|
| 15 | 2 | 1,80008 | 1,80000 | 1/0 → 1/0 | 200,058 | 5,229 ns | PASS |
| 16 | 3 | −0,000052 | 0,000015 | 0/1 → 0/1 | 220,058 | 5,046 ns | PASS |
| 17 | 3 | −0,000048 | ≈0 | 0/1 → 0/1 | 240,058 | 5,072 ns | PASS |

Em SCLK50, BLB−BL foi −598 mV, +407 mV e +421 mV em c15–17. Os dois estágios internos recuperaram a polarização de reset em 204,483 / 224,471 / 244,469 ns; BL/BLB recuperaram em 204,719 / 224,713 / 244,714 ns. A margem é contada a partir do primeiro ponto do sufixo em que SA, SAB e D ficam nas bandas corretas até a captura. O gráfico pareia o núcleo esquemático e o extraído na mesma coluna. [Medições](../build/phase3/strongarm_isolated_and_native_ff_20261122/postlayout/analysis.json) · [Gráfico comparativo](../build/phase3/strongarm_isolated_and_native_ff_20261122/postlayout/poslayout_tt_comparativo.png)

| Métrica em c15–17 | Núcleo esquemático | Núcleo extraído |
|---|---:|---:|
| Margem mínima conjunta | 5,267 ns | 5,046 ns |
| Pico do tail, `abs(Id)` | 88,6–88,8 µA | 108,4–110,4 µA |
| Sobreposição tail/reset na avaliação, marcador 1 µA | 388–400 ps | 332–333 ps |
| Fração de carga do tail no intervalo | ~95% | 33–34% |
| Sobreposição tail/reset na descida | 95–96 ps | 69–81 ps |
| Sobreposição tail/pré-carga na descida, marcador 1 µA | Ausente | Ausente |

A corrente do tail aumentou e a margem mínima caiu 0,221 ns, com D/Q corretos e recuperação observada. A sobreposição usa correntes de dreno em módulo e informa simultaneidade. Os valores não separam a carga útil dos nós internos de eventual condução simultânea pelo reset. A bancada mantém SCLK imposto na porta externa da folha e trilhos ideais. Ela exercita o RC interno dos cinco gates e a coluna ativa, com alcance limitado para carga no acionador compartilhado, droop, couplings externos e regressão de outros bits.

## 4. Decisão e próxima sequência

Priorize um único ECO físico experimental, em cópia de C, para as colunas 3, 6 e 7. As três substituições cobrem as falhas TT e FF demonstradas. A correção de FF pelo StrongARM nos bits 6 e 7 ainda precisa de teste. Começar por essas colunas também limita o salto de carga em SCLK. Avalie a alternativa uniforme de oito células depois de medir a distribuição no novo PEX. Preserve os outros cinco caminhos inicialmente.

A folha está apta a um estudo de integração experimental. Dimensionamento, circuito de reset e buffers devem permanecer rastreáveis. O risco de colocação inclui a acomodação dos sete pinos no pitch, capacitância/acoplamento em SCLK e saídas, droop e retorno local, relação com PRECH, slew e contenção. Os 13,20 fF incidentes da folha e seus gates modelados orientam a avaliação. A carga efetiva de múltiplos sentidos deve ser medida no novo PEX com o acionador e as outras redes conectadas.

Após o ECO físico em cópia, gerar GDS e LEF, conferir DRC, LVS único e PEX rastreado. Validar C250 e a fixture integrada nas três variantes TT/SS/FF, incluindo palavras completas, escritas, retenção, recuperação, handoff e captura. Só então medir timing, energia e demais requisitos para caracterização e Liberty.

## 5. Preservação e reprodução

A branch `integration/phase3-danilo-ss`, o HEAD `8e1d961`, as vistas físicas de C e o checkpoint anterior foram preservados. C mantém `FAIL` TT, `PASS` SS no escopo histórico e `NOT_CHARACTERIZED`. Monte Carlo experimental e Liberty mantêm seus estados anteriores. O controle C250 estabelece o FAIL FF nesta fixture. A verificação integrada equivalente de 370 ns em FF continua pendente. As demais verificações da rodada tratam a folha isolada. Os decks originais podem ser repetidos em cópias, com os mesmos hashes de PDK, via comandos e recibos do pacote. [Reprodução](../build/phase3/strongarm_isolated_and_native_ff_20261122/REPRODUCAO.md) · [Testes](../build/phase3/strongarm_isolated_and_native_ff_20261122/test_evidence.log) · [Preservação e checkpoints](../build/phase3/strongarm_isolated_and_native_ff_20261122/preservation.log)
