# Proposta de contrato temporal de DATA — Fase 3 — 16/11/2026

**Estado: PROPOSTA PARA APROVAÇÃO. Nenhum requisito ou critério foi alterado.**

Branch auditada: `feature/phase3-infra-leonardo`. HEAD:
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. Os três relatórios da Fase 3 já
estavam presentes como arquivos locais sem commit e foram preservados.

## 1. Decisão técnica recomendada

Recomenda-se **A como contrato funcional principal**, orientado à captura
síncrona, com retenção e propriedade do barramento continuamente verificadas
onde aplicáveis. **B deve complementá-lo para qualificação temporal da interface**,
com máximos explícitos e caracterizados. Essa combinação não muda a arquitetura:
separa conformidade funcional de garantias elétricas ainda pendentes.

A alternativa A não significa conferir somente uma amostra e ignorar o restante
do waveform. A alternativa B não significa substituir 1 ns por um valor que
acomode os resultados atuais. Nenhuma das alternativas permite aprovar DATA
indefinidamente inválido, contenção ou dado incorreto.

Conclusão sobre os quatro FAILs: **as tensões inválidas são reais e violam o
critério de bancada executado, mas não demonstram violação de um prazo normativo
de reabilitação de 1 ns**, pois esse prazo não existe nos contratos auditados.
Há fundamento técnico para rever sua classificação por requisito, mantendo
intactos o FAIL histórico, o raw, os hashes, o manifesto e o retorno da CLI.
Isso não equivale a transformar o resultado em PASS nem aprovar o smoke agora.

O contrato público já determina que `tDATA_ENABLE` está pendente e que não se
prescreve um intervalo numérico arbitrário. Não é necessário inventar uma nova
arquitetura para reconhecer essa fronteira. Depende de aprovação a política de
aceitação futura, a classificação versionada dos checks e qualquer nova garantia.

## 2. Autoridade das fontes e auditoria dos requisitos

Foram lidas integralmente a
[especificação técnica](../specs/technical_specification.md) e a
[especificação digital](../specs/sram_4x8_digital.md), além do
[contrato temporal público](../specs/sram_4x8_timing_contract.md), do
[binding físico](../specs/phase2_physical_interface.md), do RTL e dos verificadores.
Nesta auditoria, “normativo” indica a semântica definida nesses documentos
versionados; não acrescenta uma ratificação institucional ou aprovação nova.

Há também uma obrigação **operacional de aceitação** vigente no
[contrato de caracterização da Fase 3](phase3_characterization_contract.md),
seção “Critérios explícitos para esse primeiro smoke”, itens 4–7: todos os checks
do perfil pinado devem passar, com cobertura completa. Essa regra continua
vinculante para o smoke atual. A ausência de um máximo elétrico público de 1 ns
não anula esse gate nem autoriza chamar o resultado atual de PASS. A proposta
distingue a autoridade arquitetural do deadline e a regra operacional que exige
cumpri-lo na bancada vigente; mudar a política futura requer decisão explícita.

| ID de auditoria | Requisito existente | Fonte rastreável | Fronteira numérica |
|---|---|---|---|
| R01 | Capturar endereço e operação na subida de CLK | Técnica §§6/15/16; digital DIG-01 | Setup/hold públicos pendentes |
| R02 | Capturar DATA de escrita nessa mesma subida; não recapturar na descida | Técnica §16; digital DIG-02 e convenção de conclusão | Setup/hold de DIN pendentes |
| R03 | Read para 001, write para 010; comandos restantes sem novo acesso | Técnica §4; digital DIG-03/04 | Combinações lógicas definidas |
| R04 | Capturar a nova palavra no registrador de saída na descida, se READ_Q | Técnica §§6/15; digital DIG-05; temporal §§3/4 | Clock local tem atraso em relação à descida pública |
| R05 | Reter o último resultado interno até outra captura de leitura, inclusive durante writes/idle | Técnica §6; digital DIG-08; temporal §4.6 | Não depende da habilitação do pino |
| R06 | Dirigir DATA somente com read capturado e controles atuais de leitura | Técnica §4; digital DIG-06; temporal §2 | Atrasos físicos de enable/disable pendentes |
| R07 | Máscara viva não cancela nem substitui a operação interna capturada | Digital DIG-07; temporal §§2/4/5 | Não é novo clock de acesso |
| R08 | Em leituras consecutivas com enables mantidos, preservar a palavra anterior antes da próxima atualização | Digital tabela “Consecutive reads”; temporal §4 | Não implica nova palavra na subida nem mudança instantânea na descida |
| R09 | Após descida e atrasos físicos, disponibilizar o novo resultado, se a saída estiver habilitada | Técnica §6; temporal §§3/4/8 | `tREAD_VALID` explicitamente pendente |
| R10 | Em escrita/idle/desabilitado/inválido, a SRAM libera DATA; mestre só assume após liberação | Técnica §§4/16; digital handoff; temporal §§5/6 | `tDATA_DISABLE` e `tTURNAROUND` pendentes; sem ZBT garantido |
| R11 | Dado interno válido na captura local e durante setup/hold do FF; pré-carga não deve destruí-lo cedo | Técnica §6; binding físico, sequência 4; temporal §§9/10 | Referência do FF não é setup/hold público da macro |
| R12 | Pré-carga no baixo, acesso no alto, exclusão entre acessos e recuperação antes do próximo acesso | Técnica §§6/8/14; binding físico | Ordenação definida; período mínimo/Fmax não qualificados |
| R13 | Sem reset nem conteúdo inicial conhecido; expectativas só após escrita/leitura apropriadas | Técnica §5; digital DIG-09; temporal §7 | Condicionamento de partida é procedimento experimental |
| R14 | Interface bidirecional, 8 bits, sem pino data-valid adicional | Técnica §§1/4; digital DIG-10 | Não há handshake externo que anuncie conclusão elétrica |

Os IDs R01–R14 organizam esta auditoria; não são novos requisitos públicos.

### 2.1 O que já é normativo sobre retenção

`specs/sram_4x8_digital.md`, DIG-08, refere-se ao **registrador**. Sua tabela de
leituras consecutivas condiciona a retenção visível no pino a **“while both read
enables hold”**. O wrapper implementa:

```text
drive_DATA = READ_Q AND NOT(CSb) AND NOT(OEb) AND WEb
DATA       = drive_DATA ? read_data_q : Z
```

Q pode continuar com a palavra antiga enquanto DATA recebe a palavra de escrita
do mestre. Exigir que o pino preserve o valor antigo durante a escrita impediria
o uso bidirecional definido pela própria especificação. Por outro lado, não se
permite perder Q ou apresentar antecipadamente o resultado de outro endereço
numa leitura continuamente habilitada.

O hardware selecionado possui FF positivo com clock fisicamente invertido,
mux de retenção e ebufn na saída. DOUT_RAW, entrada D do FF, Q e DATA são pontos
distintos. Capturar D corretamente não prova sozinho que o buffer externo dirige
o pino corretamente; ler o pino num único ponto não prova retenção contínua.

### 2.2 Quais instantes exigem informação válida

1. Nas entradas, endereço/comando e DATA de escrita devem cumprir setup/hold
   relativamente à subida pública. A obrigação existe; seus números não estão
   qualificados. Um estímulo sabidamente ilegal não pode condenar ou aprovar o DUT.
2. Na captura de saída, a entrada D do FF deve representar o resultado correto
   no clock **local**, com seu envelope de captura aplicável. Não é DATA externo
   que o FF de saída amostra. RAW pode resolver antes e o pino ainda mostrar Q antigo.
3. Q deve resultar dessa captura e continuar correto até a próxima leitura
   capturada; writes, idle e máscaras não podem apagá-lo.
4. Com drive habilitado e Q estável, DATA deve representar Q após a propagação
   correspondente. Em uma janela já válida e com direção mantida, não se permite
   um glitch funcional não relacionado a mudança legal de dados/controle.
5. O novo dado só é esperado no pino **após** a descida e os atrasos físicos.
   Não há obrigação de novo DATA exatamente em CLK50↓. A seção 4 do contrato
   público afirma que não existe limite qualificado de `tREAD_VALID` nesta fase.

Não existe, nos documentos atuais, um instante numérico universal de amostragem
externa válido para todos os read-after-write. Também não está especificado um
registrador consumidor externo. **A próxima subida da SRAM não deve ser
inventada como captura obrigatória do leitor:** nesse momento DATA pode já ter
sido legalmente entregue ao mestre para uma escrita seguinte.

### 2.3 Normas, medidas e pressupostos distintos

| Item existente | Natureza | Consequência para aceitação |
|---|---|---|
| Regra de captura, retenção e drive lógico | Normativa funcional | Preservar e verificar independentemente dos deadlines |
| 20 ns, fases de 10 ns, slew de 50 ps e 27 °C | Condições experimentais | Não são Fmax, pulso mínimo ou temperatura nominal ratificada |
| Faixas baixo −0,18…0,36 V e alto 1,44…1,98 V em 1,8 V | Método elétrico existente para as medições/checks nominais | Manter no exame destes raws; não extrapolar fixamente para outra alimentação |
| `high = [rise_ns+1, fall_ns−0,5]` | Janela de observação do testbench | Não vira automaticamente garantia pública de habilitação |
| Readback em `rise_ns+11` ou `+12` | Ponto declarado de uma bancada | Evidência nesses pontos; não prova prazo universal após a descida |
| Guardas de handoff 0,3/0,6 ns e desligamento do mestre 0,1 ns antes da subida | Estímulos de C2 | Não são mínimos garantidos de turnaround |
| Envelope setup/hold de dfxtp_1 TT/25 °C | Referência interna experimental contra SPICE TT/27 °C | Não é setup/hold público da SRAM ou sign-off a 27 °C |
| `time_unit = "1ns"` da biblioteca | Unidade de representação | Não significa setup, enable ou propagação máximos de 1 ns |
| Rampa de alimentação de 1 ns | Condição de partida | Não é deadline de DATA |

O contrato temporal público §8 lista setup/hold de ADDR/CTRL/DIN,
`tREAD_VALID`, `tDATA_ENABLE`, `tDATA_DISABLE` e `tTURNAROUND` como pendentes.
“Pendente” não significa zero, infinito ou aprovação por ausência de limite.

## 3. Origem rastreável do deadline de 1 ns

A auditoria usou `git log`, `git show`, `git blame` e verificação de ancestralidade.
As datas abaixo são as registradas no Git, com offset −04:00. Não se atribui
intenção ao autor além do que os arquivos efetivamente registram.

| Commit ancestral de HEAD | Data registrada | Evidência |
|---|---|---|
| `3b0675b6fe42c79561be6e710e328ce95b8b6f81` | 30/10/2026, 20:05:37 | Introduz contrato digital/RTL da Fase 2: subida para pedido, descida para leitura e delays elétricos sem valor numérico |
| `94256a52bbbb4acde4fd26e7151869277e20f39b` | 04/11/2026, 08:43:53 | Introduz `begin+1e-9` no observador de protocolo e `edge+1` na análise dirigida; observa estado capturado/retenção de Q, além de pontos de readback |
| `94451696459b7faec64367d73a49770c18e4e257` | 04/11/2026, 08:43:54 | Startup também usa `edge+1`; cria o contrato temporal público que mantém enable/disable/turnaround pendentes |
| `c46e611c1bca5d6979f0568551465f08ee51f103` | 04/11/2026, 10:11:48 | Cria `phase2_extension.py`; aplica a mesma janela a `previous_data_visible_before_new_capture`, inclusive após write/idle |

O trecho vigente, atribuído por blame a `c46e611`, está em
`tools/phase2_extension.py:117–131`:

```python
high = window(edge + 1, fall - .5)
if previous_read is not None:
    # Também verifica Q; a linha abaixo observa o pino:
    if op == 'read':
        put('previous_data_visible_before_new_capture',
            levels(data[high, bit+1], previous_bit))
```

Este pseudotrecho explicita a semântica; o código original não foi editado.
`previous_read` atravessa writes/idle, e o teste do pino não distingue retomada
de leitura de enable continuamente mantido. A associação temporal completa
não está demonstrada por um orçamento de caminho ou uma caracterização máxima
no commit. O padrão de janela é anterior; não há evidência para afirmar que
seu valor tenha sido calculado a partir de uma garantia de tDATA_ENABLE.

Há uma evidência contratual particularmente forte e anterior ao check do pino:
o contrato temporal público §6, linhas 134–140, criado em `9445169`, declara
enable/disable/turnaround **pendentes**, não prescreve intervalo numérico
arbitrário e nega uma garantia de handoff instantâneo. A tabela §8 repete a
pendência e separa enable de disponibilidade da nova leitura.

As buscas históricas por `1 ns`, `1ns` e `1.0 ns` não localizaram introdução
dessas expressões em `technical_specification.md` ou `sram_4x8_digital.md`.
Mais importante que essa busca textual é a declaração positiva de pendência no
contrato público. O contrato digital já esclarece que delays do testbench não
são limites temporais do ASIC. Não foi encontrada ratificação normativa do deadline.

A documentação posterior também distingue bancadas:
[cobertura C1/C2](phase2_coverage_extension.md) declara guardas não garantidas;
[análise temporal](phase2_timing_extension.md) relata uma análise DATA rejeitada
porque a saída era restaurada só em queda+1 ns, sendo o readback da bancada em
queda+2 ns. Isso reforça a necessidade de rastrear o enable real; não cria um
novo prazo universal de 2 ns.

Reprodução das consultas principais, somente leitura:

```bash
git blame -L 115,139 -- tools/phase2_extension.py
git show c46e611:tools/phase2_extension.py
git show 9445169:specs/sram_4x8_timing_contract.md
git log --all -S'1 ns' -- specs/technical_specification.md specs/sram_4x8_digital.md
git log --all -G 'edge\+1|begin\+1e-9' -- tools/phase2_extension.py tools/phase2_access_checks.py
```

## 4. Confronto com os dados elétricos existentes

Nenhuma simulação ou extração foi executada nesta etapa. Foram conferidos os
relatórios e os resultados arquivados que os sustentam:

- [Smoke original](phase3_first_sram_smoke_20261113.md): 370 ns, 40.507 amostras,
  1.736 PASS/4 FAIL e 72 novas leituras corretas.
- [Reconstrução da janela](phase3_data_window_diagnostic_20261113.md): quatro
  FAILs em c11, bits 0/2/4/6, entre 231,007658 e 231,119291 ns.
- [Qualificação diagnóstica](phase3_data_enable_qualification_20261113.md):
  210 ns, dois padrões opostos e controle sem comutação, 32 novas leituras corretas,
  719 PASS/8 FAIL e 16 medições nativas válidas.

Evidência primária consultável: [manifesto original](../reports/phase3/smoke_sram4x8_20261113_01_real/manifest.json),
[checks originais](../reports/phase3/smoke_sram4x8_20261113_01_real/functional_checks.json),
[manifesto diagnóstico preciso](../reports/phase3/data_enable_qualification_20261113_01/run_precision/manifest.json),
[sumário temporal](../reports/phase3/data_enable_qualification_20261113_01/analysis_precision/analysis_summary.json)
e [replay original](../reports/phase3/data_enable_qualification_20261113_01/analysis_precision/original_replay.json).
Os manifestos preservam a proveniência e os hashes; o sumário distingue cruzamento
interpolado, primeira amostra válida e intervalo de estabilidade amostrado.

Condições: SKY130A, TT, 1,8 V, 27 °C, 10 fF/bit, fontes de 50 ps;
dispositivos/junções extraídos, sem RC distribuído completo. Não há PVT completo.

| Medida | Observação | O que não demonstra |
|---|---|---|
| TE_B50↓→DATA50 | ≈0,134 ns em descida; ≈0,229 ns em subida | Prazo público, tZ físico exato ou chegada da nova palavra |
| CLK50↑→palavra antiga novamente válida | 1,097761 e 1,097774 ns nos casos complementares | Máximo garantido, valor de tACCESS ou disponibilidade da nova leitura |
| Estabilidade observada até a captura seguinte | ≈9,123 ns de amostras válidas | Setup/hold mínimo, janela externa garantida ou margem PVT |
| Caso sem comutação | Tensão já válida; propagação ausente/censurada | Atraso zero ou prova de condução apenas pela tensão |
| 72 checks do smoke e 32 do diagnóstico | Novas palavras corretas nos pontos efetivamente testados | Validade contínua irrestrita ou todos os padrões/condições |

No smoke original, o último read conhecido era 0x55; uma escrita seguinte
colocou 0xAA na linha 1 e no barramento do mestre. Na retomada de read, Q
continuava 0x55, mas DATA precisava recuperar esse valor a partir de 0xAA.
Os bits pares subiam lentamente pelo buffer carregado. O checker iniciou a
janela antes de eles alcançarem 1,44 V; as amostras eram genuinamente inválidas.

Esses eventos precedem WL1/SCLK e a atualização da nova palavra. Na análise
preservada, DATA0 recupera 80% em 231,122752 ns; WL1 cruza 50% em 232,452661 ns;
SCLK em 232,755378 ns. A nova palavra chega ao registrador somente na captura
local associada à descida pública. Não é uma captura antecipada de dado errado.

O diagnóstico complementar repete a mesma dificuldade nos bits ímpares ao
inverter os padrões. Os 8 FAILs novos são do mesmo check de janela, não de
novas leituras. As observações de retenção, direção e leitura nos cenários
executados são compatíveis com a arquitetura. Não comprovam toda a conformidade
temporal nem um defeito lógico da SRAM.

O início nominal do PWL difere de CLK50 em 25 ps. Assim, `rise_ns+1` é
CLK50+0,975 ns neste ensaio. Medir desde CLK50+1 ns ainda não acomodaria a
recuperação observada até ≈CLK50+1,098 ns. Corrigir apenas a origem do tempo
não resolveria os quatro checks nem fundamentaria um prazo novo.

### 4.1 Os quatro FAILs violam uma norma existente?

| Obrigação | Evidência relevante | Conclusão restrita aos quatro casos |
|---|---|---|
| Q retido até nova captura | Q correto enquanto DATA recupera; retenção e captura verificadas nos relatórios | Não há violação demonstrada |
| DATA antigo em read→read com enable mantido | Os FAILs são write→read; os 40 checks read→read segregados passaram | Não são contraexemplos dessa obrigação |
| SRAM não dirige durante write | O host havia imposto o dado de escrita; checks de direção passaram | Não se exige DATA antigo durante esse write |
| Nova palavra após captura síncrona | 72 readbacks corretos; atualização observada depois da descida | Não há violação demonstrada nesses pontos |
| DATA antigo válido em subida nominal+1 ns após write | Nenhum limite correspondente; §6/§8 públicos o deixam pendente | FAIL de hipótese de bancada, não prova de violação normativa |

É possível concluir objetivamente que o último requisito não pode ser promovido
a norma apenas porque está implementado num checker. Não é possível concluir
daí que a SRAM satisfaz qualquer prazo de enable ou que todo o smoke está aprovado.

## 5. Alternativa A — contrato orientado à captura

### Definição proposta

Usar a semântica de captura já definida como eixo funcional: pedido/escrita na
subida, resultado no registrador na descida local correspondente, retenção de Q
até a próxima leitura e saída condicionada ao enable. Verificar o pino e sua
estabilidade nas janelas de interface aplicáveis, além dos pontos internos.

No RTL sem atraso, observar depois de NBA/deltas necessários; não atribuir
ao modelo um atraso elétrico fictício. No SPICE, respeitar o clock local, os
atrasos de Q/driver e as referências físicas. A disponibilização externa
continua um requisito distinto da captura interna.

### Critérios e limites

- Endereço/operador/dado capturados, sequência da memória e FF_D/Q corretos
  são obrigações funcionais independentes. Não se troca Q antigo por novo na subida.
- Q deve permanecer correto até a captura seguinte; não conferir apenas os
  instantes em que uma falha de retenção poderia já ter desaparecido.
- Em leitura continuamente habilitada e já válida, acompanhar DATA ao longo
  da janela, detectando glitches, valor incorreto e alterações antecipadas.
  Transições legais na captura/máscara possuem suas janelas elétricas próprias;
  elas não autorizam excluir toda a fase alta ou qualquer intervalo que falhe.
- Readback externo exige um evento/ponto de observação definido antes de executar,
  com direção legal e dados conhecidos. Os pontos `fall+1`/`fall+2` atuais podem
  sustentar observações de bancada, mas não são garantias universais.
- Uma especificação de consumo externo deve escolher esse evento e seus
  setup/hold ou aprovar um limite de `tREAD_VALID`. Não se escolhe o evento a
  posteriori procurando uma amostra que já tenha passado.

### Avaliação

É a alternativa mais próxima do modelo implementado e dos requisitos existentes.
Não altera portas, relógios, registradores ou a regra de propriedade. Entretanto,
**A sozinha não qualifica um atraso máximo de enable nem toda a interface elétrica**.
Sem um contrato externo de amostragem/propagação, seu PASS deve ser explicitamente
funcional e limitado à cobertura avaliada; o restante permanece não caracterizado.

O risco é aprovar uma memória que captura corretamente internamente, mas dirige
DATA errado, tarde ou só brevemente. Para evitá-lo, A deve conservar verificações
do pino, direção, continuidade e cenários de transição, com pontos independentes
do resultado. Não é aceitável eliminar o teste do pino e observar só FF_Q.

Evidências adicionais: mapeamento completo de requisitos/cobertura, testes
negativos de glitches/driver/retenção e uma política explícita de observação
externa. Para PVT, continuam necessários envelopes de captura e interface por
condição; o êxito do scoreboard RTL não substitui isso.

## 6. Alternativa B — máximo explícito de habilitação

### Definição proposta, sem valor atribuído

Preservar a distinção do contrato atual entre **começar a dirigir** DATA e
**dirigir a palavra correta em nível válido**. Propõe-se, para revisão, o nome
`T_REENABLE_VALID_MAX` para o segundo limite, sem redefinir silenciosamente
`tDATA_ENABLE`. Trata-se de uma proposta de nomenclatura, não de um campo novo
já aceito na configuração Python ou na especificação oficial.

Para cada bit conhecido, medir a entrada na faixa funcional correta e a
permanência nela na janela de uso. A palavra está válida quando o último bit
atinge esse estado. Separar subida, descida e ausência de transição; neste último
caso, tensão correta não prova atraso zero nem entrada em condução.

### Arcos que precisam de referências diferentes

| Arco | Referência pública proposta | Pré-condições e cuidados |
|---|---|---|
| Write→read capturado | CLK50↑ que captura read | Controles/endereço válidos em setup/hold, mestre liberado e Q anterior conhecido; incluir latência de captura/enable |
| Restauração de read vivo | Cruzamento 50% de CSb↓, OEb↓ ou WEb↑ que completa read | READ_Q já ativo e estável; demais condições satisfeitas; distinguir mudança de um controle de uma sequência com glitches |
| Disable por controle vivo | Cruzamento 50% do controle que retira read | Medir liberação por corrente/impedância em sonda definida, não apenas pela tensão |
| Disable por novo pedido | CLK50↑ que captura operação não read | Incluir captura e caminho de disable; não usar um arco assíncrono no lugar |
| Disponibilidade de nova leitura | CLK50↓→nova palavra válida | É `tREAD_VALID`/caminho de atualização; não é a restauração do Q antigo |

Uma expressão ingênua `max(tempos dos controles, CLK)` não pode legitimar
um read que não foi capturado por violação de setup/hold. O arco e suas
pré-condições devem estar definidos. Para diagnóstico interno, TE_B50 permanece
útil, mas não substitui o evento observável no contrato externo.

### Método elétrico e garantia

- Declarar configuração, extração, corner, VDD, temperatura, slew, carga por bit,
  estado inicial do barramento e propriedade do driver; manter os estímulos legais.
- Em TT/1,8 V, usar o método nominal de 20%/80% e faixas já declarado. Para outra
  alimentação/tecnologia, aprovar limiares apropriados; não reutilizar cegamente
  os números 0,36/1,44 V hardcoded nos observers atuais.
- Definir estabilidade sobre a janela de uso até uma alteração legal independente
  de controle/dado, com setup/hold do consumidor quando ele for especificado.
  Probe oposto e máscara intencionais têm fase de calibração separada e rastreável.
- Registrar resolução, brackets, casos sem transição e casos que não resolveram;
  falha de convergência até o fim do ensaio não pode ser descartada.
- Obter o orçamento máximo de uma exigência de integração e/ou de caracterização
  aprovada com cobertura, margens e limitações justificadas. Não escolher o máximo
  observado arredondado mais uma folga conveniente.

Se for prometida visibilidade da palavra antiga **antes** da captura seguinte,
é necessário definir também uma janela útil mínima ou condição equivalente.
Um orçamento que só vence depois de Q já ter sido atualizado não qualifica essa
promessa. Essa garantia quantitativa adicional requer aprovação; os 9,123 ns
observados não devem virar automaticamente sua largura mínima.

PASS do arco exige orçamento aplicável e todos os bits corretos até o deadline,
permanecendo válidos na janela prescrita. FAIL exige estímulo válido e violação
do prazo/estabilidade ou erro funcional. Sem limite ou domínio qualificado,
o atraso pode ser medido, mas a garantia é NOT_CHARACTERIZED.

### Avaliação

B é compatível com a arquitetura e dá ao integrador uma garantia utilizável,
mas acrescenta uma obrigação numérica que o contrato atual deixa pendente.
Implica novos perfis/versionamento dos observers e caracterização PVT de captura,
controle, buffer, carga e interconexão, sem alterar necessariamente o circuito.

Os riscos são escolher um limite sobreajustado, misturar arcos/referências,
aprovar pela tensão de um nó flutuante ou esconder falhas em médias por palavra.
São necessários padrões complementares, bits não comutantes, retomadas por
CLK/controles, múltiplas cargas/slews, extração identificada, todos os casos
falhos preservados e evidência de margem. Nada disso foi substituído por este
único ponto nominal. Não se recomenda valor numérico para B nesta proposta.

## 7. Comparação e recomendação consolidada

| Dimensão | A — funcional por captura e janelas aplicáveis | B — limite máximo de habilitação |
|---|---|---|
| Coerência com o que já está definido | Alta; preserva a SRAM síncrona e o estado de Q | Complementa os parâmetros explicitamente pendentes |
| Decisão nova principal | Política de evidência/observação externa e classificação dos checks | Valor, domínio, margem e janela garantida por arco |
| Impacto em verificadores | Separar propriedades sem retirar retenção/drive/estabilidade; explicitar pontos de bancada | Medir eventos, consultar orçamento independente e checar deadline por bit |
| Valor de um PASS | Correção funcional na cobertura definida | Garantia temporal apenas no domínio qualificado |
| Risco se aplicada superficialmente | Conferir só Q ou uma amostra e perder defeitos externos | Aumentar deadline até passar, usar limiar/referência errados |
| PVT futuro | Ainda precisa envelopes elétricos e interface; modelo lógico não basta | Requer orçamento/tabelas por condição e validação de cobertura |
| Quatro FAILs atuais | Revisão de sua natureza normativa é justificada; resultado antigo fica intacto | Não adjudicáveis contra um máximo aprovado inexistente; falha de 1 ns continua factual |

**Escolha recomendada: A para a autoridade funcional, com B como gate elétrico
complementar antes de declarar temporização qualificada.** Não se recomenda A
como dispensa de caracterizar a interface ou B como forma de alterar o protocolo.
Essa combinação conserva a arquitetura e evita transformar uma convenção do
testbench em requisito ou um dado experimental em garantia.

## 8. Proposta de critérios objetivos de aceitação

Esta seção é uma proposta, não instrução já aplicada ao software.

| Propriedade/gate | PASS proposto | FAIL proposto | Condição ainda não especificada |
|---|---|---|---|
| Integridade/execução | Fontes, hashes, formato e execução completos | Não atribuir falha elétrica a dado inválido | ERROR para evidência/configuração inválida; BLOCKED para dependência impeditiva |
| Captura de pedido/escrita | Comando/linha/DIN capturados uma vez e acesso correspondente | Pedido ou dado errado, recaptura indevida, operação ilegal interna | Número de setup/hold não medido não recebe PASS temporal |
| Captura da leitura | Dado esperado no ponto interno/local correto e Q correspondente | Captura incorreta/antecipada, retenção corrompida ou hold destruído | Guardas internas não qualificadas ficam explícitas; não viram setup/hold macro |
| Retenção interna | Q conserva último read conhecido até outra captura legal | Qualquer perda de Q sem evento autorizado | Conteúdo inicial desconhecido não é comparado a zero inventado |
| Direção/propriedade | SRAM desabilitada nos modos definidos e handoff sem sobreposição | Condução indevida/contenção em estímulo legal | Máximos de disable/turnaround permanecem NOT_CHARACTERIZED |
| Read continuamente habilitado | DATA correto/estável nas janelas já elegíveis e Q correspondente | Glitch ou valor errado sem evento legal, não apenas erro no instante amostrado | Não excluir intervalos somente porque o waveform falhou neles |
| Nova palavra externa | Palavra correta no evento de observação previamente declarado e nas janelas de estabilidade exigidas | Palavra errada, falta de resposta no contrato de uso ou atualização indevida | Sem evento/limite externo aprovado, resultado de bancada é limitado e timing é NOT_CHARACTERIZED |
| Retomada após write/idle/máscara | Com orçamento aprovado, todos os bits corretos até o deadline e estáveis na janela aplicável | Violação do orçamento em estímulo legal; incorreção funcional independente do orçamento | Sem orçamento: medição observada e garantia NOT_CHARACTERIZED, nunca PASS por inexistência do limite |

Um PASS de medição numérica indica que o valor foi realmente produzido e
validado; não implica PASS funcional nem sign-off temporal. Um PASS funcional
sob A não implica que todos os parâmetros de B tenham sido qualificados.

Para um perfil que exija B, a aceitação global deve continuar não aprovada
enquanto B estiver NOT_CHARACTERIZED. FAIL funcional conhecido prevalece sobre
lacunas de caracterização; erro do simulador ou da evidência permanece ERROR.
Não se recomenda alterar os cinco estados públicos nem suas semânticas de CLI:
execução real NOT_CHARACTERIZED não pode retornar sucesso; dry-run concluído
sem simulação pode retornar 0. Os retornos efetivos atuais não são modificados.

### 8.1 Disposição dos quatro FAILs sem perder integridade

1. Manter o run original como `FAIL`, 4 checks FAIL, CLI 1, com seu raw e manifesto.
   Manter também os 8 FAILs do diagnóstico, sem reescrever recibos ou hashes.
2. Em um registro de revisão **aditivo e aprovado**, ligar cada check à sua
   fonte, requisito e condição de bancada. Classificar a exigência específica
   como hipótese temporal não ratificada, sem dizer que a tensão inválida era válida.
3. Se A for aprovada para o gate funcional, verificar sua matriz completa em
   perfil novo/versionado. Não implementar um filtro que simplesmente retire
   `previous_data_visible_before_new_capture` e conte os outros checks como PASS.
4. Reportar separadamente conformidade arquitetural, diagnóstico legado e
   qualificação dos atrasos de enable/read/disable. O prazo pendente não pode
   desaparecer do denominador da cobertura temporal.
5. Qualquer eventual PASS do novo gate deve apontar a versão de contrato, escopo,
   evidência e decisões aprovadas. Não é um PASS retroativo do run antigo.

## 9. Impactos sobre infraestrutura e caracterização futura

Nada foi implementado nesta etapa. Para uma implementação futura aprovada:

- Preservar os verificadores compartilhados e suas evidências; reutilizar os
  observadores existentes. Uma política nova precisa de perfil/contexto versionado,
  com cobertura esperada própria e rastreabilidade por requisito, sem alterar
  os pins históricos para acomodar código novo.
- O adapter atual compara a cobertura por tipo com os 1.740 checks selecionados
  e aceita PASS/FAIL por check. Uma nova interpretação não deve ser disfarçada
  como o mesmo perfil nem introduzir estados novos de maneira incompatível.
- Preservar o CSV de 14 colunas e as medições reais. Referência externa/local,
  sentido, origem do orçamento e perfil devem ficar explícitos no contrato e
  metadados versionados; não reinterpretar uma linha TE_B50→DATA50 como um máximo público.
- Conservar os manifestos atuais. Se houver decisão de agregar por propriedade,
  fazê-lo em evidência aditiva: requisito, versão, resultado, motivo e arquivos
  fonte. A contagem de check legado permanece consultável.
- Manter precisão suficiente no wrdata, vetores completos, tempo crescente,
  dados finitos e limites de execução. A correção de serialização do diagnóstico
  não altera limiares ou deadlines e não justifica remover amostras.
- Para PVT futuro, rever hardcodings de tensão, referências TT/25 °C versus
  transistor a 27 °C, modelos reais por corner, extração, cargas, slews, margens
  e disponibilidade de todos os sinais. O adapter atual é nominal; não se presume
  que seus critérios já sirvam a outros corners.
- Uma futura Liberty só poderá consumir dados realmente qualificados para o arco
  e o domínio. Nem os 16 números isolados nem um PASS funcional de A substituem isso.

### Regressões necessárias depois de uma aprovação, não executadas agora

1. Reexecutar os 50 testes existentes e acrescentar testes da política por
   requisito, orçamento ausente, referência errada, domínio incompatível e CLI.
2. Reproduzir os quatro casos originais e seus espelhos nos oito bits, mantendo
   o diagnóstico legado. Reexecutar o smoke real e confirmar os 72 readbacks,
   retenção e integridade, sem apresentar replay como simulação nova.
3. Cobrir read→read, write→read, idle→read, máscara→read, read→write, mesma/outra
   linha e padrões complementares, não comutantes, primeira leitura e read sem escrita.
4. Injetar mutações de verificação/modelo: perda de Q, atualização na subida,
   dado errado, driver preso/ausente, contenção, glitch entre amostras de readback,
   resposta que só passa num ponto e violação de hold. A nova política deve detectá-las.
5. Para B, testar valores abaixo/no/acima do deadline definido, orçamento
   escolhido independentemente do waveform, todos os bits/direções e intervalos
   vazios/incompletos; não atribuir zero aos casos sem transição.
6. Conferir a consistência log↔medições↔checks↔CSV↔manifesto↔CLI e todas as
   referências/hashes; preservar falhas e execuções incompletas.

## 10. Decisões pendentes de aprovação

| Decisão | Recomendação | O que esta proposta não autoriza |
|---|---|---|
| Gate funcional e seu alcance | Adotar A com observação de Q e DATA, continuidade e propriedade preservadas | Eliminar checks falhos ou declarar aprovação só por ler Q |
| Disposição da hipótese de 1 ns | Separar diagnóstico legado de requisito normativo; preservar FAIL histórico | Trocar status/retorno ou resselar o run original |
| Amostragem externa | Definir evento de uso/consumidor e relações setup/hold ou tREAD_VALID aplicáveis | Escolher próxima subida ou fall+1 como norma sem decisão |
| Garantia de reabilitação | Adotar B como complemento, com arcos/referências e orçamento justificado | Escolher 1,1/1,2 ns ou o máximo observado como garantia |
| Visibilidade pré-captura da palavra antiga após retomada | Deliberar se há janela útil mínima garantida e como ela se relaciona ao clock/enable | Converter 9,123 ns observados em requisito universal |
| Condições e margens | Especificar domínio nominal inicial e plano de qualificação futura | Ratificar automaticamente 27 °C, PVT, Fmax ou RC completo |
| Implementação/aceitação versionada | Aprovar revisão de política, cobertura e evidências antes de alterar software | Mudar circuito, fixture, verificadores, deadline ou especificação agora |

Não se solicita aqui aprovação genérica para executar mudanças: as opções e
seus critérios estão documentados para uma decisão concreta posterior.

## 11. Verificações desta etapa e conclusão executiva

Foi conferido que HEAD coincide com `ebf60a2`; a auditoria histórica usou
commits ancestrais disponíveis, sem fetch ou troca de branch. A especificação
técnica completa e os contratos foram confrontados com o código vigente e com
as evidências arquivadas. Foram reconferidos os valores do sumário experimental
e das medições/manifestos referenciados. Não se declarou uma nova rodada elétrica.

Os 50 PASS de software citados pertencem à etapa anterior e têm transcrição
preservada. **Não foram executados testes, SPICE, PVT ou geração Liberty nesta
etapa documental.** Nenhum arquivo existente, contrato, critério, dado ou hash
foi alterado. O único novo entregável desta etapa é este documento. Nenhum commit,
merge ou push foi realizado.

**Resposta à decisão solicitada:** há base técnica e rastreabilidade suficiente
para revisar o significado normativo dos quatro FAILs: eles condenam uma janela
de bancada sem máximo público correspondente, não provam corrupção de Q ou de
nova leitura. A revisão deve conservar a evidência e ser aditiva/versionada.
Recomenda-se A como contrato funcional com B complementar para sign-off elétrico.
Sem aprovação da política e sem qualificação das janelas pendentes, o smoke
continua não aprovado; nenhuma análise documental transforma seus FAILs em PASS.
