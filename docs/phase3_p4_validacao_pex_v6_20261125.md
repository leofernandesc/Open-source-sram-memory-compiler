# P4 — validação integrada na PEX física v6

Atualizado em 25/11/2026. Geometria selecionada tecnicamente em [P3](phase3_p3_decisao_arquitetura_20261125.md). O registro numérico e os hashes por corner estão em [`phase3_p4_v6_status_20261125.json`](../build/phase3/phase3_p4_v6_status_20261125.json).

## Identidade física fixada

GDS `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37`, LEF `39f09e853f89e7693523588c5c2d28fb217c8c9710fd18cd09b2bd813be0d5c7`, PEX `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` e binding `3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d`. O binding, PEX e GDS usados nos replays correspondem à identidade documentada em P3.

## Replays integrados de 370 ns

| Corner | Resultado funcional | Cobertura e recibos | Ownership bruto |
|---|---|---|---|
| TT | 18/18 ciclos PASS; 72/72 lanes de leitura PASS | classificação, cobertura, integridade e gate P1 PASS; 319 modelos verificados; c12 idle 247,5 ns PASS | c2 `INCONCLUSIVO`, suplemento estático aprovado para bits 4/7 |
| SS | 18/18 ciclos PASS; 72/72 lanes de leitura PASS | classificação, cobertura, integridade e gate P1 PASS; 319 modelos verificados; c12 idle 247,5 ns PASS | 18/18 eventos PASS no observador bruto |
| FF | 18/18 ciclos PASS; 72/72 lanes de leitura PASS | classificação, cobertura, integridade e gate P1 PASS; 319 modelos verificados; c12 idle 247,5 ns PASS | c2 `INCONCLUSIVO`, suplemento estático aprovado para bits 1/2/4/7; c10 `INCONCLUSIVO`, auditoria read→write elegível nas oito lanes |

As seis escritas mantêm seus checks de entrada, armazenamento e readback aprovados. Os vereditos brutos de ownership permanecem preservados. Para FF c2, o JSON agregado inclui c10 e por isso reporta `INCONCLUSIVE`; a classificação acima usa somente as quatro linhas do evento c2. Para FF c10, a análise exige estabilidade contínua de DATA desde a habilitação do host até CLK e durante a janela de escrita. Todas as oito lanes satisfazem a condição e o relatório não aponta blockers. O resumo reproduzível por evento está em `build/phase3/v6_ownership_supplements_247p5/consolidated.json`, SHA-256 `b45b35606e72d59f12a746fcbfa6b5aff9208b0581284de24fc6c20cebf17601`. A aplicação segue o protocolo técnico de P2 e mantém os vereditos brutos inalterados. Os sete controles negativos de P2 rejeitam falsos PASS, mas pertencem à campanha candidata de P2 e não são novos ensaios de falha injetada no binding físico v6.

## C250 físico e estado do gate

O C250 pós-layout FF existente usa a mesma PEX/GDS/binding e terminou `TRIPLE_STRONGARM_FF_PASS`, com 250 ns, retorno 0 e 319 hashes de modelos. O recibo de simulação tem SHA-256 `baccb091429e854b139212e058991a4f0511e6e3ddfb6ba788721491e9d2c4cd`; a onda tem SHA-256 `bf0a24844e85967c28365dece31fb35ab9515ef5bb2fec64fc9aac47e2c06ba7`.

O C250 físico TT reutilizou o deck físico selado, preservando binding, PEX, mapa e modelos e alterando somente o seletor de corner FF→TT. Terminou 250 ns, retorno 0, sem erros de simulação e com 319 modelos verificados. A análise C250 retornou `TRIPLE_STRONGARM_TT_PASS`, com quatro leituras, seis escritas, seis intervalos de retenção e nenhuma falha ou lacuna de observabilidade. Recibo TT SHA-256 `d4a9d6334fd0efe12634fcec9232434f8d4b84bcec477ab522a874783ed70503`; waveform `edc2bf25c2dc2d25567b78d0c1a4523ca4a5d0e3936687e61972c18f14c29510`; análise `288dbe5d2d6331a2ab54704aef4e32aa681665267cc648ea06e49a3f7ee53e44`. O observador arquivado tem SHA-256 `6b5e8104e7aaaeaba281d1b24ab9aa50d15e453bf0267c1f0bc4131787216372`. A análise no host usou a equivalência `np.trapezoid=np.trapz` devido à versão local do NumPy. Os detalhes estão no JSON P4. A evidência está em `build/phase3/v6_c250_physical/TT/`.

C250 físico SS usou o mesmo deck selado, preservando binding, PEX, mapa e modelos e alterando somente o seletor FF→SS. Terminou 250 ns, retorno 0, sem erros e com 319 modelos verificados. A análise retornou `TRIPLE_STRONGARM_SS_PASS`, com quatro leituras, seis escritas, seis intervalos de retenção e nenhuma falha ou lacuna de observabilidade. Recibo SS SHA-256 `193e912c541f824973a9c0071436cbfaf750266723b334383032c801fae415c3`; waveform `41190426be55725726e4e4324814f66145834209c3289b3111c239a76a4715e3`; análise `6a4e59330d3a90b96371e0f29f7709f6ba86b4c1f32637fbc7b63041b43e7ba0`. Evidência em `build/phase3/v6_c250_physical/SS/`. Os C250 TT/SS anteriores da variante virtual não substituem os resultados na geometria selecionada.

## Decisão técnica do gate P4

**P4 fechado tecnicamente em 25/11/2026** para a identidade física v6 registrada acima. C250 TT/SS/FF passa; os replays integrados de 370 ns passam em função, cobertura, topologia e recibos nos três corners; os eventos de ownership raw inconclusivos estão cobertos pelas regras suplementares por evento aceitas em P2, com ondas e recibos originais intactos. O JSON [`phase3_p4_v6_status_20261125.json`](../build/phase3/phase3_p4_v6_status_20261125.json) reúne os hashes e checks. Os sete controles negativos de P2 rejeitaram falsos PASS, mas foram exercidos na campanha candidata de P2, não em novas injeções do binding v6. A revisão de arquitetura pela equipe ainda deve registrar o aceite da seleção P3.

