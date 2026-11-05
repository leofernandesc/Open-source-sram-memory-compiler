# Auditoria documental — requisitos oficiais das Fases 0, 1 e 2

Data: 05/11/2026. Etapa 1 de 3: definição dos critérios de avaliação, sem
julgamento da implementação. Este documento não confirma resultados de
ferramentas, não concede aceite e não encerra nenhuma fase.

## 1. Referência e estado encontrado

Referência publicada conferida: `integration/phase2-4x8`, commit
`3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6`. A referência remota de mesmo nome
apontava para esse commit. A árvore local estava limpa, sem diferenças staged,
unstaged ou arquivos novos não ignorados. A branch documental
`review/official-scope-phases-0-2` foi criada diretamente desse commit.
As branches de integração não são destino das alterações desta etapa.

### Fonte principal P

Lidas integralmente as páginas físicas 1–6 de **Proposta Adaptada de Projeto:
Memory Compiler para SRAM (Single-Port)**, versão open-source/gratuita,
execução de 08/09 a 19/12/2026, incluindo tabelas, notas e contingências.

- Nome solicitado: `Proposta_Adaptada_Memory_Compiler_OpenSource_09092026(1).pdf`.
- Arquivo localizado: `/home/leofernandesc/Downloads/Proposta_Adaptada_Memory_Compiler_OpenSource_09092026.pdf`.
- Segunda cópia: `/home/leofernandesc/Downloads/Arquivo/2026-09-22/Documentos/Proposta_Adaptada_Memory_Compiler_OpenSource_09092026.pdf`.
- Ambas têm SHA-256 `59021f96db0202678b9ec4c9f6195fceeb95cfd60a8ecf5c5a3845a72c332644`.
- Título, seis páginas, período, seções 1–8 e marcos correspondem à descrição
  recebida. A criação/modificação registrada no PDF é 09/09/2026.

**Limite de identidade:** o nome exato com `(1)` não foi localizado; não foi
possível comparar seus bytes com as cópias disponíveis. A fonte desta análise
é o PDF acima, identificado por conteúdo e hash, e não a especificação do
repositório como substituta. Se a cópia com `(1)` tiver conteúdo diferente,
reconciliar a matriz antes da auditoria técnica. O PDF é entrada externa,
não incluída neste commit de três documentos; outro auditor precisa obter
a cópia identificada pelo hash. Referências como `P p.4, §4, item 10` indicam
página física, seção e item da proposta.

### Fontes secundárias consultadas

Conteúdo no commit de referência. Relatos de resultados foram lidos apenas
para identificar critérios e fronteiras; seus números e rótulos de aceite
não foram usados como prova de atendimento.

| Código | Documento | Partes relevantes |
|---|---|---|
| S01 | [README](../../README.md) | Escopo, entregas das Fases 1/2 e workflow |
| S02 | [GITFLOW](../../GITFLOW.md) | Responsabilidades, seis folhas e frentes digitais |
| S03 | [Especificação técnica](../../specs/technical_specification.md) | §§1/1.1, 3–6, 9, 17–25 |
| S04 | [Contrato digital](../../specs/sram_4x8_digital.md) | Abertura, DIG-01..11, fronteira e diferenças das referências |
| S05 | [Interface físico-digital](../../specs/phase2_physical_interface.md) | Sequência, startup e gates internos |
| S06 | [Contrato temporal](../../specs/sram_4x8_timing_contract.md) | §§1, 3, 7–10 |
| S07 | [Execução da Fase 2](../phase2_execution.md) | Checkpoints, trabalho físico e limites datados |
| S08 | [Decisão das seis células](../phase1_six_cell_delivery.md) | Decisão de 28/10 e escopo atribuído à Fase 2 |
| S09 | [Handoff da Fase 1](../phase1_closure_20261029.md) | Decisão de engenharia e trabalho posterior |
| S10 | [Quadro de aceite da Fase 2](../phase2_review_20261104_acceptance.md) | Critérios F2-DIG/F2-FIS e ressalvas, sem adotar suas conclusões |
| S11 | [Matriz interna da Fase 2](../phase2_review_20261104_requirements.md) | Requisitos D/P/E, inclusive adicionais |
| S12 | [Interfaces e reprodução](../sram_4x8_interfaces.md) | Modelo, black box, síntese e handoff |
| S13 | [Especificação da bitcell](../../specs/sram_6t_cell.md) | Folhas e “Escopo posterior à Fase 1” |
| S14 | [Ambiente](../../tools/ENVIRONMENT.md) | Inventário e registros datados |
| S15 | [Implementação digital de 30/10](../phase2_digital_implementation_20261030.md) | Escopo do registro local e próxima frente |
| S16 | [Estado complementar de 04/11](../phase2_extension_state_20261104.md) | Nota de estado e preservação de históricos |
| S17 | `Planejamento_Fase_2_SRAM.pptx`, entrada externa em Downloads | 16 slides; sobretudo 3, 5–8, 13 e 15 |

S17 tem SHA-256 `82f257fafbb54c3dbdfacbb9dff3c4ef4d58a65d0fca5809beac9d112e5dfb3b`.
Foi lido como proposta de replanejamento: o slide 3 identifica F2-DIG como
proposto e exige aprovação da equipe e do orientador para a reordenação.
O arquivo também permanece externo ao commit.

## 2. Hierarquia e interpretação

1. **P — proposta adaptada oficial:** fases, atividades, marcos e cortes.
2. **Alterações explicitamente aprovadas e documentadas** pela equipe ou pelos
   orientadores, com autoria, competência e escopo identificados.
3. **Especificações do repositório:** detalhamento da solução e seus contratos.
4. **Relatórios e registros históricos:** válidos para sua versão/contexto.

Uma seleção de circuito registrada por um integrante pode fixar a referência
de engenharia. Não demonstra sozinha alteração aprovada de marco acadêmico.
Nos documentos consultados não foi identificado registro formal substituindo
as fases de P. Isso não afirma inexistência de atas/mensagens externas. S17
reconhece a aprovação necessária; S09/S10 separam handoff técnico de aceite
pelos orientadores. P não exige formulário ou assinatura específicos.

Para a auditoria seguinte: extrair obrigação antes de escolher teste; registrar
conflitos sem resolvê-los silenciosamente; não antecipar Fases 3/4; não tomar
contagem de testes, MOS, selo anterior ou o gerador como único oráculo.
As especificações locais detalham requisitos, mas não redefinem retroativamente P.

## 3. Escopo e cronograma oficiais

P p.1, §1; p.5, §5; p.6, §8: SRAM **Single-Port 6T em SKY130**, largura fixa
8 bits e faixa final 4/8/16/32 palavras. Dual-Port é trabalho futuro opcional;
largura variável é extensão eventual em dezembro. As views finais são GDSII,
LEF, Verilog comportamental e `.lib` simplificado por configuração.

| Fase | Período oficial em 2026 | Atividades/entrega | Marco ou critério explícito |
|---|---|---|---|
| 0 — Setup | Semana 1, 08–14/set | Ferramentas, tutoriais, especificação e Git | Não há Marco 0 nomeado; §6 pede toolchain instalado/testado e especificação fechada |
| 1 — Arquitetura e células-folha | Semanas 2–5, 15/set–12/out | Topologias, esquemáticos, função isolada, layouts e DRC/LVS | Marco 1, 12/out: todas as folhas com DRC/LVS limpo |
| 2 — Desenvolvimento do gerador | Semanas 4–8, 29/set–02/nov | Tiling/abutment, Python com placeholders, netlist e células reais | Marco 2, 02/nov: array pequeno em GDSII, DRC/LVS do bloco completo |
| 3 — Caracterização | Semanas 9–11, 03–23/nov | Extração, timing/potência, SNM Monte Carlo e `.lib` | Marco 3, 23/nov: relatório e `.lib` automático |
| 4 — Views digitais e integração final | Semanas 12–14, 24/nov–14/dez | Modelo Verilog/validação, LEF, quatro configurações e DRC/LVS | Marco 4, 14/dez: quatro configurações com GDSII/LEF/Verilog/`.lib`, DRC/LVS |
| 5 — Documentação e apresentação | Semana 15, 15–19/dez | Documentação, manual e demonstração ao vivo | Itens 21/22; não há Marco 5 nomeado |

Referências: P p.4, §4, itens 1–14 e Marcos 1/2; p.5, §4, itens 15–22 e
Marcos 3/4; pp.5–6, §6. São datas **planejadas**; não se avalia pontualidade
nesta etapa. Fases 1/2 sobrepõem-se entre 29/set e 12/out. Placeholders
permitem começar sem esperar todas as folhas reais (P p.4, final de §3 e
itens 11/13; p.6, nota de §6).

## 4. Matriz para a auditoria seguinte

Não há coluna de atendimento. Os critérios indicam evidência a **examinar
na etapa 2**, não resultados verificados agora. As 30 linhas separam obrigações,
orientações, dependências e questões abertas, e não 30 obrigações equivalentes.

Categorias: **obrigatório** é atividade, entrega ou restrição expressa;
**recomendação** é orientação de método sem novo marco de conclusão;
**exemplo** é ilustração identificada como tal; **dependência** liga insumos
ou etapas; **decisão pendente** exige validação/interpretação ainda não
demonstrada documentalmente. Pair design e referências de estudo foram
classificados como orientações de método, sem tornar opcional o tutorial
coletivo ou a definição de topologias expressamente pedidos nos itens 2 e 5.

### Fase 0 — 10 itens

| ID | Fase | Referência oficial | Requisito | Categoria | Critério de verificação | Documento secundário | Divergência documental | Observações |
|---|---:|---|---|---|---|---|---|---|
| F0-01 | 0 | P p.4, §4, item 1; p.2, §2 | Instalar Magic, Xschem, ngspice, Netgen, open_pdks/SKY130, gdstk, Icarus Verilog e Git | Obrigatório | Inventário de instalação/configuração e identificação das ferramentas/PDK usados | S03 §22; S14 | Yosys/OpenROAD são acréscimos locais | A alternativa de escrita GDS por Magic/gdstk não apaga gdstk da lista literal do setup |
| F0-02 | 0 | P pp.5–6, §6, semana 1 | Toolchain instalado e testado | Obrigatório | Evidência de funcionamento e acesso ao SKY130, com comandos/configurações e saídas identificáveis | S14, “Checar o ambiente” | Inventário textual não equivale sozinho a funcionamento | P não fixa versões, Docker ou CI |
| F0-03 | 0 | P p.4, §4, item 2; p.6, §7 | Executar tutoriais oficiais SKY130 em conjunto | Obrigatório | Identificar tutoriais e registro da execução/aprendizado coletivo | S14 | Fontes principais não individualizam esse registro coletivo | P menciona três participantes no item 2 e quatro no título; não inventar presença |
| F0-04 | 0 | P p.4, §4, item 3; pp.5–6, §§5/6 | Definir/documentar especificação final | Obrigatório | Versão identificada, parâmetros decididos e relação com §5 de P | S03; S04–S06 | S03 §24 conserva decisões abertas | Distinguir pendência do primeiro array e pendência futura |
| F0-05 | 0 | P p.5, título de §5 | Validar a especificação proposta com equipe/orientador | Decisão pendente | Localizar registro com autoria, data, versão e alcance da validação | S03 §§7/9/20/24; S04 abertura; S17 slide 3 | Afirmação genérica de planejamento aprovado não identifica a instância acadêmica | P não exige formulário ou assinatura específicos |
| F0-06 | 0 | P p.4, §4, item 4 | Criar Git organizado com /cells, /scripts, /sims e /docs | Obrigatório | Estrutura versionada e histórico de criação/organização | S01, estrutura; S02 | Pastas adicionais são compatíveis | Este GitFlow não é uma obrigação de P |
| F0-07 | 0 | P p.4, §3, primeiro tópico | Git compartilhado desde o início e specs comum | Obrigatório | Histórico de disponibilização e localização comum das especificações | S02/S03/S12 | Documento atual não prova sozinho “desde o dia 1” | Pode exigir registro histórico, não execução EDA |
| F0-08 | 0 | P pp.1–3, §§1/2; p.5, §5 | Usar fluxo gratuito/open-source e SKY130 | Obrigatório | Identificar tecnologia, ferramentas e complementos/substituições | S03 §§2/22; S14 | SKY130A/1,8 V e HD são detalhamentos locais | Não restaurar toolchain comercial ou qualificação industrial excluídos |
| F0-09 | 0 | P p.3, §2, após a tabela | Preferir Ubuntu no ambiente Linux | Recomendação | Descrever ambiente e compatibilidade; outra distribuição não é falha por si só | S14 | Docker é escolha local | P usa “Ubuntu recomendado” |
| F0-10 | 0 | P p.3, §3, organização | Pair design/aprendizado cruzado nas semanas 1–2 | Recomendação | Consultar registros de sessões/troca de conhecimento | S02, colaboração; S14 | Distribuição de proprietários não substitui tutorial coletivo | Orientação de organização; não criar bloqueio quantitativo novo para Marco 2 |

### Fase 1 — 9 itens

| ID | Fase | Referência oficial | Requisito | Categoria | Critério de verificação | Documento secundário | Divergência documental | Observações |
|---|---:|---|---|---|---|---|---|---|
| F1-01 | 1 | P p.4, §4, item 5 | Definir topologias da bitcell 6T e do sense amplifier | Obrigatório | Descrição e correspondência com esquemáticos/netlists selecionados | S03 §§7/12; S13 | SA detalhado e decoder dinâmico são escolhas locais | P não fixa MOS do SA/decoder ou keepers |
| F1-02 | 1 | P p.4, §4, item 5, referências | Usar artigos abertos/exemplos SKY130 como referências | Recomendação | Referências técnicas e relação com topologias | S03 §25; S13 | OpenRAM/TCC não substituem P para definir fases | Não há quantidade mínima de artigos |
| F1-03 | 1 | P p.4, §4, item 6 | Esquemático de cada folha no Xschem | Obrigatório | Inventário de esquemáticos e netlists correspondentes, pinos e seleção | S03 §1.1; S08/S09 | Exatamente seis folhas é seleção da equipe | Imagem/layout não substituem automaticamente esquemático |
| F1-04 | 1 | P p.4, §4, item 7 | Simular isoladamente cada célula no ngspice | Obrigatório | Bancada, modelos, estímulos e relatório/ondas das funções pertinentes: escrita/leitura/retenção da bitcell e funções dos periféricos | S08/S09/S13 | Matrizes e margens locais ampliam o item funcional | Não exigir retenção de bitcell de um periférico sem armazenamento |
| F1-05 | 1 | P p.4, §4, item 8 | Fazer layout no Magic, célula por célula | Obrigatório | Layout físico e versão correspondente ao esquemático selecionado | S03 §1.1; S08/S09 | PEX por folha é entrega adicional | Aparência não demonstra correção |
| F1-06 | 1 | P p.4, §4, item 9 e Marco 1; p.3, Papel 1 | DRC limpo de todas as folhas | Obrigatório | Relatório vinculado à geometria e às regras SKY130 | S03 §§1.1/19; S08/S09 | Negativos/tolerâncias detalham a verificação local | P não especifica deck industrial de signoff |
| F1-07 | 1 | P p.4, §4, item 9 e Marco 1; p.3, Papel 1 | LVS limpo de todas as folhas | Obrigatório | Referência, extração e comparação identificando células abrangidas | S03 §§1.1/19; S08/S09 | Critérios locais detalham dimensões/corpos; P não fixa tolerância numérica | Examinar significado da comparação, não só rótulo |
| F1-08 | 1 | P p.3, entrega Papel 1; p.6, §8 | Biblioteca validada: esquemático, layout e DRC/LVS | Obrigatório | Índice relacionando fontes, simulação, geometria e relatórios | S08/S09; S01, Fase 1 | Congelamento/hash/PEX são adicionais | Suficiência dos vínculos fica para a etapa 2 |
| F1-09 | 1 | P p.3, Papéis 1/2; p.4, Marco 1 | Identificar as folhas necessárias a “todas” e ao gerador | Dependência | Confrontar inventário/arquitetura com bitcell, SA, driver WL, pré-carga e decoder mencionados; explicitar suporte à escrita | S03 §1.1; S02/S13 | S13 realoca decoder à Fase 2; S02/S03 o incluem na Fase 1 | P não enumera exatamente as seis famílias atuais; não inferir write driver separado só da palavra “driver” |

### Fase 2 — 11 itens

| ID | Fase | Referência oficial | Requisito | Categoria | Critério de verificação | Documento secundário | Divergência documental | Observações |
|---|---:|---|---|---|---|---|---|---|
| F2-01 | 2 | P p.4, §4, item 10 | Especificar tiling/abutment em linhas e colunas | Obrigatório | Algoritmo, fronteiras das células e regras de encostamento/conexão confrontados com posições geradas | S07, checkpoints/trabalho físico; S17 slide 13 | Abutment não é presumido de qualquer colocação Python | Se houver espaçamento/roteamento alternativo, identificar e discutir a interpretação depois |
| F2-02 | 2 | P p.4, §4, item 11; p.3, Papel 3 | Implementar posicionamento em Python | Obrigatório | Código/configuração e execução rastreável até posições/array | S03 §21; S07 | Síntese/roteamento digital não substituem o gerador | Não exigir OpenROAD, área ótima ou genericidade irrestrita |
| F2-03 | 2 | P p.4, final de §3; §4, item 11 | Começar com placeholders/dummies para avançar em paralelo | Obrigatório | Registro histórico/protótipo da estratégia inicial e posterior troca por células reais | S07; S17 slide 13 | Critérios atuais privilegiam resultado final; início pede rastreio próprio | Não exigir dummies no GDS final nem recriar artificialmente história |
| F2-04 | 2 | P p.4, §4, item 12 | Gerar netlist estrutural das conexões | Obrigatório | Netlist emitida, instâncias/pinos/redes; confronto posterior com arquitetura e extração | S03 §21; S05/S07 | RTL comportamental/array de FF não substituem rede estrutural de folhas reais | Independência do exame é método, não contagem oficial de negativos |
| F2-05 | 2 | P p.4, §4, item 13 | Testar gerador com primeiro conjunto real validado | Obrigatório | Execução identificando fontes reais/configuração e substituição dos dummies | S03 §1.1; S05/S07 | Células específicas são escolhas da equipe | Sucesso de folhas isoladas não equivale a teste do gerador |
| F2-06 | 2 | P p.4, final de §3; §4, item 13 | Integrar células reais a partir dos entregáveis de células/periféricos | Dependência | Relação biblioteca/pinos/insumos do primeiro array e histórico de integração | S08/S09; S05 | Dependência Git não substitui marco físico | Não é preciso esperar todas as folhas para começar a programar |
| F2-07 | 2 | P p.4, §4, Marco 2 | Gerador produzir array pequeno em GDSII | Obrigatório | Fonte, configuração, comando de geração e GDSII do array efetivamente emitido | S03 §17; S05/S07 | Núcleo customizado versus top HD completo são fronteiras locais adicionais | GDS manual sem vínculo com gerador não demonstra sozinho esta obrigação |
| F2-08 | 2 | P p.4, Marco 2, “ex.: 4×8” | 4×8 como exemplo de array pequeno | Exemplo | Identificar dimensão escolhida e distinguir exemplo de exclusividade | S03 §§1/17; S17 slides 3/13 | P §6 nomeia 4×8 sem ressalva de exemplo | Não concluir sozinho que qualquer dimensão é equivalente |
| F2-09 | 2 | P p.6, §6, semanas 4–8, versus p.4, Marco 2 | Harmonizar as duas formulações sobre o primeiro array | Decisão pendente | Registro da interpretação; 4×8 escolhido localmente pode satisfazer ambas as redações | S03 §§1/17; S17 | Exemplo em Marco 2 versus alvo nominal no resumo | Alternativa a 4×8 exige alinhamento; não há enunciado único inequívoco de exclusividade |
| F2-10 | 2 | P p.4, Marco 2; p.5, §5; p.6, §7 | DRC limpo do bloco completo gerado | Obrigatório | Geometria exportada, regras e relatório do array completo, não apenas das folhas | S05, CORE/F2-FIS; S07/S10 | Reimportação GDS e outros controles são detalhamento local | Contingência não autoriza cortar DRC |
| F2-11 | 2 | P p.4, Marco 2; p.5, §5; p.6, §7 | LVS limpo do bloco completo gerado | Obrigatório | Extração do array versus referência estrutural sustentada pelos esquemáticos, com abrangência identificada | S05/S07/S10 | S17 slide 15 menciona LVS estrutural; examinar seu significado depois | Contingência não autoriza cortar LVS; modelo lógico não deve esconder comparação física |

### Contagem e alcance

| Fase | Itens | Obrigatório | Recomendação | Exemplo | Dependência | Decisão pendente |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 10 | 7 | 2 | 0 | 0 | 1 |
| 1 | 9 | 7 | 1 | 0 | 1 | 0 |
| 2 | 11 | 8 | 0 | 1 | 1 | 1 |
| Total | 30 | 22 | 3 | 1 | 2 | 2 |

Separar instalação/teste, DRC/LVS e ambiguidades permite exame objetivo, sem
ampliar P. A contagem não inclui caracterização futura como obrigação F0–2.
P p.3, §3 também orienta reunião semanal de integração (1h, sexta) e suporte
cruzado: diretrizes transversais, não um novo marco físico ou requisito de
encerrar todas as reuniões futuras antes do Marco 2.

## 5. Marcos e contingência

**Marco 1:** todas as folhas com DRC/LVS limpo em 12/out (P p.4). Isso não
torna opcionais topologia, esquemático, função isolada e layout dos itens 5–9.

**Marco 2:** gerador produzindo array pequeno em GDSII, DRC/LVS no bloco
completo em 02/nov (P p.4), antecedido pelos itens 10–13. Não constam nele
síntese SKY130HD, GLS, LEF, `.lib` caracterizada, Monte Carlo, três corners,
período de clock específico ou contador mínimo de testes. As diferenças
internas são tratadas em [02](02_documentation_differences.md).

P p.6, §7 permite, **se houver atraso**, reduzir primeiro a faixa de geração,
por exemplo de quatro configurações para duas (8×8/32×8); se necessário,
reduzir depois corners de três para TT, documentando a limitação. Não são
cortes automaticamente acionados. Registrar decisão e alcance, sem cortar
gerador ou DRC/LVS limpo. A Fase 0 coletiva também não pode ser cortada.
Essas contingências não dispensam SNM/Monte Carlo por simples associação.

P p.1 limita PVT a TT/SS/FF **sem variação completa** de temperatura/tensão.
O SNM estatístico é reduzido: p.5, §5 exige N≥200; a indicação 200–500 da p.1
não permite N<200 nem estabelece claramente teto obrigatório. O termo
“completa” no resumo da caracterização não restaura qualificação industrial
ou uma varredura ilimitada excluídas pela própria adaptação.

## 6. Critérios de trabalho da etapa 2

Examinar primeiro fontes/configurações, depois evidências correspondentes:

1. Funcionamento do ambiente; registro de tutoriais, especificação e Git (F0).
2. Inventário/versões das folhas; topologias, esquemáticos, funções isoladas,
   layouts e DRC/LVS dos mesmos circuitos (F1).
3. Tiling/abutment, trajetória dos placeholders, posicionamento e emissão de
   netlist estrutural (F2).
4. Execução com folhas reais, GDS emitido e DRC/LVS abrangendo esse array e
   sua referência estrutural ligada à biblioteca (F2).
5. Decisões sobre ambiguidades e critérios locais adicionais. Separar exame
   de conformidade a P do exame dos compromissos internos adicionais.

Não foi aberto código do gerador/RTL para julgá-lo, não foram validados dados
elétricos/físicos nem executada ferramenta EDA. Os relatórios anteriores são
fontes documentais secundárias. A fronteira com Fases 3/4 e as decisões
necessárias estão em [03](03_phase2_scope_boundary.md).
