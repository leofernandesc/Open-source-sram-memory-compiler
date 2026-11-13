# Contrato de caracterização — Fase 3, versão 1

Responsável pela infraestrutura: Leonardo. Consumidores: Danilo (RC/timing/potência),
André (leitura/sense/pré-carga), Ícaro (SNM Monte Carlo N≥200) e futuro gerador Liberty.
Baseline: `origin/release/phase2-acceptance-20261111`, commit
`89901e7e258b6955f6752163b918a296079466fa`. O ref deve resolver localmente;
não é feito fetch, merge ou atualização de seletores pelo runner.

## Escopo e auditoria de reutilização

Foram lidos `release/phase2_current.json`, `specs/technical_specification.md`,
`specs/sram_4x8_digital.md` e `docs/phase2_closure_20261111.md`.
O checkout inicial estava limpo na branch `feature/phase3-infra-leonardo`, no
mesmo commit da baseline. Não houve troca de branch nem restauração de arquivos.

| Ferramenta existente | Decisão nesta etapa |
|---|---|
| `tools/sram-eda`, `scripts/run_phase2.sh` | Reutilizar o ambiente EDA; não instalar um segundo ngspice |
| `phase2_resources.preflight` | Reutilizar verificação de disco/memória; acrescentar limites do processo |
| `phase2_evidence.digest` e guards de selagem | Reutilizar SHA-256 streaming; não reescrever recibos históricos |
| `phase2_core.selected_leaves`, `prepare_abutment_fixture.py` | Preservar seleção e montagem existentes; não regerar folhas |
| `phase2_extension.py`, `run_abutment_campaign.py` | Preservar estímulos e observadores nominais; adapter prepara cópia rastreável |
| `phase2_access_checks.py`, `analyze_phase2_extension_timing.py` | Manter verificações funcionais/análise histórica; não converter seus números em nova caracterização |
| `run_phase2_extracted_access.model_closure` | Examina `.include`; o snapshot novo precisa também capturar `.lib arquivo seção` e isolar dependências |
| Locks/atomic writes de `run_digital_regression.py` | Política nova mais restrita: reservar diretório com mkdir exclusivo e publicar manifesto por rename |

A implementação usa apenas a biblioteca padrão Python. Nenhuma mudança em células,
80 inversores, taps 24/40/60/80, layout, especificações oficiais ou releases.

## Configuração externa

`characterization/phase3/smoke.json` é um exemplo executável com pins de SHA-256
verificados no ambiente existente. O validador é `tools/phase3/contract.py`.
Paths relativos são relativos à raiz do checkout, incluindo configurações fora dela.
TT/SS/FF são `tt`, `ss`, `ff`; o modelo deve declarar a seção escolhida.
Não se procuram modelos alternativos quando um path/pin/corner falha.

Campos obrigatórios: `schema_version=1`, `configuration` (4x8/8x8/16x8/32x8),
`scope` (`sram` ou `infrastructure_smoke`), `baseline`, `pdk=SKY130A`, `corner`,
`vdd_v`, `temp_c`, `period_ns`, `duty_cycle`, `slew_ps`, `load_ff`, `extraction`,
`deck`, `netlist`, `model`, `stimuli`, `measurements`, `timeout_s`, `memory_mb`.
Cada arquivo principal é `{ "path": "...", "sha256": "64 hex caracteres" }`.
Campos desconhecidos, valores não finitos, booleanos numéricos e unidades
incompatíveis são rejeitados. As configurações maiores são aceitas como dados;
não significam que circuitos físicos dessas dimensões já estejam disponíveis.

Condições iniciais: 1,8 V, 27 °C provisórios, período 20 ns, duty 0,5, slew 50 ps;
cargas exploratórias 5/10/20 fF por bit. São pontos de ensaio, não limites garantidos.
O adapter nominal usa 10 fF adicionados explicitamente no novo deck: o deck histórico
não declarava essas oito cargas externas. O adapter preserva os PWL históricos e é
fixo nas demais condições nominais; não é um gerador paramétrico de campanhas SRAM.

O template exige os placeholders MODEL, NETLIST e CORNER para usar as entradas pinadas.
Aceita `{{MODEL}}`, `{{NETLIST}}`, `{{CORNER}}`, `{{VDD}}`, `{{TEMP}}`,
`{{PERIOD}}`, `{{HIGH}}`, `{{SLEW}}`, `{{LOAD}}`. Tempos e capacitância substituídos
estão em SI. O autor do deck é responsável por aplicar os parâmetros a todos os
estímulos e cargas. Os decks são código confiável da equipe, não uma sandbox SPICE.
Não colocar comandos de shell ou escrita em paths externos nos decks.

Cada medição declara `measure` (nome único no ngspice), `metric`, `operation`, `bit`
(0–7 ou null para escalar/palavra), `unit`, `transition` (rise/fall/stable/na) e
`definition`. `min`/`max` opcionais são critérios de ensaio nas unidades declaradas.
O parser aceita atribuições numéricas únicas `nome = valor` realmente emitidas
pelo ngspice. Valores do simulador são SI; a unidade declarada serve para converter
os limites, nunca para multiplicar novamente os resultados. Nomes repetidos ou
valores não finitos são erro. Não se infere medida a partir do sucesso do processo.

## Protocolo e definições elétricas

Entradas e dados de escrita capturados na subida de CLK; leitura registrada na
descida; DATA[7:0] bidirecional; pré-carga na fase baixa e acesso na fase alta.
A palavra anterior pode permanecer em DATA durante a fase alta da leitura seguinte.
Não usar essa palavra antiga como disponibilidade da palavra solicitada.

Propagação usa cruzamentos de 50% VDD, interpolados entre amostras, com direção e
ocorrência explícitas. Verificação funcional usa baixo ≤20% e alto ≥80% VDD.
A definição no deck deve incluir ciclo, palavra esperada, janela de observação e
critério de estabilidade até a captura; o runner não deduz validade elétrica.

| Métrica | Referência e significado |
|---|---|
| tACCESS | Subida pública CLK50 até nova palavra DATA válida; incluir registro da descida |
| tCLK_TO_DATA | Descida pública CLK50 até transição válida DATA50 |
| tREAD_INTERNAL | Subida CLK50 até DOUT_RAW válido, antes do registro |
| tWL_TO_SCLK | WL50 até ativação SCLK50, declarando polaridade |
| tSETUP / tHOLD | Limite de perturbação de ADDR/controles/DATA em torno da subida; requer busca e check funcional |
| tDATA_ENABLE / tDATA_DISABLE | Transição do controle até condução/liberação efetiva; declarar carga, sonda e critério de impedância |
| tOUT_SETUP / tOUT_HOLD | Margens de DOUT_RAW relativamente ao clock local de captura da saída |
| P_STATIC / P_IDLE | Média da potência fornecida numa janela e estado explicitados, respectivamente sem atividade / idle com clock definido |
| E_READ / E_WRITE | Integral de −V(VDD)·I(VDD_SRC) na janela da operação; sinal conforme fonte SPICE |
| P_READ_AVG / P_WRITE_AVG | Energia dividida pela duração da mesma janela |

Para energia, declarar se inclui clock, pré-carga e baseline estática; não subtrair
energia implicitamente. Documentar startup descartado, número de ciclos e sinais
salvos. Não misturar potência de host/sonda com potência da macro.

Separar rise/fall e bits estáveis. Bits sem comutação não têm atraso de cruzamento:
registrar NOT_CHARACTERIZED/ausente e um check funcional de estabilidade separado;
não preencher zero. Para palavra completa, agregar apenas após validar todos os bits,
com método registrado. Dados de SNM exigirão tabela de amostras/seed/método separada;
estatística de 200 amostras não pode ser fabricada a partir de TT/SS/FF.

## CSV, JSON e estados

`metrics.csv` sempre tem cabeçalho:

```text
run_id,configuration,corner,vdd_v,temp_c,operation,metric,bit,value,unit,status,transition,measure,reason
```

Valores ausentes são célula vazia no CSV e `null` no JSON. Unidades exportadas:
segundos (`s`), watts (`W`), joules (`J`); volts (`V`) só no smoke. Não usar NaN,
infinito, sentinela zero ou estimativa como medição.

`manifest.json` versão 1 contém configuração completa, run_id, status, branch/commit
e dirty, baseline/ref/commit, hashes das entradas e dependências, snapshots de código,
versões Python/Git/ngspice, hash do executável, comando/cwd, recursos, duração,
return code quando existente, evidências/hash e a mesma lista `measurements` do CSV.
`extraction` distingue schematic, devices/junctions e distributed RC, conforme
proveniência fornecida pelo responsável pela extração; não é inferida pelo runner.

| Estado | Significado |
|---|---|
| PASS | Execução completa, medições solicitadas presentes e dentro dos critérios fornecidos; não qualifica a SRAM |
| FAIL | Medição real fora de um limite configurado |
| ERROR | Configuração/integridade inválida, erro SPICE, timeout ou execução incompleta |
| BLOCKED | Dependência ausente, baseline incompatível ou corner não disponível |
| NOT_CHARACTERIZED | Dry-run ou medidas solicitadas indisponíveis/não configuradas |

`electrical_simulation_performed=false` no dry-run; nenhuma medição recebe valor.
`sram_characterized=false` nesta infraestrutura, inclusive quando o smoke passa.
Medições parciais não são promovidas após erro/integridade inválida; o log bruto
permanece para diagnóstico. Tempo esgotado mata o grupo do processo e preserva os
artefatos. Diretório existente é recusado, mesmo se a execução anterior falhou.
Falhas de configuração posteriores à reserva também recebem manifesto e CSV.

A dependência textual completa de includes é copiada conservadoramente, incluindo
corners não selecionados, e reescrita para arquivos locais. Paths dinâmicos de
include são recusados. Bibliotecas externas permanecem preservadas localmente;
não versionar cópias do PDK. Os originais são verificados novamente após a execução.
Os recursos Linux são limitados a um CPU, uma thread, memória virtual configurada,
CPU time e 512 MiB por arquivo, além do timeout de parede e preflight existente.

## Consumo futuro por Liberty

Aceitar somente métricas reais PASS de execuções completas, scope=sram, mesma
identidade de netlist/extração, corner/VDD/temperatura e metodologia. Agrupar por
slew/carga, pin/bit, sentido e arco. Nunca usar SMOKE_VOLTAGE, dry-run, bit estável
como atraso zero ou células vazias para preencher lookup tables. `definition`
registra referências/condições necessárias para mapear arcos e constraints.

O contrato prepara esse consumo, mas ainda não implementa gerador Liberty,
interpolação, sweeps de setup/hold, extração automática de waveform ou verificação
sintática de .lib. Antes de Liberty, fechar quais arcos representam a interface
com captura em bordas opostas, medir tabelas reais e revisar a cobertura funcional.
