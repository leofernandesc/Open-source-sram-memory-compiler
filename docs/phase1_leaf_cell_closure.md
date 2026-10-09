# Fase 1 — fechamento das leaf cells SKY130A

**Atualização de 08/10/2026 — Ciclo 4 concluído.** O gate de qualificação de
engenharia da Fase 1 está fechado para a bitcell 6T e suas leafs/periféricos
qualificados. A linha WL de 8 bits e a coluna G7 mantêm Magic DRC hierárquico e
flat `0`, LVS Netgen único e PEX. A inicialização nos nós `.t0` da latch passou
2/2 estados complementares e estáveis por 5 ns.

A PVT válida mede `C_BL,PEX=473,178787–519,179340 fF`; o máximo ocorre em
`ss/1,62 V/125 °C/Q0/BLB`, e o limite de teste é `597,056241 fF`
(`1,15 × C_BL,PEX,max`). A linha física de oito bits mede
`102,328671–102,873935 fF`; a maior diferença pareada linha menos bitcell é
`CWL_EXTRA=93,351918 fF`. As Ceff PEX requalificadas são: bitcell
`6,112664–8,894565 fF`, precharge W2,52 `11,469724–13,064186 fF`, sense
scale1p5 `31,644459–34,172158 fF` e write W5,04 `22,624034–55,101988 fF`.

A leitura passou `60/60` em `C_BL=597,056241 fF` e
`CWL_EXTRA=93,351918 fF`: ΔBL mínimo `0,334350 V`, setup mínimo `804,60 ps`,
`t_res` máximo `0,246350 ns` e disturb máximo `0,196491 V`. O ponto crítico
foi refinado com passo de 1 ps; os oito casos SS/FF a 125 °C passaram, com
`t_res,max=0,246950 ns` e disturb máximo `0,196488 V`.

A escrita passou `60/60` com CBL residual calculada por canto, estado, dado e
lado BL/BLB, sem recobrar capacitâncias já explícitas; cada lado totaliza
`597,056241 fF`. Com WE em `2,20 ns` e WL_IN em `3,40 ns`, a pré-condição do
write driver é `1,20 ns`. O flip máximo é `0,720280 ns`, o limite WL com +30%
é `0,936364 ns`, a menor folga WL30 é `79,696 ps`, a menor folga até a queda
da WL é `0,295780 ns` e a recuperação máxima é `3,978840 ns`. O caso mais
lento foi refinado a 1 ps e passou com recuperação de `3,979500 ns`.

**Estado: `CLOSED_ENGINEERING_QUALIFICATION` no escopo da Fase 1.** Após esse
fechamento, a arquitetura do decoder 2→4 foi alterada de estática para dinâmica
e foi criado um candidato transistor-level em `cells/row_decoder_2to4.spice`.
No planejamento atual, o decoder dinâmico foi realocado para a Fase 2: sizing, transientes
PVT, charge-sharing/leakage, captura Xschem, layout, DRC/LVS e integração macro
4×8 seguem pendentes. Essa realocação altera o planejamento original associado
ao entregável do decodificador e requer validação formal da equipe/orientadores. A alteração do decoder não reabre os gates medidos da
bitcell/leafs; a qualificação do novo bloco precisa de evidências próprias.

## Gates finais da Fase 1 — 08/10/2026

| Gate | Evidência disponível | Situação para aceite da Fase 1 |
|---|---|---|
| G1–G4 e schematic freeze | Sizing canônico `0,42/1,26/0,60 µm`; screening pré-layout preservado | **Fechado** como qualificação de engenharia |
| G6 e G7 físico | Cinco leafs, abutment gap zero normal/espelhado, coluna 32×, linha WL 8 bits e coluna G7 com `drc(full)=0`, LVS único e PEX | **Fechado fisicamente** |
| Inicialização da bitcell | `Q=a_215_n2026.t0`, `QB=a_167_n2114.t0`; estabilidade complementar por 5 ns | **Fechado**, 2/2 estados |
| C_BL e leaf Ceff | Bitcell 120/120; precharge 60/60; coluna 120/120; sense 360/360; write 120/120 | **Fechado**; limite de teste `597,056241 fF` |
| C_WL | Linha e bitcell 60/60; diferença pareada máxima `93,351918 fF` | **Fechado**; aplicar como carga WL extra |
| Leitura G7 | CBL `597,056241 fF`; ΔBL min `0,334350 V`; setup min `804,60 ps`; `t_res` max `0,246350 ns`; disturb max `0,196491 V` | **Fechado**, 60/60; casos críticos refinados a 1 ps passaram |
| Escrita G7 | CBL por lado/caso `597,056241 fF`; flip max `0,720280 ns`; recuperação max `3,978840 ns`; folga WL30 min `79,696 ps` | **Fechado**, 60/60; caso lento refinado a 1 ps passou |
| Decodificador dinâmico 2→4 e macro 4×8 | Candidato SPICE em `cells/row_decoder_2to4.spice`; sem simulação elétrica nem layout/DRC/LVS | **Planejado para a Fase 2 — pendente de validação da equipe/orientadores**, qualificação e integração pendentes |

### Conferência manual de DRC/LVS — 08/10/2026

- **Bitcell 6T:** o operador obteve `Total DRC errors found: 0` na
  console Tcl gráfica do Magic; evidência em captura da sessão, sem novo log
  manual anexado ao repositório.
- **Coluna G7:** o DRC completo retornou `0` tanto para
  `column_32_full_g7_wpre2p52` (hierárquica) quanto para a célula `_flat`;
  confira [`audit_full_drc_requal.log`](../layout/column_32_full_g7_wpre2p52_final/audit_full_drc_requal.log).
- **LVS manual da G7 com setup SKY130A:** o Netgen carregou
  `/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl` e retornou
  `Circuits match uniquely.` com `212` transistores (`136` NMOS e `76` PMOS)
  e `82` redes de cada lado. O operador copiou o log para
  `layout/column_32_full_g7_wpre2p52_final/lvs_sky130_manual.log`
  (arquivo local ignorado pelo Git). O relatório de requalificação anterior
  permanece em [`column_32_full_g7_requal_lvs.log`](../layout/column_32_full_g7_wpre2p52_final/column_32_full_g7_requal_lvs.log).

O LVS manual inicial com `/dev/null` permanece como evidência histórica. A
repetição com setup SKY130A **foi confirmada**, mas o Netgen ainda avisou sobre
subcircuitos MOS indefinidos (*placeholders/black boxes*) e propriedades
ausentes. A equivalência confirmada é **estrutural** e não comprova sozinha
equivalência completa de parâmetros MOS. Isso não altera os resultados DRC e
das PVTs PEX registrados. Comandos e procedimento:
[validação manual de DRC/LVS](validacao_manual_drc_lvs_sky130a.md).

Na leitura, os leaves PEX reais de bitcell, precharge e sense são instanciados;
`CBL_EXTRA=547,829394 fF` subtrai a soma dos mínimos PEX dessas folhas e
mantém cada corner no limite ou acima dele. Na escrita, o runner usa Ceff PEX
de bitcell, precharge e write driver alinhados a PVT/estado/dado/probe e calcula
um residual independente para BL e BLB; os residuais variam de `520,537871` a
`549,979800 fF` em BL e de `526,883490` a `556,284660 fF` em BLB. Em cada caso,
o total equivalente por lado é `597,056241 fF`. A carga WL extra desconta a
bitcell já presente na linha física de 8 bits.

Os resultados atuais estão em `sims/bitcell_pex_bitline_capacitance_latch_t0_requal_20261008.csv`,
`sims/precharge_w2p52_pex_capacitance_provenance_20261008.csv`,
`sims/column_32_full_g7_wpre2p52_pex_capacitance_latch_t0_requal_20261008.csv`,
`sims/row_8_wl_pex_capacitance_latch_t0_requal_20261008.csv`,
`sims/bitcell_pex_wordline_capacitance_latch_t0_requal_20261008.csv`,
`sims/sense_scale1p5_pex_input_capacitance_provenance_20261008.csv` e
`sims/write_driver_w5p04_pex_capacitance_provenance_20261008.csv`.
As matrizes integradas são `sims/g7_read_requal_latch_t0_20261008.csv` e
`sims/g7_write_requal_casewise_wlsetup1p2ns_20261008.csv`; os refinamentos de
1 ps estão em `sims/g7_read_critical_refined_1ps_20261008.csv` e
`sims/g7_write_critical_refined_1ps_20261008.csv`.

## Registro histórico — checkpoint do Ciclo 0 (08/10/2026; supersedido)

As falhas dos smokes anteriores à correção de inicialização e o lote de
escrita interrompido **não** qualificam nem reprovam o circuito. Yield de
produção, ruído estatístico completo, DC-SNM-PVT e teto de potência da macro
estão fora do escopo declarado desta fase.

## Registro histórico de 07/10/2026 — supersedido pela atualização acima

**Na revisão de 07/10/2026, a Fase 1 foi considerada concluída no escopo de qualificação de engenharia.** O
sizing canônico foi congelado em `WPU/WPD/WACC=0,42/1,26/0,60 µm` após o
fechamento elétrico G1–G4 e uma regressão curta pós-aplicação. As cinco leafs
(`bitcell_6t`, `sense_amp`, `precharge`, `wl_driver`, `write_driver`) têm agora
layout SKY130A, Magic DRC `0` no flat e Netgen LVS com `Circuits match uniquely`.
A bitcell também passou smoke de abutment em gap zero, tanto na orientação
normal quanto com o vizinho espelhado horizontalmente, ambos com DRC `0`.
A entrega física G6 da Fase 1 está concluída. No G7, a coluna física 32× integra
sense 1,5×, precharge `W=2,52 µm` e write driver `Wout=5,04 µm`; layout
hierárquico e flat têm Magic DRC `0`, LVS estrutural único e PEX RC. A extração
PVT passou `120/120`, com `C_BL,PEX,max=453,588405 fF` e teto de
requalificação `521,626665 fF`. A linha WL física de 8 bits mede
`C_WL,PEX,max=98,914001 fF`; `89,925201 fF` entram como carga extra nos benches.

A requalificação integrada pós-layout passou `60/60` em leitura e `60/60` em
escrita. Na leitura, `t_res` máximo foi `0,23209 ns` (limite `0,25 ns`), o
read-disturb máximo `0,1796454 V` (limite provisório `0,20 V`), setup mínimo
`566,03 ps` e diferencial mínimo `0,276681 V`. Na escrita, a recuperação
máxima foi `3,49470 ns` dentro da janela de 4 ns; a margem mínima da WL antes
da queda foi `0,34274 ns`. A carga simulada foi igual ou superior ao teto PEX.
Os CSVs dos benches registram os caminhos e hashes SHA256 dos netlists.

Na revisão de 07/10, o G7 e a Fase 1 foram considerados fechados no escopo de engenharia. As campanhas existentes
de SNM/mismatch permanecem screening, sem claim de yield de produção; ruído
estatístico completo e teto de potência macro não são requisitos bloqueadores
desta fase.

## Como usar as referências

| Referência | Apoio aplicável | Limite para este projeto |
|---|---|---|
| [ShonTaware/SRAM_SKY130](https://github.com/ShonTaware/SRAM_SKY130) | Exemplo de 6T SKY130 e Read SNM; `0,2 fF` é aproximação de dreno adotada ali. | Não substitui a capacitância medida da nossa bitcell nem valida nosso layout. |
| [Deepak42074/vsdsram_sky130](https://github.com/Deepak42074/vsdsram_sky130) | Exemplos de Hold/Read SNM. | Resultados de outro sizing/testbench não definem nosso aceite. |
| [SRAM Design with OpenRAM in SkyWater 130nm](https://confcats-event-sessions.s3.amazonaws.com/iscas23/papers/2314.pdf) e [cópia NSF PAR](https://par.nsf.gov/servlets/purl/10495552) | Nominal 1,8 V; arquitetura com replica bitline, dummy cells/rows e habilitação do sense. | O circuito e os corners precisam ser validados aqui; a publicação não aprova `±10%` para nossos `01v8`. |
| [65-nm Reliable 6T CMOS SRAM Cell](https://arxiv.org/pdf/2411.18114) | Mostra a relevância da tensão de WL para estabilidade de leitura. | Outro nó: não fornece um `t_WL,max` SKY130A. |
| [Design and Simulation of 6T SRAM Array](https://arxiv.org/pdf/2508.09419) | Relação aproximada `t ≈ C_BL × ΔV / I_cell`. | Exige medir `I_cell`, capacitância e o alvo real de `ΔV`; não fixa pulso nem 100 mV. |
| [OpenRAM results](https://github.com/VLSIDA/OpenRAM/blob/stable/docs/source/results.md) | Exemplos de views e resultados de macro. | Não serve como certificado DRC/LVS das nossas células. |
| [UT Austin EE382M](https://users.ece.utexas.edu/~mcdermot/vlsi1/VLSI2_SP_2017/vlsi2/lectures/16.pdf) e [Nirma University](https://repository.nirmauni.ac.in/jspui/bitstream/123456789/4740/1/12MECV16.pdf) | Pistas para estudar pulso de WL e trade-offs. | Ainda não há extração verificável de números desses PDFs neste trabalho; não atribuir a eles os limites locais. |

O alvo integrado de `200 mV` de diferencial (`150 mV` como piso efetivo de
mismatch + `50 mV` de guarda pré-layout), `+20%` no fio, `+15%` sobre PEX,
`+30%` no tempo de escrita, alvo nominal de Read SNM `>=0,4 V` e limites de read disturb são
**propostas/critério interno**. `1,62–1,80 V` é a faixa de qualificação
escolhida para o modelo atual; `1,95 V` é ponto de auditoria estática e
`1,98 V` não está qualificado. A validade dos modelos nas temperaturas
extremas continua sujeita à confirmação do PDK.

## Estado por célula — registro histórico de 07/10

| Leaf | Esquemático, evidência elétrica e fechamento físico | Resultado histórico do G7 em 07/10 (supersedido) |
|---|---|---|
| Bitcell 6T | `cells/bitcell_6t.sch` e `cells/bitcell_6t.sym` usam o sizing canônico `0,42/1,26/0,60 µm`. G1–G4 fecharam para screening pré-layout; Read SNM nominal `0,414349 V` e read-disturb crítico pré-layout `0,1781393 V`. `layout/bitcell_6t` fecha com DRC `0`, LVS único e abutment normal/espelhado em gap zero com DRC `0`. | Incluída nas matrizes G7 com carga CBL PEX e WL física. Leitura e escrita integradas passaram `60/60`; o resultado anterior com quatro falhas de recuperação pertencia à coluna `Wpre=2,10 µm` e foi supersedido pela variante final `Wpre=2,52 µm`. |
| Sense amplifier | `cells/sense_amp.sch` contém latch regenerativo de sete transistores com amostragem PMOS; o netlist do próprio Xschem passou 330/330 casos determinísticos. No G2, `150 mV` acumula `800/800` decisões sem falha; G4 promoveu `SCLK=2,84 ns`. `layout/sense_amp` fecha com DRC `0` e LVS único, 7 dispositivos/8 nets. A variante física `1,5×` passa DRC/LVS/PEX; a medição crítica na revisão anterior registrou `t_res=0,22060/0,23257 ns`, sucedida pela coluna final cuja matriz integrada fechou `60/60` e `t_res,max=0,23209 ns`. | Qualificação de leitura pós-layout concluída; não há falha de sense aberta no G7 atual. |
| Precharge/equalização | `cells/precharge.sch` gera netlist conectado; Ceff máximo pré-layout `0,908533 fF` por bitline. A variante física `Wpre=2,52 µm` tem DRC zero, LVS único com setup SKY130, PEX RC e Ceff PVT de `10,552944–12,009657 fF`. Integrada à coluna G7 revisada. | Escrita pós-layout `60/60 PASS`; recuperação máxima `3,49470 ns` em janela de 4 ns. |
| WL driver | `cells/wl_driver.sch` gera dois inversores conectados; sizing `0,42/0,84 µm`. O smoke selecionado passou em `tt/1,8 V/27 °C` e `ss/1,62 V/−40 °C`. `layout/wl_driver` fecha com DRC `0` e LVS único, 4 dispositivos/5 nets. A variante integrada reforçada tem PEX; linha física de 8 bits: `98,914001 fF`, com `89,925201 fF` extras no bench. Leitura e escrita pós-layout foram simuladas com essa carga. | G7 integrado passou `60/60` em leitura e escrita; slews de WL foram `255,85–427,69 ps` na subida e `102,11–159,72 ps` na descida. Escrita: largura efetiva `1,00475–1,04705 ns`, limite mínimo calculado `0,871819 ns` e margem mínima `0,34274 ns` antes da queda da WL. |
| Write driver | Com bitcell `WPD=1,26 µm` e 65 fF, a integração passou `60/60`; G4 mismatch passou os corners selecionados. `layout/write_driver` fecha com DRC `0` e LVS único, 10 dispositivos/12 nets, preservando `WE_B` e os quatro nós internos dos stacks. A variante física `Wout=5,04 µm` tem PEX e foi usada na matriz pós-layout. | G7 integrado passou `60/60`; recuperação máxima `3,49470 ns` dentro de 4 ns e margem mínima `0,34274 ns` antes da queda da WL. O resultado anterior `56/60` da variante `Wpre=2,10 µm` foi supersedido. |

## Gates da Fase 1 — registro histórico de 07/10, supersedido

1. **Contrato elétrico e schematic freeze — concluídos.** O sizing canônico
   `WPU/WPD/WACC=0,42/1,26/0,60 µm`, pinos, polaridades e netlists Xschem
   foram congelados após G1–G4. O sizing das variantes físicas reforçadas de
   sense, precharge, write e WL foi então validado por DRC/LVS/PEX e G7.
2. **CBL pré-layout e substituição por PEX — concluído.** O orçamento de fio `metal2`, `0,14 µm`, até
   `5 µm/linha`, dois vizinhos e margem interna de 20% produz
   `Cwire<=1,061862 fF/linha`. Com `Ccell=0,452619 fF`,
   `Cprecharge=0,908533 fF`, `Cwrite=4,033129 fF`, `Csense=9,004605 fF` e
   `Cmux=0`, os máximos calculados são
   `20,004191/26,062115/38,177963/62,409659 fF` para
   `4/8/16/32` linhas. Verificar `Csense` também durante a excursão de BL;
   `65 fF` é a nova triagem para 32 linhas. A leitura nominal em 60 fF
   passou nos dois estados, mas com WL ideal de 10 ns e bitline quase toda
   descarregada; isso não fecha energia ou pulso. A triagem de `Csense` com
   0/100/200 mV passou `12/12` somente em `tt/1,80 V/27 °C`. Ver
   [avaliação de C_BL](cbl_pre_layout_estimate.md).
   Para o ponto `tt/1,80 V/27 °C`, o tempo até 100 mV foi `63,8 ps` após o
   início da subida ideal de WL (`sims/bitcell_read_60ff_tt.csv`). A medida
   inclui borda de 50 ps e carga de 60 fF; não é `t_WL,max` nem timing com o
   driver real.
   Como triagem acelerada, o passo transitório de `50 ps` foi comparado com a
   referência de `10 ps` em `tt/1,80 V/27 °C`: a diferença foi `1,238109 mV`
   em `ΔV(21 ns)`, `0,1115 mV` no pico de read disturb e `1,8 ps` em `t100`.
   Com esse modo, ambos os estados passaram também em `ss/1,62 V/−40 °C`
   (`low_peak=0,1071132 V`, `t100=74,6 ps`) e `ff/1,80 V/125 °C`
   (`low_peak=0,1775878 V`, `t100=59,6 ps`). Esses pontos são screening; a
   qualificação temporal final pós-layout está concluída nas matrizes G7 com
   resolução de referência e netlists PEX rastreados.
   A matriz completa de screening em `60 fF` fechou `60/60` leituras e
   `60/60` escritas com driver transistor-level. Os envelopes limitantes foram
   repetidos em `10 ps`: `ss/1,62 V/125 °C` passou os dois estados com
   `t100=86,9 ps`, e `ff/1,80 V/125 °C` passou os dois estados com pico de
   read disturb `0,1776892 V`. Os CSVs consolidados estão em
   `sims/bitcell_read_60ff_pvt_screen.csv`,
   `sims/bitcell_write_driver_60ff_pvt.csv` e nos dois arquivos
   `*_final_10ps.csv`. Essa evidência fechava G1 para o orçamento antigo, mas
   a inclusão de `Cwrite` elevou o bound a `62,409659 fF`; por isso G1 foi
   reaberto para 65 fF. Esse G1 agora fechou `60/60` leituras e `60/60`
   escritas. No screening de 50 ps, o pior read disturb foi `0,1780729 V`
   (`ff/1,80 V/125 °C`), o t100 mais lento `0,0888 ns`
   (`ss/1,62 V/125 °C`) e o pior full flip de escrita `0,3194 ns`
   (`ss/1,62 V/−40 °C`). Os reruns de 10 ps confirmaram respectivamente
   `0,1781393 V`, `0,0910 ns` e `0,3192 ns`/`WL_min=0,41496 ns`. Esse bound
   pré-layout foi substituído no G7 pela extração completa da coluna:
   `C_BL,PEX,max=453,588405 fF`, teto `521,626665 fF`, com leitura e escrita
   integradas `60/60 PASS` sob carga PEX no teto ou acima dele.
3. **Leitura, escrita e controles integrados — concluído.** A matriz PVT final
   integrou precharge → bitcell → sense e write driver → bitcell com controles
   reais. Leitura e escrita passaram `60/60` cada; CBL foi aplicada no teto
   PEX ou acima dele, a WL recebeu a carga PEX representativa de 8 bits e
   recovery/read-disturb/timing foram medidos. O plano inicial previa repetir
   PVT em 65 fF e integrar esses caminhos; a matriz final com PEX substituiu
   esse screening pré-layout.
4. **Critérios de aceite aplicados na qualificação.**
   O G2 rejeitou `100 mV` como alvo de sense (`480/500` sob mismatch). O piso
   efetivo de mismatch é `150 mV`, com `800/800` decisões combinadas sem falha,
   e o alvo integrado provisório é `200 mV`, reservando `50 mV` de guarda
   pré-layout. Para timing, `0 ps` de setup até `SCLK50` passou `60/60` no PVT,
   mas a guarda interna provisória é `>=25 ps`; o pior tempo de resolução
   observado com mismatch em `150 mV` foi `0,17277 ns`, portanto a janela alta
   de avaliação proposta é `>=0,25 ns` após margem de 30%. Para **schematic
   freeze pré-layout**, o critério estatístico de engenharia passa a exigir
   zero falhas observadas no piso de `150 mV` (`160/160` por corner,
   `800/800` pooled) e, adicionalmente, PASS da matriz integrada real em
   `65 fF` com `ΔV>=200 mV`, setup `>=25 ps` e `t_res<=0,25 ns`. O bound
   unilateral de 95% é ~`0,3738%` pooled e ~`1,8549%` por corner; isso
   documenta a força da triagem e não constitui yield de produção. A guarda de
   `50 mV` não é ruído transitório medido. A requalificação PEX da Fase 1 está
   concluída; uma análise posterior de ruído deverá rever essa alocação se a
   consumir, mas isso não bloqueia o fechamento atual.
5. **Schematic freeze concluído em 05/10/2026.** O sizing canônico é
   `0,42/1,26/0,60 µm`; o timing ativo de leitura usa `SCLK=2,84 ns`. O G4
   fechou como screening de engenharia: read `10/10` no canto crítico
   `ss_mm/1,62 V/-40 °C`, `10/10` em `ff_mm/1,80 V/125 °C`, smoke all-corner
   `10/10` e write crítico `20/20`, sem claim de yield de produção.
6. **G6 físico concluído em 05/10/2026.** `bitcell_6t`, `sense_amp`,
   `precharge`, `wl_driver` e `write_driver` possuem layout roteado, flat com
   Magic DRC `0` e Netgen LVS `Circuits match uniquely`. A bitcell passou ainda
   `layout/bitcell_6t/check_abutment.tcl` em duas condições de gap zero:
   vizinho na mesma orientação e vizinho espelhado horizontalmente, ambas com
   DRC `0`. Os logs LVS ficam em `layout/<leaf>/*_lvs.log`.
7. **G7 pós-layout fechado em 07/10/2026.** A coluna candidata final
   `layout/column_32_full_g7_wpre2p52_final` integra sense 1,5×, precharge
   `Wpre=2,52 µm`, write `Wout=5,04 µm` e WL driver `1,68/5,04 µm`. Magic DRC
   hierárquico/flat: zero; Netgen LVS: match único; PEX RC: `212` MOS, `5.433`
   resistores e `1.944` capacitores. A varredura PVT da coluna passou `120/120`;
   `C_BL,PEX,max=453,588404713 fF` em `ss/1,62 V/125 °C/Q1/BL`, teto
   `521,626665420 fF`. A WL de 8 bits permanece em `98,914001 fF`, com
   `89,925201 fF` adicionais nos benches. `WLOFF=361,100284 fF` continua apenas
   stress diagnóstico.

   A capacitância PEX do precharge W2,52 µm passou `60/60` e varia de
   `10,552943572` a `12,009656935 fF`. A matriz de escrita passou `60/60` com
   PEX explícito, CBL equivalente de `525,653715–527,110428 fF` (acima do teto
   oficial), WL_IN de 1 ns, recuperação máxima `3,49470 ns`, WL mínima calculada
   `0,871819 ns` e margem mínima antes da queda de `0,34274 ns`. A matriz de
   leitura passou `60/60` usando CBL equivalente entre `521,626665` e
   `523,083379 fF`; `t_res,max=0,23209 ns`, setup mínimo `566,03 ps`, diferencial
   mínimo `0,276681 V`, read-disturb máximo `0,1796454 V` e recuperação de
   precharge máxima `1,38210 ns`. Os critérios mantiveram `t_res≤0,25 ns`,
   setup `≥25 ps`, diferencial `≥200 mV`, read-disturb `≤0,20 V` e recuperação
   de escrita `≤4 ns`.

   Evidências: `sims/column_32_full_g7_wpre2p52_final_pex_capacitance_codex_20261007.csv`,
   `sims/precharge_w2p52_pex_capacitance_precharge_only_codex_20261007.csv`,
   `sims/g7_write_wpre2p52_cbl521p626_final_codex_20261007.csv` e
   `sims/g7_read_wpre2p52_cbl521p626665_min_ceff_codex_20261007.csv`. As
   matrizes read/write guardam origem e SHA256 dos PEX em cada linha. Os quatro
   PASS do screening antigo `g7_write_wpre2p52_screen_4case_codex_20261007.csv`
   permanecem não atribuídos por falta de caminhos/hashes e não são evidência
   usada para fechar o gate.
