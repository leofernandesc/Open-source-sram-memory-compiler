# Perguntas técnicas — revisão da Fase 2

As respostas se restringem ao protótipo e às evidências indicadas. Elas não
substituem a especificação nem a revisão dos orientadores.

## 1. Por que uma bitcell 6T?

É a arquitetura convencional aprovada: dois inversores realimentados armazenam
um bit, e dois NMOS de acesso conectam os nós a BL/BLB quando WL é ativada.
Permite estudar retenção, leitura diferencial e escrita com células CMOS
customizadas. Não foi demonstrada superioridade sobre outras topologias neste
projeto. [Especificação](../../../specs/technical_specification.md).

## 2. Por que começar por 4×8?

É o primeiro alvo da especificação, com quatro linhas e uma palavra de oito
bits por linha, sem column mux. Mantém pequeno o problema de integração e
permite verificar todos os endereços. O RTL também cobre 8/16/32 palavras,
mas esses layouts não fazem parte da entrega física atual.
[Contrato digital](../../../specs/sram_4x8_digital.md).

## 3. Por que um decoder dinâmico?

Foi a arquitetura selecionada para o projeto, compatível com pré-carga e
avaliação coordenadas pelo controle. Ela depende de endereço capturado,
sequenciamento e retenção dos nós dinâmicos. A entrega não afirma que é
universalmente melhor, mais madura ou mais eficiente que uma estática.
[Seleção oficial](../../../release/phase1_current.json).

## 4. O que fazem os quatro PMOS keepers?

Cada keeper realimenta um nó dinâmico a partir de seu DEC. Ajuda a restaurar
o nó não selecionado; após a descarga selecionada, o DEC sobe e desliga esse
PMOS. A topologia e sizing são os congelados da revisão de 33 MOS.
[Estudo de robustez](../../../docs/row_decoder_robustness_20261029.md).

## 5. Por que o decoder Verilog não substitui o físico?

O lógico é uma referência para seleção binária e testes digitais. Não contém
os dispositivos, a carga dinâmica ou os efeitos elétricos do decoder escolhido.
O núcleo entregue instancia o circuito de 33 MOS e os drivers reais.
[Binding físico](../../../physical/phase2/macro_binding.v).

## 6. Como o controlador conversa com o núcleo?

Na subida captura ADDR, pedido e dado de escrita. O núcleo recebe ADDR_Q,
DIN_Q, READ_Q e WRITE_Q e devolve DOUT_RAW. Não há recaptura redundante dentro
da fronteira que acrescente um ciclo. O wrapper captura a leitura na descida.
[Interface](../../../specs/phase2_physical_interface.md).

## 7. Como são geradas as fases?

Portas HD qualificam CLK e os pedidos capturados usando taps 24/40/60/80 de
uma cadeia de 80 inversores preservados na síntese. PRECH baixo pré-carrega;
PCLK alto avalia; WE alto escreve; SCLK alto regenera. Os taps são posições,
não tempos garantidos. [Fonte](../../../physical/phase2/macro_binding.v).

## 8. Como evitamos conflito write/precharge?

O piloto inicial mediu WE ativo antes de PRECH liberar, guarda −232,897 ps.
A qualificação de WE foi deslocada para tap 40, produzindo +167,388 ps naquele
piloto. O top atual passa nos checks de exclusão e recuperação. Não extrapolar
os números de piloto como margens all-corner.
[Histórico](../../../reports/phase2/phase_guard_review/results.json).

No top final, a nova medição PRECH80→WE20 foi 211,3–212,9 ps. WL80 antecedeu SCLK20 em 238,5–243,9 ps; taps não foram modificados. [Análise complementar](../../../docs/phase2_timing_extension.md).

## 9. Como funciona a leitura diferencial?

BL e BLB começam pré-carregadas/equalizadas. A wordline conecta os dois nós da
bitcell ao par; o estado armazenado desenvolve uma diferença entre as linhas.
O sense resolve o sinal em um nível lógico. Amplitude observada no nominal
não caracteriza offset estatístico ou SNM do conjunto.
[Ondas e eventos](../../../docs/phase2_final_polish.md).

No modelo sem wire RC, o diferencial com sinal correto já foi observado 50 ps antes de SCLK20. Isso confirma a ordem nesse experimento, sem caracterizar sensibilidade do SA. [Análise complementar](../../../docs/phase2_timing_extension.md).

## 10. Como o sense amplifier resolve BL/BLB?

A folha selecionada tem sete MOS, com amostragem PMOS e latch regenerativo.
SCLK baixo amostra; alto regenera. SA_OUT liga-se a DOUT_RAW no binding atual.
Ele não é um modelo ideal nas simulações transistor-level.
[Seleção das folhas](../../../release/phase1_keeper/README.md).

## 11. Por que capturar a leitura na descida?

É o contrato aprovado: a subida captura o pedido e a fase alta executa o
acesso; a descida captura o resultado. O orçamento aproximado é de meio ciclo,
com atrasos de clock e captura reais. Isso não garante timing completo sem
caracterização da macro. [Contrato temporal](../../../specs/sram_4x8_timing_contract.md).

As menores janelas novas foram cerca de 7,435 ns em RAW e 7,240 ns em FF_D antes do clock local. FF_Q mudou após 0,190–0,223 ns; DATA válido apareceu 0,489–0,549 ns após a descida pública, nos bits que mudaram. Esses instantes distinguem clock local, mux, registro e driver. [Análise complementar](../../../docs/phase2_timing_extension.md).

## 12. Como operar sem reset?

O conteúdo inicial é indefinido. Alimentar com CLK baixo e controles inativos,
aguardar estabilização e executar o condicionamento ensaiado antes de escrever.
O procedimento nominal mantém duas capturas inativas. Um caso com zero
capturas também passou, mas aguardou 9 ns após o plateau; não é partida
imediata ou mínima universal. Nenhum IC/nodeset impôs dados internos.
[Campanha](../../../docs/phase2_final_polish.md).

## 13. Por que uma black box na síntese?

A matriz é customizada. A fronteira impede que Yosys a converta em um array
de FF comuns. GLS usa um substituto funcional para testar o wrapper; a
integração física substitui a fronteira pelo núcleo real e exige LVS e SPICE.
[Listas de fontes](../../../docs/sram_4x8_interfaces.md).

## 14. O que o LVS realmente comparou?

Netgen comparou a referência expandida ao circuito extraído do GDS, incluindo
modelos, conexões, bulks e W/L, sem esconder o núcleo numa black box. A tolerância
dimensional do deck e a redução de paralelos estão documentadas. Os defeitos
de gate, bulk, largura e comprimento foram rejeitados em cópias.
[Negativos](../../../reports/phase2/review_20261104/lvs_negative/results.json).

## 15. O que significa DRC zero?

O Magic não encontrou violações relevantes no GDS final reimportado com o
estilo full e tecnologia usados. Não comprova operação elétrica, LVS ou
signoff de fabricação. Esses resultados são verificados separadamente.
[Transcrição](../../../reports/phase2/final_gds/magic.txt).

## 16. Como o gerador organiza a matriz?

Combina 32 bitcells, periféricos por linha/coluna e pinos formais congelados;
produz referência e geometria, exporta o núcleo e integra HD por OpenROAD.
Um auditor separado confere terminais e coordenadas extraídas para evitar
aprovar exclusivamente duas representações derivadas do mesmo grafo errado.
[Auditor estrutural](../../../tools/review_phase2_structure.py).

Uma segunda passagem conferiu o complemento físico de DIN e os oito NANDs equivalentes dos enables. A primeira versão desse auditor presumiu uma rede comum e foi corrigida; não houve defeito no circuito. [Análise complementar](../../../docs/phase2_timing_extension.md).

## 17. Por que 1.493 MOS se as folhas somam 401?

Há 1.092 MOS HD adicionais: 480 nos 20 FF, 328 em captura/interface/feedback,
266 em fases/adaptadores e 18 nos três buffers CTS. Taps e fillers existem
fisicamente mas não acrescentam MOS nos modelos SPICE desses masters. Netgen
reduz 34 paralelos e compara 1.459 equivalentes; a contagem física bruta é 1.493.
[Inventário](../../../reports/phase2/review_20261104/structure/results.json).

## 18. O que prova que houve armazenamento real?

O ensaio usa a extração com 1.493 MOS e junções reais, sem array comportamental
ou fontes internas de dados. Escritas, reescritas complementares, retenção e
leituras são observadas nas bitcells, FF e DATA. Palavras conhecidas das outras
linhas são conferidas para detectar corrupção e aliasing. Não são verificadas
como zero as palavras ainda não escritas.
[Verificação de partida](../../../reports/phase2/final_polish_20261104/startup_verification/results.json).

C1 acrescentou READ→READ e WRITE→WRITE na mesma linha, com checks das palavras não selecionadas. Foram 1.150 checks, incluindo 72 bits lidos. [Análise complementar](../../../docs/phase2_timing_extension.md).

## 19. O que demonstram os 15.619 checks GLS?

Demonstram comportamento do wrapper/controlador mapeados com o scoreboard e
modelos HD a atraso zero, usando substituto funcional da macro. São 2.504
transações e diversas asserções, não 15.619 operações elétricas. A GLS roteada
repete a mesma cobertura e não duplica o número de testes exclusivos.
[Receipt](../../../reports/phase2/review_20261104/digital/results.json).

## 20. Por que 20 ns não comprova Fmax?

Foi um ponto de operação que passou nos estímulos, modelos, cargas e temperatura
ensaiados. Não houve busca do limite, STA completo, PVT ou RC detalhado. Os
parâmetros externos e arcos da macro não têm Liberty caracterizada. 50 MHz é
a taxa desse experimento, não frequência máxima garantida.
[Contrato](../../../specs/sram_4x8_timing_contract.md).

## 21. O que falta caracterizar?

Setup/hold públicos, read-valid, enable/disable, turnaround, limites de clock,
partida mínima/estatística, PVT, interconexões RC, potência e yield. O projeto
registra esses limites e a cobertura de modelos da Fase 1; não iniciou essas
campanhas nesta entrega. [Aceite](../../../docs/phase2_review_20261104_acceptance.md).

## 22. Por que a fase está concluída experimentalmente?

Há fontes e vistas reproduzíveis, síntese e GLS, núcleo e top conectados,
GDS verificado e acesso transistor-level no cenário declarado. A conclusão é
condicionada ao escopo nominal e às ressalvas, não ao projeto inteiro. O
fechamento acadêmico depende da deliberação da equipe e orientadores.
[Guia de reprodução](../../../docs/phase2_reproduction_guide.md).

## 23. Podemos dirigir DATA assim que mudamos OEb?

Não há atraso de desligamento ou turnaround qualificado. O mestre primeiro
retira leitura viva, espera liberação real e então dirige dados respeitando
setup/hold. A máscara viva não cancela o pedido capturado. Z no modelo lógico
não significa uma transição elétrica instantânea.
[Propriedade do barramento](../../../specs/sram_4x8_timing_contract.md).

C2 passou em 1.281 checks, incluindo 48 bits. Com probe oposto de 1 kΩ, os cruzamentos de corrente de 50 µA ocorreram em ~0,13–0,18 ns ao desativar e ~0,63 ns ao reativar. Não são máximos garantidos. Os handoffs de 0,3/0,6 ns não tiveram sobreposição detectada. O dado anterior pode aparecer durante a fase alta antes da nova captura. [Análise complementar](../../../docs/phase2_timing_extension.md).

## 24. Como recuperar os raws que não estão no Git?

Os receipts registram hash e local; o pacote opcional lossless pode ser
transferido pelo responsável e restaurado em cache com verificação. Caso não
esteja disponível, repetir as campanhas em diretórios novos e PDK compatível.
Um excerpt ou contador não substitui a reanálise do transiente completo.
[Procedimento](../../../docs/phase2_reproduction_guide.md).

A extensão acrescenta um bundle opcional no mesmo formato, com três raws (piloto C1, C1 completo e C2). Nenhum dump grande é incluído no Git; sem transferência do pacote, é necessário regenerar as campanhas. [Análise complementar](../../../docs/phase2_timing_extension.md).
