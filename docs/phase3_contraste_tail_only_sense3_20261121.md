# Fase 3 — Contraste causal exclusivo do tail do sense 3

**`TAIL_ONLY_NOT_SUFFICIENT` em TT, para +182 ps no recorte validado.** O atraso chegou ao gate do tail em c16 e c17 e os samplers permaneceram equivalentes ao controle. Nas duas leituras, o par regenerativo separou-se primeiro na direção esperada, inverteu depois e manteve D incorreto até a referência de captura. A intervenção deslocou a inversão em aproximadamente 179 ps. O contraste histórico que atrasou os três gates corrigiu ambas as leituras no mesmo recorte. [Análise pareada](../build/phase3/sense3_tail_only_20261121/analysis.json) · [Contraste anterior](phase3_precondicionamento_sense3_tt_20261120.md)

## Préflight e execução

Foi reaproveitado o controle histórico `VALIDATED`, com waveform completo de 13.980 amostras, SHA-256 `5954927da87434f44fe067d422c9e55769b62051d01225ef9587ed9ea6199fd5`. O recorte contém 36 MOS, 493 resistores e 968 capacitores do PEX de C `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`. SKY130A TT, 1,8 V, 27 °C, Gear/KLU, tolerâncias originais, passo máximo de 25 ps e 319 arquivos na cadeia de modelos verificada. O tempo local de 0–59 ns corresponde a 188–247 ns no transiente TT arquivado. [Gate histórico](../build/phase3/sense3_preconditioned_20261120/control_gate.json) · [Préflight](../build/phase3/sense3_tail_only_20261121/preflight.json)

| Ramo extraído | Destino | Resistência | C extraído no gate |
|---|---|---:|---:|
| R68 | `rc8584`, sampler BL `X235` | 566,852 Ω | 0,04755 fF para VSS |
| R60 | `rc8586`, sampler BLB `X521` | 567,159 Ω | 0,04776 fF para VSS |
| R76 | `rc8585`, tail `X351` | 387,618 Ω | 0,03810 fF para VSS |

Os três ramos saem de `rc8571`, que recebe SCLK de `rc8562` por `R87` de 6,46438 Ω. A capacitância extraída do ponto comum para VSS é 1,30555 fF. No PEX, o gate do tail só tem ligação direta ao resistor, ao seu capacitor para VSS e a X351. A impedância compartilhada e a realimentação pelos MOS ainda podem transmitir parte da perturbação aos samplers. O recorte reproduz o SCLK da rede compartilhada por replay na fronteira `rc8562`. A fonte histórica de 0 V em série antes de R87 e todas as conexões físicas de PRECH, gates, latch e captura foram mantidas. [Auditoria temporal TT × SS](phase3_auditoria_temporal_tt_ss_20261121.md) · [Préflight](../build/phase3/sense3_tail_only_20261121/preflight.json)

O único edit no recorte derivado foi trocar o terminal a montante de `R76` por `tail_series` e ligar `VTAIL` entre esse nó e `rc8571`. A fonte está em série, antes de R76. Ela preserva o caminho de corrente para o ponto comum, o valor do resistor, o gate e sua carga. Sua tensão é a diferença entre a trajetória histórica do ponto comum atrasada em 182 ps e a original, com junções de 25 ps e pulso restrito a 213,85–216,35 ns e 233,85–236,35 ns. O comando é zero em c15 e durante as descidas. `stimuli.spice` e `bench.spice` são idênticos ao controle. É um diagnóstico idealizado no recorte.

O único processo `ngspice -n -b bench.spice` concluiu em **31,75 s** com limite de 90 s, ngspice 44.2, retorno 0 e 14.740 amostras até 59 ns. O waveform tem SHA-256 `2b0ca2000b7d92c2ada8b9246a2f02dd09b3475d19d745ef6ca4bf97d7381aeb`. [Deck experimental](../build/phase3/sense3_tail_only_20261121/contrast/slice.spice) · [Fonte em série](../build/phase3/sense3_tail_only_20261121/contrast/clk_delta.spice) · [Recibo](../build/phase3/sense3_tail_only_20261121/contrast/result.json)

## Isolamento e descida

Foram usados os envelopes históricos de +182 ±25 ps na subida do tail e 0 ±25 ps nas bordas preservadas. Os marcadores 20/50/80% são referidos a 1,8 V. Os deltas abaixo são calculados por interpolação linear dos pontos nativos. Valores sub-ps descrevem a diferença entre as curvas simuladas, com a resolução temporal condicionada pela malha do transiente.

| Ciclo e sinal | Controle, subida 20/50/80% (ns) | Δ subida (ps) | Controle, descida 80/50/20% (ns) | Δ descida (ps) |
|---|---|---|---|---|
| c16 sampler BL | 214,156 / 214,408 / 214,807 | 0,000 / −0,053 / +0,371 | 224,071 / 224,161 / 224,270 | ≈0 / ≈0 / ≈0 |
| c16 sampler BLB | 214,155 / 214,409 / 214,807 | −0,001 / −0,084 / +0,048 | 224,071 / 224,161 / 224,270 | ≈0 / ≈0 / ≈0 |
| c16 tail | 214,154 / 214,408 / 214,807 | +181,978 / +181,996 / +182,051 | 224,071 / 224,161 / 224,270 | ≈0 / ≈0 / ≈0 |
| c17 sampler BL | 234,155 / 234,408 / 234,806 | −0,001 / −0,055 / +0,366 | 244,069 / 244,159 / 244,269 | ≈0 / ≈0 / ≈0 |
| c17 sampler BLB | 234,155 / 234,409 / 234,807 | −0,001 / −0,084 / −0,007 | 244,069 / 244,159 / 244,269 | ≈0 / ≈0 / ≈0 |
| c17 tail | 234,154 / 234,408 / 234,806 | +181,971 / +181,996 / +182,087 | 244,069 / 244,159 / 244,268 | ≈0 / ≈0 / ≈0 |

Os deltas de 20/50/80% em SCLK compartilhado e PRECH ficaram abaixo de 0,006 ps. A diferença máxima nas formas de onda ficou em 0,018 mV no ponto comum, 0,65/0,93 mV nos gates dos samplers e 0,001 mV nas fontes de BL/BLB, PRECH e VDD. O slew de subida do tail mudou até 0,12 ps. A pequena excursão anterior à subida, de aproximadamente −8 a −9 mV, já estava presente no controle e também se deslocou. No seu mínimo, o módulo da corrente medida ficou abaixo de 0,1 pA nos dois decks. A queda observável em 90% continuou em 224,037 ns no c16 e 244,035 ns no c17. [Medições e séries pareadas](../build/phase3/sense3_tail_only_20261121/analysis.json) · [CSV](../build/phase3/sense3_tail_only_20261121/paired.csv)

## Regeneração e captura

| Medição | c16 controle → tail atrasado | c17 controle → tail atrasado |
|---|---|---|
| NTAIL inicial antes da subida pública (V) | 1,148267 → 1,148267 | 1,147638 → 1,147638 |
| BL / BLB em SCLK20 do tail (V) | 1,865 / 1,880 → 1,605 / 1,842 | 1,859 / 1,880 → 1,591 / 1,840 |
| BLB−BL e modo comum em SCLK20 | +15,4 mV e 1,873 V → +237,2 mV e 1,724 V | +20,5 mV e 1,870 V → +248,2 mV e 1,716 V |
| Tail cruza 1 µA na avaliação (ns) | 214,277 → 214,462 | 234,278 → 234,463 |
| BLB−BL no primeiro 1 µA (mV) | +146,5 → +463,6 | +157,2 → +477,4 |
| NTAIL no primeiro 1 µA (V) | 1,2318 → 1,2279 | 1,2305 → 1,2268 |
| Pico de corrente do tail (µA) | 133,23 → 135,51 | 133,18 → 135,56 |
| Separação favorável de SAB−SA na avaliação (ns) | 214,171 → 214,172 | 234,161 → 234,162 |
| Inversão de SAB−SA na avaliação (ns) | 214,587 → 214,766 | 234,597 → 234,775 |
| Captura local arquivada (ns) | 220,058 | 240,058 |
| Estado de sense e D na captura | 1 incorreto → 1 incorreto | 1 incorreto → 1 incorreto |
| Decisão errada sustentada até a captura | ≥5,26 ns → ≥5,09 ns | ≥5,24 ns → ≥5,07 ns |

O predecessor c15 continuou correto. Antes de VTAIL atuar pela primeira vez, a maior diferença em NTAIL foi 1,75 µV ao longo do replay. Em c16, a mudança de gate teve efeito na dinâmica durante a avaliação, com início de condução cerca de 185 ps mais tarde e aumento de pico de 2,28 µA. Em tempos absolutos iguais até a captura, a variação máxima de BLB−BL entre os ensaios foi 2,00 mV em c16 e 2,08 mV em c17. O diferencial maior na tabela decorre principalmente da avaliação mais tardia. O primeiro sinal favorável do latch apareceu antes do tail atrasado atingir 20%. A inversão continuou após esse marcador. D seguiu alto em ambas as capturas, por volta de 1,80045 V. A referência de captura veio da macro arquivada. Neste recorte, Q e DATA não são saídas independentes da simulação. C17 foi a segunda leitura na mesma execução. Ela reproduziu a falha com NTAIL inicial comparável. [Waveforms de regeneração](../build/phase3/sense3_tail_only_20261121/regeneration.png) · [Marcadores de corrente](../build/phase3/sense3_tail_only_20261121/tail_1ua_checkpoints.csv)

Depois da avaliação houve um segundo pulso de corrente já presente no controle. Ele ficou abaixo de 1 µA em 224,209 ns e 244,207 ns nos dois decks, cerca de 81 ps antes de PRECH cair por 80% no ponto monitorado. A BL descarregada voltou a cruzar 0,9 V em 224,547 ns e 244,545 ns, com BLB acima desse nível na recuperação. Ambos os terminais retornaram para aproximadamente 1,800 V. A observação não mostrou sobreposição nova acima do marcador de corrente. Os 1 µA e os níveis de cruzamento são indicadores desta bancada.

## Alcance causal e decisão

Em c16, a combinação de atraso entregue, controle inicial compatível, samplers equivalentes e D incorreto sustenta `TAIL_ONLY_NOT_SUFFICIENT` para +182 ps. Em c17, a falha permaneceu sob o histórico produzido na própria execução. O contraste que atrasou os três gates corrigiu c16/c17 com BLB−BL de +229/+239 mV em SCLK20 do tail, ligeiramente **menor** que no contraste exclusivo. No primeiro 1 µA, o contraste conjunto também apresentou diferenciais ligeiramente menores, +458/+473 mV contra +464/+477 mV. A comparação sustenta investigar a relação entre a condução dos samplers e a ativação do tail. Diferencial maior em um marcador, sozinho, não explica o resultado. A contribuição de cada sampler e o atraso necessário para outra condição continuam em aberto.

**Próxima tarefa única** — alinhar offline controle, tail exclusivo e atraso dos três gates pelo primeiro 1 µA do tail, reconstruindo as janelas de condução dos dois samplers e a evolução de SA/SAB antes e depois desse ponto. Usar essa comparação para decidir se outra intervenção causal é justificável. A bancada de antecipação artificial de BLB−BL continua encerrada para o Marco 3. [Auditoria de fronteiras](phase3_viabilidade_fronteira_diferencial_sense3_20261121.md)

C permanece como referência de integração. Macro original TT `FAIL`, SS `PASS` no escopo ensaiado, B′ inconclusivo, driver v1 em espera, Monte Carlo experimental preservado e qualificação geral `NOT_CHARACTERIZED`. Nenhum ECO físico foi executado. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.

## Reprodução e recibos

O ZIP inclui os decks, formas de onda completas, scripts, logs e hashes. Para reproduzir apenas a análise, copiar `preflight.json` e o diretório `contrast/` para um diretório novo em `build/phase3/` e usar a fase `analyze`. O ensaio executado tem o comando SPICE no recibo e guarda de tentativa única no executor. Os ajustes de normalização do R87 histórico, arredondamento do início do eixo e serialização do resultado ocorreram no analisador offline. O deck executado permaneceu intacto. Três testes de software passaram.

```sh
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/tools \
  python3 /work/tools/phase3_sense3_tail_only.py analyze /work/build/phase3/NOVA_COPIA
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest discover \
  -s tests -p test_phase3_sense3_tail_only.py -v
```
