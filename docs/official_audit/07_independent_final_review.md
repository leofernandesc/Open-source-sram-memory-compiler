# Revisão independente final — Fases 0, 1 e 2

Data: 05/11/2026. Implementação: `3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6`.
Base documental: `851336a68e17b85c7cca9962ef873eef4fc23930`.

## 1. Metodologia e independência

A ordem executada foi: leitura integral da proposta, inspeção de fontes e evidências primárias, registro preliminar abaixo, leitura dos seis relatórios e confronto final. A seção 2 foi escrita antes de abrir `docs/official_audit/01..06`. Os documentos técnicos de implementação e seus receipts foram consultados como índices, com confirmação nos arquivos originais. Independência aqui significa reconstrução do raciocínio e verificações próprias nesta sessão; não equivale a certificação institucional por outra pessoa.

PDF conferido em `/home/leofernandesc/Downloads/Proposta_Adaptada_Memory_Compiler_OpenSource_09092026.pdf`: seis páginas, 192.152 bytes, SHA-256 `59021f96db0202678b9ec4c9f6195fceeb95cfd60a8ecf5c5a3845a72c332644`. Leitura integral com `pdftotext -layout`, incluindo organização, contingências e especificação proposta. A seção 4 determina o sequenciamento das fases; a seção 7 torna gerador e DRC/LVS irredutíveis. As inconsistências editoriais da proposta (quatro pessoas versus três; 8×8 chamado menor da faixa que inclui 4×8) não autorizam inventar requisitos para o Marco 2.

`git status --short` inicial vazio. `git ls-remote origin` confirmou ambas as referências acima. `git diff --stat 3d14880 851336a` contém exclusivamente os seis relatórios anteriores. Nova branch documental criada dessa base; nenhuma diferença de implementação entre ela e `3d14880`. Não houve reconstrução física, simulação SPICE nova, alteração de selos, RTL, scripts, layouts ou relatórios anteriores. Verificações auxiliares foram feitas em memória ou fora dos artefatos históricos. A consulta inicial à memória de trabalho serviu somente para localizar o histórico de regressão digital; não foi tomada como evidência de aceite.

## 2. Parecer preliminar registrado antes dos seis relatórios

- **Fase 0:** ambiente e estrutura técnica demonstrados; execução coletiva dos tutoriais e compartilhamento desde o dia 1 não demonstrados pelos registros examinados. Ausência de registro não prova ausência de execução.
- **Fase 1:** seis famílias selecionadas identificadas pelo seletor keeper, máscaras e SPICE conferidos por hash; logs nativos de LVS das seis correspondem a primitivas e mostram match único. O decoder corrente tem 33 MOS, não os 29 da baseline antiga. A prova isolada preservada do sense amp usa sizing anterior; WL driver também exige rastreamento próprio. Evidência integrada das variantes finais é pertinente e impede inferir defeito da mera lacuna isolada.
- **Fase 2:** produto central demonstrado para 4×8: Python gera posições, conexões e script Magic; fluxo integra binding HD, roteia e exporta GDS; DRC completo e LVS transistor a transistor preservados. Conferência da extração confirma 32 posições distintas, 16 gates de acesso por WL, 401 MOS custom e 1.493 MOS totais. Não há defeito impeditivo demonstrado nesta inspeção.
- **Abutment:** a implementação é tiling espaçado com roteamento explícito. A proposta pede literalmente encostamento; não foi encontrada autorização formal para substituí-lo. Essa é uma divergência metodológica real, sujeita à deliberação, sem invalidar automaticamente o array gerado e verificado.
- **Proveniência:** selos de 171 e 80 arquivos íntegros. Regressões recentes diferem do estado corrente apenas no documento de interfaces; regressões mais antigas também diferem nos scripts de verificação. É necessário identificar o receipt antes de generalizar a alegação de identidade.
- **Elétrica:** evidência TT/1,8 V/27 °C, clock experimental de 20 ns, sem RC de fios; janelas e guardas nominais não são Fmax nem limites públicos. Há base técnica para caracterização, sem pressupor resultado favorável em outros corners.

Este parecer preliminar não declara conformidade integral nem aprovação formal. A questão central é separar produto físico demonstrado, procedimentos históricos não comprovados e decisões metodológicas ainda não aprovadas.

## 3. Critérios reconstruídos e revisão das Fases 0–2

O critério de encerramento não se resume ao título do marco: os procedimentos antecedentes também pertencem à proposta. Entretanto, uma lacuna histórica e uma falha física comprovada têm consequências diferentes. Não há meta de MHz, área, número de testes ou robustez industrial no Marco 2. A caracterização atribuída ao Papel 2 na p.3 não antecipa todo o conteúdo dos itens 14–17 para o Marco 1: a metodologia datada pede funcionalidade isolada na Fase 1 e caracterização na Fase 3.

| Obrigação oficial reconstruída | Fonte no PDF | Resultado desta revisão | Efeito |
|---|---|---|---|
| Ambiente gratuito, SKY130 e ferramentas instaladas/testadas | pp.2–4, §2; itens 1 e cronograma | Sustentado por scripts, netlists Xschem preservadas e logs nativos de Magic/Netgen/ngspice/Icarus; ambiente documentado | Base técnica atendida; não certifica instalação na semana planejada |
| Tutoriais oficiais coletivos | p.4 item 2; p.6 §7 | Não demonstrados nos registros consultados | Ressalva de metodologia, explicitamente não dispensável por simples silêncio |
| Especificação final documentada | p.4 item 3; p.5 §5 | `specs/technical_specification.md` e contratos identificam o produto; aprovação acadêmica identificável não localizada | Documento existe; validação competente precisa ser registrada para o aceite formal |
| Git organizado e compartilhado desde o início | pp.3–4 §3/item 4 | Pastas e colaboração inicial demonstradas; data do acesso de todos não demonstrada | Ressalva histórica, sem defeito no produto atual |
| Topologias, esquemáticos e layouts individuais | p.4 itens 5/6/8 | Seis famílias reais vinculadas ao seletor; topologia 6T e latch diferencial inspecionados | Atendido no conjunto selecionado |
| Função isolada de cada folha | p.4 item 7 | Evidência isolada histórica e integrada relevante; lacuna delimitada de identidade das variantes finais | Não declarar cumprimento integral do procedimento; ver §6 |
| DRC/LVS de todas as folhas | p.4 item 9/Marco 1 | Logs nativos e hashes conferidos para as seis seleções | Marco físico 1 demonstrado |
| Tiling com abutment | p.4 item 10 | Tiling sim; abutment direto não | Equivalência metodológica exige deliberação |
| Python de posicionamento, inicialmente com placeholders | p.4 §3/item 11 | Python e posicionamento atuais demonstrados; etapa inicial dummy não demonstrada | Lacuna de trajetória, não ausência do gerador |
| Netlist estrutural e teste com folhas reais | p.4 itens 12/13 | Demonstrados nas conexões emitidas e extraídas | Atendido |
| Primeiro array físico em GDSII, DRC/LVS completos | p.4 Marco 2; p.6 §6/§7 | Demonstrado para 4×8 | Produto central atendido |

A decomposição anterior em 22 obrigações é defensável, mas não é uma unidade normativa da proposta nem um percentual de conclusão. Concordo com seus estados substantivos. Acrescento a distinção explícita: **a subexigência de abutment direto não foi implementada**, ainda que o requisito composto tiling/abutment possa receber rótulo parcial. Não classifico sua ausência como indeterminada nem como defeito elétrico.

Datas planejadas (12/out e 02/nov) não são datas de conclusão provadas: os logs e commits atuais incluem trabalho posterior. Não há prova suficiente aqui para certificar pontualidade ou aprovação de reprogramação. Isso pertence ao acompanhamento acadêmico e não altera a identidade do circuito revisado.

As contingências da p.6 admitem reduzir primeiro configurações e depois corners, mediante necessidade e documentação; não dispensam gerador/DRC/LVS. Não encontrei contingência autorizando silenciosamente trocar abutment, cortar tutorial coletivo ou atribuir um ensaio antigo a outro sizing. Também não há fundamento para exigir Liberty, Monte Carlo ou todos os quatro layouts agora.

## 4. Gerador e produto efetivamente verificado

### 4.1 Seleção, composição e emissão

`release/phase1_current.json:2` seleciona `release/phase1_keeper/manifest.json`. As cinco folhas não decoder continuam em `release/phase1/cells/`; o decoder selecionado está em `release/phase1_keeper/cells/row_decoder/`. A baseline antiga `release/phase1/manifest.json` tem decoder de 29 MOS e não deve substituir a seleção de 33 MOS.

`tools/phase2_core.py:16` (`selected_leaves`) verifica hashes e extrai pinos formais; `graph:36` constrói quatro linhas de oito bitcells; `audit:64` verifica inventário e mapas; `emit:113` exporta um harness estrutural. Esse harness com portas de fase é intermediário. O circuito físico entregue vem de `tools/run_phase2_fabric.py:23` (`generate`), que emite a referência `leaf_fabric` com as definições SPICE selecionadas, não apenas símbolos ou memórias comportamentais.

Conferi todos os hashes de views declarados pelas seis seleções. Inventário: 32×6 bitcell + 1×33 decoder + 4×4 WL + 8×3 precharge + 8×10 write + 8×7 sense = **401 MOS em 61 folhas**. `macro_binding.v` acrescenta fases e adaptadores HD; o wrapper e o controle adicionam captura e barramento. O GDS final contém **1.493 MOS**, incluindo 1.092 HD. Vinte FF pertencem à interface, não substituem os 32 bits SRAM.

`tools/run_phase2_place.py` constrói a colocação/rota externa ao fabric; `tools/finish_phase2_layout.py:133–159` importa GDS/DEF, escreve GDS, achata e extrai; linhas 175–184 verificam pinos e comparam o top. `scripts/reproduce_phase2_4x8.sh:22–28` encadeia digital, binding, fabric, route, layout, gds e gls. Não exige um GDS manual independente como entrada final.

Reexecutei somente `generate` em pasta temporária fora do repositório. O `fabric.tcl` emitido é byte a byte igual ao preservado em `reports/phase2/fabric/fabric.tcl`. Não executei esse Tcl. O helper atual de normalização também pode acrescentar declarações de modelo não instanciadas à referência; identidade do Tcl não significa identidade textual irrestrita de todos os intermediários. A evidência relevante de circuito continua sendo instâncias, parâmetros e LVS identificado.

### 4.2 Conexões físicas e independência do oráculo

Gerar referência e layout de um grafo comum cria risco de erro comum. Por isso a prova não se encerra no LVS. Inspecionei `tools/review_phase2_structure.py:15` (`inspect`) e chamei sua função de leitura, sem `main`: resolve aliases de `final_flat.ext`, terminais, bulks e coordenadas reais e usa definições SPICE da referência hierárquica. Confirmou 32 posições, 16 gates NFET de acesso por WL, oito pares BL/BLB distintos, alimentação/corpos corretos, associação de sense/precharge por coluna e ligação SA_OUT→mux e FF_Q→tri-state por bit.

As coordenadas médias de acesso extraídas nas oito colunas da primeira linha são 44.685,5; 50.685,5; 56.685,5; 62.685,5; 68.685,5; 74.685,5; 80.685,5; 86.685,5 unidades internas. As médias y por linha são 41.040,5; 46.040,5; 51.040,5; 56.040,5. Confirmam ordem espacial e pitch sem confiar somente nas constantes do gerador. Esse checker é evidência preexistente reavaliada, não foi escrito nesta auditoria; a leitura de conexões, logs expandidos e ensaios elétricos complementa sua independência limitada.

Também fiz leitura binária própria dos registros STRNAME/SNAME do GDS: 20 células, único top `sram_4x8_wrapper`, nenhuma referência ausente. Os valores de bbox das folhas foram calculados diretamente dos retângulos MAG. Não se inferiu conectividade pelo aspecto de uma imagem.

### 4.3 DRC/LVS completos e proveniência física

Objeto selecionado: `reports/phase2/final_gds/sram_4x8.gds`, SHA-256 `d45ab0ca9438116a61c5db39ef2577a6dc08c510e40dd6f6ade87a1b9299d880`.

`reports/phase2/final_gds/verify.tcl:1–21` reimporta esse GDS, carrega o top, expande/achata, ativa `drc(full)` e extrai. `magic.txt:45–48` registra estilo full e `FINAL_GDS_DRC=0`, com Magic 8.3.684. É checagem do bloco completo. Conferi hashes dos artefatos presentes relacionados no receipt final, sem divergência.

`reports/phase2/final_gds/lvs.txt` expande fabric, seis famílias e HD, compara 730 redes e declara `Circuits match uniquely.`. A referência vem das folhas selecionadas e das definições transistor-level HD; a macro black box usada na síntese não permanece como substituto do array no LVS. Os 1.493 MOS tornam-se 1.459 equivalentes após 34 fusões de paralelos em ambos os lados. Isso explica a diferença de contagem; não são dispositivos perdidos. W/L, modelos, pinos e corpos entram na comparação; tolerância de 1% e exclusão de propriedades de junção não equivalem a qualificação de parasitas ou de fabricação. Os negativos preservados em `review_20261104/lvs_negative/` fornecem contraponto às etiquetas de sucesso, sem exigir nova execução Netgen aqui.

### 4.4 Reprodução histórica

O receipt `reports/phase2/review_20261104/reproduction/results.json` identifica o candidato por hash `f300a5fb3d49d4acbde72ba8c84134d7da9e389f2b6bd1a38dabd27fa8751e75`. Conferi esse hash no arquivo local `build/phase2/gds-check-t0uycdk6/sram_4x8.gds`.

Uma rotina binária própria zerou exclusivamente os 24 bytes de datas nos registros BGNLIB/BGNSTR de cada arquivo. Original e candidato deram SHA-256 normalizado `95b09a9983b750bca450f86005afd78f26fa347f4aa3969099f0278e65807573`. O `final_extracted.spice` desse candidato também é idêntico ao selecionado, incluindo junções. A diferença entre esse hash normalizado e a convenção anterior `6d005b…` não é divergência geométrica: a operação de normalização é diferente e nenhum hash substitui o arquivo original.

Há, portanto, reprodução física histórica corroborada pelos bytes dos artefatos, além da emissão Python leve repetida agora. Não houve rebuild físico nesta revisão. O candidato auxiliar está no cache local, não publicado nessa pasta; outro clone dispõe dos registros e do procedimento, mas precisa regenerar esse candidato para repetir a comparação. A reconstrução limpa com bundle em `extension_20261104/clean_reproduction` é **reanálise sem nova simulação**, não uma segunda reconstrução física autônoma. Ambas as evidências são válidas dentro de seus alcances.

## 5. Abutment: fato técnico e consequência normativa

Em `run_phase2_fabric.py:40–45`, a posição é `(6000*b, 36000+5000*r)`. A escala é 0,005 µm/unidade interna (`tools/phase2_abstract.py`). O bbox dos retângulos da bitcell é `(-450,-2942)..(3000,-358)`: **17,25×12,92 µm**. O pitch é **30×25 µm**; a separação geométrica correspondente é 12,75 µm horizontal e 12,08 µm vertical.

1. **É tiling?** Sim, composição repetitiva regular de células em linhas/colunas; tiling em geração de arrays não exige por si só gap zero.
2. **É abutment direto?** Não. As conexões são promovidas dos pinos M3 a troncos M4 e trilhas M5 com vias explícitas (`generate`, aproximadamente linhas 65–135). Testes antigos de bitcell encostada não alteram esse fato do array.
3. **Diferença:** a proposta pede especificar como as células se conectam por encostamento; a solução usa posicionamento espaçado e roteamento adicional. Há custo de área e futura interconexão a caracterizar, sem meta oficial de densidade infringida demonstrada.
4. **Compromete o objetivo funcional?** Não foi demonstrado comprometimento: o array real foi gerado, conectado e passou as comparações físicas. Nenhuma propriedade funcional de SRAM exige, isoladamente, que toda conexão entre células seja feita por encostamento.
5. **Leitura da proposta:** o item 10 é literal ao dizer abutment e explicá-lo como encostamento. Não é defensável declarar cumprimento literal chamando qualquer roteamento de abutment. É defensável propor equivalência quanto ao objetivo acadêmico de compilar um array, dado o resultado do Marco 2; essa é uma aceitação de alternativa, não uma tradução do termo.
6. **Aprovação:** não localizada decisão da equipe/orientadores aceitando especificamente essa alternativa. Handoff de engenharia e aprovação experimental não bastam.
7. **Classificação final:** **divergência metodológica condicionante do encerramento formal**, sem bloqueio técnico funcional demonstrado. Aceitar a alternativa documentadamente permite encerrar sem redesenho por esse motivo. Se a autoridade competente exigir o método literal, a adequação e nova qualificação tornam-se necessárias por essa decisão. A auditoria não pode escolher unilateralmente nenhuma dessas políticas.

## 6. Simulação isolada e variantes finais

| Família selecionada | Identidade/configuração | Evidência preservada e conclusão proporcional |
|---|---|---|
| Bitcell 6T | PU/PD/acesso 0,42/1,26/0,60 µm; 6 MOS | Bancadas `sims/tb_bitcell_6t*.spice`, resultados de escrita/leitura/SNM e PEX selecionado vinculado nos CSV G7. Funções de armazenamento/leitura/escrita e retenção também observadas no top. Não se usa SNM determinístico como Monte Carlo futuro |
| Sense | 7 MOS; latch PMOS 1,89 µm e NMOS/tail 0,975 µm; sample PMOS 2 µm | `sims/sense_amp_characterization_pvt.csv:1–4` identifica SCH `ad8f819…`, correspondente ao draft 1,26/0,65 µm em `cells/sense_amp.sch:34–40`, não à seleção reforçada. PEX scale1p5 hash `ab60dc3…` aparece nos CSV G7 e coincide com o congelado. Função final demonstrada em integração; curva isolada do draft não qualifica sensibilidade/offset da variante final |
| Precharge | Três PMOS 2,52 µm | PEX `cf0fa457…` identificado nos G7; recuperação/equalização em integração e pré-carga das bitlines no top. Evidência isolada de capacitância não é sozinha prova de toda a função |
| WL driver | Dois inversores, quatro MOS, estágios 1,68/5,04 µm | `run_leaf_peripheral_smoke.py:22–30,74–96,212–219` lê SCH/PEX canônicos, cujos tamanhos não são automaticamente os da variante congelada. `cells/wl_driver.sch:22–25` tem 0,42/0,84 µm. CSV smoke antigos não carregam identidade suficiente para atribuição à variante final. G7 identifica PEX final `c6d099c1…`; top verifica seleção e liberação das quatro WL |
| Write driver | Dez MOS, inversão WE 0,84 µm e saída 5,04 µm | G7 de escrita identifica PEX `3995ce67…` e mede flip/recuperação; DIN capturado e preservação de palavras são exercitados no top. Não se confunde tri-state de DATA público com isolamento do driver de BL |
| Decoder | 33 MOS, quatro keepers W=0,84/L=0,15 µm | `sims/row_decoder/results/keeper_review_20261029/` preserva casos/decks e resultados próprios, além da integração final. Campanhas do decoder antigo 29 MOS e G7 sem decoder não substituem essa qualificação |

O manifesto final seleciona o sense de SPICE `52f80d15…` e SCH `3ac166bc…`; o WL de SPICE `843808b9…` e SCH `4e1772f6…`. As diferenças de sizing são positivas e verificáveis, não inferidas do nome de uma figura. As versões finais têm provas físicas próprias; no sense, a quantização de 0,975 a 0,98 µm está dentro da tolerância LVS declarada, sem implicar identidade matemática exata.

**Falta específica:** uma cadeia inequívoca bancada→netlist efetivamente executada→resultado isolado das variantes finais, sobretudo sense e WL. O registro isolado deve identificar sizing, pinos, modelos e resultado funcional pertinente. Primeiro localizar entradas/relatos já existentes; somente se inexistentes, complementar pontualmente em tarefa autorizada posterior. Não há fundamento para repetir todas as simulações ou exigir PVT completo agora.

Integração complementa e, para a demonstração de funcionamento nominal do array, fornece prova direta mais pertinente que uma folha idealizada. Entretanto, não transforma teste hierárquico em execução histórica do procedimento isolado exigido no item 7. Para conformidade integral, recuperar a comprovação específica ou registrar aceitação explícita da evidência integrada como alternativa delimitada. A lacuna por si só não demonstra defeito do sense ou do WL, nem obriga redesenho.

## 7. Registros históricos e integridade

### 7.1 O que o Git permite afirmar

Histórico conferido: `528291c`, 20/09, inicialização; `33c5375`, mesmo dia, diretórios; `07c63e3`, 21/09, GITFLOW de outro autor; `631e7fd`/`87ab2a2`, esquemático/especificação de bitcell; `5f39633`, 23/09, especificação geral. Isso demonstra colaboração inicial e destino comum para specs. Não prova primeiro push, acesso simultâneo de todos desde o dia 1 ou tutorial coletivo.

No histórico consultado do gerador, `d96896d` já contém uso real das folhas. Não localizei protótipo físico dummy anterior. Black box RTL, `.gitkeep`, fillers e stubs não são prova desse desenvolvimento inicial. Também não são prova de que ele nunca aconteceu fora dos commits.

Tutorial coletivo é procedimento expressamente protegido pela contingência; placeholders são estratégia para paralelismo; compartilhamento inicial é requisito organizacional. A falta de registro compromete a **comprovação** desses procedimentos, com intensidades diferentes, não a validade elétrica do GDS atual. Encaminhamento proporcional: buscar registros/relatos existentes e identificar autor/data/alcance; se irrecuperáveis, reconhecer a impossibilidade de comprovar e obter disposição humana explícita. Uma sessão de aprendizado feita agora pode sanar uma necessidade atual, mas jamais deve ser datada como execução passada. Não se exige criar um protótipo dummy retrospectivo.

### 7.2 Regressão RTL: selecionar o receipt correto

Conferi `reports/digital/phase2_review_20261104/results.json`, o receipt citado pela auditoria anterior. Dos insumos relacionados em `source_sha256`, somente `docs/sram_4x8_interfaces.md` difere. Snapshot local: `build/digital/run-kfaeq5te/sources/`; hash esperado `06bb04b583814f6a0709484ddb845241204cc4e499521810a7ad644cba7bbf8b`, atual `e4324add33a36af3bf6f92590df222fd6f63076152a5328a69b203df68002fc9`.

O diff desse snapshot contém exatamente seis linhas adicionais: links e explicações sobre contrato temporal/partida. Não muda a definição de sinal nem código executável. RTL, TB, scripts e testes de verificação desse run coincidem por hash. Todos os 38 logs relacionados coincidem. Chamei `reconcile_core_results` (linha 382): recompôs 154.303 checks e validou os diagnósticos negativos. Chamei `verify_core_inputs` (linha 425): **rejeitou o documento atual**, como deveria. Não se publicou outro PASS nem se editou hash antigo.

Inspeção adicional mostrou por que não se deve generalizar: `phase2_final_review` e outros receipts mais antigos também têm drift do runner/testes, enquanto `phase2_log_reconciliation` conserva apenas drift documental, mas um texto documental anterior diferente. Essas diferenças não contradizem a conclusão anterior, que identificou corretamente o run `phase2_review_20261104`; refinam seu alcance. A comparação inicial com um receipt antigo foi corrigida antes de formular conclusão final.

**Risco:** baixo para validade funcional do mesmo RTL e para o Marco 2 físico; real para quem afirma identidade integral do pacote atual. Esta seção é uma reconciliação documental explícita e preserva a rejeição estrita. Não há necessidade de nova regressão apenas para mudar a data do relatório; se for necessário um selo estrito atual, executar futuramente em diretório novo ou adotar formalmente esta reconciliação, sem adulterar o original.

### 7.3 Selos e limites de disponibilidade

Recalculei os selos de 171 arquivos em `review_20261104/acceptance/results.json` e 80 em `final_polish_20261104/final_state.json`: nenhuma divergência. Também conferi os hashes nativos relacionados em `evidence_sha256` das seis provas físicas de folhas: todos coincidem, e os seis logs LVS contêm match único. Esses números delimitam o conjunto conferido; não são pontuação de qualidade ou prova autônoma de cobertura.

O raw original está em `portable_raw/waveform.dat.gz`; outros transientes completos usados localmente estão em `build/phase2`, ignorados. O clone público não permite reanalisar todos sem bundle ou regeneração. A imagem-base não contém necessariamente a instalação lateral Magic 8.3.684. O guia identifica esse preparo; não se presumiu que a tag Docker bastasse nem se ligou/reparou o container parado nesta revisão.

## 8. Arquitetura, evidência elétrica e seus limites

A inspeção de `rtl/sram_controller.v`, `rtl/sram_4x8_wrapper.v` e `physical/phase2/macro_binding.v:19–39` confirma captura de requisição/endereço/DIN na subida, saída na descida por FF positivo com clock invertido, 80 inversores preservados e taps 24/40/60/80. Clock externo experimental: 50 MHz, período 20 ns; os taps não geram essa frequência e não representam ns.

As equações físicas conferidas são:

```text
valid = READ_Q | WRITE_Q
PRECH = valid & ((CLK & D24) | D80)  # baixo: pré-carga
WE    = WRITE_Q & CLK & D40
PCLK  = valid & CLK & D60            # baixo: reset do decoder
SCLK  = READ_Q & D80                 # baixo: amostragem; alto: regeneração
ROWr  = DECr & PCLK
```

Não basta equivalência booleana: a sequência depende do atraso real. Os relatos de guarda negativa no piloto inicial referem-se a uma implementação anterior; WE no tap 40 já está corrigido em `3d14880`. Não há fundamento para imputar ao top atual o defeito histórico rejeitado.

Nesta revisão reexecutei **somente análise**, no host com NumPy, de C1 e C2 completos por `analyze_phase2_extension_timing.measure:37`. A função confere hash do raw, integridade numérica e cruzamentos; não grava relatórios nem chama ngspice. Recalculou 484 e 336 screens de pré-carga/estabilidade sobre os mesmos transientes, sem falhas. Não são novos acessos ou simulações. As medidas abaixo coincidem com os receipts preservados:

| Relação observada em C1/C2 | Resultado nominal | Alcance |
|---|---|---|
| PRECH80↑ até WE20↑ | mínimo 0,211331 ns | 14 escritas; exclusão por limiares, não ausência universal de corrente de sobreposição |
| WL80↑ até SCLK20↑ | 0,238544–0,243873 ns | 15 leituras; wordline ativa antes da referência do sense |
| WL20↓ até PRECH80↓ | mínimo 2,196225 ns | 29 acessos; margem nominal de recuperação |
| WE20↓ até PRECH80↓ | mínimo 2,290428 ns | 14 escritas |
| Diferencial assinado BL/BLB no sense | mínimo 1,737077 V; 50 ps antes, 1,571402 V | Polaridade correta e diferencial grande, sem wire RC e offset estatístico |
| FF_D válido antes da captura local | mínimo 7,240218 ns | 120 observações bit/ciclo; disponibilidade, não setup requerido |
| DATA após descida pública | 0,488832–0,548795 ns nos bits com mudança | 60 observações; exclui os aproximadamente 10 ns desde a subida da requisição |

O caminho é SA_OUT=DOUT_RAW → mux/FF_D → FF_Q → ebufn/DATA. Atraso de saída após a descida não é tempo total subida→resultado; este inclui a meia fase anterior, além das condições de entrada. Sinais já válidos devem ser tratados como limites inferiores de settling, não transições inexistentes. As janelas posteriores ≥2 ns são limitadas pela observação, não hold mínimo. A comparação com Liberty TT/25 °C não transforma o SPICE TT/27 °C em STA qualificado.

A máscara DATA depende de READ_Q e dos controles vivos `!CSb && !OEb && WEb`. Pode expor resultado anterior antes da nova captura; desabilitar controles vivos não cancela o acesso já capturado. C2 usa probes opostos de 1 kΩ, chave do mestre de 1 Ω e piso de 50 µA: mede condução/liberação nesse arranjo. Os intervalos de disable/enable preservados são compatíveis com o analisador e seus limiares; não garantem tDIS/tEN ou turnaround sob toda carga/slew. Probe que retira DATA de nível válido é ensaio de observabilidade, não prova de defeito em operação legal.

Partida: os decks históricos e suplementos não impõem `.ic`/`.nodeset` às bitcells/FF/sense. Duas capturas inativas são procedimento nominal de referência; cinco cenários adicionais incluem rampa de 1/5/10 ns e 0/2/3 capturas nas combinações declaradas. Zero capturas adicionais inclui espera após rampa; não significa acesso imediato. Palavra nunca escrita tem estado desconhecido. Não reanalisei todos esses raws de partida nesta terceira revisão: conferi os registros, critérios, vínculo ao circuito e o alcance da reanálise da segunda auditoria. Não alego novas simulações ou nova validação estatística.

A extração inclui conectividade e junções dos dispositivos; não representa PEX RC distribuído das interconexões. `independent_off_state_model_accuracy=NOT_ESTABLISHED` no handoff é limitação de modelo reconhecida, não falha física comprovada. Sem RC/PVT, não há garantia de fase, Fmax, potência, yield ou partida universal. Esses pontos justificam caracterização futura; não reprovam automaticamente o protótipo nominal.

## 9. Confronto com os seis relatórios

Li os seis documentos depois de registrar a seção 2. Os relatórios 01–03 distinguem corretamente escopo oficial, detalhes internos e etapas posteriores. Os relatórios 04–06, no conjunto, não confundem frequência experimental com Fmax, extração LVS com RC, acesso funcional com caracterização, nem reanálise com novas simulações. Não encontrei erro material que reverta seu parecer central.

| Requisito/afirmação | Conclusão anterior | Evidência primária examinada | Conclusão desta revisão e justificativa | Impacto no Marco 2 |
|---|---|---|---|---|
| Gerador→array→GDS→DRC/LVS | Produto central demonstrado | Tcl regenerado, folhas, netlists, extração, logs completos, GDS e candidato histórico | **Confirmada**; há vínculo verificável e comparação expandida | Sustenta aptidão técnica |
| Abutment | Atendimento parcial do item composto | Bbox MAG, pitch do código e coordenadas extraídas | **Confirmada com precisão de linguagem**: tiling atendido, subexigência de abutment direto não implementada; alternativa ainda não aprovada | Condição metodológica de aceite formal; não motivo automático de redesenho |
| Isolamento final SA/WL | Rastreabilidade parcial, função integrada demonstrada | Sizing SCH/SPICE, hashes CSV G7, smoke antigo e top extraído | **Confirmada**; integrado não deve ser apagado nem chamado de isolamento | Resolver comprovação ou alternativa aceita; sem defeito inferido |
| Tutoriais/Git/dummies | Lacunas de registro | Histórico inicial multiautor; primeiro gerador já real | **Confirmada**; não comprova não execução | Tratamento documental/humano, sem regressão artificial |
| Drift da regressão | Somente seis linhas documentais, RTL/TB/scripts iguais | Snapshot `run-kfaeq5te`, diff, 38 hashes e reconciliação dos logs | **Confirmada para o receipt citado**; não generalizar aos receipts anteriores com runner diferente | Baixo risco funcional; selo estrito atual continua rejeitado |
| Reprodução física e clone limpo | Física histórica; reanálise limpa com bundle | GDS auxiliar de hash exato, normalização binária e SPICE idêntico; clean receipts | **Confirmada**; nenhuma campanha de simulação nova é inferida da restauração de raw | Evidência suficiente sem rebuild integral nesta revisão |
| Clock, sense e captura | Nominal positivo, sem Fmax/STA | Binding e reanálise C1/C2 | **Confirmada**, inclusive diferença entre disponibilidade interna e requisito de setup | Base para Fase 3; sem requisito futuro antecipado |
| 22/17/3/2 e nenhum integralmente não atendido | Decomposição anterior | Proposta e matriz | **Não adoto os números como critério**; o rótulo parcial do item composto não significa cumprimento do abutment | Nenhuma mudança no mérito; melhora legibilidade da decisão |
| Prontidão seguinte | Base utilizável, alvos maiores ainda requerem planejamento | Gerador físico fixo 4×8; PDF §5 pede 8×8/32×8 | **Confirmada**; não é prontidão imediata de todos os insumos de caracterização | Planejar dependências antes das campanhas correspondentes |

Não identifiquei requisito técnico essencial ignorado que invalide o array, nem exigência indevida de Fase 3 usada pelos auditores para reprovar M2. Formalização da especificação é assunto legítimo; pedir nova justificativa de todos os detalhes já fixados pelo circuito seria desproporcional. O tamanho 4×8 escolhido satisfaz as duas redações da proposta: não é decisão pendente nesta entrega. Tampouco é pendência republicar a branch de implementação já publicada ou reabrir os PRs.

## 10. Parecer final e deliberações

**Parecer independente: produto técnico central das Fases 0–2 demonstrado e protótipo apto ao aceite técnico do Marco 2, com ressalvas metodológicas explícitas. Não há base para declarar conformidade integral irrestrita nem aprovação formal em nome dos orientadores.**

| Pergunta | Resposta |
|---|---|
| A. Produto central do Marco 2 demonstrado? | **Sim.** Python, células reais, referência estrutural, GDSII 4×8 e DRC/LVS completos vinculados |
| B. Todos os requisitos técnicos obrigatórios suficientemente demonstrados? | **Não no sentido literal integral.** Abutment direto não foi implementado e a prova de isolamento de todas as variantes finais não está completa; funções integradas e fechamento físico estão sustentados |
| C. Defeito funcional, estrutural ou físico comprovado impeditivo? | **Não identificado** no circuito/versão/condições examinados. Isso não é prova de inexistência universal de defeitos |
| D. Divergência metodológica dependente de aprovação? | **Sim**, sobretudo abutment; a disposição da lacuna de isolamento e registros históricos também deve ser explícita para cumprimento integral |
| E. Pendências bloqueantes? | Nenhum bloqueio técnico demonstrado do produto central. Antes de encerramento formal sem ressalvas: aprovar/dispor a alternativa de abutment, identificar validação da especificação e tratar comprovação/aceitação das lacunas. Se o método literal for mantido como condição, adequação será condicionante por decisão competente |
| F. Base para iniciar Fase 3? | **Sim**, para planejar e iniciar a caracterização sobre referência aceita; não estão prontos todos os alvos físicos previstos em §5. A disponibilidade de 8×8/32×8 deve ser resolvida antes das campanhas que os usam |

Por fase: **F0** tem ambiente e organização técnica demonstrados, com reservas históricas e de validação da especificação. **F1** tem biblioteca e Marco 1 físico demonstrados, função nominal sustentada e ressalva específica de isolamento final. **F2** tem o Marco 2 central demonstrado, sem abutment direto e sem prova da trajetória dummy inicial. Essas ressalvas são legítimas; nenhuma sustenta por si só a conclusão de que o gerador físico inexiste ou falhou.

### Decisões curtas para a reunião, por prioridade

| Prioridade / decisão | Motivo | Alternativas e consequências | Momento |
|---|---|---|---|
| 1. Aceitar tiling espaçado como alternativa ao item 10? | Divergência positiva de método; núcleo físico comprovado | Aceitar e registrar equivalência delimitada: encerra essa ressalva sem redesenho. Exigir abutment literal: planejar adequação e DRC/LVS correspondente; não declarar que o circuito atual já o faz | Necessária ao encerramento formal |
| 2. Como satisfazer o item 7 para variantes finais? | Sizing antigo não prova isolamento final; integração real é relevante | Recuperar prova existente: encerra lacuna por identidade. Complementar somente SA/WL e demais vínculos efetivamente faltantes: fecha procedimento. Aceitar integração delimitadamente como alternativa: registrar disposição competente, sem renomear o ensaio | Necessária à declaração de conformidade integral; não bloqueia tecnicamente estudo de caracterização |
| 3. Ratificar referência/especificação e dispor registros históricos? | Ausência de validação acadêmica identificada, tutorial coletivo e trajetória inicial não comprovados | Identificar aprovações/relatos existentes; se irrecuperáveis, registrar lacuna e encaminhamento aceito. Se tutorial coletivo ainda necessário, realizá-lo agora como atividade atual. Não fabricar datas nem obrigar dummies retroativos | Encerramento formal/metodologia |
| 4. Disponibilizar 8×8/32×8 e fixar condições da Fase 3 | Gerador auditado é físico 4×8; proposta exige esses alvos para caracterização | Antecipar generalização necessária e manter alvos/corners; ou aprovar replanejamento/contingência justificados. Consequências em cobertura/prazo explicitadas | Planejamento da Fase 3; não novo bloqueio retroativo de M2 |

O drift documental está reconciliado nesta revisão e não exige decisão de redesenho ou repetição funcional automática. Preparar Magic correto e disponibilizar raws são ações de reprodução, não decisões acadêmicas ainda abertas por princípio. As escolhas PVT/SNM/Liberty serão fechadas ao montar a campanha da Fase 3, sem transformá-las em condições retroativas deste marco.

### Registro de verificações desta terceira revisão

Executados: identidade PDF/Git/remoto; hashes de seleções/selos/logs; leitura dos seis relatórios após a conclusão preliminar; emissão Python temporária; inspeção extraída por terminais/coordenadas; parser binário próprio de hierarquia/datas GDS; confronto exato do candidato histórico e SPICE; diff dos snapshots RTL; reconciliação dos logs e rejeição estrita confirmada; reanálise C1/C2 em memória. Não executados: novos simuladores, síntese, reconstrução física, DRC/LVS, PVT/Monte Carlo/Liberty. A reanálise de C1/C2 usou NumPy 2.4.6 do host, com os raws identificados por hash; não muda a versão do simulador histórico. Não foi necessário instalar ferramentas.

Somente este documento integra a alteração Git desta etapa. Os seis relatórios anteriores e todos os artefatos de implementação/evidências permanecem na identidade original. Não houve merge, rebase ou alteração de PR. O commit e a branch de publicação identificam esta revisão; sua publicação não concede aceite acadêmico.
