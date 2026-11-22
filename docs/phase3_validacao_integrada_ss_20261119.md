# Fase 3 — validação integrada da SRAM 4×8 em SS

Execução iniciada em 19/11/2026, horário de Manaus · `integration/phase3-danilo-ss` · HEAD `8e1d961`.

**Veredito integrado: INCONCLUSIVO.** O único transiente SS concluiu os 370 ns. As nove leituras entregaram as palavras corretas de forma sustentada. As seis escritas passaram e tiveram readback, cobrindo as quatro linhas. Três checks de propriedade ficaram inconclusivos porque a corrente da sonda ainda não comprovava drive prévio em quatro bits no instante programado do observador. A inspeção do waveform confirmou que os pinos atingiram os critérios de liberação antes de o host forte ligar. Qualificação elétrica geral `NOT_CHARACTERIZED`.

## A. Identidade e escopo

A bancada usa a geometria espaçada do ECO reconstruído de Danilo (`42f0b51`), com tap 48, captura ligada ao CLK público, `dfxtp_2`, drivers `ebufn_8` e DATA1 afastado de CLK. O PEX operacional é o padrão selado com 16.187 resistores. A rodada não introduz nenhuma variante de layout, de PEX ou de lógica.

| Artefato | SHA-256 |
|---|---|
| GDS reimportado | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF derivado do GDS | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| Netlist Verilog roteada | `eafcca0a89d53392e8cc1bbe380e87df8f4479f58a04a5132d62e2246d1a74a1` |
| PEX RC padrão selado | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Fixture histórica, recibo de operações | `a559e9d90c3393b614c937b1e515717be8fc4fe624fc445fb21e05c8b76ec708` |

Condições experimentais: SKY130A, SS, 1,8 V, 27 °C, 10 fF por bit, período de 20 ns, fase alta de 10 ns, slew de 50 ps, passo máximo de 25 ps e horizonte de 370 ns. ngspice 44.2 com KLU, em um CPU. O PEX existente foi extraído com Magic 8.3.703. A preparação confirmou os recibos de DRC/LVS e o LEF, o binding do PEX, a origem dos probes e o fechamento dos modelos. A fidelidade RC e os limites públicos de timing continuam pendentes. [Caracterização mínima](phase3_caracterizacao_minima_20261119.md) · [Recibo de preparação](../build/phase3/integrated_ss_20261119_preflight/preparation.json)

### Fixture e critérios

- A fixture mantém o CLK, endereço, CSb/OEb/WEb, payload forte e a ordem dos 18 ciclos históricos. Antes da simulação foram confirmadas 9 leituras, 6 escritas, 3 ciclos inativos e cobertura de readback das 4 linhas.
- As duas tomadas pelo host, em c8 e c10, têm guarda fixa de 1,5 ns desde o início da mudança dos controles. Uma sonda de 1 kΩ com fonte própria aplica a palavra oposta à leitura anterior. Ela é retirada antes de o host forte ligar. Nas três transições escrita→leitura, o desligamento do host começa 0,5 ns antes da alteração dos controles vivos. Em read→idle, a sonda permanece até antes do retorno à leitura. Os ciclos inativos iniciais têm sonda fraca conhecida depois da energização.
- A liberação exige que DATA concorde com a sonda e que as correntes da sonda e do ramo da macro fiquem em módulo ≤50 µA de forma sustentada. TE_B confirma o estado do driver. O limite de 50 µA pertence à bancada. Um intervalo diagnosticamente válido começa antes do fim do monitor, com amostras interiores. A guarda de 1,5 ns é uma condição do ensaio. O teste histórico de estresse de 300 ps e seus recibos permanecem separados.
- A leitura confere operação/endereço capturados, wordline única, sense e D na captura local, retenção de Q e palavra completa nas faixas ≤0,36 V ou ≥1,44 V. A palavra deve se manter até o início programado da sonda. Para leituras consecutivas, observa-se também a palavra anterior após a retirada do probe e antes da nova captura. Os casos sem transição atribuível podem ter palavra verificada e atraso ausente.
- A escrita exige a palavra externa na subida, DIN capturado e pronto antes de WE20, linha correta e confirmação por uma leitura posterior antes de qualquer sobrescrita da mesma linha. O readback das seis escritas cobre o armazenamento observável dos quatro endereços.
- O resultado da janela histórica de ±100 ps é registrado por bit e separado do veredito funcional. O contrato não especifica um prazo de leitura correspondente. Uma evidência insuficiente de liberação ou palavra estável recebe `INCONCLUSIVO` quando a bancada não distingue violação do protocolo de atraso na observação.

[Especificação](../specs/technical_specification.md) · [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Auditoria de critérios](phase3_auditoria_falhas_20261119.md) · [Programação da fixture](../build/phase3/integrated_ss_20261119_preflight/fixture.json)

### Reprodução

Os comandos usam o ambiente EDA do projeto e um novo diretório. A opção `simulate` aceita apenas uma tentativa por preparação. O nome `preflight` no diretório efetivo desta rodada foi mantido ao passar da preparação para a execução.

```bash
run=build/phase3/integrated_ss_repro_novo
timeout 120s tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/run_phase3_integrated_ss.py prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/run_phase3_integrated_ss.py simulate --output "$run" --timeout 2650
timeout 120s tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/analyze_phase3_integrated_ss.py "$run"
```

## B. Resultado por ciclo

Nos ciclos de escrita, o observado é DIN na ativação de WE20. A checagem também conferiu DATA na subida de CLK e o readback indicado. Nos ciclos de leitura, o observado é a palavra em DATA no fim do intervalo funcional, imediatamente antes da rampa da sonda. Os tempos usam CLK a 50%. Os ciclos 9 e 17 mantiveram o mesmo valor anterior em DATA, por isso têm estabilidade verificada e atraso de transição ausente.

| Ciclo | Operação | Endereço | Dado esperado | Dado observado | Operação | tACCESS / desde CLK↓ (ns) | Janela antiga | Propriedade |
|---:|---|---:|---|---|---|---|---|---|
| 0 | Inativo | — | — | — | PASS | — | — | PASS |
| 1 | Inativo | — | — | — | PASS | — | — | PASS |
| 2 | Escrita | 0 | 0xAA | 0xAA | PASS, readback c6 | — | — | PASS |
| 3 | Escrita | 1 | 0x55 | 0x55 | PASS, readback c7 | — | — | PASS |
| 4 | Escrita | 2 | 0x0F | 0x0F | PASS, readback c15 | — | — | PASS |
| 5 | Escrita | 3 | 0xF0 | 0xF0 | PASS, readback c16 | — | — | PASS |
| 6 | Leitura | 0 | 0xAA | 0xAA | PASS | 10,911 / 0,911 | 7/8 | PASS |
| 7 | Leitura | 1 | 0x55 | 0x55 | PASS | 10,875 / 0,875 | 7/8 | PASS |
| 8 | Escrita | 0 | 0x55 | 0x55 | PASS, readback c9 | — | — | INCONCLUSIVO |
| 9 | Leitura | 0 | 0x55 | 0x55 | PASS | Já válida antes da captura | 8/8 | PASS |
| 10 | Escrita | 1 | 0xAA | 0xAA | PASS, readback c11 | — | — | INCONCLUSIVO |
| 11 | Leitura | 1 | 0xAA | 0xAA | PASS | 10,911 / 0,911 | 7/8 | PASS |
| 12 | Inativo | — | — | — | PASS | — | — | INCONCLUSIVO |
| 13 | Leitura | 0 | 0x55 | 0x55 | PASS | 10,875 / 0,875 | 7/8 | PASS |
| 14 | Leitura | 1 | 0xAA | 0xAA | PASS | 10,911 / 0,911 | 7/8 | PASS |
| 15 | Leitura | 2 | 0x0F | 0x0F | PASS | 10,875 / 0,875 | 7/8 | PASS |
| 16 | Leitura | 3 | 0xF0 | 0xF0 | PASS | 10,911 / 0,911 | 7/8 | PASS |
| 17 | Leitura | 3 | 0xF0 | 0xF0 | PASS | Já válida antes da captura | 8/8 | PASS |

Os intervalos verificados de palavra completa vão de aproximadamente 0,564 a 1,421 ns até o início da respectiva sonda. O relatório em máquina inclui as fronteiras de cada palavra, observações de seleção/captura e os checks por bit. [Tabela CSV](../build/phase3/integrated_ss_20261119_preflight/cycles.csv) · [Checks e registro funcional](../build/phase3/integrated_ss_20261119_preflight/validation.json)

## C. Verificações e diagnóstico da propriedade

- **Leituras e linhas.** 9/9 palavras e 4/4 linhas tiveram confirmação. Endereço, operação capturada, wordline única, sense, D/Q, retenção de Q e estabilidade até o evento programado passaram no escopo de leitura. As palavras repetidas foram verificadas após a captura, sem atribuir um atraso de transição.
- **Escritas.** 6/6 escritas tiveram confirmação no readback, com 48/48 checks de DIN pronto para WE20 e 48/48 checks de corrente sustentada do host. Não foi observada escrita incorreta nem corrupção nos dados readback. O observador legado de DIN em subida+1 ns registrou 36 divergências diagnósticas e foi preservado separado.
- **Propriedade.** Os três retornos escrita→leitura, as nove máscaras de CSb e os demais intervalos monitorados passaram. Os oito checks legados de sobreposição do host forte passaram. O veredito primário de propriedade foi 15/18 ciclos PASS e três INCONCLUSIVO, nos dois read→write e no read→idle. A inspeção abaixo explica a evidência física disponível para essas três transições.
- **Prazo histórico.** Houve **65/72 PASS** na janela de ±100 ps. Os sete FAILs foram de DATA7 nos ciclos 6, 7, 11, 13, 14, 15 e 16. As sete palavras passaram no critério funcional de estabilidade. A primeira falha de janela é c6, na abertura em 140,900 ns. O projeto não estabelece essa abertura como prazo público de consumo. [Janela diagnóstica por bit](../build/phase3/integrated_ss_20261119_preflight/historical_read_window.csv)

O primeiro caso inconclusivo de propriedade foi c8 em **166,900 ns**, 100 ps antes de retirar o comando de leitura. DATA1, DATA3, DATA5 e DATA7 tinham TE_B baixo, mas a sonda retornava 14–27 µA, abaixo dos 50 µA exigidos para comprovar condução inicial. O mesmo padrão ocorreu em c10. Em c12 os bits foram DATA0, DATA2, DATA4 e DATA6, com 3–39 µA. Os três casos vêm após a restauração da leitura de uma máscara programada por CSb. O driver já tinha voltado ao estado de habilitação, mas sua ação elétrica sob a sonda oposta ainda estava se estabelecendo no ponto fixo do observador.

No trecho final imediatamente anterior à retirada da leitura, a corrente da sonda e a da macro têm sinais opostos e comprovam drive nos pinos que faltavam. Esse intervalo observado tem pelo menos 52 ps nos piores pinos, com base nas amostras do waveform. Depois da mudança de controle, todos os pinos passam a concordar com a sonda e ambas as correntes ficam abaixo de 50 µA. Esta inspeção suplementar preserva os resultados originais do observador.

| Transição | Último instante em que os oito pinos atingem o critério de liberação, sustentado até o fim do monitor | Host forte ligado | Separação observada |
|---|---:|---:|---:|
| c8, read→write | 167,716 ns | 168,528 ns | 0,812 ns |
| c10, read→write | 207,713 ns | 208,528 ns | 0,815 ns |
| c12, read→idle | 247,645 ns | — | Pinos em liberação até a descida do ciclo inativo, em 260,025 ns |

O maior valor de corrente oposta aos +200 ps do acionamento forte foi 9,43 µA em c8 e 0,80 µA em c10. O monitor de corrente em regime e TE_B não registraram sobreposição sustentada nesses writes. As duas tomadas pelo host respeitaram a ordem de liberação nos waveforms inspecionados. A verificação integrada completa continua **INCONCLUSIVO** por causa dos testemunhos iniciais fixos. Não foi demonstrado defeito funcional que impeça TT/FF. É necessário resolver a cobertura de propriedade em SS antes de extrapolar o resultado. [Diagnóstico suplementar com timestamps e correntes](../build/phase3/integrated_ss_20261119_preflight/diagnostico_testemunho.json)

## D. Veredito e execução

**INCONCLUSIVO no conjunto**. O transiente e todas as operações de dados passaram no escopo observado. A janela diagnóstica e as precondições de medição são mantidas separadas. A qualificação elétrica geral permanece `NOT_CHARACTERIZED`.

Uma única execução SPICE, de 370 ns, terminou com código ngspice 0 e **20.539 amostras**, em **35 min 50 s** de parede. O timeout de 44 min 10 s não foi atingido. As advertências de singularidade na solução DC inicial foram seguidas de conclusão do ponto inicial transiente, como no PEX de referência. O analisador retornou 1 para o laudo funcional inconclusivo. Em software, passaram **216 testes** (165 de infraestrutura e 51 de RC, incluindo quatro novos testes offline), sem skips. Não houve extração, DRC/LVS novo ou alteração física. [Recibo do simulador](../build/phase3/integrated_ss_20261119_preflight/simulation.json) · [Recibo de software](../reports/phase3/integrated_ss_regression_20261119/summary.json)

## E. Próxima investigação única e pendências

Medir especificamente a **recuperação da condução sob sonda após restaurar CSb**, nos três padrões de transição que ficaram inconclusivos, no mesmo SS e PEX. Definir antecipadamente um intervalo de comprovação de drive por corrente antes da mudança de controle. A guarda de 1,5 ns deve permanecer fixa. O critério de conclusão é observar drive inicial e liberação sustentada em todos os pinos das três transições, com separação positiva antes do acionamento forte. Preservar em paralelo o resultado atual do observador e o histórico de 300 ps. A investigação ainda não foi iniciada.

Permanecem pendentes a validação correspondente em TT/FF, a qualificação do PEX e de timing/setup/hold/potência, o fechamento da evidência de SNM no escopo do Marco 3 e a Liberty baseada em métricas verificadas. O pacote local contém preparação, deck, binding, registros, waveform, CSVs e análise. O código do ensaio, o da análise e os testes offline estão na branch local, com HEAD `8e1d961`.
