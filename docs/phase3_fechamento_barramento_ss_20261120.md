# Fase 3 — Fechamento da propriedade de DATA em SS

**Resultado revisado: PASS funcional no escopo ensaiado.** O replay do
waveform confirma propriedade em 18/18 ciclos, inclusive 8, 10 e 12.
O ensaio de 18 ciclos contém nove leituras corretas e estáveis e seis
escritas confirmadas por readback nas quatro linhas. A qualificação
elétrica geral permanece **`NOT_CHARACTERIZED`**.

## 1. Evidências e critérios físicos

O replay usou a geometria espaçada da integração do ECO de Danilo, na
branch `integration/phase3-danilo-ss`, HEAD
`8e1d961d65054b59f9032ed5f9338d9ee4353c33`. O transiente arquivado de
370 ns em SS foi executado com ngspice 44.2, SKY130A, 1,8 V, 27 °C,
10 fF/bit, período de 20 ns, slew de 50 ps e passo máximo de 25 ps.
O waveform tem 20.539 amostras. Os três waveforms e os artefatos pinados
da preparação foram conferidos antes da análise. O JSON de revisão
registra hashes, condições, janelas e evidências por bit. [Relatório original](phase3_validacao_integrada_ss_20261119.md)

| Entrada | SHA-256 |
|---|---|
| GDS | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Waveform integrado | `692e2218366c4d1797e53c9ee9924895e2e23eda54e3d22765f75b5ed24de44f` |
| Recibo funcional histórico | `5c255b74dddcb2eda97a03c8573f58dc91f348fbd172c07d6ed6b557bbf5c31c` |
| Waveform do controle 300 ps | `60a6b64d58c0d63a2b1b9e49293d7d8c5b2f0942406f28e3912b82258db58f0f` |
| Waveform do controle 1,5 ns | `6077961508645cc2c3c9915707a5161a00f23d1c19631bc3f087c5188ea6c29a` |

A especificação requer que o host tome DATA só depois da liberação real
pela SRAM, e que o host esteja desconectado para leitura. Os limites
públicos de enable, disable e turnaround continuam pendentes. As guardas
de 300 ps e 1,5 ns pertencem à bancada. A tensão em DATA sem carga de
prova, por si só, pode ser a tensão retida pela capacitância. [Especificação](../specs/technical_specification.md) · [Contrato temporal, §6](../specs/sram_4x8_timing_contract.md#6-troca-de-direção-do-barramento)

| Estado | Evidência exigida pelo observador |
|---|---|
| Condução sustentada | Host forte aberto. Sonda de 1 kΩ aplicando o complemento da palavra retida. `TE_B ≤ 0,36 V`. Sonda e SRAM com correntes opostas e corretas para o bit, ambas ≥50 µA em módulo. O pino deve afastar-se ≥50 mV do nível imposto pela sonda, na direção da palavra da SRAM. |
| Alta impedância sob sonda | Host forte aberto, `TE_B ≥ 1,44 V`, pino seguindo o nível lógico da sonda (20/80% de VDD), corrente em módulo ≤50 µA nos ramos da sonda e da SRAM. O limiar conserva o piso da bancada e corresponde a 50 mV em 1 kΩ. Isso comprova liberação no ensaio, com fuga sub-limiar sem caracterização. |
| Intervalo com as duas chaves abertas | `TE_B ≥ 1,44 V` em todos os bits e correntes nos três ramos abaixo do piso. Testemunho entre amostras nativas. Uma descontinuidade de chave ideal não é interpolada para dentro desse intervalo. |
| Oposição de drivers | Host forte fechado, correntes de host e SRAM com sinais opostos e módulos ≥50 µA, com `TE_B` ainda abaixo do limiar de desligamento. A oposição precisa ser sustentada. |
| Resposta compatível com corrente de deslocamento | `TE_B ≥ 1,44 V` e sonda aberta durante a tomada ou troca programada de payload. A corrente nasce junto com a comutação, tem polaridade compatível com carga/descarga pelo host, acompanha a mudança entre níveis do pino e volta ao piso, sem recorrência depois de um intervalo quieto. O pino permanece no nível esperado até o fim da observação. Os ramos medem corrente total do terminal da macro, incluindo PEX. |
| Indeterminado | Falta de sinais, de tempo amostrado ou de correspondência elétrica. Uma corrente com `TE_B` desabilitado e sem recuperação quieta comprovada fica inconclusiva. Um pico isolado e o estado do enable, por si sós, são insuficientes. |

Para provar condução ou liberação, o intervalo contínuo deve chegar ao
evento agendado correspondente. O início informado é a primeira
amostra nativa desse intervalo. São exigidas três amostras nativas e
pelo menos 50 ps até seu fim, equivalentes ao slew programado e a dois
passos máximos. Entre amostras, o observador usa interpolação linear,
com o bracket mantido no JSON. Assim, mudanças separadas por menos do
que a resolução do waveform e níveis abaixo do piso da bancada seguem
sem resolução. O mesmo critério vale para os 18 ciclos. A sondagem
ativa do pino verifica drive e liberação. A validade dos dados em
leitura normal usa os níveis 20/80% e as janelas de dados já verificadas
antes da aplicação da sonda.

Foram usadas as janelas da fixture arquivada. Nas leituras, verifica-se
condução antes de mascarar CSb e liberação até restaurá-lo, assim como
a ausência do host na leitura normal. Na passagem para escrita,
verificam-se a condução após a restauração, a liberação sob sonda,
o intervalo com as chaves abertas e a tomada pelo host forte. Nas
escritas consecutivas, o host continua dono do barramento e somente
muda o payload. O teste forte se estende até os controles da escrita
seguinte ou até a última amostra anterior à abertura programada do host.
Em c12, a observação sob sonda continua até a abertura da sonda antes
da leitura seguinte.

## 2. Ciclos 8, 10 e 12

Tempos em ns. A margem usa a primeira amostra em que os oito pinos
ficaram sustentadamente liberados e a borda inferior do bracket de
fechamento do host. Em c10, host e sonda anterior aplicavam a mesma
palavra. A corrente no fechamento ficou abaixo do piso. A referência
é o cruzamento do controle da chave de bancada, com a sua vizinhança
amostral e as correntes dos ramos registradas.

| Ciclo | Transição | Palavra retida | CSb↓50, restauração | Início da desabilitação / controle 50% | Oito pinos liberados até | Fim da prova sob sonda | Host forte | Margem observada |
|---|---|---|---:|---|---:|---:|---:|---|
| 8 | Leitura → escrita | `0x55` | 164,025 | 167,000 / 167,025 (OEb↑, WEb↓) | 167,731 | 168,428 | 168,528 | ≥0,796 ns |
| 10 | Leitura → escrita | `0x55` | 204,025 | 207,000 / 207,025 (OEb↑, WEb↓) | 207,730 | 208,428 | 208,528 | ≈0,794 ns pelo limite inferior amostral |
| 12 | Leitura → idle | `0xAA` | 244,025 | 247,000 / 247,025 (CSb↑) | 247,662 | 266,528 | Ausente | Liberado antes de CLK↑50 em 250,025 ns e durante todo o idle observado |

As tabelas abaixo usam ponto decimal para os tempos importados. `TE_B20`
é a primeira amostra do trecho contínuo com o gate ≤20% de VDD.
Drive é a primeira amostra da condução sustentada. Duração é a
comprovação mínima desse drive antes do pedido de desabilitação.
O CSV inclui a tensão em DATA e as duas correntes no ponto legado, no
primeiro drive, no pedido de desabilitação e na primeira amostra de
liberação. [Evidência dos 24 pinos](../build/phase3/bus_review_ss_20261120_report/direction_changes_by_bit.csv)

| Ciclo | DATA bit | TE_B20 (ns) | Drive (ns) | Duração (ps) | Corrente da sonda no ponto legado (µA) | Liberação (ns) |
|---|---:|---:|---:|---:|---:|---:|
| 8 | 0 | 166.776 | 166.776 | 224.0 | −220.4 | 167.594 |
| 8 | 1 | 166.776 | 166.926 | 74.0 | 26.8 | 167.706 |
| 8 | 2 | 166.751 | 166.751 | 249.0 | −226.6 | 167.578 |
| 8 | 3 | 166.776 | 166.926 | 74.0 | 14.4 | 167.731 |
| 8 | 4 | 166.751 | 166.751 | 249.0 | −225.4 | 167.578 |
| 8 | 5 | 166.776 | 166.926 | 74.0 | 26.3 | 167.731 |
| 8 | 6 | 166.801 | 166.801 | 199.0 | −207.1 | 167.594 |
| 8 | 7 | 166.776 | 166.926 | 74.0 | 14.4 | 167.731 |
| 10 | 0 | 206.776 | 206.776 | 223.8 | −220.7 | 207.600 |
| 10 | 1 | 206.776 | 206.926 | 73.8 | 27.0 | 207.708 |
| 10 | 2 | 206.751 | 206.751 | 248.8 | −226.9 | 207.568 |
| 10 | 3 | 206.776 | 206.926 | 73.8 | 14.6 | 207.708 |
| 10 | 4 | 206.751 | 206.751 | 248.8 | −225.4 | 207.582 |
| 10 | 5 | 206.776 | 206.926 | 73.8 | 26.8 | 207.708 |
| 10 | 6 | 206.801 | 206.801 | 198.8 | −207.1 | 207.600 |
| 10 | 7 | 206.776 | 206.926 | 73.8 | 14.7 | 207.730 |
| 12 | 0 | 246.775 | 246.925 | 74.9 | 8.1 | 247.637 |
| 12 | 1 | 246.750 | 246.750 | 249.9 | −226.9 | 247.502 |
| 12 | 2 | 246.775 | 246.925 | 74.9 | 38.5 | 247.637 |
| 12 | 3 | 246.775 | 246.775 | 224.9 | −221.8 | 247.518 |
| 12 | 4 | 246.775 | 246.925 | 74.9 | 28.2 | 247.637 |
| 12 | 5 | 246.750 | 246.750 | 249.9 | −225.9 | 247.502 |
| 12 | 6 | 246.800 | 246.948 | 52.3 | 2.7 | 247.662 |
| 12 | 7 | 246.775 | 246.775 | 224.9 | −222.4 | 247.502 |

A primeira divergência observável ocorreu em **166,900 ns**. Os pinos
DATA1/3/5/7 ainda estavam próximos do nível alto da sonda, entre
1,773 e 1,786 V em c8 e c10. O gate já havia habilitado os drivers,
mas a corrente da sonda nesses bits era de 14–27 µA. Em c12 ocorreu
o mesmo com DATA0/2/4/6 em 246,900 ns, com 2,7–38,5 µA. O grupo
acompanha a polaridade do nível retido quando o padrão é invertido.
Isso aponta para recuperação do caminho de saída sob sonda, depois
do enable interno. Nos bits críticos de c12, a condução comprovada
começa até cerca de 150 ps depois do primeiro gate habilitado. As
medições não individualizam o efeito do transistor do driver, da
distribuição dos controles, da resistência de saída e da carga
extraída. O intervalo entre a queda de CSb e a comprovação do drive
inclui propagação de controle e acomodação analógica sob 1 kΩ.

No ciclo 12, DATA6 ainda estava em 1,797 V, com +2,75 µA na sonda e
−4,36 µA no ramo da macro, no ponto original. Depois, o ramo da SRAM
se opôs à sonda por pelo menos 52,3 ps antes do pedido de desabilitação
e os critérios de drive permaneceram até cerca de 247,251 ns. A
primeira amostra de liberação sustentada foi em 247,662 ns, com
DATA6 em 1,772 V, +28,4 µA na sonda e −21,5 µA na macro.
Entre o fim da condução qualificada e o início da liberação comprovada,
o pino está em **transição**. O começo físico dentro do bracket de
amostras continua indeterminado. Um teste de sensibilidade que exige
100 ps para comprovar drive antes da desabilitação deixa quatro bits
inconclusivos em cada um dos três ciclos. A recuperação tem margem
de observação limitada sob essa carga. Nenhum desses intervalos fixa
um requisito público de recuperação.

Em c8, os ramos já estavam quietos no intervalo de chaves abertas.
O pico no fechamento do host forte acompanha a inversão do pad,
com o driver da SRAM já desabilitado. Em DATA6, o host elevou o pino
de cerca de 0,004 V a 1,800 V e a corrente no ramo da macro entrou
no PEX. O módulo era cerca de 196 µA a +51 ps e caiu a cerca de
6 µA a +200 ps, com `TE_B` acima de 1,44 V durante a observação.
O último bit entrou no regime quieto sustentado na amostra a
114,5 ps do fechamento. Essa resposta é compatível com carga do
PEX e do pino; a corrente de cada elemento interno não foi registrada.
Os pulsos das escritas consecutivas c3–c5 seguiram a mudança
programada de payload e também recuperaram o regime quieto.

## 3. Validação cruzada nos 18 ciclos

“Sobreposição” se refere a acionamento forte simultâneo comprovado.
A oposição intencional da sonda fraca foi usada para testar
drive/liberação. Em escrita ou idle, o estado de condução da SRAM
entra como aplicável somente na fase de leitura que precede o handoff.

| Ciclo | Resultado original | Condução comprovada | Liberação comprovada | Sobreposição | Novo veredito |
|---:|---|---|---|---|---|
| 0 | PASS | — | Sim | Ausente no escopo | PASS |
| 1 | PASS | — | Sim | Ausente no escopo | PASS |
| 2 | PASS | — | Sim | Ausente no escopo | PASS |
| 3 | PASS | — | Sim | Ausente no escopo | PASS |
| 4 | PASS | — | Sim | Ausente no escopo | PASS |
| 5 | PASS | — | Sim | Ausente no escopo | PASS |
| 6 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 7 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 8 | INCONCLUSIVO | Sim | Sim | Ausente no escopo | PASS |
| 9 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 10 | INCONCLUSIVO | Sim | Sim | Ausente no escopo | PASS |
| 11 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 12 | INCONCLUSIVO | Sim | Sim | Ausente no escopo | PASS |
| 13 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 14 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 15 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 16 | PASS | Sim | Sim | Ausente no escopo | PASS |
| 17 | PASS | Sim | Sim | Ausente no escopo | PASS |

O controle histórico de **300 ps** resultou em **FAIL** com oposição
sustentada nos oito bits e `TE_B` abaixo da condição de desabilitação,
em trechos comprovados de 229–346 ps após a tomada do host. O
controle histórico de **1,5 ns** resultou em **PASS** para o teste do
host forte. Os controles independentes validam a discriminação
de oposição. A sonda desses controles já estava desligada nessa
transição, portanto a prova detalhada de liberação sob sonda vem do
transiente integrado. [Evidência por ciclo e por controle](../build/phase3/bus_review_ss_20261120_report/review.json)

## 4. Veredito e consequência para a implementação

- **Histórico preservado.** 15 PASS e três INCONCLUSIVO de propriedade,
  com resultado integrado original INCONCLUSIVO. A cópia arquivada
  de `validation.json` tem o mesmo SHA-256 do recibo local.
- **Replay funcional revisado.** 18/18 PASS de propriedade no
  escopo monitorado; 9/9 palavras corretas e estáveis; 6/6 escritas
  confirmadas e quatro linhas cobertas. A liberação antecedeu o host
  nos dois handoffs com guarda fixa de 1,5 ns. Há contenção elétrica
  real no controle separado de 300 ps.
- **Janela histórica.** 65/72 PASS e sete FAILs de DATA7 (c6, c7, c11,
  c13, c14, c15 e c16). O replay preserva os sete registros de atraso
  diagnóstico. A janela histórica de ±100 ps não define um prazo
  público de leitura. [Auditoria dos critérios](phase3_auditoria_falhas_20261119.md)
- **Limites.** O ensaio não estabelece leakage, pior turnaround, prazo
  público de enable/disable, Fmax, PVT ou fidelidade definitiva do PEX.
  Correntes abaixo do piso e fenômenos mais rápidos que a resolução
  amostral permanecem fora da prova. O estado geral é `NOT_CHARACTERIZED`.

A implementação atual cumpriu a direção no protocolo ensaiado. A
lacuna dos três casos originais foi resolvida com o observador contínuo.
Há atraso físico de recuperação sob a sonda, mas o ensaio não
demonstra defeito de controle ou requisito de interface violado que
justifique intervenção física agora. A variante experimental com
`nand4bb_4` reduziu o tempo medido WEb50→TE_B80 de cerca de
908–937 ps para 196–219 ps e passou no handoff de estresse estudado.
Ela acrescentou 190,18 µm² de área de células e alterou o roteamento,
com regressões de leitura na janela diagnóstica. O contorno da macro
foi preservado. A comparação de potência permanece ausente. Se um
futuro orçamento de turnaround for incompatível com a implementação,
usar os recibos existentes para comparar caminhos de controle pelo
mesmo benchmark, incluindo leitura sustentada, área, potência e a
liberação por corrente. [ECO experimental e resultados](phase3_data7_turnaround_20261119.md#desabilitação-da-nand4bb-local-com-rc-integral)

**Próxima etapa recomendada.** Repetir a validação integrada de 18
ciclos em TT e FF com o mesmo candidato, PEX padrão, fixture e
observador. O critério de conclusão é a comprovação de 9/9 palavras
estáveis, 6/6 escritas com readback e 18/18 ciclos de propriedade em
cada corner, com os checks temporais históricos reportados à parte.
Essa validação ainda está pendente.

## 5. Reprodução e artefatos

O analista é `tools/review_phase3_bus_ss.py`. Os 11 testes novos em
`tests/test_phase3_rc_bus_ss.py` passaram, assim como os quatro testes
de software existentes do integrado SS. O replay final levou cerca
de 1,6 s. **Zero novas simulações** e zero novos DRC/LVS, extrações
ou alterações do circuito. A execução SPICE de 35 min 50 s é a
execução histórica identificada acima.

```bash
timeout 90s env PYTHONDONTWRITEBYTECODE=1 python3 tools/review_phase3_bus_ss.py \
  build/phase3/integrated_ss_20261119_preflight \
  --output build/phase3/bus_review_ss_replay
timeout 120s env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_rc_bus_ss.py' -v
timeout 120s env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_rc_integrated_ss.py' -v
```

O replay requer o checkout da integração com seus scripts locais,
as entradas pinadas do ensaio original e os dois controles arquivados.
O novo ZIP contém as alterações, os dois controles com waveform e
os CSVs, JSON e logs do replay. Para recuperar as entradas pinadas
do integrado, use o pacote anterior
`phase3_validacao_integrada_ss_20261119.zip`, SHA-256
`2710b17f3413c3eda672fa4b269f85de5452b80acc376df0eb60a0782ae122de`.
O diretório de saída do replay deve ser novo.
