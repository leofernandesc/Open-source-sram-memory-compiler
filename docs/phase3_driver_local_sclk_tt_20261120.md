# Fase 3 — Driver local de SCLK com dispositivos SKY130 em TT

**Veredito na bancada reduzida: `VIABLE_FOR_PHYSICAL_STUDY`.** Um inversor CMOS assimétrico seguido de uma `sky130_fd_sc_hd__inv_4` corrigiu as decisões do sense 3 nos ciclos 16 e 17. D ficou baixo por aproximadamente 4,97 ns até a captura de referência. A descida a 20% deslocou-se em até 4,94 ps, com separação de pelo menos 109 ps entre as correntes de canal do tail e dos dispositivos de pré-carga nos dois ciclos investigados, no marcador de 1 µA. [Análise medida](../build/phase3/sclk_local_driver_20261120_v1/analysis.json) · [Waveforms comparativos](../build/phase3/sclk_local_driver_20261120_v1/driver_comparison.png)

## A. Caminho e alternativas

O tap 80 é uma saída da cadeia de atraso em `macro_core`. Ele alimenta tanto `sense_drive = READ_Q AND tap80` como a lógica distinta de `precharge_phase`. A saída de `sense_drive` aciona os oito senses. No binding extraído, R87 (6,46438 Ω) liga `rc8562` do SCLK compartilhado ao nó local `rc8571`. Ao isolar R87 no grafo resistivo, restam exclusivamente os gates de X235, X521 e X351, conectados a `rc8571` por R68/R60/R76 de 566,852/567,159/387,618 Ω. Capacitores da rede compartilhada permanecem conectados aos nós originais. O ponto proposto para inserção é o lado de entrada de R87, após `sense_drive` e fora da lógica do tap 80. [Manifesto e prova de conectividade](../build/phase3/sclk_local_driver_20261120_v1/manifest.json) · [Especificação](../specs/technical_specification.md#13-sense-timing) · [Contrato temporal](../specs/sram_4x8_timing_contract.md)

| Alternativa | Controle da subida | Preservação da descida | Complexidade | Principal risco |
|---|---|---|---|---|
| Cadeia de buffers convencionais | Atraso e restauração da borda | Também introduz atraso | Baixa | Reduzir a separação entre avaliação e pré-carga |
| AND com ramo local atrasado | Atraso pelo caminho lento | Caminho direto, sujeito à propagação do AND | Porta e cadeia de atraso | Fanout na entrada, reconvergência e pulsos encurtados |
| Inversor assimétrico + estágio restaurador | Limiar e descarga de MID deslocam a ativação | PMOS mais forte carrega MID na desativação | Dois estágios | Sensibilidade a slew e corner, e pico de corrente na carga |

A terceira alternativa foi escolhida pelo caminho simples sem reconvergência e pela possibilidade de avaliar ativação e desativação com o mesmo estágio de entrada. O deslocamento de 182 ps é referência experimental de uma correção já demonstrada. A comparação exige medir forma e temporização em cada gate e comprovar a decisão até a captura. [Contraste ideal reduzido](phase3_precondicionamento_sense3_tt_20261120.md)

## B. Circuito e critérios

O primeiro estágio usa PMOS regular de 2,52 µm e NMOS regular de 0,65 µm, ambos com L = 0,15 µm e bulk ligado à alimentação correspondente. MID aciona a `inv_4`, cuja subcélula SPICE foi copiada da biblioteca instalada no PDK SKY130A `0fe599b2afb6708d281543108caf8310912f54af`. O estágio inicial contém dois MOS. A célula restauradora contém oito MOS na vista SPICE entregue. A alimentação é a mesma fonte de 1,8 V da bancada. As fontes de 0 V no ingresso e na alimentação servem para medir corrente. A saída de potência é produzida pelos transistores. [Netlist do candidato](../characterization/phase3/experiments/sclk_local_driver_v1.spice) · [Netlist da célula instalada](../build/phase3/sclk_local_driver_20261120_v1/driver_library.spice)

O recorte de 36 MOS, 493 resistores e 968 capacitores e os estímulos de fronteira foram copiados byte a byte. A fonte ideal entre `rc8562` e `sclk_driver` deu lugar ao driver. R87 e a rede a jusante ficaram intactos. O deck mudou apenas para gravar sondas adicionais. O controle e o contraste de referência foram verificados por hash e reutilizados. O novo transiente manteve 188–247 ns, incluindo o ciclo 15, TT, 27 °C, Gear e passo máximo de 25 ps. [Recibo do simulador](../build/phase3/sclk_local_driver_20261120_v1/result.json)

Os critérios foram selados antes do transiente. Exigiram um pulso válido por ciclo e ausência de cruzamentos adicionais em 20%, 50% e 80%, deslocamento positivo na ativação a 20% dos três gates e início mais tardio do primeiro intervalo de corrente do tail. A decisão de c15 deveria ser preservada. Em c16/c17, a condição inicial deveria satisfazer o envelope anterior de NTAIL e das quatro sondas SA/SAB, com decisões estáveis em níveis de 20%/80% e D baixo até a captura. Na recuperação, a descida SCLK20 deveria anteceder o primeiro gate local de pré-carga em queda a 80%, sem interseção entre os intervalos de `abs(Id) > 1 µA` de tail e pré-carga/equalizador. A carga líquida de entrada foi comparada à do ramo substituído como indicador de carregamento. Esses são critérios de bancada. O marcador de corrente permite comparar condução observada e não estabelece um limite elétrico da macro. [Critérios selados](../build/phase3/sclk_local_driver_20261120_v1/manifest.json)

## C. Medições

O ngspice 44.2 concluiu **um** transiente de 59 ns em **13,900 s**, retorno 0 e **14.003 amostras**.

| Métrica | Controle arquivado | Fonte ideal +182 ps | Driver SKY130 |
|---|---|---|---|
| Subida dos três gates, diferença a 20% / 50% / 80% | Referência | +181,46 a +182,52 ps no conjunto | +436,73 a +437,49 / +205,62 a +206,19 / −174,44 a −173,97 ps |
| Descida dos três gates, diferença a 20% / 50% / 80% | Referência | Variação absoluta máxima de 0,48 ps | +4,33 a +4,94 / +104,52 a +105,23 / +184,35 a +184,66 ps |
| Decisão, c16 / c17 | Errada / errada | Correta / correta | **Correta / correta** |
| Estabilidade das saídas do sense antes da captura | 5,261 / 5,243 ns, polaridade errada | 5,051 / 5,053 ns | 5,267 / 5,268 ns |
| D baixo contínuo antes da captura, limite por amostra nativa | Ausente / ausente | 4,766 / 4,770 ns | **4,971 / 4,977 ns** |
| Retorno sustentado de SA e SAB à banda alta | 224,768 / 244,768 ns | 225,002 / 245,000 ns | 224,966 / 244,964 ns |
| Glitches lógicos nas três avaliações | Sem cruzamentos extras | Sem cruzamentos extras | Sem cruzamentos extras |
| Pico de corrente de canal do tail na primeira avaliação | 133,23 / 133,18 µA | 157,85 / 158,30 µA | **326,78 / 325,84 µA** |

A entrada do driver tinha slew20–80 de aproximadamente 652 ps na subida e 199 ps na descida. A saída passou para **40–41 ps** e **19 ps**, respectivamente. A borda de subida começa mais tarde e chega ao nível alto mais cedo que a borda longa original, o que explica o sinal da diferença em 80%. A desativação começa mais tarde e comprime a transição em direção ao nível baixo. Nos gates, o patamar alto ficou próximo de 1,800 V e o módulo do patamar baixo ficou abaixo de 12 µV nas janelas de medição. [Bordas por terminal](../build/phase3/sclk_local_driver_20261120_v1/analysis.json)

| Ciclo | Gate | Δ subida20 / 50 / 80 (ps) | Δ descida20 / 50 / 80 (ps) |
|---|---|---|---|
| 16 | Sampler BL | +436,73 / +205,78 / −173,97 | +4,40 / +104,52 / +184,35 |
| 16 | Sampler BLB | +437,27 / +206,04 / −174,35 | +4,89 / +105,18 / +184,54 |
| 16 | Tail | +437,33 / +206,19 / −174,30 | +4,70 / +105,00 / +184,50 |
| 17 | Sampler BL | +436,83 / +205,62 / −174,01 | +4,33 / +104,57 / +184,49 |
| 17 | Sampler BLB | +437,41 / +205,89 / −174,44 | +4,94 / +105,23 / +184,66 |
| 17 | Tail | +437,49 / +206,02 / −174,22 | +4,57 / +105,05 / +184,62 |

A polaridade de c15 foi preservada, com SA alto, SAB baixo e D em 1,80045 V na captura. As diferenças iniciais de NTAIL em c16/c17 foram de +0,041/+0,089 mV. A primeira condução do tail deslocou-se de 214,277/234,278 ns para **214,603/234,602 ns**. Com o driver, BLB−BL no cruzamento SCLK20 foi +700/+713 mV. No primeiro marcador de corrente foi +729/+740 mV, com modo comum de 1,342/1,334 V e SAB−SA de +446/+452 mV nos nós dos samplers. Em ambos os ciclos, a decisão passou para SA baixo e SAB alto, com D perto de 0,20 mV na captura. [Estados inicial e final](../build/phase3/sclk_local_driver_20261120_v1/analysis.json)

A descida SCLK20 do tail antecedeu o primeiro gate local de pré-carga a 80% em 68,4/69,9/69,4 ps nos ciclos 15, 16 e 17. Em c16/c17, a última corrente de tail acima de 1 µA terminou em **224,270/244,270 ns**. A primeira corrente de pré-carga acima do mesmo marcador começou em **224,382/244,380 ns**. Não houve interseção dos intervalos medidos em nenhum dos três ciclos. A evidência distingue o comando de pré-carga, os gates locais e a corrente de canal. [Medição de corrente](../build/phase3/sclk_local_driver_20261120_v1/supplemental.json) · [Janelas e correntes por dispositivo](../build/phase3/sclk_local_driver_20261120_v1/analysis.json)

A carga líquida na entrada do driver, integrada na janela de subida de cada leitura, foi **6,94 fC**, diante de **13,45 fC** no ramo R87 do controle. O pico de corrente da entrada foi 10,4 µA, frente a 19,7–19,8 µA em R87. O pico de alimentação do driver foi cerca de **272 µA** e a energia por pulso, integrada na janela de 16 ns incluindo subida e descida, foi **70,4–70,5 fJ**. A corrente de alimentação inclui carregamento, condução simultânea e fuga. O ensaio não isolou a parcela de curto-circuito. [Carregamento e energia](../build/phase3/sclk_local_driver_20261120_v1/analysis.json)

## D. Parecer e transposição

O candidato reproduziu a correção com dispositivos reais e cumpriu o critério de desativação no recorte. A carga da entrada apareceu menor do que a do ramo substituído para esse estímulo. O risco principal de integração é a interação da borda mais forte e do pico de corrente do tail, cerca de **2,45×** o controle, com a distribuição real de SCLK e de alimentação. Os controles de fronteira permaneceram iguais por construção, e a maior diferença nas tensões externas sondadas foi 0,54 µV. A fonte de replay em `rc8562` impede que a bancada meça a realimentação do driver sobre o SCLK dos outros sete senses, a WL ou a pré-carga compartilhada. [Limitações do recorte](phase3_isolamento_causal_sense3_tt_20261120.md) · [Impacto dos controles no contraste em macro](phase3_contraste_completo_sclk_tt_20261120.md)

A inserção física poderia ligar o SCLK compartilhado à entrada de um estágio situado junto à coluna 3 e segregar a saída que alimenta os três gates locais a jusante da região de R87. São necessários o segmento local de saída, o nó MID e acesso a alimentação/bulk. A lógica de pré-carga pode manter seu controle direto. Acoplamentos e o efeito sobre o tap continuam para verificação. A `inv_4` ocupa **6,256 µm²** segundo o LEF instalado. A área total inclui o inversor assimétrico, poços, taps e roteamento ainda sem layout. Replicar a célula de saída em oito colunas ocuparia **50,048 µm²** antes desses itens. Uma prova na coluna 3 é diagnóstica. Uma política por coluna dependeria da distribuição de margens e cargas do array.

Em SS, mudanças de slew e corrente podem atrasar a regeneração e reduzir margem de captura. Em FF, a avaliação pode antecipar-se e a separação até a pré-carga pode mudar. Os resultados aqui são TT a 1,8 V e 27 °C. A robustez depende do comportamento da rede carregada.

**Próximo passo mínimo:** modelar a inserção do mesmo driver num recorte carregado que retenha o `sense_drive`, os outros sete ramos de SCLK, os acoplamentos relevantes e a rede de pré-carga. Comparar uma única inserção na coluna 3 contra o controle no mesmo recorte antes de propor edição física. O critério é manter a correção e a desativação local, sem perturbação funcional mensurável nos ramos compartilhados.

| Estado histórico | Veredito |
|---|---|
| Macro original em TT | `FAIL` |
| Contraste ideal reduzido | `CORROBORATED` |
| Contraste R87 na macro | `PASS` funcional experimental |
| Macro física com o novo driver | Ainda não demonstrada |
| Monte Carlo esquemático | 200 Hold e 206 Read válidas no domínio experimental |
| Qualificação geral | `NOT_CHARACTERIZED` |

## E. Reprodução e integridade

O runner verifica por hash o recorte, o replay, os recibos do controle e do contraste e a biblioteca instalada. Os resultados, incluindo o gráfico, ficam em `build/phase3/sclk_local_driver_20261120_v1/`. Os **19 testes de software** passaram, com cinco novos testes para pinagem, instrumentação, glitches, sobreposição e classificação, e 14 regressões do isolamento e pré-condicionamento. [Testes](../build/phase3/sclk_local_driver_20261120_v1/tests.log)

```bash
out=build/phase3/sclk_local_driver_reproduction
script=tools/phase3_sclk_local_driver.py
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" prepare --output "$out"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" simulate --output "$out"
PYTHONDONTWRITEBYTECODE=1 python3 "$script" analyze --output "$out"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sclk_local_driver.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sense3*.py' -v
```

O repositório continua na branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. Foram acrescentados o netlist experimental, o runner, os testes e este relatório. As mudanças permanecem locais. O arquivo `SHA256SUMS` do ZIP registra todos os arquivos entregues. [Manifesto](../build/phase3/sclk_local_driver_20261120_v1/manifest.json) · [Recibo](../build/phase3/sclk_local_driver_20261120_v1/result.json)
