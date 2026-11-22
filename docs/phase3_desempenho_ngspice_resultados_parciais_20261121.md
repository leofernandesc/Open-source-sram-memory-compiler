# Fase 3 — Desempenho do ngspice e recuperação parcial

**Decisão para o Marco 3 de 23/11/2026 — `ABANDON_CONTRAST_RECOMMENDED`.** Retirar o contraste B′ × C da prioridade imediata e manter C como referência de integração. O gate para uma nova execução do contraste está **`NOT_READY`**. O mecanismo de exportação por pausa programada foi verificado em RC. A causa numérica específica da desaceleração segue indeterminada e a projeção de custo ultrapassa o orçamento original até no cenário otimista. B′ segue sem veredito nos ciclos 16/17. [Tentativa arquivada](phase3_contraste_b_prime_c_tt_20261121.md) · [Critério de autorização](../build/phase3/ngspice_performance_20261121/instrumentation_plan.json)

## A. Desempenho observado

A auditoria conferiu os SHA-256 do deck, da fixture, do JSONL e dos logs com o recibo original. O CSV de progresso coincide com a projeção da telemetria nativa. Os limites de cada intervalo foram obtidos por interpolação entre os dois polls que cercam o marcador de `Reference value`, separados por cerca de 5 s. O início em 0 ns usa a emissão de `Initial Transient Solution`. Os limites do poll ficaram no JSON, pois o cruzamento pode ocorrer entre amostras e a emissão de progresso tem cadência própria. Isso mede o avanço observado do simulador. [Cálculo e brackets](../build/phase3/ngspice_performance_20261121/performance.json) · [Figura de progresso e custo](../build/phase3/ngspice_performance_20261121/desempenho_b_prime.png)

| Etapa | Tempo real / marcador final | s reais por ns | ns por min real | CPU, % de um núcleo | RSS entre primeiros e últimos polls |
|---|---:|---:|---:|---:|---:|
| Preparação até despacho de `tran` | 194,34 s | — | — | 99,82% mediana | ~20 → 1.513 MiB |
| Solução inicial após despacho | 13,46 s | — | — | 99,91% mediana | ~1.553 → 1.554 MiB |
| 0–50 ns | 567,14 s / 774,93 s | 11,34 | 5,29 | 99,96% | 1.553 → 1.490 MiB |
| 50–70 ns | 342,64 s / 1.117,57 s | 17,13 | 3,50 | 99,87% | 1.490 → 1.310 MiB |
| 70–80 ns | 675,37 s / 1.792,94 s | 67,54 | 0,89 | 99,77% | 1.302 → 940 MiB |
| 80–85,8258 ns | 602,80 s / 2.395,75 s | 103,47 | 0,58 | 99,99% | 940 → 924 MiB |

O total do processo foi 2.398,34 s. O último progresso reportado ocorreu cerca de 2,59 s antes do encerramento. O fallback de ponto de operação concluiu com sucesso. A integração usou aproximadamente um núcleo e todos os 472 polls encontraram o processo em estado `R`. O pico registrado foi 1.591.084 KiB e o RSS caiu durante a região mais cara. Entre 70 e 80 ns, os contadores mostraram cerca de 11,2 MiB de leitura física do processo dentro da janela amostrada. De 80 a 85,8258 ns esses contadores de leitura e escrita ficaram constantes. O conjunto sustenta custo computacional na integração. A telemetria não demonstra esgotamento de RAM, espera sustentada por I/O ou qual parte do solver consumiu a CPU. Também não mede faltas de página nem permite excluir toda influência do sistema. [Intervalos e contadores](../build/phase3/ngspice_performance_20261121/intervals.csv)

### Eventos entre 65 e 90 ns

| Tempo programado | Evento de estímulo | Comportamento interno esperado pelo contrato |
|---|---|---|
| 65–67 ns | CLK baixo, endereço 0, host forte em `0xAA` | Depois da escrita c2, WL/WE liberados e retorno à pré-carga |
| 67–67,05 ns | ADDR passa de 0 para 1 | A escolha externa deve ser capturada apenas na próxima subida |
| 67,10–67,15 ns | Oito fontes HOST mudam `0xAA` → `0x55` com o mesmo dono do barramento | Dado externo preparado para DIN de c3 |
| 70–70,05 ns | CLK sobe | Captura linha 1 e DIN. A lógica qualifica WE por WRITE_Q e tap 40 e avalia a WL da linha 1 via PCLK/tap 48, após liberação de pré-carga. A fase de sense de leitura não é pedida nesse ciclo. |
| 80–80,05 ns | CLK desce | WE e WL devem liberar e a pré-carga/equalização deve retornar na fase baixa. Os instantes internos efetivos não estão disponíveis. |
| 87–87,05 ns | ADDR passa de 1 para 2 | Preparação da escrita c4 |
| 87,10–87,15 ns | HOST muda `0x55` → `0x0F` em quatro bits | Preparação de DIN da linha 2 |
| 90 ns em diante | Próxima subida de CLK | A escrita de condicionamento da linha 2 ainda não foi atingida no run |

WEb e CSb permaneceram em 0 V, OEb e o enable forte em 1,8 V, enable fraco em 0 V, e a alimentação em 1,8 V. Houve **zero handoffs programados** no intervalo. A contagem é de 25 cartões PWL externos e 489 pontos no deck externo completo. Entre 65 e 90 ns, incluindo o começo da rampa em 90 ns, houve 57 pontos em 13 instantes distintos, dos quais 35 mudaram a inclinação. Todos os tempos de cada fonte são estritamente crescentes e os estímulos são contínuos por trechos. Esses números incluem pontos redundantes de valor constante e não contam breakpoints internos do simulador. [Estados externos e PWL](../build/phase3/ngspice_performance_20261121/fixture_states_65_90.csv) · [Inventário por fonte](../build/phase3/ngspice_performance_20261121/fixture_knots_65_90.csv) · [Contrato temporal](../specs/sram_4x8_timing_contract.md)

O custo subiu de **5,09 s/ns em 65–67** para **46,37 s/ns em 67–70**, antes da subida que captura c3. Portanto a queda já coincide com a troca de endereço/payload sob o mesmo dono. Entre 70 e 75 ns foram 83,89 s/ns; entre 81 e 82 ns, já em CLK baixo e sem rampa PWL externa programada, foram 192,84 s/ns. Há lentidão dentro e depois da fase de escrita. A sequência externa oferece marcadores para instrumentação; ela não identifica uma causa no driver de escrita, na WL, no sense ou no roteamento. Eventos internos de controle, refinamento de passos, custo por iteração e custo de sistemas lineares são hipóteses. [Trechos locais](../build/phase3/ngspice_performance_20261121/local_rates_65_85.csv)

O stdout tem a solução inicial e marcadores de progresso, sem histórico de intervalos aceitos/rejeitados, iterações de Newton, ordem de Gear ou custo por solve. Os avisos de matriz singular, `dynamic/true gmin stepping` e `source stepping` referem-se à solução inicial, antes do avanço. Nenhum erro fatal durante o transiente foi anotado. O encerramento registrado foi por SIGTERM do monitor no teto de parede. A instrumentação futura precisa separar densidade de passos aceitos, rejeições/iterações e custo de CPU por intervalo. A saída compacta `rusage traniter tranpoints accept rejected` funcionou no circuito RC e é uma base para deltas em checkpoints de diagnóstico. [Logs arquivados](../build/phase3/b_prime_tt_20261120/run/stderr.log) · [Manual ngspice 44, §13.5.70](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf#page=407)

## B. Recuperação e retomada

O deck arquivado chama `wrdata waveform.dat` após `tran`. Com SIGTERM antes do retorno, o comando ficou por executar, e `Reference value` contém apenas tempo. Os valores já calculados naquela tentativa não são recuperáveis pelos artefatos remanescentes.

| Mecanismo em ngspice 44.2 | Evidência e uso possível |
|---|---|
| `stop when time = …` e exportação logo após a pausa | **`VERIFIED_RC_PROGRAMMED_STOP`**. Preserva o prefixo até o último export fechado. Se o processo morrer entre pausas, o trecho após o último export continua vulnerável. Breakpoints induzem instantes na malha adaptativa e exigem avaliação de equivalência se usados para a comparação funcional. |
| `ngspice -n -b -r live.raw` com uma `.tran` de topo e `.save` | Suportado e documentado. O fonte 44.2 escreve vetores por frame binário e preenche `No. Points` no fechamento. `NOT_VERIFIED` contra interrupção no executável local nesta rodada. A sequência sintética acabou antes de chegar a essa etapa. O recuperador de frames completos foi testado com bytes construídos em Python. |
| `stop` / `resume` no mesmo processo, inclusive `bg_halt` / `bg_resume` na API compartilhada | Documentado para continuidade de um processo vivo. Sem demonstração de continuidade em B′ ou neste ensaio. A API exporta callbacks de vetores durante a execução, com integração adicional a validar. |
| `snsave` / `snload` / `resume` | O binário local emitiu um snapshot RC. A execução terminou com SIGSEGV antes de produzir o segmento restaurado. O log não localiza a instrução que causou o sinal. Retomada e equivalência com a referência ininterrupta ficaram **`NOT_VERIFIED`**. |
| Novo `tran` com tempo de início de saída deslocado, ou inicialização por tensões de um waveform | Alterar o início da saída não evita integrar o prefixo. Uma nova análise com tensões impostas não prova a preservação de históricos de integração, estados de dispositivos, NTAIL e controles. |

A fonte de versão exata foi consultada no pacote de código 44.2 distribuído por Debian. Em `src/frontend/outitf.c`, `fileStartPoint` prepara o header, `fileEndPoint` escreve o frame, `fileEnd` atualiza o contador. Buffers ainda não entregues ao SO podem se perder. O leitor experimental exige um único plot transiente real, precisão dupla e ordem de bytes x86-64, inventário exato de vetores, tempos crescentes e amostras finitas. Conserva o RAW original e registra SHA-256, último instante íntegro e bytes incompletos descartados no CSV derivado. Um plot fechado com comprimento inconsistente é recusado. [Manual ngspice 44, §§12.8, 13.5.67–69 e 13.5.84–91](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf) · [Código-fonte 44.2](https://deb.debian.org/debian/pool/main/n/ngspice/ngspice_44.2+ds.orig.tar.gz) · [Recuperador experimental](../build/phase3/ngspice_performance_20261121/raw_prefix.py)

### Teste único de bancada RC

Uma invocação do ngspice 44.2 com **0,460 s** de parede, Gear/KLU, fonte PWL, resistor de 1 kΩ e capacitor de 10 pF, sem macro, MOS ou PDK. A mesma fixture executou uma referência contínua de 200 ns e uma análise interrompida por breakpoint em 80 ns. O prefixo exportado antes da falha contém **3.215 amostras**, de 0 a 80 ns, com tempos estritamente crescentes e valores finitos. Em 80 ns, foram encontrados 1,000 V na entrada, 0,995741 V na saída e −4,259156 µA na fonte. O erro de saída frente à referência ininterrupta, interpolada nos tempos do prefixo, foi ≤3,33 nV. Contra a solução analítica PWL–RC, foi ≤0,782 µV. Esse resultado verifica o mecanismo de preservação, mesmo após a saída anormal do processo. A comparação de continuidade após recarga ficou sem dados porque `resumed.dat` não foi produzido. O RAW incremental tampouco foi produzido. Nenhuma segunda invocação foi feita. [Recibo da execução](../build/phase3/ngspice_performance_20261121/synthetic/receipt.json) · [Validação do prefixo](../build/phase3/ngspice_performance_20261121/partial_validation.json) · [Log](../build/phase3/ngspice_performance_20261121/synthetic/ngspice.log)

**Plano de preservação.** Para um diagnóstico autorizado, a opção demonstrada é uma pausa em marcador físico predefinido, exportação para arquivo temporário e publicação após validação dos vetores, timestamps e hash. Ao comparar tempos, registre também o grid introduzido pela pausa. O RAW incremental é preferível para observar uma execução sem novos breakpoints, após prova end-to-end com término antes do horizonte. A retomada de solver tem gate independente e fica fora da autorização enquanto a continuidade permanecer sem verificação. [Plano e gates](../build/phase3/ngspice_performance_20261121/instrumentation_plan.json)

## C. Horizonte e fidelidade

A sequência mínima defensável conserva a rampa de VDD e o condicionamento de partida, as escritas de 0x0F na linha 2 e 0xF0 na linha 3, o histórico da linha 1 usado em c14, a avaliação predecessor c15 e a recuperação antes e entre c16/c17. Também conserva o CLK, as janelas de avaliação e pré-carga, o histórico de Q, o dono do barramento e o intervalo de observação depois da captura de c17.

A escrita de 0x55 na linha 1 em c3 é sobrescrita por 0xAA em c10 antes de c14. Removê-la, ou eliminar outra operação sem leitura de retorno, pode parecer equivalente no histórico digital. Ainda falta demonstrar igualdade do estado elétrico da matriz, alimentação, seleção, drivers e latch quando os ciclos de interesse começarem. A auditoria anterior mostrou, no recorte de C, que incluir c15 mudou o desvio inicial de NTAIL de +284,95 mV para −0,034 mV e foi necessário para validar o controle. Essa dependência impede deslocar apenas c16/17 para o início. Terminar logo após o último restore e fim da sonda em 245,55 ns reduziria menos de 4,5 ns e eliminaria parte da verificação final de retenção. **Compressão `NOT_VALIDATED`**. A referência continua sendo a sequência de 250 ns, sem alteração do deck. [Pré-condicionamento de NTAIL](phase3_precondicionamento_sense3_tt_20261120.md) · [Fixture original](../build/phase3/b_prime_tt_20261120/run/fixture.json)

## D. Projeção de custo e decisão

As projeções somam o custo observado até a interrupção ao custo hipotético dos 164,1742 ns restantes no ritmo escolhido. Servem para dimensionar uma nova execução desde a partida. A coluna dos 164,1742 ns ilustra a extrapolação, sem pressupor que exista um estado de solver recuperável da tentativa atual.

| Cenário | Ritmo usado, s reais/ns | 164,1742 ns adicionais | Tempo total projetado |
|---|---:|---:|---:|
| Otimista, volta ao ritmo de 0–50 ns | 11,34 | 31 min | **1 h 11 min** |
| Média da integração até o último marcador | 25,49 | 1 h 10 min | **1 h 50 min** |
| Conservador, persistência do ritmo exato de 80–85 ns | 108,47 | 4 h 57 min | **5 h 37 min** |

Os cenários não são limites garantidos. Entre 80 e 85 ns, cinco ns consumiram **542,36 s**. Àquele ritmo, o restante sozinho levaria quase cinco horas. A tentativa usou praticamente um núcleo e a memória amostrada não demonstrou esgotamento de RAM. Mais núcleos não garantem ganho no caminho serial observado. Uma CPU com maior desempenho por núcleo pode ajudar, com ganho ainda desconhecido para este circuito e estes estados.

O contraste continua sendo uma pergunta técnica legítima sobre se o defeito já existia em B′. Até **23/11/2026**, sua informação incremental não justifica reservar outra execução longa e imprevisível quando C já tem evidência elétrica direta para delimitar a falha. O caminho existe em princípio, com recuperação parcial por pausas já demonstrada em RC, mas faltam o diagnóstico específico de custo e a comprovação na bancada escolhida. O gate `READY_FOR_TARGETED_RUN` exigiria recuperar vetores válidos na janela inicial, demonstrar fidelidade, separar contagem de passos/rejeições de custo por passo e demonstrar no ambiente escolhido um custo conservador compatível com o orçamento acordado. O horizonte e pergunta discriminante ficam explícitos no preflight. [Telemetria e cenários](../build/phase3/ngspice_performance_20261121/performance.json) · [Cronograma](phase3_plan_to_20261123.md)

**Próxima tarefa única.** Auditar offline, nos waveforms TT/SS já arquivados de C, a ordenação PRECH–WL–SCLK e a janela até D/CLK de captura para as leituras comparáveis. Entregar uma tabela por coluna e ciclo com polaridade BLB−BL na abertura de avaliação, validade de D até a borda e gaps de pré-carga, indicando quais margens ainda exigem sondas locais. O critério é delimitar uma única hipótese de temporização de avaliação que possa ser contrastada posteriormente em C, sem propor um ECO a partir da telemetria de B′.

## E. Preservação e reprodução

O trabalho produziu este relatório, scripts, CSVs, JSONs, figura, recibo de teste, prefixo RC e ZIP. Seis testes de software passaram. Houve uma única invocação SPICE sintética e **zero simulações SPICE da SRAM**. O HEAD permanece `8e1d961d65054b59f9032ed5f9338d9ee4353c33` em `integration/phase3-danilo-ss`. Não houve mudança de circuito, GDS, LEF, PEX ou estímulos arquivados, nem commit, push ou merge.

C permanece como referência, com **FAIL TT** e **PASS SS no escopo ensaiado**. B′ permanece inconclusivo em c16/c17; v1 segue em espera. Monte Carlo experimental preservado, qualificação elétrica geral **`NOT_CHARACTERIZED`**. [Testes](../build/phase3/ngspice_performance_20261121/tests.log) · [Recibo final](../build/phase3/ngspice_performance_20261121/verification.json)
