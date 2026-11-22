# Fase 3 — Pré-condicionamento do sense 3 e contraste local de SCLK em TT

O controle estendido foi **`VALIDATED`**. O ciclo 15 reduziu a diferença de NTAIL antes da subida pública do ciclo 16 de **+284,95 mV** para **−0,034 mV**, com as duas decisões incorretas ainda presentes. No contraste pareado, atrasar localmente a subida de SCLK manteve os demais estímulos e corrigiu as duas decisões até o instante de referência da captura. O veredito causal no recorte é **`CORROBORATED`**. [Diagnóstico da macro original](phase3_data3_tt_snm_piloto_20261120.md) · [Controle anterior](phase3_isolamento_causal_sense3_tt_20261120.md)

## A. Extensão do histórico

O replay passou de **208–247 ns** para **188–247 ns**, em tempo da referência arquivada de 250 ns. Na referência, a descida anterior de SCLK20 ocorreu em 184,274 ns e a do controle de pré-carga em 184,506 ns. Em 188 ns o clock público estava baixo, BL/BLB já estavam em 1,799882/1,799859 V e SA/SAB estavam altos. O SCLK20 do ciclo 15 subiu em 194,153 ns e voltou a cair em 204,270 ns. O replay contém a avaliação e a recuperação completas que antecedem o ciclo 16. [Manifesto e marcadores](../build/phase3/sense3_preconditioned_20261120/manifest.json)

O recorte anterior foi copiado byte a byte com **36 MOS, 493 resistores e 968 capacitores**. Os 300 terminais, incluindo os pontos aplicados em `rc8202`/`rc8216`, preservaram conectividade, valores e proxies. Nos 80 terminais com PWL, o trecho anterior a 208 ns foi interpolado a partir da referência original, com erro máximo de compressão de 0,09998 mV nas amostras arquivadas. De 208 ns em diante, todos os pares tempo–tensão anteriores foram preservados após translação exata da origem. O controle conservou `VSHIFT sclk_driver rc8562 0`. NTAIL evoluiu como nó interno, sem fonte ou condição inicial imposta. [Gerador](../tools/phase3_sense3_precondition.py) · [Características do recorte](phase3_isolamento_causal_sense3_tt_20261120.md)

Os ensaios usaram TT SKY130A, 1,8 V, 27 °C, Gear com passo máximo de 25 ps e o PEX padrão do candidato roteado espaçado. Os 319 arquivos da árvore de modelos corresponderam ao manifesto anterior. A janela de referência de captura preserva o contrato de leitura síncrona. A instrumentação reduzida observa o sense e D, sem reconstruir o registrador completo ou a interface DATA. [Especificação 4×8](../specs/technical_specification.md#15-read-operation) · [Contrato temporal](../specs/sram_4x8_timing_contract.md#3-clock-e-responsabilidades-de-captura)

## B. Controle sem atraso

O novo controle convergiu em **13,700 s** e produziu **13.980 amostras**, com retorno 0. No início em 188 ns, NTAIL ainda diferia em cerca de +303 mV. A avaliação natural do ciclo 15 descarregou o nó. Em 208 ns, após a recuperação, NTAIL estava em 1,130411 V no recorte e em 1,130468 V na macro original. [Waveform de condicionamento](../build/phase3/sense3_preconditioned_20261120/precondicionamento_ntail.png)

| Evidência | Ciclo 16 | Ciclo 17 |
|---|---:|---:|
| ΔNTAIL antes da subida pública, 209,9/229,9 ns | −0,034 mV | −0,024 mV |
| ΔNTAIL em SCLK20 correspondente de cada ensaio | −0,127 mV | −0,153 mV |
| ΔNTAIL em SCLK50 correspondente de cada ensaio | +8,701 mV | +8,247 mV |
| Corrente do tail em SCLK50 no recorte | 34,51 µA | 34,55 µA |
| Início do primeiro intervalo com `abs(Id) ≥ 1 µA` | 214,277 ns | 234,278 ns |
| Pico de corrente no primeiro intervalo de condução | 133,23 µA | 133,18 µA |
| Maior `abs(ΔNTAIL)` em tempos comuns | 12,717 mV a 214,378 ns | 13,210 mV a 234,401 ns |
| ΔNTAIL no instante comum de SCLK20 de descida do controle | −1,235 mV | −1,330 mV |
| ΔNTAIL 1 ns depois da desativação | +0,258 mV | +0,284 mV |
| Maior erro de BLB−BL perto de SCLK20 | 0,837 mV | 0,864 mV |
| Maior erro de modo comum na janela de leitura | 1,508 mV | 1,519 mV |
| Regeneração errada, primeira amostra válida macro → recorte | 214,791 → 214,797 ns | 234,815 → 234,815 ns |
| Decisão sustentada até a captura | SA alto / SAB baixo, D alto | SA alto / SAB baixo, D alto |

A medição contínua usa a união dos pontos nativos dos dois waveforms e interpolação linear. As janelas foram fixadas em **[209,9; 229,9] ns** e **[229,9; 247] ns**. Não houve intervalo interpolado acima do envelope de ±30,169 mV, inclusive quando o tail conduzia e durante a recuperação. O marcador de corrente de 1 µA identifica trechos de condução no recorte. A referência da macro disponibiliza tensões nesses nós, sem corrente arquivada nos MOS. Os pontos SCLK20/SCLK50 das duas séries são comparados por fase, e a tabela contínua do gate também registra os deltas no mesmo tempo absoluto. [Gate de controle](../build/phase3/sense3_preconditioned_20261120/control_gate.json)

Os limites anteriores para BLB−BL foram preservados, com 7,542 mV na vizinhança de ±50 ps de SCLK20 e, fora dela, o maior entre 7,542 mV e 5% do diferencial de referência. O limite de modo comum permaneceu 15,085 mV. Todas as bordas locais passaram o envelope de 25 ps. A inversão de polaridade do latch ocorreu dentro de 7,6 ps em relação à macro nos dois ciclos. A decisão errada manteve-se estável por mais de 5,24 ns antes da referência de captura. A equivalência é suficiente dentro desses critérios experimentais. [Gate de controle](../build/phase3/sense3_preconditioned_20261120/control_gate.json)

## C. Contraste local de +182 ps

O contraste convergiu em **20,515 s**, com **15.525 amostras** e retorno 0. Foi autorizado pelo gate de controle e pela verificação dos respectivos hashes. O único arquivo SPICE diferente entre os ensaios foi `clk_delta.spice`. A fonte em série atua no lado local de R87 que alimenta os gates dos samplers BL/BLB e do tail. Ela sintetiza a diferença entre a borda original e a deslocada, com suporte nas janelas 213,85–216,35 ns e 233,85–236,35 ns. O proxy externo SCLK, a pré-carga, VDD e todos os pontos PWL de BL/BLB foram mantidos. [Recibo de execução](../build/phase3/sense3_preconditioned_20261120/contrast/result.json) · [Fonte local](../build/phase3/sense3_preconditioned_20261120/contrast/clk_delta.spice)

| Ciclo | Gate | Atraso subida 20% (ps) | 50% (ps) | 80% (ps) |
|---|---|---:|---:|---:|
| 16 | Sampler BL | 182,520 | 181,805 | 182,399 |
| 16 | Sampler BLB | 182,202 | 181,900 | 181,497 |
| 16 | Tail | 182,013 | 181,996 | 181,830 |
| 17 | Sampler BL | 182,486 | 181,808 | 182,385 |
| 17 | Sampler BLB | 182,192 | 181,898 | 181,463 |
| 17 | Tail | 182,012 | 181,996 | 181,960 |

Os três gates atenderam a 182 ± 25 ps. O maior deslocamento de descida foi 0,475 ps e a maior alteração no slew20–80 de subida foi de 0,729 ps. O patamar alto permaneceu entre 1,79996 e 1,79998 V e o baixo abaixo de 0,212 mV. A fase ativa, medida a 50%, encurtou entre 181,64 e 182,28 ps, conforme esperado ao preservar a descida. [Comparação de bordas](../build/phase3/sense3_preconditioned_20261120/contrast_gate.json)

| Grandeza, controle → contraste | Ciclo 16 | Ciclo 17 |
|---|---:|---:|
| NTAIL antes da subida pública (V) | 1,148267 → 1,148267 | 1,147638 → 1,147620 |
| SCLK20 do tail (ns) | 214,154256 → 214,336269 | 234,154044 → 234,336057 |
| BLB−BL, 50 ps antes de cada SCLK20 (mV) | −4,33 → +154,31 | −2,59 → +164,08 |
| BLB−BL em cada SCLK20 (mV) | +15,43 → +228,58 | +20,52 → +239,34 |
| Modo comum em cada SCLK20 (V) | 1,87257 → 1,72862 | 1,86967 → 1,72076 |
| Início do primeiro intervalo `abs(Id) ≥ 1 µA` (ns) | 214,277178 → 214,462342 | 234,277570 → 234,463029 |
| BLB−BL no início desse intervalo (mV) | +146,51 → +458,22 | +157,16 → +472,54 |
| Corrente de pico no primeiro intervalo (µA) | 133,23 → 157,85 | 133,18 → 158,30 |
| SAB−SA nos nós dos samplers, em cada SCLK20 (mV) | −4,19 → +123,55 | −1,86 → +130,95 |
| SAB−SA na referência temporal da captura (V) | −1,800 → +1,800 | −1,800 → +1,800 |
| Primeira amostra da decisão que se manteve válida (ns) | 214,797458 → 215,006858 | 234,814804 → 235,005204 |
| Margem observada antes da captura de referência (ns) | 5,261 → 5,051 | 5,243 → 5,053 |
| Decisão até a captura e D no mesmo instante | **errada → correta**, 1,80045 → 0,00020 V | **errada → correta**, 1,80045 → 0,00020 V |

O gate verifica níveis sustentados de SA/SAB até a referência de captura, usando 0,36/1,44 V e amostras nativas. No controle, SAB−SA cruza de positivo a negativo por volta de 214,587/234,597 ns e permanece negativo até a captura. Com atraso, a polaridade já era favorável na ativação e não se inverteu durante a regeneração avaliada. [Waveforms pareados](../build/phase3/sense3_preconditioned_20261120/regeneracao_pareada.png) · [Pontos e janelas medidos](../build/phase3/sense3_preconditioned_20261120/comparison_details.json)

Antes da primeira intervenção, os nós ponderados na comparação diferiram no máximo **44 nV**. Nos dois ciclos, os controles e terminais externos medidos diferiram no máximo **0,34 µV**, compatível com a amostragem/interpolação de PWLs idênticas. Nos terminais internos dos samplers, a maior diferença em BLB−BL no mesmo tempo absoluto foi **11,81 mV**. No instante de SCLK20 do contraste, o controle já tinha desenvolvido **237,12/248,23 mV**, contra **228,58/239,34 mV** no contraste. A maior parte da diferença observada nos respectivos instantes de ativação resulta do tempo adicional de desenvolvimento, enquanto a mudança de condução dos samplers também altera a trajetória local. [Comparação pareada](../build/phase3/sense3_preconditioned_20261120/comparison_details.json)

Com a decisão complementar, NTAIL e SA/SAB seguem uma recuperação diferente. Os dois níveis de saída do latch voltaram à banda alta no contraste por volta de 225,002 ns e 245,000 ns, cerca de 233 ps depois do controle. Ambos já estavam altos no pré-condicionamento seguinte e continuavam altos no fim do transiente. O NTAIL inicial do ciclo 17 diferiu **−0,018 mV** entre controle e contraste. A recuperação distinta foi medida e não comprometeu o segundo ensaio de regeneração. [Waveforms e correntes](../build/phase3/sense3_preconditioned_20261120/)

## D. Conclusão e próxima ação

**Controle `VALIDATED` · Hipótese temporal no recorte `CORROBORATED`.** O histórico acrescentado estabeleceu um estado inicial comparável e preservou as duas falhas. Com o mesmo recorte e os mesmos estímulos de fronteira, a única intervenção deliberada de SCLK foi suficiente para corrigir a regeneração nos ciclos 16 e 17. O ensaio sustenta estudar um ECO temporal. Ele não determina o atraso mínimo ou separa quantitativamente os efeitos de diferencial, modo comum e carga injetada pelos samplers.

A transposição física exige verificar a entrega do atraso no caminho real de SCLK. O recorte preserva resistências de aproximadamente 475,6 Ω entre as fontes de replay remotas e os terminais dos samplers, mas omite a impedância dinâmica do array completo, usa proxies para 59 terminações e mantém 220 placas capacitivas externas a potencial fixo. A intervenção em série ideal não demonstra o efeito de um driver físico sobre as cargas comuns da macro.

**Próxima ação única:** construir um candidato esquemático de atraso local com driver e carga representativos, preservando a descida e sem atuar no ramo compartilhado. Aceitá-lo para estudo físico quando a bancada pareada reproduzir o envelope medido nos três gates, preservar a pré-carga e WL e manter ambas as decisões corretas até a captura. Esta rodada encerrou no contraste reduzido.

| Escopo | Estado |
|---|---|
| Macro original em TT | `FAIL`, `0xF8` em vez de `0xF0` nos ciclos 16 e 17 |
| Macro TT com fonte R87 | `PASS` funcional experimental |
| Atribuição causal na macro completa | `INCONCLUSIVE` |
| Monte Carlo esquemático | 200 Hold e 206 Read válidas no domínio experimental |
| Qualificação elétrica geral | `NOT_CHARACTERIZED` |

## E. Reprodução e integridade

Foram executados dois transientes reduzidos de 59 ns, com **34,215 s de tempo de simulador somado**. Os testes pertinentes passaram **14/14**, oito preexistentes e seis novos. Eles verificam a preservação da série histórica, a intervenção limitada a duas janelas, a detecção de excursões entre marcadores e o bloqueio de um gate sem validação ou sem hash correspondente. [Regressões](../build/phase3/sense3_preconditioned_20261120/tests.log)

Para reproduzir no checkout com os artefatos arquivados e o ambiente EDA, use um diretório novo. O runner bloqueia a execução do contraste se o controle novo não validar.

```bash
out=build/phase3/sense3_preconditioned_reproduction
script=tools/phase3_sense3_precondition.py
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" prepare --output "$out"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" control --output "$out"
PYTHONDONTWRITEBYTECODE=1 python3 "$script" analyze-control --output "$out"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" contrast --output "$out"
PYTHONDONTWRITEBYTECODE=1 python3 "$script" analyze-contrast --output "$out"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sense3*.py' -v
```

Para recalcular as figuras e os checkpoints, execute com NumPy e Matplotlib no ambiente EDA, apontando `PYTHONPATH=tools` e copiando `export_comparison.py` ao diretório novo. [Código de exportação](../build/phase3/sense3_preconditioned_20261120/export_comparison.py)

| Evidência | SHA-256 |
|---|---|
| Referência TT original de 250 ns | `7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Recorte SPICE preservado | `4c9cc67caa3bc8d3aa14d38461b1e18cbbe61a05915be4dd7abd34f8fbc7e3f7` |
| Gate anterior, `INCONCLUSIVE` | `285bf6e021e48ee069f14fd88188bb54452f414b8abb2913c298e61abda6977a` |
| Manifesto do pré-condicionamento | `77c4074ee89750e32f2fa2cd7c8ff86ea784c5fcf06f96b4ce122444f7e6cea2` |
| Waveform do controle | `5954927da87434f44fe067d422c9e55769b62051d01225ef9587ed9ea6199fd5` |
| Waveform do contraste | `b216d30a1dd8dd6e17ef99b6c7006e11ccc20239e758c97314118050e242d642` |

A execução deixou três arquivos novos no espaço versionável: este relatório, `tools/phase3_sense3_precondition.py` e `tests/test_phase3_sense3_precondition.py`. Os decks, waveforms, logs, figuras, recibos e manifestos estão em `build/phase3/sense3_preconditioned_20261120/`. O HEAD continua em `8e1d961d65054b59f9032ed5f9338d9ee4353c33`, na branch `integration/phase3-danilo-ss`. A rodada ficou local, sem commit, push ou merge.
