# Roteiro de apresentação — Fase 1

Roteiro de fala para acompanhar os oito slides de `person3_phase1_status.html`. Duração aproximada: 4 a 5 minutos. As explicações dos esquemáticos são intencionalmente breves.

## Slide 1 — Andamento da Fase 1

“Bom dia. Vou apresentar o andamento dos circuitos periféricos da SRAM SKY130A: o decoder de linha, o wordline driver e o write driver. Vou mostrar rapidamente como cada circuito funciona, quais resultados já foram medidos e o que ainda falta fechar nesta fase.”

## Slide 2 — Escopo

“A primeira implementação da memória é uma SRAM síncrona 4×8: quatro palavras de oito bits, com uma palavra em cada linha física. O endereço seleciona uma linha pelo decoder; o wordline driver reforça esse sinal para a linha de células. Na escrita, o write driver controla o par diferencial de bitlines. O foco aqui são essas folhas de circuito, ainda sem afirmar que a macro completa está validada.”

## Slide 3 — Wordline driver

“O esquemático usa dois inversores CMOS em cascata. O segundo estágio é maior e fornece mais corrente para carregar a capacitância da wordline; como são dois estágios, a saída mantém a mesma polaridade da entrada. Foram aprovados 36 de 36 casos no esquemático e outros 36 de 36 usando o PEX disponível. No caso de carga estimada de 17,4 femtofarads, o pior atraso medido foi de 0,291 nanossegundo no esquemático e 0,386 no PEX. Esse PEX cobre o circuito folha, não a linha física completa.”

## Slide 4 — Write driver

“O esquemático gera WE_B a partir de WE e tem dois caminhos complementares para BL e BLB. Quando a escrita está habilitada, DATA e seu complemento externo selecionam níveis opostos nas bitlines; quando está desabilitada, os caminhos de saída ficam isolados. Na simulação nominal, a escrita de zero levou BL para perto de zero e BLB para 1,8 volt; a escrita de um produziu o comportamento complementar. As varreduras de capacitância foram medidas, mas ainda não existe um limite de aceitação especificado para comparar esses valores.”

## Slide 5 — Decoder dinâmico B7

“Este é um decoder dinâmico 2 para 4. Na fase de pré-carga, os PMOS carregam os quatro nós internos; na avaliação, o endereço habilita uma das quatro pilhas NMOS para descarregar o nó correspondente. Um inversor de saída transforma essa descarga em uma saída DEC ativa. Assim, 00 seleciona DEC0, 01 seleciona DEC1, 10 seleciona DEC2 e 11 seleciona DEC3. O candidato B7 passou nos critérios elétricos pré-layout executados, mas ainda não tem layout, DRC, LVS ou extração próprios.”

## Slide 6 — Captura do endereço e PCLK

“Também foi estudado quanto tempo deixar entre a captura do endereço e a avaliação do decoder. As transições da saída do registrador foram aproximadas com dados de clock-to-Q da Liberty SKY130, e o PCLK foi aplicado como sinal ideal. Para o caso pré-layout testado, 1,50 nanossegundo passou nos 72 casos selecionados e deixou 431 picosegundos entre a estabilização dos literais e PCLK, acima do guard experimental de 250 picosegundos. Esse valor é uma referência provisória: não fecha setup e hold do sistema, nem define a frequência máxima da memória.”

## Slide 7 — Concluído e pendente

“Nas folhas do wordline driver e do write driver há simulação, layout, DRC sem violações e correspondência LVS única. Para o decoder, ainda faltam layout, DRC, LVS e repetir as verificações com parasitas extraídos. Também falta integrar as folhas com a linha física, o bitcell e o precharge. Uma tentativa integrada anterior parou na geração do netlist do precharge, antes de chegar ao ngspice; por isso, a leitura e a escrita da macro ainda não estão demonstradas.”

## Slide 8 — Plano de fechamento

“Os próximos passos são registrar as premissas da interface PCLK, desenhar e fechar o layout do decoder, extrair seus parasitas e repetir os testes críticos. Depois, a equipe precisa conferir a carga real da wordline e executar os testes integrados de escrita e leitura. A entrega da Fase 1 deve reunir os arquivos e resultados reproduzíveis, além de deixar explícitas as pendências que dependerem das interfaces dos outros blocos.”

## Fechamento

“Em resumo, os dois drivers já têm evidência de validação física em nível de folha. O decoder dinâmico B7 tem caracterização elétrica pré-layout e uma estimativa provisória de temporização, mas ainda precisa passar pelo fluxo físico e pela integração. Esse é o limite do que os resultados atuais permitem afirmar.”

## Respostas curtas se perguntarem

- **1,50 ns já é o período final da SRAM?** Não. É um alvo provisório medido para o caso pré-layout testado; a origem real de PCLK, setup e hold e a frequência máxima ainda precisam ser caracterizados.
- **O decoder já passou em DRC e LVS?** Ainda não. Os resultados apresentados para ele são de simulação pré-layout; o fechamento físico está pendente.
- **A macro 4×8 já foi validada?** Não. Os resultados são de circuitos folha e estudos pré-layout; a integração completa com bitcells e precharge ainda precisa ser executada.
