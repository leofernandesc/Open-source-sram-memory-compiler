# Diagnóstico da janela DATA — Fase 3 — 13/11/2026

## Conclusão e alcance

Os quatro FAILs foram reproduzidos exatamente com o waveform real preservado.
A causa imediata é a **reabilitação analógica de DATA após escrita→leitura**:
o registrador guarda `0x55`, mas o barramento, que o host havia dirigido com
`0xAA`, ainda está recuperando `0x55` no início da janela fixa do observer.
A transição dos quatro FAILs não é a apresentação prematura da nova leitura.

A especificação exige retenção do registrador e da palavra no barramento quando
as habilitações de leitura permanecem ativas. Ela não define que o pino DATA
reabilitado depois de uma escrita já deva estar estável em `rise_ns + 1 ns`.
Por isso, esses FAILs não demonstram defeito funcional normativo da SRAM, mas
**também não podem ser convertidos em PASS sem qualificar a janela de habilitação**.
As tensões inválidas são reais; não foram tratadas como falsos positivos por hipótese.

Classificação principal dos quatro: **3 — expectativa temporal do verificador
sem fundamento no contrato numérico**, aplicada à retomada após escrita. A
conformidade com um prazo físico máximo de habilitação permanece indeterminada
(categoria 6 nesse aspecto), pois esse prazo ainda não foi especificado/qualificado.
O smoke histórico permanece FAIL, CLI 1; timing e potência NOT_CHARACTERIZED.

## Fontes, identidade e reprodução

Branch `feature/phase3-infra-leonardo`, HEAD preservado
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. No início já existia, sem commit,
`docs/phase3_first_sram_smoke_20261113.md`; esse arquivo foi preservado.

Fontes consultadas: relatório do smoke, `specs/technical_specification.md`,
`specs/sram_4x8_digital.md`, `rtl/sram_4x8_wrapper.v`, `rtl/sram_controller.v`,
`physical/phase2/macro_binding.v`, netlist roteada/extraída e binding selecionado,
`tools/phase2_extension.py`, `phase2_access_checks.py` e adapter da Fase 3.

Execução analisada:
`reports/phase3/smoke_sram4x8_20261113_01_real/`.
Waveform: `inputs/waveform.dat`, 40507 amostras, 154 colunas, 0–370 ns,
SHA-256 `1a7670edaa2be0202c1861f053864dcd5f93b24ed727117dd2a6385c7893feae`.
Manifesto original: SHA-256
`6cc1d6efc804f293d4a421678c06494cab63aacfc2fe75ad3ac5022d39750cc7`.
Foram conferidos novamente os 700 pins de entrada e os 708 hashes de evidência
antes do replay. Os bytes e os estados do manifesto original não foram alterados.

O diagnóstico utiliza TT, 1,8 V, 27 °C, 20 ns/50%, slew 50 ps e 10 fF por bit,
com dispositivos/junções e sem RC distribuído completo. Não houve novo SPICE:
o raw contém os sinais necessários para reconstruir as falhas. O replay não
constitui uma nova simulação ou uma nova execução de caracterização.

Artefatos de diagnóstico em `reports/phase3/data_window_diagnostic_20261113_01/`:
`analysis.json`, `failed_samples_v2.csv`, `window_signals.csv`, `bit_events.json`,
`replayed_functional_checks_v2.json`, figura PNG/SVG, scripts e transcrições.
O CSV de amostras inválidas contém **todas as 64 amostras** (16 por bit).
Esses CSVs são diagnósticos com unidades explícitas, não substituem `metrics.csv`.

## 1. Reconstrução de endereço, memória e valor esperado

| Ciclo | Operação | Endereço | Valor e confirmação observada |
|---|---|---|---|
| 7 | Leitura | 1 (`01`) | `0x55`, conforme registro e check funcional |
| 8 | Escrita | 0 (`00`) | Escreve `0x55` |
| 9 | Última leitura válida antes da falha | 0 (`00`) | `DATA=REG_Q=CELL_ROW0=0x55` em 201,004698 ns |
| 10 | Escrita | 1 (`01`) | Reescreve a linha de `0x55` para `0xAA`; CELL_ROW1=0xAA em 221,000101 ns; REG_Q continua 0x55 |
| 11 | Leitura em investigação | 1 (`01`) | Memória contém 0xAA; palavra retida do último read é 0x55; nova leitura 0xAA confirmada em 241,004549 ns |

A última leitura bem-sucedida é uma amostragem observada em 201,004698 ns, não
uma estimativa do instante de disponibilidade. O registrador já continha 0x55;
não se atribui atraso de transição a um bit que não comutou nessa leitura.

`ADDR_Q[1:0]` é `01` no instante dos FAILs: Q0=1,79999999 V e
Q1=2,31840838e-9 V. Os pinos ADDR externos não constam do `wrdata`;
o PWL pinado define endereço 01 sem alteração entre os ciclos 10/11, e a captura
01 é confirmada no raw. Não se inventou uma amostra elétrica dos pinos ausentes.

O verificador compara DATA com a **palavra do último read de qualquer endereço**,
0x55, não com o conteúdo atual da linha 1 (0xAA). Nos bits pares, espera alto
(1,44–1,98 V); o novo conteúdo da linha 1 nesses bits é baixo. Essa diferença
é correta para a palavra antiga retida antes da captura da nova leitura.

## 2. Tabela individual dos quatro FAILs

Todos pertencem a `previous_data_visible_before_new_capture`, ciclo 11,
leitura da linha 1. Tempos abaixo são os timestamps efetivamente presentes no raw.

| Sinal | Esperado | Primeira–última amostra inválida (ns) | Observado primeira→última | Interpretação | Amostras | Categoria |
|---|---|---|---|---|---:|---|
| DATA[0] | 1 (palavra antiga 0x55) | 231.007658–231.119291 | 0.957592467→1.42949231 V | X pelo critério 20/80 | 16 | 3; limite normativo pendente |
| DATA[2] | 1 (palavra antiga 0x55) | 231.007658–231.119291 | 0.957592467→1.42949231 V | X pelo critério 20/80 | 16 | 3; limite normativo pendente |
| DATA[4] | 1 (palavra antiga 0x55) | 231.007658–231.119291 | 0.957592467→1.42949231 V | X pelo critério 20/80 | 16 | 3; limite normativo pendente |
| DATA[6] | 1 (palavra antiga 0x55) | 231.007658–231.119291 | 0.957592467→1.42949231 V | X pelo critério 20/80 | 16 | 3; limite normativo pendente |

Não se interpreta 0,957592467 V como zero ou um válido: está na região entre
20% e 80% VDD. Na primeira amostra, o barramento é `0X0X0X0X` pelos limiares
funcionais; o registrador interno permanece 0x55. O valor máximo na janela é
1,80005975 V e o mínimo é o da primeira amostra inválida, nos quatro bits.

`phase2_extension.check`, linhas 117–131, usa:

```python
high = (t >= rise_ns + 1) & (t <= fall_ns - .5)
# Quando existe previous_read, todo op=='read' recebe esta verificação.
levels(DATA[bit][high], previous_read[bit])
```

No ciclo 11 isso significa **[231; 239,5] ns**, incluindo todas as amostras dessa
janela, não apenas uma amostra do novo dado. A primeira amostra disponível após
231 ns é 231,007658 ns. O teste também é aplicado após writes e idle, sem
qualificar separadamente o tempo de reabilitação da saída.

## 3. Estados reais e caminho físico da saída

Na primeira amostra inválida (231,007658 ns):

| Sinal | Valor observado | Estado |
|---|---:|---|
| CLK | 1,8 V | Alto |
| CSb / OEb / WEb | 0 / 0 / 1,8 V | Controles externos de leitura |
| READ_Q / WRITE_Q | 1,60144853 / −0,000065743622 V | Leitura capturada; escrita inativa |
| HOST_EN / HOST_WEAK_EN | 0 / 0 V | Nenhum host/probe habilitado |
| TE_B0 | 0,003452897 V | Saída habilitada, enable ativo baixo |
| REG_Q0 | 1,8000165 V | Bit antigo retido alto |
| DATA0 | 0,957592467 V | Barramento ainda em recuperação |
| DOUT_RAW0 / CAPTURE_D0 | 1,79994834 / 1,7999686 V | Ainda não são a nova decisão baixa da linha 1 |
| CAPTURE_CLK0 | −0,00000128638689 V | Nenhuma captura da nova palavra neste instante |
| PRECH / PCLK / SCLK | ≈0,0000668 / −0,00000874 / 0,0000671 V | Pré-carga ativa; avaliação/sense inativos |
| WL0…WL3 | ≈0,000001318 V | Todas inativas |
| I_HOST0 / I_WEAK0 | −9,57592467e-13 A cada | Sem contenção ativa demonstrada |

As 88 verificações `previous_ff_q_retained` passaram. O modelo não está
atualizando o registrador com um dado errado nesses quatro pontos.

A correspondência física foi conferida com `observation_map`, `.subckt` e a
instância XDUT, sem assumir nomes de outra arquitetura:

| Célula/pino | Nó no binding |
|---|---|
| Registrador `_75_.Q` e buffer `_87_.A` | `v(xdut.e58)` = REG_Q0 |
| Buffer `_87_.TE_B` | `v(xdut.e71)` |
| Buffer `_87_.Z` | `v(xdut.DATA0)`, associado ao pino externo DATA0 pela lista de portas XDUT |
| Registrador `_75_.D` | `v(xdut.e57)` = entrada local de captura |
| Registrador `_75_.CLK` | `v(xdut.e16)` = clock local de captura |

O wrapper implementa `DATA = (read_q && live_read) ? read_data_q : 8'bz`,
com `live_read = !CSb && !OEb && WEb`. O hardware de saída selecionado é
`sky130_fd_sc_hd__ebufn_1`. O registrador de saída é `dfxtp_1` com clock local
que sobe após a descida pública; o multiplexador de entrada implementa a retenção
quando não há read. Não se presumiu latch transparente nem saída combinacional
direta do sense amplifier. Os 80 inversores e taps 24/40/60/80 foram somente lidos.

O helper diagnóstico inicial recusou o alias `v(xdut.DATA0)` por esperar
`v(DATA0)` literalmente. Sua versão 2 passou a verificar a associação explícita
da porta `.subckt` com XDUT. Esse ajuste foi somente no helper novo de diagnóstico;
não é defeito ou correção do checker, runner ou circuito. A tentativa inicial
e seus arquivos parciais foram preservados em `analysis_attempt1.txt`.

## 4. Linha temporal elétrica

Cruzamentos abaixo são interpolados entre amostras reais; os brackets estão em
`analysis.json`. Não representam resolução temporal infinita ou limite garantido.
Todos os tempos são absolutos em ns. Propagação usa eventos de 50% quando
indicados; 20%/80% são usados para delimitar validade funcional.

| Sinal | Evento | Tempo absoluto (ns) |
|---|---|---:|
| OEb | fall a 0.90 V | 227.025000 |
| WEb | rise a 0.90 V | 227.025000 |
| HOST_EN | fall a 0.90 V | 229.925000 |
| CLK | rise a 0.90 V | 230.025000 |
| WRITE_Q | fall a 0.90 V | 230.449737 |
| READ_Q | rise a 0.90 V | 230.703606 |
| TE_B0 | fall a 0.90 V | 230.767339 |
| TE_B0 | fall a 0.36 V | 230.809477 |
| DATA0 | rise a 0.36 V | 230.893896 |
| READ_Q | rise a 1.44 V | 230.926345 |
| DATA0 | rise a 0.90 V | 230.996281 |
| DATA0 | rise a 1.44 V | 231.122752 |
| PRECH | rise a 1.44 V | 231.399303 |
| PCLK | rise a 0.90 V | 232.176450 |
| WL1 | rise a 0.90 V | 232.452661 |
| WL1 | rise a 1.44 V | 232.466900 |
| SCLK | rise a 0.90 V | 232.755378 |
| DOUT_RAW0 | fall a 0.90 V | 232.775544 |
| DOUT_RAW0 | fall a 0.36 V | 232.809804 |
| CLK | fall a 0.90 V | 240.025000 |
| CAPTURE_CLK0 | rise a 0.90 V | 240.271571 |
| REG_Q0 | fall a 0.90 V | 240.449261 |
| DATA0 | fall a 1.44 V | 240.534980 |
| DATA0 | fall a 0.90 V | 240.569202 |
| DATA0 | fall a 0.36 V | 240.609011 |
| WL1 | fall a 0.36 V | 240.662433 |
| PRECH | fall a 0.36 V | 242.937425 |

O enable do host cruza 50% em 229,925 ns, antes da subida pública; esse
cruzamento de controle não é uma medição de liberação em alta impedância. READ_Q sobe a 50% em 230,703606 ns; TE_B cruza 20% em 230,809477 ns.
DATA0 então sobe do valor de escrita para o **bit antigo 1**: cruza 50% em
230,996281 ns e 80% em 231,122752 ns. As quatro reprovações precedem até mesmo
WL1 (50% em 232,452661 ns) e SCLK (50% em 232,755378 ns).

Só depois do sense DOUT_RAW0 cai, em 232,775544 ns a 50%. O registrador permanece
com o bit antigo durante a fase alta. A descida pública ocorre em 240,025 ns,
a captura local em 240,271571 ns, REG_Q0 cai a 50% em 240,449261 ns e DATA0
apresenta a nova transição descendente a 50% em 240,569202 ns. Portanto, a mudança
associada à **nova palavra** é posterior à descida e à captura local.

`rise_ns=230` no registro é o início nominal do PWL, não o cruzamento CLK50 em
230,025 ns. Trocar somente essa referência deslocaria a janela em aproximadamente
25 ps; não explicaria nem eliminaria toda a recuperação até 231,122752 ns. Não
se atribui o FAIL a arredondamento de timestamps ou a um ponto digital ideal.

## 5. Janela observada de validade de DATA

Estes intervalos valem somente para este waveform TT/carga/fixture, não são
novas especificações. A tabela compara cada bit aos limiares da palavra antiga
0x55 e da nova 0xAA; entradas de validade para bits baixos usam 20%, para altos 80%.

| Bit | Antigo válido após retomada (ns) | Antigo deixa sua faixa (ns) | Novo válido (ns) |
|---:|---:|---:|---:|
| 0 | 231.122752 | 240.534980 | 240.609011 |
| 1 | 230.941783 | 240.586187 | 240.814720 |
| 2 | 231.122752 | 240.534980 | 240.609011 |
| 3 | 230.941783 | 240.586187 | 240.814720 |
| 4 | 231.122752 | 240.517524 | 240.591530 |
| 5 | 230.941783 | 240.568705 | 240.797196 |
| 6 | 231.122752 | 240.517524 | 240.591530 |
| 7 | 230.941783 | 240.568705 | 240.797196 |

Para a **palavra completa 0x55**, as amostras válidas contínuas vão de
231,128651 a 240,510708 ns. As fronteiras interpoladas dos oito bits são
aproximadamente 231,122752 e 240,517524 ns. O antigo dado é retido no pino antes
da descida; a propagação após a captura explica sua permanência transitória
por algum tempo após a descida, sem implicar um ciclo extra de leitura.

A **nova palavra completa 0xAA** entra nas faixas em aproximadamente 240,814720 ns;
as amostras válidas contínuas vão de 240,817623 a 241,527373 ns, quando a
perturbação da fixture retira DATA da faixa válida. A amostra de leitura 241,004549 ns está dentro delas.
Todas as 72 verificações de novas leituras e as 72 de captura de Q passaram.

A fixture liga propositalmente uma sonda fraca oposta em 241,5 ns, mascara a saída
com CSb em 242,5 ns e a restaura em 244 ns, desligando a sonda em 245,5 ns
(eventos PWL com transições de 50 ps). **Não se deve extrapolar validade normal
através desse ensaio de oposição/liberação.** Por exemplo, DATA pode mostrar o
valor oposto enquanto o registrador continua 0xAA. Depois da sonda, as amostras
analisadas voltam a 0xAA em 245,815–247 ns (fim escolhido para este diagnóstico).
A sonda estava desligada em todos os quatro FAILs iniciais; não os causou.

Os dois problemas são distintos: acomodação de **habilitação** na retomada de
leitura e propagação da **atualização do registrador** após a descida. Um único
offset de amostragem não caracteriza ambos.

![Waveform real: retomada de DATA, fases e nova captura](../reports/phase3/data_window_diagnostic_20261113_01/data_window.png)

A figura foi gerada das amostras preservadas com matplotlib; não é uma interface
ou waveform sintético. PNG e SVG independentes acompanham o CSV de diagnóstico.

## 6. Confronto com a especificação e classificação

- `technical_specification.md`, seções 4/6: saída em alta impedância em writes e
  operação de saída dependente do read capturado e dos controles atuais; registro
  retém o read anterior; nova palavra depois da descida mais atraso físico.
- `sram_4x8_digital.md`, DIG-06/DIG-08 e tabela “Consecutive reads”: retenção de Q
  e apresentação no pino **while both read enables hold**. Delays elétricos não
  têm valor numérico no modelo; delays de testbench não são limites do ASIC.
- `rtl/sram_4x8_wrapper.v`, linhas 28–32: captura na descida, saída condicionada
  à operação capturada e live_read. Isso está de acordo com os nós elétricos.
- `phase2_extension.py`, linhas 117–131: exige DATA antigo desde `edge+1` em toda
  leitura posterior ao primeiro read, inclusive quando o ciclo anterior era write.

A especificação exige manter **Q interno** até outra leitura capturada. Também
exige manter a palavra antiga em DATA durante leituras consecutivas com enable
mantido. Não exige essa palavra em DATA enquanto o host escreve e não oferece
um limite numérico de reabilitação para write→read. A classificação diagnóstica
não acrescenta esse limite nem modifica o contrato para esconder o FAIL.

| Categoria proposta pelo responsável | Conclusão para os quatro FAILs |
|---|---|
| 1. Defeito funcional real da SRAM | Não demonstrado: Q retido, nova captura e novas palavras corretas nos checks aplicáveis |
| 2. Amostragem fora da janela especificada | Não há janela numérica especificada para esta retomada; só é demonstrado que a amostragem começou antes da validade observada |
| 3. Expectativa temporal incorreta do verificador | Causa principal: 1 ns foi tratado como prazo normativo de saída já acomodada numa retomada write→read |
| 4. Estímulo/sincronização da fixture | Sem defeito comprovado neste cenário; host já desligado, endereço capturado correto, sonda ainda desligada |
| 5. Interpretação elétrica incorreta | Não: DATA está realmente entre 20%/80%; não reinterpretar como nível válido usando 50% |
| 6. Causa indeterminada | Não para o mecanismo observado; continua indeterminada a conformidade com um futuro máximo de habilitação e a decomposição física do atraso |

O replay segregado preserva todos os resultados, sem retirar checks:

| Transição anterior à leitura | PASS desse check de DATA antigo | FAIL |
|---|---:|---:|
| read→read | 40 | 0 |
| write→read | 12 | 4 |
| idle→read | 8 | 0 |

Passar em outras retomadas não qualifica o prazo de 1 ns universalmente. A subida
lenta nos bits pares após reabilitação é consistente com o buffer carregando DATA
com a nova carga exploratória de 10 fF; a comparação sem carga adicional foi
registrada no relatório anterior. Não foi atribuído o atraso a transistores ou
parasitas individuais sem sinais de corrente internos ou uma extração RC completa.

## 7. Correção proposta e decisão desta investigação

Não se demonstrou um defeito exclusivamente de infraestrutura que admita corrigir
com segurança o critério de aprovação sem definir um contrato elétrico pendente.
O problema cruza a metodologia do observer e a ausência de limite de habilitação;
por isso, **não se alterou o checker ou a SRAM**. O critério atual continua FAIL.
Não houve aumento de tolerância, seleção de uma amostra posterior para PASS,
mascaramento até DATA ficar válido nem substituição de dados.

Proposta para revisão explícita da metodologia:

1. Manter a verificação independente de retenção do registrador e os checks de
   leituras consecutivas com direção mantida; não suprimir sua cobertura.
2. Identificar a retomada read após write/idle/máscara como arco de habilitação
   diferente de clock-to-data. Medir eventos e direção por bit/carga, sem escolher
   a janela a partir do mesmo DATA que se quer aprovar (critério circular).
3. Definir/qualificar um limite de habilitação antes de usá-lo como deadline do
   pino. Até lá, esse requisito permanece NOT_CHARACTERIZED; o FAIL histórico
   não é convertido em PASS por uma nova classificação.
4. Versionar uma eventual metodologia nova e seus testes/evidências. Os verificadores
   atuais têm hashes ligados à evidência congelada; não reescrever esses recibos
   para acomodar mudanças. Uma mudança de verificação não deve ocultar os 4 FAILs.

Nenhuma necessidade de mudar circuito ou estímulos foi demonstrada. Se o prazo
futuro aprovado for mais estrito que o comportamento medido, será preciso discutir
buffer/carga, protocolo ou especificação com suas consequências, não alterá-los
automaticamente. Não há aprovação de um novo valor numérico nesta investigação.

## 8. Validação posterior, comandos e estados

Replay no raw imutável, com o mesmo `phase3.functional.check_waveform` que chama
os verificadores existentes: **1.736 PASS, 4 FAIL, 72 novas leituras PASS e
88 checks de retenção de Q PASS**. O resultado completo é idêntico, campo a campo,
ao `functional_checks.json` original. Não se criou verificador elétrico substituto.

Comandos executados a partir da raiz (sem ngspice):

```bash
tools/sram-eda python3 reports/phase3/data_window_diagnostic_20261113_01/analyze_window_v2.py
tools/sram-eda python3 reports/phase3/data_window_diagnostic_20261113_01/bit_events.py
tools/sram-eda python3 reports/phase3/data_window_diagnostic_20261113_01/plot_window.py
tools/sram-eda python3 reports/phase3/data_window_diagnostic_20261113_01/run_tests.py
```

Os scripts atuais preservam saídas exclusivas; para uma reprodução em nova pasta,
substituir o destino local ou escolher nomes novos em vez de sobrescrever evidências.
`analyze_window_v2.py` usa `open('x')` para o CSV e recusará um destino já existente.

A suíte da revisão foi executada novamente: **50 PASS, zero falhas,
erros ou skips**, com os padrões `test_phase3*.py`, `test_phase2_evidence.py`,
`test_phase2_output_safety.py`, `test_phase2_extension.py`, `test_phase2_startup.py`
e `test_phase2_protocol.py`. Os testes incluem a distinção entre simulador,
medição e verificação, os códigos CLI e a semântica NOT_CHARACTERIZED. Mocks e
fixtures desses testes são validação de software, não evidência elétrica nova.

Estados preservados: simulador original PASS/0; medida NOT_CHARACTERIZED;
funcional FAIL; execução real FAIL/CLI 1; dry-run original NOT_CHARACTERIZED/CLI 0.
`metrics.csv` permanece com 15 colunas e zero linhas. Nenhuma métrica normalizada
de timing/potência ou limite de funcionamento foi criado a partir destes diagnósticos.

**Não executados:** novo SPICE, PVT, Liberty, SNM e RC distribuído. Os dados reais
já disponíveis foram suficientes para a reconstrução; não há correção de produção
que justifique repetir a simulação nesta investigação.

## 9. Entrega e resposta aos critérios de conclusão

1. Os quatro FAILs não comprovam defeito funcional da arquitetura; registram
   recuperação analógica real mais lenta que a hipótese de amostragem de 1 ns.
2. A SRAM apresenta os novos dados corretamente nas 72 verificações efetivamente
   executadas; isso não prova todas as condições ou margens elétricas.
3. Retenção de Q e de DATA em leituras continuamente habilitadas está de acordo
   com a especificação; deadline de 1 ns para read retomado após write não está definido.
4. A janela empírica completa da palavra antiga tem amostras válidas entre
   231,128651 e 240,510708 ns; a nova palavra é válida desde 240,817623 ns nas
   amostras até a sonda em 241,5 ns. Não existe ainda janela numérica garantida.
5. Não há mudança de circuito/fixture justificada. O requisito de habilitação e
   sua verificação precisam de qualificação/metodologia versionada, sem relaxamento ad hoc.
6. **O smoke funcional não pode ser declarado aprovado**: seu verificador aplicado
   continua com 4 FAILs, e a questão temporal de habilitação ainda precisa ser fechada.

Criados: este relatório e os artefatos locais de diagnóstico na pasta indicada.
Nenhum arquivo de produção, especificação, layout, célula, temporização, seletor,
recibo, raw, CSV ou manifesto preexistente foi modificado. Nenhum commit, merge ou push.
