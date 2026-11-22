# Fase 3 — Acionamento físico local de R87 com SKY130 inv_2

**`FUNCTIONAL_WITH_INTEGRATION_RISK`.** O v2 corrigiu c16 e c17 no recorte TT. Os três gates comutaram de forma coordenada, D ficou baixo por aproximadamente 4,99 ns até cada captura e a recuperação foi preservada. A redução de força da célula de saída baixou o pico de corrente do tail de aproximadamente 327 para **314 µA**, ainda perto de **2×** o pico do contraste ideal. A evidência sustenta manter o v2 como candidato experimental e adiar o ECO físico até resolver o risco de integração. [Resultado medido](../build/phase3/sclk_local_driver_20261121_v2/analysis.json)

## Candidato e preflight

O v2 preserva o inversor de entrada assimétrico testado em v1, com PMOS de 2,52 µm e NMOS de 0,65 µm, ambos com L = 0,15 µm. A subida de SCLK precisa descarregar MID pelo NMOS mais estreito. Na descida, o PMOS mais forte recarrega MID e o restaurador puxa a saída ativamente para baixo. A assimetria foi mantida para preservar o mecanismo já funcional, com a menor mudança necessária para testar menor força de saída.

A única troca de espécie de célula é **`sky130_fd_sc_hd__inv_4` → `sky130_fd_sc_hd__inv_2`**. A vista SPICE da célula instalada contém dois NMOS regulares de 0,65 µm em paralelo e dois PMOS HVT de 1 µm em paralelo, com L = 0,15 µm. Isso reduz pela metade os dispositivos paralelos do restaurador e sua carga nominal sobre MID, mantendo o dobro dos ramos do `inv_1` para preservar capacidade de descarga. O LEF dá área de 3,754 µm² para só a célula de saída, ante 6,256 µm² no v1. A área do bloco completo depende do inversor de entrada, poços, taps e roteamento. [Netlist do candidato](../characterization/phase3/experiments/sclk_local_driver_v2.spice) · [Célula instalada](../build/phase3/sclk_local_driver_20261121_v2/run/driver_library.spice) · [Driver v1](phase3_driver_local_sclk_tt_20261120.md)

O estágio recebe `rc8562` e aciona `sclk_driver` antes de R87 (6,46438 Ω). Da bifurcação `rc8571`, R68/R60/R76 mantêm acoplados os gates de X235/X521/X351 pelas resistências extraídas. A carga prevista é a mesma rede de três gates, cuja carga líquida dinâmica de subida pelo R87 no controle é 13,45 fC, equivalente a aproximadamente 7,5 fF pela razão Q/1,8 V. Isso é uma referência de carga efetiva naquele pulso. Os capacitores do ramo e os modelos MOS permanecem ativos. O estágio tem duas inversões e saída CMOS, com polaridade igual à entrada e caminho ativo de desativação. As duas fontes de 0 V são medidores em série na entrada e na alimentação. A temporização provém dos dispositivos.

O **preflight `READY`** conferiu o ramo exclusivo, o PEX `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`, os 319 arquivos de modelos SKY130A, o controle, o contraste conjunto, o v1 e os hashes dos estímulos. O recorte de 36 MOS, 493 resistores e 968 capacitores e `stimuli.spice` permaneceram byte a byte idênticos ao controle. O deck principal só ganhou sondas de pré-carga, corrente e alimentação. O c15 continua no mesmo intervalo. A fonte de 0 V do controle antes de R87 deu lugar ao driver. BL/BLB, PRECH, WL representada pelo replay, captura, VDD e os controles externos ficaram como no controle arquivado. [Manifesto e critérios pré-selados](../build/phase3/sclk_local_driver_20261121_v2/manifest.json)

Foi executado **um** transiente de 59 ns com `ngspice -n -b bench.spice`, ngspice 44.2, SKY130A TT, 1,8 V, 27 °C, Gear/KLU e passo máximo de 25 ps. O tempo local 0–59 ns corresponde a 188–247 ns na referência. Retorno 0 em **31,95 s**, timeout de 120 s, **14.001 amostras**, waveform completo e correntes sincronizadas. O hash do deck principal é `43a5017da8cac4e6c18904b0077877bd1104186c3d794cbb5f2edee022718946`. O hash do waveform é `f1c6d59d18e68089418ebf8f65aa93d3d885cb39ef84bc2437df885421c027cc`. [Tentativa selada](../build/phase3/sclk_local_driver_20261121_v2/run/attempt.json) · [Recibo](../build/phase3/sclk_local_driver_20261121_v2/run/result.json)

## Resultado funcional

O c15 preservou D alto e a recuperação do latch antes de c16. Na referência da macro, a bitcell da linha 3, bit 3, preservou Q/QB próximo de 0/1,8 V antes e depois da avaliação. As fontes históricas de BL/BLB são mantidas no recorte. O recorte mede o latch e D. Q da bitcell, Q do flip-flop de saída e DATA da macro permanecem referências externas.

| Medição v2 | c16 | c17 |
|---|---:|---:|
| NTAIL antes da subida pública (V) | 1,148309 | 1,147724 |
| Primeiro tail a 1 µA (ns) | 214,571 | 234,571 |
| BLB−BL / SAB−SA nesse instante (mV) | +668 / +414 | +681 / +421 |
| Sense complementado e sustentado a partir de (ns) | 214,769 | 234,767 |
| D baixo a partir da primeira amostra sustentada (ns) | 215,065 | 235,065 |
| Captura arquivada (ns) | 220,058 | 240,058 |
| SA / SAB na captura (V) | −0,00012 / 1,79999 | −0,00012 / 1,79999 |
| D na captura (V) | 0,000196 | 0,000197 |
| Margem de D baixo até a captura | ≥4,993 ns | ≥4,993 ns |

Em ambos os ciclos, o sense permaneceu na polaridade correta após a ativação, sem inversão tardia até a captura. O v2 preservou três pulsos lógicos completos, sem cruzamentos adicionais de 20/50/80% nos gates monitorados. Os intervalos de transição dos três gates se sobrepõem. Na subida, o maior skew entre os três gates ficou em 1,18 ps. Na descida, em 0,99 ps. Esses deltas são interpolações do transiente e não prazos públicos. [Gráfico comparativo](../build/phase3/sclk_local_driver_20261121_v2/comparison.png) · [Bordas por gate](../build/phase3/sclk_local_driver_20261121_v2/gate_edges.csv)

## Comparação elétrica

| Indicador c16 / c17 | Controle | Ideal conjunto | v1 `inv_4` | v2 `inv_2` |
|---|---|---|---|---|
| Acionamento 20/50/80% na subida, deslocamentos frente ao controle, faixa dos 3 gates | Referência | Aproximadamente +182 ps em todos | +437 / +206 / −174 ps | +403 / +173 / −204 ps |
| Deslocamento na descida a 80/50/20%, aproximadamente | Referência | Até 0,48 ps de diferença | +184 / +105 / +5 ps | +167 / +88 / −11 ps |
| Slew subida 20–80% no tail (ps) | 652,5 / 652,3 | 652,3 / 652,3 | 40,8 / 40,6 | 45,6 / 45,5 |
| Slew descida 80–20% no tail (ps) | 198,9 / 199,0 | 198,9 / 198,9 | 19,1 / 18,9 | 20,9 / 21,1 |
| Primeiro 1 µA do tail (ns) | 214,277 / 234,278 | 214,462 / 234,463 | 214,603 / 234,602 | 214,571 / 234,571 |
| Pico de tail na avaliação (µA) | 133,23 / 133,18 | 157,85 / 158,30 | 326,78 / 325,84 | **314,07 / 313,48** |
| Pico de tail na desativação (µA) | 14,20 / 14,18 | 21,42 / 21,42 | 30,44 / 30,68 | 31,79 / 32,01 |
| Decisão e D baixo sustentado até captura | Errada / errada | Correta, 4,77 / 4,77 ns | Correta, 4,97 / 4,98 ns | **Correta, 4,99 / 4,99 ns** |

A desativação a 20% do tail em v2 precedeu o primeiro gate local de PRECH em queda a 80% por **85,9/85,2 ps**. O último `|Id|` acima de 1 µA do tail terminou em 224,256/244,253 ns. O primeiro ramo de pré-carga/equalizador acima do mesmo marcador começou em 224,383/244,381 ns. As separações foram **126/127 ps** em c16/c17 e a de c15 também permaneceu positiva. Sense e bitlines voltaram às bandas de pré-carga. A corrente de desativação cresceu ligeiramente frente ao v1, sem interseção observada dos intervalos no marcador utilizado. O marcador de 1 µA é diagnóstico, sem limite absoluto de corrente definido pelo projeto. [Intervalos de corrente](../build/phase3/sclk_local_driver_20261121_v2/analysis.json) · [Picos de desativação](../build/phase3/sclk_local_driver_20261121_v2/shutdown_peak.csv)

O v2 consumiu aproximadamente **53,0 fJ por pulso** no estágio, frente a 70,4–70,5 fJ em v1, com pico de alimentação do driver de 210–211 µA contra 271–272 µA. A carga de entrada ficou em **6,94 fC**, semelhante à de v1 e abaixo dos 13,45 fC do ramo substituído no pulso histórico. Isso quantifica somente o recorte alimentado por replay. A fonte de SCLK de fronteira mascara realimentação sobre o acionador compartilhado, e a bancada não mede o efeito nos outros sete senses, na rede compartilhada de alimentação ou em SS/FF. A mudança frente ao ideal foi usada para interpretar slew, corrente e margem. Ela não prejudicou o resultado funcional deste recorte.

## Veredito e próximo gate

O v2 é um **driver SKY130 funcional e coordenado no recorte TT**, com subida efetiva mais rápida que a do contraste ideal e recuperação demonstrada. Reduziu área da célula restauradora e energia frente ao v1, mas o pico de corrente de avaliação caiu só cerca de 4% e ficou próximo do regime de v1. A combinação de slew de aproximadamente 46 ps e pico de aproximadamente 314 µA torna a interação com a impedância das redes compartilhadas a pendência dominante. **`FUNCTIONAL_WITH_INTEGRATION_RISK`**, sem aprovação para integrar um ECO agora.

**Próximo gate de integração** — demonstrar, em uma bancada de fronteira que preserve a impedância do acionador compartilhado e a alimentação, que o v2 mantém a decisão e a desativação sob carga representativa, sem deslocar SCLK/PRECH dos outros senses nem produzir queda de alimentação funcionalmente relevante. A transposição para layout depende dessa evidência. O gate fica para outra rodada.

C permanece como referência. TT `FAIL` histórico em c16/c17. SS `PASS` no escopo integrado. FF e Liberty pendentes. Monte Carlo SNM concluído no domínio experimental `tt_mm`, com homologação pendente. Qualificação geral `NOT_CHARACTERIZED`. Nenhum ECO foi executado. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.

Quatro testes de software passaram. O analisador pós-processamento usou uma integral trapezoidal explícita para compatibilidade com a versão NumPy do ambiente de gráficos. O deck, o manifesto pré-selado, o executor congelado e os waveforms foram preservados. Para processar novamente os dados, usar a fase `analyze` do script com uma cópia dos artefatos em um diretório novo. [Testes](../build/phase3/sclk_local_driver_20261121_v2/tests.log) · [Script](../tools/phase3_sclk_local_driver_v2.py)
