# Fase 3 — reconstrução do ECO 4×8 e investigação em SS

Execução iniciada em 18/11/2026 no fuso de Manaus e continuada em 19/11.
Branch local `integration/phase3-danilo-ss` a partir de `8e1d961`.

## Identidade das revisões

O ponto de partida é a topologia do protótipo descrita em
[`42f0b51`](https://github.com/leofernandesc/Open-source-sram-memory-compiler/commit/42f0b5128d7e5dde4385731e85fa504a6ee005a7):
tap 48 em `evaluation.C`, inversores dos oito registradores de saída ligados
ao CLK público e oito drivers `ebufn_8`. Mantivemos a distribuição de clock
dos demais domínios. A reconstrução usa os Verilog, GDS e LEF selados do
`route_v1`/`layout_v1` como insumos e refaz o roteamento do ECO. A bitcell e
os periféricos analógicos continuam vindos da mesma matriz com abutment.

O Git da frente Danilo fornece scripts e o relatório. O ODB/DEF, o
GDS de hash `b69f657d…`, o recibo `layout_verification.json`, o PEX integral
`f5503371…`, a restauração subatto e os decks/manifestos/waveforms dos três
corners descritos em `build/phase3/read_path_20261117/` não estavam no checkout
nem nos arquivos locais encontrados. O novo roteamento tem identidade própria.
Danilo registrou TT 72/72, SS com 31 falhas em 72 bits e FF 72/72 no
transiente integral de 370 ns. As falhas SS do relatório ocorreram nos
ciclos 6, 7, 11, 13, 14, 15 e 16. Nesta rodada só os ciclos de leitura 6 e
7 entraram no diagnóstico curto. A aprovação dos outros cinco ciclos
permanece sem observação local no mesmo transiente.

O GDS reconstruído é `a593676029af53d37fd9e40a1a2a5b1ef283c463428e940a168302c88064539e`.
O Magic 8.3.703 deu DRC=0 tanto na geometria integrada quanto na reimportação
em processo novo. O Netgen obteve LVS único na comparação com a referência
do Verilog reconstruído. A reimportação encontrou 1.733 MOS e 16 portas.
A matriz reutilizada tem `leaf_fabric.gds` e `leaf_fabric.lef` com os mesmos
hashes no `route_v1` e no `layout_v1`, incluindo a normalização de origem.

O projeto continua SRAM 6T single-port. Os oito FF de saída recebem a subida
do clock invertido, correspondente à descida de CLK. Os registros de entrada
mantêm seu domínio original. O diff do ECO preserva os 80 estágios de atraso.

## Reprodução

Executar no ambiente EDA existente com ngspice 44.2 e Magic compilado no
commit [`2c6d97b`](https://github.com/RTimothyEdwards/magic/commit/2c6d97b2f21003fa1778d5658eb02b32724399ab).
O techfile usado tem SHA-256
`3129815ae08ff4e4459d93dcea18121a311638a85110d884500351e406edd3d0`.
Usar diretórios novos para preservar todas as tentativas.

```bash
# Em um diretório novo sob build/phase3, buscar o commit fixo e compilar no EDA.
git init build/phase3/magic703_source_novo
git -C build/phase3/magic703_source_novo fetch --depth=1 \
  https://github.com/RTimothyEdwards/magic.git 2c6d97b2f21003fa1778d5658eb02b32724399ab
git -C build/phase3/magic703_source_novo checkout --detach FETCH_HEAD
tools/sram-eda sh -ec '
  cd build/phase3/magic703_source_novo
  CFLAGS=-O2 ./configure --prefix=/work/build/phase3/magic703_novo \
    --with-tcl=/usr/lib/x86_64-linux-gnu --with-tk=/usr/lib/x86_64-linux-gnu
  make -j2
  make install
'
tools/sram-eda python3 tools/rebuild_phase3_danilo_eco.py \
  --output build/phase3/eco_route_novo
tools/sram-eda sh -ec '
  export PATH=/work/build/phase3/magic703_novo/bin:$PATH
  python3 tools/finish_phase2_layout.py --route-report build/phase3/eco_route_novo \
    --output reports/phase2/local/eco_layout_novo
  python3 tools/verify_phase2_gds.py --layout-report reports/phase2/local/eco_layout_novo \
    --output reports/phase2/local/eco_gds_novo
'
tools/sram-eda python3 tools/run_phase3_eco_pex.py extract \
  --geometry reports/phase2/local/eco_gds_novo --output build/phase3/eco_pex_novo \
  --magic /work/build/phase3/magic703_novo/bin/magic
tools/sram-eda python3 tools/run_phase3_eco_pex.py restore-subatto \
  --source build/phase3/eco_pex_novo --output build/phase3/eco_pex_selado_novo
tools/sram-eda python3 tools/run_phase3_eco_pex.py simulate \
  --source build/phase3/eco_pex_selado_novo --output build/phase3/eco_ss_novo \
  --corner ss --cycles 8
```

O ensaio de oito ciclos inclui as quatro escritas iniciais e as duas
primeiras leituras. Para os 18 ciclos, omitir `--cycles`. O código de retorno
diagnóstico é 1 e significados separados são gravados no manifesto. A operação
usa 1,8 V, 27 °C, 10 fF por DATA, 20 ns de período, slew de 50 ps e passo máximo
de 25 ps. O teste de nova palavra usa a janela do benchmark em torno do ponto
existente. O analisador também registra as causas observáveis por bit.

A reconstrução gerou **1.733 MOS, 16.023 R e 12.393 C**, mesmas contagens
reportadas pelo Danilo. A restauração em cópia separada usa os valores
positivos de `rnode` menores que 1 aF para os cartões de substrato a VSS
que o Magic imprimiu como zero. Alterou 123 cartões, somando 0,0609159321 fF.
Os 5.169 pares auditados concordam com C-only nas tolerâncias existentes.
O PEX recuperado tem SHA-256
`84cecaa3e29fc8940a3cd2673b0547ed7365a658b2ba3c7b3d7b6cd2bcbf858e`.
O gate estrutural exige caminho DC de ambos os trilhos e ausência de curto.
No RC integral, BL/BLB e SCLK podem ser sondados nos subnós dos MOS de
amostragem do sense. Alvos nominais sem nome preservado usam um subnó
representativo da rede extraída, selecionado pela coordenada no `.ext`.
A primeira tentativa com cobertura insuficiente foi interrompida antes
de produzir um resultado elétrico.

## Correção no analisador

`tCLK_TO_DATA` continua por bit, da descida pública em CLK50 até a transição
DATA50 atribuível à leitura. `tACCESS` agora usa a subida pública em CLK50
até o instante em que **todos os oito bits** entram nas faixas 20/80 e
permanecem válidos até o fim da janela obrigatória. Não existe atraso zero
fabricado para bits estáveis. A palavra sem transição atribuível ou com leitura
inválida permanece `NOT_CHARACTERIZED`. As definições e as 14 colunas
continuam registradas no CSV. Esse cálculo é diagnóstico no domínio ensaiado.

## Evidências reaproveitáveis das outras frentes

- O sense de sete MOS e a pré-carga da matriz mantêm a mesma identidade da
  Fase 2. A ressalva do sense PEX a 5 mV continua relevante caso o diferencial
  observado no instante local do sense seja pequeno. Os resultados de
  `docs/sense_pex_small_signal_investigation.md` informam essa investigação.
- As séries históricas `sims/bitcell_read_snm_mismatch_sf_1p62_125.csv` e
  `sims/bitcell_hold_snm_mismatch_sf_1p62_minus40.csv` têm 200 seeds cada e
  documentam triagem pré-layout da 6T nas condições registradas. Podem ser
  citadas nesse escopo com a identidade da célula conferida. A margem de
  leitura integrada depende de WL, BL/BLB, pré-carga e tempo de sense na
  revisão final. Uma troca da bitcell exigiria rever a série histórica.

## Verificações de software

`tools/run_phase3_regressions.py` completou 165 casos. A suíte RC completou
32 casos, incluindo validade da palavra inteira, a identidade da topologia
reconstruída e a separação entre falha em sense, captura e DATA.

## Controle SS e escolha da primeira correção

Na exportação **C-only** do GDS reconstruído, o ngspice 44.2 completou
170 ns com 9.533 amostras. Verificou-se a leitura após as quatro escritas
iniciais. O resultado original foi **10/16 bits corretos** na janela
de bancada, com falhas em c6/DATA[1,7] e c7/DATA[0,2,4,6].
Todos os dezesseis bits tiveram D correto na captura e Q correto no
ponto externo. Nos seis bits reprovados, TE_B estava ativo e o
diferencial BL–BLB assinado antes de SCLK estava entre 0,432 V e
0,604 V na sonda selecionada. A wordline chegou a 80% antes de
SCLK20 por 0,374–0,462 ns nos dois ciclos.

As seis falhas foram de subida de DATA. No início da janela (140,9 ns ou
160,9 ns), o pino ainda estava abaixo de 1,44 V. A transição até 20/80
ocorreu entre **0,875 e 0,974 ns** depois da descida pública entre esses
bits. Por exemplo, no c7 DATA6 chega a 1,44 V por volta de 160,999 ns.
Para as oito subidas, Q cruzou 50% **0,543–0,574 ns** após a descida de CLK.
O clock local cruzou 50% cerca de **0,043–0,048 ns** depois da descida pública.
O atraso está no caminho da captura ao pino, com parcela importante no
FF→Q. A conclusão se limita aos dois ciclos do controle capacitivo.
O gráfico `build/phase3/ss_c_only_cycle7_bit6.png` usa as amostras
da execução e mostra onde a subida de DATA cruza 1,44 V na janela original.

A alteração experimental isolada substitui os oito `dfxtp_1` de saída
por `dfxtp_2` através de `--output-ff dfxtp_2` no reconstrutor. O sentido da
captura, a rede de clock público, o tap 48 e os oito `ebufn_8` são preservados.
A hipótese é adiantar a chegada de Q ao driver de saída. A carga de clock e
de D pode mudar, então o ganho precisa ser medido em netlists de geometrias
verificadas, com o mesmo benchmark. A primeira medida da diferença usa
C-only e precede eventual promoção da variante a candidato.

A variante foi roteada e verificada fisicamente. A reimportação independente
deu DRC=0 e LVS único para **1.749 MOS**, mantendo as 16 portas. O aumento é
de 16 MOS na macro e o floorplan permanece 540 × 380 µm. Esse resultado
físico refere-se somente a esta variante e ao seu netlist de referência.
O LEF da biblioteca indica 7,36 × 2,72 µm por `dfxtp_1` e
7,82 × 2,72 µm por `dfxtp_2`. A soma das áreas dos oito FF aumenta
10,01 µm². O GDS da variante tem SHA-256
`9ef1cfba59b056beb80a549339258c43b95c8732dbe99b99ff22968544ef0f5d`.
O PEX integral da mesma geometria tem 16.114 R e 12.437 C.
A restauração documentou 119 cartões, 0,0614285818 fF e
**5.144/5.144** pares aprovados na auditoria. Seus trilhos chegam aos
MOS e não há curto resistivo. O netlist restaurado é
`7015819b05efaf1ff24ae70b6fcd5bd049ee451e9fe6871ddb5a4a469bdd12e7`.

### Comparação elétrica isolada em TT, SS e FF

`tools/phase3_rc_output_slice.py` compara o inversor de captura, o FF e
o `ebufn_8` reais do PDK. Na comparação abaixo, Q recebeu carga capacitiva
explícita de 6 fF e DATA de 45 fF. O driver permaneceu habilitado. D foi
estabilizado antes da descida pública. Todos os valores vêm de `.meas`
do ngspice 44.2 a 1,8 V / 27 °C.

| Corner | CLK↓50→DATA80, _1 | _2 | _4 | CLK↓50→DATA20, _1 / _2 / _4 |
|---|---:|---:|---:|---:|
| TT | 509,48 ps | 474,69 ps | 472,32 ps | 382,94 / 378,57 / 401,48 ps |
| SS | 767,58 ps | 711,16 ps | 704,53 ps | 563,01 / 560,44 / 598,89 ps |
| FF | 366,92 ps | 343,52 ps | 343,48 ps | 283,31 / 278,83 / 292,72 ps |

A carga leve (5 fF em Q e 24 fF em DATA) e os cruzamentos de Q50
estão nos manifestos `output_slice_{tt,ss,ff}`. Na carga maior, o _2
reduziu a subida em 34,79 ps em TT, 56,42 ps em SS e 23,40 ps em FF.
O _4 adiciona apenas 6,63 ps de ganho em SS na subida e atrasa a descida
38,46 ps frente ao _2. Isso sustenta manter o _2 como primeira tentativa.
A bancada isolada usa cargas concentradas e exclui matriz, RC de alimentação,
mux de retenção, escrita e arbitragem do barramento. Esses dados apoiam
a seleção da variante, sem constituir tempos de acesso da macro.

## Localização das falhas com RC integral

A referência reconstruída completou o transiente SS de 170 ns com 9.354
amostras. Com a janela [S−100 ps, S+100 ps] do benchmark, houve **6/16**
bits corretos. O simulador completou com sucesso e a CLI retornou 1.

| Ciclo | Endereço | Palavra esperada | Bits que falharam | Transições |
|---|---:|---|---|---|
| 6 | 0 | AA | 1, 3, 5, 7 | Subida |
| 7 | 1 | 55 | 0, 2, 4, 6 e 1, 7 | Subida e descida, respectivamente |

Nas dez falhas, D estava correto na captura, Q estava correto na observação
e TE_B já estava baixo. A diferença de BL/BLB na polaridade esperada
ficou entre 0,236 e 0,487 V, 50 ps antes de SCLK20 local. Os registros
failure_stages.csv e read_path.csv contêm WL, SCLK, o diferencial, sense,
D/Q e os níveis em DATA. Assim, os dois ciclos observados falharam depois
da captura. No ciclo 7, DATA6 mediu 0,508 V em 160,9 ns, 0,952 V em
161 ns e 1,366 V em 161,1 ns. O primeiro cruzamento estável de 1,44 V
ocorreu em 161,1257 ns, 1,1007 ns depois de CLK↓50. O limite inferior da
janela estava em 160,9 ns. Na geometria C-only da mesma referência o
cruzamento ocorreu em 160,9986 ns. As contribuições capacitivas e
resistivas da saída justificam testar alterações nesse caminho primeiro.

O controle C-only com dfxtp_2 completou 170 ns e 9.469 amostras.
Aprovou **14/16** bits, ante **10/16** na referência. Restaram as subidas
dos bits 4 e 6 do ciclo 7. D e Q estavam corretos em ambos. Os cruzamentos
de 1,44 V ocorreram 0,8813 e 0,9345 ns após CLK↓50, respectivamente.
DATA6 ganhou cerca de 39 ps ante o controle C-only da referência e ainda
entrou na faixa válida cerca de 60 ps depois do início da janela.

Uma segunda bancada SS isolada acrescentou um ebufn_8 em paralelo.
Com dfxtp_2 e as mesmas cargas concentradas de 6/45 fF, a subida de
DATA passou de 711,16 para 636,45 ps e a descida de 560,44 para 538,60 ps.
O ensaio adiciona carga ao FF e exclui a distribuição de TE_B.
Como o maior atraso medido na macro supera a janela em cerca de 226 ps,
o ganho isolado é insuficiente para validar o paralelismo como solução.

## Independência entre captura de escrita e handoff

A reanálise recheck-protocol confere os hashes antes de gerar um recibo
separado. Os arquivos originais e suas contagens continuam disponíveis.
A antiga observação Q em CLK↑ + 1 ns continua registrada e falha em 24
dos 32 checks. No PEX da referência, os oito bits de DIN de cada escrita
entram nas faixas válidas entre 2,006 e 2,431 ns antes de WE20 e
permanecem válidos ao longo da janela medida. Todos os 32 checks relativos
à abertura de WE passam. A medição abrange a prontidão interna de DIN.
Setup/hold público permanece NOT_CHARACTERIZED.

Na troca do ciclo 7 para a escrita do ciclo 8, há sobreposição em todos
os oito bits. Os controles externos saem de leitura a partir de 167,0 ns,
o host começa a habilitar em 167,30 ns e as formas de onda ainda mostram
HOST_EN > 0,36 V junto de TE_B < 1,44 V entre aproximadamente
167,3175 e 167,5790 ns na referência RC. O pico absoluto observado no
ramo do host em DATA6 é de 10,91 mA, que pode incluir carga ou descarga
capacitiva. Posteriormente, os checks de corrente de escrita em regime
estável passam. Os controles WEb, CSb e OEb entram na nor3b_1 que
alimenta a rede live_read. As NANDs locais geram TE_B. O caminho de
desligamento precisa ser verificado separadamente da latência após
captura. Esse fail segue bloqueando o resultado funcional.

A guarda de 0,30 ns pertence à fixture. O resultado prova sobreposição
no estímulo ensaiado. O orçamento público de disable/turnaround da
macro segue pendente de qualificação. A especificação técnica exige que
o host espere o desligamento da saída antes de dirigir DATA e que respeite
setup/hold. O prazo de 0,30 ns da fixture serve para comparar as revisões
no ensaio e não constitui um limite público.

## Encurtamento físico dos caminhos DATA

A topologia ff2 tinha redes DATA assimétricas. Na rede DATA6, 116,38 µm
eram um único segmento horizontal em met1. Um agrupamento inicial de
pinos à direita aliviou DATA4–7, mas aumentou o comprimento de DATA0
de 82,81 para 189,79 µm. A segunda variante mantém cada pino DATA
na borda inferior perto do par driver/mux correspondente. O Verilog
roteado e a área da macro permanecem idênticos aos da variante ff2.

| Roteamento | Soma dos segmentos DATA[7:0] | DATA6 | Maior rede DATA |
|---|---:|---:|---:|
| Posicionamento automático | 1.040,52 µm | 187,23 µm | 195,81 µm |
| Pinos agrupados | 884,72 µm | 65,81 µm | 189,79 µm |
| Pinos distribuídos | 552,70 µm | 61,47 µm | 89,37 µm |
| Pinos distribuídos com DATA1 afastado | 549,60 µm | 61,93 µm | 86,83 µm |

Os comprimentos vêm dos segmentos em met1/met2 dos DEFs, sem vias.
O CSV data_wiring_comparison.csv identifica cada DEF pelo SHA-256.
O perfil físico pode ser reconstruído com o comando de roteamento acima
acrescentando `--output-ff dfxtp_2 --data-pin-placement distributed`.
A posição dos pinos físicos mudou. Essa variante exige seu próprio LEF
em qualquer integração com uma macro vizinha.

O GDS de pinos distribuídos tem SHA-256
`d603a286ef5212c17b8e8a453766454cc1b53eeb34b82857c1f2ba8e60222033`.
A reimportação obteve DRC=0 e LVS único, 1.749 MOS e 16 portas.
O topo LEF veio desse mesmo GDS. As 47 caixas de pinos foram
conferidas contra metal real e o OpenROAD leu o LEF. Seu SHA-256 é
`2a7cbdccc7641be0cc0ba9dab7394ce8c2e3e78750f467bfaa72e3e2fa431683`.
O exportador aceita o modo explícito `--verified-geometry`, com
hash conferido e destino local novo. A opção histórica sem esse argumento
continua usando a fonte original. Para reproduzir o LEF deste ECO:

```bash
tools/sram-eda sh -ec '
  export PATH=/work/build/phase3/magic703_novo/bin:$PATH
  python3 tools/export_phase2_top_lef.py \
    --verified-geometry reports/phase2/local/eco_gds_novo \
    --output reports/phase2/local/eco_lef_novo
'
```

No C-only da variante ff2 automática, os cartões incidentes em DATA6
somam 28,00 fF. Com pinos distribuídos, somam 10,28 fF. O mesmo
levantamento obteve 29,43 → 11,74 fF em DATA4 e 36,02 → 15,44 fF em
DATA7. São somas de parasitas incidentes, incluindo acoplamento. A carga
externa do benchmark permanece 10 fF por bit nas duas geometrias.

## Comparação de desligamento isolado em SS

O circuito isolado usa as células reais e a transição simultânea de
OEb e WEb do handoff. A rede live_read tem oito NANDs e carga
concentrada de 35,60701 fF. Cada TE_B inclui a entrada de um ebufn_8 e
3,79 fF concentrados. O tempo desde OEb↑50 até TE_B↑80 foi de 548,9 ps
com nor3b_1, 487,7 ps com nor3b_2 e 410,7 ps com nor3b_4, usando
nand2_1. O pulso de referência do host cruza 20% em 285 ps após
OEb↑50 pelas rampas programadas. Mesmo com o estágio de controle
comum reforçado, TE_B80 chega depois desse evento. O ensaio concentra cargas e serve
para selecionar as próximas alternativas de desligamento.

Mantendo as mesmas cargas e trocando a NAND local para nand2_4, os
tempos OEb↑50→TE_B↑80 foram 500,6 ps, 390,6 ps e 279,3 ps com as três
versões da NOR. A última ficou apenas 5,7 ps antes do marco nominal do
host no modelo concentrado. A troca também aumenta a carga sobre
live_read. Essa margem é insuficiente para promover células maiores
sem medir o RC de disable e os efeitos sobre a reabilitação e as sondas
de máscara. As geometrias verificadas desta rodada preservam essa lógica.

Uma forma equivalente é calcular em cada driver
`TE_B = OEb | CSb | !WEb | !READ_Q`. O ensaio isolado mede cada
controle separadamente, mantendo READ_Q ativo e usando a mesma carga
em TE_B. Com OR4_4 e inversão de WEb compartilhada, OEb e CSb chegaram
a TE_B80 em 175,6 e 173,4 ps, mas WEb levou 455,7 ps. Com OR4BB_4
nativa, os tempos foram 176,0 ps para OEb, 174,1 ps para CSb e
285,0 ps para WEb. WEb consumiu praticamente todo o intervalo de
285 ps da fixture no modelo sem rotas. Os resultados sustentam
investigar o caminho de WEb e desaconselham promover qualquer uma
dessas células por conta da resposta mais rápida a OEb e CSb.

## Comparação antes/depois no benchmark de 170 ns

As contagens usam todos os oito bits nas leituras dos ciclos 6 e 7,
na janela original. A fixação do instante inicial e final da janela
permaneceu idêntica entre experimentos. O estado de leitura, a
propriedade do barramento e a qualificação são expostos separadamente.

| Revisão | Modelo | Corner | Leituras corretas | Execução elétrica |
|---|---|---|---:|---|
| ECO reconstruído | RC integral | SS | 6/16 | 9.354 amostras, simulador PASS |
| ECO reconstruído | RC integral | TT | 16/16 | 10.262 amostras, simulador PASS |
| ECO reconstruído | RC integral | FF | 16/16 | 10.448 amostras, simulador PASS |
| ECO reconstruído | C-only | SS | 10/16 | 9.533 amostras, simulador PASS |
| ECO com dfxtp_2 | RC integral | SS | 7/16 | 9.280 amostras, simulador PASS |
| ECO com dfxtp_2 | C-only | SS | 14/16 | 9.469 amostras, simulador PASS |
| ECO com dfxtp_2 | C-only | TT | 16/16 | 10.390 amostras, simulador PASS |
| ECO com dfxtp_2 | C-only | FF | 16/16 | 10.584 amostras, simulador PASS |
| ECO com dfxtp_2 e pinos distribuídos | C-only | SS | 16/16 | 9.575 amostras, simulador PASS |
| ECO com dfxtp_2 e pinos distribuídos | RC integral | SS | 12/16 | 9.412 amostras, simulador PASS |
| ECO com dfxtp_2, pinos distribuídos e DATA1 afastado | C-only | SS | 16/16 | 9.578 amostras, simulador PASS |
| ECO com dfxtp_2, pinos distribuídos e DATA1 afastado | RC integral | SS | 14/16 | 9.392 amostras, simulador PASS |

O dfxtp_2 no RC integral eliminou a falha de descida de DATA1 no
ciclo 7. Nos nove casos restantes D e Q preservaram os valores
corretos e o atraso apareceu entre Q e o pino. O cruzamento de 1,44 V
em DATA6 no ciclo 7 adiantou de 161,1257 ns para 161,0864 ns.
A nova transição ainda cruza 186 ps após o início da janela.
O PEX TT C-only dessa variante forneceu tACCESS experimental da
palavra de 10,5737 ns e 10,6188 ns nos ciclos 6 e 7. Houve sobreposição
nos oito bits do handoff TT, e o resultado funcional e global foi FAIL.
No TT com RC integral do ECO reconstruído, houve 16/16 bits de leitura
e oito sobreposições no handoff. A CLI retornou 1. O tACCESS da palavra
foi 10,7554 ns no ciclo 7 e NOT_CHARACTERIZED no ciclo 6 por falta
de atribuição inequívoca da palavra à captura correspondente.
Em FF com RC integral da mesma reconstrução também houve 16/16 e
oito sobreposições no handoff. A CLI retornou 1. A comparação TT/SS/FF
da referência local cobre dois ciclos de leitura. As séries de Danilo
abrangem nove ciclos e preservam os resultados históricos registrados.
Em FF também houve sobreposição nos oito bits. Em DATA6 foram observadas
amostras de sobreposição entre 167,3159 e 167,3386 ns. Os dois controles
tiveram CLI 1, preservando a falha mesmo com 16/16 leituras corretas.
Essas medições TT descrevem somente o transiente registrado e o
modelo capacitivo. Elas não qualificam a macro em RC integral.

## Corrente no host após redistribuir os pinos

A nova distribuição removeu os dois FAILs de leitura que restavam no
controle C-only SS. No ciclo 7, DATA4 e DATA6 ficaram válidos em
160,8197 e 160,8097 ns, respectivamente. A janela abre em 160,900 ns.
O resultado global permaneceu FAIL e a CLI retornou 1. O handoff
continuou sinalizando sobreposição nos oito bits, e DATA1 excedeu
50 µA em cada uma das quatro escritas. Os oito DIN ficaram prontos
antes da abertura de WE em todas as quatro operações.

| Ciclo | Instante do pico DATA1 | Corrente absoluta | TE_B no pico |
|---|---:|---:|---:|
| 2 | 50,000730 ns | 71,929 µA | 1,800144 V |
| 3 | 70,000409 ns | 72,771 µA | 1,800074 V |
| 4 | 90,000409 ns | 72,554 µA | 1,800076 V |
| 5 | 110,000409 ns | 72,772 µA | 1,800074 V |

Os quatro pulsos coincidem com a subida pública de CLK enquanto TE_B
está alto e o valor no pino continua correto. O DEF tem um trecho
vertical de DATA1 em met2 paralelo à rota de CLK. O PEX capacitivo
mede 1,85847 fF de acoplamento CLK–DATA1 nessa geometria, contra
0,09423 fF no ff2 automático. Durante a rampa de 50 ps, a estimativa
C × ΔV/Δt desse cartão é de 66,9 µA. O acoplamento explica a maior
parte do pulso e separa esse efeito da sobreposição no handoff. O
check de 50 µA continua ativo com o mesmo critério e falha preservada.

O próximo ajuste físico, `--data-pin-placement distributed-spaced`,
move apenas a coordenada de entrada de DATA1 de 271 para 260 µm
entre as restrições de pinagem. O roteador pode alterar os caminhos
vizinhos. É necessário comparar o novo PEX de CLK–DATA1 e repetir
a leitura e a corrente de escrita na mesma fixture.

O GDS dessa variante tem SHA-256
`b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365`.
Obteve DRC=0 e LVS único com o mesmo Verilog roteado. O LEF foi
derivado do GDS reimportado e tem SHA-256
`1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091`.
A nova extração C-only traz 0,16616 fF no cartão CLK–DATA1, uma
redução de 91%. A capacitância incidente de DATA6 ficou em 10,46 fF.
Esses valores demonstram a redução do acoplamento no modelo extraído.
O novo transiente SS C-only manteve 16/16 bits. Os quatro picos em
DATA1 caíram para 7,714 µA, 9,041 µA, 7,676 µA e 9,044 µA.
Todos os 32 checks de prontidão DIN e todos os 32 checks de corrente
de escrita ficaram aprovados com a janela e o limite originais.
DATA6 ficou válido em 160,8170 ns no ciclo 7. Os oito FAILs de
sobreposição no handoff continuam e a CLI retornou 1.

Em SS com RC integral, os pinos distribuídos sem o afastamento de
DATA1 eliminaram cinco das nove falhas de leitura da versão ff2.
Restaram os ciclos 6/DATA1, 6/DATA5, 6/DATA7 e 7/DATA7. D e Q
estavam válidos nesses quatro casos. A subida de DATA7 no ciclo 6
chegou à faixa de validade em 140,9507 ns e o início da janela era
140,900 ns. Os quatro pulsos de DATA1 também aparecem com RC integral
nessa geometria, entre 70,25 e 70,65 µA. A direção ainda falha nos
oito bits do handoff. A CLI retornou 1.

Com DATA1 afastado, o RC integral eliminou as quatro violações de corrente
em DATA1. Os picos nas escritas foram 9,531, 10,759, 9,059 e 10,724 µA.
Os 32 checks de prontidão de DIN e 32 de corrente passaram. A leitura
subiu para 14/16. As duas falhas restantes são de DATA7 e o sense, D e Q
estavam válidos nas observações relevantes.

| Leitura SS | DATA7 esperado | DATA7 no início da janela | DATA7 no centro | Entrada na faixa válida |
|---|---:|---:|---:|---:|
| Ciclo 6, endereço 0 | 1 | 1,27568 V | 1,61711 V | 140,935652 ns |
| Ciclo 7, endereço 1 | 0 | 0,36017 V | 0,01210 V | 160,900016 ns |

A subida cruza 1,44 V cerca de 35,7 ps depois da abertura da janela.
Na descida, a tensão no início da janela está aproximadamente 0,17 mV
acima de 0,36 V. O instante interpolado é limítrofe frente à resolução
do transiente. O check permanece FAIL pelo valor medido no limite da janela.
Os oito FAILs no handoff também persistem. O simulador terminou 170 ns
com sucesso. A CLI retornou 1 e a qualificação segue NOT_CHARACTERIZED.

## Integridade e escopo da rodada

A extração integral selada dos pinos distribuídos contém 1.749 MOS,
16.044 resistores, 12.216 capacitores e os 16 pinos públicos.
Foram restaurados 92 cartões subatto, com 5.046 pares auditados.
O SHA-256 do SPICE selado é
`64078265f1ff1bc7012a4d0c03afc9376fb13830b6f2de4208b2cdc0fd6cbd66`.
O PEX selado com DATA1 afastado mantém 1.749 MOS e 16 portas, com
16.187 resistores e 12.371 capacitores. A auditoria conferiu todos os
5.118 pares. Foram restaurados 92 cartões subatto, que somam 0,04869 fF.
O SHA-256 do SPICE selado é
`12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`.
A extração integral da versão agrupada foi interrompida após a comparação
geométrica, pois alongava as rotas do primeiro grupo de bits. Os arquivos
da tentativa foram preservados. O GDS agrupado obteve DRC=0 e LVS único.
Os logs de ngspice registram advertências no ponto DC de início causadas
por nós de metal com ligação exclusivamente capacitiva. O simulador
registrou sucesso no ponto inicial transiente antes de integrar os
transientes completos observados. Nenhum resistor foi inserido no deck
para tratar essas advertências nesta rodada.

```bash
tools/sram-eda python3 tools/run_phase3_regressions.py \
  --output reports/phase3/danilo_ss_regressao_nova
tools/sram-eda python3 -m unittest discover -s tests -p 'test_phase3_rc*.py' -v
tools/sram-eda python3 tools/run_phase3_eco_pex.py recheck-protocol \
  --source build/phase3/danilo_ss_ff2_distributed_ss_c_probed \
  --output build/phase3/reanalise_protocolo_nova
```

A regressão final confirmou 165 casos da infraestrutura e 32 de RC.
Foram verificados os hashes dos waveforms e o CSV de 14 colunas.
Os arquivos da Fase 2, a fixture e os verificadores compartilhados
mantêm os bytes anteriores. As mudanças ficaram no checkout local,
com as geometrias e as evidências geradas em diretórios ignorados.
As etapas complementares não alteram os estados históricos da
homologação nominal do perfil de bancada P3-DATA-002 r1.

## Arquivos locais da entrega

| Arquivo ou grupo | Alteração |
|---|---|
| .gitignore | Isola extrações, waveforms e builds em build/phase3 |
| tools/rebuild_phase3_danilo_eco.py | Reconstrói o ECO a partir de entradas seladas e parametriza as hipóteses de FF e posicionamento |
| tools/run_phase3_eco_pex.py | Extrai, audita, simula, atribui falhas por estágio e reanalisa o handoff preservando as evidências |
| tools/phase3_rc_characterization.py | Mede tACCESS por palavra válida e mantém tCLK_TO_DATA por bit |
| tools/phase3_rc_probe_report.py e tools/phase3_rc_read_path.py | Lê vetores do runner e observa SCLK local e o percurso até DATA |
| tools/phase3_rc_cap_audit.py, tools/phase3_rc_extraction.py, tools/phase3_rc_probe.py e tools/phase3_rc_requalify.py | Reaproveita as ferramentas da frente Danilo com a origem registrada |
| tools/phase3_rc_output_slice.py | Executa comparações isoladas de captura, drive e desligamento |
| tools/export_phase2_top_lef.py | Expõe exportação opt-in para GDS experimental verificado e saída local nova |
| tests/test_phase3_rc*.py | Regressões importadas e cobertura da reconstrução, métricas e diagnósticos |
| docs/phase3_danilo_rc_timing_progress_20261115.md | Relatório original de Danilo vindo do commit 42f0b51 |
| docs/phase3_danilo_ss_integration_20261118.md | Registro da reconstrução e desta rodada de validação |

As hipóteses de FF e pinagem preservam a matriz 6T e os periféricos
analógicos. A alteração de posição dos pinos mantém a área de 540 ×
380 µm. As variantes de pinagem reutilizam o mesmo conjunto de células
que a revisão ff2. As medidas de energia do runner abrangem o ciclo
completo. Potência estática, setup/hold de interface, disable/turnaround
garantido, qualificação de timing e energia TT/SS/FF e Liberty permanecem
pendentes.

## Veredito e próximo experimento

A topologia de Danilo foi recuperada com uma geometria independente.
Na comparação com RC integral, a referência reproduziu a diferença
entre SS e TT/FF em dois ciclos. A melhor revisão local corrigiu oito
das dez falhas de leitura SS e eliminou os pulsos excessivos de DATA1.
O handoff continua reprovado e DATA7 ainda chega tarde em dois checks.
Os resultados de 18 ciclos de Danilo permanecem históricos e a revisão
com DATA1 afastado ainda precisa de TT e FF com RC integral.

A próxima intervenção de leitura deve atuar na capacitância, no drive
ou na rota Q→DATA7, mantendo a borda pública de captura. O ganho precisa
ser demonstrado com margem em ambas as transições, já que a descida
ficou muito próxima do critério de bancada. A revisão da desabilitação
de TE_B é um experimento separado. Deve preservar a tabela verdade e
medir OEb, WEb e CSb individualmente com RC, verificando também
reabilitação, máscara e o retorno de DATA à propriedade do host.
Uma alteração que só acelere OEb deixa sem cobertura a escrita com
OEb ainda ativo. As opções de porta experimentadas em bancada
isolada ainda carecem de margem no caminho de WEb.

A validação final de leitura, escrita e direção precisa cobrir os
18 ciclos em TT/SS/FF com o mesmo GDS, LEF, PEX e fixture. As medidas
de timing, energia, setup/hold e alta impedância por arco e a geração
de Liberty dependem dessa validação e dos estímulos elétricos
correspondentes. O projeto 4×8 fica com diagnóstico reproduzido e
correções físicas parciais. A qualificação elétrica permanece em aberto.
