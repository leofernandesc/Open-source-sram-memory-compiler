# Fase 3 — Isolamento causal do sense amplifier 3 em TT

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
O controle reduzido reproduziu as duas decisões incorretas da macro em TT.
Mesmo com BL/BLB e SCLK próximos da referência, `NTAIL` começou o ciclo 16
285 mV mais alto. A diferença persistiu durante a condução do tail.
O pré-condicionamento deixou o gate `INCONCLUSIVE` e o contraste de
182 ps ficou bloqueado. [Especificação](../specs/technical_specification.md) ·
[Contrato temporal](../specs/sram_4x8_timing_contract.md) ·
[Diagnóstico da macro](phase3_data3_tt_snm_piloto_20261120.md) ·
[Primeiro contraste](phase3_sclk_contraste_snm_20261120.md) ·
[Contraste completo R87](phase3_contraste_completo_sclk_tt_20261120.md)

## A. Circuito reduzido

O recorte conserva as instâncias `X102`, `X234`, `X235`, `X351`, `X521`,
`X1267` e `X1560` exatamente como no binding pós-layout. `X235` e `X521`
são os samplers BL/BLB. `X351` conecta `NTAIL` (`rc7187`) ao retorno
local `rc5874`, com bulk separado em `rc5873`. Os nós centrais SA/SAB
são `rc5990`/`rc8022`. Nos samplers são `rc5993`/`rc8025` e na saída
observada são `rc5991`/`rc8026`. As bitlines nos samplers são
`rc8210`/`rc8222`. Os gates BL, BLB e tail são `rc8584`, `rc8586` e
`rc8585`, respectivamente.

O recorte tem **36 MOS, 493 R e 968 C**. Inclui os 12 MOS do mux
receptor, os dois MOS de entrada do FF como carga de D, os três MOS
do pré-carregador/equalizador e os 12 MOS da lógica local de escrita
da coluna. A saída do sense e D são produzidos pelos MOS retidos.
O feedback de Q e os controles do receptor são reproduzidos nas
fronteiras. O FF completo e a interface DATA ficaram fora do recorte.

Os valores de R/C selecionados foram preservados. A alimentação e
o bulk usam as rotas extraídas da união de 57 caminhos resistivos
até VDD/VSS. O retorno local do tail é reproduzido a partir da sonda
histórica. Essa redução preserva os caminhos físicos escolhidos e
perde a carga dinâmica global da malha da macro. R87 conserva
6,46438 Ω. A cópia da bancada insere uma fonte de 0 V em série com
R87 para o controle. `C178` (4,28661 fF), `C155` (1,61725 fF) e
`C186` (0,19503 fF) continuam no nó compartilhado `rc8562`, separados
da possível excitação local do contraste.

Todos os **28.810 cartões excluídos** estão inventariados. Os
capacitores retidos mantêm valores e placas originais. Entre os
terminais reproduzidos ou terminados há 59 proxies com caminho
resistivo até uma sonda do mesmo nó lógico e 220 placas de sinais
não observados mantidas em potencial constante. Essa aproximação
conserva a capacitância e exclui o acoplamento dinâmico da placa
externa. Exemplos no latch são `C2910` de 0,95275 fF para um clock
interno e `C3995` de 0,37620 fF para a região do tap 48. O proxy do
SCLK compartilhado é a sonda `rc8605`, pois a referência não salvou
`rc8562`. A localização e a resistência de cada proxy estão no
manifesto. [Manifesto completo](../build/phase3/sense3_isolation_20261120/manifest.json) ·
[Elementos removidos](../build/phase3/sense3_isolation_20261120/removed.csv)

| Artefato | SHA-256 |
|---|---|
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Binding original | `40f4cc2f0da257b8435bcd387b938fcaba2b7456c3a74b3b350446fd5a434fc3` |
| Waveform TT original com `0xF8` | `7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646` |
| Recorte executado | `4c9cc67caa3bc8d3aa14d38461b1e18cbbe61a05915be4dd7abd34f8fbc7e3f7` |
| Estímulos executados | `5a7598024fb7b68fe0641840932cd7d3cd5487fc892bd7029d371a38a1a5532b` |
| Waveform do controle | `1ec8de9bb7112f453f87e714b3dfe827bf90cde26a9460b5acebfa7dfbb6feff` |

## B. Estímulos e critério de equivalência

As PWLs usam exclusivamente o waveform TT original de 250 ns.
A janela 208–247 ns dá 39 ns de transiente, incluindo 2 ns de
pré-condicionamento até a primeira subida pública, as duas avaliações
e a desativação seguinte. O ponto de operação foi calculado com os
valores de entrada arquivados. A partida ocorreu sem `.ic`,
`.nodeset`, `uic` ou fonte nas saídas e em NTAIL. A compactação linear
das PWLs limita o desvio a 0,100 mV na malha do arquivo de origem.

BL/BLB são impostas por fontes de tensão em `rc8202`/`rc8216`,
perto dos acessos da célula, deixando `rc8210`/`rc8222` responderem
à rede R/C e aos samplers. A resistência DC calculada por análise
nodal da malha passiva retida é **475,614 Ω para BL e 475,582 Ω para
BLB**. O pré-carregador, equalizador e write driver locais continuam
ativos como dispositivos, com seus controles arquivados. A fronteira
ideal elimina a realimentação para o array 6T a montante e sua
impedância incremental. A equivalência medida no controle refere-se
às trajetórias nos terminais dos samplers.
[Cálculo da resistência passiva](../build/phase3/sense3_isolation_20261120/passive_bl_impedance.json)

O critério selado exige SCLK a 20/50/80% dentro de 25 ps da
referência. Para BLB−BL em torno de SCLK20, a diferença admissível é
7,542 mV, metade do menor diferencial original observado nesse
marcador. Para o modo comum, é 15,085 mV, o valor desse mesmo
diferencial usado como escala experimental. Fora da vizinhança de
SCLK20, o envelope diferencial usa o maior entre 7,542 mV e 5% do
módulo do diferencial instantâneo. A decisão deve aparecer na mesma
fase e permanecer observável até a captura histórica, em níveis
20%/80%. Essas faixas avaliam a bancada reduzida. Elas não definem
sensibilidade, condução dos transistores ou especificações da macro.

## C. Controle sem atraso

Uma execução em ngspice **44.2/KLU**, SKY130A TT, 1,8 V, 27 °C,
com o fechamento original de 319 arquivos de modelos, Gear e passo
máximo de 25 ps. Concluiu em **11,847 s**, retorno `0`, sem erro de
convergência registrado, com **9.261 amostras** e corrente dos três
MOS amostrada. As adequações aos gates foram verificadas na mesma
escala temporal do waveform original.
[Recibo da execução](../build/phase3/sense3_isolation_20261120/control/result.json) ·
[Currents e sondas internas no ngspice](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf)

| Observação | c16 macro TT → controle | c17 macro TT → controle |
|---|---:|---:|
| SCLK20 no tail (ns) | 214,152765 → 214,154256 | 234,152509 → 234,154044 |
| BLB−BL 50 ps antes de SCLK20 (mV) | −4,014 → −4,322 | −2,199 → −2,583 |
| BLB−BL em SCLK20 (mV) | +15,085 → +15,450 | +19,946 → +20,524 |
| Modo comum em SCLK20 (V) | 1,872615 → 1,872590 | 1,869893 → 1,869668 |
| NTAIL antes da subida pública (V) | 1,148301 → 1,433247 | 1,147661 → 1,147639 |
| NTAIL em SCLK20 (V) | 1,225616 → 1,476737 | 1,225284 → 1,225133 |
| NTAIL em SCLK50 (V) | 1,036614 → 1,261968 | 1,035782 → 1,044031 |
| Inversão de SAB−SA durante avaliação (ns) | 214,579364 → 214,565074 | 234,590259 → 234,597004 |
| Primeira amostra da decisão errada sustentada (ns) | 214,791458 → 214,771258 | 234,814804 → 234,814804 |
| Tempo de SCLK20 até decisão errada sustentada (ps) | 638,69 → 617,00 | 662,29 → 660,76 |
| Sense na captura histórica | SA alto, SAB baixo em ambos | SA alto, SAB baixo em ambos |

O maior desvio de borda dos três gates foi **1,54 ps**. Na
vizinhança de SCLK20, o erro de BLB−BL ficou em **0,824/0,860 mV** e
o do modo comum em **0,598/0,598 mV**. Até a captura, os erros
máximos por janela foram até **1,474 mV** no diferencial e
**1,517 mV** no modo comum. Os quatro pontos do latch ficaram
próximos de 1,8 V no pré-condicionamento. A decisão `SA=1` incorreta
apareceu nos dois ciclos, com D perto de 1,800 V na captura
histórica. [Waveforms comparativos](../build/phase3/sense3_isolation_20261120/control_comparison.png) ·
[Medições e critérios](../build/phase3/sense3_isolation_20261120/control_gate.json)

**O estado inicial do tail limitou o gate.** Em c16, a diferença
de NTAIL foi **+284,95 mV** antes da subida pública, **+251,12 mV**
em SCLK20 e **+225,35 mV** em SCLK50. Nesse último ponto o tail
reduzido já conduzia **37,88 µA** pelo `id` registrado. Em SCLK20
eram cerca de 1,75 nA no tail, enquanto os samplers apresentavam
15,77 e 5,44 µA. Esses pontos distinguem corrente medida de
marcadores de gate e não fixam o início físico exato da condução.
A referência da macro não contém as correntes dos MOS.

Em c17, após uma avaliação e recuperação naturais no recorte,
NTAIL começou a **−0,023 mV** da referência e diferiu 8,25 mV em
SCLK50. Isso aponta para a ausência do histórico do ciclo
predecessor na partida de c16. A diferença de c16 permanece quando
o tail conduz corrente relevante. A reprodução da decisão por si
só é insuficiente para arredondar essa diferença a uma equivalência
de pré-condicionamento. O exame de NTAIL foi aplicado além dos
quatro pontos iniciais do latch, à luz do requisito explícito de
estado inicial equivalente. Usou a mesma escala de 30,169 mV
reservada à comparação inicial, excedida em mais de nove vezes.

Decisão observada nos dois ciclos **`REPRODUCED`**. Validade global
do controle **`INCONCLUSIVE`**. Autorização de contraste **bloqueada**.

## D. Contraste e conclusão causal

O contraste de 182 ps ficou **`NOT_RUN`**. O controle registra
somente a fonte de série R87 em 0 V. Portanto, esta rodada comprova
que o recorte reproduz a decisão incorreta sob tensões de entrada
e bordas de SCLK próximas da macro. Ela não mede atraso isolado,
correção da regeneração sob atraso ou um valor para um ECO.

| Frente | Estado |
|---|---|
| Macro original em TT | `FAIL`, duas leituras de `0xF8` |
| Macro TT com R87 | `PASS` funcional experimental, `0xF0` nos dois ciclos |
| Causalidade na macro completa | `INCONCLUSIVE` |
| Monte Carlo esquemático | Amostragem concluída no domínio experimental, 200 Hold e 206 Read |
| Qualificação elétrica geral | `NOT_CHARACTERIZED` |

**Próxima tarefa única.** Acrescentar o ciclo predecessor c15 ao
pré-condicionamento do controle, começando na pré-carga que o
antecede por volta de 188 ns, no mesmo recorte e sem forçar NTAIL.
Aceitar se o histórico reconstruído aproximar NTAIL de c16 antes
de avaliar e durante a condução, mantendo a fidelidade medida de
BL/BLB e SCLK e as duas decisões erradas sustentadas. A tarefa
permanece proposta. A impedância ativa do array e o acoplamento
global continuam relevantes para transferir qualquer resultado
isolado à macro física.

## Execução, arquivos e testes

A preparação consumiu cerca de 9 min 37 s desde o início da
rodada. Foi realizado **um transiente reduzido**, de 11,847 s.
Foram aprovados **oito testes de software**. Um erro de serialização
de booleanos NumPy interrompeu a primeira emissão do gate após
a simulação. A saída parcial e o analisador selado foram arquivados.
O analisador passa a usar tipos nativos e verifica NTAIL além das
saídas do latch. O gate definitivo foi obtido dos mesmos arquivos
brutos, sem repetir SPICE. [Testes](../build/phase3/sense3_isolation_20261120/tests.log) ·
[Saída parcial preservada](../build/phase3/sense3_isolation_20261120/control_gate_serialization_partial.json)

Comandos do controle e da reanálise. Para reproduzir a simulação
em outra rodada, use um diretório novo com os arquivos de
referência arquivados disponíveis. O gate desta execução impede
o estágio `contrast`.

```bash
run=build/phase3/sense3_isolation_20261120
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 \
  tools/run_phase3_sense3_isolation.py prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 \
  tools/run_phase3_sense3_isolation.py control --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 tools/analyze_phase3_sense3_isolation.py \
  control --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg python3 \
  tools/export_phase3_sense3_evidence.py --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_phase3_sense3_isolation.py' -v
```

O ZIP contém o runner, o analisador, o exportador, a suíte, este
relatório, o manifesto, o inventário de exclusões, o deck, os dados e
recibos do controle e `SHA256SUMS`. O HEAD, a branch e os arquivos
físicos foram preservados. As alterações locais preexistentes
continuam no checkout. Sem commit, push ou merge.
