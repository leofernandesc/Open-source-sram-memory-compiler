# Fase 3 — Diagnóstico de DATA3 em TT e piloto de SNM nominal

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
O escopo é a geometria espaçada 4×8 com o PEX padrão e a folha 6T
esquemática. [Especificação técnica](../specs/technical_specification.md) · [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Contrato de caracterização](phase3_characterization_contract.md)

## A. Diagnóstico TT

### O que os waveforms anteriores já mostravam

Nos ciclos 16 e 17 do TT integrado, o endereço e a seleção da linha
3 estavam corretos. A palavra era `0xF8` em vez de `0xF0`.
DATA3 ficou alta após a descida. O sense e D já estavam altos
na captura. Em SS, com o mesmo PEX e estímulos, o sense
resolveu o bit corretamente. Os estados históricos de TT
e de propriedade em SS foram preservados.
[Integração TT × SS](phase3_tt_snm_20261120.md) · [Propriedade em SS](phase3_fechamento_barramento_ss_20261120.md)

Na escrita original c5 em TT, o host apresentou `0xF0` e
DATA3 estava em 0 V no CLK↑50 em 110,025 ns. A saída de
captura da escrita, `_70_.Q`, entrou no nível baixo antes de
WE20 em 112,523 ns. A linha 3 foi selecionada. Entre 115 e
119,95 ns, o waveform confirma BL3 ≤10 mV, BLB3 ≥1,78 V e
WL medida ≥1,44 V. A mesma polaridade foi vista em SS, com
maior atraso no início da escrita. Os arquivos anteriores
observavam DIN e as BLs nos terminais do sense, sem sondas
dos nós de armazenamento. Os dois readbacks errados não
distinguem escrita de avaliação por si sós.
[Reanálise offline](../build/phase3/data3_tt_archives_final_20261120/diagnosis.json)

Para ler zero em DATA3, espera-se `ΔBL = BLB−BL > 0` nos
terminais de entrada do sense. Antes da leitura, as duas
bitlines estão pré-carregadas, com diferencial próximo de zero.
No waveform original, em c16/c17, o marcador SCLK20 do
sampler BL ocorreu cerca de 43/36 ps antes de WL80 em TT e
114/126 ps depois em SS. Em TT, ΔBL era −3,9/−2,0 mV 50 ps
antes de SCLK20 e +15,8/+20,8 mV em SCLK20. Em SS, ΔBL era
+77,4/+88,0 mV e +122,3/+134,0 mV nos mesmos eventos.
SCLK20 e WL80 são referências de forma de onda. Esses valores
não estabelecem limiar de regeneração ou diferencial mínimo.

### Identidade e preflight do ensaio direcionado

| Artefato | SHA-256 |
|---|---|
| GDS | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Waveform integrado TT | `2125aae7f92e94e81ca686c0519be5695ba72f370c0f7b0bcfefc8875a0cd1fd` |
| Waveform integrado SS | `692e2218366c4d1797e53c9ee9924895e2e23eda54e3d22765f75b5ed24de44f` |

TT determinístico, 1,8 V, 27 °C, 10 fF/bit, período de 20 ns,
fases de 10 ns, rampas de 50 ps, passo máximo de 25 ps,
ngspice 44.2 com KLU em um CPU. O transiente foi reduzido
de 370 para 250 ns, preservando os ciclos de origem
`0,1,2,3,4,5,8,10,14,15,16,17`. Até o início da mudança em
127 ns, os estímulos do prefixo foram mantidos. Isso inclui
partida, duas capturas desabilitadas e as escritas iniciais,
inclusive c5.

Foram preservadas todas as seis escritas e sua ordem. Nas
duas escritas movidas, preservaram-se payload, endereço,
clock, largura da fase e a janela do host. Os handoffs agora
ocorrem sem os reads removidos e suas sondas fracas. Depois
das escritas, a memória programada esperada é `55 AA 0F F0`.
Foram mantidos os quatro reads finais, inclusive os dois
predecessores de padrões `0xAA` e `0x0F` e o read repetido da
linha 3. A partir dos controles estabilizados de cada leitura,
as fontes foram comparadas à sequência original, incluindo
sondas e máscaras até o desligamento da sonda. O primeiro
read sucede uma escrita no ensaio reduzido. As operações
omitidas poderiam afetar estado analógico residual. O vínculo
com a falha original exige a reprodução no novo waveform.

O circuito inclui exatamente o binding do TT integrado,
reverificado com o PEX selado. As mudanças no deck foram
os estímulos reduzidos, o horizonte e as sondas
`.save`/`wrdata`. O mapeamento encontrou os acessos
`X1592/X663` na interseção de WL da linha 3 com BL/BLB da
coluna 3 e verificou os quatro dispositivos cruzados. No
sense, as entradas são os terminais dos samplers `X235/X521`
e o tail é `X351`. Q/QB da célula são sondas distintas do
Q do registrador de saída. [Preflight](../build/phase3/data3_tt_20261120/preflight.json)

### Resultado — falha reproduzida, classe C

O ngspice concluiu os 250 ns em **25 min 10 s**, com retorno 0 e
**15.322 amostras**. O waveform tem SHA-256
`7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646`.
Os reads predecessores c14 e c15 retornaram `0xAA` e `0x0F`.
Os reads c16 e c17 repetiram `0xF8` com o mesmo bit 3 errado.
A reanálise dos arquivos e a nova simulação concordam no
estágio divergente. [Recibo](../build/phase3/data3_tt_20261120/simulation.json) · [Diagnóstico em JSON](../build/phase3/data3_tt_diagnosis_final_20261120/diagnosis.json)

**A escrita da célula foi confirmada.** O host apresentou
`0xF0`, DIN do bit 3 ficou baixo antes de WE20 e as bitlines
assumiram a polaridade de escrita. O nó Q da célula estava
em aproximadamente 1,800 V antes da escrita. Q cruzou
0,9 V em descida em 114,259 ns e QB cruzou 0,9 V em subida
em 114,382 ns, após WL80 no acesso BL em 114,214 ns. Com a
WL já baixa em 125 ns, Q era **0,00017 V** e QB, **1,80240 V**.
De 120,55 ns até a última observação de leitura, em 241,50 ns,
Q ficou entre −0,007 e +0,147 V e QB entre 1,772 e 1,832 V.
Esse intervalo cobre as reescritas de outras linhas, as
pré-cargas e as duas avaliações do bit. A bitcell armazenou
e reteve o zero durante o ensaio que reproduziu a falha.

Antes de c16 e c17, as duas bitlines estavam próximas de
1,8 V e a palavra anterior tinha bit 3 alto. Na leitura, a
tensão de BL começa a cair e BLB−BL fica positiva
continuamente antes de o gate do tail chegar a 20% de
VDD. As duas WLes medidas nos gates de acesso apresentam
a mesma fase. O diferencial do próprio latch se torna
positivo no meio da subida de SCLK, depois **inverte**.
A inversão ocorre enquanto o diferencial nos terminais
do sense mantém a polaridade correta. Isso localiza a
primeira divergência funcional na **avaliação/regeneração**.

| Evento | c16 reduzido | c17 reduzido |
|---|---:|---:|
| CLK↑50 (ns) | 210,025 | 230,025 |
| WL80 no acesso de BL, em ns | 214,216 | 234,209 |
| Entrada BLB−BL passa a positiva até a captura (ns) | 214,121 | 234,113 |
| SCLK20 do tail (ns) | 214,153 | 234,153 |
| BLB−BL em SCLK20 do tail (mV) | +15,1 | +19,9 |
| BLB−BL em SCLK50 do tail (mV) | +360,5 | +373,2 |
| SA_OUTB−SA_OUT em SCLK50 do tail, terminais dos samplers (mV) | +77,8 | +81,8 |
| Inversão do diferencial do latch (ns) | 214,579 | 234,590 |
| BLB−BL na inversão do latch (mV) | +679,1 | +712,7 |
| VGS do tail na inversão (V) | 1,164 | 1,177 |
| Primeiro estado lógico errado sustentado no sense (ns) | 214,791 | 234,815 |
| Borda local de captura (ns) | 220,058 | 240,058 |
| Sense / D na captura (V) | 1,798 / 1,803 | 1,798 / 1,803 |
| Q do FF / DATA3 na observação (V) | 1,800 / 1,800 | 1,800 / 1,800 |

TT original mostra a mesma sequência, com os horários dos reads
120 ns depois. Em SS, a comparabilidade usa a geometria,
estímulos originais e sondas arquivadas. A separação BLB−BL já
é maior no início da rampa e o diferencial do latch segue para
a polaridade correta. No gráfico, TT inclui pontos nos
terminais dos samplers. SS usa os pontos do latch já arquivados,
representantes da mesma rede elétrica distribuída.
[Eventos TT e SS](../build/phase3/data3_tt_diagnosis_final_20261120/events.csv) · [Amostras nativas](../build/phase3/data3_tt_diagnosis_final_20261120/read_transition_samples.csv) · [Gráfico da regeneração](../build/phase3/data3_tt_diagnosis_final_20261120/data3_regeneracao.png)

**Classificação e confiança.**

| Hipótese | Conclusão |
|---|---|
| A — Escrita/retenção | Excluída para o bit 3 no replay da falha. A célula mudou de estado na escrita e manteve a polaridade correta. |
| B — Desenvolvimento do diferencial | O diferencial de entrada tem polaridade correta e cresce no instante observado. A margem disponível na fase efetiva de amostragem pode contribuir. O valor tardio não mede o diferencial transferido pelos PMOS enquanto ainda conduzem. |
| C — Avaliação/regeneração | Confirmada, confiança alta. A saída do latch troca para a polaridade oposta com o dado armazenado correto e BLB−BL positiva. |
| D — Captura | Excluída como primeiro estágio. Sense e D já expressam o bit errado na borda de captura. |
| E — Mecanismo físico exato | Ainda pendente. A associação com WL/SCLK e o menor diferencial inicial em TT é forte. Faltou uma perturbação controlada para separar temporização causal de assimetria parasitária, injeção de carga e margem do latch. |

A conectividade verificada e o resultado correto em SS são
evidências contra uma inversão fixa de polaridade. A condição
inicial pré-carregada e os reads predecessores foram observados.
Os tempos de cruzamento são referências elétricas. A decisão
de regeneração depende do estado do latch, das bitlines e da
condução dos samplers e tail durante a rampa. O alvo histórico
de 200 mV do ensaio G7 pertence a outra condição de excitação.
Aplicá-lo ao valor tardio de BLB−BL neste waveform não provaria
uma margem suficiente. [Estudo histórico do sense PEX](sense_pex_small_signal_investigation.md)

Comandos para reproduzir. A atuação no circuito desta rodada
se limitou à observação passiva.

```bash
run=build/phase3/data3_tt_20261120
timeout 120s tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/run_phase3_data3_tt.py prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/run_phase3_data3_tt.py simulate --output "$run" --timeout 2100
timeout 90s env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/analyze_phase3_data3_tt.py --run "$run" \
  --output build/phase3/data3_tt_diagnosis_replay
```

## B. Primeiro lote Monte Carlo

**Metodologia verificada no primeiro lote. Domínio provisório.**
Os lotes usaram ngspice 44.2 e a biblioteca contínua SKY130A do
Volare `0fe599b2afb6708d281543108caf8310912f54af`. A seção
`tt_mm` usa `parameters_fet_tt.spice`, `MC_MM_SWITCH=1` e
`MC_PR_SWITCH=0`. Os hashes da cadeia de modelo e do netlist
canônico foram verificados. Cada seed executou um processo
separado com `.options seed=... seedinfo`. 1,8 V e 27 °C
representam um ponto nominal experimental.
[Auditoria estatística anterior](phase3_tt_snm_20261120.md#b-monte-carlo-de-snm--provisional)

Ambos os modos usam a folha canônica com seis transistores,
com os tamanhos e parâmetros de junção preservados. O deck
abre a realimentação para extrair duas VTCs. Em Hold, WL=0 V
e BL=BLB=1,8 V. Os dois acessos desligados incluem a fuga
modelada. Em Read, WL=BL=BLB=1,8 V durante a varredura DC.
A entrada foi varrida de 0 a 1,8 V em passos de 1 mV. O
método mede o menor dos maiores quadrados inscritos nos
dois lóbulos, em volts.
[Folha 6T](../release/phase1/cells/bitcell_6t/bitcell_6t.spice)

| Modo | Seed | Lóbulo 1 (mV) | Lóbulo 2 (mV) | SNM (mV) | Vtrip E/D (mV) | Estado |
|---|---:|---:|---:|---:|---|---|
| Hold | 20001 | 686,730 | 678,180 | 678,180 | 755,22 / 747,74 | Válida |
| Hold | 20002 | 691,830 | 684,860 | 684,860 | 765,02 / 757,56 | Válida |
| Hold | 20003 | 697,760 | 702,529 | 697,760 | 770,90 / 776,44 | Válida |
| Hold | 20004 | 696,556 | 705,616 | 696,556 | 769,18 / 777,01 | Válida |
| Hold | 20001, repetição | 686,730 | 678,180 | 678,180 | 755,22 / 747,74 | Válida, fora da contagem |
| Read | 30001 | 418,571 | 393,803 | 393,803 | 852,01 / 835,31 | Válida |
| Read | 30002 | 407,990 | 413,882 | 407,990 | 830,88 / 834,59 | Válida |
| Read | 30003 | 432,457 | 411,391 | 411,391 | 828,65 / 805,97 | Válida |
| Read | 30004 | 387,603 | 428,633 | 387,603 | 830,51 / 847,17 | Válida |
| Read | 30001, repetição | 418,571 | 393,803 | 393,803 | 852,01 / 835,31 | Válida, fora da contagem |

As dez varreduras convergiram, com **1.801 pontos finitos por
VTC**, seed confirmada no log, dois lóbulos e três interseções
em cada execução. Houve **quatro seeds distintas válidas,
uma repetição válida e zero inválidas por modo**. Os hashes de
VTC das quatro seeds são distintos. As repetições são
idênticas byte a byte às primeiras curvas. As diferenças de
Vtrip entre metades e entre seeds confirmam a aplicação do
mismatch. Quatro realizações não permitem provar independência
estatística ou estimar caudas com precisão.

A medição foi recalculada de cada VTC selada. Trocar os
lados preservou o SNM dentro da resolução de exportação.
Subamostrar o mesmo traço em passos de 2 mV mudou o SNM
em até 0,013 mV em Hold e 0,006 mV em Read. Em testes de
software, uma interrupção DC com retorno 0 e um timeout
foram registrados como ERROR/TIMEOUT, com deck/log preservados
e sem valor de SNM. As amostras reais não apresentaram esses
erros. [Hold auditado](../build/phase3/snm_nominal_hold_batch01_20261120_audit/audit.json) · [Read auditado](../build/phase3/snm_nominal_read_batch01_20261120_audit/audit.json)

Cada lote de 220 seeds predeclaradas tem **4/200 checkpoints
válidos** no domínio experimental. Se o domínio for aprovado,
faltam pelo menos 196 realizações válidas por modo. A repetição
tem manifesto no próprio diretório e fica fora da amostra.
Retomar o mesmo diretório mantém as seeds medidas, verifica
os hashes e registra novas tentativas separadamente. O preflight
de retomada selecionou 20005 e 30005, sem executar essas seeds. As séries
de `sf_mm` continuam separadas e não contam nesse total. A
meta de Read SNM ≥0,4 V no ponto determinístico nominal não é
um critério de aprovação estatística deste lote. Os dados não
permitem inferir rendimento industrial.
[Contrato da bitcell](../specs/sram_6t_cell.md)

Comandos do piloto, com `mode=hold`/`read` e
`seed_base=20001`/`30001`. Use diretórios novos para uma
reprodução independente dos checkpoints já arquivados.

```bash
run="build/phase3/snm_nominal_${mode}_batch01_20261120"
tools/sram-eda python3 tools/run_phase3_snm.py init --profile nominal-proposed \
  --mode "$mode" --seed-base "$seed_base" --count 220 --output "$run"
tools/sram-eda python3 tools/run_phase3_snm.py run --output "$run" --limit 4 --timeout 45
tools/sram-eda python3 tools/validate_phase3_snm_nominal_pilot.py repeat "$run" --timeout 45
tools/sram-eda python3 tools/validate_phase3_snm_nominal_pilot.py audit "$run" --output "${run}_audit"
tools/sram-eda python3 tools/run_phase3_snm.py export --output "$run" --target "${run}_export"
```

## C. Próxima decisão

**Próxima execução recomendada.** Fazer um único contraste
diagnóstico TT na bancada reduzida, usando o waveform atual
como referência e deslocando somente a fase de SCLK do sense.
Escolher o novo instante a partir do diferencial **disponível
no início da amostragem**, comparado ao funcionamento observado
em SS, e exigir D válido antes da captura local no fim da fase
alta. Manter a polaridade esperada, o armazenamento, os
estímulos, as cargas e o restante dos controles. A condição
decisiva é observar se disponibilizar mais diferencial antes
da regeneração impede a inversão do latch e recupera
`0xF0` nos dois reads, com a célula ainda correta. Isso testa a
necessidade de retimar SCLK sem escolher ainda o atraso de um
ECO nem tratar o tempo observado como especificação.

Se o contraste confirmar a hipótese, retimar o enable do sense
tem o menor escopo de mudança. O novo atraso consumiria parte da
janela até a captura de descida, podendo aumentar o mínimo da
fase alta e reduzir Fmax. A desativação do sense e a próxima
pré-carga precisam manter a fase baixa livre. TT, SS e FF exigem
uma faixa comum. Reaproveitar a lógica de temporização, quando
viável, tem custo de área e complexidade menor que redesenhar
o latch. A energia depende do tempo de condução e das
comutações, com impacto ainda desconhecido. Se o atraso não
recuperar a polaridade, medir a transferência diferencial e
avaliar o balanceamento de carga/offset ou separar amostragem e
regeneração. Essa separação oferece maior controle e acrescenta
estado, roteamento e consumo. Antecipar WL afetaria decoder,
pré-carga e a escrita e tem justificativa menor neste momento.

- **Monte Carlo completo.** Pode prosseguir em lotes depois de
  confirmar o domínio experimental para a caracterização
  esquemática. Já há 4/200 por modo quando esse domínio for
  aceito. A qualificação de SNM para as configurações físicas
  permanece uma atividade distinta.
- **FF integrado.** Executar quando houver uma candidata
  escolhida após o diagnóstico causal, com GDS/LEF/PEX e
  fixture comuns aos corners usados para aprovar a revisão.
- **Setup/hold, potência e Liberty.** Retomar após estabilizar
  o caminho de leitura e confirmar a funcionalidade da revisão
  física. A qualificação geral segue `NOT_CHARACTERIZED`.

**Escopo concluído.** Passaram os 32 testes de software
pertinentes, incluindo seis novos. Foi feita uma simulação
pós-layout direcionada em TT e cinco execuções DC por modo.
SS e TT integrados foram reusados offline. FF, 200 seeds por
modo, ECO, extração, potência, setup/hold e Liberty estão
pendentes. Geometria e Git foram preservados.

O ZIP local contém scripts, testes, waveform direcionado,
decks, recibos, VTCs, logs, gráfico e tabelas. O replay offline
completo também usa estes três pacotes anteriores, sobre o
checkout de referência.

| Entrada arquivada | SHA-256 |
|---|---|
| `phase3_validacao_integrada_ss_20261119.zip` | `2710b17f3413c3eda672fa4b269f85de5452b80acc376df0eb60a0782ae122de` |
| `phase3_fechamento_barramento_ss_20261120.zip` | `c2e07bc773f564e81a2f47627afb14d056a925bbfc64aacfbffa016178f2d1cd` |
| `phase3_tt_snm_20261120.zip` | `d0a103570eb2d0528e9720e1d494bd3f356afec3aaf5045838ebe3bf16477a52` |
