# Fase 1 — fechamento das leaf cells SKY130A

**Estado em 2026-10-07: schematic freeze e fechamento físico G6 concluídos; matrizes integradas de G7 concluídas, com o gate aberto por recuperação de escrita acima de 4 ns.** O
sizing canônico foi congelado em `WPU/WPD/WACC=0,42/1,26/0,60 µm` após o
fechamento elétrico G1–G4 e uma regressão curta pós-aplicação. As cinco leafs
(`bitcell_6t`, `sense_amp`, `precharge`, `wl_driver`, `write_driver`) têm agora
layout SKY130A, Magic DRC `0` no flat e Netgen LVS com `Circuits match uniquely`.
A bitcell também passou smoke de abutment em gap zero, tanto na orientação
normal quanto com o vizinho espelhado horizontalmente, ambos com DRC `0`.
A entrega física G6 da Fase 1 está concluída. No G7, a coluna física 32× reforçada
integra sense 1,5×, precharge `W=2,10 µm` e write driver `Wout=5,04 µm`; layout
hierárquico e flat têm Magic DRC `0`, LVS estrutural único e PEX RC. A extração
PVT mede `C_BL,PEX,max=452,580954 fF` (`120/120 PASS`), com teto de
requalificação `520,468097 fF`. A linha de WL física de 8 bits também fecha
DRC/LVS/PEX e mede `98,914001 fF`, dos quais `89,925201 fF` são carga extra
aplicada aos benches integrados.

A requalificação PVT integrada de leitura concluiu `60/60 PASS`. A matriz de
escrita também concluiu: `56/60 PASS` e quatro falhas em `sf/ss`, 1,62 V/−40 °C,
nos dois sentidos, por recuperação de BL/BLB abaixo de `VDD−0,1 V` ao final da
janela de 4 ns. A repetição focal de 30 ns passou `4/4` e mediu cruzamento em
`4,031–4,186 ns`, confirmando recuperação tardia. A Fase 1 segue aberta até
trazer o cruzamento para dentro do contrato vigente e requalificar esses casos.
Os resultados de mismatch continuam sendo triagem de engenharia, sem claim de
yield de produção.

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

## Estado por célula

| Leaf | Esquemático, evidência elétrica e fechamento físico | Estado atual no G7 |
|---|---|---|
| Bitcell 6T | `cells/bitcell_6t.sch` e `cells/bitcell_6t.sym` usam o sizing canônico `0,42/1,26/0,60 µm`. G1–G4 fecharam para screening pré-layout; Read SNM nominal `0,414349 V` e read-disturb crítico `0,1781393 V`. `layout/bitcell_6t` fecha com DRC `0`, LVS único e abutment normal/espelhado em gap zero com DRC `0`. | Incluída nas matrizes G7 com a carga PEX e WL física. Leitura passou; a escrita comuta, mas quatro casos excedem o limite de recuperação de 4 ns. |
| Sense amplifier | `cells/sense_amp.sch` contém latch regenerativo de sete transistores com amostragem PMOS; o netlist do próprio Xschem passou 330/330 casos determinísticos. No G2, `150 mV` acumula `800/800` decisões sem falha; G4 promoveu `SCLK=2,84 ns`. `layout/sense_amp` fecha com DRC `0` e LVS único, 7 dispositivos/8 nets. A variante física `1,5×` passa DRC/LVS/PEX e o ponto `ss/1,62 V/125 °C` no teto, com `t_res=0,22060/0,23257 ns`; a matriz integrada de leitura passou `60/60`. | Qualificação de leitura pós-layout concluída; não há falha de sense aberta no G7 atual. |
| Precharge/equalização | `cells/precharge.sch` gera netlist conectado; Ceff máximo pré-layout `0,908533 fF` por bitline. `layout/precharge` fecha com DRC `0` e LVS único, 3 PMOS; o tap físico de substrato para `VSS` removeu `VSUBS` flutuante do netlist RC. A variante `Wpre=2,10 µm` tem PEX e foi integrada à coluna G7. | A recuperação da escrita continua acima de 4 ns em quatro casos PVT; reforçar e revalidar a topologia física de precharge. |
| WL driver | `cells/wl_driver.sch` gera dois inversores conectados; sizing `0,42/0,84 µm`. O smoke selecionado passou em `tt/1,8 V/27 °C` e `ss/1,62 V/−40 °C`. `layout/wl_driver` fecha com DRC `0` e LVS único, 4 dispositivos/5 nets. A variante integrada reforçada tem PEX; linha física de 8 bits: `98,914001 fF`, com `89,925201 fF` extras no bench. Leitura e escrita pós-layout foram simuladas com essa carga. | Resolver as quatro falhas de recuperação na escrita; manter os resultados de slew, timing, largura efetiva e read-disturb associados às matrizes integradas. |
| Write driver | Com bitcell `WPD=1,26 µm` e 65 fF, a integração passou `60/60`; G4 mismatch passou os corners selecionados. `layout/write_driver` fecha com DRC `0` e LVS único, 10 dispositivos/12 nets, preservando `WE_B` e os quatro nós internos dos stacks. A variante física reforçada tem PEX e foi usada na matriz pós-layout. | Corrigir a recuperação de BL/BLB acima de 4 ns nos quatro casos críticos e repetir a qualificação afetada. |

## Gates para concluir

1. **Congelar contrato elétrico e sizing.** Escolher o sizing da bitcell
   frente ao alvo de SNM e write margin; definir pinos, polaridades e sizing
   das quatro células periféricas. Guardar netlists extraídos do Xschem e
   conferir dispositivos/nós sem conexões abertas.
2. **Fechar `C_BL` pré-layout.** O orçamento de fio `metal2`, `0,14 µm`, até
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
   qualificação temporal final continua usando a resolução de referência.
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
   `0,1781393 V`, `0,0910 ns` e `0,3192 ns`/`WL_min=0,41496 ns`.
3. **Fechar leitura, escrita e controles integrados.** Repetir PVT em pelo
   menos 65 fF, depois ligar precharge → bitcell → sense e
   write driver → bitcell com controles reais. Medir `t100`/`tΔV_target`,
   `t_WL,max`, mínimo de escrita, SCLK setup, hold/disturb, potência e
   recuperação para os dois dados. Separar pulso de leitura do de escrita se
   o pulso único descarregar a coluna além do limite de energia/excursão.
4. **Aplicar os critérios de aceite antes de rotular PASS de qualificação.**
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
   `50 mV` deve ser reaberta após PEX ou se ruído transitório explícito consumir
   essa alocação.
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
7. **G7 aberto por recuperação de escrita: PEX físico e matrizes integradas concluídos.** Os
   máximos de leaf PEX e o surrogate anterior permanecem como histórico. A
   coluna reforçada `layout/column_32_full_g7` passou DRC hierárquico/flat, LVS
   único e PEX; `sims/column_32_full_g7_pex_capacitance_pvt.csv` passou
   `120/120`, com `C_BL,PEX,max=452,580954 fF` e teto `520,468097 fF`. A WL
   representativa de 8 bits mede `C_WL,PEX,max=98,914001 fF`; o bench usa
   `89,925201 fF` extras. A extração WLOFF de `361,100284 fF` continua sendo
   apenas stress diagnóstico de 32 WLs curto-circuitadas.

   Sense 1,5×, precharge `W=2,10 µm`, write `Wout=5,04 µm` e WL driver
   `1,68/5,04 µm` têm layout candidato com DRC/LVS/PEX. No ponto crítico
   `ss/1,62 V/125 °C`, o sense passa ambos estados (`t_res=0,22060/0,23257 ns`)
   e a escrita passa ambos os sentidos (pior full-flip `0,63440 ns`, margem de
   WL mínima `0,39812 ns`). A matriz PVT integrada concluiu: read `60/60 PASS`;
   write `56/60 PASS`, `4/60 FAIL`. As falhas estão em `sf/ss`, 1,62 V/−40 °C,
   uma por estado em cada corner; o bit flip completa, mas BL/BLB não atingem
   `VDD−0,1 V` até o fim da janela configurada de 4 ns. A repetição de 30 ns
   passou os quatro casos e mediu `4,031–4,186 ns`. O diagnóstico focal de 5 ns
   também concluiu `4/4` e mediu cruzamentos de `4,03137`, `4,07829`, `4,13750`
   e `4,18573 ns`; esses resultados não alteram o limite de 4 ns. Não fechar G7
   até tratar e requalificar os casos, recalcular os piores resultados e
   registrar a decisão final.
