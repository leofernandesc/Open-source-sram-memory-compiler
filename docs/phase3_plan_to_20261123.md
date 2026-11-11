# Planejamento operacional — Fase 3 (caracterização elétrica)

**Período formal da proposta:** 03–23/11/2026  
**Janela de execução a partir da decisão:** 11–23/11/2026  
**Marco 3:** 23/11/2026 — relatório de caracterização e `.lib` simplificada gerada automaticamente  
**Equipe proposta:** Danilo, André, Leonardo, Integrante 4 (nome não informado). A alocação abaixo é **proposta nova**, não um histórico confirmado de tarefas.

## 1. Escopo obrigatório da proposta

- **14:** extrair parasitas do bloco gerado, com Magic.
- **15:** automatizar ngspice em TT, SS e FF para tempo de acesso, setup/hold, potência dinâmica e estática.
- **16:** Monte Carlo reduzido para SNM, com objetivo N ≥ 200 amostras conforme a especificação.
- **17:** gerar via Python `.lib` simplificada baseada nos resultados e com provenance por corner.
- **Marco 3:** relatório de caracterização + `.lib` gerada automaticamente até 23/11.

A proposta também requer caracterização em 8×8 e 32×8, embora a geração física dessas dimensões esteja agendada somente para a Fase 4 (24/11–14/12). Isto é uma **dependência de cronograma real**: não declarar RC físico ou caracterização pós-layout dos dois arrays sem que existam e sejam validados. Até 23/11, priorizar o 4×8 selecionado, a metodologia escalável e uma decisão registrada sobre a antecipação dos alvos físicos ou o complemento após 24/11. Qualquer contingência de reduzir corners/configurações requer aprovação explícita; o plano não a concede automaticamente.

## 2. Responsáveis (distribuição proposta)

| Pessoa | Frente principal | Saída verificável |
|---|---|---|
| **Danilo** | Bitcell 6T, SNM hold/read/write; amostragem Monte Carlo, análise estatística; apoio às dimensões | Curvas butterfly, distribuição SNM (N≥200 onde implementável), CSV e método auditável |
| **André** | Extração Magic RC, redes BL/BLB/WL; sense e precharge; verificação de margens da leitura | Netlists RC com hashes, comparação vs referência sem RC, erros/limitações e curvas de bitline/sense |
| **Leonardo** | Infraestrutura de fluxo, automação/integração, estrutura do relatório e **gerador `.lib`** | Pipeline reproducível Python→dados→Liberty, checks sintáticos e rastreabilidade |
| **Integrante 4 — nome a definir** | Caracterização temporal e potência por corners; sweep SPICE em lote | Tempo de acesso, setup/hold, potência estática/dinâmica TT/SS/FF, tabelas e logs |

**Revisão cruzada:** Danilo revisa dados SNM/RC de André; André valida interpretação elétrica da tabela do Integrante 4; Integrante 4 testa a `.lib` de Leonardo contra CSVs; Leonardo audita reprodutibilidade e hashes de todas as frentes.

## 3. Caminho crítico e agenda diária (11–23/11)

| Data | Danilo — SNM / bitcell | André — extração / leitura | Integrante 4 — timing / potência | Leonardo — automação / Liberty | Checkpoint |
|---|---|---|---|---|---|
| **11–12/11** | Definir SNM e condições/perturbações | Auditar nets e preparar PEX RC completo; comparar hashes | Definir estímulos, medidas e critérios temporais | Congelar baseline, estrutura de dados e interfaces do pipeline | Interfaces entre quatro frentes fechadas |
| **13–14/11** | Bench hold/read/write; piloto MC | Extração RC + validação de conectividade e sanidade | Primeiro lote TT no 4×8, timing/potência | Runner paramétrico de corner/carga, CSV, registradores de provenance | **14/11:** um cenário TT reprodutível |
| **15–16/11** | Monte Carlo N≥200, salvar seeds e distribuição | Comparar ΔBL/WL/SCLK e falhas com/sem RC | TT completo; começar SS/FF se modelos operacionais | Esquema de células/tabelas e primeiro `.lib` sintético a partir de dados reais | **16/11:** tabelas TT e SNM preliminares |
| **17–18/11** | Revisão estatística, SNM e limites | Revisão de margens e PEX de referência | Consolidar SS/FF, potência e setup/hold | `.lib` por corners, checagem de unidade/lookup/pins e validação cruzada | **18/11:** três corners ou risco formalizado |
| **19–20/11** | Relatório SNM consolidado | Parecer RC + risco do sense | Relatório de timing e potência | Integração, check de regressão, imagens/plots, sumário | **20/11:** release candidate do Marco 3 |
| **21–22/11** | Revisar evidências de André | Revisar tabelas do Integrante 4 | Auditar `.lib` vs fontes | Correções de inconsistência, hashes, congelamento | **22/11:** auditoria 4 olhos e congelamento |
| **23/11** | Entregar SNM | Entregar PEX/margens | Entregar medição elétrica | Publicar `.lib` + relatório + recibos | **MARCO 3** |

## 4. Critérios de aceite do Marco 3

1. Origem de cada resultado em deck/versão PDK/corner/temperatura/VDD/carga/estímulos e SHA-256.
2. PEX extraída e avaliada no nível alcançado; não chamar RC completo um netlist apenas de MOS+junções.
3. Medidas de tempo de acesso, setup/hold e potência com definições claras; indicar valores indisponíveis ou não caracterizados.
4. SNM com método, seeds, número de amostras e distribuições; distinguir nominal de Monte Carlo e declarar quando 8×8/32×8 não estiverem disponíveis.
5. Gerador `.lib` gera arquivo válido e reprodutível a partir das tabelas reais; sem valores inventados de delay/power.
6. Relatório técnico com resultados, gráficos, falhas, limitações, diferenças entre corners e ações para a Fase 4.
7. Revisão cruzada dos quatro integrantes e aprovação competente documentada quando obtida.

## 5. Bloqueadores e plano de contingência

**Dependência A:** o RC distribuído do candidato com abutment não foi caracterizado na Fase 2. André precisa provar identidade/correspondência da extração antes de todos usarem seus resultados. Plano alternativo: descrever o que é extraível e registrar limitação; não promover modelo MOS+junções a PEX completo.

**Dependência B:** a proposta exige estatísticas 8×8 e 32×8, mas a geração dessas dimensões pertence formalmente à Fase 4. No checkpoint de 12/11 decidir: (a) antecipar versões eletricamente verificáveis das duas configurações com responsabilidade adicional, se houver capacidade; ou (b) fechar a caracterização e `.lib` preliminares do 4×8 em 23/11, registrar requisito pendente e completar 8×8/32×8 na Fase 4. O caminho (b) deve ser reconhecido como **entrega parcial frente ao requisito completo**, não PASS integral.

**Dependência C:** Monte Carlo/SNM N≥200 pode ser caro. Executar piloto de 10–20 amostras, calcular throughput real e só então lotear 200 com limites de memória e timeout; preservar falhas em vez de descartar seeds desfavoráveis.

**Contingências oficiais:** se o prazo ameaçar, a proposta admite cortar primeiro a faixa de configurações para 8×8/32×8 e, depois, corners TT/SS/FF para TT, mas apenas mediante autorização e registro. **Não cortar** gerador nem DRC/LVS. Não inventar potência/offset/frequência mínima.

## 6. Continuidade após o Marco 3

- **24/11–14/12 (Fase 4):** 4, 8, 16 e 32 palavras × 8 bits, todas as views GDSII/LEF/Verilog/`.lib` e DRC/LVS de cada configuração. Aplicar a caracterização às dimensões 8×8 e 32×8 conforme disponibilidade dos seus circuitos.
- **15–19/12 (Fase 5):** documentação final e demonstração do gerador; prazo global **19/12/2026**.

**Importante:** o planejamento descreve responsabilidades propostas e metas futuras; nenhum experimento da Fase 3 é marcado como realizado sem log correspondente.