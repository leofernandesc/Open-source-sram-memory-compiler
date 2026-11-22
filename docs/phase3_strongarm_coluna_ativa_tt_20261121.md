# Fase 3 · StrongARM em coluna ativa 4×1 em TT

**Veredito · `STRONGARM_ACTIVE_COLUMN_WITH_RISK`.** A coluna ativa do bit 3 escreveu e reteve `0, 1, 1, 0` nas linhas 0–3. O StrongARM original de 11 MOS, com o SCLK histórico, entregou **1, 0, 0** em c15–c17. As duas bitlines se recuperaram após cada leitura. A condução simultânea do tail e do reset interno persistiu por **388–400 ps** na subida de SCLK. C permanece com `FAIL` TT. [Análise completa](../build/phase3/sense3_strongarm_active_column_tt_20261121/analysis.json)

## Coluna e fronteiras

A única coluna é a de DATA3. Foram selecionadas quatro células 6T, os 12 MOS do write driver, dois PMOS de pré-carga e o equalizador de C. A dupla BL/BLB conserva os 28 resistores da interconexão extraída, inclusive os ramais para as células, para a escrita e para o sense. O recorte total tem **39 MOS extraídos, 36 resistores e 175 capacitores**, com 45 nós ativos na coluna. Com o StrongARM e células HD de saída e de complemento de escrita, a bancada tem 98 MOS. A entrada do StrongARM liga-se a `rc8210/rc8222`, os terminais do sense de C. BL, BLB e Q/QB são nós ativos. O netlist mantém o núcleo StrongARM, os dois buffers, o mux e o FF do protótipo anterior byte a byte, com a dupla ativa nos pinos de entrada. [Inventário original de BL/BLB](phase3_viabilidade_fronteira_diferencial_sense3_20261121.md) · [Preflight](../build/phase3/sense3_strongarm_active_column_tt_20261121/preflight.json) · [Netlist da coluna](../build/phase3/sense3_strongarm_active_column_tt_20261121/run/column.spice)

| Linha | Q / QB no binding | Acessos BL / BLB | Comando de WL arquivado | Última escrita preservada, bit 3 |
| --- | --- | --- | --- | --- |
| 0 | `rc6957 / rc6952` | X1570 / X631 | `rc8059`, proxy no mesmo grupo resistivo | c8, `0x55` → 0 |
| 1 | `rc6958 / rc6953` | X637 / X1416 | `rc8084`, proxy no mesmo grupo resistivo | c10, `0xAA` → 1 |
| 2 | `rc6959 / rc6954` | X1511 / X581 | `rc8109`, proxy no mesmo grupo resistivo | c4, `0x0F` → 1 |
| 3 | `rc6960 / rc6955` | X1592 / X663 | `rc7944 / rc7945`, gates exatos dos acessos | c5, `0xF0` → 0 |

| Elemento | Representação | Origem dos parâmetros | Limitação e efeito potencial |
| --- | --- | --- | --- |
| BL/BLB e célula | Redes R/C distribuídas preservadas, quatro células ativas, MOS de acesso e junções com parâmetros extraídos | PEX selado de C, SHA-256 `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` | Terminais de acesso permanecem físicos. A nova folha StrongARM tem os parasitas dos modelos MOS. O roteamento físico futuro segue em aberto. |
| Acoplamentos internos e a trilhos | Cartões incidentes aos nós ativos, com os trilhos fisicamente identificados ligados a VDD/VSS ideais | PEX C, inclui C896 de 15,988 fF entre as bitlines e os cartões distribuídos para trilhos | Os trilhos ideais absorvem as correntes. Droop, bounce e retornos compartilhados seguem fora do escopo. |
| Pré-carga e escrita | X1352/X1645 e X374 ativos, 12 MOS de escrita ativos. Inversor `inv_1` do PDK gera DINB | PEX C e complemento de escrita da arquitetura existente | Fontes ideais de PRECH, WE interno ativo alto e DIN em fronteiras de controle. Os gates usam tap arquivado da mesma rede quando a sonda exata está ausente. |
| Seleção e caminho de saída | WL arquivada em quatro linhas, READ_Q arquivado, mux e FF reais. SCLK no gate de X351 histórico e borda de captura original | Ondas TT de C (`7f6c050f…`) e candidato de 11 MOS arquivado | Decoder, fanout compartilhado de SCLK e impedância da sua rede ficam fora do ensaio. Não há mux de coluna. |
| Acoplamentos de controle e vizinhança | Placas de controle usam o replay na rede correspondente. Oito capacitores para redes vizinhas de bitline usam agressor histórico unidirecional. A coluna em teste pode responder à sua corrente | PEX C e taps arquivados das mesmas redes | As outras colunas ficam representadas por tensão capacitiva de fronteira, sem MOS nelas. As placas externas são proxies quando o tap difere. Interação de retorno com as vizinhas segue em aberto. |
| Placas do sense anterior | Oito cartões que terminavam em SA/SAB/NTAIL do sense removido ficaram fora, 3,546 fF no total e 3,447 fF diretamente nas bitlines | Identificação por conectividade dos três nós removidos | Esses cartões pertenciam ao latch e ao seu roteamento anterior. Sua ausência altera a carga e o feedthrough. O teste não presume os mesmos acoplamentos na nova geometria. |
| Acoplamentos secundários sem sonda | Dezoito cartões omitidos de nós de armazenamento e da escrita, 0,48644 fF somados. Nenhum ligado diretamente à dupla BL/BLB. Maior cartão individual de aproximadamente 0,0544 fF | Inventário por placa do PEX | Possível efeito indireto sobre Q/QB e nós do writer. A 1,8 V, o maior cartão equivale a cerca de 0,098 fC por transição de trilho. A convergência de Q/QB e a retenção foram verificadas no transiente. |

Todos os demais cartões não nulos diretamente incidentes a BL/BLB têm origem e tratamento registrados. Esses cartões somam 29,129 fF internos ao recorte, 52,861 fF aos trilhos, 15,972 fF a controles e 2,236 fF a vizinhança, contados uma vez por elemento. São inventários de placas distribuídas, sem redução a um capacitor equivalente. Nenhum acoplamento externo sem sonda foi terminado artificialmente em terra. [Inventário por placa](../build/phase3/sense3_strongarm_active_column_tt_20261121/capacitor_inventory.csv)

## Condicionamento e execução

O estado foi estabelecido eletricamente. O deck inicia com a rampa de VDD de 0 a 1,8 V em 1 ns. Os controles de 0–8 ns são do startup arquivado. A junção de 8–10 ns ocorre com WE, WL e SCLK inativos e PRECH ativo nas duas margens. O trecho local de 10–169 ns reproduz os controles de 88–247 ns no arquivo TT, com deslocamento uniforme de −78 ns. Esse trecho preserva as quatro últimas escritas e as leituras c14–c17 completas. As escritas mais antigas de linhas 0/1 são sobrescritas por c8/c10, respectivamente. A condição analógica de partida de C em 88 ns não foi imposta às células. As quatro escritas e a leitura predecessora c14 dão o condicionamento antes do c15. Nenhum `.ic`, `.nodeset` ou fonte de estado foi aplicado a Q/QB. As rampas principais de SCLK e captura das quatro leituras usam os pontos nativos. A compressão dos controles nos demais intervalos está limitada a 0,1 mV, conferida no preflight. [Histórico TT](phase3_data3_tt_snm_piloto_20261120.md) · [Replay](../build/phase3/sense3_strongarm_active_column_tt_20261121/control_replay.csv)

**Preflight `READY`.** A seleção por WL, a polaridade de WE e DIN, os bulks e os 319 modelos TT foram conferidos antes de executar. O fechamento das fronteiras preserva a resposta elétrica de BL/BLB no recorte. Rodou um único transiente de **169 ns**, TT, 1,8 V, 27 °C, Gear/KLU e passo máximo de 25 ps. O comando foi executado no container `sram-xschem` na pasta do deck:

```sh
timeout --kill-after=5s 240s stdbuf -o0 -e0 /opt/ngspice/ngspice-44.2/bin/ngspice -n -b bench.spice
```

Tempo **110,857 s**, retorno **0**, **37.604 amostras** finitas de tensões e correntes em eixos idênticos, cobrindo todo o horizonte. Deck SHA-256 `2d8c923d546177cf1a0442175cd9341a97026b918efb01a73a0a29dcd5687dd2`, waveform `dffffa1b16e9d891a61a6ffb02c769e3dfd0657779a31bdc7e8ebb7b7177391b`, correntes `22a94f68207756127916dd5d46a90ed3d4018d5a009920265589c8488deb11b0`. [Comando](../build/phase3/sense3_strongarm_active_column_tt_20261121/attempt.json) · [Recibo](../build/phase3/sense3_strongarm_active_column_tt_20261121/simulation.json) · [Log](../build/phase3/sense3_strongarm_active_column_tt_20261121/run/ngspice.log)

## Leituras, bitlines e kickback

As quatro escritas foram verificadas em 107, 127, 147 e 167 ns no eixo da fonte. De cada verificação até a última recuperação monitorada, as células mantiveram Q/QB nas bandas 20/80% de 1,8 V. c14 leu 1 na linha 1 e estabeleceu o predecessor do FF. As três leituras-alvo seguem abaixo. A margem usa o intervalo contínuo com SA/SAB e D corretos até a captura, com amostras e interpolação na borda.

| Ciclo | Linha / bit | Captura no eixo histórico (ns) | SA/SAB e D na captura | Q do FF | Margem conjunta (ns) | Extremos de Q/QB da célula durante leitura e recuperação |
| --- | --- | ---: | --- | ---: | ---: | --- |
| c15 | 2 / 1 | 200,058 | Alto/baixo, D alto | 1 | 5,475 | Q ≥1,775 V, QB ≤0,130 V |
| c16 | 3 / 0 | 220,058 | Baixo/alto, D baixo | 0 | 5,267 | Q ≤0,133 V, QB ≥1,773 V |
| c17 | 3 / 0 | 240,058 | Baixo/alto, D baixo | 0 | 5,293 | Q ≤0,133 V, QB ≥1,773 V |

Com WL ativa, BLB−BL adquiriu o sinal esperado antes de SCLK20 e o preservou até a captura nas três leituras. A diferença em SCLK20 foi **−46,2 / +22,5 / +28,5 mV** em c15/c16/c17, ante **−30,5 / +15,1 / +19,9 mV** no replay ideal. O modo comum em SCLK20 ficou em 1,839 / 1,856 / 1,853 V. No primeiro cruzamento de 1 µA no tail, obteve-se **−273,5 / +173,6 / +186,7 mV**. Em c16/c17, DI_BLB estava abaixo de DI_BL por cerca de 0,985/1,082 V quando o par e D entraram nas bandas corretas. Após a captura, BL/BLB retornaram à faixa alta e assim permaneceram pelo restante da recuperação monitorada, a partir de 204,719 / 224,708 / 244,706 ns. [Medições](../build/phase3/sense3_strongarm_active_column_tt_20261121/measurements.csv) · [Gráfico de bitlines, célula e captura](../build/phase3/sense3_strongarm_active_column_tt_20261121/coluna_ativa_tt.png)

A atividade dos gates pode carregar e descarregar os terminais reais. Foi calculada por KCL em cada ponta, integrando as correntes pelos dois R que a alimentam e subtraindo (C_{ponta}Delta V) no capacitor local para VSS. Na abertura de avaliação, de SCLK20 até 0,5 ns depois de SCLK80, os picos da soma resistiva nas pontas chegaram a **5,30 µA**. Essa corrente inclui a carga do C local. No trecho funcional de 88–247 ns, BL variou de −0,064 a 1,878 V e BLB de −0,046 a 1,871 V. As excursões foram observadas no circuito ativo. A integral do módulo dos incrementos de carga atribuídos ao gate chegou a **0,94 fC** numa entrada. A análise observa o sinal de BLB−BL, o acoplamento próximo das transições e Q/QB. Não houve inversão relevante do diferencial nem corrupção após a escrita. O desvio frente ao replay ideal também contém a descarga normal da célula, a mudança da carga do sampler antigo e as fronteiras declaradas. Sem um controle ativo pareado, a parcela de tensão causada exclusivamente por kickback permanece indeterminada.

## Reset e risco residual

| Indicador | Replay ideal | Coluna ativa |
| --- | --- | --- |
| c15 / c16 / c17 | PASS / PASS / PASS | PASS / PASS / PASS |
| Par e D estáveis até captura | Sim, margens 5,480 / 5,267 / 5,293 ns | Sim, margens 5,475 / 5,267 / 5,293 ns |
| BL/BLB respondem ao sense | Impostas por fontes ideais | Sim, pelos R/C, células e drivers retidos |
| Recuperação | Quatro nós do StrongARM recuperados | StrongARM e BL/BLB recuperados |
| Tail/reset na subida, marcador 1 µA | 397 / 397 / 398 ps | 400 / 388 / 393 ps |
| Pico de tail na avaliação | 90,7 / 93,0 / 93,0 µA | 88,7 / 88,6 / 88,8 µA |
| Carga no tail durante a sobreposição | 16,73 / 17,55 / 17,47 fC | 16,48 / 16,56 / 16,53 fC |
| Fração da carga do tail nessa janela | 94,8 / 95,6 / 95,6% | 94,9 / 94,7 / 94,9% |
| Kickback com consequência funcional | Não qualificado | Nenhuma consequência funcional observada no recorte. Parcela de tensão indeterminada. |
| Integridade de célula | Inferida da fonte histórica | Quatro escritas verificadas, retenção observada e nenhuma troca durante as leituras |

Na descida, a sobreposição interna foi de aproximadamente 95–96 ps. Em c15/c16/c17, os quatro nós voltaram à banda alta em 204,301 / 224,300 / 244,298 ns. No intervalo da descida, os três MOS de pré-carga/equalização da coluna tiveram correntes observáveis e nenhum intervalo coincidiu com XTAIL acima de 1 µA pelo mesmo marcador. O maior pico individual entre os dispositivos de pré-carga após a captura foi de cerca de 323 µA em c15. Esse transiente recarregou a bitline que havia sido descarregada e ficou separado da condução de tail pelo marcador. A carga comparada é a corrente integrada no tail durante o intervalo de simultaneidade, com a contribuição direta dos resets em aberto. O marcador de 1 µA é diagnóstico e a persistência da sobreposição nas rampas fundamenta o veredito de risco observado. [Protótipo com replay ideal](phase3_prototipo_strongarm_sense3_tt_20261121.md) · [Correntes e janelas](../build/phase3/sense3_strongarm_active_column_tt_20261121/analysis.json)

**Próximo gate:** na mesma coluna ativa, substituir somente a fonte ideal de SCLK por um acionador com impedância local representativa. Manter VDD/VSS ideais e as bitlines ativas. Comparar a fase efetiva, os picos e a carga de overlap, e exigir D correto e sustentado nos três ciclos antes de ampliar o escopo físico.

A geometria C, o checkpoint e os ZIPs anteriores permanecem preservados. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961`. C segue em `FAIL` TT e `PASS` SS no escopo integrado. FF e Liberty pendentes. Driver v2 e StrongARM permanecem experimentais. Monte Carlo concluído no domínio experimental. Macro `NOT_CHARACTERIZED`. Um preflight e um transiente em TT, sem alterações físicas ou execução de etapas posteriores.
