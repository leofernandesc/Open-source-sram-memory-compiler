# Fase 3 — Contraste de SCLK em TT e Monte Carlo nominal

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
[Especificação técnica](../specs/technical_specification.md) · [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Contrato de caracterização](phase3_characterization_contract.md)

## A. Contraste de SCLK

### Hipótese e intervenção selada antes do SPICE

O TT reduzido de referência, com 250 ns e waveform SHA-256
`7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646`,
gravou e reteve zero na célula da linha 3, coluna 3. Nos dois reads,
BLB−BL adquiriu a polaridade esperada, mas o latch resolveu para 1
e a palavra lida foi `0xF8`. Em c16/c17 a inversão ocorreu
425/436 ps depois do SCLK20 local do sampler, com VGS do tail
de aproximadamente 1,164/1,177 V. O dado estava errado antes
da captura. [Diagnóstico da referência](phase3_data3_tt_snm_piloto_20261120.md)

Escolhemos um **atraso único de 182 ps na ativação do SCLK
do sense 3**. O critério, registrado antes da tentativa, foi
repor em TT o intervalo WL80→SCLK20 observado nos dois reads
corretos em SS. Os pontos de WL em SS são as sondas arquivadas
da linha. Em TT são o gate do acesso BL da célula. SCLK20 em
SS usa o sampler BL arquivado e, em TT, o tail local. Assim,
esses intervalos orientam o contraste e não definem um
orçamento de projeto. Os crossings não são limiares físicos
de condução do PMOS ou do tail.

| Ciclo de origem | Tail20−WL80 em TT (ps) | Sampler20−WL80 em SS (ps) | Atraso para igualar a referência relativa (ps) | Tempo de tail20 planejado até captura em TT (ns) |
|---|---:|---:|---:|---:|
| c16 | −62,77 | +114,36 | 177,13 | 5,723 |
| c17 | −56,38 | +125,57 | 181,96 | 5,724 |

O maior atraso foi arredondado ao picosegundo superior. Na
trajetória original, BLB−BL era +15,1/+19,9 mV no tail20 e
chegava a cerca de +234/+245 mV no instante planejado.
A trajetória original já incorpora a interação com o latch,
então esses valores são uma referência para escolha e não
uma previsão do BL sob a intervenção. Nenhum limiar externo
de 200 mV foi imposto.
[Preflight com medições e escolha](../build/phase3/sclk_tt_contrast_run_20261120/preflight.json)

### Implementação de bancada e condições

O recorte preserva **a mesma sequência de 250 ns**, incluindo
partida, seis escritas e quatro reads, GDS, PEX padrão,
binding, modelos `tt`, 1,8 V, 27 °C, 10 fF/bit e clock de
20 ns. O simulador instalado é ngspice 44.2/KLU. O deck
externo difere apenas no include do adaptador. O binding
original foi preservado byte a byte.

| Identidade física | SHA-256 |
|---|---|
| GDS | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |

O adaptador de fixture atua nas três terminações
locais de SCLK do sense 3, nos dois samplers e no tail.
Mantém todos os MOS, terminais e valores de R/C do binding.
Insere fontes ideais em série com os resistores de acesso
das três terminações e, durante o pulso de prova, reproduz
as amostras nativas de cada gate transladadas em 182 ps.
As fontes comandam 0 V em série fora de duas janelas
de intervenção, 211–219 ns e 231–239 ns. O retorno
ao acionamento original foi programado no platô alto,
antes da descida. A intenção é deslocar a ativação,
preservar forma e amplitude no gate, encurtar a fase ativa
em aproximadamente 182 ps e manter a desativação original.
A reprodução ideal precisa ser verificada no waveform da
tentativa. Sua impedância ativa de comando é uma limitação
na transposição para uma solução física. O teste é local
ao sense 3. Ele não modela atraso global de todos os senses.

```bash
run=build/phase3/sclk_tt_contrast_run_20261120
timeout 90s env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/run_phase3_sclk_contrast.py prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/run_phase3_sclk_contrast.py simulate --output "$run" --timeout 2100
```

### Resultado — INCONCLUSIVO

Houve uma única tentativa. Foi encerrada por SIGTERM após
**14 min 57 s** por custo desproporcional. O avanço registrado
era de **0,324629 ns**, ainda dentro da rampa de VDD da
partida. A primeira intervenção começaria em 211 ns. O limite
configurado de 35 min não foi atingido. Não houve caso
completo nem waveform de saída, que o deck escreve ao fim
do transiente. O wrapper registrou `ERROR` e código −15 do
processo. O recibo separado registra a interrupção e seu
motivo. [Log ngspice](../build/phase3/sclk_tt_contrast_run_20261120/ngspice.log) · [Recibo](../build/phase3/sclk_tt_contrast_run_20261120/simulation.json) · [Interrupção](../build/phase3/sclk_tt_contrast_run_20261120/operator_stop.json)

Os avisos iniciais de matriz singular em `xdut.rc7913` e
as tentativas de gmin/source stepping também estão no log
da referência. Ambos chegaram a concluir o ponto de operação
transiente. O fato novo é a progressão muito lenta do
transiente instrumentado, ainda com as fontes de série
comandadas em zero. A formulação numérica da fixture é uma
suspeita. O log não identifica exatamente a causa da lentidão.

| Verificação | Referência TT | Contraste |
|---|---|---|
| Bitcell armazenou e reteve zero | Verificado | Sem evidência nova |
| BLB−BL esperado antes e durante a rampa | Verificado na referência temporal, com diferencial inicialmente pequeno | Evento não alcançado |
| Latch deixou de inverter | Inversão confirmada | Evento não alcançado |
| Word readback c16/c17 | `0xF8/0xF8` | Sem medição |
| Estabilização de sense/D antes de capturar o zero | Ausente | Sem medição |
| Predecessores c14/c15 | `0xAA/0x0F` | Sem medição |
| Desativação, pré-carga e fase seguinte | Registradas na referência | Sem medição |

**A antecipação da avaliação ainda não é uma causa demonstrada.**
O diagnóstico anterior da regeneração incorreta continua
válido. Esta tentativa só verificou o preparo do contraste e
expôs o custo numérico da instrumentação. Nenhuma segunda
simulação foi feita.

## B. Monte Carlo de SNM

O preflight revalidou os quatro checkpoints de Hold e os
quatro de Read, junto às repetições de controle já arquivadas.
Cada campanha predeclara 220 seeds. A folha canônica tem
seis MOS, com ambos os acessos presentes. WL=0 em Hold e
WL=1,8 V em Read, com BL e BLB em 1,8 V e DC de 1 mV.
`tt_mm` usa o contínuo SKY130A Volare
`0fe599b2afb6708d281543108caf8310912f54af`,
`MC_MM_SWITCH=1`, `MC_PR_SWITCH=0` e 27 °C experimental.
O manifesto fixa os hashes da folha, scripts e fechamento
do PDK. O pipeline revalida os dois lóbulos e a seed do log
com a VTC de cada ponto. O resultado experimental conta
zeros físicos e preserva erros numéricos separadamente.
As repetições e as séries antigas em `sf_mm` ficam fora
da contagem. [Preflight do lote](../build/phase3/snm_campaign_200_20261120/preflight.json)

### Resultado — meta experimental atingida

| Cobertura | Hold | Read |
|---|---:|---:|
| Seeds tentadas, sem contar a repetição arquivada | 200 | 206 |
| Seeds distintas válidas | **200** | **200** |
| Válidas retomadas do piloto / novas | 4 / 196 | 4 / 196 |
| Erros numéricos de extração | 0 | 6 |
| Falhas de convergência DC ou timeouts | 0 | 0 |
| SNM físico zero | 0 | 0 |
| Seeds predeclaradas não executadas | 20 | 14 |

Foram feitas 398 novas tentativas em nove lotes, cada um
com até 50 casos e timeout individual de 15 s. O tempo
somado dos lotes foi cerca de 7 min 40 s. Os checkpoints
chegaram a 200 medidas por modo sem repetir seeds válidas.
O manifest de cada modo e os hashes dos primeiros quatro
decks, traços e logs continuam iguais aos do preflight.
As duas repetições anteriores permanecem arquivadas fora
da contagem. [Journal dos lotes](../build/phase3/snm_campaign_200_20261120/batches.jsonl) · [Checkpoints finais](../build/phase3/snm_campaign_200_20261120/checkpoints.json)

| Estatística, mV | Hold | Read |
|---|---:|---:|
| Média | 684,740 | 409,961 |
| Desvio-padrão amostral | 8,473 | 10,690 |
| Mediana | 685,271 | 410,573 |
| Mínimo | 655,439 | 381,598 |
| Máximo | 701,742 | 439,523 |
| P05 | 669,142 | 392,397 |
| P25 | 680,332 | 402,553 |
| P75 | 689,629 | 416,791 |
| P95 | 697,775 | 426,198 |
| IC 95% da média | 683,568–685,909 | 408,505–411,441 |

O IC usa bootstrap percentil, 10.000 reamostragens e
seed 20261120. As estatísticas descrevem as medidas
válidas no ponto experimental e, em Read, são condicionais
à resolução do extrator. A meta de 0,4 V do ensaio
determinístico não foi aplicada às amostras de Monte Carlo.
Esses ICs não medem taxa de falha ou rendimento industrial.
[Estatísticas Hold](../build/phase3/snm_campaign_results_20261120/hold/summary.json) · [Estatísticas Read](../build/phase3/snm_campaign_results_20261120/read/summary.json)

As 400 VTCs foram relidas dos checkpoints verificados,
recalculadas e confrontadas com o deck e a seed do log.
Em cada modo existem 200 hashes de waveform distintos.
Os extremos foram conferidos diretamente com suas
curvas de 1.801 pontos, mantendo os dois lóbulos e o
menor lado em cada caso. O ponto representativo mais
próximo da mediana foi incluído na figura.

| Modo | Extremo | Seed | Lóbulos (mV) | SNM (mV) |
|---|---|---:|---|---:|
| Hold | Mínimo | 20057 | 655,439 / 707,106 | 655,439 |
| Hold | Máximo | 20185 | 701,742 / 706,739 | 701,742 |
| Read | Mínimo | 30009 | 450,330 / 381,598 | 381,598 |
| Read | Máximo | 30033 | 439,523 / 447,764 | 439,523 |

[Histograma Hold](../build/phase3/snm_campaign_results_20261120/hold/snm.png) · [Borboletas Hold](../build/phase3/snm_campaign_results_20261120/hold/butterflies.png) · [CSV Hold](../build/phase3/snm_campaign_results_20261120/hold/samples.csv) · [Histograma Read](../build/phase3/snm_campaign_results_20261120/read/snm.png) · [Borboletas Read](../build/phase3/snm_campaign_results_20261120/read/butterflies.png) · [CSV Read](../build/phase3/snm_campaign_results_20261120/read/samples.csv)

As seis rejeições de Read ocorreram nas seeds 30005,
30021, 30053, 30090, 30148 e 30192. Todas produziram
1.801 linhas e terminaram a DC com código 0. O extrator
achou ambiguidade no sinal do diferencial numa extremidade
do domínio rotacionado. Em cada VTC rejeitada, um extremo
teve módulo de aproximadamente 0,085–0,099 µV, dentro do
epsilon de 0,1 µV. As VTCs intocadas exibem três mudanças
de sinal se o epsilon for ignorado. Isso sugere sensibilidade
numérica e requer um tratamento de precisão validado antes
de incluir essas amostras. Nenhuma foi registrada como SNM
zero, nem foi repetida. [Rejeições auditadas](../build/phase3/snm_campaign_results_20261120/invalid_trace_diagnostics.json)

```bash
# Partindo da cópia arquivada do piloto com quatro checkpoints por modo.
journal=build/phase3/snm_campaign_200_20261120
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/complete_phase3_snm.py preflight --output "$journal"
# Este comando exige o recibo terminal da única tentativa de contraste TT.
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 1 \
  python3 tools/complete_phase3_snm.py advance --output "$journal" --budget 1100 --timeout 15
# Com os checkpoints completos também é possível executar somente este export.
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/complete_phase3_snm.py export --output build/phase3/snm_campaign_results_20261120
```

**Conclusão estatística.** O tamanho amostral foi obtido
para a folha 6T esquemática em `tt_mm`, 1,8 V e 27 °C
experimental. A qualificação final depende da confirmação
do domínio e do tratamento das rejeições numéricas. Os
arrays físicos e os demais pontos de operação da
especificação ainda exigem caracterização própria.

## C. Decisão de engenharia

**Próxima execução recomendada.** Fazer um contraste isolado
em TT com uma instrumentação mais simples no ramo exclusivo
de SCLK, mantendo a referência de 182 ps e a verificação
da forma realmente entregue aos gates. A primeira opção
é um único estímulo de deslocamento no ramo dedicado antes
da distribuição, sem as três restrições comportamentais
autorreferentes na vizinhança do latch. No grafo resistivo
do PEX, `R80` (94,993 Ω) é a aresta entre a saída do
driver e a rede de distribuição aos 24 terminais de SCLK.
É um ponto candidato para a fixture. O tap 80 alimenta
tanto `sense_drive` quanto `precharge_phase` no Verilog
roteado. Alterar o tap compartilhado misturaria alterações
de pré-carga com o teste de temporização. O critério de
conclusão permanece a palavra `0xF0` nos dois reads com
armazenamento correto, sense/D sustentados antes da captura,
predecessores corretos e retorno à pré-carga. Essa execução
fica para outra rodada. [Verilog da candidata](../build/phase3/danilo_ss_ff2_spaced_route/routed.v)

O mecanismo concorrente mais promissor a observar no mesmo
contraste é a transferência de diferencial enquanto os PMOS
amostram e o tail começa a conduzir. Na referência TT, a
polaridade correta chega às bitlines e aparece no latch,
depois a polaridade do latch inverte. Se maior antecedência do
diferencial com SCLK deslocado preservar esse erro, a próxima
linha de investigação é o balanceamento de parasitas, offset
efetivo e injeção de carga no fechamento dos samplers.
Não há evidência atual para escolher um ECO físico. Uma
eventual mudança de SCLK precisa demonstrar margem para D
na fase alta, recuperação na fase baixa e impacto sobre
período mínimo, área e energia, com a mesma revisão em
TT/SS/FF.

FF integrado, caracterização elétrica da candidata, setup/hold,
potência e Liberty permanecem pendentes. O resultado geral é
`NOT_CHARACTERIZED`. A campanha esquemática de SNM e a definição
do domínio estatístico para os arrays físicos são atividades
distintas.

Passaram **37 testes de software** pertinentes, cinco deles
novos. O ZIP contém o preparo e o log do único contraste, o
recibo da interrupção, as duas campanhas com os decks, VTCs,
logs e hashes, os resultados e os testes. O checkout local
permanece na branch acima, sem commit, merge ou push.

Para recriar também o preparo de SCLK offline, restaure os
arquivos anteriores dos ZIPs
`phase3_validacao_integrada_ss_20261119.zip`,
`phase3_fechamento_barramento_ss_20261120.zip`,
`phase3_tt_snm_20261120.zip` e
`phase3_data3_tt_snm_piloto_20261120.zip` sobre o checkout
de referência. Para reproduzir os lotes elétricos desde o
piloto, use os checkpoints originais de quatro amostras por
modo. O novo ZIP contém os checkpoints completos para export
e auditoria offline, sem novas execuções de SPICE.
