# Decisão técnica de P2 — SRAM 4×8

Data: 25/11/2026. Escopo: candidata virtual de oito StrongARM no envelope RC da PEX v6, GDS `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37`, PEX `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f`, binding `d2151cac96a35a99b200764eec6ebbea517915d413cc1ddb8664a1dc7e247227`, fixture integrada de 370 ns e idle c12 em 247,5 ns.

## Decisão

Aceito para P2 o protocolo de ownership suplementar abaixo. Com essa regra, P2 fecha funcionalmente para o candidato virtual nos três corners. Os vereditos brutos de TT c2 e FF c2/c10 permanecem `INCONCLUSIVO` nos recibos originais. O aceite acrescenta uma classificação por lane baseada nos dados brutos e nas análises suplementares vinculadas por hash.

Para idle→write em c2, o witness é suficiente quando o idle e sua liberação estão verificados, a sonda fraca está desligada, o host forte fica habilitado, a macro permanece isolada, DATA está no nível esperado, há ao menos três amostras nativas cobrindo 50 ps conservadores e não há oposição sustentada. Uma oposição transitória em uma única amostra no fechamento do host não caracteriza contenção sustentada. O witness estático só se aplica à escrita após idle.

Para read→write em FF c10, além do gate, host, isolamento e quietude, exigir condução e liberação verificadas da leitura, intervalo de turnaround isolado com ao menos três amostras, separação nativa positiva, sonda fraca desligada e DATA no nível esperado continuamente desde o primeiro ponto em que o host forte conduz até a subida de CLK e ao longo da janela de escrita. Estabilidade tardia após a habilitação não passa. O piso conservador de 50 ps continua valendo.

O pedido de idle c12 em 247,5 ns é aceito para este protocolo integrado. Preserva-se o resultado histórico do estímulo a 247 ns, que não passa o piso conservador.

## Evidências de aceite

- TT, SS e FF completam 18/18 operações e nove leituras por oito lanes. Seleção, regeneração, recuperação e retenção passam. Seis escritas têm readback e cobrem as quatro linhas. c12 read→idle passa nos três corners.
- SS tem ownership bruto integralmente aprovado, incluindo c2 e c10. TT c10 e SS c10 fornecem positivos de read→write. SS c2 fornece positivo de idle→write.
- Os sete controles físicos negativos cobrem host ausente e contenção em TT/FF c2, além de host ausente, liberação atrasada e habilitação fraca simultânea em FF c10. Nenhum recebe `PASS` do observador original e as condições suplementares rejeitam todos.
- O auditor de FF c10 verifica estabilidade desde a habilitação do host. A regressão com estabilização tardia falha. A onda natural permanece elegível, com 70 amostras antes de CLK em cada lane suplementada e separação conservadora de 1,029869 ns.
- Manifestos e relatórios associam os dados às ondas, recibos, PEX e modelos. Os diagnósticos de controles físicos são usados como negativos da regra, não como substitutos da onda integrada.

## Limites e etapa seguinte

Esta decisão fecha P2 para a candidata virtual com as condições nominais declaradas. Não seleciona a arquitetura física final, não converte a topologia de oito StrongARM em layout, e não caracteriza timing, potência, SNM ou Liberty. A etapa seguinte é P3. A v6 híbrida é a única geometria com DRC/LVS/PEX físico identificado. Validar seus replays de 370 ns como controle físico e decidir formalmente se ela será a geometria 4×8 final. Se for escolhida, P4 vincula C250 e o aceite funcional à PEX da v6. Se a decisão escolher oito StrongARM, fechar layout, DRC, LVS e nova PEX antes de P4.

Evidências detalhadas: `build/phase3/diagnostics/p2_revalidation_20261125T083047/review_matrix_v2.json`, `supplement_physical_controls.json`, `FF_c10_read_to_write_candidate_v2.json` e os runs `build/phase3/integrated_{replay,observed}_247p5/{TT,SS,FF}/`.
