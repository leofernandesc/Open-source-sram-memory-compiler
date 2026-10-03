# Fase 1 — fechamento das leaf cells SKY130A

**Estado em 2026-10-03: aberto.** A entrega pedida é a biblioteca de leaf
cells com esquemático, layout e DRC/LVS limpos. Os testes elétricos abaixo são
evidência de triagem pré-layout; nenhum arquivo `.mag` da biblioteca foi
encontrado neste checkout. Não declarar Fase 1 concluída nem schematic freeze
com base apenas em netlist ou contagem de simulações PASS.

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

`100 mV` de diferencial, `+20%` no fio, `+15%` sobre PEX, `+30%` no tempo
de escrita, alvo nominal de Read SNM `>=0,4 V` e limites de read disturb são
**propostas/critério interno**. `1,62–1,80 V` é a faixa de qualificação
escolhida para o modelo atual; `1,95 V` é ponto de auditoria estática e
`1,98 V` não está qualificado. A validade dos modelos nas temperaturas
extremas continua sujeita à confirmação do PDK.

## Estado por célula

| Leaf | Esquemático e evidência elétrica | O que falta para aceite da leaf |
|---|---|---|
| Bitcell 6T | `cells/bitcell_6t.sch` e símbolo existem; retenção, leitura, escrita, SNM, leakage e mismatch foram explorados. Sizing canônico `0,42/0,84/0,60 µm` falha alvo interno de Read SNM nominal (`0,348804 V < 0,4 V`). `0,42/1,26/0,60 µm` foi selecionado para closure (`0,414349 V` nominal), mas ainda não foi congelado nem aplicado à captura. | Completar a matriz PVT em 60 fF, fechar limites estatísticos/de potência e só então decidir a aplicação/freeze do sizing e o layout da bitcell. |
| Sense amplifier | `cells/sense_amp.sch` agora contém latch regenerativo de sete transistores com amostragem PMOS; o netlist do próprio Xschem passou 330/330 casos determinísticos em fontes BL/BLB ideais. Entrada AC: `60/60`, `7,853676–9,004605 fF` em `SCLK=0`, BL/BLB em VDD. | Offset com mismatch/ruído por corner, setup e janela SCLK; acoplar à coluna real, medir `ΔV_min` e energia; layout/DRC/LVS. `5 mV` de estímulo ideal passando não é sensibilidade garantida. |
| Precharge/equalização | `cells/precharge.sch` gera netlist conectado; Ceff máximo `0,908533 fF` por bitline. Com `60 fF`, chegou a `>=0,95 VDD` e equalizou em `tt/1,8 V/27 °C` e `ss/1,62 V/−40 °C` no estímulo de 4 ns. | Sweep completo, menor tempo de pré-carga, sequenciamento PRECH/WL/SCLK, potência e layout/DRC/LVS. |
| WL driver | `cells/wl_driver.sch` gera dois inversores conectados; sizing `0,42/0,84 µm` provisório. Com 50 fF, o smoke selecionado passou em `tt/1,8 V/27 °C` (atraso 50% `0,415 ns`) e `ss/1,62 V/−40 °C` (`0,665 ns`). | Sweep PVT, carga física real de WL, slew no extremo da linha, read disturb e layout/DRC/LVS. |
| Write driver | Com bitcell `WPD=1,26 µm` e 60 fF, passou `2/2` em `tt/1,62 V/27 °C` (full flip `0,288 ns`), `2/2` em `ss/1,62 V/−40 °C` (`0,321 ns`, +30%=`0,417 ns`) e `2/2` em `ff/1,80 V/125 °C` (`0,246 ns`, +30%=`0,319 ns`). | Completar a matriz PVT em 60 fF, mismatch, margem/timing e layout/DRC/LVS. |

## Gates para concluir

1. **Congelar contrato elétrico e sizing.** Escolher o sizing da bitcell
   frente ao alvo de SNM e write margin; definir pinos, polaridades e sizing
   das quatro células periféricas. Guardar netlists extraídos do Xschem e
   conferir dispositivos/nós sem conexões abertas.
2. **Fechar `C_BL` pré-layout.** O orçamento de fio `metal2`, `0,14 µm`, até
   `5 µm/linha`, dois vizinhos e margem interna de 20% produz
   `Cwire<=1,061862 fF/linha`. Com `Ccell=0,452619 fF`,
   `Cprecharge=0,908533 fF`, `Csense=9,004605 fF` e `Cmux=0`, os máximos
   calculados são `15,971062/22,028986/34,144834/58,376530 fF` para
   `4/8/16/32` linhas. Verificar `Csense` também durante a excursão de BL;
   `60 fF` é somente triagem para 32 linhas. A leitura nominal em 60 fF
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
3. **Fechar leitura, escrita e controles integrados.** Repetir PVT em pelo
   menos 60 fF, depois ligar precharge → bitcell → sense e
   write driver → bitcell com controles reais. Medir `t100`/`tΔV_target`,
   `t_WL,max`, mínimo de escrita, SCLK setup, hold/disturb, potência e
   recuperação para os dois dados. Separar pulso de leitura do de escrita se
   o pulso único descarregar a coluna além do limite de energia/excursão.
4. **Definir critérios de aceite antes de rotular PASS de qualificação.**
   Acordar `ΔV_target` a partir de offset/ruído/yield; orçamentos de
   leakage/potência e yield de mismatch, inclusive escrita e disturb. A
   expressão `max(100 mV, 4σ_offset + ruído)` é proposta, não especificação
   aprovada. Documentar domínio de temperatura do PDK.
5. **Revisar arquitetura e declarar schematic freeze** somente após os
   gates acima, registrando revisão de esquema, modelo, corners e resultados.
6. **Desenhar cada layout no Magic** (`bitcell_6t`, `sense_amp`,
   `precharge`, `wl_driver`, `write_driver`); verificar espelhamento/abutment
   da bitcell, pinos, alimentação e regras de geometria. Executar DRC Magic
   sem violações e LVS Netgen entre extração e netlist Xschem sem diferenças
   não justificadas para **cada** leaf. Guardar logs, relatórios, versão do
   PDK e views. Só então a entrega física da Fase 1 está completa.

O PEX vem depois do schematic freeze e do layout. Sua carga extraída substitui
o orçamento pré-layout; requalificar com o teto interno de
`1,15 × C_BL,PEX`. Se houver divergência elétrica ou física, reabrir o gate
afetado em vez de manter o status de fechado.
