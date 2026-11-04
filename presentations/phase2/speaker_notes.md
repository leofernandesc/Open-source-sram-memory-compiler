# Roteiro de fala — Fase 2

Duração sugerida: 20–25 minutos, ajustável à discussão. Este roteiro não é uma leitura literal dos bullets.


## Slide 1 — Open-Source SRAM Memory Compiler

**Objetivo:** Implementação e auditoria concluídas no escopo experimental; revisão formal pendente.

**Fala sugerida:** Bom dia. Vamos apresentar a integração da Fase 2: partimos das células customizadas da fase anterior e chegamos a uma SRAM 4 por 8 fisicamente conectada. O foco é mostrar como RTL, controle elétrico, layout e verificação se relacionam. A entrega tem fontes, artefatos e evidências rastreáveis. Vou separar o que foi implementado, o que os ensaios comprovam e o que continua sem caracterização.

**Destaque:** Digital Control, Physical Integration and Experimental Validation of a 4×8 SRAM in SKY130

**Ressalva:** Não há afiliação institucional ou nomes de orientadores confirmados nas fontes usadas; esses campos foram omitidos.

**Transição:** Começo pela motivação e pelo tamanho do primeiro protótipo.

**Fontes:** [README.md](../../README.md), [GITFLOW.md](../../GITFLOW.md)


## Slide 2 — Uma ponte entre lógica e silício

**Objetivo:** O protótipo pequeno permite inspecionar a integração completa.

**Fala sugerida:** Uma SRAM customizada depende tanto da bitcell quanto de seleção de linha, bitlines e leitura diferencial. O compilador organiza essas peças de maneira repetível. Começamos com quatro palavras de oito bits, sem multiplexação de colunas, para conseguir analisar cada interface. Isso não significa que já exista geração física para as quatro profundidades previstas. Hoje a vista física entregue é 4 por 8; as maiores têm evidência RTL.

**Destaque:** SRAM customizada: armazenamento e periféricos projetados no nível de transistor.

**Ressalva:** Não atribuir densidade ou eficiência comercial ao floorplan experimental.

**Transição:** A Fase 2 teve dois aceites complementares.

**Fontes:** [specs/technical_specification.md](../../specs/technical_specification.md), [docs/phase2_execution.md](../../docs/phase2_execution.md)


## Slide 3 — Dois marcos, duas evidências

**Objetivo:** Uma SRAM funcional em Verilog não comprova uma SRAM física.

**Fala sugerida:** Separamos os aceites para não confundir níveis de abstração. A frente digital precisa preservar a arquitetura durante a síntese. A frente física precisa conectar as bitcells e os periféricos, verificar a geometria e recuperar dados por circuitos reais. Um núcleo customizado pronto também não basta: o top precisa incluir registradores, controle e barramento. O parecer atual aceita esses resultados dentro do experimento nominal, aguardando revisão da equipe.

**Destaque:** F2-DIG: mapear controle e registradores em SKY130HD e verificar a netlist por GLS.

**Ressalva:** Aprovação experimental é diferente de aprovação formal dos orientadores.

**Transição:** Essa integração reutiliza uma seleção congelada da Fase 1.

**Fontes:** [docs/phase2_review_20261104_acceptance.md](../../docs/phase2_review_20261104_acceptance.md)


## Slide 4 — Seis famílias, 401 MOS customizados

**Objetivo:** As folhas foram preservadas; adaptações de integração ficam fora delas.

**Fala sugerida:** A bitcell armazena o bit; o decoder e o wordline driver selecionam a linha; o precharge prepara o par de bitlines; o write driver aplica dados complementares; e o sense amplifier resolve a leitura. A composição soma 401 MOS. O decoder selecionado já é a revisão de 33 MOS com quatro keepers, não a versão histórica de 29. Preservar o manifesto evita misturar células de campanhas diferentes.

**Destaque:** 32 bitcells 6T · 1 decoder dinâmico de 33 MOS · 4 WL drivers

**Ressalva:** A autoria de cada família segue o histórico; integração não substitui o trabalho anterior.

**Transição:** Agora mostro como essas células se conectam à lógica digital.

**Fontes:** [release/phase1_current.json](../../release/phase1_current.json), [release/phase1_keeper/manifest.json](../../release/phase1_keeper/manifest.json), [docs/phase2_review_20261104.md](../../docs/phase2_review_20261104.md)


## Slide 5 — Arquitetura integrada

**Objetivo:** Uma palavra de oito bits por linha física, sem column mux.

**Fala sugerida:** À esquerda está a interface pública. Na subida do clock capturamos dois bits de endereço, oito dados de escrita e dois pedidos de operação. O controle de fases fica entre esses pedidos e o núcleo. Na saída, oito registradores capturam a leitura na descida e oito buffers tri-state controlam o barramento. As cores distinguem as standard cells dos circuitos customizados. O desenho é explicativo; a conectividade efetiva é verificada no layout extraído.

**Destaque:** Azul: células padrão SKY130HD

**Ressalva:** São 20 FF de controle/captura, e não 32 FF substituindo as bitcells.

**Transição:** Com a fronteira clara, podemos definir o protocolo externo.

**Fontes:** [rtl/sram_4x8_wrapper.v](../../rtl/sram_4x8_wrapper.v), [physical/phase2/macro_binding.v](../../physical/phase2/macro_binding.v)


## Slide 6 — O pedido é capturado; a saída é mascarada

**Objetivo:** Mudar controles vivos pode liberar DATA sem cancelar o acesso capturado.

**Fala sugerida:** Os códigos são apresentados na ordem CSb, OEb e WEb. Só 001 lê e 010 escreve. Depois da captura, o endereço e o dado interno permanecem registrados, mesmo se as entradas externas mudarem. A saída tem uma máscara combinacional adicional: ao retirar leitura viva, liberamos DATA, mas não abortamos a operação interna. Em leituras consecutivas o valor anterior pode continuar visível durante a fase alta. O novo valor pertence à captura na descida.

**Destaque:** 001 → leitura · 010 → escrita · demais combinações → nenhum novo acesso.

**Ressalva:** O mestre deve aguardar a liberação real do driver antes de dirigir DATA; turnaround não está caracterizado.

**Transição:** Essas regras foram implementadas em vistas RTL separadas.

**Fontes:** [specs/sram_4x8_digital.md](../../specs/sram_4x8_digital.md), [rtl/sram_controller.v](../../rtl/sram_controller.v), [rtl/sram_4x8_wrapper.v](../../rtl/sram_4x8_wrapper.v)


## Slide 7 — RTL e fronteira da macro

**Objetivo:** A definição comportamental de armazenamento não entra na fabricação.

**Fala sugerida:** Há uma vista simples do comportamento público e outra estrutural com controlador e wrapper. Na simulação digital, uma macro funcional fornece o armazenamento para exercitar a interface. Na síntese, usamos uma black box com os mesmos pinos. Assim o Yosys mapeia controle, FF e buffers sem converter a matriz em registradores. Depois essa fronteira é ligada ao núcleo físico. Também evitamos uma segunda captura de endereço, que acrescentaria um ciclo indevido.

**Destaque:** sram_model: referência pública parametrizada.

**Ressalva:** Não compilar simultaneamente as definições macro_model e macro_bb.

**Transição:** O comportamento foi comparado com um scoreboard independente.

**Fontes:** [rtl/model.f](../../rtl/model.f), [rtl/wrapper_sim.f](../../rtl/wrapper_sim.f), [rtl/wrapper_synth.f](../../rtl/wrapper_synth.f)


## Slide 8 — Verificação orientada ao protocolo

**Objetivo:** Conteúdo não escrito é desconhecido; mutantes verificam os observadores.

**Fala sugerida:** O scoreboard trabalha com transações e expectativas externas. Foram exercitados todos os endereços, os oito controles e suas transições ordenadas, além de 00, FF, AA, 55 e padrões walking. As alterações de entradas durante a fase alta verificam que usamos os valores capturados. Também há casos negativos deliberados para detectar borda errada e máscara ausente. Os 154 mil checks cobrem vários modelos e asserções por transação; não são 154 mil operações físicas.

**Destaque:** Scoreboard independente; sem reutilizar helpers do DUT.

**Ressalva:** A regressão digital cobre profundidades maiores, sem afirmar layouts correspondentes.

**Transição:** A etapa seguinte verifica se a síntese preservou essa semântica.

**Fontes:** [tb/sram_ref_model.sv](../../tb/sram_ref_model.sv), [reports/digital/phase2_review_20261104/results.json](../../reports/digital/phase2_review_20261104/results.json)


## Slide 9 — Mapeamento real em SKY130HD

**Objetivo:** GLS sem atraso confirma comportamento, não fechamento de timing.

**Fala sugerida:** O mapeamento foi feito com a Liberty da SKY130HD e os modelos de alimentação explícita. O barramento não ficou apenas como construção Verilog: há oito ebufn, com polaridade de enable conferida em um piloto e em um mutante. O wrapper passou nos 15.619 checks. A netlist roteada repetiu a mesma cobertura; não somamos as duas execuções como 31 mil testes exclusivos. Essa GLS usa atraso zero e uma macro funcional, portanto não mede o desempenho completo da SRAM.

**Destaque:** 20 flip-flops · 8 ebufn físicos · 1 macro customizada.

**Ressalva:** Liberty de mapeamento TT/25 °C; ensaio elétrico nominal a 27 °C.

**Transição:** Para verificar o circuito real, precisamos do binding de fases.

**Fontes:** [reports/phase2/review_20261104/digital/results.json](../../reports/phase2/review_20261104/digital/results.json), [reports/phase2/routed_gls/results.json](../../reports/phase2/routed_gls/results.json)


## Slide 10 — Pedidos digitais, fases elétricas

**Objetivo:** Taps 24 / 40 / 60 / 80 são posições em uma cadeia de inversores.

**Fala sugerida:** O núcleo recebe requisições já capturadas. A cadeia de 80 inversores e as portas qualificadoras geram separação entre liberação da pré-carga, escrita, avaliação e sense. PCLK é qualificado por validade e clock; cada DEC também é qualificado antes do driver de wordline. O sense persiste depois da descida o suficiente para a captura local. As posições dos taps não representam nanossegundos e não constituem uma solução qualificada para todos os corners.

**Destaque:** ADDR_Q e DIN_Q estabilizam endereço e escrita.

**Ressalva:** Não há FSM dedicada, replica bitline ou reset acrescentado.

**Transição:** O decoder dinâmico é uma parte essencial dessa sequência.

**Fontes:** [specs/phase2_physical_interface.md](../../specs/phase2_physical_interface.md), [physical/phase2/macro_binding.v](../../physical/phase2/macro_binding.v)


## Slide 11 — Pré-carga, avaliação e retenção

**Objetivo:** 33 MOS oficiais; o decoder RTL permanece somente referência funcional.

**Fala sugerida:** No decoder dinâmico, primeiro carregamos os nós internos. Depois a combinação do endereço abre uma rede de descarga. O inversor desse caminho gera DEC ativo. O keeper de realimentação ajuda a manter alto um nó não selecionado e se desliga quando a saída correspondente sobe após descarga. A implementação usa um footer compartilhado para isolar avaliação. É importante respeitar os pinos por nome: no subcircuito congelado DEC3 aparece antes de DEC2, mas o mapeamento lógico das quatro linhas continua o binário esperado.

**Destaque:** PCLK baixo: PMOS carregam os quatro nós internos.

**Ressalva:** O esquema visual deste slide é explicativo e não substitui o esquemático congelado.

**Transição:** O gerador reproduz essa conectividade ao compor a matriz.

**Fontes:** [specs/technical_specification.md](../../specs/technical_specification.md), [release/phase1_keeper/manifest.json](../../release/phase1_keeper/manifest.json), [docs/phase2_review_20261104.md](../../docs/phase2_review_20261104.md)


## Slide 12 — Composição e verificação independente

**Objetivo:** A mesma configuração reproduziu GDS e SPICE equivalentes.

**Fala sugerida:** O gerador monta a matriz e os periféricos, produz referência e layout e exporta a fronteira física para a integração. Para evitar que o mesmo erro seja repetido no grafo e na geometria, usamos uma conferência independente da extração: cada WL tem 16 gates de acesso, correspondentes a duas portas por bitcell, e cada par BL/BLB corresponde à coluna correta. A reconstrução a partir das fontes produziu o mesmo GDS após normalizar datas e SPICE idêntico inclusive nas junções.

**Destaque:** 4 linhas × 8 colunas; 32 bitcells e 8 pares BL/BLB.

**Ressalva:** O gerador físico entregue está limitado a 4×8; equivalência de artefatos não substitui leitura/escrita elétrica.

**Transição:** O resultado integrado está nesta geometria real.

**Fontes:** [tools/phase2_core.py](../../tools/phase2_core.py), [tools/run_phase2_fabric.py](../../tools/run_phase2_fabric.py), [tools/review_phase2_structure.py](../../tools/review_phase2_structure.py), [reports/phase2/review_20261104/reproduction/results.json](../../reports/phase2/review_20261104/reproduction/results.json)


## Slide 13 — O top-level físico entregue

**Objetivo:** Imagem do GDS real: M4/M5 e footprints das células padrão.

**Fala sugerida:** Esta imagem mostra a geometria realmente entregue, não uma ilustração genérica de chip. O total é de 1.493 MOS. Os 1.092 adicionais incluem 480 MOS dos vinte FF, 328 da lógica de captura e interface, 266 das fases e adaptadores e 18 de três buffers de clock. Taps e fillers ocupam geometria, mas seus modelos usados aqui não acrescentam MOS à contagem. A dimensão do top é um floorplan experimental e não uma macro compacta otimizada.

**Destaque:** 1.493 MOS: 401 customizados + 1.092 SKY130HD.

**Ressalva:** A visualização não comprova DRC ou LVS; essas verificações vêm separadamente.

**Transição:** Primeiro mostro a sequência elétrica efetivamente observada.

**Fontes:** [reports/phase2/layout_overview/results.json](../../reports/phase2/layout_overview/results.json), [physical/phase2/delivery.json](../../physical/phase2/delivery.json), [reports/phase2/review_20261104/structure/results.json](../../reports/phase2/review_20261104/structure/results.json)


## Slide 14 — Da pré-carga à captura

**Objetivo:** TT · 1,8 V · 27 °C · conectividade e junções extraídas, sem wire RC.

**Fala sugerida:** Este é um recorte real contendo escrita e leitura do cenário de partida com dois ciclos inativos. PRECH é ativo baixo; por isso precisamos que suba antes de WE e da wordline. Durante a leitura aparece a separação entre BL e BLB, seguida da regeneração do sense. A captura nos FF tem atraso local em relação à descida externa. As verificações analisaram todas as amostras, inclusive a recuperação, e não apenas o valor final de DATA.

**Destaque:** PRECH libera antes de WE/WL.

**Ressalva:** As curvas não contêm PEX RC detalhado das interconexões.

**Transição:** A separação entre as fases precisou de correções durante o desenvolvimento.

**Fontes:** [reports/phase2/final_polish_20261104/startup_extended/r1_idle2/results.json](../../reports/phase2/final_polish_20261104/startup_extended/r1_idle2/results.json), [reports/phase2/final_polish_20261104/events/results.json](../../reports/phase2/final_polish_20261104/events/results.json)


## Slide 15 — Problemas reais, correções rastreáveis

**Objetivo:** Readback correto, sozinho, não revelava todos os problemas.

**Fala sugerida:** O primeiro exemplo é elétrico: o dado lido estava correto, mas WE começava enquanto a pré-carga ainda não tinha liberado. Corrigimos a qualificação para o tap 40 e preservamos os dois resultados. No roteamento, uma subtração de obstruções deixava um anel de cinco nanômetros fechando o acesso ao pino. Corrigimos a exportação do pad real, sem alterar a célula. Por fim, a importação no Magic precisava carregar vias tecnológicas e vistas físicas de taps e fillers. Isso mostra por que uma saída de ferramenta ou uma única simulação não bastam.

**Destaque:** WE antecipado: guarda −232,897 ps → tap 40 → +167,388 ps no piloto.

**Ressalva:** As guardas citadas são dos pilotos históricos, não limites de PVT da macro final.

**Transição:** As correções foram fechadas com verificações físicas independentes.

**Fontes:** [docs/phase2_execution.md](../../docs/phase2_execution.md), [reports/phase2/phase_guard_review/results.json](../../reports/phase2/phase_guard_review/results.json)


## Slide 16 — Geometria e conectividade verificadas

**Objetivo:** DRC verifica regras geométricas; LVS compara o circuito extraído.

**Fala sugerida:** DRC e LVS respondem perguntas diferentes. DRC verifica regras de construção do layout. LVS compara o circuito que extraímos com a referência, incluindo o controle e os dispositivos reais. A comparação não usa uma black box para esconder o núcleo. Reimportamos o GDS final e repetimos a verificação. Os quatro defeitos deliberados foram rejeitados inclusive quando o Netgen retorna código de processo zero, por isso analisamos o conteúdo do log. A redução de paralelos explica a diferença de contagem sem remover MOS físicos.

**Destaque:** Magic: zero violações no GDS reimportado.

**Ressalva:** Zero DRC no deck público não equivale a signoff de foundry ou confiabilidade de fabricação.

**Transição:** Depois de verificar a geometria, exercitamos o armazenamento real.

**Fontes:** [reports/phase2/final_gds/magic.txt](../../reports/phase2/final_gds/magic.txt), [reports/phase2/final_gds/lvs.txt](../../reports/phase2/final_gds/lvs.txt), [reports/phase2/review_20261104/lvs_negative/results.json](../../reports/phase2/review_20261104/lvs_negative/results.json)


## Slide 17 — Escrever, manter e recuperar

**Objetivo:** Bitcells e sense amplifiers transistor-level; sem armazenamento comportamental.

**Fala sugerida:** A campanha original percorreu os endereços e verificou também o protocolo. A dirigida acrescentou padrões walking e mudanças no endereço e nos dados externos após a captura. O resultado continuou coerente com a requisição registrada. O gráfico complementar ilustra estados internos e leitura externa no circuito real, durante escrita e reescrita complementar. As 1.332 verificações já incluem os 160 bits lidos; não somamos esse subconjunto outra vez. Retenção e preservação são demonstradas nas janelas e padrões ensaiados.

**Destaque:** Campanha original: 128 bits lidos + 392 checks adicionais.

**Ressalva:** A figura é um recorte identificado de um ensaio real de partida; os totais da campanha dirigida vêm do receipt separado.

**Transição:** A temporização precisa distinguir disponibilidade interna de garantia externa.

**Fontes:** [reports/phase2/extracted_access_singlethread/results.json](../../reports/phase2/extracted_access_singlethread/results.json), [reports/phase2/review_20261104/directed/results.json](../../reports/phase2/review_20261104/directed/results.json), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md)


## Slide 18 — Contrato temporal sem números inventados

**Objetivo:** Janelas internas disponíveis não são setup/hold públicos da SRAM.

**Fala sugerida:** Formalizamos o comportamento, mas não preenchemos as lacunas com números arbitrários. SA_OUT e DOUT_RAW são o mesmo nó neste binding; depois há mux, FF e tri-state. As janelas próximas de 7,44 e 7,25 nanossegundos mostram estabilidade disponível antes do clock local. Os dois nanossegundos posteriores são o limite da observação, não hold mínimo. A comparação usa uma referência Liberty de 25 graus contra o ensaio de 27 graus. O clock de 20 nanossegundos é uma condição que funcionou, não a frequência máxima.

**Destaque:** Subida: captura da requisição. Descida: captura da leitura.

**Ressalva:** Setup/hold externo, read-valid, enable/disable, turnaround e mínimo de partida não estão qualificados.

**Transição:** A última rodada também ampliou a partida sem reset.

**Fontes:** [specs/sram_4x8_timing_contract.md](../../specs/sram_4x8_timing_contract.md), [reports/phase2/final_polish_20261104/capture_directed/results.json](../../reports/phase2/final_polish_20261104/capture_directed/results.json)


## Slide 19 — Cinco partidas independentes

**Objetivo:** Zero ciclos inativos ainda incluiu 9 ns de espera após o plateau.

**Fala sugerida:** Cada cenário começou em um processo novo do simulador. Variamos rampa, quantidade de capturas inativas e primeira linha e palavra. A primeira operação foi escrita, seguida de leitura; depois escrevemos as outras linhas e reescrevemos a primeira com o complemento. O auditor conferiu os nós de armazenamento conhecidos, a pré-carga, a seleção e o barramento. Todos os cinco passaram. O caso sem ciclos inativos aguardou nove nanossegundos após o plateau. Mantivemos duas capturas inativas como procedimento de reprodução, sem alegar ganho estatístico ou mínimo universal.

**Destaque:** Rampas 1 / 5 / 10 ns; condicionamento de 0 / 2 / 3 ciclos nas combinações ensaiadas.

**Ressalva:** Cinco cenários direcionados não representam todas as rampas, estados iniciais, brownout ou PVT.

**Transição:** Podemos então consolidar os aceites sem misturar os escopos.

**Fontes:** [reports/phase2/final_polish_20261104/startup_verification/results.json](../../reports/phase2/final_polish_20261104/startup_verification/results.json), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md)


## Slide 20 — Resultados consolidados

**Objetivo:** Desenvolvimento concluído no escopo experimental; revisão formal pendente.

**Fala sugerida:** O resultado principal é a convergência das representações: o controle mapeado corresponde ao protocolo; o layout corresponde ao circuito; e o circuito recupera os dados nos ensaios reais. Mantemos os aceites separados, com a configuração e as condições explícitas. Os arquivos podem ser revisados pelo manifesto e pelo guia de reprodução. O pacote também preserva tentativas e correções históricas para não transformar tudo em uma sequência de PASS sem explicação.

**Destaque:** F2-DIG: síntese/GLS funcional aprovada.

**Ressalva:** O parecer técnico não substitui a deliberação dos integrantes e orientadores.

**Transição:** As limitações delimitam o que o projeto ainda não está afirmando.

**Fontes:** [docs/phase2_review_20261104_acceptance.md](../../docs/phase2_review_20261104_acceptance.md), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md), [physical/phase2/delivery.json](../../physical/phase2/delivery.json)


## Slide 21 — Limites reconhecidos

**Objetivo:** Conhecer o limite da evidência faz parte da conclusão técnica.

**Fala sugerida:** Esses pontos são limites do trabalho realizado e não defeitos automaticamente atribuídos ao circuito. O protótipo funciona no ponto TT, 1,8 volts e 27 graus, com interconexões sem RC detalhado. Ainda não medimos frequência máxima, pior caso externo ou variabilidade estatística. A limitação de cobertura de modelos da Fase 1 também continua registrada. Apontamos essas fronteiras sem iniciar agora a próxima fase.

**Destaque:** Fmax e temporização externa completa ainda não caracterizados.

**Ressalva:** Não confundir o nominal experimental com robustez de fabricação.

**Transição:** Fecho com a contribuição concreta desta fase.

**Fontes:** [specs/sram_4x8_timing_contract.md](../../specs/sram_4x8_timing_contract.md), [docs/phase2_review_20261104_acceptance.md](../../docs/phase2_review_20261104_acceptance.md)


## Slide 22 — Da célula ao sistema SRAM

**Objetivo:** Fase 2 tecnicamente concluída no escopo experimental. Fechamento acadêmico depende da equipe e dos orientadores.

**Fala sugerida:** A Fase 2 transformou células individuais em uma SRAM 4 por 8 integrada, com controle digital mapeado, vistas físicas e leitura e escrita demonstradas. Conseguimos reproduzir a geometria e fortalecer a auditoria, sem esconder os problemas encontrados ou extrapolar o alcance do experimento. A entrega está pronta para revisão técnica. Gostaria de discutir com vocês a aceitação desse escopo e os parâmetros que precisam ser definidos antes de qualquer caracterização posterior. Obrigado.

**Destaque:** Controle digital sintetizado e células customizadas integrados.

**Ressalva:** Sem aprovação formal atribuída antecipadamente aos orientadores.

**Fontes:** [docs/phase2_reproduction_guide.md](../../docs/phase2_reproduction_guide.md), [docs/phase2_final_polish.md](../../docs/phase2_final_polish.md)

