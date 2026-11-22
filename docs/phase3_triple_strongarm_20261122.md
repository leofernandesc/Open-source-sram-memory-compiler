# Fase 3 · Três StrongARM na SRAM 4×8

**O ECO virtual corrigiu todas as palavras do C250 em TT, SS e FF. A nova macro passou no primeiro FF pós-layout**, com as seis escritas e os dados das células preservados. As três substituições corrigiram os erros conhecidos dos bits 3, 6 e 7 na janela ensaiada. A geometria experimental de 540 × 380 µm passou em DRC e LVS, e o PEX foi extraído desse mesmo GDS. [Gate virtual](../build/phase3/strongarm_triple_20261122/virtual_gate.json) · [Resultado FF pós-layout](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/analysis.json)

## Resultado funcional virtual

| Corner | C original | ECO de um StrongARM | ECO de três StrongARM |
|---|---|---|---|
| TT | FAIL c16 e c17 | PASS no C250 | **PASS** |
| SS | PASS no teste integrado histórico | PASS no C250 | **PASS** |
| FF | FAIL c15, c16 e c17 | FAIL c15 | **PASS** |

Em todos os três ensaios virtuais, as quatro palavras estiveram estáveis nos prazos do C250. As seleções de linha, os valores em D na borda local de captura e as palavras em Q e DATA foram verificadas para os oito bits. Os cinco senses originais dos bits 0, 1, 2, 4 e 5 acertaram as quatro leituras nos três corners. A janela de recuperação foi observada para os três StrongARM, incluindo SA/SAB, intermediários e BL/BLB. Os pares Q/QB das 32 células 6T foram observados após cada uma das seis escritas até a escrita seguinte da mesma linha ou até 245,55 ns. Todos os pares se mantiveram dentro das bandas esperadas nos pontos amostrados. [FF](../build/phase3/strongarm_triple_20261122/FF/analysis.json) · [TT](../build/phase3/strongarm_triple_20261122/TT/analysis.json) · [SS](../build/phase3/strongarm_triple_20261122/SS/analysis.json)

| Ciclo | Linha | Esperado | C original FF | Virtual TT | Virtual SS | Virtual FF |
|---:|---:|---|---|---|---|---|
| 14 | 1 | `0xAA` | `0xAA` | `0xAA` | `0xAA` | `0xAA` |
| 15 | 2 | `0x0F` | `0xCF` | `0x0F` | `0x0F` | `0x0F` |
| 16 | 3 | `0xF0` | `0xF8` | `0xF0` | `0xF0` | `0xF0` |
| 17 | 3 | `0xF0` | `0xF8` | `0xF0` | `0xF0` | `0xF0` |

### Efeito da carga compartilhada

O PEX de cada célula foi preservado bit a bit, com os cinco gates do tail e reset conectados ao SCLK real extraído. Os seis buffers `buf_1` ligam SA/SAB aos percursos legados. Foi removido apenas o conjunto ativo dos três senses e os 22 capacitores das três caudas antigas já desligadas. Todos os demais cartões da macro ficaram idênticos. A decisão sobre as placas dos capacitores, conexões por bit, grupos WL e mapeamento até mux/FF são reprodutíveis. [Auditoria do híbrido](../build/phase3/strongarm_triple_20261122/model_audit.md) · [Mapa de conectividade](../build/phase3/strongarm_triple_20261122/FF/map.json) · [Diff do binding](../build/phase3/strongarm_triple_20261122/FF/binding.diff)

| Corner | Menor margem conjunta SA/SAB e D | SCLK50 no tronco em c15, diferença vs. ECO de uma célula | Pico do tail entre as três células | Sobreposição tail/reset na subida |
|---|---:|---:|---:|---:|
| FF | 6,143 ns | +61,7 ps | 130,4–138,9 µA | 479–542 ps |
| TT | 4,660 ns | +76,1 ps | 95,9–105,9 µA | 357–370 ps |
| SS | 1,896 ns | +99,2 ps | 59,3–74,5 µA | 119–121 ps |

A referência FF nativa indica +59,2 ps em SCLK50 no mesmo c15, e a referência TT nativa indica +72,5 ps. As sondas dos cinco senses originais também observaram o atraso do tronco. A maior mudança interpolada em SCLK50 dos samplers remanescentes versus o ECO único foi de aproximadamente 62 ps em FF, 76 ps em TT e 100 ps em SS. As palavras permaneceram corretas. SCLK está acompanhado desde o tap 80, por READ_Q, NAND interno e tronco de saída `rc8562`, até os cinco gates de cada nova célula. Os brackets amostrais constam nos JSONs. As diferenças interpoladas abaixo do intervalo de amostragem descrevem o alinhamento observado, com resolução limitada.

Os gráficos e os waveforms registram as correntes de dreno dos oito dedos do estágio de saída AND2_4. A soma simultânea dos módulos de Id chegou a aproximadamente 1,30 mA em FF, 1,08 mA em TT e 0,83 mA em SS nas janelas das leituras. Essa soma serve como indicador de atividade e inclui contribuições de dispositivos em sentidos distintos. O risco residual mais claro no híbrido FF é a simultaneidade entre tail e pré-carga de aproximadamente 15–17 ps durante a queda, ao marcador diagnóstico de 1 µA. A carga do tail durante essas janelas foi de aproximadamente 0,027–0,035 fC. Houve recuperação e retenção, e a energia correspondente aos mecanismos de transferência segue sem separação quantitativa. [FF c15](../build/phase3/strongarm_triple_20261122/FF/c15_strongarm.png) · [TT c16](../build/phase3/strongarm_triple_20261122/TT/c16_strongarm.png) · [SS c16](../build/phase3/strongarm_triple_20261122/SS/c16_strongarm.png)

### Recibos e integridade

Um transiente por corner, 250 ns, SKY130A, 1,8 V, 27 °C, Gear/KLU, máximo de 25 ps e a fixture histórica idêntica. Cada corner teve retorno 0 e seu manifesto conferiu 319 arquivos dos modelos. Os três transientes consumiram aproximadamente 2 h 22 min acumulados. Na execução FF, uma sonda herdada apontava para a antiga cauda `rc7187`. Removi a referência do comando de exportação pendente nas duas cópias localizadas na memória do processo. O recibo atesta os hashes antes/depois, e o deck originalmente lançado preserva seu hash. O ngspice integrou uma única vez os 250 ns com o circuito e os estímulos congelados. Os decks de reprodução, TT e SS removem a sonda também da lista de observação inicial. [Recibo de recuperação](../build/phase3/strongarm_triple_20261122/FF/export_recovery.json) · [Diff de reprodução](../build/phase3/strongarm_triple_20261122/FF/export_reproduction.diff) · [Recibo FF](../build/phase3/strongarm_triple_20261122/FF/simulation.json) · [Recibo TT](../build/phase3/strongarm_triple_20261122/TT/simulation.json) · [Recibo SS](../build/phase3/strongarm_triple_20261122/SS/simulation.json)

## Implementação física experimental

O GDS da variante mantém o contorno de **540 × 380 µm** e as instâncias, metal e formas do nível superior de C. Foi atualizada somente a estrutura `leaf_fabric`, preservando 32 bitcells, cinco senses antigos, 80 estágios e a interface pública. No interior do fabric, a faixa acima dos senses originais acomodou os núcleos de 28,770 × 18,195 µm e as seis células de saída. BL/BLB conectam os pares existentes às portas em metal2. As conexões de SCLK e VDD usam trilhas locais e as redes nativas. As alimentações dos buffers usam os retornos locais e taps SKY130 abutidos. O SA de cada coluna chega ao acesso DOUT de C. O SAB tem buffer explícito e termina em rota local. [Mapa de colocação](../build/phase3/strongarm_triple_20261122/physical/fabric_v6/placement.json) · [Auditoria GDS](../build/phase3/strongarm_triple_20261122/physical/macro_v6/merge.json)

A revisão da montagem reimportada identificou sobreposições M4 das primeiras rotas locais com o nível superior, além de folga `licon.11` nos seis buffers, mesmo com DRC limpo no fabric antes da integração. Na revisão verificada, três escapes foram deslocados e os buffers foram ligados às colunas de VSS já presentes. Para cumprir a folga após a reimportação, quatro contatos externos dos drenos/fontes PMOS de cada buffer foram afastados 10 nm dos gates, com extensão correspondente da difusão. A geometria dos gates e os W/L ficaram iguais. O teste de sobreposição entre metal novo e metal diretamente no nível superior deu área zero. Magic 8.3.703, com o mesmo deck SKY130A, verificou **DRC zero** no GDS completo reimportado. O Netgen retornou **correspondência única**, sem erros de propriedade. O netlist extraído do GDS contém 1.785 MOS. [DRC da macro](../build/phase3/strongarm_triple_20261122/physical/macro_v6/gds_check/magic.log) · [LVS da macro](../build/phase3/strongarm_triple_20261122/physical/macro_v6/gds_check/lvs_verified.log) · [Recibo de geometria](../build/phase3/strongarm_triple_20261122/physical/macro_v6/gds_check/results.json)

O LEF da variante foi revalidado contra o GDS. Os 16 acessos públicos se mantêm em metal real. As obstruções existentes cobrem toda a geometria nova, mantendo as mesmas coordenadas de pinagem e obstrução. [LEF](../build/phase3/strongarm_triple_20261122/physical/macro_v6/sram_4x8.lef) · [Recibo do LEF](../build/phase3/strongarm_triple_20261122/physical/macro_v6/lef_delta.json)

### Extração da geometria verificada

O PEX distribuído contém **1.785 MOS, 16.442 resistores e 12.612 cartões de capacitância**, dos quais 10.556 têm valor positivo. O Magic exportou as 16 portas com a alimentação primeiro. A cópia de simulação usa a ordem de portas da fixture histórica. O teste compara todos os cartões fora do cabeçalho e confirma identidade nessa normalização. A restauração de 92 contribuições subattofarad recuperou 0,04869 fF dos dados brutos do Magic. A soma por par de redes coincidiu com a exportação capacitiva da mesma geometria nos 5.247 pares, dentro do critério do auditor. A contração resistiva do PEX recuperou 748 redes dos terminais dos transistores, com VDD e VSS separados. O Netgen comparou essa visão do PEX com o esquema do ECO e retornou correspondência única. O hash do GDS no recibo da extração é o mesmo do GDS aprovado em DRC/LVS. [Manifesto do PEX](../build/phase3/strongarm_triple_20261122/physical/pex_verified/manifest.json) · [Auditoria de capacitância](../build/phase3/strongarm_triple_20261122/physical/pex_verified/capacitance_audit.csv) · [LVS da visão DC do PEX](../build/phase3/strongarm_triple_20261122/physical/pex_verified/dc_lvs.log)

A capacitância explícita incidente em toda a rede SCLK passou de 134,40 para 151,21 fF. O acoplamento extraído entre SCLK e PRECH permaneceu próximo de 7,54 fF. As seis bitlines modificadas têm 55,70–65,78 fF de capacitância explícita incidente, frente a 59,21–68,65 fF em C. As somas contam as placas que cruzam os grupos resistivos e excluem as capacitâncias intrínsecas dos MOS. A resposta dinâmica depende da impedância distribuída, dos estados dos dispositivos e das bordas nas outras redes. [Inventário extraído C e geometria nova](../build/phase3/strongarm_triple_20261122/physical/extracted_loads.json)

### Primeiro transiente da macro pós-layout

**FF C250 pós-layout `TRIPLE_STRONGARM_FF_PASS`.** A única execução usou SKY130A FF, 1,8 V, 27 °C, Gear/KLU e passo máximo de 25 ps. Os 250 ns terminaram em 46 min 34 s, com 15.549 amostras e nenhum erro registrado. O mesmo observador do ECO virtual conferiu sinais de escrita, seleção de endereço e WL, D até a captura local de cada bit, Q após a captura e DATA nos dois instantes de verificação. Os pares Q/QB observados das 32 células permaneceram corretos nas janelas de retenção após as seis escritas. SA/SAB, nós intermediários e BL/BLB dos três StrongARM recuperaram até 3,49 ns depois de cada início de fase baixa do CLK público. No último ciclo, todos esses nós já haviam recuperado até 243,482 ns. [Recibo](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/simulation.json) · [Waveform](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/waveform.dat) · [Tabela dos oito bits](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/lanes.csv)

| Ciclo | Esperado | D na captura | Q após captura | DATA | Margem mínima conjunta SA/SAB e D nos três StrongARM |
|---:|---|---|---|---|---:|
| 14 | `0xAA` | `0xAA` | `0xAA` | `0xAA` | 6,159 ns |
| 15 | `0x0F` | `0x0F` | `0x0F` | `0x0F` | 6,132 ns |
| 16 | `0xF0` | `0xF0` | `0xF0` | `0xF0` | **6,116 ns** |
| 17 | `0xF0` | `0xF0` | `0xF0` | `0xF0` | 6,144 ns |

O SCLK50 do tronco em c15 ocorreu em 193,222550 ns, 21,8 ps depois de C FF e 37,4 ps antes do híbrido de três células. Para as quatro leituras, o slew 20–80% do tronco ficou entre 551 e 559 ps na subida e entre 185 e 187 ps na descida. As três bordas locais permaneceram no mesmo intervalo amostral do tronco e entre si. A interpolação os coloca cerca de 0,8 ps depois do tronco no cruzamento de 50%, abaixo da resolução local da comparação. Nos outros cinco senses, a decisão foi correta e sustentada nas quatro leituras. [Comparativo pareado C, ECO único, ECO triplo e pós-layout](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/ff_pareado.png)

Os picos de Id do tail ficaram entre **148,8 e 158,7 µA**, acima dos 130,4–138,9 µA do híbrido FF. Na subida, houve simultaneidade tail/reset de 453–468 ps, com 42,9–45,7 fC de carga de tail nessas janelas. A soma simultânea dos módulos de Id dos dedos de saída do AND2_4 atingiu 1,28 mA. Na queda, as sondas do tail e dos dispositivos de pré-carga e equalização da coluna, com o marcador diagnóstico de 1 µA, ficaram sem simultaneidade detectada nas 12 combinações leitura/coluna. As medições observam corrente de dreno, dependem da amostragem e incluem a carga dos nós que comutam. Os picos e a simultaneidade na subida ainda requerem avaliação elétrica sob os demais corners e no ensaio integrado. [Correntes](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/currents.dat) · [c15](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/c15_strongarm.png) · [c16](../build/phase3/strongarm_triple_20261122/physical_qualification/FF/c16_strongarm.png)

| Entrega física experimental | Situação |
|---|---|
| [GDS integrado](../build/phase3/strongarm_triple_20261122/physical/macro_v6/sram_4x8.gds) e layout Magic | Implementados, 540 × 380 µm |
| LEF | Conferido contra o GDS e lido pelo OpenROAD, 16 pinos e contorno preservado |
| DRC no GDS reimportado | PASS, zero violações |
| LVS no GDS e na visão DC do PEX | PASS, correspondência única |
| PEX vinculado ao GDS | Disponível, SHA-256 `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` |
| FF pós-layout | PASS nas quatro leituras e seis escritas da fixture C250 |
| TT/SS pós-layout e ensaio integrado | Pendentes |

## Pendências e preservação

A qualificação geral permanece `NOT_CHARACTERIZED`. A próxima etapa é rodar TT e SS pós-layout com esse PEX congelado, seguida da fixture integrada de 18 ciclos em TT, SS e FF, com atenção à transição de propriedade do barramento, à desativação de drivers e à recuperação. A caracterização pede acesso da palavra completa, setup, hold, potência estática, potência/energia dinâmica, SNM no domínio aplicável e cobertura PVT, slew e carga para as tabelas de Liberty. A especificação ainda exige resultados para 8×8 e 32×8, e a temperatura nominal de caracterização segue pendente de confirmação. [Especificação](../specs/technical_specification.md)

A macro C, seu PEX, o ECO de uma célula, o StrongARM isolado, os arquivos locais e o checkpoint estão preservados. O trabalho permanece na branch `integration/phase3-danilo-ss` e HEAD `8e1d961`. Oito testes de software conferiram conectividade, fixture, sondas, selos e observação. Foram executados quatro transientes completos nesta rodada. [Reprodução](../build/phase3/strongarm_triple_20261122/REPRODUCAO.md) · [Recibo de preservação](../build/phase3/strongarm_triple_20261122/preservation.log)
