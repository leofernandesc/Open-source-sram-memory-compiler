# Fase 3 — Partida histórica do recorte carregado em TT

**Controle `INCONCLUSIVE`.** A partida histórica recuperou a solução do ponto de operação no recorte. A integração transiente foi abortada em **1,664 ps**, durante a rampa, com `Timestep too small` no ramo `vcut205#branch`. A simulação não chegou às escritas ou leituras.

## Diferenças de inicialização

| Evento | Macro TT arquivada, 250 ns | Primeiro recorte carregado |
|---|---|---|
| VDD externo | 0 V em t=0, 1,8 V em 1 ns | 1,8 V desde o ponto de operação |
| CLK na energização | Baixo, seguido de capturas inativas nas subidas nominais de 10 e 30 ns | Baixo, seguido pela subida nominal de escrita em 3 ns |
| Controles iniciais | Antes da primeira captura inativa, READ_Q e WRITE_Q não têm estado lógico garantido. As duas capturas deixam o comando inativo | O replay começa no histórico de uma escrita, com WRITE_Q alto e READ_Q baixo |
| WL durante a rampa | Todos os quatro WL ficaram abaixo do limiar lógico alto. Há transitórios analógicos de partida | Medição indisponível. A execução anterior não produziu waveform |
| Primeira escrita | Subida nominal em 50 ns na referência TT usada nesta investigação | Subida nominal em 3 ns no prefixo, com VDD ideal já nominal |
| Condicionamento | Rampa, espera e duas capturas inativas antes da primeira escrita | Sem rampa e sem os dois ciclos inativos |

O contrato não garante o conteúdo das células nem dos registros na energização. Na referência TT desta rodada, em 1 ns o CLK ainda estava baixo, o comando de pré-carga media 1,007 V e a habilitação de escrita 0,394 V. Em 9 ns, ambos estavam próximos de zero e as quatro WL estavam baixas. Esses dados distinguem os transitórios iniciais do controle de uma escrita programada. A tentativa anterior em VDD constante ficou em `true gmin stepping` e atingiu 720,35 s. A diferença de partida motiva o ensaio, sem atribuir uma causa à convergência antecipadamente. [Especificação](../specs/technical_specification.md) · [Contrato de partida](../specs/sram_4x8_timing_contract.md) · [Referência TT](phase3_data3_tt_snm_piloto_20261120.md) · [Controle anterior](phase3_sclk_carregado_tt_20261120.md)

## Alteração e integridade

A cópia usa `VDD_BASE VDD VSS PWL(0 0 1n 1.8)` no mesmo par de terminais. VSS permanece em 0 V. Os retornos, bulks e domínios internos continuam ligados pela mesma malha extraída. As 21 fontes com replay foram estendidas com a referência de 0 a 46 ns. Em 46–47 ns o CLK está baixo enquanto as condições de fronteira passam ao início do prefixo de escrita. Todos os nós e níveis dos segmentos anteriores são preservados com uma translação temporal única de **+47 ns**, sem editar os intervalos entre bordas. As fronteiras sem replay ficaram idênticas.

| Evento | Tempo no simulador | Tempo de referência para as medições do recorte |
|---|---:|---:|
| Rampa e primeiro período de espera | 0–10 ns | Prefixo da referência TT original |
| Duas subidas inativas | 10,025 / 30,025 ns | Prefixo da referência TT original |
| Junção com CLK baixo | 46–47 ns | Início do prefixo anterior em 147 ns |
| Primeira e segunda escritas, subidas a 50% | 50,025 / 70,025 ns | 150,025 / 170,025 ns |
| Janelas de leitura c15–c17 | 88–147 ns | 188–247 ns |
| Subidas c15 / c16 / c17 a 50% | 90,025 / 110,025 / 130,025 ns | 190,025 / 210,025 / 230,025 ns |

Os estímulos confirmaram WRITE_Q ativo, READ_Q inativo, endereço e dados estáveis em 57 ns para linha 2 `0x0F` e em 77 ns para linha 3 `0xF0`. Esses são resultados do preflight, ainda distintos da escrita elétrica. A cópia do recorte preservou byte a byte os **1.013 MOS, 14.810 resistores e 8.138 capacitores**, com R87 original. Nenhum cartão de dispositivo foi alterado. O deck acrescentou 32 sondas passivas de Q/QB nas linhas 2 e 3, marcadores de fase, precisão de gravação e um horizonte de 147 ns. As opções Gear, KLU, tolerâncias, temperatura e passo máximo de 25 ps foram preservados. A integridade da árvore de modelos e do PEX padrão foi conferida antes da execução. [Manifesto e auditoria temporal](../build/phase3/sclk_shared_ramp_20261120/manifest.json) · [Recorte](../build/phase3/sclk_shared_ramp_20261120/slice.spice)

## Execução e diagnóstico

Foi executado **um controle SPICE** em SKY130A TT, 27 °C e 1,8 V nominal. O ngspice 44.2/KLU foi capturado com stdout e stderr não bufferizados. As marcas de fase e as 86 amostras de processo permitem distinguir a preparação, a solução inicial e a integração.

| Evidência | Resultado |
|---|---|
| Preparação do deck | 147,60 s até a marca de entrada em `tran` |
| Solução inicial | Concluída em 175,28 s de parede, 27,68 s após o despacho |
| `dynamic gmin stepping` | Iniciou em 172,14 s e completou em 175,28 s |
| Primeiro avanço transiente confirmado | 176,02 s de parede, a 8 fs de tempo simulado |
| Maior tempo transiente observado | **1,664 ps**, ainda na rampa. O marcador permaneceu igual por 235,62 s nas amostras de processo |
| Integração após a solução inicial | 252,80 s até o retorno de `tran` com erro |
| Encerramento | **428,43 s** de parede, antes das guardas de 5 min para a solução inicial e 20 min total. O monitor enviou SIGTERM após o erro explícito |
| Recursos | 427,26 s de CPU acumulada e pico amostrado de 941.160 KiB de RSS, cerca de 919 MiB |
| Saída | Runner 1, processo ngspice −15 após o SIGTERM. O simulador informou 15 pontos e abortou. Nenhum waveform foi salvo para reanálise |

[Comando e guardas](../build/phase3/sclk_shared_ramp_20261120/attempt.json) · [Recibo com fases](../build/phase3/sclk_shared_ramp_20261120/result.json) · [Telemetria](../build/phase3/sclk_shared_ramp_20261120/samples.jsonl) · [Log de erro](../build/phase3/sclk_shared_ramp_20261120/stderr.log)

O diagnóstico do simulador foi `Timestep too small` em 1,664 ps, com passo de 3,125 × 10⁻²³ s e indicação de `vcut205#branch`. O cartão `VCUT205 rc7913 VSS 0` já existia no recorte anterior. Ele mantém a VSS uma placa do nó extraído `m1_16160_31260#`. A placa remanescente acopla por 16 capacitores, que somam 34,54 fF, a sinais como WL e qualificação de linha. Dois capacitores excluídos pela regra de corte, `C6381` e `C6439`, conectavam o mesmo metal a VDD e VSS no PEX original. O ramo apontado é uma terminação da bancada, sem intervenção no sense ou nas bitcells. O diagnóstico localiza o ponto relatado pelo solver, mas os dados não demonstram que o aterramento seja a causa única. [Ramo e cartões extraídos](../build/phase3/sclk_shared_ramp_20261120/startup_failure.json)

A sequência de rampa e espera resolveu a etapa de ponto de operação no ensaio atual, que havia consumido toda a janela na tentativa em 1,8 V constante. O bloqueio passou a ocorrer na integração durante a rampa. A comparação envolve a sequência de partida inteira e não isola o efeito da rampa das condições de fronteira.

## Resultado funcional e decisão

| Ensaio | Expectativa ou referência | Resultado elétrico da rodada |
|---|---|---|
| Escrita linha 2 | `0x0F` | Não alcançada |
| Escrita linha 3 | `0xF0` | Não alcançada |
| c15 | Referência TT `0x0F` | Não alcançada |
| c16 | Referência TT `0xF8` para `0xF0` esperado | Não alcançada |
| c17 | Referência TT `0xF8` para `0xF0` esperado | Não alcançada |
| Equivalência de sense, BL/BLB, D/Q, SCLK, WL, NTAIL e pré-carga | Envelopes da rodada anterior preservados | Sem waveform integral para avaliar |

**Controle `INCONCLUSIVE`.** A solução inicial foi comprovada, enquanto a recuperação das leituras históricas permanece sem demonstração. O monitor preservou a evidência do erro e o gate manteve o v1 carregado como `NOT_RUN`. [Gate](../build/phase3/sclk_shared_ramp_20261120/control_gate.json)

**Próxima ação única:** preparar um recorte menor ao redor do driver compartilhado de SCLK, dos oito ramos e senses, da pré-carga e dos retornos extraídos. Priorizar a conservação da conexão e das capacitâncias nativas das placas relevantes, começando pela fronteira apontada em `VCUT205`. Onde o array for cortado, usar estímulos arquivados em pontos remotos e preservar a impedância pelo caminho extraído retido. Manter dispositivos do array nos caminhos em que faltarem sondas de fronteira suficientes. O critério de aceitação da nova bancada é um controle completo que reproduza as três decisões históricas e passe na equivalência de BL/BLB, SCLK, pré-carga e NTAIL. A redução proposta fica para outra rodada.

| Estado histórico | Veredito |
|---|---|
| Macro original TT | `FAIL` |
| Contraste ideal no recorte | `CORROBORATED` |
| Driver v1 isolado | `VIABLE_FOR_PHYSICAL_STUDY` |
| Driver v1 carregado | `NOT_RUN` |
| Monte Carlo | 200 Hold e 206 Read válidas no domínio experimental |
| Qualificação elétrica geral | `NOT_CHARACTERIZED` |

## Reprodução e integridade

**9/9 testes de software passaram**, quatro novos para integridade da translação, instrumentação, guardas e exigência de armazenamento, mais cinco do recorte carregado. A rodada acrescentou apenas este relatório, `tools/phase3_sclk_loaded_ramp.py` e `tests/test_phase3_sclk_loaded_ramp.py` ao espaço versionável. Os decks, manifestos e recibos estão em `build/phase3/sclk_shared_ramp_20261120/`. HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`, branch `integration/phase3-danilo-ss`, com alterações locais anteriores preservadas. [Regressões](../build/phase3/sclk_shared_ramp_20261120/tests.log)

Comandos usados, no checkout com o PDK e os arquivos históricos disponíveis. Para reprodução, escolha uma saída nova.

```bash
run=build/phase3/sclk_shared_ramp_20261120
script=tools/phase3_sclk_loaded_ramp.py
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" control --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 "$script" analyze --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sclk_loaded*.py' -v
```

| Artefato | SHA-256 |
|---|---|
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Recorte inalterado | `3f2f9cd987ff7903609716cf193d4e17c9ed3d36e5f37096c7df6fd73c620eb1` |
| Manifesto | `92ed4fce4a3156c2b9533248f0df13b8fa1d74a9e4373f9acf768d67a7c5be76` |
| Recibo | `380d6f7571a5ae481612cdc6a599078391f8844691ba5893397a6df3d0467ac8` |
| Gate | `001669b0fedccd1d39eaf9fa633a6b4a746d4c5319494c8ff7f325d99da89f4d` |
