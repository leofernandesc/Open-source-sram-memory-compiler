# Auditoria documental — diferenças entre proposta e registros locais

Data: 05/11/2026. Comparação documental no commit
`3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6`. Não se avaliam código, geometria,
qualidade das simulações ou atendimento de requisitos nesta etapa.
As fontes P e S01–S17 estão identificadas em
[01 — requisitos oficiais](01_official_requirements.md).

## 1. Regra de leitura

Uma exigência adicional pode ser útil e coerente com o projeto, sem constar
do marco oficial. Uma atividade antecipada também não é, por si só, mudança
indevida de arquitetura. A diferença importa quando ela passa a ser apresentada
como condição **oficial** de fechamento, sem decisão competente que a sustente.

Esta comparação separa: contradição textual, ampliação interna, detalhamento
compatível, ambiguidade da própria proposta e registro histórico. Nenhum desses
rótulos significa defeito da implementação. Não se usam aceites anteriores
para decidir qual interpretação deve prevalecer.

## 2. Fronteiras entre fases e aceites

### D01 — Views e qualificação temporal atribuídas globalmente à Fase 2

- **Proposta:** Fase 2 termina no array pequeno gerado em GDSII com DRC/LVS
  completo (P p.4, §4, itens 10–13/Marco 2). A `.lib` automática é Fase 3
  (p.5, itens 15–17/Marco 3); Verilog, LEF e quatro configurações completas
  são Fase 4 (p.5, itens 18–20/Marco 4).
- **Registro local:** S03 §1.1 atribui “generated macro views” e qualificação
  temporal de sistema à Fase 2. S09, “Remaining workflow and Phase 2”, item 3,
  inclui GDSII, LEF, Verilog, Liberty e qualificação das configurações como
  próximo estágio Fase 2. S08, “Binding scope decision”, também agrupa
  compiler/views nessa fase.
- **Diferença:** mistura o projeto completo com o mínimo do Marco 2. S03 §§18,
  20/21 contêm obrigações globais coerentes com P, mas **não têm alocação de
  fase própria**; não devem ser lidos automaticamente como todos exigíveis
  na Fase 2 por causa da redação ampla de §1.1.
- **Decisão/aprovação:** esses registros de engenharia não apresentam aprovação
  específica dos orientadores transferindo os itens 17–20 para o Marco 2.
  S05/S07/S10, mais recentes, já deixam caracterização/Liberty para depois.
- **Tratamento documental:** na próxima revisão, separar requisito global,
  entrega antecipada e requisito do Marco 2. Se a equipe quiser manter a
  expansão como compromisso acadêmico, identificar a aprovação. Não se altera
  agora nenhuma especificação histórica.

### D02 — F2-DIG, síntese SKY130HD e GLS como gate de Fase 2

- **Proposta:** Python, folhas reais, netlist estrutural, GDSII e DRC/LVS no
  Marco 2; não há obrigação de sintetizar controle ou rodar GLS (P p.4).
  A validação do modelo comportamental com Icarus/GTKWave aparece no item 18,
  Fase 4 (p.5); síntese digital não é obrigação explícita de nenhuma fase de P.
- **Registro local:** S05, “Independent acceptance gates”; S07, checkpoints;
  S10, F2-DIG; S11, D11–D16; S17 slides 3/8/12/15 exigem mapeamento HD,
  macro black box, tri-state e GLS. S02 institucionaliza frentes digitais.
- **Diferença:** frente adicional e antecipação parcial da Fase 4. Não é
  equivalente a redefinir o Marco 2 oficial só como RTL/síntese/GLS.
- **Decisão/aprovação:** S17 slide 3 chama F2-DIG de **proposto** e registra
  expressamente a necessidade de aprovação da equipe/orientador. S04 abre
  com “Approved planning decisions”, mas não identifica ali quem aprovou
  alteração do marco acadêmico ou onde está o ato correspondente.
- **Tratamento:** manter duas perguntas na auditoria técnica: conformidade
  ao Marco 2 e conformidade ao compromisso digital interno. A ausência de
  uma obrigação em P não autoriza rotular como concluído um gate interno
  explicitamente mantido pela equipe; tampouco esse gate deve ser imputado a P.

### D03 — SRAM síncrona completa, acesso elétrico e partida como gates adicionais

- **Proposta:** simulação funcional de cada folha é Fase 1 (P p.4, item 7).
  Teste do gerador com folhas reais e DRC/LVS do array são Fase 2 (itens 13 e
  Marco 2). Não há uma campanha SPICE específica de acesso completo, partida
  com rampas ou registradores sintetizados prescrita no Marco 2.
- **Registro local:** S05 separa CORE e F2-FIS, exige write/read real, startup,
  cargas/captura e repetição no top digital-físico. S10/S11 adicionam
  perturbações, barramento, captura, testes negativos e rastreabilidade.
  S17 slides 13/15 já propõem acesso real à macro.
- **Diferença:** critérios de integração mais restritivos e detalhados. Os
  pontos de observação e testes não redefinem os itens 14–17 de caracterização.
- **Decisão/aprovação:** há planejamento de engenharia, mas S10 ressalva que
  seu aceite não é aprovação dos orientadores. Não foi localizada ratificação
  específica dessa ampliação acadêmica no corpus examinado.
- **Tratamento:** catalogar como compromisso interno adicional. O teste do
  gerador continua obrigatório; um teste funcional pode ajudá-lo, sem inventar
  que P exige os contadores, cinco rampas, 20 FF ou top SKY130HD encontrados.

### D04 — Conectividade extraída versus PEX e caracterização

- **Proposta:** LVS completo já é exigido nos Marcos 1/2; extração de parasitas
  é explicitamente item 14, Fase 3 (P p.4). A tabela de ferramentas prevê
  extração RC básica com Magic/ngspice (p.2). Não exige PEX industrial detalhado.
- **Registro local:** S03 §1.1 seleciona PEX de folhas na entrega Fase 1;
  S08/S09 incluem esse artefato. S05/S07/S10 distinguem extração para
  conectividade/junções de RC detalhado das interconexões, deixado para depois.
- **Diferença:** há antecipação ou evidência adicional por folha; isso não
  transforma PEX RC em condição oficial do Marco 1/2. Extrair a rede para
  LVS tampouco demonstra, sozinho, o item 14 de caracterização parasítica.
- **Tratamento:** examinar depois que tipo de extração sustenta cada afirmação.
  “Sem iniciar Fase 3” deve ser entendido como fronteira da campanha, não
  negação de uso anterior de técnicas também empregadas em caracterização.
  Não concluir agora nada sobre o conteúdo das netlists.

## 3. Escolhas arquiteturais e autoridade das decisões

### D05 — Seis folhas e decoder dinâmico: seleção local versus texto oficial

- **Proposta:** P p.3, Papéis 1/2, menciona bitcell, sense amplifier, driver
  de wordline, pré-carga e decoder de linhas/colunas. O resumo da p.6 enumera
  bitcell, sense amp, driver e pré-carga; P não fixa exatamente seis famílias,
  33 MOS, keepers, NAND dinâmico ou um arquivo de decoder.
- **Registro local:** S02/S03 §1.1 e §9 fixam seis folhas e o decoder de
  Leonardo. S08 registra decisão do proprietário em 28/10; S09 registra a
  disposição de engenharia de 29/10 e reserva revisão acadêmica posterior.
- **Diferença:** detalhamento/seleção de engenharia, não transcrição literal
  de P. O suporte à escrita precisa ser explicitado no inventário, mesmo sem
  uma lista oficial que nomeie write driver separado.
- **Conflito secundário concreto:** S13, nos parágrafos antes e dentro de
  “Escopo posterior à Fase 1”, ainda apresenta decoder candidato em
  `cells/row_decoder_2to4.spice` e realocação para Fase 2 pendente de validação.
  Isso diverge da referência atual declarada por S02/S03. S08/S09 já dão
  contexto de substituição histórica, mas S13 conserva linguagem de presente.
- **Tratamento:** na auditoria seguinte, identificar uma referência de circuito
  a partir da seleção local rastreada, sem julgá-la agora. Para o encerramento
  acadêmico, registrar o conjunto de folhas e a disposição dessa realocação;
  não contar uma decisão de proprietário como aprovação automática de escopo.

### D06 — Protocolo público e circuito de controle não especificados por P

- **Proposta:** Single-Port 6T/SKY130 e largura/faixa de geração (P pp.1/5).
  Não define sincronismo, bordas, nomes/polaridade de sinais, DATA bidirecional,
  ausência de reset, número de FF, wordline por palavra ou taps de atraso.
- **Registro local:** S03 §§3–6/13–17, S04 DIG-01..11 e S05/S06 estabelecem
  essas escolhas, inclusive 001/010, captura na subida, leitura na descida,
  máscara viva, sem reset/FSM/column mux e decoder dinâmico.
- **Diferença:** especificação do produto desenvolvida pela equipe, compatível
  em princípio com o detalhamento solicitado na Fase 0. Não se conclui aqui
  compatibilidade elétrica ou aprovação formal de cada escolha.
- **Aprovação e pendências:** S03 §§7/9/20/24 ainda pede confirmação para
  prioridade final de otimização, estratégia dos decoders maiores e temperatura.
  S04 reconhece diferenças do TCC/OpenRAM, o que evita apresentá-los como
  protocolos idênticos, mas suas referências não substituem decisão da equipe.
- **Tratamento:** auditar depois esses contratos como requisitos internos
  separados. Consultar quem validou qual versão, sem exigir valores temporais
  que P não prescreveu para o Marco 2.

### D07 — Condição experimental não é corte de caracterização aprovado

- **Proposta:** três corners TT/SS/FF sem sweep completo de tensão/temperatura
  (P p.1); timing/potência/SNM e `.lib` na Fase 3 (pp.4–5). A contingência da
  p.6 permite reduzir corners para TT, se necessário, com limitação documentada.
- **Registro local:** S01/S05/S06/S10/S16 delimitam ensaios TT/1,8 V/27 °C,
  clock de 20 ns e parâmetros públicos não caracterizados. S03 §20 ainda
  exige três corners e deixa temperatura nominal pendente.
- **Diferença:** nominal experimental e obrigação futura não são equivalentes.
  Não há contradição automática em deixar limites sem caracterização na Fase 2;
  haveria confusão se TT experimental fosse usado como dispensa permanente de
  SS/FF ou se 20 ns fosse requisito oficial/Fmax.
- **Tratamento:** caracterizar o compromisso Fase 3 conforme P ou registrar
  acionamento explícito da contingência. Não se inferiu esse acionamento de
  resultados existentes. P não exige signoff industrial, yield ou PVT irrestrito.

## 4. Ambiguidades oficiais e lacunas de rastreabilidade

| ID | Fonte oficial versus fonte secundária | Diferença/questão | Decisão ou verificação documental necessária |
|---|---|---|---|
| D08 | P p.4, Marco 2: 4×8 como exemplo; p.6, §6: primeiro array 4×8. S03 §§1/17 e S17 slides 3/13: alvo 4×8 | O texto oficial não permite afirmar simultaneamente que a dimensão é exclusivamente obrigatória e somente uma ilustração em todas as seções | Registrar interpretação. Manter 4×8 pode atender a ambas as redações; discutir qualquer alternativa antes de aceitá-la como equivalente |
| D09 | P p.5, §5 pede caracterização de 8×8 e 32×8, chama essas configurações de menor/maior; p.1 e o próprio §5 incluem 4×8. S03 §§1/20 conserva a faixa e os dois alvos | 8×8 não é a menor da faixa declarada. Além disso, a Fase 3 precisa de dois tamanhos cuja geração completa aparece na Fase 4 | Esclarecer quais arrays devem estar disponíveis para caracterizar na Fase 3 e o sentido de “menor”; não substituir 8×8 por 4×8 unilateralmente |
| D10 | P p.1 apresenta SNM com 200–500 amostras; p.5, §5 fixa N≥200; S03 §20 usa N≥200 | O mínimo é explícito; teto 500 e modalidade de SNM não estão igualmente definidos. Screens determinísticos e mismatch de outros circuitos não são automaticamente esse requisito | Fixar método de SNM/estados e número de amostras para a Fase 3, sem exigir Monte Carlo industrial completo nem declarar que a campanha já existe |
| D11 | P p.4, itens 1–4 e 10/11: setup testado, tutoriais coletivos, tiling/abutment e início com placeholders. S14/S03 §22/S07 privilegiam ambiente e fluxo atual | As fontes principais não oferecem um índice único que vincule cada uma dessas atividades à obrigação oficial; o resultado final não descreve necessariamente a trajetória inicial | Procurar registros apropriados na etapa 2. Ausência de menção no índice não prova ausência de atividade. Não fabricar retrospectivamente histórico de tutorial/placeholder |
| D12 | P p.6, §7: contingências ordenadas e preservação de gerador/DRC/LVS. S03 §§1/19–21 mantém quatro configurações e três corners | Redução eventual tem previsão oficial, mas não é automaticamente política ativa do repositório | Se necessária, identificar gatilho, configurações/corners preservados, aprovação competente e limites documentados; não cortar o núcleo obrigatório |
| D13 | P p.1 título e p.3 indicam quatro pessoas, mas tabela p.1/item 2 p.4 dizem três e §3 enumera somente Papéis 1–3. S02 distribui três proprietários; S17 divide quatro frentes | Inconsistência organizacional na própria proposta e mudança de distribuição de responsabilidades | Registrar equipe real e atribuição dos papéis, sem transformar frente de trabalho em pessoa fictícia ou novo gate físico |
| D14 | S03 §25, referência 1 genérica; S07 chama o plano de aprovado; S17 slide 3 chama a ampliação de proposta | Falta uma referência inequívoca, nas formulações genéricas, ao PDF/versão e ao ato de aprovação da reordenação | Esta auditoria identifica o PDF por hash e separa autoridades. Solicitar o registro de aprovação quando uma ampliação for usada como condição acadêmica |

“Não localizado” refere-se ao corpus documental examinado, não a uma busca
por toda comunicação privada da equipe. Nenhuma diferença acima autoriza
alterar circuito, apagar evidência, desconsiderar problema real ou mudar P.

## 5. Históricos e estado atual

S08 é identificado como baseline de 28/10, anterior à revisão com keepers;
S09 é handoff de engenharia de 29/10. O estado e a referência de cada um não
são mutuamente intercambiáveis (S08 abertura; S09 “Closure decision”).

S15 registra uma implementação digital local de 30/10 e lista síntese como
próxima frente. S14 contém inventários datados e alerta que a tag antiga do
container não determina o ambiente atual. S12 também conserva texto de
handoff digital junto a descrição de protótipo posterior. Isso exige leitura
por data/seção, não conclusão de que o toolchain atual está ausente.

S07, “Local delivery” e fim da auditoria de 04/11, e S10, ações imediatas,
conservam frases de publicação pendente. S01 e S16 explicitam o contexto de
publicação e preservação dos registros. Na referência Git conferida desta
etapa, a branch publicada é `3d14880`. Essas frases antigas não provam uma
pendência de Git atual nem alteram o Marco 2; tampouco publicação prova
conformidade acadêmica. Não foram corrigidas retrospectivamente.

## 6. Inventário de diferenças sem julgamento da implementação

- **Obrigações oficiais a rastrear melhor no índice de evidências:** tutoriais
  coletivos, versão/validação da especificação, trajetória dos placeholders,
  semântica de abutment e vínculo gerador → netlist → GDS → DRC/LVS do array
  (F0-03/04/05 e F2-01/03/04/07/10/11). Não se afirma que faltam tecnicamente.
- **Acréscimos de aceite interno:** F2-DIG, síntese/GLS, top HD, captura,
  tri-state, startup, acesso transistor-level e verificadores negativos
  (D02/D03/D06). Sua autoridade e alocação devem permanecer identificadas.
- **Atividades futuras indevidamente agrupadas sob Fase 2 em algumas fontes:**
  Liberty, views completas e qualificação temporal/configurações, sobretudo
  S03 §1.1 e S09, lista posterior (D01).
- **Critério potencialmente mais permissivo a impedir:** trocar o array
  gerado/verificado por folhas isoladas, RTL ou relatório de selo; ou chamar
  extração só de conectividade de caracterização parasítica. Esta é uma regra
  para a auditoria seguinte, não constatação de que o projeto o fez (D02/D04).
- **Inconsistências para alinhamento:** 4×8 exemplo/alvo, 8×8 denominado menor,
  disponibilidade dos arrays para a Fase 3, responsabilidades e aprovação
  da reordenação (D08/D09/D13/D14).

Os pontos não têm estados de conformidade. A próxima etapa deve examinar
as evidências diretamente, usando a matriz oficial e uma camada separada
para os compromissos internos que a equipe confirmar.
