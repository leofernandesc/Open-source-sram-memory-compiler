# P5 — piloto de tACCESS na v6 física

Data: 25/11/2026. O relatório reprodutível é [`build/phase3/timing_v6_247p5_access.json`](../build/phase3/timing_v6_247p5_access.json), SHA-256 `4534be238aaf2c9cf53eefb04b6cfa23e8587ca129c682ea73b716af919f36cf`.

Para cada uma das nove leituras integradas por corner, o valor foi calculado como o instante mais tardio em que `DATA[7:0]` satisfaz os limites de validade do observador menos a subida pública de CLK registrada na fixture. Todas as 72 lanes/corner usadas no cálculo têm veredito funcional `PASS`. A medição corresponde à PEX física v6, a 1,8 V e 27 °C, com carga integrada de 10 fF por lane e período de 20 ns.

| Corner | Leituras | tACCESS mínimo | tACCESS médio | tACCESS máximo |
|---|---:|---:|---:|---:|
| TT | 9 | 10,067 ns | 10,509 ns | 10,651 ns |
| SS | 9 | 10,079 ns | 10,740 ns | 10,951 ns |
| FF | 9 | 10,059 ns | 10,384 ns | 10,490 ns |

Estes números são observações do estímulo integrado, sem sweep de carga/slew, sem busca de setup/hold e sem amostragem estatística. O gate funcional de cada leitura passou. Os valores continuam `PROVISIONAL`; não estabelecem limite máximo público, frequência máxima nem timing Liberty. O relatório também inclui um piloto do pedido combinado CSb/OEb de idle até a primeira amostra nativa de liberação sustentada: TT 553,148 ps, SS 685,168 ps e FF 460,229 ps. Ele usa uma única troca read→idle por corner, carga integrada de 10 fF e sonda fraca de 1 kΩ, com release mantido até o fim da janela. Não separa os arcos CSb, OEb e WEb. Um piloto de `tCLK_TO_DATA` foi extraído depois, apenas nos lanes que transitam após a descida pública de CLK; não substitui os sweeps de carga/slew nem o timing qualificado por arco. tDIS isolado por controle, setup/hold e arcos adicionais permanecem pendentes. O piloto de liberação está em [`timing_v6_idle_release.json`](../build/phase3/timing_v6_idle_release.json), SHA-256 `b42d905275bc8620a04b5b07f152083fd5a1577b9da439445d2aa5ab1c1823fd`.

