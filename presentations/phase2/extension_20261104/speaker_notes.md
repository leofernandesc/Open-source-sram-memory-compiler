# Roteiro de fala — revisão complementar da Fase 2

## Slide 1 — Open-Source SRAM Memory Compiler

Objetivo: Implementação e auditoria concluídas no escopo experimental; revisão formal pendente.

Bom dia. Vamos apresentar a integração da Fase 2: partimos das células customizadas da fase anterior e chegamos a uma SRAM 4 por 8 fisicamente conectada. O foco é mostrar como RTL, controle elétrico, layout e verificação se relacionam. A entrega tem fontes, artefatos e evidências rastreáveis. Vou separar o que foi implementado, o que os ensaios comprovam e o que continua sem caracterização.

Ressalva: Não há afiliação institucional ou nomes de orientadores confirmados nas fontes usadas; esses campos foram omitidos.

Transição: Começo pela motivação e pelo tamanho do primeiro protótipo.

Fontes: [README.md](../../../README.md); [GITFLOW.md](../../../GITFLOW.md).

## Slide 2 — Contexto e escopo do projeto

Objetivo: A implementação física desta entrega está limitada a quatro palavras de oito bits.

Uma SRAM customizada depende tanto da bitcell quanto de seleção de linha, bitlines e leitura diferencial. O compilador organiza essas peças de maneira repetível. Começamos com quatro palavras de oito bits, sem multiplexação de colunas, para conseguir analisar cada interface. Isso não significa que já exista geração física para as quatro profundidades previstas. Hoje a vista física entregue é 4 por 8; as maiores têm evidência RTL.

Ressalva: Não atribuir densidade ou eficiência comercial ao floorplan experimental.

Transição: A Fase 2 teve dois aceites complementares.

Fontes: [technical_specification.md](../../../specs/technical_specification.md); [phase2_execution.md](../../../docs/phase2_execution.md).

## Slide 3 — Critérios de entrega da Fase 2

Objetivo: F2-DIG verifica mapeamento e comportamento; F2-FIS verifica integração e acesso elétrico.

Separamos os aceites para não confundir níveis de abstração. A frente digital precisa preservar a arquitetura durante a síntese. A frente física precisa conectar as bitcells e os periféricos, verificar a geometria e recuperar dados por circuitos reais. Um núcleo customizado pronto também não basta: o top precisa incluir registradores, controle e barramento. O parecer atual aceita esses resultados dentro do experimento nominal, aguardando revisão da equipe.

Ressalva: Aprovação experimental é diferente de aprovação formal dos orientadores.

Transição: Essa integração reutiliza uma seleção congelada da Fase 1.

Fontes: [phase2_review_20261104_acceptance.md](../../../docs/phase2_review_20261104_acceptance.md).

## Slide 4 — Células selecionadas na Fase 1

Objetivo: O manifesto da Fase 1 seleciona as seis famílias e seus artefatos congelados.

A bitcell armazena o bit; o decoder e o wordline driver selecionam a linha; o precharge prepara o par de bitlines; o write driver aplica dados complementares; e o sense amplifier resolve a leitura. A composição soma 401 MOS. O decoder selecionado já é a revisão de 33 MOS com quatro keepers, não a versão histórica de 29. Preservar o manifesto evita misturar células de campanhas diferentes.

Ressalva: A autoria de cada família segue o histórico; integração não substitui o trabalho anterior.

Transição: Agora mostro como essas células se conectam à lógica digital.

Fontes: [phase1_current.json](../../../release/phase1_current.json); [manifest.json](../../../release/phase1_keeper/manifest.json); [phase2_review_20261104.md](../../../docs/phase2_review_20261104.md).

## Slide 5 — Arquitetura da SRAM 4×8

Objetivo: Organização física: quatro linhas de oito bits, sem multiplexação de colunas.

À esquerda está a interface pública. Na subida do clock capturamos dois bits de endereço, oito dados de escrita e dois pedidos de operação. O controle de fases fica entre esses pedidos e o núcleo. Na saída, oito registradores capturam a leitura na descida e oito buffers tri-state controlam o barramento. As cores distinguem as standard cells dos circuitos customizados. O desenho é explicativo; a conectividade efetiva é verificada no layout extraído.

Ressalva: São 20 FF de controle/captura, e não 32 FF substituindo as bitcells.

Transição: Com a fronteira clara, podemos definir o protocolo externo.

Fontes: [sram_4x8_wrapper.v](../../../rtl/sram_4x8_wrapper.v); [macro_binding.v](../../../physical/phase2/macro_binding.v).

## Slide 6 — Protocolo de leitura e escrita

Objetivo: Mudar controles vivos pode liberar DATA sem cancelar o acesso capturado.

Os códigos são apresentados na ordem CSb, OEb e WEb. Só 001 lê e 010 escreve. Depois da captura, o endereço e o dado interno permanecem registrados, mesmo se as entradas externas mudarem. A saída tem uma máscara combinacional adicional: ao retirar leitura viva, liberamos DATA, mas não abortamos a operação interna. Em leituras consecutivas o valor anterior pode continuar visível durante a fase alta. O novo valor pertence à captura na descida.

Ressalva: O mestre deve aguardar a liberação real do driver antes de dirigir DATA; turnaround não está caracterizado.

Transição: Essas regras foram implementadas em vistas RTL separadas.

Fontes: [sram_4x8_digital.md](../../../specs/sram_4x8_digital.md); [sram_controller.v](../../../rtl/sram_controller.v); [sram_4x8_wrapper.v](../../../rtl/sram_4x8_wrapper.v).

## Slide 7 — Hierarquia RTL

Objetivo: A síntese preserva a fronteira da macro customizada.

Há uma vista simples do comportamento público e outra estrutural com controlador e wrapper. Na simulação digital, uma macro funcional fornece o armazenamento para exercitar a interface. Na síntese, usamos uma black box com os mesmos pinos. Assim o Yosys mapeia controle, FF e buffers sem converter a matriz em registradores. Depois essa fronteira é ligada ao núcleo físico. Também evitamos uma segunda captura de endereço, que acrescentaria um ciclo indevido.

Ressalva: Não compilar simultaneamente as definições macro_model e macro_bb.

Transição: O comportamento foi comparado com um scoreboard independente.

Fontes: [model.f](../../../rtl/model.f); [wrapper_sim.f](../../../rtl/wrapper_sim.f); [wrapper_synth.f](../../../rtl/wrapper_synth.f).

## Slide 8 — Cobertura da verificação digital

Objetivo: Conteúdo não escrito é desconhecido; mutantes verificam os observadores.

O scoreboard trabalha com transações e expectativas externas. Foram exercitados todos os endereços, os oito controles e suas transições ordenadas, além de 00, FF, AA, 55 e padrões walking. As alterações de entradas durante a fase alta verificam que usamos os valores capturados. Também há casos negativos deliberados para detectar borda errada e máscara ausente. Os 154 mil checks cobrem vários modelos e asserções por transação; não são 154 mil operações físicas.

Ressalva: A regressão digital cobre profundidades maiores, sem afirmar layouts correspondentes.

Transição: A etapa seguinte verifica se a síntese preservou essa semântica.

Fontes: [sram_ref_model.sv](../../../tb/sram_ref_model.sv); [results.json](../../../reports/digital/phase2_review_20261104/results.json).

## Slide 9 — Síntese e GLS em SKY130HD

Objetivo: GLS sem atraso confirma comportamento, não fechamento de timing.

O mapeamento foi feito com a Liberty da SKY130HD e os modelos de alimentação explícita. O barramento não ficou apenas como construção Verilog: há oito ebufn, com polaridade de enable conferida em um piloto e em um mutante. O wrapper passou nos 15.619 checks. A netlist roteada repetiu a mesma cobertura; não somamos as duas execuções como 31 mil testes exclusivos. Essa GLS usa atraso zero e uma macro funcional, portanto não mede o desempenho completo da SRAM.

Ressalva: Liberty de mapeamento TT/25 °C; ensaio elétrico nominal a 27 °C.

Transição: Para verificar o circuito real, precisamos do binding de fases.

Fontes: [results.json](../../../reports/phase2/review_20261104/digital/results.json); [results.json](../../../reports/phase2/routed_gls/results.json).

## Slide 10 — Interface entre controle e núcleo

Objetivo: Taps 24 / 40 / 60 / 80 são posições em uma cadeia de inversores.

O núcleo recebe requisições já capturadas. A cadeia de 80 inversores e as portas qualificadoras geram separação entre liberação da pré-carga, escrita, avaliação e sense. PCLK é qualificado por validade e clock; cada DEC também é qualificado antes do driver de wordline. O sense persiste depois da descida o suficiente para a captura local. As posições dos taps não representam nanossegundos e não constituem uma solução qualificada para todos os corners.

Ressalva: Não há FSM dedicada, replica bitline ou reset acrescentado.

Transição: O decoder dinâmico é uma parte essencial dessa sequência.

Fontes: [phase2_physical_interface.md](../../../specs/phase2_physical_interface.md); [macro_binding.v](../../../physical/phase2/macro_binding.v).

## Slide 11 — Decoder dinâmico e seleção de linha

Objetivo: 33 MOS oficiais; o decoder RTL permanece somente referência funcional.

No decoder dinâmico, primeiro carregamos os nós internos. Depois a combinação do endereço abre uma rede de descarga. O inversor desse caminho gera DEC ativo. O keeper de realimentação ajuda a manter alto um nó não selecionado e se desliga quando a saída correspondente sobe após descarga. A implementação usa um footer compartilhado para isolar avaliação. É importante respeitar os pinos por nome: no subcircuito congelado DEC3 aparece antes de DEC2, mas o mapeamento lógico das quatro linhas continua o binário esperado.

Ressalva: O esquema visual deste slide é explicativo e não substitui o esquemático congelado.

Transição: O gerador reproduz essa conectividade ao compor a matriz.

Fontes: [technical_specification.md](../../../specs/technical_specification.md); [manifest.json](../../../release/phase1_keeper/manifest.json); [phase2_review_20261104.md](../../../docs/phase2_review_20261104.md).

## Slide 12 — Geração da matriz e integração física

Objetivo: A mesma configuração reproduziu GDS e SPICE equivalentes.

O gerador monta a matriz e os periféricos, produz referência e layout e exporta a fronteira física para a integração. Para evitar que o mesmo erro seja repetido no grafo e na geometria, usamos uma conferência independente da extração: cada WL tem 16 gates de acesso, correspondentes a duas portas por bitcell, e cada par BL/BLB corresponde à coluna correta. A reconstrução a partir das fontes produziu o mesmo GDS após normalizar datas e SPICE idêntico inclusive nas junções.

Ressalva: O gerador físico entregue está limitado a 4×8; equivalência de artefatos não substitui leitura/escrita elétrica.

Transição: O resultado integrado está nesta geometria real.

Fontes: [phase2_core.py](../../../tools/phase2_core.py); [run_phase2_fabric.py](../../../tools/run_phase2_fabric.py); [review_phase2_structure.py](../../../tools/review_phase2_structure.py); [results.json](../../../reports/phase2/review_20261104/reproduction/results.json).

## Slide 13 — Layout integrado da SRAM 4×8

Objetivo: Imagem do GDS real: M4/M5 e footprints das células padrão.

Esta imagem mostra a geometria realmente entregue, não uma ilustração genérica de chip. O total é de 1.493 MOS. Os 1.092 adicionais incluem 480 MOS dos vinte FF, 328 da lógica de captura e interface, 266 das fases e adaptadores e 18 de três buffers de clock. Taps e fillers ocupam geometria, mas seus modelos usados aqui não acrescentam MOS à contagem. A dimensão do top é um floorplan experimental e não uma macro compacta otimizada.

Ressalva: A visualização não comprova DRC ou LVS; essas verificações vêm separadamente.

Transição: Primeiro mostro a sequência elétrica efetivamente observada.

Fontes: [results.json](../../../reports/phase2/layout_overview/results.json); [delivery.json](../../../physical/phase2/delivery.json); [results.json](../../../reports/phase2/review_20261104/structure/results.json).

## Slide 14 — Sequenciamento elétrico de acesso

Objetivo: TT · 1,8 V · 27 °C · conectividade e junções extraídas, sem wire RC.

Este recorte é da leitura da linha 1 na campanha nova de barramento, depois de a saída ter registrado AA. A nova palavra é 55. A wordline ativa desenvolve o diferencial e SCLK inicia a regeneração. RAW e a entrada do FF já ficam disponíveis durante a fase alta, mas FF_Q e DATA mantêm o resultado anterior até a captura na descida. O clock local chega cerca de 0,23 a 0,25 nanossegundo depois da descida pública. Nos bits que mudaram, o novo DATA ficou válido cerca de 0,49 a 0,55 nanossegundo depois dessa descida. São medidas da bancada nominal, sem carga externa caracterizada.

Ressalva: Fonte C2, ciclo 7; TT, sem wire RC. A validade de DATA é distinta da habilitação do driver.

Transição: A separação entre as fases precisou de correções durante o desenvolvimento.

Fontes: [phase2_timing_extension.md](../../../docs/phase2_timing_extension.md); [results.json](../../../reports/phase2/extension_20261104/c2_bus/results.json).

## Slide 15 — Problemas encontrados e correções

Objetivo: Readback correto, sozinho, não revelava todos os problemas.

O primeiro exemplo é elétrico: o dado lido estava correto, mas WE começava enquanto a pré-carga ainda não tinha liberado. Corrigimos a qualificação para o tap 40 e preservamos os dois resultados. No roteamento, uma subtração de obstruções deixava um anel de cinco nanômetros fechando o acesso ao pino. Corrigimos a exportação do pad real, sem alterar a célula. Por fim, a importação no Magic precisava carregar vias tecnológicas e vistas físicas de taps e fillers. Isso mostra por que uma saída de ferramenta ou uma única simulação não bastam. No top final e nas sequências adicionais, a guarda entre liberação da pré-carga e escrita ficou em torno de 212 ps. Esses resultados usam circuitos e estímulos distintos dos dois pilotos da figura.

Ressalva: As guardas citadas são dos pilotos históricos, não limites de PVT da macro final.

Transição: As correções foram fechadas com verificações físicas independentes.

Fontes: [phase2_execution.md](../../../docs/phase2_execution.md); [results.json](../../../reports/phase2/phase_guard_review/results.json); [phase2_timing_extension.md](../../../docs/phase2_timing_extension.md).

## Slide 16 — Verificação física: DRC e LVS

Objetivo: DRC verifica regras geométricas; LVS compara o circuito extraído.

DRC e LVS respondem perguntas diferentes. DRC verifica regras de construção do layout. LVS compara o circuito que extraímos com a referência, incluindo o controle e os dispositivos reais. A comparação não usa uma black box para esconder o núcleo. Reimportamos o GDS final e repetimos a verificação. Os quatro defeitos deliberados foram rejeitados inclusive quando o Netgen retorna código de processo zero, por isso analisamos o conteúdo do log. A redução de paralelos explica a diferença de contagem sem remover MOS físicos.

Ressalva: Zero DRC no deck público não equivale a signoff de foundry ou confiabilidade de fabricação.

Transição: Depois de verificar a geometria, exercitamos o armazenamento real.

Fontes: [magic.txt](../../../reports/phase2/final_gds/magic.txt); [lvs.txt](../../../reports/phase2/final_gds/lvs.txt); [results.json](../../../reports/phase2/review_20261104/lvs_negative/results.json).

## Slide 17 — Simulação elétrica de leitura e escrita

Objetivo: Bitcells e sense amplifiers transistor-level; sem armazenamento comportamental.

A campanha anterior cobria walking-one e walking-zero. A auditoria dos estímulos mostrou duas lacunas mais específicas: leituras consecutivas da mesma linha e escritas complementares adjacentes nela. C1 passou nesses casos, verificando também as outras palavras conhecidas. O gráfico mostra a troca dos nós de armazenamento e a saída registrada. C2 acrescentou observação de corrente na liberação e reativação do barramento. Os 1.150 e 1.281 checks já incluem 72 e 48 bits lidos, respectivamente. O piloto é subconjunto e não aumenta cobertura exclusiva. Também conferimos pré-carga e estabilidade nos mesmos transientes; não são outras transações.

Ressalva: Gráfico C1, 128..288 ns; ambos os novos testes utilizam o mesmo DUT físico e TT nominal.

Transição: A temporização precisa distinguir disponibilidade interna de garantia externa.

Fontes: [phase2_coverage_extension.md](../../../docs/phase2_coverage_extension.md); [results.json](../../../reports/phase2/extension_20261104/c1_sequences/results.json).

## Slide 18 — Contrato temporal e barramento

Objetivo: Janelas internas disponíveis não são setup/hold públicos da SRAM.

O contrato mantém subida para capturar a requisição e descida para capturar leitura. Nesta figura, depois da leitura, aplicamos um probe de um quilo-ohm contra o valor de saída. É uma calibração externa para observar se o driver conduz; DATA não precisa ser nível lógico válido enquanto essa carga oposta está ligada. Ao retirar a leitura viva por CSb, a corrente cai e DATA acompanha o probe, enquanto FF_Q permanece constante. Quando restauramos CSb, volta a existir corrente. Após retirar o probe, o dado normal é recuperado. O atraso indicado usa um piso de cinquenta microampères, não uma especificação de leakage ou de turnaround. Na troca para o mestre forte, as guardas ensaiadas de 0,3 e 0,6 nanossegundo não apresentaram sobreposição detectada. Não são guardas mínimas garantidas.

Ressalva: tDIS/tEN no slide abreviam cruzamentos nominais de corrente sob o probe declarado; não são limites públicos qualificados.

Transição: A partida continua apoiada nos cinco cenários já publicados.

Fontes: [phase2_timing_extension.md](../../../docs/phase2_timing_extension.md); [sram_4x8_timing_contract.md](../../../specs/sram_4x8_timing_contract.md).

## Slide 19 — Ensaios de partida sem reset

Objetivo: Zero ciclos inativos ainda incluiu 9 ns de espera após o plateau.

Cada cenário começou em um processo novo do simulador. Variamos rampa, quantidade de capturas inativas e primeira linha e palavra. A primeira operação foi escrita, seguida de leitura; depois escrevemos as outras linhas e reescrevemos a primeira com o complemento. O auditor conferiu os nós de armazenamento conhecidos, a pré-carga, a seleção e o barramento. Todos os cinco passaram. O caso sem ciclos inativos aguardou nove nanossegundos após o plateau. Mantivemos duas capturas inativas como procedimento de reprodução, sem alegar ganho estatístico ou mínimo universal.

Ressalva: Cinco cenários direcionados não representam todas as rampas, estados iniciais, brownout ou PVT.

Transição: Podemos então consolidar os aceites sem misturar os escopos.

Fontes: [results.json](../../../reports/phase2/final_polish_20261104/startup_verification/results.json); [phase2_final_polish.md](../../../docs/phase2_final_polish.md).

## Slide 20 — Quadro de resultados

Objetivo: F2-DIG funcional e F2-FIS nominal concluídos; aceite formal pendente.

A síntese e a GLS verificaram o controle mapeado. O LVS comparou o layout ao circuito, e as simulações transistor-level verificaram os acessos no ponto nominal. Mantemos os aceites separados, com a configuração e as condições explícitas. Os arquivos podem ser revisados pelo manifesto e pelo guia de reprodução. As tentativas e correções históricas permanecem identificadas nos relatórios. A rodada adicional não alterou circuito ou layout. A revisão dos dados também foi reproduzida num worktree limpo, usando o pacote opcional de transientes. Essa reprodução é da análise: não foi outra execução de SPICE.

Ressalva: O parecer técnico não substitui a deliberação dos integrantes e orientadores.

Transição: As limitações delimitam o que o projeto ainda não está afirmando.

Fontes: [phase2_review_20261104_acceptance.md](../../../docs/phase2_review_20261104_acceptance.md); [phase2_final_polish.md](../../../docs/phase2_final_polish.md); [delivery.json](../../../physical/phase2/delivery.json); [phase2_extension_state_20261104.md](../../../docs/phase2_extension_state_20261104.md).

## Slide 21 — Limitações da validação

Objetivo: A caracterização completa não faz parte do aceite experimental desta entrega.

Esses pontos são limites do trabalho realizado e não defeitos automaticamente atribuídos ao circuito. O protótipo funciona no ponto TT, 1,8 volts e 27 graus, com interconexões sem RC detalhado. Ainda não medimos frequência máxima, pior caso externo ou variabilidade estatística. A limitação de cobertura de modelos da Fase 1 também continua registrada. Apontamos essas fronteiras sem iniciar agora a próxima fase. As medições novas de DATA e corrente continuam nominais, sem transformar os parâmetros públicos pendentes em garantias.

Ressalva: Não confundir o nominal experimental com robustez de fabricação.

Transição: Fecho com a contribuição concreta desta fase.

Fontes: [sram_4x8_timing_contract.md](../../../specs/sram_4x8_timing_contract.md); [phase2_review_20261104_acceptance.md](../../../docs/phase2_review_20261104_acceptance.md).

## Slide 22 — Conclusão da Fase 2

Objetivo: Fase 2 tecnicamente concluída no escopo experimental. Fechamento acadêmico depende da equipe e dos orientadores.

A Fase 2 transformou células individuais em uma SRAM 4 por 8 integrada, com controle digital mapeado, vistas físicas e leitura e escrita demonstradas. A reconstrução reproduziu a geometria e o circuito extraído; os relatórios registram as correções e o alcance dos ensaios. A entrega está pronta para revisão técnica. Gostaria de discutir com vocês a aceitação desse escopo e os parâmetros que precisam ser definidos antes de qualquer caracterização posterior. Obrigado.

Ressalva: Sem aprovação formal atribuída antecipadamente aos orientadores.

Transição:

Fontes: [phase2_reproduction_guide.md](../../../docs/phase2_reproduction_guide.md); [phase2_final_polish.md](../../../docs/phase2_final_polish.md).
