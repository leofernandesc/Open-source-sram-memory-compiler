# Fase 3 · Contraste TT de rebalanceamento das saídas do sense 3

**Veredito · `REBALANCE_NOT_SUFFICIENT`.** Dois buffers SKY130 casados desacoplaram a rota identificável do mux com SCLK nominal. O circuito preservou c15 e a recuperação, mas o latch ainda inverteu para a decisão incorreta em c16 e c17. Em ambos, o mux recebeu essa decisão e D ficou alto até a captura. O resultado vale para este par de buffers e esta fronteira no recorte de 59 ns. [Revisão arquitetural](phase3_revisao_arquitetural_sense_sky130_20261121.md) · [Análise pareada](../build/phase3/sense3_rebalance_tt_20261121/analysis.json)

## A. Fronteira elétrica e carga

O preflight comparou o PEX selado de C e o recorte validado. `_40_.A1.t3/.t4` correspondem a `rc5994/rc5995` e carregam os gates de X173 e X920. Além desses gates, os únicos cartões incidentes aos dois terminais são R2619, R2620, R2621, C10212 e C10213. Nenhuma fonte de replay incide nos terminais. As conexões de R2619 e R2621 que chegavam a SA (`rc5990`) passaram para a saída `mux_feed`. R2620, os dois gates e os cartões C10212/C10213 mantiveram seus terminais e valores. O marcador `**FLOATING` nos comentários do PEX acompanha cartões que permanecem fisicamente conectados pela rede resistiva. Nenhum outro cartão do recorte foi editado. [Preflight com cartões antes/depois](../build/phase3/sense3_rebalance_tt_20261121/preflight.json)

| Componente | SA original | SA após inserção | SAB original | SAB após inserção | Evidência e destino |
| --- | ---: | ---: | ---: | ---: | --- |
| MOS do latch e samplers | Intrínseca por modelo | Mesmos cartões | Intrínseca por modelo | Mesmos cartões | W/L e parâmetros extraídos preservados. C efetiva depende da polarização. |
| NTAIL, cartões explícitos | 0,324 fF | 0,324 fF | 1,006 fF | 1,006 fF | Preservados no latch. |
| Grupo SCLK | 4,287 fF | 4,287 fF | 1,617 fF | 1,617 fF | `C178 rc8562 rc5990 4.28661f` e C155 preservados. |
| BL / BLB | 2,089 / 0,356 fF | iguais | 0,242 / 0,544 fF | iguais | Preservados os dois lados dos acoplamentos e o replay. |
| VSS | 6,434 fF | 6,066 fF | 3,071 fF | 3,071 fF | C10212 (0,16566) e C10213 (0,20279 fF) continuam em `rc5994/rc5995` ligados a VSS. A rota que os dirige fica a jusante. |
| VDD | 3,959 fF | 3,959 fF | 1,758 fF | 1,758 fF | Preservados. |
| Mútuo SA–SAB | 2,781 fF | 2,781 fF | 2,781 fF | 2,781 fF | Um único C, incidente aos dois nós. |
| PRECH / D e demais redes | 0,233 / 0,049 e 4,261 fF | iguais | Sem cartões intergrupo | igual | Placas em SA permanecem em SA, mesmo quando pertencem ao grupo de leitura no PEX. |
| **Total explícito incidente** | **24,77220 fF** | **24,40375 fF** | **11,01917 fF** | **11,01917 fF** | Somatório por conectividade. A diferença residual é **13,38458 fF**. |
| Entrada do mux | X173/X920. A1 nominal 1,884 fF pela Liberty TT | Gates dirigidos por `mux_feed` | Ausente | Ausente | Valor de biblioteca a 25 °C como referência, sem equivalência dinâmica no recorte a 27 °C. |
| Entrada dos buffers novos | Ausente | A de `buf_1`, 2,103 fF de referência | Ausente | A de `buf_1`, 2,103 fF de referência | Subcircuitos MOS completos. A capacitância efetiva e o efeito Miller dependem da trajetória. |

Somente **0,36845 fF** explícitos acompanham o ramo desacoplado. Isso corresponde a cerca de 2,7% da diferença incidente original, além da retirada da carga direta dos gates do mux. As somas agrupam as placas pela malha resistiva, sem representar uma carga concentrada ou dinâmica. Acoplamentos nos nós centrais, inclusive com SCLK, permaneceram onde foram extraídos. Os MOS novos não têm parasitas de interconexão de uma geometria futura. O ensaio é um modelo híbrido diagnóstico. [Inventário original de C](phase3_revisao_arquitetural_sense_sky130_20261121.md#carga-desequilibrada-na-própria-geometria-c)

## B. Candidato e autorização

Foi escolhido um único par de `sky130_fd_sc_hd__buf_1` antes do run. Cada célula usa dois inversores, com NMOS `nfet_01v8` de 0,52/0,15 µm e PMOS `pfet_01v8_hvt` de 0,79/0,15 µm em cada inversor. As entradas são `rc5990` (SA) e `rc8022` (SAB). Os dois usam os mesmos VDD/VSS e bulks do recorte. A saída de SA é não inversora e chega aos dois gates A1, depois ao mesmo mux e ao nó D `rc6372`. A saída de SAB fica sem consumidor, observada apenas em tensão. Não há componente compensatório, novo controle temporal ou realimentação intencional. As condições de saída diferentes impedem afirmar casamento dinâmico perfeito das entradas. O valor de referência para a carga máxima da saída do `buf_1` na Liberty TT a 25 °C é 130,015 fF. A carga nominal de referência do mux e os 0,36845 fF de rota dão ordem de grandeza de poucos fF no lado dirigido. A verificação funcional do caminho usa o waveform, com os modelos completos. [Célula copiada do PDK](../build/phase3/sense3_rebalance_tt_20261121/buf_1.spice) · [Referências de capacitância](../build/phase3/sense3_rebalance_tt_20261121/lib_tt_reference.json)

**Gate `READY`.** PEX C `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`, controle `VALIDATED`, 319 hashes de modelos TT conferidos. As fontes e `clk_delta.spice` foram copiadas byte a byte. `VSHIFT sclk_driver rc8562 0`, R87, os sete MOS do sense e suas conexões de latch, PRECH, o histórico de BL/BLB e a referência de captura foram preservados. WL segue representada pelo replay histórico do recorte. NTAIL é um nó interno que evolui naturalmente. O preflight passou por atribuição da rota a dois terminais exatos, mesmo com a maior parte da assimetria extraída ainda presente. [Controle pré-condicionado](phase3_precondicionamento_sense3_tt_20261120.md) · [Deck](../build/phase3/sense3_rebalance_tt_20261121/run/bench.spice)

## C. Execução única e resultado

SKY130A TT, 1,8 V, 27 °C, Gear/KLU e passo máximo de 25 ps. O transiente de 59 ns cobre 188–247 ns no eixo histórico. Comando executado em `/work/build/phase3/sense3_rebalance_tt_20261121/run` no container `sram-xschem`:

```sh
timeout --kill-after=5s 120s stdbuf -o0 -e0 /opt/ngspice/ngspice-44.2/bin/ngspice -n -b bench.spice
```

Tempo medido de **66,364 s**, saída 0, **13.986 amostras** até 59 ns. Eixos de tensões e correntes idênticos, finitos e monotônicos. Deck SHA-256 `b61a430421bcb0bf51d5d7967e0bbc6515d4345d997569c0a058f2eeb055e279`, waveform `addf4c6145afce9772370b0e81be291c12c3249fc6509434532a4a20a39ff9ed`. [Comando e hashes](../build/phase3/sense3_rebalance_tt_20261121/attempt.json) · [Recibo de execução](../build/phase3/sense3_rebalance_tt_20261121/simulation.json) · [Log](../build/phase3/sense3_rebalance_tt_20261121/run/ngspice.log)

| Ciclo | Bit esperado | Controle na captura | Candidato na captura | Validade contínua até a captura (eixo histórico) | Resultado |
| --- | ---: | --- | --- | --- | --- |
| c15 | 1 | SA alto, SAB baixo, D ≈ 1,80045 V | SA alto, SAB baixo, D ≈ 1,80045 V | Par correto desde 194,700 ns. D alto desde o início observado da avaliação, 194,154 ns, até 200,058 ns | Preservado |
| c16 | 0 | SA alto, SAB baixo, D ≈ 1,80045 V | SA alto, SAB baixo, D ≈ 1,80045 V | Par e D errados sustentados desde 214,882 ns até 220,058 ns. Sem janela do zero correto em D. | Falha reproduzida |
| c17 | 0 | SA alto, SAB baixo, D ≈ 1,80045 V | SA alto, SAB baixo, D ≈ 1,80045 V | Par e D errados sustentados desde 234,905 ns até 240,058 ns. Sem janela do zero correto em D. | Falha reproduzida após recuperação de c16 |

O critério de níveis usou 20/80% de 1,8 V e sufixo válido contínuo até a referência de captura. Buffer SA e os dois gates A1 permaneceram altos durante as avaliações. Na captura, a saída SAB estava baixa. O caminho buffer→mux→D transmitiu o estado errado do latch nos c16/c17. O recorte compara D na referência de captura e deixa Q e DATA da macro fora do ensaio. [Séries pareadas](../build/phase3/sense3_rebalance_tt_20261121/paired.csv) · [Gráfico de regeneração e captura](../build/phase3/sense3_rebalance_tt_20261121/regeneracao_e_captura.png)

## D. Primeira divergência e recuperação

Os cruzamentos 20/50/80 da subida e da descida de SCLK na raiz e nos três gates preservaram o número de bordas. O maior delta estimado por interpolação foi inferior a 0,30 ps ao longo das três leituras, sem resolução física para distinguir deslocamentos sub-ps neste teste. VDD permaneceu idêntico e as fontes de replay são idênticas por hash. Diferenças amostradas nos mesmos tempos nos pontos de replay, após interpolação, ficaram abaixo de 0,24 µV. O circuito mudou ligeiramente nas bitlines locais, com maior delta do diferencial de aproximadamente 7,9 mV nas janelas de avaliação e recuperação. [Diferenças e marcadores](../build/phase3/sense3_rebalance_tt_20261121/pair_deltas.json)

| Medida, controle → candidato | c15 | c16 | c17 |
| --- | --- | --- | --- |
| NTAIL anterior à avaliação (V) | 1,433247 → 1,433247 | 1,148267 → 1,148274 | 1,147638 → 1,147619 |
| BLB−BL no primeiro tail de 1 µA (mV) | −161,29 → −160,95 | +146,51 → +146,53 | +157,16 → +157,18 |
| Modo comum no mesmo marco (V) | 1,78512 → 1,78534 | 1,78824 → 1,78828 | 1,78062 → 1,78066 |
| SAB−SA no mesmo marco (mV) | −97,75 → −94,91 | +48,20 → +48,44 | +53,86 → +54,14 |
| Pico de X235 / X521 (µA) | 11,09 / 23,50 → 11,18 / 24,34 | 30,68 / 6,28 → 30,72 / 6,43 | 31,22 / 6,32 → 31,26 / 6,49 |
| Pico de X351 (µA) | 143,28 → 147,94 | 133,23 → 136,51 | 133,18 → 136,42 |
| Primeira inversão desfavorável de SAB−SA (ns) | Ausente → ausente | 214,587 → 214,628 | 234,597 → 234,645 |

c16 e c17 começaram a separar na direção favorável em 214,173 e 234,163 ns com os buffers. Depois, a polaridade inverteu cerca de **41 ps e 48 ps** mais tarde que no controle. BLB−BL ainda era positivo, aproximadamente +774 e +821 mV nas inversões do candidato. O ganho de tempo observado não evitou a inversão. A primeira divergência funcional continua sendo a regeneração. A comparação altera tanto a conexão de carga quanto os dispositivos dinâmicos na saída. Os buffers compartilham os trilhos do recorte e o ensaio não separou seu consumo de alimentação. Ela não isola um mecanismo de offset ou acoplamento específico.

Na recuperação, o último cruzamento de X351 para abaixo de 1 µA antecedeu o primeiro cruzamento para cima, entre X1352, X1645 e X374, em cerca de 170/174/174 ps para c15/c16/c17. No intervalo da captura até o fim da recuperação de cada leitura, não houve sobreposição pelo marcador escolhido no candidato. O marcador é diagnóstico. As correntes de PRECH/equalizador não foram gravadas no controle arquivado. A comparação com o controle usa os gates, a corrente de tail, o retorno de BL/BLB e SA/SAB à faixa alta e o NTAIL anterior à leitura. O candidato recuperou essa faixa alta em 204,955, 224,766 e 244,762 ns, próximo do controle. Saídas de buffer no ciclo completo apresentaram SA alto e SAB alto→baixo→alto nas três leituras, sem pulsos lógicos extras observados. [Correntes e recuperação](../build/phase3/sense3_rebalance_tt_20261121/analysis.json)

## E. Decisão e preservação

1. **O ramo do mux foi desacoplado.** Os gates de A1 e 0,36845 fF explícitos são dirigidos pelo buffer. C178 e os demais acoplamentos centrais permaneceram.
2. **O desbalanceamento explícito caiu pouco.** Restaram 13,38458 fF de diferença incidente antes de considerar os MOS. A comparação não demonstra equilíbrio elétrico dinâmico.
3. **As duas leituras TT continuaram erradas.** O par se separou inicialmente no sentido correto e inverteu antes da captura.
4. **O caminho até D permaneceu funcional.** D manteve o valor que o latch produziu, alto em todos os três ciclos.
5. **Nenhum problema novo de recuperação foi demonstrado no recorte.** A pré-carga posterior ficou separada da condução do tail pelo marcador adotado.
6. **Sem suporte para implementar fisicamente este candidato.** O resultado delimita a eficácia do desacoplamento do mux neste ponto. Continua aberta a influência do restante da assimetria, incluindo os acoplamentos locais que ficaram em SA. O v2 continua como referência experimental de correção no recorte.

Recriar o deck e a análise em uma cópia, sem executar SPICE, reproduziu os arquivos byte a byte. O trabalho ocorreu em `build/phase3/sense3_rebalance_tt_20261121/`, com um único candidato, um único transiente e nenhum ajuste após observar o resultado. Nenhum artefato histórico, GDS, LEF ou PEX foi modificado. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961`, sem commit, push ou merge. C permanece em `FAIL` TT e `PASS` SS no escopo ensaiado. FF integrado e Liberty pendentes. Monte Carlo `tt_mm` experimental concluído, homologação pendente. Qualificação elétrica `NOT_CHARACTERIZED`.
