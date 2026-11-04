"""Editable slide narrative; generates slides.json and Portuguese speaker notes."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
slides=[]
def add(title,kicker,kind,bullets,takeaway,source,speech,caveat='',transition=''):
 slides.append(dict(title=title,kicker=kicker,kind=kind,bullets=bullets,takeaway=takeaway,source=source,speech=speech,caveat=caveat,transition=transition))
add('Open-Source SRAM\nMemory Compiler','PHASE 2 · TECHNICAL REVIEW','cover',
 ['Digital Control, Physical Integration and Experimental Validation of a 4×8 SRAM in SKY130','Equipe: Danilo · André · Leonardo'],
 'Implementação e auditoria concluídas no escopo experimental; revisão formal pendente.',
 ['README.md','GITFLOW.md'],
 'Bom dia. Vamos apresentar a integração da Fase 2: partimos das células customizadas da fase anterior e chegamos a uma SRAM 4 por 8 fisicamente conectada. O foco é mostrar como RTL, controle elétrico, layout e verificação se relacionam. A entrega tem fontes, artefatos e evidências rastreáveis. Vou separar o que foi implementado, o que os ensaios comprovam e o que continua sem caracterização.',
 'Não há afiliação institucional ou nomes de orientadores confirmados nas fontes usadas; esses campos foram omitidos.', 'Começo pela motivação e pelo tamanho do primeiro protótipo.')
add('Contexto e escopo do projeto','CONTEXTO','cards',
 ['SRAM customizada: armazenamento e periféricos projetados no nível de transistor.','Compilador: composição repetível das células e geração de vistas físicas.','4×8: primeiro alvo físico; RTL já exercita 4, 8, 16 e 32 palavras.'],
 'A implementação física desta entrega está limitada a quatro palavras de oito bits.', ['specs/technical_specification.md','docs/phase2_execution.md'],
 'Uma SRAM customizada depende tanto da bitcell quanto de seleção de linha, bitlines e leitura diferencial. O compilador organiza essas peças de maneira repetível. Começamos com quatro palavras de oito bits, sem multiplexação de colunas, para conseguir analisar cada interface. Isso não significa que já exista geração física para as quatro profundidades previstas. Hoje a vista física entregue é 4 por 8; as maiores têm evidência RTL.',
 'Não atribuir densidade ou eficiência comercial ao floorplan experimental.', 'A Fase 2 teve dois aceites complementares.')
add('Critérios de entrega da Fase 2','OBJETIVO DA FASE 2','gates',
 ['F2-DIG: mapear controle e registradores em SKY130HD e verificar a netlist por GLS.','F2-FIS: conectar células reais, gerar o GDS e demonstrar acesso elétrico com DRC/LVS.'],
 'F2-DIG verifica mapeamento e comportamento; F2-FIS verifica integração e acesso elétrico.', ['docs/phase2_review_20261104_acceptance.md'],
 'Separamos os aceites para não confundir níveis de abstração. A frente digital precisa preservar a arquitetura durante a síntese. A frente física precisa conectar as bitcells e os periféricos, verificar a geometria e recuperar dados por circuitos reais. Um núcleo customizado pronto também não basta: o top precisa incluir registradores, controle e barramento. O parecer atual aceita esses resultados dentro do experimento nominal, aguardando revisão da equipe.',
 'Aprovação experimental é diferente de aprovação formal dos orientadores.', 'Essa integração reutiliza uma seleção congelada da Fase 1.')
add('Células selecionadas na Fase 1','HERANÇA DA FASE 1','leaves',
 ['32 bitcells 6T · 1 decoder dinâmico de 33 MOS · 4 WL drivers','8 precharge · 8 write drivers · 8 sense amplifiers','Seleção congelada: release/phase1_current.json'],
 'O manifesto da Fase 1 seleciona as seis famílias e seus artefatos congelados.', ['release/phase1_current.json','release/phase1_keeper/manifest.json','docs/phase2_review_20261104.md'],
 'A bitcell armazena o bit; o decoder e o wordline driver selecionam a linha; o precharge prepara o par de bitlines; o write driver aplica dados complementares; e o sense amplifier resolve a leitura. A composição soma 401 MOS. O decoder selecionado já é a revisão de 33 MOS com quatro keepers, não a versão histórica de 29. Preservar o manifesto evita misturar células de campanhas diferentes.',
 'A autoria de cada família segue o histórico; integração não substitui o trabalho anterior.', 'Agora mostro como essas células se conectam à lógica digital.')
add('Arquitetura da SRAM 4×8','SRAM SÍNCRONA 1RW','architecture',
 ['Azul: células padrão SKY130HD','Verde: seis famílias customizadas','12 FF de requisição + 8 FF de leitura; DATA bidirecional.'],
 'Organização física: quatro linhas de oito bits, sem multiplexação de colunas.', ['rtl/sram_4x8_wrapper.v','physical/phase2/macro_binding.v'],
 'À esquerda está a interface pública. Na subida do clock capturamos dois bits de endereço, oito dados de escrita e dois pedidos de operação. O controle de fases fica entre esses pedidos e o núcleo. Na saída, oito registradores capturam a leitura na descida e oito buffers tri-state controlam o barramento. As cores distinguem as standard cells dos circuitos customizados. O desenho é explicativo; a conectividade efetiva é verificada no layout extraído.',
 'São 20 FF de controle/captura, e não 32 FF substituindo as bitcells.', 'Com a fronteira clara, podemos definir o protocolo externo.')
add('Protocolo de leitura e escrita','PROTOCOLO','protocol',
 ['001 → leitura · 010 → escrita · demais combinações → nenhum novo acesso.','Subida: captura de ADDR, operação e DATA de escrita.','Descida: captura de leitura; o registro retém o último resultado.','DATA habilitado somente com READ_Q e controles vivos de leitura.'],
 'Mudar controles vivos pode liberar DATA sem cancelar o acesso capturado.', ['specs/sram_4x8_digital.md','rtl/sram_controller.v','rtl/sram_4x8_wrapper.v'],
 'Os códigos são apresentados na ordem CSb, OEb e WEb. Só 001 lê e 010 escreve. Depois da captura, o endereço e o dado interno permanecem registrados, mesmo se as entradas externas mudarem. A saída tem uma máscara combinacional adicional: ao retirar leitura viva, liberamos DATA, mas não abortamos a operação interna. Em leituras consecutivas o valor anterior pode continuar visível durante a fase alta. O novo valor pertence à captura na descida.',
 'O mestre deve aguardar a liberação real do driver antes de dirigir DATA; turnaround não está caracterizado.', 'Essas regras foram implementadas em vistas RTL separadas.')
add('Hierarquia RTL','IMPLEMENTAÇÃO DIGITAL','hierarchy',
 ['sram_model: referência pública parametrizada.','sram_controller + wrapper: captura e interface 4×8.','macro_model: substituto funcional para simulação.','macro_bb: núcleo preservado como black box na síntese.'],
 'A síntese preserva a fronteira da macro customizada.', ['rtl/model.f','rtl/wrapper_sim.f','rtl/wrapper_synth.f'],
 'Há uma vista simples do comportamento público e outra estrutural com controlador e wrapper. Na simulação digital, uma macro funcional fornece o armazenamento para exercitar a interface. Na síntese, usamos uma black box com os mesmos pinos. Assim o Yosys mapeia controle, FF e buffers sem converter a matriz em registradores. Depois essa fronteira é ligada ao núcleo físico. Também evitamos uma segunda captura de endereço, que acrescentaria um ciclo indevido.',
 'Não compilar simultaneamente as definições macro_model e macro_bb.', 'O comportamento foi comparado com um scoreboard independente.')
add('Cobertura da verificação digital','DESIGN VERIFICATION','digital_checks',
 ['Scoreboard independente; sem reutilizar helpers do DUT.','Todos os endereços, 8 controles, 64 transições e padrões dirigidos.','2.048 operações pseudoaleatórias por regressão de memória.','154.303 checks RTL na campanha completa.'],
 'Conteúdo não escrito é desconhecido; mutantes verificam os observadores.', ['tb/sram_ref_model.sv','reports/digital/phase2_review_20261104/results.json'],
 'O scoreboard trabalha com transações e expectativas externas. Foram exercitados todos os endereços, os oito controles e suas transições ordenadas, além de 00, FF, AA, 55 e padrões walking. As alterações de entradas durante a fase alta verificam que usamos os valores capturados. Também há casos negativos deliberados para detectar borda errada e máscara ausente. Os 154 mil checks cobrem vários modelos e asserções por transação; não são 154 mil operações físicas.',
 'A regressão digital cobre profundidades maiores, sem afirmar layouts correspondentes.', 'A etapa seguinte verifica se a síntese preservou essa semântica.')
add('Síntese e GLS em SKY130HD','SÍNTESE E GLS','synthesis',
 ['20 flip-flops · 8 ebufn físicos · 1 macro customizada.','Sem latches inesperados ou armazenamento convertido em FF.','Piloto tri-state validou 0, 1 e Z.','15.619 checks GLS aprovados.'],
 'GLS sem atraso confirma comportamento, não fechamento de timing.', ['reports/phase2/review_20261104/digital/results.json','reports/phase2/routed_gls/results.json'],
 'O mapeamento foi feito com a Liberty da SKY130HD e os modelos de alimentação explícita. O barramento não ficou apenas como construção Verilog: há oito ebufn, com polaridade de enable conferida em um piloto e em um mutante. O wrapper passou nos 15.619 checks. A netlist roteada repetiu a mesma cobertura; não somamos as duas execuções como 31 mil testes exclusivos. Essa GLS usa atraso zero e uma macro funcional, portanto não mede o desempenho completo da SRAM.',
 'Liberty de mapeamento TT/25 °C; ensaio elétrico nominal a 27 °C.', 'Para verificar o circuito real, precisamos do binding de fases.')
add('Interface entre controle e núcleo','INTERFACE DIGITAL–FÍSICA','binding',
 ['ADDR_Q e DIN_Q estabilizam endereço e escrita.','READ_Q / WRITE_Q são pedidos, não pulsos diretos.','PCLK, PRECH, WE e SCLK coordenam acesso e recuperação.','DOUT_RAW alimenta o mux e o FF de saída.'],
 'Taps 24 / 40 / 60 / 80 são posições em uma cadeia de inversores.', ['specs/phase2_physical_interface.md','physical/phase2/macro_binding.v'],
 'O núcleo recebe requisições já capturadas. A cadeia de 80 inversores e as portas qualificadoras geram separação entre liberação da pré-carga, escrita, avaliação e sense. PCLK é qualificado por validade e clock; cada DEC também é qualificado antes do driver de wordline. O sense persiste depois da descida o suficiente para a captura local. As posições dos taps não representam nanossegundos e não constituem uma solução qualificada para todos os corners.',
 'Não há FSM dedicada, replica bitline ou reset acrescentado.', 'O decoder dinâmico é uma parte essencial dessa sequência.')
add('Decoder dinâmico e seleção de linha','DECODER DINÂMICO','decoder',
 ['PCLK baixo: PMOS carregam os quatro nós internos.','PCLK alto: o endereço capturado descarrega apenas o caminho selecionado.','Quatro keepers restauram os nós não selecionados.','DEC qualificado → WL driver → linha física.'],
 '33 MOS oficiais; o decoder RTL permanece somente referência funcional.', ['specs/technical_specification.md','release/phase1_keeper/manifest.json','docs/phase2_review_20261104.md'],
 'No decoder dinâmico, primeiro carregamos os nós internos. Depois a combinação do endereço abre uma rede de descarga. O inversor desse caminho gera DEC ativo. O keeper de realimentação ajuda a manter alto um nó não selecionado e se desliga quando a saída correspondente sobe após descarga. A implementação usa um footer compartilhado para isolar avaliação. É importante respeitar os pinos por nome: no subcircuito congelado DEC3 aparece antes de DEC2, mas o mapeamento lógico das quatro linhas continua o binário esperado.',
 'O esquema visual deste slide é explicativo e não substitui o esquemático congelado.', 'O gerador reproduz essa conectividade ao compor a matriz.')
add('Geração da matriz e integração física','GERADOR PYTHON','generator',
 ['4 linhas × 8 colunas; 32 bitcells e 8 pares BL/BLB.','Instâncias periféricas e pinos lidos dos artefatos congelados.','Magic: custom fabric; OpenROAD: integração com SKY130HD.','Auditor separado confere terminais, coordenadas e ordem dos bits.'],
 'A mesma configuração reproduziu GDS e SPICE equivalentes.', ['tools/phase2_core.py','tools/run_phase2_fabric.py','tools/review_phase2_structure.py','reports/phase2/review_20261104/reproduction/results.json'],
 'O gerador monta a matriz e os periféricos, produz referência e layout e exporta a fronteira física para a integração. Para evitar que o mesmo erro seja repetido no grafo e na geometria, usamos uma conferência independente da extração: cada WL tem 16 gates de acesso, correspondentes a duas portas por bitcell, e cada par BL/BLB corresponde à coluna correta. A reconstrução a partir das fontes produziu o mesmo GDS após normalizar datas e SPICE idêntico inclusive nas junções.',
 'O gerador físico entregue está limitado a 4×8; equivalência de artefatos não substitui leitura/escrita elétrica.', 'O resultado integrado está nesta geometria real.')
add('Layout integrado da SRAM 4×8','LAYOUT INTEGRADO','layout',
 ['1.493 MOS: 401 customizados + 1.092 SKY130HD.','20 FF e lógica de fases, captura, interface e CTS.','Floorplan experimental: 540 × 380 µm.'],
 'Imagem do GDS real: M4/M5 e footprints das células padrão.', ['reports/phase2/layout_overview/results.json','physical/phase2/delivery.json','reports/phase2/review_20261104/structure/results.json'],
 'Esta imagem mostra a geometria realmente entregue, não uma ilustração genérica de chip. O total é de 1.493 MOS. Os 1.092 adicionais incluem 480 MOS dos vinte FF, 328 da lógica de captura e interface, 266 das fases e adaptadores e 18 de três buffers de clock. Taps e fillers ocupam geometria, mas seus modelos usados aqui não acrescentam MOS à contagem. A dimensão do top é um floorplan experimental e não uma macro compacta otimizada.',
 'A visualização não comprova DRC ou LVS; essas verificações vêm separadamente.', 'Primeiro mostro a sequência elétrica efetivamente observada.')
add('Sequenciamento elétrico de acesso','FORMAS DE ONDA REAIS','phases',
 ['PRECH libera antes de WE/WL.','WL seleciona a linha; BL/BLB desenvolvem diferencial.','SCLK regenera e o FF captura após a descida pública.'],
 'TT · 1,8 V · 27 °C · conectividade e junções extraídas, sem wire RC.', ['reports/phase2/final_polish_20261104/startup_extended/r1_idle2/results.json','reports/phase2/final_polish_20261104/events/results.json'],
 'Este é um recorte real contendo escrita e leitura do cenário de partida com dois ciclos inativos. PRECH é ativo baixo; por isso precisamos que suba antes de WE e da wordline. Durante a leitura aparece a separação entre BL e BLB, seguida da regeneração do sense. A captura nos FF tem atraso local em relação à descida externa. As verificações analisaram todas as amostras, inclusive a recuperação, e não apenas o valor final de DATA.',
 'As curvas não contêm PEX RC detalhado das interconexões.', 'A separação entre as fases precisou de correções durante o desenvolvimento.')
add('Problemas encontrados e correções','ENGENHARIA','issues',
 ['WE antecipado: guarda −232,897 ps → tap 40 → +167,388 ps no piloto.','Roteamento: anel de obstrução de 5 nm isolava acessos M4.','Importação: vias tecnológicas e vistas físicas reais precisaram ser preservadas.'],
 'Readback correto, sozinho, não revelava todos os problemas.', ['docs/phase2_execution.md','reports/phase2/phase_guard_review/results.json'],
 'O primeiro exemplo é elétrico: o dado lido estava correto, mas WE começava enquanto a pré-carga ainda não tinha liberado. Corrigimos a qualificação para o tap 40 e preservamos os dois resultados. No roteamento, uma subtração de obstruções deixava um anel de cinco nanômetros fechando o acesso ao pino. Corrigimos a exportação do pad real, sem alterar a célula. Por fim, a importação no Magic precisava carregar vias tecnológicas e vistas físicas de taps e fillers. Isso mostra por que uma saída de ferramenta ou uma única simulação não bastam.',
 'As guardas citadas são dos pilotos históricos, não limites de PVT da macro final.', 'As correções foram fechadas com verificações físicas independentes.')
add('Verificação física: DRC e LVS','DRC · LVS · GDSII','physical_checks',
 ['Magic: zero violações no GDS reimportado.','Netgen: correspondência expandida de modelos, terminais e dimensões.','Gate, bulk, W e L adulterados foram rejeitados.','1.493 MOS brutos → 1.459 equivalentes após redução legal de paralelos.'],
 'DRC verifica regras geométricas; LVS compara o circuito extraído.', ['reports/phase2/final_gds/magic.txt','reports/phase2/final_gds/lvs.txt','reports/phase2/review_20261104/lvs_negative/results.json'],
 'DRC e LVS respondem perguntas diferentes. DRC verifica regras de construção do layout. LVS compara o circuito que extraímos com a referência, incluindo o controle e os dispositivos reais. A comparação não usa uma black box para esconder o núcleo. Reimportamos o GDS final e repetimos a verificação. Os quatro defeitos deliberados foram rejeitados inclusive quando o Netgen retorna código de processo zero, por isso analisamos o conteúdo do log. A redução de paralelos explica a diferença de contagem sem remover MOS físicos.',
 'Zero DRC no deck público não equivale a signoff de foundry ou confiabilidade de fabricação.', 'Depois de verificar a geometria, exercitamos o armazenamento real.')
add('Simulação elétrica de leitura e escrita','VALIDAÇÃO ELÉTRICA','electrical',
 ['Campanha original: 128 bits lidos + 392 checks adicionais.','Campanha dirigida: 1.332 checks totais, incluindo 160 bits lidos.','Walking-one/zero, perturbações pós-captura, idle e máscara viva.'],
 'Bitcells e sense amplifiers transistor-level; sem armazenamento comportamental.', ['reports/phase2/extracted_access_singlethread/results.json','reports/phase2/review_20261104/directed/results.json','docs/phase2_final_polish.md'],
 'A campanha original percorreu os endereços e verificou também o protocolo. A dirigida acrescentou padrões walking e mudanças no endereço e nos dados externos após a captura. O resultado continuou coerente com a requisição registrada. O gráfico complementar ilustra estados internos e leitura externa no circuito real, durante escrita e reescrita complementar. As 1.332 verificações já incluem os 160 bits lidos; não somamos esse subconjunto outra vez. Retenção e preservação são demonstradas nas janelas e padrões ensaiados.',
 'A figura é um recorte identificado de um ensaio real de partida; os totais da campanha dirigida vêm do receipt separado.', 'A temporização precisa distinguir disponibilidade interna de garantia externa.')
add('Contrato temporal da interface','INTERFACE PÚBLICA','timing',
 ['Subida: captura da requisição. Descida: captura da leitura.','RAW válido ~7,44 ns antes do clock local; FF_D ~7,25 ns.','Estabilidade posterior observada ≥2 ns: janela limitada.','20 ns = 50 MHz no experimento; Fmax e turnaround pendentes.'],
 'Janelas internas disponíveis não são setup/hold públicos da SRAM.', ['specs/sram_4x8_timing_contract.md','reports/phase2/final_polish_20261104/capture_directed/results.json'],
 'O contrato registra o comportamento funcional e identifica os parâmetros numéricos ainda não caracterizados. SA_OUT e DOUT_RAW são o mesmo nó neste binding; depois há mux, FF e tri-state. As janelas próximas de 7,44 e 7,25 nanossegundos mostram estabilidade disponível antes do clock local. Os dois nanossegundos posteriores são o limite da observação, não hold mínimo. A comparação usa uma referência Liberty de 25 graus contra o ensaio de 27 graus. O clock de 20 nanossegundos é uma condição que funcionou, não a frequência máxima.',
 'Setup/hold externo, read-valid, enable/disable, turnaround e mínimo de partida não estão qualificados.', 'A última rodada também ampliou a partida sem reset.')
add('Ensaios de partida sem reset','SEM RESET EXTERNO','startup',
 ['Rampas 1 / 5 / 10 ns; condicionamento de 0 / 2 / 3 ciclos nas combinações ensaiadas.','5 cenários PASS · 3.383 checks totais, incluindo 240 bits lidos.','Sem IC, nodeset ou conteúdo artificialmente imposto.'],
 'Zero ciclos inativos ainda incluiu 9 ns de espera após o plateau.', ['reports/phase2/final_polish_20261104/startup_verification/results.json','docs/phase2_final_polish.md'],
 'Cada cenário começou em um processo novo do simulador. Variamos rampa, quantidade de capturas inativas e primeira linha e palavra. A primeira operação foi escrita, seguida de leitura; depois escrevemos as outras linhas e reescrevemos a primeira com o complemento. O auditor conferiu os nós de armazenamento conhecidos, a pré-carga, a seleção e o barramento. Todos os cinco passaram. O caso sem ciclos inativos aguardou nove nanossegundos após o plateau. Mantivemos duas capturas inativas como procedimento de reprodução, sem alegar ganho estatístico ou mínimo universal.',
 'Cinco cenários direcionados não representam todas as rampas, estados iniciais, brownout ou PVT.', 'Podemos então consolidar os aceites sem misturar os escopos.')
add('Quadro de resultados','ACEITES SEPARADOS','results',
 ['F2-DIG: síntese/GLS funcional aprovada.','F2-FIS: SRAM 4×8 integrada e aprovada no experimento nominal.','DRC/LVS e acessos reais, com artefatos e hashes rastreáveis.','Contrato temporal documentado e partida ampliada.'],
 'F2-DIG funcional e F2-FIS nominal concluídos; aceite formal pendente.', ['docs/phase2_review_20261104_acceptance.md','docs/phase2_final_polish.md','physical/phase2/delivery.json'],
 'A síntese e a GLS verificaram o controle mapeado. O LVS comparou o layout ao circuito, e as simulações transistor-level verificaram os acessos no ponto nominal. Mantemos os aceites separados, com a configuração e as condições explícitas. Os arquivos podem ser revisados pelo manifesto e pelo guia de reprodução. As tentativas e correções históricas permanecem identificadas nos relatórios.',
 'O parecer técnico não substitui a deliberação dos integrantes e orientadores.', 'As limitações delimitam o que o projeto ainda não está afirmando.')
add('Limitações da validação','ESCOPO EXPERIMENTAL','limits',
 ['Fmax e temporização externa completa ainda não caracterizados.','Sem RC detalhado, robustez PVT ou partida estatística.','Sem potência/yield caracterizados ou qualificação de fabricação.','Geração física 8×8 / 16×8 / 32×8 continua fora desta entrega.'],
 'A caracterização completa não faz parte do aceite experimental desta entrega.', ['specs/sram_4x8_timing_contract.md','docs/phase2_review_20261104_acceptance.md'],
 'Esses pontos são limites do trabalho realizado e não defeitos automaticamente atribuídos ao circuito. O protótipo funciona no ponto TT, 1,8 volts e 27 graus, com interconexões sem RC detalhado. Ainda não medimos frequência máxima, pior caso externo ou variabilidade estatística. A limitação de cobertura de modelos da Fase 1 também continua registrada. Apontamos essas fronteiras sem iniciar agora a próxima fase.',
 'Não confundir o nominal experimental com robustez de fabricação.', 'Fecho com a contribuição concreta desta fase.')
add('Conclusão da Fase 2','CONCLUSÕES E DISCUSSÃO','closing',
 ['Controle digital sintetizado e células customizadas integrados.','SRAM 4×8 física com leitura, escrita e captura demonstradas.','Entregáveis: RTL, gerador Python, GDS/LEF/DEF/MAG/SPICE, relatórios e scripts.'],
 'Fase 2 tecnicamente concluída no escopo experimental. Fechamento acadêmico depende da equipe e dos orientadores.', ['docs/phase2_reproduction_guide.md','docs/phase2_final_polish.md'],
 'A Fase 2 transformou células individuais em uma SRAM 4 por 8 integrada, com controle digital mapeado, vistas físicas e leitura e escrita demonstradas. A reconstrução reproduziu a geometria e o circuito extraído; os relatórios registram as correções e o alcance dos ensaios. A entrega está pronta para revisão técnica. Gostaria de discutir com vocês a aceitação desse escopo e os parâmetros que precisam ser definidos antes de qualquer caracterização posterior. Obrigado.',
 'Sem aprovação formal atribuída antecipadamente aos orientadores.')
(ROOT/'slides.json').write_text(json.dumps(slides,ensure_ascii=False,indent=2)+'\n')
notes=['# Roteiro de fala — Fase 2\n\nDuração sugerida: 20–25 minutos, ajustável à discussão. Este roteiro não é uma leitura literal dos bullets.\n']
md=['# Open-Source SRAM Memory Compiler — Phase 2\n\nFonte editável: `slides.json`; diagramas nativos no PPTX.\n']
for i,s in enumerate(slides,1):
 notes += [f"\n## Slide {i} — {s['title'].replace(chr(10),' ')}\n",f"**Objetivo:** {s['takeaway']}\n",f"**Fala sugerida:** {s['speech']}\n",f"**Destaque:** {s['bullets'][0]}\n"]
 if s['caveat']:notes += [f"**Ressalva:** {s['caveat']}\n"]
 if s['transition']:notes += [f"**Transição:** {s['transition']}\n"]
 notes += ['**Fontes:** '+', '.join(f'[{n}](../../{n})' for n in s['source'])+'\n']
 md += [f"\n---\n\n## {i:02d} — {s['title'].replace(chr(10),' ')}\n\n{s['kicker']}\n\n",'\n'.join('- '+b for b in s['bullets'])+'\n',f"\n**Síntese do conteúdo:** {s['takeaway']}\n",'\n**Fontes:** '+', '.join(f'[{n}](../../{n})' for n in s['source'])+'\n']
(ROOT/'speaker_notes.md').write_text('\n'.join(notes).rstrip()+'\n')
(ROOT/'phase2_technical_review.md').write_text('\n'.join(md).rstrip()+'\n')
print('slides',len(slides))
