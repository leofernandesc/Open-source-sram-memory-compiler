# Fase 3 — margem de DATA7 e troca de direção da SRAM 4×8

Branch local `integration/phase3-danilo-ss`, HEAD `8e1d961`. A referência
desta rodada é a variante com tap 48, captura pelo CLK público, drivers
`ebufn_8`, `dfxtp_2` e DATA1 afastado de CLK. O GDS de referência é
`b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365`.
O SHA-256 de seu PEX integral selado é
`12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`.
A fixture, seus limiares e a janela S ±100 ps são os mesmos do relatório anterior.

## DATA7

O percurso é do FF _82_ Q, pela rede _94_.A, ao ebufn_8 _94_ Z e
às derivações para o pino DATA7 e o mux de escrita _52_. A referência
tem o FF em x=388,70 µm e y=68,00 µm, o driver em x=389,16 µm e
y=59,84 µm e o pino em x=384,79 µm na borda inferior. O trecho vertical
de met2 até o pino tem 61,37 µm. Na extração integral, a primeira ligação
resistiva desde o pino público para seu subnó interno é de 88,92 Ω.
Esse valor descreve uma aresta do PEX. A rede tem ramos e terminais MOS
e deve ser simulada com sua distribuição de R e C.

A variante `--data7-pair-near-pin` mantém os pinos DATA e fixa somente
o FF _82_ e o driver _94_ nos sites x=378,58 µm, y=27,20 µm e
y=21,76 µm. O roteamento e os taps são regenerados. A ligação vertical
até DATA7 caiu para 22,95 µm. O Verilog de entrada é idêntico e as
instâncias de tap no Verilog pós-roteamento mudam de posição. A
colocação automática dos outros pinos de controle pode mudar de
coordenada e o LEF dessa revisão deve acompanhar seu próprio GDS.

| Grandeza no PEX C-only | Referência | Par perto do pino |
|---|---:|---:|
| Capacitância incidente DATA7 | 14,16094 fF | 10,70954 fF |
| Capacitância incidente Q7 | 5,62495 fF | 5,39163 fF |
| Acoplamento DATA7–Q7 | 0,84662 fF | 0,20547 fF |
| Acoplamento DATA1–CLK | 0,16616 fF | 0,06702 fF |

A carga de bancada continua 10 fF por bit. As somas incidentes incluem
acoplamentos e descrevem o netlist. A troca de capacitância efetiva
depende da atividade dos vizinhos. O PEX integral e a forma de onda
comparável determinam o efeito em tempo.

Na nova extração integral, a aresta de acesso ao pino DATA7 passou
de 88,92 para 45,04 Ω. O GDS verificado é
`b38561cc8406ead2c5cec728855ea38131e9149dacd17b3eb54d5c20cfa18ab6`.
Seu LEF tem SHA-256
`4fc9af25665102507d81f793a35fb2a2a8950b61437411769438f9e98231afbe`.
O PEX selado tem 1.749 MOS, 15.735 resistores, 12.323 capacitores,
5.109 pares sem diferenças na auditoria e SHA-256
`4a0023e33021161055df3321ceaa76890e4e605c462e7efe5bef37327a977898`.

Os dois primeiros ensaios de posicionamento registraram rejeições
do OpenROAD. O primeiro usava a orientação DEF na API de placement.
O segundo encostava as caixas após a transformação de orientação.
A versão legal usa duas linhas R0 e preserva os logs das tentativas.

A repetição de sensibilidade usa `--max-step-ps 10` na mesma geometria
de 14/16. O controle original usou 25 ps. A margem reportada é a
diferença entre o início fixo da janela e a entrada final na faixa
20/80 que permanece válida até o fim. Uma diferença menor que a
resolução local ou que a variação observada entre passos não sustenta
margem física. Esse teste de robustez não muda as regras do benchmark.

| Passo máximo na referência | Subida, ciclo 6 | Descida, ciclo 7 | Bits corretos |
|---|---:|---:|---:|
| 25 ps | −35,652 ps | −0,016 ps | 14/16 |
| 10 ps | −33,987 ps | +1,705 ps | 15/16 |

Com 10 ps, houve 17.532 amostras em 170 ns. As duas passagens por
limiar foram interpoladas entre pontos separados por cerca de 10 ps.
No passo maior, os intervalos locais eram 16,374 e 10,984 ps. A subida
segue com atraso reproduzível. A descida muda de classificação na
escala da discretização e continua sem margem demonstrada.

## Contrato de interface e guarda da fixture

A especificação técnica exige liberar o modo de leitura, aguardar
a saída ficar em alta impedância e então habilitar o host respeitando
setup/hold. A seção *Read-to-write handoff* da especificação digital
coloca a dupla condução fora do estímulo legal. O contrato deixa a
latência física por caracterizar. Os 300 ps do ciclo 8 são um parâmetro
da fixture da Fase 2.

No waveform de referência SS, OEb sobe e WEb desce no intervalo
167,000–167,050 ns. O interruptor forte do host cruza seu limiar de
ativação de 1,0 V em 167,327778 ns. Por bit, TE_B cruza 80% em
167,573070–167,591939 ns, de 245,3 a 264,2 ps depois da ativação.
O ramo do host apresenta picos de 20,35 a 79,50 µA nesse intervalo.
O payload do host é 0x55 e a saída anterior também é 0x55. A janela
mede sobreposição por um limiar interno de desabilitação, com níveis
lógicos concordantes. A corrente do host inclui componentes capacitivas.

`tools/phase3_rc_turnaround.py` usa o mesmo PEX integral auditado em
uma bancada separada. Escreve 0xAA, lê essa palavra, aplica
desabilitação independente por WEb, OEb e CSb, volta a leitura entre
máscaras e depois escreve 0x55 e o lê de volta. Um host fraco de 1 kΩ
dirige o complemento durante as máscaras. A liberação é observada
pela passagem do barramento ao nível do probe e pela redução da
corrente fraca. A reabilitação sob carga adversa é verificada por
TE_B baixo e retorno da corrente do probe. As duas leituras lógicas
usam janelas com o probe desconectado. O ensaio registra atraso de
controle50 até live_read50, TE_B80 e DATA válido sob a carga definida.

A troca final usa um host forte de 1 Ω e palavra oposta à anterior.
As guardas diagnósticas programadas são 300 ps e 1.500 ps, medidas
desde o começo das rampas. A comparação registra o instante de
acionamento do interruptor e o primeiro TE_B80 por bit. Monitores de
0 V registram a corrente no terminal da macro e no ramo do host.
As correntes de sinais opostos incluem efeitos capacitivos e são
preservadas separadamente da estimativa de intervalo de dupla
condução. O valor de 1.500 ps é um ponto de diagnóstico. O benchmark
original continua com sua guarda original.

## Comandos

Todos os comandos partem da raiz do projeto. As saídas são diretórios
novos e `tools/sram-eda` fornece a instalação pinada.

```bash
tools/sram-eda python3 tools/rebuild_phase3_danilo_eco.py \
  --output build/phase3/data7_pair_novo_route --output-ff dfxtp_2 \
  --data-pin-placement distributed-spaced --data7-pair-near-pin
tools/sram-eda python3 tools/run_phase3_eco_pex.py simulate \
  --source build/phase3/danilo_ss_ff2_spaced_pex_sealed \
  --output build/phase3/data7_reference_novo_10ps --corner ss --cycles 8 \
  --max-step-ps 10 --timeout 4200
tools/sram-eda python3 tools/phase3_rc_turnaround.py \
  --source build/phase3/danilo_ss_ff2_spaced_pex_sealed \
  --output build/phase3/turnaround_ref_novo --corner ss --host-guard-ps 1500
tools/sram-eda python3 tools/phase3_rc_output_slice.py \
  --output build/phase3/turnaround_nand4bb_novo --corner ss --direct-disable --native-nand
```

Para fechar o PEX da nova geometria, aplicar os comandos de integração,
reimportação, LEF, extração e selagem do relatório anterior ao route
report da variante. A árvore em `reports/phase2/local/` contém os
recibos independentes de DRC/LVS e do LEF ligado ao GDS.

## Experimento de desabilitação local

A bancada isolada com `nand4bb` aplica os três controles um por vez
a células reais SKY130. As entradas invertidas são OEb e CSb. WEb
entra diretamente na NAND, no caminho de subida de TE_B. A entrada
READ_Q fica ativa. Carga em TE_B de 3,79 fF além da entrada do
ebufn_8. A primeira tentativa com oito ramos ideais por tamanho
atingiu o timeout e foi preservada. O caso repetido usa um ramo por
tamanho, pois as fontes de estímulo e de alimentação são ideais e
cada ramo é independente neste deck.

| Célula | OEb50 → TE_B80 | WEb50 → TE_B80 | CSb50 → TE_B80 |
|---|---:|---:|---:|
| nand4bb_1 | 332,1 ps | 324,9 ps | 343,6 ps |
| nand4bb_2 | 228,4 ps | 197,9 ps | 240,2 ps |
| nand4bb_4 | 173,2 ps | 134,4 ps | 185,4 ps |

A alternativa opt-in `--ownership-nand4bb 4` substitui as oito
`nand2_1` de saída por NAND4BB locais. Sua tabela verdade continua
`TE_B = !(READ_Q && WEb && !OEb && !CSb)`. O registrador de operação
continua recebendo live_read, e o controle de captura usa a mesma
borda e rede. A geometria deste ensaio mantém a variante spaced de
partida e não inclui o reposicionamento de DATA7. A medição isolada
serve para selecionar a célula. A carga e distribuição dos controles
públicos mudam depois de rotear, portanto a latência medida nessa
bancada não se transfere à macro.

A revisão isolada tem DRC zero e LVS único, com 2.005 MOS e 16
portas. O GDS verificado é
`9748048c077fa7dfa64ee468fa7b398940e1d884d173fd2a46bbe043b24b9640`
e o LEF derivado tem SHA-256
`ee240534b7f48e8bdbcecdad03449ed6f1ac379f3222a0aea338e1637bffb46e`.
As oito portas acrescentam 190,18 µm² de área de células LEF.
O contorno da macro continua 540 × 380 µm.
O PEX integral selado contém 17.738 resistores e 13.698 capacitores.
Auditou 5.400 pares sem divergência e tem SHA-256
`fc0a6d240072bcd55ccf1a4b6659e3c7ede64327db80836178883edfcc35e8fb`.

A primeira bancada integral de máscaras usou tempos de recuperação
curtos. Durante o evento WEb, partindo de leitura ativa, obteve
live_read50 em 411,9 ps e TE_B80 de 907,6 a 936,7 ps. Antes da máscara
de OEb a habilitação ainda estava se recuperando, e a observação
passou a representar um driver já desabilitado. Essa evidência não
qualifica OEb, CSb nem o handoff final. A versão v2 é separada,
com 2,5 ns de máscara e 6 ns de recuperação entre os eventos. As
checagens de precondição e alta impedância usam os mesmos limiares.
O ensaio histórico e seu erro de cobertura continuam preservados.

## Desabilitação medida na referência com RC integral

A v2 com guarda de 1.500 ps completou 108 ns, 5.763 amostras e
24/24 máscaras com saída previamente ativa, liberação e reabilitação
verificadas. Foram medidos os oito bits, a 1,8 V, 27 °C em SS.

| Controle | Até live_read50 | Até TE_B80 | Até corrente do probe ≤50 µA | Restauração até TE_B20 |
|---|---:|---:|---:|---:|
| WEb↓ | 411,9 ps | 907,6–936,7 ps | 821,0–1.067,5 ps | 2.721–2.775 ps |
| OEb↑ | 227,4 ps | 731,1–760,0 ps | 642,6–888,2 ps | 2.750–2.796 ps |
| CSb↑ | 222,1 ps | 724,3–753,3 ps | 635,5–881,6 ps | 2.727–2.773 ps |

A referência de restauração é o controle50 da rampa de retorno.
O critério de corrente exige que o probe permaneça abaixo do limiar
até o fim da observação da máscara. As faixas variam entre bits e
entre as polaridades das saídas. Medir somente TE_B pode subestimar
a latência para um receptor externo em algumas condições.

Na troca final (OEb↑ e WEb↓ simultâneos), com guarda de 1.500 ps,
o host ligou em 70,027778 ns. O último TE_B80 ocorreu em
69,179446 ns. A margem observada foi 848–874 ps, os oito checks
de propriedade passaram e o pico de corrente estável do host
ficou abaixo de 10 µA. A leitura da segunda escrita passou 8/8.
A primeira leitura manteve a falha conhecida de DATA7 no limite
inferior da janela de observação. O manifesto global é FAIL,
com o resultado de handoff separado.
O replay de direção também verificou a primeira escrita e a
desabilitação sustentada até o host sair da segunda escrita. A
macro voltou a habilitar a leitura cerca de 5,8 ns após a liberação
do host, sob o sequenciamento programado nessa bancada.

### Proposta para a interface do host

Definir tDIS por controle e polaridade da palavra anterior, referenciado
ao cruzamento de 50% no pino de máscara. Medir a liberação dos oito
pinos com carga, slew e probe calibrados, uma condição de alta
impedância sustentada e o mesmo GDS/LEF/PEX da revisão. O host deve
contar a guarda a partir da última borda de controle relevante,
aguardar o máximo qualificado mais a incerteza do sistema e só então
habilitar seu driver. A retomada de escrita deve preservar setup e
hold públicos quando esses arcos forem caracterizados. Em produção,
qualificar tDIS, reabilitação e guarda nos corners e cargas aprovados.
O ponto de 1.500 ps demonstra uma sequência realizável no SS ensaiado.
Seu uso como valor público depende de caracterização e aprovação.

O ensaio v2 com guarda de 300 ps preservou os 24 checks de máscara e
a leitura de retorno 0x55. A troca reprovou nos oito bits. Os dois decks
da referência v2 diferem apenas na rampa do interruptor forte do host.

| Guarda diagnóstica | Intervalo host ligado até TE_B80 | Correntes opostas 100 ps após ligar o host | Correntes opostas 200 ps após ligar o host |
|---|---:|---:|---:|
| 300 ps | 321,7–351,0 ps | 234,9–1.246,7 µA | 84,1–1.164,4 µA |
| 1.500 ps | 0 ps | 3,8–7,8 µA | 0,8–4,3 µA |

A coluna de corrente usa o menor módulo das duas correntes simultâneas
de sinais opostos medidas em VM e VH. A 300 ps, os picos do instante de
fechamento da chave ideal de 1 Ω incluem impulsos capacitivos de
amplitude muito superior. A corrente dezenas ou centenas de ps depois
distingue a oposição persistente sob a guarda curta. Esses valores
descrevem este modelo de bancada e não são limites de corrente da macro.

## Rejeição do reposicionamento do par DATA7

A revisão que moveu o FF e o driver completou 170 ns em SS com RC
integral e passo máximo de 25 ps. A subida de DATA7 no ciclo 6
entrou em faixa válida em 140,901691 ns, melhorando 33,96 ps e
ainda atrasada 1,69 ps. A descida no ciclo 7 ficou válida em
160,884376 ns, margem de 15,62 ps. A revisão introduziu novas
falhas (ciclo 6 DATA1 e DATA5, ciclo 7 DATA6). Os quatro checks
reprovados tinham D e Q corretos. O resultado foi 12/16, contra
14/16 na referência. Todos os checks de corrente de escrita e
prontidão DIN passaram, e os oito FAILs de handoff persistiram.

O reroteamento teve efeitos fora de DATA7 e esta geometria foi
rejeitada. A alternativa seguinte reaproveita o DEF selado da
referência, com todas as colocações e os demais nets fixados.
`tools/route_phase3_data7_metal4.py` promove somente o trecho
vertical de DATA7, mantendo o pino e a derivação para escrita.
O DEF de entrada da alternativa difere somente nesse trecho e
em suas duas pilhas de via. DRC, LVS, verificação de geometria e
simulação usam os artefatos novos dessa alternativa.

A alternativa met4 usa GDS
`ed9e149f7e18701409c70ee8c3ab14f2c59909e5805d314251a0a7e5b8785955`
e LEF
`f5e390d42e56e00ea0f4dfde452a9a5735fe38c5923ea37748196835c18283ea`.
O GDS reimportado obteve DRC zero e LVS único, com 1.749 MOS.
A comparação geométrica de todas as células confirmou referências
idênticas e diferenças de polígonos somente no topo, entre
x=384,60–385,48 µm e y=2,535–60,885 µm, em met2, met3, met4 e vias.
O recibo está em `build/phase3/data7_met4_route/geometry_delta.json`.
No C-only, DATA7 passou de 14,16094 para 13,72225 fF incidentes.
O acoplamento Q7–DATA7 ficou praticamente igual e DATA1–CLK
permaneceu em 0,16616 fF. A extração integral determina o efeito
das resistências distribuídas e das novas vias.

```bash
tools/sram-eda python3 tools/route_phase3_data7_metal4.py \
  --output build/phase3/data7_met4_novo_route
```

A etapa seguinte aplica o mesmo fluxo de acabamento, verificação,
exportação LEF e extração do experimento do par DATA7, usando os
novos diretórios.

Um teste isolado com dfxtp_2 e 5 fF em Q e 24 fF em DATA comparou
um, dois e três ebufn_8. Os tempos de CLK↓50 até DATA80 foram
603,50, 577,76 e 589,68 ps, respectivamente. Para DATA20 foram
522,12, 514,91 e 519,98 ps. Com três drivers o cruzamento Q50
atrasou de 352,47 para 392,78 ps. O terceiro driver aumentou a
carga do FF e perdeu margem frente ao segundo. O paralelismo
isolado se manteve como diagnóstico e não foi introduzido no
GDS.

## Desabilitação da NAND4BB local, com RC integral

A bancada v2 com 300 ps na revisão nand4bb_4 completou 108 ns,
5.802 amostras, todas as 24 máscaras e todos os oito checks de
handoff. A tabela compara a mesma observação por controle e por
bit, com os dois PEXs devidamente identificados.

| Controle | Referência até TE_B80 | NAND4BB local até TE_B80 | NAND4BB até corrente do probe ≤50 µA |
|---|---:|---:|---:|
| WEb↓ | 907,6–936,7 ps | 195,8–218,8 ps | 198,9–364,2 ps |
| OEb↑ | 731,1–760,0 ps | 236,9–247,3 ps | 263,0–398,9 ps |
| CSb↑ | 724,3–753,3 ps | 258,1–271,5 ps | 276,3–419,8 ps |

A margem do último TE_B80 até ligar o host ficou em 151,7–159,7 ps
no handoff combinado. A corrente do host em regime estável ficou
entre 2,22 e 10,30 µA. Os dois writes mantiveram a propriedade do
barramento. A volta para leitura ocorreu após o host liberar e
a leitura de retorno passou 8/8. Os 24 checks também verificaram
retorno de drive após OEb, WEb e CSb individuais. A recuperação
TE_B20 ocorreu em 220–427 ps nessa bancada.

A alteração de controle concluiu a verificação diagnóstica da
troca simultânea com a guarda curta. Os tempos de liberação
observados sob as outras máscaras mostram por que 300 ps não
pode ser estendido a uma garantia geral. A geometria teve três
falhas na primeira leitura v2 (DATA1, DATA5 e DATA7), que impediram
PASS funcional global. O retorno da escrita passou nos oito bits.

Na sequência original, com os mesmos oito ciclos e passo máximo de
25 ps usados na referência, o simulador completou 170 ns e gerou
9.399 amostras. Os 72 checks obrigatórios de escrita e propriedade
passaram. Na referência, oito desses checks falhavam no handoff.
A leitura ficou em 13/16. A descida de DATA7 no ciclo 7 passou,
enquanto a subida de DATA7 no ciclo 6 continuou atrasada. DATA1 e
DATA5 passaram a falhar no mesmo ciclo 6.

| Ciclo | Linha | Bit | Esperado | DATA no início da janela | DATA no centro | D na captura | Q no centro |
|---:|---:|---|---:|---:|---:|---:|---:|
| 6 | 0 | DATA1 | 1 | 1,42884 V | 1,68415 V | 1,80364 V | 1,79904 V |
| 6 | 0 | DATA5 | 1 | 1,34252 V | 1,64837 V | 1,80599 V | 1,80087 V |
| 6 | 0 | DATA7 | 1 | 1,31190 V | 1,63598 V | 1,80224 V | 1,80137 V |

O limiar alto é 1,44 V durante toda a janela fixa. Os três FAILs
foram classificados como `DATA_INVALID_WITH_VALID_D_Q` no recibo
`build/phase3/turnaround_nand4bb4_ss_benchmark/failure_stages.csv`.
O sense estava resolvido na captura e TE_B estava baixo no ponto de
observação. A variante mudou o roteamento do periférico. A regressão
aparece nos dois segmentos do caminho de DATA5. Da captura local
até o cruzamento de 50% na entrada do driver, o atraso passou de
499,65 a 512,35 ps. Da entrada do driver até DATA80, passou de
313,55 a 334,75 ps. A capacitância incidente em DATA5 subiu de
11,166 a 12,983 fF. Isso indica onde recuperar margem. Isolar cada
extração de carga, acoplamento ou deslocamento ainda exige uma
geometria com as rotas críticas preservadas. A geometria NAND
demonstrou a correção da troca de direção e continua reprovada
como substituta funcional.

O recibo `build/phase3/data7_margin_replay` verifica os hashes
dos waveforms e recompõe os cruzamentos, a resolução local e as
margens por bit. O CSV de métricas mantém as 14 colunas. O
`tACCESS` da palavra do ciclo 6 ficou sem valor nas duas geometrias.
Na variante NAND, o ciclo 7 produziu 10,87158 ns do CLK50 de subida
à última entrada estável da palavra na faixa de validade. Esse
valor diagnóstico de um ciclo não constitui uma qualificação de
timing para a macro.

### Cobertura de resistência da rota met4

A extração padrão dessa geometria omitiu os 29 resistores
anteriormente presentes em DATA7, embora a conectividade do
GDS tenha passado em LVS. A auditoria de capacitância e a
conectividade dos trilhos passaram. Uma auditoria de contagens
globais não detecta esse caso. O ensaio transiente desse deck
foi interrompido por falta de cobertura no net estudado.

Na extração isolada com debug, Magic estimou Tnew=0,89 ps e
registrou `Not adding DATA[7]` com o corte padrão Tmin=1,00 ps.
Forçar a exportação produziu o nó no arquivo, mas a poda dos
ramos continuou ativa. Esse comportamento foi conferido nos
fluxos `ResWriteExtFile` e `ResDoSimplify` da versão compilada.
Tnew é uma estimativa interna de extração. O critério de tempo
e os limiares do benchmark permanecem os mesmos.

O runner aceita `--require-rc-port 'DATA[7]'` para bloquear
simulações se o pino não tiver resistência distribuída no PEX.
O teste real dessa proteção retornou BLOCKED, código 1 e ausência
de execução do simulador. A extração suporta
`--rc-mindelay-ps 0 --force-rc-port 'DATA[7]'`. A extração
isolada produziu 35 resistores no net com o corte desativado,
com ou sem a opção de forçar a exportação. Foram iniciadas
novas extrações da referência e da nova geometria separadamente,
sob as mesmas opções, para comparar os dois transientes.

No modelo passivo original, a resistência do pino aos terminais
de DATA do driver, tomando os terminais de cada polaridade em
curto ideal, foi de 88,92 Ω na rede de subida e 361,16 Ω na
de descida. Na revisão de reposicionamento, os valores são
45,04 Ω e 317,29 Ω. Isso separa a resistência do interconector
da resistência dinâmica dos dispositivos. Os valores e os
terminais selecionados estão no recibo
`build/phase3/data7_resistance_confirmed/results.json`.

### Selagem comparável sem a poda por atraso

As duas extrações sem corte concluíram com cobertura de resistência
em DATA7. A primeira selagem reprovou nas duas geometrias. Em cada
uma havia 57 discrepâncias, todas entre a referência C-only igual
a zero e uma capacitância de substrato abaixo de 1 aF no RC.
Por exemplo, para `a_53783_10205#` o arquivo plano `.ext` registra
0,992822 aF. O exportador C-only imprimiu zero e o `.res.ext`
dividiu a capacitância em dois subnós de 0,496411 aF. A selagem já
recuperava os valores dos subnós para o RC.

A correção recupera também os valores declarados no arquivo plano
para os cartões C-only discretamente zerados quando esses pares
divergem. Ela gera uma cópia auditável do C-only e uma lista das
57 restaurações, sem alterar seus originais ou a tolerância da
auditoria. As selagens novas verificaram 5.178 pares na referência
e 5.180 pares na met4, todos iguais dentro dos limites existentes.
Os dois PEXs têm 19.771 resistores. A referência original
selada tinha 16.187, uma diferença de 3.584 resistores.

| Geometria | SHA-256 do PEX selado | R passiva de DATA7 na subida | R passiva de DATA7 na descida |
|---|---|---:|---:|
| Referência sem corte | `935a3b5a368a421f10a7b9956c35a45192940bc759778aff10eed2c810ef6479` | 269,163 Ω | 361,160 Ω |
| met4 sem corte | `8dfe4c366686dbcd60b52a44104fec42ecc4b3b584ae809a96f1d842e26c48e9` | 239,948 Ω | 331,946 Ω |

Nessa extração, a promoção de metal reduziu a resistência passiva
efetiva em 29,215 Ω na subida e 29,214 Ω na descida. O resultado
usa terminais de uma polaridade em curto ideal, sem a resistência
dinâmica do driver. A observação de margem no pino depende do
transiente completo. Os valores não devem ser comparados aos de
outra revisão com corte de atraso ativo.

As simulações pareadas completaram 170 ns. A referência obteve
9.164 amostras e met4 obteve 9.158. A referência teve margem de
−63,11 ps na subida e −44,00 ps na descida de DATA7. Met4 teve
−62,29 ps e −43,57 ps. A diferença medida entre geometrias foi
inferior a 1 ps nas duas transições, abaixo dos intervalos locais
de amostragem de 14–20 ps.

As duas geometrias entregaram 6/16 bits na janela, com as mesmas
falhas (ciclo 6 DATA1, DATA5, DATA7 e ciclo 7 DATA0, DATA1, DATA2,
DATA4, DATA5, DATA6, DATA7). D e Q estavam válidos nos dez casos.
Cada execução ainda registrou oito FAILs de propriedade. A queda
da referência de 14/16 para 6/16 foi reproduzida mantendo seu
próprio GDS e alterando o corte de atraso do extrator. Isso
expõe sensibilidade à extração além de DATA7 e impede fechar
o problema com a promoção de metal.

Na subida, da captura local a Q visto na entrada do ebufn_8,
o intervalo cresceu de 512,55 a 531,33 ps na referência quando
o extrator manteve os ramos adicionais. Da entrada do driver
até DATA80, cresceu de 344,17 a 353,70 ps. Na descida, os dois
intervalos foram de 525,84 para 543,89 ps e de 295,29 para
322,76 ps. Extrações diferentes alteram tanto o caminho
até a entrada do driver quanto a propagação até o pino.

Para reproduzir a comparação em cada geometria já verificada,
execute as três etapas com nomes de saída novos. Use a mesma
configuração nas duas. O comando de simulação retorna 1 enquanto
a qualificação elétrica está incompleta. Consulte o manifesto
para distinguir erro de execução e resultado funcional.

```bash
tools/sram-eda python3 tools/run_phase3_eco_pex.py extract \
  --geometry <recibo_gds> --magic /work/build/phase3/magic-8.3.703-opt/bin/magic \
  --rc-mindelay-ps 0 --force-rc-port 'DATA[7]' --output <rc_bruto>
tools/sram-eda python3 tools/run_phase3_eco_pex.py restore-subatto \
  --source <rc_bruto> --output <rc_selado>
tools/sram-eda python3 tools/run_phase3_eco_pex.py simulate \
  --source <rc_selado> --output <resultado_ss> --corner ss --cycles 8 \
  --max-step-ps 25 --timeout 3900 --require-rc-port 'DATA[7]'
```

### Triagem do inversor de captura de DATA7

O ensaio separado `data7_capture_slice_ss` manteve `dfxtp_2` e
`ebufn_8`. Usou 2,545 fF de carga concentrada na saída do
inversor, 5,630 fF em Q e 24,166 fF em DATA, incluindo os 10 fF
da bancada. Os valores vêm das somas de capacitância incidente
do PEX de referência. A comparação usa as células reais do PDK.

| Inversor | CLK↓50 → Q50 | CLK↓50 → DATA80 | CLK↓50 → DATA20 |
|---|---:|---:|---:|
| clkinv_1 | 380,16 ps | 633,92 ps | 549,44 ps |
| clkinv_2 | 364,18 ps | 617,84 ps | 533,59 ps |
| clkinv_4 | 353,87 ps | 607,54 ps | 523,26 ps |

O inversor maior adiantou subida e descida em cerca de 26 ps
neste modelo. A bancada não inclui o aumento de carga que um
inversor maior aplicaria na distribuição pública de CLK. O valor
observado também é menor que o atraso da subida do ensaio de
referência a 10 ps. A alteração não foi incorporada à macro.

### Variante de acesso interno em met3

O mesmo DEF pinado foi usado para uma terceira hipótese física.
`--internal-port` remove o percurso vertical até a borda inferior
e transfere somente DATA7 para um retângulo met3 centrado em
(384,79 µm, 61,71 µm), ligado por uma via ao ramo existente.
DATA7 mantém nome, direção e ligações ao driver e ao mux de
escrita. Os sete demais pinos DATA, o afastamento de DATA1, a
colocação dos FFs, os drivers e todas as outras instâncias
foram preservados.

O XOR de GDS confirmou a mesma hierarquia e alterações de
polígonos apenas no acesso em met2/met3 e na via. Somente
o label de DATA7 mudou. O recibo está em
`build/phase3/data7_internal_r0_route/geometry_delta.json`.
O GDS reimportado obteve DRC zero e LVS único, 1.749 MOS e
16 portas. Seu SHA-256 é
`b388c48fd66cf9c0002a2e7b85485a0f58040c9d0623be66d00b1b7ac31be38f`.
O LEF, obtido desse mesmo GDS, manteve o contorno de 540 ×
380 µm e contém o acesso met3 de DATA7. Seu SHA-256 é
`511da44a0da4ddadb7e1f24cc323d72e4d34158a40915f6f9175c8179fbdd3cb`.
A etapa valida o LEF contra o metal do GDS. A integração do
pino em um projeto pai ainda dependeria de validar o acesso
de roteamento com esse novo LEF.

No C-only, a capacitância incidente de DATA7 passou de
14,16094 para 8,17243 fF, queda de 5,98851 fF. DATA1 se
manteve em 11,52934 fF. A carga nominal da fixture continua
em 10 fF por bit. A geometria do acesso interno é independente
da variante de desabilitação NAND4BB.

A extração sem corte produziu 19.771 resistores, comprovação
de resistência distribuída em DATA7 e 5.163 pares de
capacitância auditados, todos aprovados. O PEX selado tem
SHA-256 `126428424c1eac17d7b4dd556ed23e3a3aa2a8a26c61d0cb464a77e303f988c3`.
A resistência passiva de DATA7 caiu a 217,583 Ω na rede de
subida e 309,580 Ω na rede de descida. São reduções de 51,580 Ω
frente à geometria de referência sob o mesmo perfil de extração.
O recibo dos três casos está em
`build/phase3/data7_resistance_three_geometries/results.json`.

O simulador completou os 170 ns em 9.174 amostras. Em relação à
referência com as mesmas opções, o acesso interno adiantou DATA7
em 36,87 ps na subida e 17,25 ps na descida. A chegada de Q à
entrada do driver variou menos de 0,2 ps. Assim, o ganho
observado está após o FF, no caminho até o pino. Durante a
abertura da janela, a subida estava em 1,30187 V (mínimo de
1,44 V) e a descida em 0,73920 V (máximo de 0,36 V).

| SS, RC sem poda por atraso e passo máximo de 25 ps | Ciclo 6, margem de subida DATA7 | Ciclo 7, margem de descida DATA7 | Leitura | Escrita e propriedade |
|---|---:|---:|---:|---:|
| Referência | −63,11 ps | −44,00 ps | 6/16 | 64/72 |
| Rota met4 na borda | −62,29 ps | −43,57 ps | 6/16 | 64/72 |
| Acesso interno met3 | −26,24 ps | −26,75 ps | 6/16 | 64/72 |

Na geometria de acesso interno, a última entrada válida foi em
140,926241 ns na subida e 160,926746 ns na descida. Os intervalos
locais de amostragem foram 13,06 e 11,37 ps, respectivamente.
As duas margens negativas excederam esses intervalos. Os limites
do benchmark foram mantidos. Os dez bits que falham coincidem
com a referência sem poda. D e Q estavam corretos, com perda da
janela após a captura. Os oito FAILs de handoff também persistiram.
A CLI retornou 1 e a geometria permanece experimental.

Os checks e os cruzamentos por bit estão em
`build/phase3/data7_matched_nocut_margins/read_margins.csv`.
A figura compara as mesmas amostras e a janela de 200 ps.
[Waveform pareado de DATA7](../build/phase3/data7_matched_nocut_figure/data7_ss_pareado.png)

```bash
tools/sram-eda python3 tools/route_phase3_data7_metal4.py \
  --internal-port --output build/phase3/data7_acesso_interno_novo
```

## Testes, código e integridade

Execuções EDA no contêiner do projeto com ngspice 44.2 (KLU),
Magic 8.3.703 e OpenROAD `v2.0-25787-gee9759486`.
O fluxo Python usou 3.10.12 no contêiner. Para a bancada RC, os
mesmos modelos SKY130A, 1,8 V, 27 °C, 20 ns e 10 fF por bit
foram usados nas comparações SS. Os testemunhos dos modelos e
da fixture estão nos manifestos. Cada transiente tem deck,
netlist de binding, probes, log, waveform, CSV e recibo próprios.
Os logs sem poda registram singularidade durante tentativas do
ponto DC inicial. O ngspice avançou com o ponto inicial transiente
e a análise funcional usa somente waveforms completos e validados.

| Código desta rodada | Alteração |
|---|---|
| `tools/rebuild_phase3_danilo_eco.py` | Opções físicas separadas para reposicionar o par DATA7 ou aplicar NAND4BB local |
| `tools/route_phase3_data7_metal4.py` | Edição do acesso físico de DATA7 a partir do DEF pinado, em met4 na borda ou em met3 no interior |
| `tools/run_phase3_eco_pex.py` | Passo de transiente, cobertura resistiva por pino, controle da poda por atraso e selagem dos efeitos de precisão do exportador |
| `tools/phase3_rc_turnaround.py` | Ensaios independentes de WEb, OEb e CSb, sobreposição, correntes, recuperação e escrita com readback |
| `tools/phase3_rc_probe_report.py` | Validação do horizonte de waveform para bancadas menores |
| `tools/phase3_rc_output_slice.py` | Triagem de máscaras, drive em paralelo e inversor de captura sob cargas explícitas |
| `tests/test_phase3_rc_eco.py` | Regressões do escopo da edição, evidências e detecção de falhas |

Passaram 165 testes da infraestrutura e 41 testes de RC e ECO,
total de 206 sem skips. O sumário de 165 casos está em
`reports/phase3/data7_turnaround_leonardo_regression_r2/summary.json`
e o log de 41 casos em
`build/phase3/data7_turnaround_regressions_r3.log`.
Os comandos abaixo usam destinos novos.

```bash
tools/sram-eda python3 tools/run_phase3_regressions.py \
  --output reports/phase3/regressao_nova
tools/sram-eda python3 -m unittest discover -s tests -p 'test_phase3_rc*.py' -v
git diff --check
```

A branch continua em `8e1d961`. Os arquivos da Fase 2,
os seletores de release, as especificações, a fixture original
e os verificadores compartilhados não foram alterados. Os testes
de software usam seus próprios dados e não contam como execução
elétrica. A saída dos ensaios EDA ficou em diretórios ignorados.

## Veredito da rodada

| Escopo | TT | SS | FF |
|---|---|---|---|
| Protótipo Danilo reconstruído, oito ciclos da rodada anterior, mesmo GDS e PEX | Leitura 16/16, propriedade 64/72 | Leitura 6/16, propriedade 40/72 | Leitura 16/16, propriedade 64/72 |
| Integração com dfxtp_2 e pinos espaçados, corte padrão, oito ciclos | RC integral não executado nesta geometria | Leitura 14/16 a 25 ps e 15/16 a 10 ps, propriedade 64/72 em ambos | RC integral não executado nesta geometria |
| Variantes desta rodada, oito ciclos e RC integral | Não executado | Melhor transferência de direção na NAND4BB com corte padrão, 72/72 de escrita e propriedade. A leitura foi 13/16. Com o mesmo perfil sem poda, as três geometrias de leitura entregaram 6/16. | Não executado |
| Revisão combinada, 18 ciclos | Não executado | Não executado | Não executado |

As contagens da primeira linha são do protótipo reconstruído
do histórico do commit `42f0b51`, com GDS `a593676029af…` e
PEX `84cecaa3e29f…`. São escopos distintos. A campanha reportada
por Danilo permanece no seu relatório. Nesta rodada, as quatro
geometrias novas obtiveram DRC zero e LVS único, com GDS e LEF da
mesma revisão auditados. A figura separada de correntes mostra
os casos de handoff sem e com a NAND local.
[Corrente no handoff SS com guarda de 300 ps](../build/phase3/turnaround_figures/handoff_ss_300ps.png)

A correção de direção com NAND4BB funcionou na bancada SS e
na sequência original. A variante não substitui a referência
porque a leitura regrediu em DATA1 e DATA5, além de continuar
atrasada em DATA7 no ciclo 6. A hipótese met4 foi descartada
por ganho inferior a 1 ps. Acesso interno em met3 produziu
ganho mensurável em DATA7, porém sem margem positiva nos dois
casos. Assim, falta uma revisão que preserve a leitura e
a troca de direção no mesmo benchmark. A revisão combinada
não foi construída para a campanha de 18 ciclos.

A próxima intervenção deve preservar as rotas de CLK, Q e
DATA1/DATA5 ao aplicar a NAND local. Para DATA7, o acesso interno
é a alteração física isolada que mais adiantou as duas bordas.
O ganho adicional deve ser medido no caminho de captura/drive
com o PEX comparável, incluindo resolução temporal suficiente.
Um teste isolado com inversor maior apontou ganho da mesma ordem
do atraso remanescente e ainda requer margem demonstrada no
layout. Repetir primeiro SS no benchmark fixo. Somente após
aprovar leitura, escrita e propriedade em uma geometria única
faz sentido executar a campanha de 18 ciclos com seu próprio
GDS, LEF e PEX nos três corners.

`tACCESS` continua baseado na última entrada estável da palavra
completa no intervalo de validade. Os três ensaios pareados
reprovaram ambas as palavras, e nenhum recebeu valor de
`tACCESS`. Permanecem pendentes a cobertura de 18 ciclos,
setup/hold, qualificação de timing e potência e um orçamento de
alta impedância e turnaround em condições qualificadas. A
qualificação elétrica permanece `NOT_CHARACTERIZED` e a
Liberty fica pendente.
