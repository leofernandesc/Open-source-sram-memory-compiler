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
