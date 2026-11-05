# Parecer técnico preliminar — Fases 0, 1 e 2

Data: 05/11/2026. **Etapa 2 de 3**, sujeita à revisão independente da Etapa 3
e à deliberação da equipe/orientadores. Não constitui aprovação formal.

Implementação examinada: `3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6`.
Base documental: `cf47ca244b6a912338f572a3d9d031cfe309116b`, branch
`review/official-scope-phases-0-2`. Proposta oficial de seis páginas
confirmada pelo SHA-256
`59021f96db0202678b9ec4c9f6195fceeb95cfd60a8ecf5c5a3845a72c332644`.

## 1. Resposta à pergunta central

**O resultado físico central do Marco 2 está tecnicamente demonstrado.
O parecer é: APTO AO ACEITE DO MARCO 2 COM RESSALVAS ESPECÍFICAS.**

Foi verificada a cadeia **folhas selecionadas → gerador Python → netlist
estrutural → GDSII 4×8 → DRC/LVS do bloco completo**. Não se identificou
defeito funcional ou estrutural demonstrado que impeça esse resultado.
O parecer não decorre apenas de contadores PASS: fontes, pinos, seleção,
dispositivos extraídos, geometria, logs nativos e identidades foram examinados.

**Não se pode afirmar que todas as obrigações e toda a metodologia das
Fases 0–2 foram integralmente comprovadas.** A matriz contém lacunas
históricas, rastreio parcial de simulações isoladas e uma diferença concreta
entre o abutment previsto e o posicionamento espaçado implementado. Esses
pontos não são defeitos elétricos comprovados, mas também não foram dispensados
pelo auditor. A conformidade literal/metodológica requer os encaminhamentos
abaixo antes de uma declaração de cumprimento integral.

## 2. Conformidade por fase

| Fase | Obrigações examinadas | Estado técnico e documental |
|---|---:|---|
| 0 — Setup | 7: 5 atendidas, 1 parcial, 1 não demonstrada | Ambiente/SKY130 e uso integrado demonstrados. Tutoriais coletivos não demonstrados; compartilhamento inicial tem evidência parcial |
| 1 — Folhas | 7: 6 atendidas, 1 parcial | Seis famílias selecionadas, esquemáticos/netlists correspondentes, layouts, DRC/LVS e função integrada sustentados. Não se comprovou isolamento inequívoco de cada variante final reforçada |
| 2 — Gerador | 8: 6 atendidas, 1 parcial, 1 não demonstrada | Primeiro array 4×8 real gerado e verificado. Abutment literal não implementado; placeholders iniciais não demonstrados |
| **Total obrigatório** | **22: 17 atendidas, 3 parciais, 2 não demonstradas** | Nenhum item classificado como integralmente não atendido ou não aplicável; atendimento parcial não significa ausência de divergência |

Os outros oito itens da Etapa 1 são recomendações, exemplos, dependências
ou decisões e têm avaliação separada. Em particular, a validação da
especificação pela equipe/orientador (F0-05) não foi demonstrada no corpus;
as seis famílias e o decoder são seleções técnicas identificadas, não
aprovação acadêmica atribuída aos orientadores.

A matriz completa, com procedimento, artefato, limite e criticidade por ID,
está em [04](04_technical_evidence_audit.md). Ela não é uma porcentagem de
qualidade nem substitui a leitura das ressalvas.

## 3. Resultados tecnicamente sustentados

- **Biblioteca:** cinco folhas preservadas e decoder atual de **33 MOS** com
  quatro keepers. Auditor do handoff conferiu os vínculos e 3.020 arquivos
  indexados; seis netlistagens Xschem atuais coincidiram com as congeladas.
- **Gerador:** composição Python 4×8, pinos formais respeitados, 32 bitcells,
  quatro WL, oito pares BL/BLB; emissão atual de Tcl idêntica ao artefato
  de execução. Os dispositivos reais, não placeholders, compõem o GDS.
- **Top físico:** **1.493 MOS = 401 customizados + 1.092 HD**; contagem e
  mapeamento por terminais/coordenadas extraídos recalculados de forma
  independente do gerador. Top GDS único, 540×380 µm, referências resolvidas.
- **DRC/LVS:** logs vinculados ao GDS final com zero violações, comparação
  expandida de dispositivos, pinos e W/L; negativos de gate/bulk/W/L
  examinados. Não foram reexecutadas ferramentas físicas nesta etapa.
- **Reprodução:** execução física histórica corroborada com o GDS auxiliar
  encontrado por hash exato; igualdade binária após remover somente datas e
  SPICE extraído idêntico. Não se alegou novo rebuild integral sem cache.
- **Digital adicional:** logs reconciliados com **154.303 checks RTL** e
  **15.619 por execução GLS**, macro preservada, 20 FF e oito ebufn físicos.
  O pacote estrito atual RTL tem a ressalva documental da seção 4.
- **Elétrica adicional:** análises dos raws completos recalculadas: original
  **128 bits + 392 checks**; dirigida **1.332 checks totais/160 bits incluídos**;
  cinco partidas **3.383/240**; C1 **1.150/72** e C2 **1.281/48**, sem falhas
  nos critérios inspecionados. São reanálises, não novas simulações.

Os resultados elétricos limitam-se a **TT, 1,8 V, 27 °C, clock experimental
20 ns, conectividade e junções extraídas, sem RC detalhado dos fios**.
Checks de bits estão incluídos nos totais, quando indicado; GLS sintetizada
e roteada repetem cobertura. Não há soma desses contadores como “testes únicos”.

## 4. Pendências e sua importância

### 4.1 Nenhum bloqueio funcional/estrutural demonstrado

Não foi encontrado circuito final falhando nos acessos auditados, array
ausente, GDS sem vínculo com gerador, divergência LVS do objeto selecionado
ou DRC pendente nesse objeto. Essa conclusão é limitada à referência e
às condições examinadas; não prova inexistência de qualquer outro defeito.

### 4.2 Ressalvas oficiais que exigem tratamento explícito

| Item | Pendência comprovada da avaliação | Ação recomendada |
|---|---|---|
| F2-01 — abutment | Há células espaçadas com roteamento: pitch 30×25 µm e bbox de bitcell 17,25×12,92 µm. A composição funciona, mas não é encostamento direto | Discutir se a alternativa atende à intenção acadêmica do item 10 e registrar a decisão competente. Se o abutment literal for exigido, adequação/requalificação torna-se condicionante do aceite; não foi autorizada/executada aqui |
| F1-04 — isolamento | Evidência funcional selecionada é forte em integração; parte da caracterização isolada pertence a drafts ou não identifica inequivocamente a variante final | Localizar bancada/resultado da revisão correta ou complementar somente o isolamento faltante, mantendo histórico e hashes |
| F0-03 — tutoriais | Execução coletiva não identificada em registro verificável | Solicitar identificação do tutorial/sessão e relato/registro existente; não afirmar que não ocorreu nem inventar prova retroativa |
| F0-07 — compartilhamento | Git colaborativo e specs comum demonstrados; disponibilidade a todos no primeiro dia não datável | Esclarecer histórico com a equipe; não exigir formato documental que P não prescreve |
| F2-03 — placeholders | Primeiro código versionado identificado já usa células reais | Localizar protótipo/registro anterior, se houver, ou reconhecer lacuna de comprovação metodológica |

Essas pendências impedem um parecer **sem ressalvas** de cumprimento integral
de P. Não justificam descartar o array funcional ou exigir caracterização de
Fase 3 para compensar falta de registro histórico. A decisão sobre equivalência
metodológica do abutment não pode ser tomada silenciosamente pelo auditor.

### 4.3 Pendências internas não bloqueantes do resultado do Marco 2

1. **Proveniência estrita da regressão RTL:** `verify_core_inputs` rejeita um
   documento de interfaces atualizado após o run; só foram acrescentados
   links, sem mudança de RTL/TB/scripts. Logs reconciliam, mas não se deve
   apresentar a verificação estrita atual como aprovada. Produzir evidência
   nova em rodada própria ou uma reconciliação explicitamente documentada,
   sem editar o recibo antigo para simular que já tinha esses insumos.
2. **Ambiente de reprodução:** Magic 8.3.684 usado no top é instalação lateral
   documentada; a imagem-base atual fornece 8.3.589. Preparar o ambiente correto
   antes de nova execução física. Os raws adicionais precisam do bundle local
   ou regeneração para reanálise integral em outro clone.
3. **Aprovações e datas:** identificar a validação da especificação/alcance das
   frentes extras. Registros de entrega/revisão posteriores aos marcos
   planejados não comprovam conclusão nas datas originais. Esta auditoria
   avalia o estado técnico atual, não certifica pontualidade ou reprogramação
   acadêmica aprovada.
4. **Documentos históricos:** comentários/relatórios que dizem “não publicado”
   ou “binding futuro” têm contexto datado e não descrevem o fluxo completo
   atual. Não foram corrigidos retroativamente.

## 5. Riscos arquiteturais e atividades futuras

O [relatório de arquitetura](05_architecture_review.md) separa riscos de
defeitos. A cadeia fixa de 80 inversores e taps 24/40/60/80 depende de PVT,
cargas/slews e interconexão. As guardas nominais positivas não são garantia
universal. A escolha de 50 MHz está registrada como ensaio; não foi encontrada
justificativa quantitativa de sistema ou Fmax correspondente.

O sense recebe diferencial grande nos casos ensaiados. Não se demonstrou
que ele está otimamente temporizado nem que precise ser antecipado. O caminho
SA_OUT→RAW→FF_D→FF_Q→DATA foi distinguido: DATA ficou válido **0,489–0,549 ns**
após a descida pública somente nos bits/casos/carga medidos. Não é especificação
garantida de atraso, enable/disable ou turnaround. Referência Liberty de
setup/hold a 25 °C foi usada como screening contra SPICE a 27 °C, não STA.

A proposta reserva à Fase 3 extração/caracterização de timing e potência,
corners TT/SS/FF no escopo adaptado, SNM Monte Carlo reduzido com N≥200 e
geração automática de `.lib`. À Fase 4 cabem views/configurações finais.
Não se classificaram essas entregas como falhas obrigatórias do Marco 2;
também não se declararam realizadas por existirem alguns testes antecipados.

## 6. Prontidão preliminar para a Fase 3

**Há base técnica utilizável para planejar a Fase 3**, com biblioteca e
protótipo 4×8 identificados. Não é autorização para iniciar suas campanhas
nem atestado de que todas as dependências já estão resolvidas.

Antes da execução correspondente, é necessário:

- Deliberar as ressalvas oficiais e identificar a aprovação da especificação.
- Resolver a sequência de alvos: P prevê caracterizar pelo menos 8×8 e 32×8,
  mas a generalização completa aparece depois, na Fase 4. O gerador físico
  auditado é 4×8 fixo. Planejar a obtenção desses alvos ou mudança aprovada;
  não fingir que seus layouts já existem nem tornar os quatro obrigatórios
  retroativamente no Marco 2.
- Fixar condições e métodos das futuras medidas e o ambiente reproduzível,
  incluindo alcance dos modelos e dos parasitas. Contingência de corners
  ou configurações depende de decisão documentada, não de corte automático.

Não há recomendação de alterar agora as seis folhas, taps ou protocolo.
Nenhuma atividade da Fase 3 foi iniciada nesta auditoria.

## 7. O que a Etapa 3 deve confrontar independentemente

1. A suficiência dos vínculos de seleção, netlists, extração e DRC/LVS do
   **mesmo** objeto gerado — sem usar este parecer como única prova.
2. A interpretação de F2-01: diferença de metodologia reconhecida e quem
   pode aprovar sua equivalência ao objetivo acadêmico.
3. O rastreio da simulação isolada das variantes finais e os registros
   históricos de tutorial/compartilhamento/placeholders, sem presumir omissão
   de execução nem inventar trajetória.
4. A limitação da regressão RTL estrita após alteração documental e a distinção
   entre logs funcionais válidos e evidência completa atualizada.
5. Os limites do clock, da cadeia de fases, dos modelos, da carga de DATA
   e da reanálise com raws opcionais, sem exigir caracterização futura para M2.

## 8. Entrega e preservação

Novos documentos desta etapa:

- [04 — evidências e matriz](04_technical_evidence_audit.md).
- [05 — arquitetura e compromissos internos](05_architecture_review.md).
- [06 — este parecer](06_phase2_technical_verdict.md).

Os documentos 01–03 e a implementação permanecem intactos. Não foram
alterados RTL, SPICE, esquemáticos, layouts, MOS, taps, gerador, manifestos
ou aceites selados. Os commits desta rodada são documentais, na branch de
auditoria; não há merge ou mudança dos PRs #7/#8.

O fechamento formal e a passagem de fase dependem da revisão humana e da
deliberação sobre as ressalvas, não da emissão automática deste relatório.
