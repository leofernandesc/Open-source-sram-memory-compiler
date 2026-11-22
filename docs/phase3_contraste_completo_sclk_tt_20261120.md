# Fase 3 — Contraste completo de SCLK em TT

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
O experimento preserva o candidato físico 4×8. Nos ciclos de origem
16 e 17, o TT histórico armazenou o zero corretamente na célula
(linha 3, bit 3), mas a regeneração produziu `0xF8` para `0xF0`
esperado. A classificação nesta rodada distingue o readback da
fidelidade do deslocamento aplicado.
[Especificação](../specs/technical_specification.md) ·
[Contrato temporal](../specs/sram_4x8_timing_contract.md) ·
[Diagnóstico TT](phase3_data3_tt_snm_piloto_20261120.md)

## A. Execução e autorização

Foi registrado `NUMERICAL_PROGRESS_VERIFIED` com o SHA-256 do
recibo do ensaio de 14 ns que progrediu até 10,4000 ns com a
PWL original. Essa autorização comprova a partida numérica.
O gate histórico guardado permanece `BLOCKED`. A equivalência
elétrica foi reservada à comparação dos waveforms a seguir.
[Autorização nova](../build/phase3/sclk_r87_full_tt_20261120/authorization.json) ·
[Gate histórico](../build/phase3/sclk_r87_20261120/startup_gate.json) ·
[Diagnóstico da partida](phase3_ngspice_partida_sclk_20261120.md)

| Entrada verificada | SHA-256 |
|---|---|
| GDS | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Binding sem a fonte | `40f4cc2f0da257b8435bcd387b938fcaba2b7456c3a74b3b350446fd5a434fc3` |
| Fechamento dos modelos, 319 arquivos | `3145e3762bf282bb0428afb9f28ef1710bb40c11447442d93b206c43369249b6` |
| Waveform histórico selado | `7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646` |
| Binding experimental e PWL original | `479547cdf229a92492a17e61f0091fe8227f01095ba6387797b010f0c73a1d56` |

O preflight reconstruiu a PWL de 3.203 pontos a partir do waveform
selado e confirmou os mesmos bytes. Remover a única fonte
experimental de corrente recupera o binding original. R87 liga
`rc8562` a `rc8571` por 6,46438 Ω. A jusante há somente os três
gates de X235, X521 e X351. A PWL permanece definida nas janelas
211–219 ns e 231–239 ns, com 182 ps programados e pico calculado
de 69,336 mA. TT/SKY130A, 1,8 V, 27 °C, 10 fF/bit, período de
20 ns, slew de 50 ps, passo máximo de 25 ps e captura na descida
de CLK. Mantiveram-se todos os estímulos, as tolerâncias, Gear,
KLU e o circuito pós-layout. Foram acrescentadas duas sondas de
tensão em R87, uma observação da corrente da fonte e três `echo`
de fase. [Preparo anterior](phase3_sclk_preflight_auditoria_snm_20261120.md) ·
[Manual do ngspice 44, seções 11.6.1 e 27.1](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf)

```bash
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/run_phase3_sclk_r87_full.py \
  --output build/phase3/sclk_r87_full_tt_20261120
```

O subprocesso é `stdbuf -o0 -e0 ngspice -n -b bench.spice`.
O monitor mantém stdout e stderr observáveis em tempo real e
amostra PID, CPU, RSS, I/O e avanço a cada 5 s. Usa 300 s para
preparação, até 2.850 s de integração após o primeiro avanço
positivo e um teto total de 3.000 s incluindo a janela de
encerramento. Ausência de linha de progresso fica desconhecida.
[Comando e limites](../build/phase3/sclk_r87_full_tt_20261120/attempt.json)

O ngspice 44.2 concluiu a única execução com retorno `0`.
O waveform integral chegou a **250 ns** com **28.687 amostras**.
O último marcador publicado foi 249,980 ns. O avanço ficou mais
lento nas duas janelas densas da PWL e voltou a acelerar fora delas.
O stderr registrou o mesmo fallback de ponto de operação do diagnóstico
de partida e nenhuma interrupção do transiente.

| Marco ou duração | Tempo (s) |
|---|---:|
| Primeira saída do processo | 3,372 |
| Deck pronto / despacho de `tran` | 110,073 / 110,074 |
| Despacho até solução inicial | 7,784 |
| Primeiro avanço transiente, 0,0016 ns | 118,227 |
| Solução inicial até retorno de `tran` | 2.059,220 |
| Gravação e saída depois de `tran` | 1,884 |
| Tempo de parede total | 2.178,961 (36 min 19 s) |
| Tempo acumulado de CPU | 2.174,574 |

Foram guardadas 430 amostras do processo, com pico de RSS de
1.642.928 KiB. O SHA-256 do waveform é
`1b10d5efcb5a227c9bd94e792d78682cb2d487683f41ac136cf4f6c069e91775`.
[Recibo do ngspice](../build/phase3/sclk_r87_full_tt_20261120/result.json) ·
[Telemetria](../build/phase3/sclk_r87_full_tt_20261120/samples.jsonl)

## B. Fidelidade pré-declarada

As bordas são medidas em 20%, 50% e 80% de 1,8 V nas amostras
de cada waveform, por interpolação linear em seu próprio grid.
A marca de 10% aproxima o início da rampa. Nenhum desses pontos
é um limiar universal de condução. Para aceitar o deslocamento,
cada cruzamento de subida dos três gates precisa estar em
182 ± 25 ps e cada cruzamento de descida permanecer a até 25 ps
do original. A diferença de `slew` 20→80 e a diferença de largura
de pulso em relação ao encurtamento esperado de 182 ps têm
envelopes de 50 ps porque dependem de dois cruzamentos. Os
platôs devem continuar em nível lógico válido. Os 25 ps são
o passo máximo do transiente e a resolução operacional selada
para o contraste, sem pretensão de especificar o macro.

| Ciclo | Gate | Atraso a 10% (ps) | Atraso a 20% (ps) | Atraso a 50% (ps) | Atraso a 80% (ps) | Slew 20→80 ref. → contraste (ps) | Δ largura a 50% (ps) | Maior \|Δ descida\| (ps) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 16 | Sampler BL | 150,02 | 151,28 | 157,83 | 180,64 | 651,59 → 680,95 | −158,33 | 0,69 |
| 16 | Sampler BLB | 149,51 | 150,98 | 157,91 | 179,73 | 652,19 → 680,94 | −157,66 | 0,25 |
| 16 | Tail | 149,29 | 150,84 | 158,01 | 180,20 | 653,19 → 682,55 | −158,03 | 0,38 |
| 17 | Sampler BL | 150,67 | 151,50 | 158,27 | 181,15 | 651,56 → 681,21 | −156,87 | 1,80 |
| 17 | Sampler BLB | 150,14 | 151,23 | 158,35 | 180,22 | 652,22 → 681,21 | −156,19 | 2,16 |
| 17 | Tail | 149,92 | 151,09 | 158,45 | 180,83 | 653,11 → 682,85 | −156,56 | 1,94 |

O atraso variou ao longo da rampa. Nos seis casos o cruzamento
de 20% chegou **5,50–6,16 ps antes do limite inferior de 157 ps**.
O cruzamento de 80% ficou próximo do alvo, com rampa 20→80 cerca
de 29–30 ps mais longa. Em todos os gates, o platô baixo permaneceu
abaixo de 0,203 mV e o alto ficou em aproximadamente 1,800 V.
A desativação foi preservada dentro de 2,16 ps.

No waveform do contraste, R87 a montante cruza 50% em 214,368945
e 234,369857 ns. O nó local cruza em 214,563858 e 234,564495 ns,
respectivamente. A diferença de cerca de 195 ps compara terminais
**dentro da mesma execução**. A comparação gate a gate contra a
referência histórica mede os 158 ps dessa mesma borda.
[Cruzamentos, amplitudes e larguras](../build/phase3/sclk_r87_full_tt_analysis_20261120/contrast.json)

## C. Efeitos colaterais

O critério compara cruzamentos e estados lógicos nos sinais comuns,
incluindo WL, pré-carga, CLK, habilitação de DATA e as sondas
arquivadas dos outros sete senses. As diferenças de amplitude
são reportadas com o instante correspondente. Para bitlines e
saídas de sense fora do ramo, cruzamentos isolados de um limiar
analógico são registrados à parte das mudanças que atingem ambos
os níveis lógicos. Para o armazenamento, o
estado incorreto exige evidência de inversão sustentada dos nós
complementares. Para corrente, o arquivo R87 e a PWL distinguem
o pico comandado da soma algébrica entre fonte e corrente pelo
resistor. Essa soma representa o efeito imediato a montante do
ramo. O waveform histórico não observou diretamente `rc8562`
ou `rc8571`, de modo que as comparações ali se limitam às
sondas arquivadas da rede compartilhada.

| Intervalo ou grandeza | Observação |
|---|---|
| Antes de 211 ns | Corrente da fonte medida em 0 A. As 53 comparações de controle, endereço, sense, D/Q, BL/BLB e DATA mantiveram os eventos compatíveis. A maior diferença foi 35,5 µV em `_85_.Q` no limite da janela. |
| SCLK compartilhado e sete outros senses | Cruzamentos de 50% adiantados em aproximadamente 36–37 ps nas duas janelas. Diferença de forma de onda de até 87,9 mV nas sondas compartilhadas. |
| WL e pré-carga | WL80 no acesso local adiantada 16,63 / 16,75 ps. Liberação da pré-carga a 50% adiantada 5,84 / 6,41 ps. CLK público e habilitação de DATA ficaram dentro do envelope de 25 ps. O host forte permaneceu desligado nas leituras. |
| Caminhos dos outros bits | `SA_OUTB` dos senses 4–7 teve cruzamentos deslocados em até 37,36 ps e diferença de até 260,61 mV. Os oito bits ficaram corretos na observação externa. |
| Corrente em R87 | Picos medidos de 69,336 / 68,987 mA na fonte e 23,108 / 23,099 µA no ramo líquido a montante, obtido somando a corrente medida à queda em R87 dividida pela resistência. O pico da fonte pertence à instrumentação. |
| Após as janelas | Os controles voltaram ao envelope observado. Tail SCLK20 desativou em 224,269 / 244,269 ns, antes da pré-carga50 em 224,379 / 244,379 ns. BL e BLB, com os três gates baixos, voltaram de forma sustentada à pré-carga em 224,791 / 244,791 ns, cerca de 82–84 ps mais tarde que na referência. O zero armazenado permaneceu íntegro até 250 ns. |

A redistribuição de fase nos outros sete senses e a antecipação de
WL mostram que a alteração elétrica atravessou os limites do ramo
topologicamente exclusivo. Atribuir a correção da leitura somente
ao deslocamento local exigiria separar esses efeitos. A execução
também não separa a retroação elétrica de diferenças de
discretização nos pontos adicionais da PWL. A corrente
dos MOS de amostragem não foi gravada. As sondas do latch, BL/BLB
e `VGS` do tail permitem localizar os eventos sem equiparar um
cruzamento arbitrário à condução física.
[Corrente e tensão nos dois terminais](../build/phase3/sclk_r87_full_tt_analysis_20261120/r87_current_and_voltage.csv) ·
[Waveforms comparativos](../build/phase3/sclk_r87_full_tt_analysis_20261120/read_waveforms.png)

## D. Resultados funcionais

O ponto de observação externo é o início programado da sonda
fraca, 1,5 ns após a descida nominal. A palavra completa deve
estar simultaneamente em níveis 20%/80%, em um intervalo
sustentado até a observação que contém ao menos três amostras
nativas e 50 ps de duração demonstrada. Esse intervalo verifica
estabilidade da evidência e não define um prazo público de
`tREAD_VALID`. A janela histórica de ±100 ps ficou fora do
veredito. Os instantes locais de D e Q usam as sondas arquivadas
do D do FF e da rede de Q no driver.

| Ciclo | Palavra esperada | Referência TT | Contraste TT | Veredito no contraste |
|---|---|---|---|---|
| 14 | `0xAA` | `0xAA` | `0xAA` | PASS |
| 15 | `0x0F` | `0x0F` | `0x0F` | PASS |
| 16 | `0xF0` | `0xF8` | `0xF0` | PASS |
| 17 | `0xF0` | `0xF8` | `0xF0` | PASS |

| Medição | c16 referência → contraste | c17 referência → contraste |
|---|---:|---:|
| WL80 no gate da bitcell (ns) | 214,216 → 214,199 | 234,209 → 234,192 |
| SCLK20 no tail (ns) | 214,153 → 214,304 | 234,153 → 234,304 |
| SCLK20 no tail em relação a WL80 (ps) | −62,77 → +104,70 | −56,38 → +111,46 |
| BLB−BL a SCLK20 do tail, com VGS ≈ 0,360 V (mV) | +15,1 → +191,3 | +19,9 → +201,3 |
| BLB−BL a SCLK50 do tail (mV) | +360,5 → +650,0 | +373,2 → +663,3 |
| Inversão de SAB−SA durante a avaliação | 214,579 ns → ausente | 234,590 ns → ausente |
| Sense correto sustentado no contraste, primeira amostra (ns) | 214,990 | 234,985 |
| D correto sustentado no contraste, primeira amostra (ns) | 215,272 | 235,235 |
| Instante local de captura no contraste (ns) | 220,058 | 240,058 |
| Q correto no contraste | Primeiro nível baixo comprovado em 220,423 ns | Retido baixo desde c16 |
| DATA3 correto no contraste | Primeiro nível baixo comprovado em 220,584 ns | Já baixo em 240 ns |
| Palavra completa estável, primeira amostra corroborada → observação (ns) | 220,655 → 221,500 | 240,000 → 241,500 |

No contraste, D permaneceu baixo durante pelo menos 4,786 ns e
4,823 ns antes das duas capturas. A palavra c16 tem 86 amostras
nativas no intervalo estável e c17 tem 145. No segundo ciclo a
palavra repetida já era válida no início da janela verificada.
Essa observação não mede latência de uma nova transição do pino.
As seis capturas de escrita foram verificadas. Nos reads da linha 3,
Q da bitcell permaneceu entre −7 e +148 mV e QB entre 1,772 e
1,832 V. Assim, o estado correto foi mantido nas duas avaliações.
[Eventos internos e externos](../build/phase3/sclk_r87_full_tt_analysis_20261120/read_events.csv)

## E. Vereditos independentes

- **Funcional TT no contraste: `PASS` no escopo.** As duas palavras
  voltaram a `0xF0`, com sense, D, Q e DATA3 consistentes com o zero
  armazenado. As leituras predecessoras continuaram corretas.
- **Hipótese causal de SCLK: `INCONCLUSIVA`.** A avaliação local
  foi retardada, e o maior intervalo desde WL acompanhou mais
  diferencial de bitline e regeneração correta. Isso é compatível
  com a hipótese temporal. O deslocamento a 20% ficou fora da faixa
  selada nos três gates e a rede compartilhada também mudou de fase.
  O ensaio não estabelece 182 ps como a causa isolada nem como valor
  a implementar fisicamente.

A macro sem instrumentação conserva o `FAIL` histórico em TT.
A correção funcional experimental justifica investigar a temporização
relativa de amostragem e regeneração. Uma correção física ainda depende
de isolar o efeito elétrico. A qualificação geral da macro permanece
`NOT_CHARACTERIZED`.

## F. Próxima ação

Fazer **um contraste isolado no sense 3 extraído**, reproduzindo BL e
BLB da referência com o mesmo modo comum e impedância de acionamento
nos dois casos. Alterar apenas a subida de SCLK nos três terminais e
preservar a descida. Aceitar o ensaio quando o controle reproduzir a
regeneração incorreta, os três gates do contraste medirem 182 ± 25 ps
nos cruzamentos acordados e a decisão do latch puder ser comparada
sob entradas equivalentes. Isso testa a hipótese temporal sem que
uma antecipação de WL ou do SCLK dos outros senses possa explicar o
resultado. Esta próxima tarefa ficou apenas proposta.

## Evidências e regressão

Foram executados **14 testes distintos de software** sobre o monitor
e o analisador. A reanálise do waveform arquivado confirmou as seis
capturas de escrita, os dois padrões predecessores e os dois `0xF8`
originais. Foram verificados novamente os 319 arquivos de modelos
após a simulação. O diff do deck experimental contra o original de
250 ns contém somente as sondas e marcas de fase autorizadas.

```bash
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg python3 \
  tools/analyze_phase3_sclk_r87_full.py build/phase3/sclk_r87_full_tt_20261120 \
  --output build/phase3/sclk_r87_full_tt_analysis_20261120 --plots
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_phase3_sclk_r87_full.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_phase3_sclk_startup.py'
```

O ZIP de entrega inclui os dois scripts novos, a suíte nova,
este relatório, os decks e recibos, o waveform integral com corrente,
a análise, o gráfico e `SHA256SUMS`. Para reanálise, mantenha os
arquivos históricos de `build/phase3/data3_tt_20261120/` e
`build/phase3/integrated_tt_20261120/` no checkout, conforme o diagnóstico
de origem. O HEAD, a branch e as alterações preexistentes foram
preservados. Sem commit, push ou merge.
[Testes](../build/phase3/sclk_r87_full_tt_tests_20261120/tests_final.log) ·
[Reanálise do controle](../build/phase3/sclk_r87_full_tt_tests_20261120/reference_replay.log) ·
[Integridade do deck](../build/phase3/sclk_r87_full_tt_tests_20261120/integrity.log)
