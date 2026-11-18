# Fase 3 — Danilo: extração RC, timing e potência

**Data do diagnóstico:** 15/11/2026 (America/Manaus)  
**Branch:** `feature/phase3-rc-timing-danilo`  
**Baseline congelada:** `origin/release/phase2-acceptance-20261111`, commit `89901e7e258b6955f6752163b918a296079466fa`  
**GDS de entrada:** `reports/phase2/direct_abutment_20261111/gds_v1/sram_4x8.gds`  
**SHA-256 do GDS:** `83e72aee8d45a9826751cdefd46dd062acc2a17ec0acfd33c07f218d20d8e64e`

## Escopo e evidências existentes

A atribuição da equipe para a Fase 3 coloca **Danilo** como responsável pela extração RC e pela caracterização temporal e de potência nos corners TT, SS e FF. As entregas são independentes das frentes de margem de leitura (André), Monte Carlo de SNM (Ícaro) e infraestrutura/Liberty (Leonardo). O Marco 3 é em **23/11/2026**. Este é o alinhamento mais recente para esta frente; o planejamento anterior em `docs/phase3_plan_to_20261123.md` registra uma distribuição preliminar distinta.

Todos os experimentos desta frente estão em `build/phase3/`, ignorado pelo Git, usando diretórios distintos por execução. Os arquivos da Fase 2 permanecem como entradas somente de leitura.

| Ensaio | Evidência local | Resultado e limite |
| --- | --- | --- |
| Magic, resistência distribuída em todas as redes | `build/phase3/rc_runs/20261115T190212Z-af649475/` e cópia requalificada `build/phase3/rc_requalified/20261116T014953Z-bdca57e3/` | 1.493 MOS, 300.400 R, 101.942 C; **somente estrutura RC**. A conectividade DC do VSS está aberta para os terminais MOS. |
| Magic, modo integrado `extract do resistance` | `build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a/` | **PASS_RC_NETLIST_STRUCTURE:** 1.493 MOS, 322.018 R, 101.005 C (48.111 capacitâncias nulas); VDD alcança 1.302 e VSS alcança 1.275 terminais MOS, sem curto entre os trilhos. SHA-256 do SPICE: `600f1ae686029e522d5d36299befc036e031e79c26e8c0725c0082752aaa8b27`. Ainda exige ensaio funcional. |
| Magic, resistência em sinais selecionados | `build/phase3/rc_runs/20261115T193552Z-e02e6d0d/` | 1.493 MOS, 743 R, 7.650 C; extração **parcial**, sem todos os resistores das alimentações. VDD alcança 1.302 e VSS alcança 1.275 terminais MOS, sem curto resistivo entre as fontes. |
| ngspice TT sobre RC completo com as malhas de alimentação distribuídas | `build/phase3/electrical_runs/20261116T025325Z-tt-bb698eaa/` | **FAIL (timeout de 900 s):** apenas 32,6098 ns do benchmark de 370 ns foram processados. Não houve resultados funcionais nem medidas de timing/potência. |
| ngspice TT com malhas de alimentação ideais e RC de sinais | `build/phase3/electrical_runs/20261116T031342Z-tt-f32929c7/` | **FAIL_FUNCTIONAL: 39 de 72 bits de leitura falharam**. Modelo diagnóstico com 1.493 MOS, 202 R e 5.073 C; sem IR drop e sem qualificação de timing/potência. |
| ngspice TT, 1,8 V, 27 °C, 10 fF por saída, sobre RC parcial | `build/phase3/electrical_runs/20261115T193658Z-tt-2028ca49/` | **FAIL_FUNCTIONAL: 38 de 72 bits de leitura falharam**. Os valores de timing/potência desse ensaio não são qualificáveis. |
| Controle sem RC distribuída, netlist transistorizada da Fase 2 | `build/phase3/diagnostics/20261116T014638Z-faa53b43/` | Estímulos e leituras de referência apresentam as palavras esperadas nos instantes originais de amostragem. Não validam a extração RC. |

## Bloqueador de conectividade

No `.ext` anterior à extração resistiva, o Magic registra equivalência entre `FILLER_131_1129.VNB` e `VSS`. O `.res.ext` completo marca o primeiro nó com `killnode`; no SPICE resultante, os terminais de vários MOS passam a `FILLER_21_0.VNB`, enquanto a extensa malha `VSS.n*` não possui caminho resistivo até os transistores. A auditoria de conectividade DC identifica **0 terminais MOS alcançáveis por VSS**, embora VDD alcance 1.302 terminais. Isso impede tratar o RC completo como um circuito eletricamente validado. A variante de RC parcial mantém ambos os trilhos conectados, mas falha na leitura funcional: os problemas são distintos. A evidência disponível não estabelece defeito físico no GDS; o comportamento ainda exige diagnóstico da extração Magic.

O teste do modo documentado do Magic 8.3.613 com `extract do resistance` antes de `extract all` **restabeleceu os caminhos DC** de ambas as fontes na extração RC completa. Foram verificados dispositivo, rede resistiva, capacitâncias, hash, e ausência de curto VDD–VSS. O diagnóstico em `build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a/` contém TCL, log, `.ext`, `.res.ext`, SPICE e manifesto com hashes. O gerador `tools/phase3_rc_extraction.py` passou a usar este fluxo para o perfil `all` e a rejeitar malhas de alimentação desconectadas ou em curto. Essas verificações não demonstram comportamento funcional, setup/hold ou potência.

O ensaio TT elétrico com esta extração completa excedeu o limite de 900 s e só avançou até 32,6098 ns. No SPICE, **321.816 de 322.018 resistores (99,94%)** pertencem às malhas de VDD/VSS. Isso explica o custo excessivo da resolução transiente, mas não permite inferir o comportamento funcional da SRAM. Para isolar a participação das malhas de alimentação, `phase3_rc_characterization.py` aceita o modo diagnóstico `--supply-model ideal`, que contrai as redes resistivas de VDD/VSS, conserva as resistências de sinais e agrega as capacitâncias restantes por par de nós. O SPICE diagnóstico tem 1.493 MOS, 202 resistores e 5.073 capacitores. **Esse modelo simplificado não representa IR drop nem substitui resultados sobre RC completo.**

O ensaio TT com alimentação idealizada foi concluído e **reprovou 39/72 bits** nos instantes de amostragem originais. No ciclo 6, a leitura de `0xAA` em 141 ns apresentou todas as saídas próximas de 0,2 V; no ciclo 7, a leitura de `0x55` em 161 ns apresentou saídas próximas de 1,8 V. Após o início da injeção fraca do host, aparecem outras palavras, portanto leituras posteriores não podem ser reinterpretadas como aprovação no instante exigido. Um controle com netlist da Fase 2 e a mesma carga externa de 10 fF apresentou `0xAA` em 141 ns e `0x55` em 161 ns. Os estímulos dos dois decks coincidem, salvo nomes de capacitores externos e o término mais cedo (170 ns) do controle.

Ensaios adicionais de isolamento, todos apenas diagnósticos e com alimentação idealizada, mantiveram as 202 resistências de sinal e a carga externa de 10 fF. Sem capacitâncias extraídas, as palavras em 141 ns (`0xAA`) e 161 ns (`0x55`) coincidem com a referência. Com apenas 1.413 pares de capacitores sinal–trilho (2,635 pF), a leitura em 141 ns falha: os bits altos ficam entre 0,477 V e 0,732 V. Com apenas 3.659 pares entre sinais (1,181 pF), as palavras amostradas são `0x22` em 141 ns e `0x14` em 161 ns, ambas incorretas. Nos dois ensaios com capacitores isolados, `rc701` ficaria puramente capacitivo; foi adicionado `R_DIAG_FLOAT_RC701=1e15 Ω` somente para estabilizar numericamente o ponto de operação. Esse componente não pertence ao PEX. A comparação indica que capacitâncias parasitas são dominantes na falha observada, sem qualificar o circuito nem apontar por si só qual parasita do PEX está errado.

Uma auditoria exploratória, usando a ordem das 1.493 instâncias MOS como correspondência e contraindo as **202 resistências de sinais** e as malhas de alimentação, encontrou **730 redes exatamente correspondentes às 730 redes do netlist transistorizado de referência da Fase 2**: nenhuma rede original dividida e nenhuma união indevida entre duas redes originais. Os parâmetros e a ordem das instâncias MOS também coincidiram. Isso afasta diferenças topológicas no limite de curto ideal como explicação imediata, mas não substitui LVS, nem valida valores resistivos/capacitivos, tempos de subida ou margem de leitura. As capacitâncias efetivas, somadas por pares após a simplificação, totalizam 14,739 pF; cerca de 10,923 pF estão diretamente entre VDD e VSS, com fontes ideais no ensaio diagnóstico.

Para uma nova extração reproduzível, a partir da raiz do checkout e com o contêiner EDA operacional:

```bash
./tools/sram-eda python3 tools/phase3_rc_extraction.py --profile all
```

Para ensaiar TT sobre uma extração cujo manifesto tenha passado na auditoria estrutural:

```bash
./tools/sram-eda python3 tools/phase3_rc_characterization.py \
  --extract-run build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a \
  --corner tt --load-ff 10
```

Para diagnosticar se as malhas distribuídas de alimentação são responsáveis pela falha ou lentidão, usando uma aproximação com VDD/VSS ideais:

```bash
./tools/sram-eda python3 tools/phase3_rc_characterization.py \
  --extract-run build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a \
  --corner tt --load-ff 10 --supply-model ideal --timeout 900
```

## Critérios para liberar TT, SS e FF

1. Reproduzir a RC a partir do GDS fixado, registrando script, logs, hashes e contagens de dispositivos/parasitas.
2. Demonstrar caminho DC do VDD **e do VSS** até terminais MOS e ausência de curto resistivo entre as fontes.
3. Executar primeiro TT no benchmark funcional existente, com os mesmos instantes de amostragem e cargas; exigir **72/72 bits corretos**.
4. Só após TT funcionalmente aprovado, executar SS e FF em série (`workers=1`) e calcular medidas definidas com unidades e referências de transição.
5. Entregar tabelas de tempo e energia/potência com proveniência, e marcar explicitamente `NOT_CHARACTERIZED` onde não houver estímulos ou medidas suficientes (incluindo setup/hold e potência estática, na instrumentação atual).

**Situação:** extração RC completa com conectividade DC de alimentação foi obtida; caracterização funcional TT/SS/FF **ainda não foi aprovada**. Não publicar resultados quantitativos de timing ou potência derivados do ensaio TT anterior funcionalmente reprovado.

## Auditoria de continuidade — 16/11/2026

Revalidei a branch `feature/phase3-rc-timing-danilo` no HEAD `b6a4d119581097900cd76d99f016944f900c6381`; o checkout estava limpo antes desta atualização. A extração continua ligada ao GDS fixado pelo hash registrado acima. No contêiner EDA `sram-xschem` (Magic 8.3.613, ngspice 44.2, Sky130A da versão Volare `0fe599b2afb6708d281543108caf8310912f54af`), o `.ext` declara `tech sky130A`, `style ngspice()` e `scale 1000 1 500000`; o `sky130A.magicrc` carrega o techfile do mesmo PDK e desliga a reescala do ext2spice. Os valores extraídos, portanto, estão ligados à regra/versão identificada, mas isso ainda não é uma calibração independente do RC contra medição ou extração de referência.

A auditoria SPICE confirmou 1.493 instâncias MOS, 322.018 resistores e 101.005 capacitores. Os 101.005 capacitores somam 14,738793 pF; 93.771 pares estão entre nós das malhas VDD/VSS e somam 10,922844 pF. Os outros pares somam 3,815949 pF, incluindo 1,110065 pF entre sinais e 2,492607 pF entre sinal e trilho. Estes totais descrevem os cartões produzidos pelo Magic; não demonstram erro de escala. A auditoria topológica anterior segue sem substituir LVS.

A falha permanece reproduzível como diagnóstico: a aproximação de trilhos ideais reprova 39/72 bits e o PEX integral não completa o transiente de 370 ns dentro de 900 s. A separação dos capacitores em ensaios isolados aponta dependência forte de C parasita, mas ambos os ensaios requerem o resistor artificial de 1e15 ohm no nó flutuante `rc701` e excluem a impedância distribuída de alimentação. Eles não permitem escolher ou ajustar capacitâncias para obter aprovação. O fluxo Magic atual tampouco provê, sozinho, uma referência independente para validar os valores capacitivos.

### Decisão de encerramento

**Frente Danilo — NÃO CONCLUÍDA.** A entrega estrutural de extração RC está pronta e rastreável; a qualificação elétrica ainda não passou. Faltam: (1) validar a distribuição de parasitas em referência independente ou com ensaio geométrico calibrado; (2) obter TT funcional 72/72 no deck integral ou em redução de rede demonstravelmente equivalente nos terminais relevantes; (3) somente após TT aprovado, medir timing e potência em TT/SS/FF com proveniência. Setup/hold e potência estática seguem `NOT_CHARACTERIZED` pela instrumentação atual. Não gerei dados substitutos, não alterei janelas de amostragem e não promovi os diagnósticos simplificados a resultados de PEX.

Esta atualização fecha a auditoria e registra objetivamente os bloqueios; não certifica a Fase 3. A próxima decisão técnica deve ser sobre a discrepância elétrica observada entre a extração Magic e o benchmark de referência, com revisão dos valores parasitas antes de qualquer ajuste do circuito ou do estímulo.

## Continuidade — 17/11/2026: sondas internas e atribuição temporal

Foi reprocessado **sem nova simulação** o ensaio de sondas
`build/phase3/probe_runs/20261116T052501Z-db99feb6/` com
`tools/phase3_rc_probe_report.py`. O manifesto registra
`COMPLETE_DIAGNOSTIC`, as duas formas de onda foram verificadas pelos hashes
registrados, e a comparação usa interpolação em cada grade temporal. As 13
sondas foram associadas pelo **nome real da coluna** do `waveform.dat` de cada
lado: a ordem alfabética do mapa JSON não coincide com a ordem do vetor
gravado pelo ngspice. Resultado detalhado em
`build/phase3/probe_reports/20261116T052501Z-db99feb6-comparison.json`.

| Evidência | Controle Fase 2 | RC com alimentação idealizada | Observação |
| --- | ---: | ---: | --- |
| `BLB0` aos 139 ns | 1,91228 V | 1,55611 V | Diferença na linha complementar antes da captura |
| `BL0` aos 139 ns | ~0 V | ~0 V | Linha direta próxima de zero em ambas |
| `SA_OUTB0` aos 139 ns | 1,80000 V | ~0 V | Divergência já presente na saída interna do sense amplifier |
| Queda de `CLK` em `_86_.CLK`, limiar 0,9 V | 140,22583 ns | 140,40108 ns | Deslocamento de +0,17525 ns |
| Queda de `evaluation.X`, limiar 0,9 V | 140,43851 ns | 140,83368 ns | Deslocamento de +0,39517 ns |
| Queda de `WL0`, limiar 0,9 V | 140,65312 ns | 141,32281 ns | Deslocamento de +0,66969 ns |
| `precharge_drive.X` aos 143 ns | 0,05555 V | 1,80001 V | Sequência de controle ainda distinta após captura |
| `sense_drive.X` aos 143 ns | 0,04213 V | 1,79998 V | Sequência de controle ainda distinta após captura |
| DATA em 141 ns, esperado `0xAA` | `0xAA` | `0x00` | Leitura 6 falha com RC |
| DATA em 161 ns, esperado `0x55` | `0x55` | `0xFF` | Leitura 7 falha com RC |

O primeiro instante de diferença por sonda no JSON é definido somente pela
grade de **130 a 144 ns, com passo de 0,05 ns e limiar de 0,3 V**. São sondas
selecionadas, e uma diferença antecipada pode ocorrer em ciclos anteriores ou
por deslocamento de fase. Esses números não estabelecem a primeira causa física
da divergência. Em particular, a falha de `SA_OUTB0` aparece antes da captura,
o que exige examinar o desenvolvimento de BL/BLB e as condições de habilitação
do sentido de leitura. O atraso da WL também é observável, mas não é suficiente
para explicar isoladamente a falha.

A inspeção das capacitâncias **incidentes** do SPICE diagnóstico mostrou
aproximadamente **55,3897 fF em BL0**, **55,9542 fF em BLB0**,
**10,8251 fF em SA_OUTB0**, **62,8957 fF em WL0**,
**104,2136 fF em `precharge_drive.X`** e
**131,6763 fF em `sense_drive.X`**. Entre `BL0` e `BLB0`, há
**13,921 fF** de capacitância agregada no modelo com trilhos ideais.
São somas de cartões incidentes e contribuições de acoplamento, **não**
capacitâncias de carga equivalente, nem prova de que um valor extraído esteja
incorreto. Atribuir uma falha a um cartão exige confrontar sua geometria/regras
Magic e uma referência independente, preservando acoplamentos e nós terminais.

No cálculo exploratório de `tACCESS` e `tCLK_TO_DATA`, o cruzamento de DATA
precisa representar a **nova palavra após a borda de descida/captura de CLK**.
A transição anterior à captura pode ser recuperação da palavra anterior.
O analisador passou a classificá-la como `OUTPUT_BEFORE_FALLING_EDGE` e
`NOT_CHARACTERIZED` para o atraso, com teste de regressão. Bits estáveis ou
sem cruzamento único permanecem sem valor temporal atribuído. Os valores de
energia/potência por janela continuam experimentais e só podem ser consumidos
com os estados de simulação, verificação funcional e qualificação elétrica.

Foi verificado no ramo remoto `origin/feature/phase3-infra-leonardo` o contrato
P3-DATA-002 r1, com **626 observações funcionais** aprovadas para a bancada
nominal no seu domínio, sem extensão homologada para RC distribuído. O atual
ensaio de 72 bits mantém classificação **diagnóstica**. O CSV local mantém as
14 colunas do contrato, mas seu manifesto e o conjunto de checks não representam
uma execução do runner homologado para esse domínio. `simulator_status`,
`functional_validation` e `electrical_qualification` são expostos separadamente.
Setup/hold, potência estática e caracterização de timing/potência TT/SS/FF
continuam **`NOT_CHARACTERIZED`**.

Validação local nesta retomada: **23 testes unitários PASS**, incluindo a nova
cobertura de ordem de colunas das sondas, integridade de amostras e classificação
de transições anteriores à captura. O comando `./tools/sram-eda --check`
informou que o contêiner `sram-xschem` não existe neste ambiente. Assim, a
retomada reutiliza os artefatos verificados e não acrescenta execução elétrica.

Para reproduzir o relatório na raiz do projeto:

```bash
python3 tools/phase3_rc_probe_report.py \
  --probe-run build/phase3/probe_runs/20261116T052501Z-db99feb6
python3 -m unittest -q \
  tests.test_phase3_rc_extraction tests.test_phase3_rc_characterization \
  tests.test_phase3_rc_requalify tests.test_phase3_rc_probe \
  tests.test_phase3_rc_probe_report
```

**Próximo bloqueio técnico.** É necessário validar as regras e a geometria dos
parasitas de BL/BLB, WL e dos controles de pré-carga/sense contra uma referência
independente e repetir TT no domínio RC. Uma possível redução das malhas de
alimentação só poderá servir à caracterização após demonstrar preservação das
respostas nos terminais relevantes, incluindo impedância e efeitos de acoplamento
na faixa temporal da leitura. A contração ideal de VDD/VSS usada neste relatório
permanece uma aproximação de diagnóstico. A situação da frente Danilo segue
**NÃO CONCLUÍDA**.

## Continuidade em 17/11/2026

Os ensaios desta retomada estão em `build/phase3/read_path_20261117/`.
O ambiente `sram-xschem` confirmou ngspice 44.2, Magic 8.3.613 e Sky130A
com acesso ao daemon Docker. Os decks usam a macro 4×8, TT, 1,8 V, 27 °C,
clock de 20 ns e carga externa de 10 fF por bit. O GDS de entrada é o
mesmo da aceitação da Fase 2.

### Caminho de leitura por bit

O analisador `tools/phase3_rc_read_path.py` registra o diferencial
`BL−BLB` 50 ps antes de `SCLK` atingir 20% de VDD, a polaridade do
sense, a captura pelo clock local e a estabilização de `DATA`. Os limites
lógicos usados são 0,36 V e 1,44 V. Um bit passa na janela original se
mantiver o nível esperado durante a amostra nominal ±100 ps. A observação
posterior termina 50 ps antes da entrada do host fraco, ou 50 ps antes da
máscara de saída quando o host fraco está desligado.

| Ensaio em TT com trilhos ideais | D correto na captura | Q correto na amostra | DATA correto na janela original |
| --- | ---: | ---: | ---: |
| RC original, 370 ns, máximo de 10 ps | 36/72 | 36/72 | **33/72** |
| Atraso de 1,5 ns no ramo de sense, 170 ns, máximo de 10 ps | 16/16 | 16/16 | **4/16** |
| Mesmo atraso, 370 ns, máximo de 25 ps, host fraco desligado | 72/72 | 72/72 | **24/72** |

Com o RC original, `SCLK` cruza 20% de VDD de 0,214 a 0,222 ns antes
de `WL0` cruzar 80%, nos três acessos à linha 0. O diferencial com
o sinal esperado fica entre **−12,91 e +12,69 mV** 50 ps antes desse
cruzamento de `SCLK`, considerando os nove ciclos e os oito bits. Com
o atraso de diagnóstico, a margem de `WL` até `SCLK` passa a
1,167–1,253 ns, o menor diferencial antes do sense sobe para **1,389 V**
e os pares `SA_OUT/SA_OUTB` resolvem corretamente nos **72/72 bits**.
Os 72 bits chegam corretos a Q. Com o host fraco desligado, **68/72**
estão estáveis ao fim da observação anterior à máscara. A fase de
avaliação do sense explica as decisões internas erradas nesse modelo.
O tempo de propagação entre captura e `DATA` continua limitando a
leitura no pino. O atraso inserido é um elemento ideal de diagnóstico.

Nas 48 mudanças de valor em Q com o host fraco desligado, a descida
pública precede o clock local em 0,420–0,479 ns. O clock local precede
Q válido em mais 0,332–0,390 ns. As 22 descidas válidas de DATA chegam
em 1,129–1,346 ns a partir da descida pública. Nas subidas que chegam
antes do corte de observação, o intervalo é 1,636–2,235 ns. As outras
quatro subidas são em DATA6 e DATA7, com os drivers habilitados até
o corte. Esses intervalos guiam a investigação do clock de captura,
do driver de saída e da carga de roteamento.

Os dados por bit estão em `original_retry_metrics/read_path.csv`,
`delayed_metrics/read_path.csv` e `delayed_no_weak_metrics/read_path.csv`.
O gráfico `read_path_cycle6.png` mostra BL/BLB, WL e sense no bit 0
e a captura até DATA1 na leitura de `0xAA`, com os hashes em
`read_path_cycle6_sources.json`.

### Dupla contagem confirmada no Magic 8.3.613

A reexportação do mesmo `.ext` com `ext2spice extresist off` preservou
os 1.493 MOS e seus parâmetros. O mapeamento depois de contrair os
resistores associa 730 redes pelos terminais MOS. O utilitário
`tools/phase3_rc_cap_audit.py` compara os totais por par de redes.
Detectou **15 pares divergentes em 4.941**, todos referenciados a VSS,
com 985,707 fF a mais no RC. Em `DATA[6]`, o RC exporta 29,38384 fF
para VSS, soma dos 9,52128 fF de substrato com os 19,86256 fF de
acoplamento, e mantém os capacitores de acoplamento entre as redes.
O comportamento coincide com a dupla contagem descrita no
[Magic #550](https://github.com/RTimothyEdwards/magic/issues/550).

O par BL0–BLB0 já contém 13,9206 fF no `.ext` 8.3.613 e conserva esse
valor no RC. A extração histórica da Fase 2 em 8.3.684 registra
7,68113 fF para o par no mesmo GDS. Entre essas revisões houve mudança
na interpretação da regra de sidewall, revertida em 8.3.693. Essa
comparação de versões estabelece a diferença do extrator. A validação
numérica independente da regra física continua pendente.
[Correção de sidewall no Magic](https://github.com/RTimothyEdwards/magic/commit/9fd4ee57386c08346b20389a55e4eb9d32553979)

Para isolar o efeito da dupla contagem, a variante `cap_only_trial`
usa os resistores de sinal do RC original, as capacitâncias da exportação
C-only ligadas aos nós nominais, alimentação idealizada e o circuito
original de sense. O procedimento preserva o valor por par da referência
C-only. A localização distribuída de C e a impedância de alimentação
ficam fora desse modelo de diagnóstico. Em 370 ns, com passo máximo de
25 ps, **32/72** bits passaram na janela original de DATA e **36/72**
chegaram corretos a D e Q. A ativação precoce de SCLK persistiu.
`SCLK20` veio de 0,214 a 0,301 ns antes de `WL80` e o diferencial
antes de sense continuou na faixa de milivolts. Os passos máximos
diferem entre esse ensaio e o original de 33/72, portanto a diferença
de um bit não é atribuída à troca dos capacitores.

### Reextração do GDS com Magic 8.3.703

Foi compilada uma instalação local em `build/phase3/read_path_20261117/`
a partir do commit `2c6d97b2f21003fa1778d5658eb02b32724399ab`. A extração
usou o mesmo techfile Sky130A, SHA-256
`3129815ae08ff4e4459d93dcea18121a311638a85110d884500351e406edd3d0`.
O log e o manifesto da extração completa estão em
`upstream_extraction/20261118T024527Z-0d383d6e/`. O identificador do
diretório usa UTC e a execução ocorreu em 17/11 no fuso de Manaus.
[Código-fonte do Magic](https://github.com/RTimothyEdwards/magic/tree/2c6d97b2f21003fa1778d5658eb02b32724399ab)

| Verificação | RC completo 8.3.703 |
| --- | --- |
| Identidade do GDS | `83e72aee8d45a9826751cdefd46dd062acc2a17ec0acfd33c07f218d20d8e64e` |
| SHA-256 do SPICE | `f7079a1e38720e86bd290c34fea2b268c2625cdad98376388a9f82d0d4438548` |
| Elementos | 1.493 MOS, 14.394 R, 11.235 C |
| Alimentação | VDD chega a 1.302 terminais MOS, VSS a 1.275, sem curto resistivo |
| Conservação de C por par de redes | **5.026/5.026** dentro da tolerância de exportação |
| DATA6–VSS | 9,52642 fF no RC, 9,52641 fF no C-only |
| BL0–BLB0 | 13,92880 fF em ambas as exportações |

A exportação C-only de referência foi feita na extração dos sinais
críticos com a mesma versão. Os dois `.ext` diferem apenas no timestamp.
`cap_audit_703_full/net_pairs.csv` registra todos os pares e a
conservação após contrair os resistores para a comparação. A extração
completa reteve os resistores distribuídos. A auditoria valida a
contabilização de capacitâncias. A precisão da distribuição espacial e
das impedâncias dos trilhos exige validação elétrica.

O ensaio C-only `cap_coupon/` usa duas linhas M4 isoladas de 0,60 µm de
largura, 2,80 µm de espaçamento e 69,34 µm de trecho paralelo, dimensões
dos trechos principais de BL0/BLB0 medidas no GDS. O cálculo pela regra
`defaultsidewall` do estilo `ngspice()` é
`94 × 69,34 / (2,80 + 0,57) = 1.934,1128 aF`.
Ambas as versões exportaram **1,93411 fF**. O ensaio confere a escala da
regra na geometria isolada. Vizinhos, cruzamentos e blindagem na macro
completa exigem referência adicional. A tentativa de extração resistiva
do cupom com duas portas por condutor terminou em falha do Magic 8.3.613.

O rebatimento dos terminais dos 1.493 MOS, após a contração dos
resistores para a comparação, encontrou as mesmas 730 redes da
referência funcional da Fase 2. O recibo `phase2_connectivity_703.json`
registra a comparação e seus hashes.

### TT da macro original com RC completo

O ngspice 44.2 completou os 370 ns com passo máximo de 10 ps e os
trilhos distribuídos. Foram exportadas 38.337 amostras. O resultado é
`FAIL_FUNCTIONAL`, com **32/72 bits aprovados e 40/72 falhas** na
janela original. A primeira leitura teve 0/8 bits estáveis na janela.
Nas oito leituras seguintes, DATA estava integralmente alto no instante
nominal e só 4/8 bits por palavra coincidiram com o esperado.

O simulador identificou `m1_16160_31260#` como nó sem caminho DC.
O nó consta na extração como metal com conexões apenas capacitivas.
Após tentativas de gmin e source stepping, o log registra ponto
de operação transitório bem-sucedido. O deck foi executado com suas
capacitâncias e sem resistor artificial nesse nó. O manifesto em
`upstream_electrical/20261118T025928Z-tt-96becae7/manifest.json`
registra `simulator_status=PASS` e `electrical_qualification=NOT_CHARACTERIZED`.

### Antecipação da wordline para o tap 48

Em `tap48_trial`, a extração dos sinais críticos pelo Magic 8.3.703
tem 358 resistores e passa na comparação dos 5.026 pares de C. No
circuito de diagnóstico, as portas dos dois MOS da entrada C de
`evaluation` passam do tap 60 para o tap 48. O restante do netlist
usa a extração do roteamento anterior. Com 370 ns e passo máximo de
25 ps, o sense e D/Q ficam corretos em **72/72 bits** e os pinos
passam em **24/72 bits** na janela original. O intervalo de `WL80`
até `SCLK20` fica em 0,258–0,351 ns, com diferencial antes do sense
de pelo menos **316 mV**. Os BL/BLB foram sondados nos terminais dos
MOS de amostragem do sense, depois da resistência distribuída.

O resultado demonstra uma alternativa de ligação para investigar no
layout. O intervalo de escrita, a captura e o caminho de saída precisam
ser verificados após o roteamento. Os decks, hashes e MOS alterados
estão em `tap48_trial/inputs.json`, com as medições em
`tap48_metrics/read_path.csv`.

### Clock de captura e driver de saída

O ensaio `tap48_root_clock_trial` ligou os oito inversores de captura
ao nó `clkbuf_0_CLK.X`, antes dos dois buffers de folha. O transiente
isolado expirou próximo de 167,26 ns e ficou sem waveform exportada.

O ensaio `combined_output_trial` usou o tap 48, a mesma ligação de
clock e a topologia do `ebufn_2` do PDK. Foram acrescentados 32 dedos
de transistor e redimensionados oito MOS de habilitação do pull-up,
mantendo 358 R e 7.376 C do roteamento original. A simulação até
165 ns completou os ciclos 6 e 7. Os **16/16** bits chegaram corretos
ao sense, a D e a Q, e **16/16** estabilizaram em DATA antes do host
fraco. Na janela original, passaram **8/16**. As oito falhas restantes
foram subidas, com DATA válido de 0,960 a 1,379 ns após a descida
pública. Nas mesmas transições, o clock local chegou em 0,223–0,228 ns.
A geometria de difusão das células ampliadas é aproximada, e os
parasitas da rota precisam ser extraídos após o ECO físico.

O mapeamento dos transistores e os hashes estão em
`output_eco/mapping.json` e `combined_output_trial/capture_clock_change.json`.
As medições estão em `combined_output_metrics/read_path.csv`.

Com a projeção `ebufn_8`, a mesma ligação ao clock raiz aprovou
**16/16** bits no instante nominal e **15/16** durante a janela
completa. No ciclo 7, DATA6 atingiu 1,44 V a 0,892 ns da descida
pública, cerca de 17 ps após o início da janela. A duração máxima
de passo era 25 ps. O valor identifica um caso marginal e serve
para selecionar a próxima variante. Os resultados estão em
`combined_output8_metrics/read_path.csv`.

Na variante `combined_public_clock_full_trial`, os oito inversores de
captura foram ligados ao nó CLK de entrada, mantendo os buffers originais
dos outros domínios. Com 370 ns e passo máximo de 25 ps, passaram
**72/72** no sense, em D/Q e na janela de DATA. O menor diferencial
com sinal esperado antes de SCLK foi **316 mV** e a última transição
de DATA se estabilizou a **0,692 ns** da descida pública. O resultado
usa a topologia `ebufn_8` projetada sobre os parasitas da rota anterior.
As cargas do novo roteamento e a impedância distribuída dos trilhos
ficam fora desse ensaio. As medidas e hashes estão em
`combined_public_clock_full_metrics/`.

### Protótipo físico em 18/11/2026

O protótipo implementa tap 48 em `evaluation.C`, ligação dos inversores
de captura ao CLK de entrada e oito drivers `ebufn_8`. O roteamento
OpenROAD ficou em `route_eco8_prepared/`. A primeira exportação usou
por engano o GDS da matriz antes da normalização da origem do LEF.
Essa incompatibilidade deslocou a matriz e gerou violações na
reimportação. As tentativas com outro conversor, exportação plana e
restrição de camada usavam a mesma entrada incompatível.

O mesmo ODB foi exportado novamente em
`route_eco8_normalized_fabric/layout/` com o par GDS/LEF de
`layout_v1`, verificando ambos os hashes do manifesto `route_v1`.
O GDS resultante tem SHA-256
`b69f657d20a9eb76446bcceee9ae668a813dda64b2567690392f3bf55fb5e57d`.
A reimportação independente no Magic 8.3.703 passou com **DRC=0**.
O Netgen obteve **LVS único**, com 1.733 MOS extraídos, 16 portas
e 730 redes. A referência foi gerada do Verilog do protótipo e da
mesma matriz da Fase 2. O recibo é `layout_verification.json` e
os detalhes estão em `reimport/magic.log` e `reimport/lvs.txt`.

### Extração e TT pós-layout do protótipo

O RC dos sinais críticos tem 615 R e 7.735 C, com os 5.169 pares
capacitivos conservados e caminhos DC dos dois trilhos até os MOS.
Em TT, 1,8 V, 27 °C e 10 fF por saída, o ngspice completou
370 ns com passo máximo de 25 ps e **72/72 bits** aprovados na janela
original de ±100 ps. O recibo está em `eco_tt_signals/manifest.json`.
Essa extração distribui R nos sinais selecionados. As malhas de
alimentação distribuídas fazem parte do ensaio integral.

O RC integral bruto tem 16.023 R e 12.393 C. O verificador encontrou
oito diferenças de capacitância de substrato. Em todos os oito nós,
a soma dos `rnode` da rede antes do formato SPICE reproduz a
capacitância ao substrato da exportação C-only. Os `rnode` positivos
abaixo de 1 aF, omitidos na formatação decimal do Magic, explicam a
diferença dentro da tolerância de exportação. Por exemplo, no nó
`a_50271_10101#`, a soma distribuída é 0,0324138 fF. Os termos abaixo
de 1 aF somam 0,007217 fF, e o C entre a rede e VSS no RC ficou em
0,02519 fF.

Em `eco_rc_all_subatto/`, `restore_subatto_caps.py` recuperou
os valores do `.res.ext` em 123 cartões de capacitância de substrato
que continham zero, totalizando 0,060916 fF. Foram preservados os
terminais, os 16.023 resistores, os transistores e as demais
capacitâncias. A auditoria dessa netlist verifica **5.169/5.169**
pares dentro da tolerância. O manifesto e a lista de cartões em
`subatto_caps.json` permitem conferir cada valor e sua origem.
O RC integral do protótipo usa o SHA-256
`f550337136e71772585c1d7b1a843770f8e4e51885d3b1817745e0b61d4e2595`.

Da raiz do projeto, com a instalação local 8.3.703 disponível no contêiner:

```bash
work=build/phase3/read_path_20261117
./tools/sram-eda python3 tools/phase3_rc_extraction.py \
  --magic "/work/$work/magic-8.3.703/bin/magic" \
  --output-root "$work/upstream_extraction"

python3 tools/phase3_rc_cap_audit.py \
  --rc "$work/upstream_extraction/20261118T024527Z-0d383d6e/extracted_rc.spice" \
  --c-only "$work/upstream_signal_rc/c_only.spice" \
  --output "$work/cap_audit_703_full_replay"

python3 tools/phase3_rc_read_path.py "$work/delayed_no_weak" \
  --output "$work/delayed_no_weak_replay"

./tools/sram-eda python3 tools/phase3_rc_characterization.py \
  --extract-run "$work/upstream_extraction/20261118T024527Z-0d383d6e" \
  --corner tt --supply-model full --timeout 3900 \
  --output-root "$work/upstream_electrical"
```

### Estado da caracterização integral do protótipo

O ensaio TT com a extração integral corrigida do protótipo foi iniciado em
`eco_tt_full/`, usando o RC restaurado cujo SHA-256 está registrado acima.
Na primeira tentativa, o `ngspice.log` terminou em **323,5 ns** sem waveform;
a causa da interrupção não foi estabelecida. A repetição, com o mesmo deck,
RC e hashes dos três arquivos de entrada, concluiu 370 ns em ngspice 44.2 e
gerou 22.521 amostras em `eco_tt_full_retry_20261118/`. O manifesto registra
`simulator_status=PASS`, **72/72** bits corretos na verificação funcional
pública da janela original e `electrical_qualification=NOT_CHARACTERIZED`.
Esse resultado é para o protótipo com topologia alterada e RC integral; não
reverte o resultado **40/72 FAIL** da macro original.

O analisador público encontrou `tACCESS` mensurável em **37/72** casos; os
outros 35 ficaram `NOT_CHARACTERIZED` porque não houve transição qualificável
na janela definida pelo analisador. `tCLK_TO_DATA` também teve 37 medidas
válidas. A energia integrada por ciclo de 20 ns ficou em 13,67–16,64 pJ para
leitura, 10,55–12,20 pJ para escrita e 3,14–3,93 pJ nos ciclos idle. As
potências médias de ciclo correspondentes foram 0,683–0,832 mW, 0,527–0,610
mW e 0,157–0,197 mW. Esses valores incluem o consumo integrado no ciclo
completo, inclusive leakage, e são medidas exploratórias do modelo TT a 1,8 V,
27 °C e 10 fF por saída; não constituem potência dinâmica isolada nem
caracterização qualificada. Recibos e CSVs estão no mesmo diretório do run.

O corner SS também completou 370 ns e 20.437 amostras, mas falhou em
**31/72 bits** na mesma janela funcional pública. As falhas ocorreram nos
ciclos 6, 7, 11, 13, 14, 15 e 16; uma saída alta representativa chegou a
1,409 V, abaixo do limite de 1,44 V. O simulador terminou normalmente, porém
timing e potência SS não são qualificáveis com a funcionalidade reprovada.
Manifesto, waveform, checks e log estão em `eco_ss_full_20261118/`.
O ensaio FF, em `eco_ff_full_20261118/`, também completou 370 ns, com
22.943 amostras e **72/72 bits corretos**
na janela funcional pública. `tACCESS` foi mensurável em 38/72 bits; os outros
34 não tiveram transição qualificável na janela. É um PASS exploratório para
o protótipo e as condições registradas, não signoff da macro. A energia por
ciclo de 20 ns ficou em 15,20–18,22 pJ para leitura, 10,54–12,22 pJ para
escrita e 3,19–3,92 pJ em idle; as potências médias de ciclo foram
0,760–0,911 mW, 0,527–0,611 mW e 0,160–0,196 mW. Como em TT, são integrais
do ciclo completo, incluindo leakage, e não potência dinâmica isolada.

### Fechamento da frente e pendências do Marco 3

| Entrega | Estado observado em 18/11/2026 |
| --- | --- |
| Extração RC completa e auditoria de capacitâncias | **Concluída estruturalmente** para a macro original e para o protótipo; a causa de contagem excessiva no Magic 8.3.613 foi isolada e a extração 8.3.703 conservou 5.026/5.026 pares da macro original. A validação de impedâncias e parasitas da macro completa ainda é limitada. |
| Macro original, TT, leitura funcional com RC integral | **FAIL_FUNCTIONAL**, 40/72 bits; não qualifica timing ou potência. |
| Protótipo, DRC/LVS | **PASS** na versão roteada identificada em `layout_verification.json`; isso verifica a implementação física, não caracteriza a SRAM. |
| Protótipo, TT com RC dos sinais críticos | **PASS de janela funcional**, 72/72; não inclui o RC integral de alimentação. |
| Protótipo, TT com RC integral | **PASS exploratório**, 72/72, 370 ns, 22.521 amostras; tACCESS mensurável em 37/72. Não é signoff da macro. |
| Protótipo, SS com RC integral | **FAIL_FUNCTIONAL**, 31/72 bits; sem qualificação de timing/potência. |
| Protótipo, FF com RC integral | **PASS exploratório**, 72/72, 370 ns, 22.943 amostras; tACCESS mensurável em 38/72. Não é signoff da macro. |
| Caracterização de tempo de acesso e potência em TT/SS/FF | **PARCIAL**; TT/FF têm medidas públicas exploratórias, mas 35/72 e 34/72 tACCESS ficam `NOT_CHARACTERIZED`, respectivamente. SS falhou funcionalmente. Potência medida é média do ciclo completo, não potência dinâmica isolada. |
| Setup/hold e potência estática | **`NOT_CHARACTERIZED`** na instrumentação disponível. |
| SNM com Monte Carlo, N ≥ 200 | Há dados existentes de 200 seeds para SNM read e hold em `sf_mm`, referenciados em `docs/matriz_testes_bitcell_6t.md` e `docs/relatorio_validacao_bitcell_6t_sky130.md`. São triagem pré-layout da bitcell em dois pontos, não Monte Carlo da macro nem cobertura PVT/yield completa; a frente de SNM precisa confirmar se os reutiliza como entrega do Marco 3. |
| `.lib` simplificada gerada de dados reais e validada | **PENDENTE** na evidência desta frente; pertence à infraestrutura/Liberty. |
| Caracterização física 8×8 e 32×8 | **PENDENTE**, condicionada à geração dessas dimensões prevista para a Fase 4 ou a uma decisão formal de antecipação. |
| Revisão cruzada e relatório integrado | **PENDENTE**. |

**Conclusão:** o protótipo roteado passa o benchmark público com RC integral em
TT e FF, mas falha em SS (31/72); a macro original continua reprovada em TT
(40/72). A alteração de topologia ainda requer decisão de adoção e correção
para SS antes de ser considerada solução funcional nos três corners. As métricas
públicas TT/FF são exploratórias; SS não qualifica timing nem potência. Setup/
hold e potência estática seguem `NOT_CHARACTERIZED`; o deck público não mede
atraso interno de leitura nem separa potência dinâmica de leakage. A Fase 3
integrada também depende da validação/revisão da SNM existente, geração e
validação da `.lib`, decisão sobre 8×8/32×8 e revisão cruzada conforme o plano.
