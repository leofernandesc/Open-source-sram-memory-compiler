# Fase 3 — Auditoria temporal TT × SS da macro C 4×8

**Veredito `TIMING_HYPOTHESIS_SUPPORTED`.** Nas duas falhas do bit 3, a rampa observada do sampler antecipa-se ao desenvolvimento do diferencial em relação ao caso correto em SS. A primeira divergência lógica está no par do sense, antes de chegar a D/Q. A auditoria sustenta investigar a interação entre a janela de amostragem e a resposta local do latch. A condução exata na macro e a suficiência de uma intervenção na geometria completa permanecem inconclusivas.

## 1. Identidade e definições

Os ensaios integrados usam o mesmo GDS espaçado, LEF, binding, PEX integral, arquivo de fixture, sequência de 18 ciclos e sondas. O diff do deck contém apenas a seleção TT/SS na diretiva `.lib`. O ambiente SKY130A admitiu as duas seções e a árvore instalada de **319 arquivos** conferiu com os dois manifestos. Condições comuns de 1,8 V, 27 °C, CLK de 20 ns com rampas de 50 ps e fases de 10 ns, 10 fF/bit, limite de integração de 25 ps, KLU/Gear e guarda de bancada de 1,5 ns. Foram verificadas as cadeias de arquivos e logs, com os dois horizontes de 370 ns completos. [Recibos e matriz](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/measurements.json)

| Artefato | SHA-256 |
|---|---|
| GDS C | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF C | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| PEX padrão C | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Fixture integrada | `f92bfbadd3c7af8ef4309884613258608657b00f5fa9a8ce371f0c4d4c00533d` |
| Waveform integrado TT · 22.730 amostras | `2125aae7f92e94e81ca686c0519be5695ba72f370c0f7b0bcfefc8875a0cd1fd` |
| Waveform integrado SS · 20.539 amostras | `692e2218366c4d1797e53c9ee9924895e2e23eda54e3d22765f75b5ed24de44f` |

- **Clock e janelas.** Eventos absolutos em ns no transiente de 370 ns. A comparação entre fases usa CLK público ↑50 como origem, CLK público ↓50 e CLK local ↑50 no inversor de captura. Patamares digitais usam ≤0,36 V e ≥1,44 V. As demais porcentagens referem-se a VDD nominal. Estabilidade é a janela final contínua que termina na captura ou antes da sonda fraca, apoiada por pelo menos três pontos nativos. A sonda fica a 341,5 e 361,5 ns em c16/c17. O fim da observação de DATA/Q usado na matriz é 50 ps antes dela.
- **Pré-carga.** A subida do **gate do PMOS PRECH de BL da coluna 0**, `rc8510` (`macro_core.precharge_drive.X.t8`), marca a desabilitação comandada. PRECH é ativa em baixo. O alias do arquivo de sondas parece indicar a saída do driver, mas o terminal da forma de onda é esse gate remoto. Desligamento efetivo do PMOS, liberação do equalizador e sobreposição de correntes em b3 ficam `NOT_OBSERVED`.
- **Seleção e WL.** PCLK `rc8375` é uma referência de avaliação da rede, a chegada de `WL_IN` ao driver fica `NOT_OBSERVED`. Em c16/c17, WL `rc7928` (`bitcell_6t_24.WL.t0`) representa a linha 3; no integrado é o ponto da saída do driver dessa linha. Os gates de acesso da célula b3 são pontos distintos, disponíveis apenas no TT reduzido. WL20/50/80 medem evolução da linha e servem à comparação.
- **SCLK e latch.** O marcador da rede compartilhada é `rc8605`, no gate do sampler BL de b0. A saída física de `sense_drive` em `.X.t0/.t1` não foi gravada. Todos os oito gates do sampler BL foram gravados. Em b3 ele é `rc8584` (`.X.t17)); gate de BLB, tail, NTAIL, correntes e terminais internos do latch não foram gravados nos integrados. A separação medida usa `SA` na entrada do mux (`rc5991` em b3) e `SAB` no ponto retido (`rc8026`). Seu último zero antes da polaridade final é somente um marcador, com censura à esquerda quando a polaridade já estava presente ao abrir a janela.
- **Bitlines e dados.** BL/BLB são os terminais dos samplers, mapeados pelos MOS extraídos. Usa-se Δ = BLB−BL; para comparar polaridades, Δ assinado = `(1 − 2 × bit esperado) × Δ`. Conta-se a duração contínua de sinal correto que termina em SCLK20, limitada à janela desde WL20. D correto deve permanecer válido até a captura. Em Q, confere-se o valor adquirido e sua retenção até a próxima captura, ou até o fim do ensaio em c17. Uma releitura com Q já no mesmo nível fornece verificação de retenção e de sense/D, sem demonstrar um novo atraso de comutação.

Cruzamentos interpolados guardam os dois tempos nativos que os cercam. Para diferenças assinadas a matriz guarda também os extremos possíveis desses brackets. Em c16 TT o bracket de SCLK20 − WL80 é aproximadamente [−75, −25] ps. Em c17 TT é [−50, 0] ps. Em SS os mesmos brackets são [75, 125] e [100, 150] ps. Não há resolução comprovada para ordenar diferenças sub-picossegundo entre colunas. [Mapa físico das 32 células e oito senses](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/physical_probes.json) · [Contrato, §§3–4 e 8–10](../specs/sram_4x8_timing_contract.md)

## 2. Ciclos 16 e 17 · sense 3

**Tempos absolutos de referência, ns.** PRECH, PCLK e WL são os pontos mapeados acima; SCLK é o gate BL de b3.

| Corner · ciclo | CLK↑50 / CLK↓50 | PRECH20 / 50 / 80 | PCLK50 | WL20 / 50 / 80 | SCLK20 / 50 | Captura local |
|---|---|---|---|---|---|---|
| TT · 16 | 330,025 / 340,025 | 331,92 / 332,15 / 332,41 | 333,03 | 334,03 / 334,10 / 334,20 | 334,15 / 334,41 | ~340,06 |
| TT · 17 | 350,025 / 360,025 | 351,92 / 352,15 / 352,41 | 353,03 | 354,02 / 354,09 / 354,19 | 354,15 / 354,41 | ~360,06 |
| SS · 16 | 330,025 / 340,025 | 332,87 / 333,19 / 333,55 | 334,53 | 335,94 / 336,03 / 336,15 | 336,27 / 336,62 | ~340,07 |
| SS · 17 | 350,025 / 360,025 | 352,87 / 353,19 / 353,55 | 354,53 | 355,93 / 356,02 / 356,14 | 356,27 / 356,62 | ~360,07 |

| Corner · ciclo | PRECH50→WL50 / WL50→SCLK50 | SCLK20 − WL80 | WL em SCLK20 | Δ a SCLK20−50 ps / SCLK20 / SCLK50 | Δ positivo até SCLK20 | SCLK20→captura |
|---|---|---:|---:|---|---:|---:|
| TT · 16 | 1,95 ns / 0,31 ns | ~−43 ps | 1,25 V | −4 / +16 / +362 mV | ~33 ps | 5,90 ns |
| TT · 17 | 1,94 ns / 0,32 ns | ~−36 ps | 1,28 V | −2 / +21 / +374 mV | ~40 ps | 5,90 ns |
| SS · 16 | 2,84 ns / 0,59 ns | ~+114 ps | 1,67 V | +77 / +122 / +562 mV | ~187 ps | 3,80 ns |
| SS · 17 | 2,83 ns / 0,60 ns | ~+126 ps | 1,69 V | +88 / +134 / +576 mV | ~203 ps | 3,80 ns |

**Pré-carga e recuperação.** Nos dois corners, BL/BLB de b3 estão perto de 1,800 V antes da seleção e 1,826 V no PRECH50 da sonda. O comando amostrado sobe bem antes de WL; isso exclui uma sobreposição entre **esses marcadores**, sem comprovar as correntes de desativação/equalização no bit 3. Após CLK↓, as descidas de WL50, SCLK50 da sonda b0 e PRECH50 ocorrem, em c16, perto de 341,36 / 344,16 / 344,38 ns em TT e 341,99 / 346,22 / 346,59 ns em SS. Em c17 se repete a mesma ordem. BLB−BL passa de uma condição quase equalizada ao sinal correto, e permanece positivo de SCLK20 até o par de saída estabilizar nos quatro casos. [Tensões por evento](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/node_values.csv)

**Regeneração e captura.** Em TT o par observado troca para a polaridade final errada perto de **334,58/354,59 ns** e se torna estavelmente complementar errado em **334,78/354,80 ns**. Nesse instante Δ já é cerca de **+1,08/+1,12 V**, com sinal compatível com zero. D não apresenta nível baixo válido entre SCLK20 e a captura. D fica próximo de **1,803 V** na borda e a janela de D alto já está aberta no início da observação, de aproximadamente **5,90 ns**. O par lógico errado fica resolvido por cerca de **5,27/5,26 ns** antes da captura. O erro chega a Q e DATA, e as palavras são **0xF8**. Q do bit 3 já estava alto antes de c16 por causa de c15 e segue retido. Em SS o par correto estabiliza perto de **337,33/357,29 ns** e D fica baixo cerca de **2,25/2,34 ns** antes da captura, com **~1,7 mV** na borda; Q/DATA ficam baixos e as palavras são **0xF0**. Em SS c16 há transição em Q3 e c17 é releitura. O SS usa mais tempo da janela até a captura e resolve corretamente. Os 144 registros de bits mantêm o Q adquirido até o evento de captura seguinte ou fim do ensaio. A captura em TT observa uma decisão já errada no sense e não demonstra falta de setup. [Waveforms TT × SS](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/sense3_tt_vs_ss.png) · [Matriz em CSV](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/timing_by_bit.csv)

## 3. Outros senses e controles

Todos os oito bits em SS e os outros sete em TT passam em c16/c17 com sense, D e Q observados. A tabela mostra Δ assinado em mV no **próprio sampler BL** em SCLK20 e SCLK50. Cada célula da tabela reúne c16 / c17.

| Bit · esperado | TT SCLK20 | TT SCLK50 | Sense/D/Q TT | SS SCLK20 | SS SCLK50 | Sense/D/Q SS |
|---|---:|---:|---|---:|---:|---|
| 0 · 0 | 10 / 17 | 505 / 524 | 0 · PASS | 158 / 175 | 798 / 818 | 0 · PASS |
| 1 · 0 | 31 / 36 | 410 / 423 | 0 · PASS | 146 / 159 | 623 / 639 | 0 · PASS |
| 2 · 0 | 14 / 20 | 500 / 519 | 0 · PASS | 161 / 178 | 788 / 807 | 0 · PASS |
| **3 · 0** | **16 / 21** | **362 / 374** | **1 · FAIL** | **122 / 134** | **562 / 576** | **0 · PASS** |
| 4 · 1 | 32 / 37 | 390 / 403 | 1 · PASS | 141 / 154 | 593 / 608 | 1 · PASS |
| 5 · 1 | 15 / 20 | 444 / 460 | 1 · PASS | 146 / 162 | 700 / 718 | 1 · PASS |
| 6 · 1 | 27 / 32 | 350 / 362 | 1 · PASS | 127 / 138 | 531 / 545 | 1 · PASS |
| 7 · 1 | 16 / 21 | 424 / 440 | 1 · PASS | 141 / 156 | 668 / 684 | 1 · PASS |

- O deslocamento SCLK20 relativo ao marcador compartilhado b0 de SS para TT é indistinguível da resolução dos dados. Nos ciclos falhos, todos os bits de TT têm posição SCLK20 − WL80 da linha parecida. O bit 3 não tem atraso excepcional demonstrado no seu ramo. A marca SCLK20 de SS fica **~2,11 ns** mais tarde desde CLK↑ que em TT, enquanto WL80 fica **~1,95 ns** mais tarde. A folga relativa cresce **~157/161 ps**. PRECH50 e PCLK50 também atrasam **~1,05 ns** e **~1,50 ns**. O ambiente inteiro de avaliação muda, inclusive a subida 20–80 do sampler b3 de ~0,65 ns em TT para ~0,87 ns em SS. [Decomposição TT × SS](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/corner_decomposition.csv)
- Os bits 0 e 2 em TT passam com menor Δ assinado em SCLK20 que b3, e evoluem para Δ maior em SCLK50. Os bits 0, 2, 5 e 7 também passam apesar de sinal oposto 50 ps antes de SCLK20 nos dois ciclos. Em todo o conjunto, **22 bits corretos em TT** têm SCLK20 − WL80 negativo por interpolação. Isso contradiz a hipótese de que um desses dois marcadores isoladamente separa êxito de falha. Em SS todos os caminhos arquivados têm Δ assinado positivo em SCLK20. [Distribuição dos 144 caminhos](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/controls_all_bits.png)
- O próprio bit 3 em TT resolve zero com comutação em c7, linha 1, e c13, linha 0. Nessas leituras, Δ em SCLK20 é +73 e +128 mV e SCLK20 − WL80 é +26 e +71 ps. Em c14 na linha 1, resolve um com Δ de −108 mV e há comutação. Em c15, predecessor da linha 2, resolve um com ordem SCLK20 − WL80 de ~−42 ps e Δ de −32 mV. Q3 já estava alto nesse caso. C9 e SS c17 também incluem releituras sem mudança de Q3. Para a linha 3, a evidência de leitura correta no mesmo padrão é de SS; não há controle correto de leitura TT nessa linha. [Controles por ciclo e polaridade](../build/phase3/timing_audit_tt_ss_20261121/evidence_final/control_summary.json)

## 4. Evidência complementar e alcance causal

**TT reduzido de 250 ns, relógio próprio.** Mesmo PEX C, waveform `7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646`. Preserva os ciclos de origem 0, 1, 2, 3, 4, 5, 8, 10, 14, 15, 16 e 17, com compressão do intervalo entre operações. Em c16/c17 a referência da fixture está deslocada de −120 ns em relação à integrada. As medidas abaixo são nativas do ensaio reduzido. [Preflight e sondas](../build/phase3/data3_tt_20261120/preflight.json) · [Diagnóstico 250 ns](phase3_data3_tt_snm_piloto_20261120.md)

- A célula linha 3/b3 está em Q baixo e QB alto através das leituras. No próprio terminal de acesso `.WL.t8`, WL80 fica em **214,216/234,209 ns**. SCLK20 do sampler BL fica em **214,154/234,154 ns**, equivalente a **~−61/−55 ps** usando essa WL. No proxy de linha do mesmo TT reduzido, obtém-se ~−43/−36 ps. Essa diferença entre pontos físicos impede substituir a WL integrada por aquela do gate local, especialmente em SS.
- Os três gates locais `.X.t17, .t19 e .t18` marcam 20% perto de **214,15/234,15 ns** e 50% perto de **214,41/234,41 ns**. A ordem fina entre eles fica abaixo da resolução útil. NTAIL é ~**1,148 V** antes de c16/c17, ~**1,225 V** no tail20, ~**1,036 V** no tail50. Em tail50, o par local SAB−SA ainda tem **+78/+82 mV**, com sinal de zero. Por volta de **214,58/234,59 ns**, o par local cruza para o sinal errado. Em captura, SAB−SA está em **−1,798 V**, embora BLB−BL seja +1,45 V. Essa inversão após começar no sentido esperado é mais informativa que a tensão de SCLK20. Corrente do tail e da pré-carga continua `NOT_OBSERVED` no TT reduzido da macro. Não há SS reduzido com essas sondas para comparar NTAIL.
- **`CAUSALLY_SUPPORTED` no recorte controlado de 59 ns**, no qual o predecessor c15 restaura NTAIL e a intervenção de subida local ~182 ps corrige os dois casos em TT. No controle daquele recorte, a corrente de tail cruzou o marcador de 1 µA perto de 214,28/234,28 ns na referência temporal de 250 ns. Isso localiza condução no **recorte** e não um instante de current onset na macro integral. O contraste anterior por fonte no R87 da macro recuperou a palavra e também afetou sinais compartilhados. O driver físico v1 em bancada isolada não resolve a lacuna de fidelidade sob carga. [Controle e contraste isolados](phase3_precondicionamento_sense3_tt_20261120.md) · [Contraste R87 na macro e efeitos colaterais](phase3_contraste_completo_sclk_tt_20261120.md)

**Interpretação das classes.** `MEASURED` abrange os marcadores, o diferencial e a polaridade observada no latch, sense, D e Q. `CORRELATED` é a melhora de ~0,16 ns na relação WL–SCLK e de ~0,11 V no Δ de b3 em SS, junto à decisão correta. A diferença registrada começa na fase comum e se manifesta na evolução local das bitlines antes da divergência do par. `CAUSALLY_SUPPORTED` aplica-se à sensibilidade ao deslocamento dos gates no recorte. `INCONCLUSIVE` abrange qual parcela é atribuível a preparação de WL, corrente residual de pré-carga/equalização, injeção de carga, slew de SCLK, NTAIL ou regeneração assimétrica da macro. Um Δ pequeno em SCLK20 é comum a controles corretos e a margem requerida da SRAM não foi estabelecida. A evidência favorece uma **janela de avaliação precoce em relação à formação do diferencial, interagindo com a resposta do latch**, sem afirmar suficiência universal de atraso ou um valor mínimo de Δ.

## 5. Próximo experimento único proposto

**Contraste pareado de diferencial no recorte de 59 ns já validado**, com o controle TT que reproduz c16/c17 e mantém c15. Preserve SCLK, pré-carga, condições de contorno, impedâncias de replay e modo comum dos estímulos. No par de fronteiras BL/BLB da coluna 3, antecipe **somente** a componente diferencial durante a abertura de avaliação. Use como alvo a trajetória de Δ do replay TT que era disponível no contraste local bem-sucedido, com gate de fidelidade no terminal medido, limites físicos de alimentação e igualdade do histórico antes da intervenção. Registre corrente de tail, NTAIL, forma nos samplers, Δ/corrente nos terminais e polaridade complementar estável até a referência da captura. Se a decisão mudar com SCLK fixo e os estados forem equivalentes, haverá evidência de que a disponibilidade do diferencial explica a recuperação nesse recorte. Se o latch persistir errado apesar do diferencial-alvo confirmado, investigar a ação combinada de amostragem, injeção e tail. Um recorte que não conserve o condicionamento deixa o contraste inconclusivo.

O ramo de SCLK estudado anteriormente é **R87**, entre `macro_core.sense_drive.X.n0` e `.n6`, a jusante do `sense_drive` e em direção aos três gates locais da coluna 3. O novo contraste manteria R87 e o tap 80 intactos. O tap 80 também alimenta `macro_core.precharge_phase`; deslocá-lo mudaria PRECH e a recuperação, além da distribuição de SCLK. Nenhum ECO foi implementado.

## 6. Preservação e reprodução

Reanalisados **144 caminhos** em nove leituras por corner, **1.296 checkpoints** e o apoio TT de 250 ns, sem novo SPICE. **Sete testes offline passaram.** A edição local acrescentou este relatório e artefatos em área ignorada. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. Arquivos e resultados anteriores preservados, sem mudança física, commit, push ou merge.

C continua referência de integração, com **FAIL funcional TT**, **PASS funcional SS no escopo ensaiado** e qualificação geral `NOT_CHARACTERIZED`. B′ segue inconclusivo em c16/c17. O driver v1 está em espera e o Monte Carlo experimental permanece preservado. [Testes](../build/phase3/timing_audit_tt_ss_20261121/tests.log) · [Recibo final](../build/phase3/timing_audit_tt_ss_20261121/verification.json)
