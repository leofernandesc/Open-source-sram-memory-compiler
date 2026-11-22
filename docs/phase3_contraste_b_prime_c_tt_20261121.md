# Fase 3 — Contraste funcional TT entre B′ e C

## Escopo e preflight

B′ é a reconstrução independente do primeiro ECO, com tap 48, captura pelo CLK público, oito `ebufn_8` e registradores `dfxtp_1`. C é a geometria espaçada com `dfxtp_2`. O contraste trata as geometrias como duas realizações físicas distintas. O histórico de C veio do waveform reduzido de 250 ns já arquivado. [Auditoria arquitetural](phase3_auditoria_comparativa_arquitetura_4x8_20261120.md) · [Diagnóstico de C](phase3_data3_tt_snm_piloto_20261120.md)

| Artefato B′ | SHA-256 verificado |
|---|---|
| GDS | `a593676029af53d37fd9e40a1a2a5b1ef283c463428e940a168302c88064539e` |
| LEF top | `6be3c6b87742f7113d13b76ec19f5d7269cd75fa595ca05587f8aad85faac7b0` |
| PEX integral | `84cecaa3e29fc8940a3cd2673b0547ed7365a658b2ba3c7b3d7b6cd2bcbf858e` |

O GDS tem recibos de DRC=0 e LVS único. Os recibos de LEF e PEX pinam esse GDS. O PEX contém 1.733 MOS, 16.023 R, 12.393 C, 16 portas e malhas de VDD/VSS distribuídas, com auditoria de capacitância sem diferenças. O binding é byte a byte igual ao do run arquivado de B′ de 170 ns e preserva os cartões do PEX. Os mapas conferidos cobrem endereços, operação, quatro WLs, pré-carga, SCLK compartilhado e os três gates locais, raízes e terminais de BL/BLB, latch, NTAIL, D/Q, DATA e correntes da fixture. Os 16 pares de armazenamento das linhas 2 e 3 foram localizados pelo acesso à WL/BL e pelo feedback CMOS; dois métodos independentes concordam na célula linha 3/bit 3. [Manifesto do preflight](../build/phase3/b_prime_tt_20261120/run/manifest.json) · [Mapa e dispositivos de sonda](../build/phase3/b_prime_tt_20261120/run/probe_receipt.json)

Foram preservados SKY130A `tt` e os 319 hashes da cadeia de modelos de C, 1,8 V nominal com rampa de 1 ns, 27 °C, período de 20 ns, fases de 10 ns, slew de 50 ps, 10 fF por DATA, Gear/KLU e `tran 10p 250n 0 25p`. As fontes PWL, mascaramento e protocolo são os do deck reduzido arquivado. A comparação textual permite apenas o novo binding, as listas de vetores de observação e três marcadores de log no bloco de controle. Os ciclos de origem são 0, 1, 2, 3, 4, 5, 8, 10, 14, 15, 16 e 17. A sequência escreve `0x0F` na linha 2 em c4 e `0xF0` na linha 3 em c5. As releituras c15–17 ocorrem nas bordas públicas descendentes programadas em 200, 220 e 240 ns. A compressão removeu as leituras anteriores às escritas de origem c8 e c10, mas preservou as esperas programadas de 1,5 ns para a reabertura do driver forte. O escopo oferece evidência de separação entre donos nas transições presentes, incluindo write→read e máscaras em leitura. A espera é uma condição de ensaio. [Deck](../build/phase3/b_prime_tt_20261120/run/bench.spice) · [Cronologia](../build/phase3/b_prime_tt_20261120/run/fixture.json)

Critérios congelados antes do SPICE. Na captura local, verificam-se sense, D e o valor capturado e retido em Q; no pino, verifica-se a palavra inteira estável até a entrada da sonda fraca programada, com limites 0,36 V e 1,44 V. Registra-se separadamente S ±100 ps. O tACCESS, onde há transição atribuível, vai de CLK↑50 até a palavra nova válida e sustentada. O contrato exige correção na captura; o prazo público de disponibilidade em DATA segue pendente. Propriedade usa tensão, enable e corrente, com piso de 50 µA e testemunho de pelo menos três amostras e 50 ps. A retenção de Q é acompanhada até a próxima captura e o estado das células de condicionamento, da escrita ao fim do ensaio. Os cruzamentos de WL80 e SCLK20 servem à comparação de forma de onda. [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Analisador pré-pinado](../build/phase3/b_prime_tt_20261120/analyze.py)

Cinco testes de software passaram antes da avaliação de B′. O replay offline de C reproduziu `0x0F/0xF8/0xF8` em c15–17, erro em sense/D, bit 3 armazenado corretamente e falha iniciada em ambas as avaliações. O waveform de referência verificado tem SHA-256 `7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646`. [Testes](../build/phase3/b_prime_tt_20261120/tests.log) · [Reanálise de C](../build/phase3/b_prime_tt_20261120/preflight_reference/archived_c.json)

## Execução

Comando no ambiente EDA do projeto, com ngspice 44.2 e um CPU do simulador.

```bash
./tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/tools \
  python3 build/phase3/b_prime_tt_20261120/contrast.py run \
  /work/build/phase3/b_prime_tt_20261120/run
```

O processo filho foi `stdbuf -o0 -e0 ngspice -n -b bench.spice`. O preflight offline levou 3,75 s. O monitor registra preparação, despacho de `tran`, solução inicial, primeiro avanço, CPU e RSS. A guarda para solução inicial é de 300 s desde o despacho, e o teto do processo é de 2.400 s.

| Etapa ou medida | Valor observado |
|---|---:|
| Preparação do ngspice até o despacho de `tran` | 194,340 s |
| Despacho até a solução inicial | 13,457 s |
| Despacho até o primeiro avanço reportado | 13,798 s, em 0,0002 ns |
| Integração, da primeira referência até o encerramento | 2.190,198 s |
| Tempo total de parede | 2.398,336 s |
| CPU acumulada / RSS máximo amostrado | 2.395,549 s / 1.591.084 KiB |
| Limite de avanço registrado | **85,8258 ns de 250 ns** |
| Exportação de waveform de B′ | **Ausente** |
| Número de amostras elétricas exportadas / observações de telemetria | 0 / 472 |
| Encerramento | `TOTAL_WALL_LIMIT`, ngspice −15 (SIGTERM), comando de controle retornou 1 |

Houve avisos de matriz singular e falhas de `gmin stepping` e `source stepping`, seguidos de solução bem-sucedida pelo fallback de ponto de operação transiente. A integração começou e continuou avançando com CPU próxima de um núcleo completo. À passagem pela escrita iniciada em 70 ns, o ritmo caiu. Por exemplo, entre aproximadamente 1.083 s e 1.802 s de parede, o tempo simulado foi de cerca de 69,9 a 80,5 ns. O processo foi encerrado pelo monitor no limite de parede, com margem para o envio de SIGTERM. A lentidão no transiente foi o limitante observado; o log não identifica uma causa física nem um erro fatal do simulador.

O deck só executa `wrdata` depois de `tran` retornar. Portanto o máximo registrado é progresso do integrador, sem tensões ou correntes de B′ que sustentem uma classificação funcional. O teto foi atingido ainda antes da escrita da linha 2, programada para CLK↑ em 90 ns, e da linha 3 em 110 ns. [Recibo do único processo](../build/phase3/b_prime_tt_20261120/run/result.json) · [stdout](../build/phase3/b_prime_tt_20261120/run/stdout.log) · [stderr](../build/phase3/b_prime_tt_20261120/run/stderr.log) · [Telemetria compacta](../build/phase3/b_prime_tt_20261120/simulator_progress.csv)

## Resultados funcionais e comparação B′ × C

| Ciclo de origem | Linha | Palavra esperada | B′ · célula, sense, D, Q, DATA | C arquivado · sense / D / Q / DATA | C · intervalo estável observado em DATA |
|---:|---:|---|---|---|---|
| 15 | 2 | 0x0F | Não observados | 0x0F / 0x0F / 0x0F / 0x0F · PASS | 200,614–201,500 ns |
| 16 | 3 | 0xF0 | Não observados | 0xF8 / 0xF8 / 0xF8 / 0xF8 · FAIL | 220,642–221,500 ns, palavra errada |
| 17 | 3 | 0xF0 | Não observados | 0xF8 / 0xF8 / 0xF8 / 0xF8 · FAIL | 240,067–241,500 ns, palavra errada |

No waveform de C, o readback de c15 confirma a palavra da linha 2; as sondas internas do diagnóstico de armazenamento cobrem a célula linha 3/bit 3. O zero permaneceu armazenado antes, durante e depois das leituras de c16/c17. Nas janelas entre antes de WL e a observação externa, Q da célula ficou entre aproximadamente −7 e 147 mV, e QB entre 1,772 e 1,832 V. A passagem do bit 3 errado para D antes da borda local distingue a falha de regeneração de um atraso no pino. A janela diagnóstica em C foi 8/8, 7/8 e 7/8 em c15–17. A retenção de Q previamente capturado até a leitura seguinte foi confirmada nos três casos, inclusive quando o resultado anterior estava errado.

| Medida | B′ TT desta rodada | C TT reduzido, c16 / c17 |
|---|---|---|
| WL80 no acesso à célula | Ausente | 214,215535 / 234,208891 ns |
| SCLK20 do sampler BL | Ausente | 214,154176 / 234,153955 ns |
| SCLK20 − WL80 | Ausente | −61,36 / −54,94 ps |
| BLB−BL em SCLK20 | Ausente | +15,96 / +20,92 mV |
| NTAIL antes da subida, em SCLK20 e em SCLK50 do tail | Ausente | 1,148 / 1,226 / 1,037 V; 1,148 / 1,225 / 1,036 V |
| PRECH50, liberação | Ausente | 212,147161 / 232,147765 ns |
| Primeira amostra da decisão errada estável | Ausente | 214,791458 / 234,814804 ns |
| Captura local a 50%, D do bit 3 | Ausente | 220,058178 ns, 1,803 V / 240,058082 ns, 1,803 V |
| Propriedade na sequência reduzida | Ausente | 8 PASS, quatro inconclusivos (c2, c8, c16, c17); sem oposição forte sustentada comprovada |

As medidas de C acima usam o ponto local `wl_at_q` do ensaio de 250 ns. Os valores dos marcadores de WL em outro ponto da rede ou no ensaio de 370 ns têm referência elétrica distinta. O revisor não interpreta ausência de testemunho de drive como contenção. Os resultados integrados TT/SS permanecem nos seus recibos de origem. Os ensaios antigos de B′ de 170 ns verificaram c6/c7 e não preenchem as medições faltantes de c15–17. [CSV com campos ausentes explícitos](../build/phase3/b_prime_tt_20261120/reads.csv) · [Dados C por ciclo, tensões e correntes](../build/phase3/b_prime_tt_20261120/preflight_reference/archived_c.json)

## Parecer

**`INCONCLUSIVE`.** A bancada passou no preflight e a tentativa encontrou solução inicial. O avanço insuficiente dentro do teto impediu medir os casos discriminantes. Ainda não há evidência para dizer se B′ tem a mesma falha do sense 3, nem para apontar o conjunto de mudanças de B′ para C como origem da falha. Mantém-se C como referência física de integração, com seu FAIL TT registrado. O driver local v1 fica em espera como experimento, sem evidência nova que justifique promover ou descartar a abordagem.

**Única próxima investigação recomendada.** Em rodada autorizada, executar o mesmo deck pinado de B′ em um nó de cálculo com capacidade e janela de execução compatíveis com o transiente de 250 ns, preservando o binding, estímulos, modelos e tolerâncias. O critério de conclusão é exportar o waveform até o fim e observar ambas as escritas de condicionamento e c15–17 com os critérios congelados nesta rodada. A medição atual indica uma limitação de custo numérico dessa tentativa e não embasa um ECO.

As alterações locais preexistentes foram preservadas, com o relatório novo e evidências em área ignorada. Confirmação da branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33` e `git diff --check` limpo quanto a whitespace. A rodada teve **uma tentativa SPICE em B′**, sem simular C, sem alterar circuito, sem nova extração ou verificação física e sem commit, push ou merge. Permanecem os resultados históricos, o Monte Carlo experimental e a qualificação geral `NOT_CHARACTERIZED`. [Recibo de encerramento](../build/phase3/b_prime_tt_20261120/verification.json)
