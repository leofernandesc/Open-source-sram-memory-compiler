# Auditoria técnica das Fases 0, 1 e 2 — evidências e conformidade

Data: 05/11/2026. Etapa 2 de 3. Auditoria da implementação e das evidências;
não é revisão formal dos orientadores, implementação corretiva ou execução
da Fase 3. O parecer resumido está em [06](06_phase2_technical_verdict.md);
os compromissos adicionais estão em [05](05_architecture_review.md).

## 1. Referência, autoridade e preservação

Proposta oficial P: **Proposta Adaptada de Projeto: Memory Compiler para SRAM
(Single-Port)**, seis páginas, lidas integralmente nesta auditoria. A cópia
externa em `Downloads/Proposta_Adaptada_Memory_Compiler_OpenSource_09092026.pdf`
teve sua identidade confirmada por SHA-256:

```text
59021f96db0202678b9ec4c9f6195fceeb95cfd60a8ecf5c5a3845a72c332644
```

Aplicou-se a hierarquia de [01](01_official_requirements.md): P; alterações
explicitamente aprovadas; especificações locais; registros históricos.
Os 30 IDs e as 22 obrigações da Etapa 1 são uma decomposição para auditoria,
não uma classificação emitida pelos orientadores. As divergências documentais
de [02](02_documentation_differences.md) e as fronteiras de
[03](03_phase2_scope_boundary.md) permanecem preservadas.

| Referência conferida | Identidade no início da auditoria |
|---|---|
| Implementação local e `origin/integration/phase2-4x8` | `3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6` |
| Branch documental local e remota | `review/official-scope-phases-0-2` |
| HEAD documental inicial | `cf47ca244b6a912338f572a3d9d031cfe309116b` |
| Diferença inicial contra a implementação | Somente os documentos 01, 02 e 03 desta pasta |
| Árvore inicial | Limpa; sem alterações staged/unstaged ou untracked não ignorados |

As duas referências remotas foram consultadas por fetch direcionado; não
havia avanço a incorporar. Não foi feito merge da integração. Arquivos
ignorados em `build/phase2/` e `build/digital/` foram tratados como evidências
locais auxiliares, sem confundi-los com conteúdo de um clone público.
Somente os documentos 04–06 são acrescentados nesta execução. As referências
abaixo descrevem o conteúdo de `3d14880`, não eventuais avanços posteriores.

## 2. Método e alcance das verificações

**Executado nesta auditoria**, além da leitura de fontes, histórico e logs:

1. Conferência do PDF, Git, manifests, hashes e arquivos selecionados.
2. Inventário leve das ferramentas na imagem existente, sem instalação.
3. Auditor de handoff da Fase 1 e geração headless das seis netlists Xschem
   em diretórios descartáveis; comparação com os SPICE congelados.
4. Emissão Python de `fabric.tcl` e `reference.spice` em diretório temporário,
   sem executar Magic, place-and-route ou simulação.
5. Leitura binária do GDS com gdstk e comparação com a reprodução histórica
   localizada pelo hash exato; exame independente dos terminais/coordenadas
   extraídos e da contagem de MOS.
6. Reconciliação dos logs RTL/GLS e recálculo dos verificadores elétricos
   sobre os transientes completos existentes, incluindo partida e C1/C2.
7. Sete testes unitários de integridade de evidências, todos aprovados.

**Inspecionado, sem reexecutar a ferramenta física:** DRC, LVS, negativos
físicos e a reconstrução integral histórica. Não houve nova síntese, GLS,
simulação ngspice, extração ou reconstrução física. Um resultado histórico
com identidade confirmada é distinguido de uma nova execução nesta etapa.
Contadores recalculados não representam novas simulações do circuito.

As análises com dependências EDA foram sequenciais, em containers descartáveis
da imagem já disponível, projeto montado somente para leitura, rede desativada,
uma CPU e até 1,5 GiB de RAM. Temporários ficaram em `/tmp`; não se iniciou
nem se reparou o container original parado. Antes delas havia aproximadamente
2,8 GiB de RAM disponível, 2 GiB de swap livre e 2,3 GiB de disco livre.
Não foram removidos caches, imagens ou resultados.

### Convenções de julgamento

- **ATENDIDO:** artefato e evidência suficientes para o requisito indicado.
- **PARCIALMENTE ATENDIDO:** parte demonstrada, com lacuna delimitada.
- **NÃO DEMONSTRADO:** evidência insuficiente; não significa que não ocorreu.
- **NÃO ATENDIDO:** evidência positiva de descumprimento integral do item.
- **NÃO APLICÁVEL:** inaplicabilidade justificada.

“Recomendável” na criticidade indica tratamento antes de declarar conformidade
integral ou para melhorar reprodução; não torna opcional a obrigação oficial.
Nenhuma lacuna histórica foi convertida em defeito elétrico por inferência.

## 3. Fase 0 — ambiente e organização

### 3.1 Ambiente encontrado

Host Ubuntu 24.04.5; imagem instalada `isaiassh/unic-cass-tools:1.0.7`, ID
`sha256:921d95e8cd03b8fbe5cec683ea14add4c1b6e0db1d5d05187fac7deb16b5e0f8`.
O container de trabalho `sram-xschem` estava parado. O inventário foi obtido
em instância descartável da mesma imagem, sem depender de X/Wayland.

| Ferramenta/tecnologia | Conferência atual | Evidência de utilização e limite |
|---|---|---|
| Magic | Imagem-base: 8.3.589 | Logs das cinco folhas usam 589; decoder selecionado e top final usam 8.3.684. Não são versões intercambiadas silenciosamente |
| Xschem | 3.4.6, instalação `/opt/xschem/313acc8` | Seis esquemáticos congelados netlistados agora, RC=0, equivalência normalizada exata |
| ngspice | 44.2, KLU | Logs nativos, decks e raws das campanhas efetivamente inspecionados/reanalisados; nenhuma nova simulação |
| Netgen | 1.5.293 | Logs completos de folhas e top; setup e comparações de parâmetros identificados |
| SKY130/open_pdks | SKY130A, volare `0fe599b2afb6708d281543108caf8310912f54af` | Biblioteca ngspice, HD, xschem, magicrc e setup LVS acessíveis |
| gdstk | 0.9.62 | GDS final lido nesta auditoria; hierarquia e limites físicos conferidos |
| Icarus Verilog | 13.0 de desenvolvimento, revisão `25a84d5cf` | Logs RTL/GLS e configuração de compilação examinados |
| Git | 2.34.1 na imagem | Objetos, referências, histórico, status e índices consultados |
| Yosys / OpenROAD | 0.44 / `v2.0-25787-gee9759486` | Acréscimos locais, não ferramentas impostas por P; fontes e logs examinados |

[ENVIRONMENT](../../tools/ENVIRONMENT.md) documenta a instalação lateral de
Magic 8.3.684 e seu helper; [guia de reprodução](../phase2_reproduction_guide.md)
registra a versão usada no top. A tag da imagem-base sozinha **não recria a
camada modificada do container**. A versão 684 não foi instalada nesta etapa,
e não se alegou reprodução física com a 589. Isso limita a repetição imediata
do fluxo físico na instância descartável, não invalida os logs selecionados.

Identidades de tecnologia conferidas na imagem e nos comprovantes:

| Arquivo | SHA-256 |
|---|---|
| `libs.tech/magic/sky130A.magicrc` | `7bc1d5d14d910bd1407287ec1ab1305b17e1d7ac384f918c5dad34e97494b94d` |
| `libs.tech/netgen/sky130A_setup.tcl` | `7a33f3f54fab57a9d9b0887ac7b7b64ce6c454110e8b7f01f3cfb90a1282dc94` |
| `libs.tech/ngspice/sky130.lib.spice` | `5efa041a988893c1a3580d0ecd57870ea3146b27741c7d42b56baaa336b9549e` |

Os modelos incluídos recursivamente são conferidos pelos verificadores
elétricos; o hash de `sky130.lib.spice` sozinho não bastaria. Caminhos antigos
`/home/designer/shared/...` são registros históricos: os vínculos atuais usam
hashes e cópias selecionadas, não exigem a existência desse diretório.

### 3.2 Histórico e metodologia

O histórico foi consultado com `git log --all --reverse` e buscas por
tutorial, pair design e reuniões. Pontos verificáveis:

- `528291c`, 20/09: início do repositório por Leonardo.
- `33c5375`, 20/09: pastas `cells`, `scripts`, `sims`, `docs`, `specs`.
- `07c63e3`, 21/09: GITFLOW por Danilo; `631e7fd` e `87ab2a2`, mesma data,
  acrescentam esquemático e especificação de bitcell.
- `5f39633`, 23/09: especificação técnica geral por Leonardo.

Isso demonstra organização e colaboração inicial. Não data o primeiro push,
a liberação de acesso a cada integrante ou a disponibilização das specs a
todos no primeiro dia. Não foi localizado registro identificável dos tutoriais
SKY130 executados coletivamente. P não exige ata, certificado ou formato
específico: mensagens, relato identificável ou outro registro existente podem
esclarecer esses pontos, sem criar artificialmente uma execução passada.
Também não foi localizada aprovação acadêmica identificada da especificação
ou da realocação das fases. Uma decisão do proprietário de um circuito não
equivale a essa aprovação.

### 3.3 Matriz F0 — obrigações

Referências oficiais completas e redação original dos IDs: [01, Fase 0](01_official_requirements.md#fase-0--10-itens).

| ID / obrigação | Artefato e procedimento | Evidência e estado | Pendência / limite | Criticidade |
|---|---|---|---|---|
| F0-01 — instalar toolchain | Inventário acima; `tools/ENVIRONMENT.md`; arquivos PDK e executáveis | **ATENDIDO**: ferramentas oficiais instaladas; SKY130 acessível | Recriar versão Magic 684 exige ambiente lateral documentado | Recomendável para reprodução futura |
| F0-02 — toolchain testado | Netlistagem Xschem atual, leitura GDS, logs físicos/elétricos e digitais vinculados | **ATENDIDO**: integração funcional demonstrada, não apenas lista de versões | Não se repetiu todo o fluxo físico agora | Sem pendência do resultado |
| F0-03 — tutoriais coletivos | Busca no histórico e documentação de setup/planejamento | **NÃO DEMONSTRADO**: não se identificaram tutorial, sessão e participação coletiva | Obter registro/relato existente; não afirmar ausência da atividade | Recomendável; metodologia histórica |
| F0-04 — definir/documentar specs | `technical_specification.md`, contratos digital/físico/temporal, confronto com P §5 | **ATENDIDO** para especificação documentada do protótipo e alvos gerais | Aprovação é F0-05; parâmetros de caracterização ainda abertos não são limites já garantidos | Alinhamento acadêmico separado |
| F0-06 — Git organizado | Objetos e pastas desde `33c5375`; GITFLOW e árvore atual | **ATENDIDO** | Datas reais diferem do cronograma planejado; não se inferiu execução na semana prevista | Sem bloqueio técnico |
| F0-07 — compartilhamento inicial/specs comum | Histórico inicial com autores distintos e pasta `specs` | **PARCIALMENTE ATENDIDO**: colaboração e destino comum demonstrados | Disponibilização a todos “desde o dia 1” não é datável pelos objetos Git locais | Recomendável; lacuna histórica |
| F0-08 — fluxo gratuito/open-source/SKY130 | Ferramentas, decks, bibliotecas e fontes efetivamente utilizados | **ATENDIDO** | Docker/HD são escolhas adicionais compatíveis; não representam ferramenta comercial substituta | Sem bloqueio técnico |

**Parecer F0:** ambiente tecnicamente utilizável. As lacunas de tutoriais e
compartilhamento histórico não anulam o funcionamento demonstrado; impedem
afirmar comprovação integral da metodologia de setup.

## 4. Fase 1 — biblioteca selecionada

### 4.1 Seleção e correspondência das views

O seletor [phase1_current](../../release/phase1_current.json) aponta para
[manifesto keeper](../../release/phase1_keeper/manifest.json), SHA-256
`d1e70cefa6a90e4e820e75544a1665d5a4de5764ae0d3eaccf268c498f80116b`.
As cinco folhas de `release/phase1/` permanecem iguais; somente o decoder
é substituído pela revisão keeper. O baseline de 29 MOS é histórico.
Foram confrontados pinos, parâmetros, símbolo, fontes, máscaras, PEX e logs.

| Família selecionada | MOS / configuração relevante | Views e prova física |
|---|---|---|
| Bitcell 6T | 6; PU/PD/acesso = 0,42/1,26/0,60 µm | [SCH/SPICE/MAG/PEX](../../release/phase1/cells/bitcell_6t/); [prova](../../release/phase1/verification/bitcell_6t/result.json) |
| Sense amplifier | 7; latch 1,5×, PMOS amostradores 2 µm | [views](../../release/phase1/cells/sense_amp/); [prova](../../release/phase1/verification/sense_amp/result.json) |
| Precharge/equalização | 3 PMOS de 2,52 µm | [views](../../release/phase1/cells/precharge/); [prova](../../release/phase1/verification/precharge/result.json) |
| Wordline driver | 4; dois estágios, larguras 1,68/5,04 µm | [views](../../release/phase1/cells/wl_driver/); [prova](../../release/phase1/verification/wl_driver/result.json) |
| Write driver | 10; saída 5,04 µm; inversão interna de WE | [views](../../release/phase1/cells/write_driver/); [prova](../../release/phase1/verification/write_driver/result.json) |
| Decoder dinâmico | **33**; quatro PMOS feedback keepers W/L=0,84/0,15 µm | [views](../../release/phase1_keeper/cells/row_decoder/); [prova](../../release/phase1_keeper/verification/row_decoder/result.json) |

A netlistagem atual dos seis SCH, com bibliotecas Xschem/SKY130 configuradas
explicitamente, retornou RC=0; a normalização do fluxo de verificação produziu
as mesmas seis netlists congeladas. Não houve comparação apenas visual.
No decoder, a ordem formal é `VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`;
as conexões são emitidas nessa ordem a partir de nomes. `EVAL_GND` é separado
de VSS pelo transistor de avaliação. Não se usou o decoder alternativo ou
o modelo lógico como prova da implementação física.

O auditor [verify_phase1_handoff](../../tools/verify_phase1_handoff.py)
conferiu 3.020 arquivos indexados, seis seleções e seus vínculos. Sua operação
legada usa cópia temporária descartável, sem reescrever os relatórios originais.
Todos os logs selecionados de DRC indicam zero grupos; o LVS compara tipos,
terminais, corpos e W/L. Foram examinados os controles negativos de gate,
bulk, modelo, W e L — 30 comparações selecionadas, não 30 novos testes físicos.
O setup oficial usa tolerância dimensional de 1%; a quantização do NMOS do
sense de 0,975 para 0,98 µm está explícita e fica dentro dessa tolerância.
A associação do PEX ao circuito colapsa resistores **para LVS**; não é nova
qualificação do algoritmo de extração ou da precisão de seus R/C.

### 4.2 Função elétrica: evidência por família

Os quatro CSV congelados em [electrical](../../release/phase1/electrical/)
contêm 129 linhas: leitura G7 (60), escrita G7 (60), refinamentos de leitura
(8) e escrita (1). Seus hashes de PEX identificam as cinco folhas acima.
Os scripts [leitura](../../sims/run_integrated_column_read.py) e
[escrita](../../sims/run_integrated_column_write.py) contêm estímulos, medidas
de decisão/flip, retenção e recuperação. Os CSV não são transientes completos;
nesta etapa conferiram-se identidade, dados medidos e critérios do produtor,
sem reconstruir ondas antigas ausentes do pacote selecionado.

| Família | Evidência funcional examinada | Conclusão e limite |
|---|---|---|
| Bitcell | Bancadas de bitcell; G7 verifica Q/QB antes/depois, disturb e recuperação; top extraído tem escrita/readback e retenção das palavras conhecidas | Armazenamento, escrita, leitura e retenção nominal demonstrados. Estado conhecido em bancada isolada não comprova partida sem reset; esta tem testes próprios |
| Sense | Caracterização isolada histórica e G7 com PEX **scale1p5**; C1/C2 observam diferencial, saída e captura | Função da versão selecionada demonstrada em integração. Os 330 casos isolados do SCH de hash `ad8f819…` são do draft anterior: não os atribuir automaticamente à versão reforçada |
| Precharge | G7 W2,52: BL/BLB recuperam; C1/C2 conferem as 16 bitlines antes dos acessos | Preparação funcional demonstrada. Medida isolada de Ceff não equivale a toda a função de equalização |
| WL driver | Smoke isolado e PEX históricos; G7 com hash da variante 1,68/5,04; top seleciona/desativa quatro WL reais | Acionamento demonstrado no contexto integrado. Vários CSV smoke antigos não registram hash da variante; o nome do CSV não resolve essa ambiguidade |
| Write driver | G7 W5,04 mede flip/recuperação; top e C1 verificam DIN capturado, complemento e preservação de outras linhas | Escrita e inibição funcional em integração demonstradas. C2 mede direção do barramento público, não leakage isolado de BL do write driver |
| Decoder | [campanha keeper](../../sims/row_decoder/results/keeper_review_20261029/summary.json), decks/checks e métricas; auditor recompõe verificações; top exercita quatro endereços físicos | 105 casos pós-layout obrigatórios/3.045 checks, 48 casos funcionais; cinco falhas deliberadas de limite de carga retidas. G7 antigo não inclui esse decoder e não o qualifica |

**Ressalva de F1-04:** há simulações isoladas e funcionamento elétrico das
folhas selecionadas em bancadas integradas, mas não se identificou uma cadeia
de comprovação isolada inequívoca para **cada variante final reforçada**.
Em particular, não se transfere a campanha do sense draft para o scale1p5,
nem um smoke sem hash para qualquer sizing WL. Essa lacuna de método/vínculo
é distinta de falha funcional: o circuito integrado selecionado foi examinado
com os dispositivos reais, e seus transientes foram recalculados nesta auditoria.
Localizar o registro isolado correspondente ou complementar pontualmente a
evidência, em outra execução, é a recomendação; não refazer todo o trabalho.

A [decisão de handoff](../../release/phase1_handoff_20261029/decision.json)
retém `independent_off_state_model_accuracy=NOT_ESTABLISHED`. Isso é uma
limitação do alcance dos modelos/screenings, não prova de dano físico nem
dispensa de caracterização futura. Sua aceitação pelo proprietário da revisão
não é aprovação acadêmica ou garantia de fabricação.

### 4.3 Matriz F1 — obrigações

Referências oficiais: [01, Fase 1](01_official_requirements.md#fase-1--9-itens).

| ID / obrigação | Artefato e procedimento | Evidência e estado | Pendência / limite | Criticidade |
|---|---|---|---|---|
| F1-01 — topologias bitcell/SA | SCH/SPICE congelados, manifesto e exame de redes regenerativas/acesso | **ATENDIDO**: 6T e sense latch de 7 MOS identificados | Não implica SNM estatístico ou sensibilidade qualificada | Futura caracterização |
| F1-03 — SCH de cada folha | Seis SCH/SYM e netlistagem headless atual | **ATENDIDO**: RC=0 e correspondência normalizada exata com SPICE selecionado | Configuração da biblioteca necessária; não há missing symbol no netlisting conferido | Sem bloqueio |
| F1-04 — simulação isolada de cada folha | Bancadas/CSV históricos, G7, campanha keeper e confronto de hashes/variantes | **PARCIALMENTE ATENDIDO**: função demonstrada, rastreio isolado incompleto para variantes finais | Recuperar/completar comprovantes isolados específicos; não reutilizar PASS de sizing antigo | Recomendável; completude do método |
| F1-05 — layout individual Magic | Seis MAG congelados e extrações vinculadas aos SCH | **ATENDIDO** | Sem alteração nesta auditoria | Sem bloqueio |
| F1-06 — DRC das folhas | Logs nativos, geometria/hashes e configuração full | **ATENDIDO**: zero grupos nas seis versões selecionadas | Resultado do deck open-source identificado, não signoff industrial | Limite conhecido |
| F1-07 — LVS das folhas | Referências dos SCH, extrações, Netgen e negativos | **ATENDIDO**: match com parâmetros/terminais; seis famílias abrangidas | Tolerância 1%/reduções explicitadas | Limite conhecido |
| F1-08 — biblioteca validada | Seletor, inventário, views, provas físicas e evidência elétrica acima | **ATENDIDO** como biblioteca funcional e fisicamente vinculada | Não transforma o rastreio parcial de isolamento em cumprimento integral de F1-04 | Ressalva específica acima |

**Parecer F1:** biblioteca real, selecionada e íntegra, com fechamento físico
demonstrado e função demonstrada no escopo ensaiado. Conformidade metodológica
integral da simulação isolada das revisões finais não foi comprovada.

## 5. Fase 2 — cadeia do gerador até o bloco verificado

### 5.1 Entradas e representação estrutural

[phase2_core.py](../../tools/phase2_core.py), funções `selected_leaves`, `graph`,
`audit`, `emit` (linhas 16, 36, 64, 113), lê o seletor, confere hashes e extrai
os pinos formais. A composição física implementada é fixa em **4×8**:
32 bitcells, um decoder 33 MOS, quatro WL drivers, oito precharge, oito write
e oito sense, total **401 MOS** em 61 instâncias de folhas. Complementos de
DIN e qualificação de linha ficam fora desse fabric no top físico.

O harness estrutural emitido por `emit` inclui essas interfaces e portas HD;
o caminho físico selecionado usa a netlist `leaf_fabric` produzida por
[run_phase2_fabric.py](../../tools/run_phase2_fabric.py), `generate` (linha 23).
Ela é construída das definições SPICE congeladas e de conexões nominais
emitidas na ordem formal de cada subcircuito. Não é um array de FF, modelo
comportamental ou mera compilação de símbolos black box.

O top completo é ligado por [macro_binding.v](../../physical/phase2/macro_binding.v),
netlist HD mapeada e [finish_phase2_layout.py](../../tools/finish_phase2_layout.py).
O código de acabamento constrói a referência expandida usando as definições
dos MOS das folhas e o SPICE PDK das standard cells. O LVS final expande
os dispositivos; a black box usada em síntese não oculta o array no LVS.

### 5.2 Posicionamento, orientação, roteamento e abutment

Em `run_phase2_fabric.py:40–45`, as bitcells são colocadas em
`(6000*b, 36000+5000*r)` nas unidades internas de Magic, com orientação R0.
O decoder ocupa `(-27000,26000)`, WL drivers acompanham as quatro linhas,
e precharge/sense/write ocupam faixas por coluna. As posições são explícitas;
o código não oferece generalização física automática para 8/16/32 palavras.
Isso não é obrigação atual de entregar quatro configurações no Marco 2.

O scale do MAG é 1/2 e o conversor de abstração usa 0,005 µm/unidade interna.
O bbox geométrico da bitcell selecionada é 3.450×2.584 unidades internas,
ou **17,25×12,92 µm**. Os pitches são **30×25 µm**, deixando separações
geométricas de aproximadamente **12,75 µm em x e 12,08 µm em y**.
Portanto, a matriz selecionada **não usa encostamento direto das células**.

Conexões por barras M3 dos pinos, promoção a M4, troncos BL/BLB/alimentação,
trilhas M5 de WL/controle e vias explícitas completam a composição. A
abstração é derivada da geometria em [phase2_abstract.py](../../tools/phase2_abstract.py),
com pinos/obstruções para roteamento HD. O top usa OpenROAD, macro em R0,
alimentação VDD/VSS e VPB/VNB, taps/fillers e acabamento Magic de vias/GDS/DEF.
O floorplan final é 540×380 µm, sem alegação de área otimizada.

**F2-01 tem atendimento parcial literal:** há tiling regular e integração
funcional, mas não o abutment direto referido em P p.4, item 10. Existem
testes anteriores de abutment isolado da bitcell, inclusive gap zero; eles
não transformam o array espaçado em array por abutment. Não foi localizada
decisão explícita aprovando essa substituição metodológica. Cabe alinhamento
com a equipe/orientadores, sem redesenho automático para obter um parecer.

### 5.3 Placeholders e trajetória de desenvolvimento

O histórico de `tools/phase2_core.py` e `tools/run_phase2_fabric.py` foi
consultado em todas as referências locais. No primeiro commit identificado,
`d96896d`, 04/11, o gerador já utiliza as folhas reais. Não foi localizado
protótipo físico anterior de array com placeholders nem registro suficiente
de sua troca pelas folhas selecionadas. Pastas `.gitkeep`, macro Verilog
black box, fillers e stubs de taps não comprovam esse protótipo.

F2-03 é **NÃO DEMONSTRADO**, não “não executado”. Trabalho anterior não
versionado pode existir; só a equipe pode fornecer seu registro. Isso não
contradiz a utilização atual, comprovada, de células reais (F2-05/F2-06),
nem justifica criar retrospectivamente uma história de placeholders.

### 5.4 Vínculos físicos e identidade dos artefatos

Entradas e resultados são selecionados por
[checkpoints](../../physical/phase2/checkpoints.json),
[delivery](../../physical/phase2/delivery.json) e pelos manifests publicados.
Foram conferidos os **21** arquivos do índice de entrega e os **151** arquivos
da extensão, preservando **260** insumos históricos desta última. A extensão
não altera a seleção do circuito. Os antigos campos `LOCAL_ONLY` descrevem
a data de seus relatórios, não o estado atual de publicação.

| Artefato selecionado | SHA-256 conferido |
|---|---|
| [GDS top completo](../../reports/phase2/final_gds/sram_4x8.gds) | `d45ab0ca9438116a61c5db39ef2577a6dc08c510e40dd6f6ade87a1b9299d880` |
| [SPICE extraído final](../../reports/phase2/final_gds/final_extracted.spice) | `eba610035b7d7d97cd97f49c39819ffa8de022b70c969851e152bbe8253bb89b` |
| [Binding elétrico renomeado](../../reports/phase2/extracted_access_singlethread/binding.spice) | `27de843b585fffaca43d78b5ebd9c81e6ecddee99b067ade26cb60002e515f55` |
| [Log LVS final](../../reports/phase2/final_gds/lvs.txt) | `a0391e46a0db25b1450ada7de6a3bc39f678e08c28bbd2cc6006118b490ef764` |
| [Log Magic final](../../reports/phase2/final_gds/magic.txt) | `f70a8ab35cbb8c33bedac6d22ebbb4a2ec806aa4fa31d6cf36541f6e64bece75` |

A leitura gdstk encontrou 20 células, único top `sram_4x8_wrapper`, unidade
1 µm/precisão 1 nm, bbox 0..540×380 µm, sem referências hierárquicas ausentes.
O GDS `leaf_fabric` de 401 MOS é um intermediário, não todo o top público.
O núcleo completo documentado também não deve ser confundido com esse fabric.

O procedimento independente
[review_phase2_structure.inspect](../../tools/review_phase2_structure.py)
foi reexecutado sobre `final_flat.ext`, a referência expandida e o JSON
roteado. Não importa o gerador de layout: resolve aliases, terminais reais,
modelos, bulks e coordenadas dos transistores. Confirmou:

- 32 posições de armazenamento distintas, quatro linhas e oito colunas em
  ordem física, oito pares BL/BLB distintos e VDD separado de VSS.
- **16 gates de acesso por WL**, dois por bitcell, com modelo/corpo corretos.
- Conexão de cada bitcell aos pares e alimentação corretos; sense e precharge
  na coluna correspondente; SA_OUT para o mux de captura correto.
- Read FF_Q para o `ebufn` do bit correspondente; contagem extraída de
  **1.493 MOS = 401 customizados + 1.092 HD**.

A segunda inspeção estrutural armazenada em
[structure_corrected](../../reports/phase2/extension_20261104/structure_corrected/results.json)
confere ainda DIN/DIN_B e a rede CMOS de habilitação por bit. Seu código e
insumos foram examinados; não se executou seu `main`, que escreveria relatório.
Usar um grafo comum para gerar referência/layout não foi a única prova.

### 5.5 DRC e LVS do objeto entregue

O log Magic final registra **8.3.684**, tecnologia SKY130A
`1.0.493-0-g0fe599b`, importação do GDS e checagem `drc(full)`:
`No errors found` e `FINAL_GDS_DRC=0`. O script
[verify_phase2_gds.py](../../tools/verify_phase2_gds.py) reimporta o GDS final
e extrai o mesmo objeto. Não é apenas DRC das seis folhas. Não foi identificada
exceção geométrica ignorada no resultado selecionado.

O LVS nativo registra expansão do fabric customizado e das standard cells,
correspondência de pinos, corpos e propriedades, com resultado único sem
property errors. Os **1.493 MOS físicos anteriores à redução** viram
**1.459 dispositivos equivalentes** após 34 fusões de paralelos: PMOS HVT
550→529, NMOS regular 679→666, PMOS regular 184 e NMOS especial 80.
São 730 redes em cada lado. Não são 34 transistores ausentes do layout.

O deck aplica tolerância de 1% em W/L; AD/AS/PD/PS são ignorados na comparação
LVS, mas a geometria de junções continua na netlist de simulação. Isso impede
afirmar que LVS também qualificou a exatidão dos parasitas. Os quatro negativos
de [LVS completo](../../reports/phase2/review_20261104/lvs_negative/results.json)
foram examinados com seus logs: gate/bulk produzem mismatch identificado;
W/L de +20% produzem property errors no top. O sucesso do processo Netgen
não foi interpretado como aprovação da comparação negativa.

### 5.6 Reprodução: o que foi e o que não foi demonstrado

O [script completo](../../scripts/reproduce_phase2_4x8.sh) e o
[guia](../phase2_reproduction_guide.md) encadeiam fontes congeladas, netlists,
fabric, binding, rota, acabamento, GDS reimportado e GLS. A referência a ODB
intermediário não é uma exigência de possuir o cache antigo: existe fluxo
de reconstrução desde as entradas.

Nesta auditoria, a emissão Python em diretório temporário reproduziu
**byte a byte `fabric.tcl`**, SHA-256
`8fcc4c82f0fe06818b718c9e1cab4d0bcd21803ac39192bf8133b712f209151d`.
Os 12 insumos físicos/SPICE das seis folhas correspondem à seleção. A
referência recém-emitida acrescenta seis declarações não utilizadas
`.model sky130_fd_pr__special_nfet_01v8 nmos`, pelo helper comum ampliado
depois do primeiro fabric. Removidas somente essas declarações, o texto
de referência é idêntico ao selecionado. Não mudou nenhuma instância,
conexão ou parâmetro MOS; não se confundiu identidade textual com equivalência.

O [registro histórico de reprodução](../../reports/phase2/review_20261104/reproduction/results.json)
aponta o candidato `f300a5fb3d49d4acbde72ba8c84134d7da9e389f2b6bd1a38dabd27fa8751e75`.
Seu GDS não está versionado naquela pasta. Foi localizado no cache local
`build/phase2/gds-check-t0uycdk6/sram_4x8.gds` **pelo hash exato**, sem
substituição por nome parecido. A comparação binária independente zerou
somente os 24 bytes de datas de cada registro BGNLIB/BGNSTR: os dois GDS
então tiveram hash `95b09a9983b750bca450f86005afd78f26fa347f4aa3969099f0278e65807573`.
A netlist `final_extracted.spice` desse candidato é byte a byte igual à
selecionada, incluindo modelos e junções. A normalização independente tem
convenção própria; não se usa seu hash como substituto do GDS entregue.

Assim, há **reprodução física histórica documentada, corroborada pelos
artefatos locais exatos**, e nova reprodução leve da emissão Python agora.
Não houve reconstrução física integral nova num clone sem cache nesta etapa.
O candidato histórico não foi selecionado nem simulado eletricamente nesta
auditoria. No clone público, os logs de reprodução estão disponíveis; o GDS
auxiliar do candidato deve ser regenerado se o cache não existir.

### 5.7 Matriz F2 — obrigações

Referências oficiais: [01, Fase 2](01_official_requirements.md#fase-2--11-itens).

| ID / obrigação | Artefato e procedimento | Evidência e estado | Pendência / limite | Criticidade |
|---|---|---|---|---|
| F2-01 — algoritmo tiling/abutment | Código, MAG/bbox/pitch, Tcl e GDS; §5.2 | **PARCIALMENTE ATENDIDO**: tiling/roteamento demonstrados; abutment direto não implementado | Obter decisão explícita sobre alternativa espaçada ou planejar adequação se o método literal for exigido | Alinhamento necessário para conformidade literal; não defeito funcional demonstrado |
| F2-02 — posicionamento Python | `generate`, abstração, comandos e emissão atual idêntica de Tcl | **ATENDIDO** | Implementação física 4×8 fixa; generalização posterior não demonstrada | Futura |
| F2-03 — início com placeholders | Histórico de código/branches e registros de execução; §5.3 | **NÃO DEMONSTRADO** | Localizar protótipo/registro existente; não fabricar histórico | Recomendável; metodologia histórica |
| F2-04 — netlist estrutural | `core.emit`, referência fabric e top expandido; conferência independente extraída | **ATENDIDO** | Harness, fabric e top são objetos distintos identificados | Sem bloqueio |
| F2-05 — testar folhas reais | Hashes das entradas, execução/reprodução, 401 MOS customizados no top | **ATENDIDO** | Ausência de trajetória dummy continua separada em F2-03 | Sem bloqueio do resultado final |
| F2-07 — array pequeno gerado em GDSII | Fluxo fonte→Tcl→GDS e reprodução histórica corroborada; §5.6 | **ATENDIDO**: array real 4×8 produzido por fluxo automatizado | Fluxo integral não foi refeito agora; ambiente/caches explicitados | Reprodução delimitada |
| F2-10 — DRC bloco completo | GDS identificado, importação Magic full, log e hash | **ATENDIDO**: zero violações no top entregue | Deck open-source identificado; não signoff de fabricação | Limite conhecido |
| F2-11 — LVS bloco completo | Referência das folhas/PDK versus extração; logs e negativos | **ATENDIDO**: comparação expandida com pinos/modelos/bulks/W/L | Redução de paralelos/tolerância explícitas | Limite conhecido |

**Parecer F2:** o resultado físico central do Marco 2 está demonstrado.
Não se conclui que todos os métodos antecedentes de P foram comprovados:
abutment é uma divergência real; placeholders são uma lacuna histórica.

## 6. Recomendações, exemplos, dependências e decisões — classificação separada

Estes oito itens não entram no denominador das 22 obrigações.

| ID / categoria | Evidência/procedimento | Resultado e limite | Encaminhamento |
|---|---|---|---|
| F0-05 / decisão pendente | Especificações, planejamento, decisões de handoff e ausência de identificação de aceite acadêmico no corpus | **NÃO DEMONSTRADO** o ato de validação equipe/orientador; nenhuma assinatura específica é exigida | Identificar confirmação existente e seu alcance; não emitir em nome dos orientadores |
| F0-09 / recomendação Ubuntu | `/etc/os-release` e ambiente Docker | **ATENDIDO** como orientação de compatibilidade | Não é gate adicional do Marco 2 |
| F0-10 / recomendação pair design | Busca de registros de sessões e histórico colaborativo | **NÃO DEMONSTRADO** o formato de sessões; colaboração por commits existe | Confirmar com equipe se relevante à avaliação metodológica |
| F1-02 / recomendação referências | Especificações e referências OpenRAM/TCC/SKY130 em docs | **ATENDIDO** quanto a referências identificáveis usadas no projeto | Não equivale a aprovação acadêmica do circuito nem transfere autoridade sobre fases |
| F1-09 / dependência inventário | Seletor, seis famílias, 401 MOS e estrutura extraída | **ATENDIDO**: famílias necessárias e escrita explicitadas | Seis famílias são decisão local, não número imposto por P |
| F2-06 / dependência folhas reais | Vínculos de seleção e integração no fabric/top | **ATENDIDO** | Seleção de engenharia não é alteração formal do escopo acadêmico |
| F2-08 / exemplo 4×8 | Estrutura e GDS reais | **ATENDIDO** como concretização do exemplo | Não declarar equivalência de qualquer outro tamanho sem discutir P §6 |
| F2-09 / decisão de tamanho | Primeiro array efetivamente 4×8 | **ATENDIDO** quanto à compatibilidade prática com ambas as formulações de P | A escolha evita o conflito; não resolve abstratamente se outro tamanho seria aceitável |

## 7. Rastreabilidade e achados transversais

Os verificadores elétricos existentes foram lidos antes de serem chamados.
Foram executadas suas funções de leitura/análise, sem usar `main` que gravaria
nos diretórios históricos. A reconciliação completa e suas limitações estão
em [05, §§2/5/6](05_architecture_review.md).

Um achado adicional é **a divergência atual do hash de documentação da
regressão RTL**: `verify_core_inputs` rejeita `docs/sram_4x8_interfaces.md`.
O snapshot exige `06bb04b583814f6a0709484ddb845241204cc4e499521810a7ad644cba7bbf8b`;
o arquivo atual tem `e4324add33a36af3bf6f92590df222fd6f63076152a5328a69b203df68002fc9`.
O diff foi lido: apenas seis linhas com links para contrato temporal e partida.
Todos os outros insumos da regressão coincidem, incluindo RTL/TB/scripts.
Os logs e seus resultados reconciliam **154.303** checks, mas **a verificação
estrita do conjunto inteiro de entradas atuais não passou**. Não se reescreveu
o recibo nem se afirmou PASS atual irrestrito. É pendência de atualização de
evidência documental do compromisso interno, sem efeito de circuito demonstrado
ou bloqueio do GDS/DRC/LVS do Marco 2.

### Classificação de achados

| Achado | Categoria solicitada | Evidência/localização | Impacto e tratamento |
|---|---|---|---|
| A01 — tutoriais coletivos sem registro identificável | **B — requisito não demonstrado** | F0-03; histórico e setup | Histórico/metodologia; obter comprovação existente |
| A02 — instante inicial de compartilhamento não datável | **B** | F0-07; commits iniciais | Atendimento parcial; não invalida Git colaborativo atual |
| A03 — isolamento das variantes finais não inteiramente rastreado | **B** | F1-04; drafts isolados versus hashes G7 | Complementar vínculo específico; não atribuir campanha antiga ao novo sizing |
| A04 — espaçamento/roteamento versus abutment | **C — divergência documental/metodológica** | F2-01; `generate:40–45`, pitch/bbox | Discussão explícita para conformidade literal, sem presumir aprovação da alternativa |
| A05 — placeholders iniciais sem evidência | **B** | F2-03; primeiro código já real em `d96896d` | Histórico, separado do gerador funcional atual |
| A06 — hash de documento posterior à regressão | **C** | `verify_core_inputs`; snapshot/diff acima | Evidência estrita está desatualizada; atualizar em execução própria, preservando histórico |
| A07 — cadeia de atrasos e alcance do modelo off-state | **D — risco arquitetural/modelo** | Binding, transientes e decisão de handoff | Nominal funciona; robustez fora do ensaio não comprovada |
| A08 — PEX/TT-SS-FF/timing/potência/SNM/views maiores | **E — caracterização/etapas futuras** | P itens 14–20; [03](03_phase2_scope_boundary.md) | Não imputados ao Marco 2; planejar antes das campanhas correspondentes |
| A09 — ambiente exato e texto de referência com modelos não usados | **F — melhoria de reprodução** | §§3.1/5.6; helper e logs | Usar Magic correto, distinguir igualdade textual de equivalência elétrica |

Não foi identificado **A — defeito técnico demonstrado do circuito/gerador
final** que impeça gerar o GDS, comparar sua conectividade ou operar na condição
nominal ensaiada. Isso não significa cobertura universal, cumprimento integral
de toda a metodologia ou aprovação formal do marco.

## 8. Balanço da matriz e limite do parecer

| Fase | Obrigações | Atendido | Parcialmente atendido | Não demonstrado | Não atendido | Não aplicável |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 7 | 5 | 1 | 1 | 0 | 0 |
| 1 | 7 | 6 | 1 | 0 | 0 | 0 |
| 2 | 8 | 6 | 1 | 1 | 0 | 0 |
| Total | **22** | **17** | **3** | **2** | **0** | **0** |

As contagens resumem os julgamentos, não os justificam. Abutment parcial e
lacunas históricas não foram apagados para fechar a tabela. O parecer é
**tecnicamente apto ao aceite do Marco 2 com ressalvas específicas**, porque
o produto central está demonstrado e não há bloqueio funcional/estrutural
comprovado. A conformidade literal/metodológica completa ainda requer os
encaminhamentos registrados em [06](06_phase2_technical_verdict.md).

### Procedimentos de conferência sem alterar relatórios

Comandos de leitura usados a partir da raiz:

```sh
git status --short --branch
git log --all --reverse -- tools/phase2_core.py tools/run_phase2_fabric.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/verify_phase1_handoff.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/tests -p test_phase2_evidence.py -v
```

As chamadas de função usadas em processo Python descartável foram
`review_phase2_delivery.verify_entries`,
`review_phase2_extension_delivery.verify(True)`,
`run_phase2_fabric.generate` em pasta temporária,
`review_phase2_structure.inspect`, `run_digital_regression.reconcile_core_results`
e `verify_core_inputs`, `audit_phase2.electrical`,
`verify_phase2_startup_review.verify_case`, `verify_phase2_extension.verify_case`
e `analyze_phase2_extension_timing.measure`. Elas não publicaram relatórios
novos. O segundo grupo exige NumPy e, nas referências elétricas, o PDK
identificado; os raws completos locais são necessários onde indicado.
Procedimentos de restauração/regeneração constam no guia e na nota de extensão.
Os arquivos 01–03, as seis células e todos os artefatos selecionados permanecem
intactos; não se abriu/atualizou PR nem se alterou branch de implementação.
