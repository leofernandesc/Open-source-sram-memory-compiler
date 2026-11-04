# Fase 2 — auditoria de cobertura e campanhas complementares

Referência desta rodada: `4ffbbf5`, branch `integration/phase2-4x8`.
PR #7 continua aberto; PR #8 está em Draft sobre a branch da Fase 1.
O circuito e as evidências anteriores são entradas somente de leitura.

## Método e evidência existente

Foram confrontados o contrato, RTL/scoreboard, scripts de geração de estímulos,
listas reais de ciclos nos receipts e checks dos transientes. Contar apenas o
nome de um teste produziria lacunas falsas: WRITE→READ e READ→WRITE já ocorrem
nos ensaios anteriores. A classificação abaixo é por comportamento, abstração
e observador. Os pares adjacentes, com relação de endereço, estão em
`reports/phase2/extension_20261104/existing_coverage.json`.

Abreviações: B = campanha elétrica original; D = dirigida walking-data;
S = cinco cenários de partida. Todas usam o top de 1.493 MOS extraído, TT,
1,8 V/27 °C, sem wire RC. RTL e GLS usam modelos funcionais de armazenamento.

| Comportamento esperado | Evidência RTL / GLS | Evidência elétrica e observador existente | Estrutural/física | Limitação e prioridade adicional |
|---|---|---|---|---|
| READ→READ, mesma palavra | Scoreboard/padrões/transações pseudoaleatórias | Não encontrado par adjacente READ/READ do mesmo endereço em B/D/S | Driver/sense/captura conectados por LVS | Lacuna P1 de verificação: recuperação/reavaliação pode não ser exigida por leituras espaçadas. C1 |
| READ→READ, palavras diferentes | Todas as transições e endereços | B: 12 pares; D: 3, além de S; DATA e FF na descida | Mapeamento das quatro linhas conferido | Coberto nominalmente; incluir como controle de contraste em C1 |
| WRITE→WRITE, mesmo endereço | Tráfego RTL inclui repetição | Não encontrado par adjacente no mesmo endereço em B/D/S | DIN/complementos/conexões corretos | Lacuna P1 de verificação: inverter novamente após um único baixo. C1 |
| WRITE→WRITE, endereços diferentes | Coberto | B: 6 pares; S: 3 por cenário | BL/BLB por coluna e WL por linha | Coberto; inicializar palavras distintas em C1 |
| Reescrita complementar | 00/FF/AA/55 e walking | D/S exigem complemento, com outras operações entre algumas escritas | 32 bitcells reais | Já coberto; adicional é a repetição adjacente, não apenas outro padrão |
| Alternância de linhas | Todos os pares lógicos | B/D/S acessam 00/01/10/11 | Terminais/coordenadas extraídas e LVS | Coberto nominalmente; verificar também armazenamento não selecionado |
| WRITE→READ imediato | Coberto | D: 16 pares mesmo endereço; S: leituras de escrita inicial/complemento | Sense e FF reais | Não é lacuna; reutilizar em C1/C2 |
| READ→WRITE imediato | Coberto | D: 15 pares, mas de linhas diferentes | ebufn físicos e captura DIN | Falta reforço para mesma linha e handoff curto observado. C1/C2 |
| READ→WRITE→READ, mesma linha | Tráfego RTL | Sequências mistas existem, mas não toda a tripla adjacente da mesma linha | Sem latch/recaptura redundante | P1 de verificação: C1 exige alteração e leitura da mesma linha |
| Preservação de linhas não selecionadas | Scoreboard e readback | S: 312 checks de nós conhecidos por cenário; B: readback após comandos inválidos | 16 gates de acesso por WL | Não exigir estado de palavra ainda não escrita; ampliar após cada operação C1 |
| ADDR/DATA externos mudam após captura | Perturbações explícitas | D: 72 checks de ADDR e 128 de DIN | 12 FF de requisição | Coberto; observar ADDR_Q/DIN_Q em C1 sem redefinir setup/hold |
| Seis comandos inativos/inválidos | 8 códigos/64 transições | B: seis códigos, readback e probes de barramento | Decode dos controles mapeado | Já coberto; não criar outra campanha apenas para repetir códigos |
| Retenção em idle e retorno | RTL e retenção do registro | B/D: dois ciclos; S: idle e nova leitura | Bitcells sempre alimentadas | Somente janelas nominais, não retenção estatística/longa duração |
| Máscara viva e restauração de DATA | RTL/GLS e mutante de máscara | D: 160 checks de leitura mascarada; B: 96 probes de 1 kΩ | Enable ebufn e FF_Q conferidos | Só amostras discretas; ausência de tDIS/tEN e corrente transitória. C2 |
| Partida sem reset | X para conteúdo não escrito | Cinco cenários / 3.383 checks, 0/2/3 capturas com rampas 1/5/10 ns | Sem reset/IC/nodeset | Coberto nas combinações; não reexecutar busca de mínimo nesta rodada |
| PRECH/WE/WL/SCLK e captura | GLS não demonstra atrasos | B/D/S: exclusão, prontidão e envelopes FF; 55 eventos medidos em S | Taps 24/40/60/80 e corpos verificados | Reavaliar mínimos com novos padrões, sem alterar taps ou limites |
| READ na interface antes da nova descida | RTL retém resultado anterior | D: checks do FF; DATA sob máscara e probes | FF_Q→ebufn real | Ampliar observação simultânea DATA/FF_Q/enable com leitura de palavra diferente. C2 |

Os riscos P1 acima classificam **lacunas de verificação**, não defeitos
confirmados no circuito. DRC/LVS e correspondência de grafo não substituem
esses testes temporais e funcionais.

## Campanhas escolhidas antes da execução

### C1 — sequências de acesso

Hipótese: o circuito deve reavaliar corretamente após cada baixo, inclusive
READ→READ e WRITE→WRITE no mesmo endereço. Inicializar as quatro palavras
com AA/55/0F/F0; realizar leituras repetidas, reescritas complementares
adjacentes, READ→WRITE→READ da mesma linha, alternância e READ→IDLE→READ.
O piloto contém somente as duas capturas inativas, as quatro escritas de
inicialização e duas leituras consecutivas da linha 0. O completo amplia a
sequência, preservando os mesmos critérios. Não é uma terceira campanha.

### C2 — propriedade e transientes do barramento

Hipótese: a máscara viva deve desativar/reabilitar o ebufn sem perder FF_Q,
e o handoff executado deve liberar o driver antes do mestre assumir DATA.
Instrumentar somente a bancada: fontes de 0 V em série com os caminhos
externos do mestre e do probe permitem medir corrente. A netlist DUT continua
idêntica. Carregar temporariamente a saída habilitada com 1 kΩ contra o dado
registrado é **calibração de observabilidade**, não uma transação legal com
dois mestres fortes. Os intervalos são separados dos checks de protocolo.

Após captura de leitura: probe habilitado em +11,5 ns, máscara em +12,5 ns,
restauração em +14 ns e remoção do probe em +15,5 ns, relativos à subida.
O dado normal é amostrado antes do probe, em +11 ns. Handoffs READ→WRITE
utilizam guardas declaradas de 0,3/0,6 ns entre início da retirada de leitura
viva e acionamento do mestre; WRITE→READ libera o mestre 0,1 ns antes da
subida. Não são mínimos garantidos. Uma falha não autoriza aumentar a guarda
e apagar o resultado; requer classificação e eventual ensaio de diagnóstico.

## Critérios fixados

- Circuito: mesmos 1.493 MOS/modelos/junções e hash do binding selecionado;
  sem IC/nodeset nem dispositivo de armazenamento comportamental.
- Sequenciamento: critérios publicados de 20%/80%, uma WL por vez, seleção
  correta e recuperação tardia no baixo; mesmo envelope interno de captura.
  A análise independente conferirá também os quatro N e 16 BL/BLB entre
  0,8 e 0,2 ns antes de cada acesso válido, para não aceitar somente um dado
  antigo numa leitura repetida sem demonstrar a recuperação entre acessos.
- Scoreboard: somente palavras previamente escritas têm expectativa; exigir
  valor interno e leitura correspondente, preservando todas as outras conhecidas.
- Barramento normal: DATA/FF_Q válidos nos instantes fora de calibração;
  retenção do resultado anterior durante a fase alta de nova leitura.
- Calibração: corrente habilitada observável >50 µA sob oposição de 1 kΩ;
  depois da máscara, corrente ≤50 µA e tensão dentro de 50 mV do probe.
  Esse piso instrumental corresponde a 50 mV/1 kΩ usado no screening anterior;
  não é especificação de leakage, drive ou turnaround.
- Mestre forte: rejeitar sobreposição entre HOST_EN>20% e TE_B<80% dos
  ebufn; conferir corrente após a carga inicial, separando transientes capacitivos.
- Medidas: cruzamentos interpolados, referências de 50% para clocks/controles,
  20%/80% para fase/condução; instante nominal PWL e cruzamento são distintos.
- Execução incompleta, timeout ou recurso insuficiente não são falha elétrica
  nem PASS. Preservar logs e classificação específica.

## Resultado

| Execução | Ciclos / duração | Checks totais | Bits lidos, já incluídos | Resultado |
|---|---|---:|---:|---|
| Piloto C1 | 8 / 170 ns | 309 | 16 | PASS |
| C1 completo | 20 / 410 ns | 1.150 | 72 | PASS |
| C2 barramento | 15 / 310 ns | 1.281 | 48 | PASS |

C1 contém dois pares READ→READ da mesma linha, um WRITE→WRITE da mesma
linha e triplas READ→WRITE→READ. As quatro palavras são escritas antes de
exigir conteúdo conhecido. Após cada operação, os nós das palavras conhecidas
são conferidos, além do readback público. ADDR e dados externos mudam durante
a fase alta de C1; as capturas permanecem corretas.

C2 contém seis leituras com observação de corrente antes, durante e depois
da máscara viva. As duas trocas READ→WRITE usam guardas de estímulo de
0,3 e 0,6 ns. Não houve sobreposição detectada por HOST_EN>20% e TE_B<80%
nas amostras examinadas. A corrente do mestre nos intervalos estacionários
atendeu ao piso de 50 µA. Isso não exclui fenômenos entre amostras ou abaixo
desse piso. Os checks contínuos usam todas as amostras salvas, com passo
máximo de 10 ps; checks de valor armazenado e readback usam pontos declarados.

A análise temporal adicional aprovou **820 screens**, sobre os mesmos
transientes de C1/C2: pré-carga dos quatro nós dinâmicos e dos 16 nós BL/BLB
antes de cada acesso e estabilidade de RAW/FF_D nos 2 ns posteriores à
captura local. São observadores adicionais, não 820 novas transações.
O piloto é subconjunto de C1 e não deve ser somado como cobertura exclusiva.
Também não somamos bits lidos novamente aos totais.

As evidências estão em
[`c1_sequences/`](../reports/phase2/extension_20261104/c1_sequences/),
[`c2_bus/`](../reports/phase2/extension_20261104/c2_bus/),
[`raw_reanalysis/results.json`](../reports/phase2/extension_20261104/raw_reanalysis/results.json)
e [`timing_selected/`](../reports/phase2/extension_20261104/timing_selected/).
Cada execução preserva estímulo, binding, modelos auxiliares, fontes Python
congeladas por execução, log ngspice nativo, checks e hash do raw completo.

## Revisão estrutural e qualidade dos verificadores

A segunda passagem independente confirmou 32 bitcells, os quatro caminhos
WL, oito colunas, alimentação/corpos, oito inversores de complemento da
escrita e FF_Q→ebufn→DATA. Foram conferidos os MOS reais dos NANDs que
habilitam cada ebufn, além da auditoria anterior de terminais e coordenadas.

A primeira versão do auditor novo falhou por pressupor enable compartilhado.
O roteamento replica oito NANDs com entradas Booleanas equivalentes. A
arquitetura não exige uma única rede física. Preservamos o
[`FAIL`](../reports/phase2/extension_20261104/structure/results.json),
a fonte daquela versão e o
[`PASS corrigido`](../reports/phase2/extension_20261104/structure_corrected/results.json).
Foi corrigido o observador; nenhum fio ou transistor da SRAM foi alterado.

Oito adulterações em cópias descartáveis foram rejeitadas: contador, hash do
raw, estímulo, artefato obrigatório ausente, circuito alterado, log incompleto,
checks alterados e snapshot da fonte. O original permaneceu íntegro.
[`Resultado`](../reports/phase2/extension_20261104/tampering/results.json).
Os 63 testes Python relevantes passaram: 48 já existentes e 15 novos testes
dos observadores. Fixtures sintéticas desses testes são explicitamente
identificadas; não representam simulações da SRAM.

## Riscos remanescentes

As lacunas específicas de sequências adjacentes e de observabilidade do
barramento foram reduzidas nas condições ensaiadas. Nenhum defeito funcional
do DUT foi demonstrado nesta rodada. Retenção prolongada, mínimos temporais,
conteúdo aleatório de partida, offsets/mismatch, interconnect RC e PVT
permanecem fora da conclusão. Os pontos de revisão humana estão no
[checklist da equipe](phase2_team_review_checklist.md).
