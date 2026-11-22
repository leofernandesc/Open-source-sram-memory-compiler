# Fase 3 — Reconstrução offline do recorte carregado de SCLK em TT

**Veredito NOT_READY.** O recorte menor preserva os oito caminhos de sense e substitui a terminação de VCUT205 por um equivalente capacitivo. Restam **252 grupos de fronteira sem modelo justificado**. Destes, **35** acoplam diretamente aos nós de regeneração, incluindo **sete no sense 3**. A inclusão ausente no deck bloqueia sua execução. **Zero execuções SPICE.** [Manifesto](../build/phase3/sclk_recut_audited_r2_20261120/manifest.json) · [Prioridades de fechamento](../build/phase3/sclk_recut_audited_r2_20261120/boundary_resolution_priority.csv)

## A. Auditoria da fronteira

No PEX padrão, **rc7913** é o metal **m1_16160_31260#**. Seu grupo resistivo contém só o próprio nó, sem caminho para os trilhos e sem pino de MOS direto. Há 27 cartões C, dos quais nove têm valor zero. Os 18 positivos somam **52,52646 fF**. Os vizinhos resistivos dos capacitores incluem WL, qualificação de linha, controle e alimentação. O inventário identifica os terminais D/G/S/B dos MOS nas redes vizinhas. [Entorno elétrico completo](../build/phase3/sclk_recut_audited_r2_20261120/vcut205_electrical_audit.json)

| Parcela do PEX de rc7913 | Tratamento no corte que falhou |
|---|---|
| 16 capacitores, 34,54116 fF | Valores retidos com a segunda placa forçada por VCUT205 rc7913 VSS 0 |
| C6381 para VDD, 4,4424 fF | Excluído |
| C6439 para VSS, 13,5429 fF | Excluído |
| Nove capacitores de valor zero | Excluídos, sem contribuição no modelo C |

A regra anterior aterrava placas externas sem sonda para manter os capacitores e fornecer referência DC. Para esse metal, o aterramento altera a matriz de capacitância e elimina os acoplamentos mútuos. Num metal puramente capacitivo com carga livre constante, a derivada de sua tensão é a média ponderada das derivadas de tensão dos terminais. Eliminando o nó, cada par recebe **Cij = Ci × Cj / ΣC**, incluindo os termos de VDD e VSS. No vizinho de C1292, por exemplo, o termo diagonal nativo é **5,65746 fF**, diante de **6,44932 fF** na versão aterrada. São coeficientes do modelo linear, não medições de carga durante a regeneração. [Cartões CKRON e seus valores](../build/phase3/sclk_recut_audited_r2_20261120/frontiers.json)

| 206 fontes VCUT históricas | Classe | Evidência |
|---|---|---|
| CLK público | Preservada, 1 | Mesmo pino de estímulo externo, com a translação temporal documentada |
| Entradas capturadas (12) e placas reproduzidas por sonda (8) | Aproximada, 20 | Tensão arquivada, fonte ideal sem impedância incremental do circuito omitido |
| Placa flutuante VCUT205 | Suspeita, 1 | Condutor C-only com fonte de 0 V e dois acoplamentos aos trilhos excluídos |
| Demais placas fixadas a VSS | Suspeita, 184 | No PEX, há 130 nós C+MOS, 46 C+R e oito C+R+MOS |

Cada placa foi classificada com cartões mantidos e cortados, grupo resistivo e vínculo com a sonda, quando existente. O erro histórico *Timestep too small* em 1,664 ps nomeou o ramo de VCUT205. A transformação topológica é comprovada. A causa numérica exclusiva e a dimensão do efeito no waveform permanecem abertas. O recorte novo usa uma só fonte no nó medido por grupo resistivo com evidência, mantendo o caminho R pertinente. As demais fronteiras ficam explicitamente pendentes, sem aterramentos artificiais. [Inventário das 206 fronteiras](../build/phase3/sclk_recut_audited_r2_20261120/old_frontiers.csv) · [Falha arquivada](phase3_partida_recorte_carregado_tt_20261120.md)

## B. Estratégia e matriz de fidelidade

| Estratégia | Fidelidade e risco |
|---|---|
| A. Expandir o recorte isolado | O sense 3 já reproduziu c16/c17 com fronteiras remotas BL/BLB. Nos outros sete sentidos, as sondas de BL/BLB estão nos samplers. Aplicar o replay nesses pontos esconderia a resposta a jusante da impedância das bitlines. Também seria necessário reintroduzir o estágio físico de SCLK e a interação com pré-carga. |
| B. Reduzir o recorte carregado | Preserva as células 6T, drivers de escrita, WL, pré-carga e a geração física de SCLK. Permite reduzir o caminho de saída de sete colunas, com D físico e seu primeiro inversor de carga. Os acoplamentos dos circuitos excluídos e o feedback Q precisam de tratamento explícito. |

Foi adotada **B**, com o FF completo do bit 3 e as 32 bitcells preservados. A palavra de cada leitura será avaliada nos oito sentidos em D nas referências de captura. A avaliação de Q físico fica restrita ao bit 3. Para as outras sete colunas, Q arquivado é entrada de feedback. Foram mantidas as portas NOR que produzem **_34_.Y** e **_44_.Y**. Suas redes eram as duas maiores fronteiras desconhecidas no primeiro rascunho, com 6,29 e 5,05 fF incidentes. As portas usam os estímulos públicos do deck histórico. [Proveniência dos cones e dos replays](../build/phase3/sclk_recut_audited_r2_20261120/manifest.json)

| Elemento | Representação no recorte | Evidência e limitação |
|---|---|---|
| SCLK compartilhado | Driver original, 45 nós R, oito ramos e 24 gates | Cartões do grupo e R87 mantidos byte a byte. A fonte atua antes da geração. |
| Sense 3 | Samplers, latch, tail, D e FF de captura nativos | Gates rc8584/rc8586/rc8585, NTAIL rc7187 e D rc6372 preservados. A decisão ainda precisa ser reproduzida. |
| Outros sete senses | Latches e cargas de entrada de D nativas, Q reproduzido | Primeiro inversor do FF retido. A carga dinâmica interna e os novos Q ficam fora do escopo. |
| Pré-carga e WL | Controle original, pré-carga com 45 nós, 24 dispositivos locais e caminhos WL | Sem fontes ideais nessas saídas ou nos gates locais. |
| BL/BLB | Impedância distribuída, 32 células 6T e caminho de escrita nativo | Sem fonte ideal na bitline, sampler ou armazenamento. Duas escritas físicas de condicionamento continuam no deck. |
| Alimentação | Trilhos externos comuns e malha extraída até os dispositivos | Caminhos até MOS e capacitores verificados. Correntes ativas omitidas limitam a estimativa de droop da macro. |
| Fronteiras capacitivas | Capacitores físicos no corte, equivalente de rc7913 e caminhos R de fontes conhecidas | 25 grupos externos com replay e 252 sem resolução. O replay ainda fixa a tensão no ponto observado. |
| Estado inicial | Rampa TT de 1 ns, duas escritas e c15 completo antes de c16/c17 | O estado de NTAIL depende da evolução do circuito. |

| Complexidade | Recorte anterior | Recorte novo |
|---|---:|---:|
| MOS | 1.013 | **840** |
| Resistores | 14.810 | **14.534** |
| Capacitores | 8.138 | **8.165** |
| Fontes ideais incluindo VDD/VSS | 229 | **50** |
| Total de cartões MOS/R/C | 23.961 | **23.539** |

Os resistores incluem 146 equivalentes de série, com proveniência de 632 cartões. Eles eliminam nós sem cargas, capacitâncias ou sondas, preservando os caminhos paralelos. Também foram retirados 49 ramos de ponta sem carga. Dos 8.165 C, 153 são pares equivalentes de rc7913. O aumento de C decorre da eliminação do metal flutuante. A redução de MOS é de 17,1%. Custo e convergência futuros permanecem por medir. [Equivalentes R](../build/phase3/sclk_recut_audited_r2_20261120/series_resistors.json) · [Conectividade e contagem independentes](../build/phase3/sclk_recut_audited_r2_20261120/verification.json)

## C. Critérios de aceitação do controle

O controle mantém a distribuição original de SCLK. A janela de **147 ns** inclui a partida histórica de 0–46 ns, escritas nas subidas a 50% de 50,025/70,025 ns e leituras de 88 a 147 ns. Nessa parte, tempo histórico = tempo local + 100 ns. O controle deve comprovar Q/QB e retenção nas linhas 2 e 3 antes das leituras. O erro de c16/c17 precisa surgir da regeneração com armazenamento correto e manter-se em D até a captura. [Critérios e instantes em JSON](../build/phase3/sclk_recut_audited_r2_20261120/acceptance.json)

| Ciclo | Esperado | Reprodução exigida | SCLK20 do tail 3 na referência | BLB−BL nesse instante | NTAIL prévio |
|---|---|---|---:|---:|---:|
| 15 | 0x0F | 0x0F | 194,152661 ns | −30,476 mV | 1,148258 V |
| 16 | 0xF0 | 0xF8 | 214,152765 ns | +15,085 mV | 1,148301 V |
| 17 | 0xF0 | 0xF8 | 234,152509 ns | +19,946 mV | 1,147661 V |

Confirmar a estabilidade nos oito D, complementaridade dos sinais de regeneração e Q físico no bit 3. Comparar bordas 20/50/80% de SCLK, pré-carga, WL e captura disponível usando os **25 ps** do envelope diagnóstico anterior. Comparar BLB−BL com **7,542 mV** em torno da ativação. Fora dessa janela, usar o maior entre 7,542 mV e 5% do diferencial. O envelope de modo comum é **15,085 mV**. NTAIL em c16/c17 deve atender aos **30,169 mV** nas janelas contínuas de condicionamento, condução e recuperação. Os critérios usam o PEX padrão e a resolução dos dados arquivados. O máximo de 25 ps do integrador não é uma estimativa universal de erro. A divergência de até cerca de 44 ps entre configurações RC pertence a outro experimento e não amplia o envelope. [Gate histórico](phase3_precondicionamento_sense3_tt_20261120.md) · [Auditoria do RC](phase3_auditoria_falhas_20261119.md)

Diferenças que preservem polaridade, condução, margens e envelopes são registradas como analógicas. Uma divergência capaz de alterar a regeneração impede comparação mesmo que a palavra coincida. Evidência insuficiente resulta em **INCONCLUSIVE**. Palavra ou decisão comprovadamente diferente resulta em **NOT_REPRODUCED**. **VALIDATED** exige as duas escritas, as três palavras e fidelidade elétrica.

Quando as fronteiras forem fechadas, cabe um único controle TT com monitor por fases, 5 min para solução inicial após despachar o transiente e 20 min no total. O contraste v1 dependerá de controle **VALIDATED**. [Monitor reaproveitável](../tools/phase3_sclk_loaded_ramp.py)

## D. Bloqueio e próxima tarefa

As **252 fronteiras sem evidência** aparecem com seus nomes e cartões. As **35** que acoplam diretamente aos latches somam **0,42751 fF** de capacitâncias incidentes nesses nós. Os **sete grupos** diretamente acoplados ao sense 3 somam **0,08325 fF**. São medidas topológicas. O efeito físico depende de fase, amplitude e impedância. A falta desses modelos impede interpretar a simulação de um deck que deixasse tais placas flutuantes ou as fixasse sem fundamento.

**Próxima tarefa única:** fechar as fronteiras do mapa, começando pelos sete grupos acoplados ao sense 3. Os dois primeiros são **rc7115** (a_60103_12015.n1, 0,04476 fF diretos) e **rc7125** (a_60269_12015.n0, 0,02030 fF diretos). Seus drivers MOS nativos estão identificados. Usar o cone físico necessário, replay no terminal historicamente observado com caminho R ou equivalência documentada. O critério de conclusão é um deck contínuo sem fronteira pendente, com o gate de fidelidade preservado. [Mapa de fronteiras e drivers](../build/phase3/sclk_recut_audited_r2_20261120/boundary_resolution_priority.csv)

| Estado | Resultado |
|---|---|
| Macro original TT | FAIL |
| Contraste ideal de SCLK isolado | CORROBORATED |
| Driver v1 isolado | VIABLE_FOR_PHYSICAL_STUDY |
| Driver v1 carregado | NOT_RUN |
| Novo controle elétrico | NOT_RUN |
| Qualificação geral | NOT_CHARACTERIZED |

## E. Reprodução e integridade

**17/17 testes de software passaram**, oito novos e nove regressões de recorte/partida. Duas gerações offline foram idênticas byte a byte. O verificador confirmou cartões nativos sem alteração, matriz de C da placa, equivalência das séries R, caminhos de alimentação e bloqueio do deck incompleto. O PEX padrão e a árvore de 319 arquivos de modelo SKY130A TT foram conferidos com as referências arquivadas. [Testes](../build/phase3/sclk_recut_audited_r2_20261120/tests.log) · [Determinismo](../build/phase3/sclk_recut_audited_r2_20261120/determinism.json)

```bash
original=build/phase3/sclk_recut_audited_r2_20261120
repro=build/phase3/sclk_recut_repro
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/phase3_sclk_recut.py --output "$repro"
cp "$original/verify_recut.py" "$repro/verify_recut.py"
PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1 python3 "$repro/verify_recut.py"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sclk_recut.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sclk_loaded*.py' -v
```

O circuito e o deck de controle pendente estão no diretório de evidências. O trabalho acrescentou este relatório, **tools/phase3_sclk_recut.py** e **tests/test_phase3_sclk_recut.py** ao espaço versionável. A branch **integration/phase3-danilo-ss** continua no HEAD **8e1d961d65054b59f9032ed5f9338d9ee4353c33**. Os artefatos anteriores foram preservados. A entrega ficou local.

| Evidência | SHA-256 |
|---|---|
| PEX padrão | 12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a |
| Novo circuito | aef668a5de56df80c56e6e76efc8babe2000b93fdec925f174a3f05515433732 |
| Manifesto | fa2b6eadccbb378d8a930358cb9f5878a97cf8da9b4ad5d686a7978123859c19 |
