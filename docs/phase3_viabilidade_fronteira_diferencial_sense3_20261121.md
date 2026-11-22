# Fase 3 — Viabilidade física da antecipação diferencial no sense 3

**`NO_DEFENSIBLE_BOUNDARY` para a intervenção de 182 ps na coluna 3 e com o replay disponível.** Dos 12 pares físicos da rede BL/BLB, apenas o acesso da linha 3 e os terminais dos samplers têm séries TT arquivadas nos pontos exatos. A trajetória calculada nesses pares excede materialmente as excursões observadas. Impô-la alteraria a impedância de entrada e a troca de carga com o circuito. As demais fronteiras têm caminho físico rastreável e trajetória `NOT_OBSERVED`. O resultado limita a viabilidade do experimento com a evidência atual. A possibilidade física de gerar um diferencial mais cedo por outros meios continua em aberto. [Manifesto](../build/phase3/sense3_diff_boundary_20261121/manifest.json)

## Caminho físico

A referência é a macro C sem intervenção, no ensaio reduzido TT de 250 ns, 1,8 V, 27 °C, carga de 10 fF/bit e passo máximo de 25 ps. A análise conferiu o hash do PEX `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`, o binding renomeado, as sondas, o waveform e a autorização histórica do controle de 59 ns. A comparação temporal usa o relógio absoluto do ensaio de 250 ns, ao qual corresponde a janela 188–247 ns do recorte. [Preflight TT](../build/phase3/data3_tt_20261120/preflight.json) · [Gate do recorte](../build/phase3/sense3_preconditioned_20261120/control_gate.json)

- **BL** — os sufixos abaixo pertencem a `macro_core.array_and_peripherals.write_driver_3.BL`. Acesso da linha 3 `X1592` em `.t0` (`rc8202`), junções de distribuição `.n0/.n1/.n2` (`rc8199/rc8200/rc8201`), sampler PMOS `X235` em `.t8` (`rc8210`). Caminho resistivo mínimo `R411` 239,543 Ω, `R413` 14,725 Ω e `R420` 296,067 Ω.
- **BLB** — sufixos do par `write_driver_3.BLB`. Acesso da linha 3 `X663` em `.t2` (`rc8216`), junções `.n0/.n1/.n2` (`rc8211/rc8212/rc8213`), sampler PMOS `X521` em `.t8` (`rc8222`). Caminho mínimo `R397` 239,482 Ω, `R399` 14,718 Ω e `R406` 291,538 Ω.
- **Dispositivos ativos** — os gates de acesso da linha 3 são `rc7944/rc7945` (WL). Os nós internos da célula são `rc6960/rc6955`. Os PMOS `X1352/X1645` pré-carregam as linhas e `X374` as equaliza. Os ramos de escrita conectam-se por `X1619/X323` a BL e `X442/X1081` a BLB. Os oito transistores de acesso das quatro linhas estão no PEX e foram omitidos no recorte. VPORT0/VPORT1 repõem a tensão medida nos terminais da linha 3, com a pré-carga, o equalizador e o write driver locais ainda ativos no recorte.
- **Rede passiva** — 28 resistores e 87 capacitores não nulos incidentes na coluna foram preservados com os mesmos valores. O PEX inclui seis cartões de capacitância nula adicionais. Os caminhos mínimos acima somam 550,335 Ω e 545,738 Ω. A resistência DC equivalente da malha retida vale 475,614 Ω e 475,582 Ω devido aos caminhos paralelos. Ela descreve o percurso passivo entre o replay e o sampler. A impedância incremental da célula, o acoplamento às redes externas e a realimentação do array exigem outros dados. [Inventário de cartões](../build/phase3/sense3_diff_boundary_20261121/column_cards.csv) · [Cálculo histórico de resistência](../build/phase3/sense3_isolation_20261120/passive_bl_impedance.json)

`C896` liga as duas junções centrais com **15,988 fF**. Nelas também se concentram os acoplamentos a VDD (`C949/C924`, 7,987/12,534 fF), VSS (`C11998/C12011`, 6,154/6,082 fF), SCLK (`C144/C143`, 1,108/0,899 fF) e PRECH (`C381/C380`, 1,027/0,629 fF). Os acoplamentos extraídos aos ramos das quatro WLs somam 3,104 fF. Há ainda placas ligadas aos nós internos do write driver, do latch, de células e de colunas vizinhas. Esses caminhos, junto às capacitâncias dos MOS, permitem redistribuição de carga durante comutações. O evento de c16 cruza 1,8 V no acesso BLB cerca de 0,38 ns antes de PRECH atingir 0,9 V no ponto arquivado e antes da subida de WL. A contribuição de cada caminho para o pico fica indeterminada sem as correntes ou as tensões em ambas as placas relevantes. [PEX e inventário R/C](../build/phase3/sense3_diff_boundary_20261121/column_cards.csv)

## Fronteiras examinadas

| Candidato | Nós BL / BLB | Menor caminho até sampler, Ω | Waveform TT no ponto | Origem e risco de idealização |
|---|---|---:|---|---|
| Acesso linha 3 | `rc8202 / rc8216` | 550 / 546 | Observado | Descarga pela célula via WL e reação da coluna. VPORT impõe a tensão e substitui a resposta de carga da célula e do array |
| Acessos linhas 0, 1, 2 | `rc8203 / rc8217`, `rc8204 / rc8218`, `rc8205 / rc8219` | 567 / 563, 547 / 542, 549 / 545 | `NOT_OBSERVED` | Ramais de outras células. Fixar esses nós imporia um caminho artificial à rede mesmo durante a leitura da linha 3 |
| Junções do array `.n0` | `rc8199 / rc8211` | 311 / 306 | `NOT_OBSERVED` | Ramificação das quatro linhas. Fixá-la absorveria a variação de carga do array |
| Junções acopladas `.n1` | `rc8200 / rc8212` | 296 / 292 | `NOT_OBSERVED` | Placas de C896 e acoplamentos de controle. Impor tensão nessas placas substituiria a resposta da rede às comutações |
| Junções de escrita `.n2` | `rc8201 / rc8213` | 308 / 304 | `NOT_OBSERVED` | Ligação ao write driver e caminho paralelo ao sense. Fixá-la introduziria acionamento na leitura |
| PMOS/NMOS de escrita | `rc8206 / rc8215`, `rc8207 / rc8214` | 512 / 509, 410 / 406 | `NOT_OBSERVED` | Terminais dos drivers existentes. A tensão calculada exigiria um modelo ativo de acionamento e de retorno de carga |
| Pré-carga/equalização | `rc8208 / rc8220`, `rc8209 / rc8221` | 409 / 404, 409 / 405 | `NOT_OBSERVED` | Terminais dos PMOS de pré-carga e equalização. Fixá-los mudaria a rede de carga inicial e a liberação de PRECH |
| Terminais dos samplers | `rc8210 / rc8222` | 0 / 0 | Observado | Resposta da malha sob carga do sense. Uma fonte ideal eliminaria a impedância vista pelos samplers, o acoplamento de retorno e a filtragem do percurso |

Os dois pares observados pertencem à mesma coluna distribuída, ligada à célula selecionada e aos transistores de pré-carga, escrita e amostragem. As junções intermediárias oferecem caminhos resistivos mais curtos, mas continuam dentro dessa rede. As sondas de WL, PRECH e SCLK ajudam a interpretar as fases. Uma forma de onda em outro tap, ainda que da mesma rede resistiva, seria um proxy. Os dez pares sem observação ficaram sem trajetória, modo comum ou pico estimados. [Nós originais, caminhos e medições por par](../build/phase3/sense3_diff_boundary_20261121/manifest.json)

## Trajetória observada e antecipação calculada

Nos dois pares observados, a reconstrução usa `Δ'(t) = Δ(t + 182 ps)` e aplica `±Δ'/2` ao modo comum original. O valor de 182 ps vem do contraste de subida de SCLK anterior. Foram usados os pontos nativos e deslocados da macro de 250 ns, por interpolação linear. Por isso, os números no mesmo marcador são ligeiramente diferentes dos calculados antes com o replay compactado e o SCLK do recorte.

| Par e ciclo | SCLK20 local, ns | CM histórico, V | Δ histórico → alvo, mV | BL histórica → calculada, V | BLB histórica → calculada, V | Pico BLB histórico → calculado, V |
|---|---:|---:|---:|---:|---:|---:|
| Acesso c16 | 214,153 | 1,860 | +37 → +290 | 1,841 → 1,715 | 1,879 → 2,005 | 1,879 → 2,018 |
| Acesso c17 | 234,153 | 1,856 | +45 → +301 | 1,833 → 1,705 | 1,878 → 2,006 | 1,878 → 2,017 |
| Samplers c16 | 214,153 | 1,873 | +15 → +234 | 1,865 → 1,756 | 1,880 → 1,990 | 1,881 → 2,018 |
| Samplers c17 | 234,153 | 1,870 | +20 → +245 | 1,860 → 1,747 | 1,880 → 1,992 | 1,880 → 2,017 |

A expressão antecipada é contínua ao longo do intervalo interpolado. Uma junção instantânea com o histórico no início da janela inicial de SCLK20 introduziria um degrau em BLB de aproximadamente 105/109 mV no acesso ou 80/84 mV nos samplers, com degrau oposto em BL. Nas junções de 211/219 ns e 231/239 ns, todos os degraus calculados têm módulo inferior a 0,12 mV. Uma transição contínua fora da avaliação pode tratar a junção matemática. A questão física é de onde viriam a carga adicional em BLB e a retirada simultânea em BL. Os dispositivos e estímulos originais produziram a trajetória histórica. Um equivalente de tensão e impedância, com corrente e acoplamento verificáveis, seria necessário para defender uma trajetória diferente sem mascarar a dinâmica. [Séries e junções](../build/phase3/sense3_diff_boundary_20261121/observed_and_calculated.csv)

### Domínio dos modelos

A excursão original acima dos 1,8 V é parte do waveform da macro, até **+81 mV** em BLB nos samplers. Os picos acima de 2 V são resultados algébricos do alvo, cerca de **+137 a +139 mV sobre os picos originais**. A documentação SKY130 para os MOS padrão de 1,8 V delimita as **diferenças entre terminais** de validade do modelo. Para NMOS, (V_{DS}) e (V_{GS}) vão de 0 a 1,95 V e (V_{BS}) de −1,95 a +0,30 V. Para PMOS, as faixas são −1,95 a 0 V e −0,10 a +1,95 V, respectivamente. Esses domínios de modelo não qualificam confiabilidade nem definem um limite absoluto de tensão de nó. Os terminais e condições de corpo do circuito alterado teriam de ser avaliados. O PEX mapeia os terminais físicos, mas o contraste calculado não fornece os novos potenciais locais, a corrente das junções ou a duração de eventual polarização fora do domínio. [SkyWater SKY130 PDK, Device Details](https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html)

## Decisão

1. **Fronteira.** Nenhuma fronteira examinada sustenta a intervenção específica com a evidência disponível. Os taps intermediários permanecem inconclusivos quanto à sua trajetória física.
2. **Impedância.** A malha passiva entre o replay e os samplers pode ser preservada. Uma fonte ideal fixa o nó em que é inserida e altera a resposta incremental. Falta um equivalente dinâmico que preserve as correntes de carga e a retroalimentação do array.
3. **Plausibilidade dos 182 ps.** O alvo é matematicamente consistente. A energia e a sincronização necessárias para produzi-lo com a célula, a pré-carga, a escrita e SCLK originais ficaram sem demonstração. A excursão histórica acima de VDD é compatível com acoplamentos e não justifica reproduzir os picos calculados por imposição.
4. **Isolamento.** A simetria das fontes preservaria o modo comum no ponto impostado. Impedâncias e acoplamentos distintos podem convertê-la em mudança de modo comum nos samplers. O controle c15 permanece representativo com o deck histórico. Mudar a fronteira alteraria sua carga mesmo antes da intervenção e exigiria revalidação. Uma correção em c16 pode mudar naturalmente a condição inicial de c17.
5. **Prioridade para o Marco 3.** Encerrar a antecipação artificial de BLB−BL neste recorte. Medir e justificar um novo equivalente de fronteira custaria outro ciclo de investigação. Já existe evidência causal da temporização local de SCLK no recorte validado.

**Próxima tarefa única** — preparar, em outra rodada, um contraste reduzido que desloque somente a subida no ramo `R76` para `rc8585`, gate do tail `X351`. Manter a descida do tail, os gates dos samplers nos ramos `R68` e `R60`, o replay BL/BLB, os demais controles e o predecessor c15. O critério é verificar o atraso efetivo do tail, conferir a equivalência das bordas dos samplers e comparar o instante da inversão de SAB−SA e o valor sustentado em D até a captura, usando c16 como primeira avaliação causal. O contraste histórico deslocou os três gates juntos. Esse ensaio futuro testaria se o tail sozinho é suficiente, com c17 interpretado à luz da decisão de c16. [Contraste temporal histórico](phase3_precondicionamento_sense3_tt_20261120.md)

## Preservação e reprodução

Zero simulações, zero mudanças no circuito e nenhuma nova fonte. C segue como referência de integração, com `FAIL` TT e `PASS` SS no escopo ensaiado. Contraste diferencial `NOT_RUN`, suficiência `INCONCLUSIVE`, B′ inconclusivo em c16/c17 e driver v1 em espera. Monte Carlo experimental preservado e qualificação geral `NOT_CHARACTERIZED`. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.

```sh
out=$(mktemp -d build/phase3/sense3_diff_boundary_check.XXXXXX)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 tools/audit_phase3_sense3_diff_boundary.py "$out"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest discover -s tests -p test_phase3_sense3_diff_boundary.py -v
```

Os dois testes verificam a reconstrução de modo comum, o cálculo da junção, o mapeamento no arquivo de origem e a cobertura das sondas. O manifesto e os CSVs são gerados localmente. O ZIP inclui a referência bruta, o PEX e os recibos de integridade.
