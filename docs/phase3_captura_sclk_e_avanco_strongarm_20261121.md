# Fase 3 · Captura de SCLK e avanço do StrongARM

**A referência temporal da macro C foi recuperada e validada.** A nova simulação TT atingiu 250 ns, recuperou as seis sondas internas e repetiu o C250 histórico. A etapa B foi auditada com o novo waveform. A carga dinâmica omitida continuou sem um modelo justificável para o controle reduzido. O contraste StrongARM com acionamento físico permanece `NOT_RUN`. Foi executada **uma simulação SPICE** nesta campanha. [Recibo](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/simulation.json) · [Validação](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/validation.json)

| Etapa | Objetivo | Veredito | Evidência ou condição |
|---|---|---|---|
| A | Captura de SCLK em C | `REFERENCE_CAPTURE_VALIDATED` | 250 ns completos e 15.322 amostras. Os 144 vetores comuns têm os mesmos tempos e valores salvos em C250. |
| B | Controle reduzido do acionador nativo | `BOUNDARY_NOT_DEFENSIBLE` | Entradas e PRECH recuperadas. Auditoria de cargas e acoplamentos concluída, sem transiente do recorte. |
| C | StrongARM com SCLK físico em TT | `NOT_RUN` | Depende do controle nativo. |
| D | Triagens SS e FF | `NOT_RUN` | Nenhuma evidência nova por corner. |
| E | Preparação física | `NOT_RUN` | Depende de funcionamento em TT com acionador físico. Nenhum layout novo. |

## A · Captura e validação

O bench foi copiado de `build/phase3/data3_tt_20261120/`. Os hashes do bench histórico, binding, fabric, mapa de sondas e manifesto de modelos conferiram com o preflight original. O PEX selado tem SHA-256 `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`. O deck acrescentou as seis sondas somente à linha `.save` e a `wrdata`. Continuam intactos o circuito, as fontes, a sequência das seis escritas, o ponto de operação inicial e as opções numéricas. O manifesto dos modelos teve **319 hashes conferidos** no contêiner. [Preflight](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/preflight.json) · [Diff](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/instrumentation.diff)

O ngspice 44.2 executou TT, 1,8 V nominal, 27 °C, Gear/KLU e passo máximo de 25 ps, com `tran 10p 250n 0 25p`. O processo saiu com código 0 e exportou normalmente após o transiente. A execução levou **3.082,91 s (51 min 23 s)**, ante 1.509,70 s no histórico, dentro do teto de 90 min. O pico de RSS reportado foi 1.658.848 KiB. A telemetria do progresso registra avanço até o encerramento, sem tentativa adicional. O waveform novo tem SHA-256 `267dcc4d1b634ba08c0d58cc403864f98658866d7f1f63219fb7bbcc57af6f71`. [Progresso](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/progress.jsonl) · [Waveform](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/waveform.dat)

### Resultado funcional de C

| Ciclo | Linha | Esperado | Palavra lida | D de DATA3 na captura (V) | Q após 0,5 ns (V) | Margem contínua de D para o bit esperado |
|---:|---:|---|---|---:|---:|---|
| 15 | 2 | `0x0F` | `0x0F` | 1,803 | 1,799 | ≥10,058 ns dentro da janela observada |
| 16 | 3 | `0xF0` | `0xF8` | 1,803 | 1,799 | Sem margem válida. D alto incorreto por toda a janela de 10,058 ns. |
| 17 | 3 | `0xF0` | `0xF8` | 1,803 | 1,800 | Sem margem válida. D alto incorreto por toda a janela de 10,058 ns. |

As seis escritas de c2, c3, c4, c5, c8 e c10 reproduziram endereço capturado, dados do host, WE e wordline correspondente. A sonda direta de retenção é a bitcell da linha 3, bit 3, que manteve Q baixo e QB alto de 120,55 a 245,55 ns. Em c16/c17, o maior Q foi 0,147 V e o menor QB foi 1,772 V nas janelas medidas. O predecessor c14 retornou `0xAA`. Após c17, SCLK e PRECH entraram na banda baixa, com BL/BLB acima de 1,727/1,748 V no trecho de 245 a 249,95 ns. A observação funcional não qualifica cada bitcell individualmente e a margem de D da tabela não é uma especificação de setup. [Leituras, escritas e recuperação](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/validation.json)

### Referência temporal recuperada

Os tempos abaixo estão no eixo C250, em ns. Os números são interpolações, com os intervalos nativos preservados no CSV. Os cruzamentos do tronco na subida têm brackets de 25 ps. Os gates de READ_Q ficam altos ao longo de c15–c17, sem cruzamento de 50% nessas janelas. A ativação de ambos já aparece em c14, perto de 171,496 ns. [CSV de c14–c17](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/six_probe_edges.csv) · [Histórico das seis sondas](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/new_probe_full_history_edges.csv) · [Gráfico TT](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/sclk_capture_comparison.png)

| Ciclo | PRECH ↑50 | Tap 80 ↑20/50/80 | NAND ↓50 | SCLK tronco ↑20/50/80 | CLK local ↑50 | SCLK tronco ↓80/50/20 | PRECH ↓50 |
|---:|---:|---|---:|---|---:|---|---:|
| 15 | 192,146 | 193,858 / 193,887 / 193,926 | 193,969 | 194,152 / 194,405 / 194,803 | 200,058 | 204,071 / 204,161 / 204,270 | 204,378 |
| 16 | 212,145 | 213,859 / 213,887 / 213,926 | 213,969 | 214,152 / 214,406 / 214,805 | 220,058 | 224,070 / 224,160 / 224,269 | 224,377 |
| 17 | 232,146 | 233,858 / 233,886 / 233,925 | 233,968 | 234,152 / 234,406 / 234,805 | 240,058 | 244,068 / 244,158 / 244,267 | 244,375 |

A diferença de 50% entre tap 80 e tronco foi de **518–520 ps**. O tronco subiu de 20 a 80% em 651–653 ps e desceu de 80 a 20% em cerca de 199 ps. O tronco, o gate do tail, o proxy de SCLK e o CLK local coincidiram também com as sondas do contraste R87 em c15, antes da injeção de corrente histórica. Essa verificação independente cobre c15. [Comparação com o prefixo R87](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/r87_preinjection_comparison.json)

A partir das duas tensões recuperadas de C131 (7,54814 fF), calculou-se `Q = C × (V_SCLK − V_PRECH)`. A maior corrente média em um intervalo salvo foi de **19,2–19,3 µA** na janela de avaliação e **45,6–45,8 µA** na recuperação. A variação absoluta acumulada de carga na janela de avaliação foi cerca de **27,43 fC**. A corrente vem da diferença de carga entre amostras, sem estimar picos subamostra, corrente total de saída do AND ou corrente no tail do StrongARM. [Corrente capacitiva e diferenças entre sondas](../build/phase3/strongarm_physical_sclk_campaign_20261121/A_capture/proxy_and_c131.json)

## B · O que ainda impede o controle nativo reduzido

A bancada candidata teria os **12 MOS originais do AND2_4**, com os gates A e B excitados independentemente pela captura, `rc7285` livre e o tronco SCLK livre, preservando o RC distribuído e C131 até a placa `rc8467`. Essa topologia agora tem entradas observadas. A auditoria avançou até a carga do acionador e verificou dois recortes possíveis e a utilidade do contraste R87. [Gate B](../build/phase3/strongarm_physical_sclk_campaign_20261121/B_native_boundary/gate.json)

| Opção examinada | Resultado |
|---|---|
| 12 MOS, rede SCLK original, entradas e C131 com replay em nós exatos | A rede tem 45 nós resistivos e 24 gates, 21 nas outras sete colunas. Fora de trilhos, nós internos e placas observadas diretamente, restam **46,90 fF** com um proxy resistivo distinto e **1,61 fF** sem sonda no grupo. A carga MOS depende da trajetória dos seus terminais. |
| Manter os oito senses nativos ativos, incluindo os grupos resistivos de BL/BLB, SA/SAB e tail | A triagem topológica alcança 68 MOS no núcleo e 136 MOS adicionais tocando esses nós. Com os trilhos fora da contagem, ainda aparecem 226 grupos externos com pelo menos uma placa sem observação exata. A contagem indica a extensão do corte. A criticidade elétrica varia por placa. |
| Inferir a carga pelo contraste histórico de R87 | Há uma única injeção entre dois nós, com alterações registradas nos controles compartilhados e nos demais caminhos de leitura. O ensaio não separa as admitâncias dinâmicas dos vários ramos. |

O acoplamento de **4,28661 fF de C178** liga o tronco ao SA do sense 3 antes da sonda de mux. A captura mediu diferenças entre pontos de uma mesma rede de até **47,65 mV** no caminho de SA e **58,48 mV** no caminho BL. Esses valores não demonstram violação digital. Eles mostram que a proximidade resistiva não basta para igualar a tensão, e a corrente de um capacitor também depende de seu slew. Uma fonte de tensão em um proxy pode ainda suprimir a resposta da placa à troca de carga. Os 48,51 fF restantes representam uma escala ilustrativa de **87,31 fC** para uma excursão de 1,8 V. Essa conta não estima carga líquida nem estabelece tolerância de fidelidade. [Inventário dos capacitores](../build/phase3/strongarm_physical_sclk_campaign_20261121/B_native_boundary/native_sclk_capacitors.csv) · [Fechamento estrutural](../build/phase3/strongarm_physical_sclk_campaign_20261121/B_native_boundary/closure_screen.json)

A recuperação do tap 80, READ_Q, NAND, PRECH e tronco elimina a falta de referência de fase. Falta justificar uma carga dinâmica para os sete ramos e os acoplamentos omitidos, preservando o efeito de substituir somente o ramo alvo. Por isso, não foi produzido um deck B que dependesse de aterramento de placas, da imposição de saída ou de uma carga agregada escolhida para reproduzir a borda. O controle nativo e as etapas dependentes ficaram sem simulação.

## Decisão e próximo gate

O StrongARM continua com a evidência anterior de **1, 0, 0 em TT sob SCLK ideal**, com margem mínima de D de 5,267 ns, recuperação da coluna ativa e sobreposição tail/reset de 388–400 ps naquele ensaio. As correntes e a recuperação com acionador físico continuam sem medição. SS e FF seguem sem triagem neste escopo. Ainda não há evidência desta campanha para iniciar o layout isolado sob os gates acordados. A referência da macro C permanece `FAIL` TT, `PASS` SS no escopo integrado e `NOT_CHARACTERIZED`. [Coluna ativa com SCLK ideal](phase3_strongarm_coluna_ativa_tt_20261121.md)

O menor próximo gate é **qualificar a carga dinâmica da rede SCLK no plano de R87**, preservando C131 e os elementos que carregam o tronco pelo caminho de SA/SAB e bitlines. Use a captura validada como referência independente de entrada e de saída. Para os ramos omitidos, uma equivalência deve sustentar tanto o comportamento nominal de C quanto uma mudança de carga no ramo alvo, com observabilidade de corrente de porta ou uma demonstração equivalente. Só então compare a saída livre do AND nativo em c15–c17 e autorize a substituição experimental pelo StrongARM. Essa etapa aproveita a captura já feita e evita repetir a macro para obter os mesmos nós.

## Reprodução e preservação

Na raiz do workspace, o pacote conserva o deck executado, os scripts, logs, waveforms A e C250, critérios, manifesto e testes. O contêiner histórico `sram-xschem` monta o workspace em `/work`. Para reprodução, use uma cópia isolada dos artefatos desta campanha. O runner recusa sobrescrever os recibos e logs da tentativa. A medição offline usa o checkout com as ferramentas existentes e NumPy. [Testes](../build/phase3/strongarm_physical_sclk_campaign_20261121/test_campaign.log) · [Verificação do checkpoint](../build/phase3/strongarm_physical_sclk_campaign_20261121/preservation.log)

```bash
area=build/phase3/strongarm_physical_sclk_campaign_20261121
PYTHONDONTWRITEBYTECODE=1 python3 "$area/test_campaign.py" -v
# As análises e o gráfico podem ser regenerados na cópia do pacote.
bash "$area/postprocess_capture.sh"
# Reprodução SPICE em destino isolado, sem arquivos de saída de outra execução.
docker exec -e PYTHONDONTWRITEBYTECODE=1 -w "/work/$area" sram-xschem \
  python3 run_once.py A_capture_repro --stop-ns 250 --timeout 5400
```

Para o último comando, criar `A_capture_repro` por cópia do manifesto `preflight.json` e dos arquivos de entrada listados no campo `outputs`. Essa reprodução fica fora da execução entregue. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. PEX, GDS, LEF, checkpoints e alterações locais preservados. Sem commit, push ou merge.
