# Auditoria documental — fronteira do Marco 2 e fases posteriores

Data: 05/11/2026. Esta é a etapa documental da auditoria. Não se decide aqui
se o gerador, os circuitos ou as evidências existentes satisfazem os critérios.
P e S01–S17 designam as fontes identificadas em
[01](01_official_requirements.md); as diferenças estão detalhadas em
[02](02_documentation_differences.md).

## 1. Entrega obrigatória até o Marco 2

A definição oficial está em P p.4, §4, itens 10–13 e Marco 2, com confirmação
do calendário em p.6, §6. Seu núcleo é:

1. **Algoritmo de tiling:** especificar organização em linhas/colunas e
   conexão por abutment, com fronteiras das células e regras compreensíveis.
2. **Posicionamento em Python:** implementar o gerador; o desenvolvimento
   começa com placeholders e avança em paralelo à Fase 1.
3. **Netlist estrutural gerada:** representar as conexões das células,
   distinguindo-as de um modelo comportamental de memória.
4. **Integração das células reais:** testar o gerador com o primeiro conjunto
   validado da Fase 1. Dummies são estratégia de início, não substitutos das
   células reais na demonstração do Marco 2.
5. **Primeiro array pequeno em GDSII:** produzido pelo gerador, e não apenas
   um layout independente colocado na pasta de entrega.
6. **DRC e LVS do bloco completo:** correspondentes ao array gerado/exportado,
   não somente aos layouts individuais. A referência estrutural precisa ser
   sustentada pelos esquemáticos e pela seleção de folhas.

A dimensão 4×8 é exemplo no enunciado de Marco 2, mas aparece nominalmente
na linha correspondente de §6. A especificação da equipe escolhe 4×8
(S03 §§1/17), escolha que permite contemplar ambas as formulações. Não se
conclui que a proposta exige exclusivamente 4×8 em qualquer leitura, nem
que outra dimensão esteja automaticamente aceita. Uma alternativa requer
alinhamento registrado (F2-08/09 e D08).

Os pré-requisitos oficiais também devem ser examinados: ambiente e
especificação da Fase 0; folhas com esquemáticos, simulações funcionais,
layouts e DRC/LVS na Fase 1 (P p.4, itens 1–9/Marco 1; p.3, entrega Papel 1).
Iniciar Python não depende de esperar todas as folhas, mas demonstrar o
array real depende das folhas utilizadas estarem identificadas e validadas.

S05/S10 distinguem núcleo customizado e top com controle HD completo. Essa
fronteira é uma definição interna a confirmar, não uma distinção textual
do PDF. “Bloco completo” no Marco 2 deve ser associado ao objeto escolhido
para a demonstração, com suas instâncias/conexões efetivas. Não presumir
que basta uma matriz sem os circuitos necessários nem impor, a partir de P,
uma quantidade específica de registradores/células HD.

## 2. O que a proposta deixa para a Fase 3

P pp.4–5, §4, itens 14–17 e Marco 3; p.5, §5; p.1, cortes de escopo:

| Atividade/entrega | Escopo oficial | Limite de interpretação |
|---|---|---|
| Extração de parasitas | Bloco gerado, com Magic extract; tabela §2 prevê RC básica | Não exigir extração industrial detalhada; extração de conectividade para LVS não equivale automaticamente a RC |
| Timing elétrico | Varreduras em lote para tempo de acesso, setup e hold | Não está definido um valor-alvo oficial em ns ou MHz para o Marco 2 |
| Potência | Dinâmica e estática | Ensaios funcionais nominais não substituem esses relatórios; também não os tornam obrigação antecipada |
| Corners | TT, SS e FF | A adaptação dispensa variação completa de temperatura/tensão; a temperatura nominal não foi numericamente fixada em P |
| SNM estatístico | Monte Carlo reduzido; N≥200 em §5 e indicação 200–500 em §1 | Não é Monte Carlo industrial completo; método de SNM/estados e quantidade devem ser explicitados no planejamento |
| Liberty | `.lib` simplificado gerado automaticamente dos dados de timing/potência | Não basta uma interface vazia ou tabelas inventadas; inspeção da geração fica para auditoria técnica apropriada |
| Marco 3 | Relatório de caracterização + `.lib` automático até 23/nov | Alcance é o reduzido da proposta, não signoff de fabricação |

P p.5, §5 pede relatório de caracterização para **pelo menos 8×8 e 32×8**.
Esse enunciado deve permanecer na base de requisitos, salvo alteração aprovada.
Não substituir automaticamente 8×8 por 4×8 porque o texto também o chama de
“menor da faixa”. A inconsistência é de documentação/planejamento (D09).

P p.3, Papel 2 também atribui SNM, tempo e potência das folhas ao responsável
elétrico. Essa distribuição de responsabilidades não fornece datas próprias.
Não se deve transportar toda caracterização para o Marco 1 só por aparecer
junto à descrição do papel: §4 distingue função isolada na Fase 1 e
caracterização na Fase 3. Se a equipe pretendia uma caracterização de folhas
como pré-requisito específico adicional, registrar seu alcance e aprovação.

O uso antecipado de extração, medidas de atraso ou SPICE de integração é
possível como apoio de engenharia. Não transforma uma campanha parcial em
conclusão de Fase 3, nem implica que todos os requisitos dessa fase se tornem
obrigatórios para fechar o Marco 2 (D03/D04/D07).

## 3. O que a proposta deixa para a Fase 4

P p.5, §4, itens 18–20 e Marco 4; pp.5–6, §§5/6/8:

| Atividade/entrega | Obrigação posterior | Fronteira com Fase 2 |
|---|---|---|
| Modelo comportamental Verilog | Geração por template Python e validação com Icarus/GTKWave | RTL antecipado pode apoiar integração; não substitui array físico nem é exigência explícita do Marco 2 |
| LEF | Geração a partir do Magic | Uma view antecipada pode ser útil; não consta no Marco 2 |
| Faixa completa de configurações | Rodar gerador para 4, 8, 16 e 32 palavras × 8 bits | Não exigir layouts 8/16/32 como mínimo do primeiro array pequeno |
| Verificação em todas | DRC/LVS de cada configuração gerada | DRC/LVS do primeiro array é obrigatório já na Fase 2; dos quatro, no Marco 4 |
| Views por configuração | GDSII + LEF + Verilog + `.lib` | A `.lib` depende dos dados/geração da Fase 3; o pacote completo é Marco 4 |
| Marco 4 | Quatro configurações automáticas com views e DRC/LVS, até 14/dez | Não confundir com simples modelos RTL das quatro profundidades |

A Fase 5 consolida arquitetura, manual, resultados e apresentação com
**demonstração ao vivo do gerador** (P p.5, itens 21/22; p.6, §6). Documentar
fontes e uso antes disso atende à colaboração, mas a apresentação final
não vira condição retroativa específica do Marco 2.

## 4. Dependências e sobreposições a esclarecer

| Relação | O que P efetivamente diz | Implicação para planejamento, sem resolver unilateralmente |
|---|---|---|
| Fase 1 → Fase 2 | Sobreposição de 29/set a 12/out; começar com dummies e testar folhas reais quando disponíveis (p.4, §§3/4; p.6, nota §6) | Biblioteca não deve bloquear programação inicial; rastrear a troca para o primeiro conjunto real validado |
| Primeiro array → caracterização | Item 14 extrai o bloco gerado (p.4) | Preservar fonte/configuração e GDS/netlist de entrada, sem confundir seleção de arquivos com demonstração de conformidade |
| Fase 3 precisa de 8×8/32×8 | §5 manda caracterizar esses tamanhos; §4 coloca geração das quatro configurações na Fase 4 (p.5) | Definir disponibilidade antecipada dos dois casos para caracterização, ou replanejar formalmente; não exigir por isso todos os quatro layouts no Marco 2 |
| `.lib` Fase 3 → pacote Fase 4 | Marco 3 pede geração automática; Marco 4 pede `.lib` em cada configuração (p.5) | Definir como dados/corners/configurações alimentam as views finais; não inventar arcos/tabelas para preencher lacunas |
| “8×8 menor” versus faixa com 4×8 | A expressão e a faixa estão em §5, reforçada por §1 (pp.1/5) | Perguntar se 8×8 é só o menor caso **de caracterização escolhido** ou erro de redação; conservar o alvo literal até decisão |

O resumo conceitual da p.1 apresenta views antes de caracterização, enquanto
os passos datados de §4/§6 colocam caracterização na Fase 3 e views digitais
na Fase 4. Para a matriz foram transcritos os passos e marcos datados, sem
usar a frase conceitual como autorização para inverter silenciosamente as
fases. As dependências acima precisam ser articuladas pela equipe.

## 5. Compromissos internos adicionais

As fontes S03–S07, S10/S11 e S17 acrescentam escolhas/gates: protocolo
síncrono público, captura, ausência de reset, decoder dinâmico selecionado,
controle de fases, síntese HD, GLS, tri-state, acesso transistor-level,
startup, auditorias de evidência e separação CORE/F2-FIS. D01–D07 explicam
quais são detalhamentos, antecipações ou ampliação de aceite.

Para a auditoria técnica, usar duas camadas:

- **Obrigação oficial:** itens de P necessários ao Marco 2, com suas
  dependências F0/F1 e contingências legitimamente acionadas.
- **Compromisso interno confirmado:** critérios que a equipe decidiu manter
  para a solução escolhida, vinculados à versão e à autoridade dessa decisão.

A separação não autoriza ignorar uma inconsistência funcional da solução
escolhida nem eliminar trabalho. Serve para não exigir `.lib`, corner SS/FF
ou views finais como se estivessem escritos no Marco 2, e para não apresentar
apenas síntese/GLS como se substituíssem o gerador/GDS/DRC/LVS oficiais.
Não se decide nesta etapa se algum desses problemas ocorre no projeto.

## 6. Decisões por momento de necessidade

As decisões não estão todas no mesmo nível de urgência. “Antes do Marco 2”
abaixo significa antes da deliberação de seu aceite, não exigência de que
sejam reabertas escolhas já formalmente documentadas.

| ID | Momento | Questão a alinhar | Base documental | Registro esperado / efeito |
|---|---|---|---|---|
| Q01 | Antes da deliberação do Marco 2 | Confirmar versão da especificação e inventário de folhas/primeiro bloco real | P p.4, itens 3/13; p.5, §5; S03 §1.1; conflito S13 versus S02/S03 (D05/D06) | Identificar decisões competentes e referência de engenharia; não aprovar tecnicamente o inventário só por constar no documento |
| Q02 | Antes da deliberação do Marco 2, se houver alternativa dimensional | Primeiro array 4×8: manter alvo local ou propor equivalente? | P p.4, Marco 2, versus p.6, §6; F2-08/09 | Manter 4×8 evita conflito prático entre as redações; aceitar outro tamanho requer interpretação explícita |
| Q03 | Antes da deliberação do Marco 2 | F2-DIG/top HD/acesso elétrico são compromissos internos ou alteração acadêmica aprovada? | P p.4; S17 slide 3; S05/S10; D01–D03 | Localizar aprovação da ampliação/reordenação ou declarar camadas separadas. Não rebaixar o Marco 2 a RTL |
| Q04 | Antes de executar a Fase 3 | Como obter 8×8 e 32×8 a tempo da caracterização, e o que significa “menor”? | P p.5, §5, versus itens 14–20; D09 | Planejar casos antecipados ou alteração formal de sequência/alvos. Não torna automaticamente quatro layouts exigíveis na Fase 2 |
| Q05 | Antes de fixar a campanha da Fase 3 | Temperatura/supply e escopo TT/SS/FF; necessidade real de contingência | P p.1 e p.6, §7; S03 §§20/24; D07/D12 | Condições identificadas; eventual corte justificado/documentado. 27 °C experimental não é decisão universal já aprovada |
| Q06 | Antes da campanha SNM na Fase 3 | Método/estados e amostras, respeitando N≥200 | P pp.1/5; S03 §§7/20; D10 | Protocolo de SNM reduzido; não presumir que outro teste de mismatch o substitui |
| Q07 | Antes de uma escolha de projeto que dependa dela | Prioridade final entre robustez, desempenho, potência e área | S03 §§7/24; P p.5, §5, validação da especificação | P não fixa otimização industrial nem meta numérica. Não converter pendência genérica em bloqueio do Marco 2 sem demonstrar seu efeito sobre o primeiro array |
| Q08 | Antes da generalização dos arrays para caracterização/Fase 4 | Estratégia de decoders maiores e geração por configuração | S03 §§9/21/24; P p.5, itens 18–20/§5 | Resolver quando necessário a 8×8/32×8, possivelmente já para a Fase 3; não exige rediscutir o decoder do primeiro array nesta etapa |
| Q09 | Ao replanejar a entrega final, se necessário | Acionar redução de configurações e depois de corners? | P p.6, §7 | Corte condicional, com motivação e alcance; nunca dispensar gerador ou DRC/LVS. Não presumir corte por falta de prazo |
| Q10 | Para organização e apresentação acadêmica | Equipe real, papéis e evidência da aprovação do replanejamento | P pp.1/3/4; S02/S17; D13/D14 | Resolver inconsistência três/quatro e autoria das decisões; não criar integrante nem gate elétrico inexistente |

Q01–Q03 não pedem uma caracterização de Fase 3: pedem que a equipe saiba
**qual obrigação e qual objeto está deliberando**. Q04–Q08 não são bloqueios
genéricos ao Marco 2. Sua antecipação só se justifica quando uma dependência
real ou decisão do primeiro array o exigir. Q09 é eventual; Q10 é alinhamento
organizacional. Os formulários exatos de aprovação não são prescritos em P.

## 7. Condições documentais para avaliar o Marco 2 depois

A próxima auditoria deverá conseguir localizar, sem depender de um parecer
prévio de aceite:

- Fonte oficial e eventuais mudanças aprovadas, com versão e alcance.
- Especificação/inventário do array escolhido e folhas reais de entrada.
- Algoritmo de tiling/abutment e código/configuração de posicionamento.
- Registro do uso inicial de placeholders e da integração das folhas reais.
- Netlist estrutural emitida e GDSII gerado, vinculados à mesma configuração.
- Relatórios DRC/LVS com geometria, referência e abrangência do **bloco completo**.
- Relação das evidências de F0/F1 que constituem suas dependências, incluindo
  funcionamento do ambiente, tutoriais e biblioteca de folhas.
- Lista separada dos requisitos internos adicionais, de sua autoridade e
  das perguntas de caracterização/futuras que não pertencem ao Marco 2.

Esses são tipos de prova derivados de P e formas de rastreá-los, não resultados
obtidos nesta execução. Reproduzir um passo na etapa técnica só será decidido
após inspeção da evidência correspondente, sem exigir novas simulações por
mera contagem. Não se executou síntese, GLS, SPICE, DRC/LVS ou extração aqui.

A pergunta desta etapa fica delimitada: até o Marco 2, a proposta exige
ambiente/especificação e biblioteca de folhas como base, e **gerador Python
com netlist estrutural e primeiro array real em GDSII, com DRC/LVS do bloco
completo**. O atendimento a esses critérios e a suficiência das evidências
permanecem para a auditoria técnica seguinte.
