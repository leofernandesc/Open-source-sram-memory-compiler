# Fase 3 · ECO virtual do StrongARM na macro completa

**O StrongARM corrigiu c16 e c17 em TT, na macro 4×8 com SCLK físico nativo.** O ECO virtual passou em TT e SS no diagnóstico C250. Em FF, o StrongARM do bit 3 acertou os quatro reads, mas os senses originais dos bits 6 e 7 resolveram c15 como 1. A palavra em FF foi `0xCF` em vez de `0x0F`. A aprovação funcional da macro fica limitada aos corners e à fixture que passaram. [Resumo e recibos](../build/phase3/strongarm_virtual_eco_20261121/campaign_summary.json)

## Execuções e palavras

| Ciclo | Esperado | C original TT | ECO virtual TT | ECO virtual SS | ECO virtual FF |
|---:|---|---|---|---|---|
| 14 | `0xAA` | `0xAA` | `0xAA` | `0xAA` | `0xAA` |
| 15 | `0x0F` | `0x0F` | `0x0F` | `0x0F` | **`0xCF`** |
| 16 | `0xF0` | `0xF8` | **`0xF0`** | `0xF0` | `0xF0` |
| 17 | `0xF0` | `0xF8` | **`0xF0`** | `0xF0` | `0xF0` |

| Corner | Veredito | Tempo efetivo | Final / retorno | Amostras |
|---|---|---:|---|---:|
| TT | `VIRTUAL_ECO_TT_PASS` | 3.021,53 s | 250 ns / 0 | 15.346 |
| SS | `VIRTUAL_ECO_SS_PASS` | 2.969,02 s | 250 ns / 0 | 13.886 |
| FF | `VIRTUAL_ECO_FF_FAIL` | 2.919,38 s | 250 ns / 0 | 15.534 |

Foram três transientes SPICE, com **2 h 28 min 30 s acumulados**, nos modelos TT, SS e FF de SKY130A, todos a 1,8 V nominal e 27 °C. O binding experimental, os modelos do núcleo e o buffer ficaram congelados. Entre os decks, a seleção `.lib` é a única diferença. As condições de C250 foram preservadas, inclusive a rampa, as seis escritas, os 250 ns, Gear/KLU e o passo máximo de 25 ps. Os 319 hashes do fechamento dos modelos foram verificados por execução. A referência C250 original foi reutilizada por meio do seu waveform instrumentado validado. [Recibos TT](../build/phase3/strongarm_virtual_eco_20261121/TT/simulation.json) · [Recibos SS](../build/phase3/strongarm_virtual_eco_20261121/SS/simulation.json) · [Recibos FF](../build/phase3/strongarm_virtual_eco_20261121/FF/simulation.json)

## Auditoria do ECO e parasitas

`VIRTUAL_ECO_READY` foi confirmado pela conectividade extraída. Foram removidos **X102, X234, X1267 e X1560** do latch original, os samplers PMOS **X235 e X521** e o tail **X351**. Foram acrescentados os **11 MOS** do núcleo StrongARM, com W/L arquivado, e dois adaptadores não inversores `sky130_fd_sc_hd__buf_1` do ensaio 4×1. A interface do mux, o FF de saída e seus controles são os de C. Todos os **1.742 MOS restantes**, **16.187 R** e **12.371 C** permaneceram idênticos cartão a cartão. Isso preserva as 32 bitcells, os sete senses adjacentes, o acionador de 80 estágios, a distribuição R87, a pré-carga, o decoder, o write driver, as wordlines e a alimentação extraída.

O StrongARM lê `rc8210/rc8222`, usa SCLK em `rc8585` após R87 e R76, e usa `rc1713/rc5874` como pontos locais de VDD/VSS. Os cinco gates reais carregam a rede nativa. O buffer de SA aciona `rc5993` e passa pela rota original até A1 de `_40_` e D de `_78_`. O buffer complementar aciona `rc8025`. As rotas antigas de SA/SAB permanecem carregadas no lado de saída desses buffers, com seus acoplamentos a SCLK, BL/BLB, PRECH e demais grupos.

O envelope virtual mantém os parasitas locais antigos, incluindo o par diferencial de 2,78132 fF nas rotas de saída, os ramos passivos R68/R60 e C6858 de 4,17213 fF na cauda reutilizada `rc7187`. Os novos nós internos de regeneração e intermediários têm os modelos intrínsecos e as cargas dos buffers aplicáveis. C131, C178, C155 e C186 continuam nas mesmas placas extraídas. O tratamento explícito deu caminho elétrico às antigas redes de sinal por dispositivos e pela rede resistiva nativa. O modelo local é híbrido e precisará ser substituído pelo PEX do StrongARM físico. [Manifesto do ECO](../build/phase3/strongarm_virtual_eco_20261121/TT/eco_audit.json) · [Diff do binding](../build/phase3/strongarm_virtual_eco_20261121/TT/binding.diff) · [Inventário local](../build/phase3/strongarm_virtual_eco_20261121/local_pex_inventory.csv) · [Pinagem, W/L e escolhas de implementação](../build/phase3/strongarm_virtual_eco_20261121/implementation_notes.md)

## Evidência funcional e elétrica

D foi medido na borda local interpolada de cada FF. Q e a palavra completa foram verificados no prazo C250 de +1 ns relativo ao início da descida pública e na observação de DATA em +1,5 ns, antes da atuação da sonda fraca da fixture. Os resultados confirmam endereço, WE e WL na janela de avaliação das seis escritas. As palavras com readback estão na tabela. A retenção observada diretamente é da bitcell da linha 3, bit 3, de 120,55 a 245,55 ns. Nas leituras c16/c17 de todos os corners, o maior Q ficou abaixo de 0,154 V e o menor QB acima de 1,770 V. A validação dos demais bits no escopo observado usa seus D/Q e os readbacks completos. [Lanes TT](../build/phase3/strongarm_virtual_eco_20261121/TT/lanes.csv) · [Lanes SS](../build/phase3/strongarm_virtual_eco_20261121/SS/lanes.csv) · [Lanes FF](../build/phase3/strongarm_virtual_eco_20261121/FF/lanes.csv)

| Corner | D3 / Q3 c16 (V) | D3 / Q3 c17 (V) | Margem conjunta de regeneração e D em c15 / c16 / c17 (ns) |
|---|---|---|---|
| TT | 0,00175 / 0,000137 | 0,00167 / 0,000120 | 5,441 / 4,927 / 4,950 |
| SS | 0,00166 / 0,002146 | 0,00159 / 0,000271 | 3,142 / 2,329 / 2,371 |
| FF | 0,00098 / 0,000143 | 0,00091 / 0,000140 | 6,686 / 6,342 / 6,368 |

D3/Q3 ficaram altos em c15 nos três corners, aproximadamente 1,80 V. Em TT, o atraso do tap 80 até o tronco em c16 foi de cerca de **515 ps** no cruzamento de 50%. O gate local em c16 passou por 20/50/80% em **214,154 / 214,404 / 214,814 ns** e por 80/50/20% na descida em **224,072 / 224,163 / 224,273 ns**. Contra C original, o maior deslocamento interpolado nesses níveis de SCLK foi de cerca de 8 ps no gate do sense 3 e 7,4 ps nos samplers rastreados dos outros bits em TT. Esses deslocamentos são estimativas de interpolação, com brackets de amostragem preservados no JSON. Em TT, nenhum erro foi observado nos outros sete bits, e em SS as quatro palavras também passaram integralmente.

Em c16, o tronco ↑50 ficou em 214,402 ns em TT, 216,611 ns em SS e 213,199 ns em FF. O intervalo tap 80 ↑50 → tronco ↑50 foi de cerca de 515, 766 e 386 ps, respectivamente. READ_Q está alto na abertura de avaliação em c15–c17, e as bordas de tap 80, NAND, tronco, gate local e PRECH foram observadas diretamente. [Medições detalhadas TT](../build/phase3/strongarm_virtual_eco_20261121/TT/analysis.json) · [Medições detalhadas SS](../build/phase3/strongarm_virtual_eco_20261121/SS/analysis.json) · [Medições detalhadas FF](../build/phase3/strongarm_virtual_eco_20261121/FF/analysis.json)

| Corner | Pico de `abs(Id)` do tail, c15–c17 (µA) | Sobreposição tail/reset na avaliação, c15–c17 (ps) | Sobreposição tail/reset na descida, c15–c17 (ps) |
|---|---:|---:|---:|
| TT | 99,28–99,55 | ~232 | 101–102 |
| SS | 69,03–70,80 | 0 | 52–55 |
| FF | 129,91–133,55 | 482–495 | 116–117 |

Os marcadores de 1 µA descrevem a simultaneidade de correntes de dreno salvas. BL/BLB e os quatro nós de reset recuperaram nas janelas observadas. Pelo mesmo marcador, não houve intervalo de simultaneidade do tail do StrongARM com os dispositivos de pré-carga de BL/BLB nas janelas de avaliação e recuperação medidas. Isso não qualifica potência ou limites elétricos. Em TT, o pico do tail subiu de cerca de 89 µA na bancada ativa com SCLK ideal para cerca de 99 µA no híbrido completo, enquanto a simultaneidade na subida caiu de 388–400 ps para cerca de 232 ps. As diferenças de circuito de entrada, alimentação, geometria antiga e carga coexistem entre as duas bancadas. A carga integrada durante sobreposição e as correntes dos quatro PMOS de reset estão nos JSONs e arquivos de correntes. [Gráfico TT](../build/phase3/strongarm_virtual_eco_20261121/TT/comparison.png) · [Gráfico SS](../build/phase3/strongarm_virtual_eco_20261121/SS/comparison.png) · [Gráfico FF](../build/phase3/strongarm_virtual_eco_20261121/FF/comparison.png)

## FF · Primeira divergência observável em c15

A linha selecionada é 2. Nos bits 6 e 7, SCLK20 ocorreu em **193,007 ns**, cerca de **97 ps antes de WL80**. Nesse ponto, BLB−BL foi **−6,94 mV** no bit 6 e **+5,50 mV** no bit 7. No cruzamento SCLK50, os diferenciais já estavam positivos, **+276 mV** e **+233 mV**, respectivamente. Ainda assim, as sondas de SA na entrada do mux e de SAB atingiram a polaridade complementar errada em **193,559 ns** e **193,583 ns**. Ambas ficaram com a decisão errada até a captura, e D dos dois bits estava alto em cerca de 1,80 V. Q e DATA propagaram a falha. A divergência funcional já está nos **senses originais 6 e 7**, antes do FF ou do compartilhamento do barramento. [Gráfico dos caminhos 6 e 7](../build/phase3/strongarm_virtual_eco_20261121/FF/ff_c15_paths.png) · [Eventos medidos](../build/phase3/strongarm_virtual_eco_20261121/ff_c15_first_divergence.json)

A antecipação de SCLK em relação a WL e o pequeno diferencial no início são evidências compatíveis com uma janela de avaliação vulnerável em FF. Os dados da rodada não isolam a contribuição causal da troca do sense 3. O FF arquivado de outra geometria tem binding distinto. Sem uma referência FF nativa pareada em C250, o erro pode estar presente em C original neste cenário ou depender da mudança de carga do ECO virtual.

## Decisão física e sequência mínima

O StrongARM é funcionalmente superior ao sense 3 original em TT no ensaio integrado c16/c17. A distribuição compartilhada de SCLK acionou adequadamente o StrongARM nas quatro leituras de TT, SS e FF. O resultado sustenta o **estudo de layout isolado do bloco**, com dimensões congeladas. A proposta ainda depende de resolver FF antes de aprovar a substituição na macro.

1. Gerar um controle **FF de C original**, exatamente com C250 e o mesmo PEX nativo. Observar c15 nos bits 6 e 7, incluindo SCLK, WL, BL/BLB, SA/SAB, D/Q e a palavra. Se o erro também aparecer em C, tratar a janela dos senses originais em FF. Se C passar, investigar a alteração de carga para localizar a regressão antes de liberar a integração.
2. Desenhar e verificar a célula StrongARM isolada. Manter a pinagem BL/BLB, SCLK, SAO/SABO e VDD/VSS. Medir a simetria, as cargas de entrada, o acoplamento e os retornos físicos. Exigir DRC limpo e LVS correspondente.
3. Reextrair a célula e a macro experimental com a alteração só na coluna 3. Reexecutar C250 e a fixture integrada em TT/SS/FF, incluindo regressão de escrita, retenção, os oito bits, recuperação, handoff e timing. Caracterizar eletricamente a geometria aprovada.

O plano anexo detalha W/L, posição, alimentação, conexão com mux/FF e critérios de DRC/LVS e PEX. O GDS de C continua como referência. A macro original permanece `FAIL` TT, `PASS` SS no escopo integrado e `NOT_CHARACTERIZED`, com FF nativo pendente. [Plano da célula isolada](../build/phase3/strongarm_virtual_eco_20261121/physical_plan/next_layout_gate.md)

## Reprodutibilidade e preservação

O leitor inicial de TT rejeitou uma sonda duplicada de retorno local. A análise offline comprovou identidade integral entre as duas colunas e fez a normalização do alias. Em SS, a checagem inicial de WE/WL em +5 ns antecedia a avaliação do corner. O observador revisado confirma a janela real de WL e de WE no clock alto, com o mesmo critério nos três corners. As bandas, a borda local e o prazo de validade de DATA ficaram iguais. As análises iniciais e os waveforms originais da rodada estão arquivados. [Ajuste do observador](../build/phase3/strongarm_virtual_eco_20261121/observer_resolution.md) · [Checkpoint TT](../build/phase3/strongarm_virtual_eco_20261121/TT/tt_checkpoint.md)

No checkout, a análise e os testes podem ser refeitos sem SPICE:

```bash
run=build/phase3/strongarm_virtual_eco_20261121
export PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1
python3 "$run/test_eco.py" -v
for corner in TT SS FF; do python3 "$run/analyze_eco.py" "$run/$corner"; done
python3 "$run/summarize_eco.py"
python3 "$run/diagnose_ff_c15.py"
```

O ZIP inclui o deck de cada corner, netlists, diffs, waveforms de tensão e corrente, logs, análises, gráficos, testes e manifesto de hashes. A reprodução SPICE usa o ambiente EDA `sram-xschem`, ngspice 44.2 e a árvore montada em `/work`, em uma cópia isolada dos arquivos de entrada por corner. Os recibos registram o comando real e os hashes conferidos. A branch `integration/phase3-danilo-ss`, o HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`, o checkpoint e as alterações locais foram preservados. [Logs de testes](../build/phase3/strongarm_virtual_eco_20261121/test_eco.log) · [Verificação dos checkpoints](../build/phase3/strongarm_virtual_eco_20261121/preservation.log)
