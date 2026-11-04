# Fase 2 — matriz de requisitos e evidências

PASS refere-se ao escopo escrito na linha. As evidências estão em
`reports/phase2/review_20261104/`, salvo indicação diferente.

| ID / requisito | Implementação | Teste e evidência | Estado |
|---|---|---|---|
| D01 — interface síncrona 1RW, DATA[7:0], ADDR[1:0], controles e VDD/VSS | Wrapper/LEF/GDS/SPICE | GLS e auditoria de interfaces; `digital/`, `structure/` | PASS |
| D02 — somente 001 lê e 010 escreve | `rtl/sram_controller.v:16` | Oito controles e 64 transições; `digital/wrapper_gls.txt` | PASS |
| D03 — requisição/endereço/DIN na subida | Controlador e 12 FF HD | Scoreboard e perturbações transistor-level; `directed/checks.json` | PASS |
| D04 — alterações posteriores não substituem pedido capturado | FF, sem recaptura na macro | 72 checks de ADDR, 128 de DIN e controles vivos alterados; `directed/` | PASS |
| D05 — resultado na descida, sem ciclo extra | Wrapper e oito FF HD | GLS nas duas bordas e captura local medida; `capture_directed/` | PASS |
| D06 — último resultado preservado | Feedback do mux HD | 288 checks de retenção e cobertura RTL; `directed/` | PASS |
| D07 — liberação viva do barramento | READ_Q AND live_read; ebufn | Piloto 0/1/Z, 96 probes originais e 160 de leitura mascarada | PASS |
| D08 — sem reset/conteúdo inicial forçado | RTL/SPICE sem reset/IC/nodeset | X no modelo e leitura elétrica inicial sem conteúdo esperado | PASS |
| D09 — partida nas condições ensaiadas | Rampa 1 ns e duas capturas inativas | Escrita/leitura subsequentes em `directed/` e bancada original | PASS |
| D10 — todas as rampas/estados e duração mínima de partida | Não caracterizado | Nenhuma estatística ou sweep executado | NOT_EVALUATED |
| D11 — mapeamento real SKY130HD | Yosys e Liberty TT/25 °C | 20 dfxtp, oito ebufn e ausência de latches inesperados; `digital/` | PASS |
| D12 — macro preservada, nenhum array FF no núcleo | Black box digital e expansão física | Inventário Yosys e 32 bitcells extraídas; `digital/`, `structure/` | PASS |
| D13 — polaridade tri-state | `synth/sky130_tristate.v` | Piloto e inversão deliberada rejeitada no scoreboard | PASS |
| D14 — GLS sintetizada/roteada | HD powered, UNIT_DELAY=0; substituto funcional só em verificação | 15.619 checks por execução da mesma cobertura; `digital/`, `reproduction/gls/` | PASS |
| D15 — RTL para profundidades 4/8/16/32 | `rtl/sram_model.v` | 154.303 checks e seis profundidades inválidas; `reports/digital/phase2_review_20261104` | PASS |
| D16 — constraints experimentais identificadas | `physical/phase2/experimental.sdc` | Clock 20 ns/50% usado na reconstrução; `reproduction/route/flow.tcl` | PASS |
| D17 — STA/SDF/Fmax e IO timing qualificado | Sem Liberty caracterizada da macro | Não é afirmado desempenho completo | NOT_EVALUATED |
| P01 — folhas congeladas preservadas | Manifestos Fase 1 | `verify_phase1_handoff.py`, consolidação e aceite revisado | PASS |
| P02 — decoder dinâmico oficial de 33 MOS e keepers | Folha selecionada | LVS expandido, SPICE e contagem recursiva; `structure/` | PASS |
| P03 — ordem formal DEC3/DEC2 correta | Binding por pino formal | Netlist, extração e acessos 00/01/10/11 | PASS |
| P04 — 32 bitcells, quatro WL, oito pares BL/BLB | Núcleo físico | Auditor de terminais/posições; 16 gates de acesso por WL | PASS |
| P05 — periféricos nas quantidades previstas | Folhas + interfaces HD | Contagem/conexões extraídas e LVS; `structure/` | PASS |
| P06 — cada bit/linha no destino correto | Roteamento, registradores e tri-states | Terminais, ordem geométrica e palavras distintas; `structure/`, `directed/` | PASS |
| P07 — 401 customizados + 1.092 HD | PDK expandido e extração | 1.493 MOS; 1.459 após redução Netgen | PASS |
| P08 — corpos, poços, taps e alimentação | GDS/PDN/taps reais | DRC full, LVS e mutante de bulk rejeitado; `physical/`, `lvs_negative/` | PASS |
| P09 — sequenciamento sem conflito no ensaio | Taps 24/40/60/80; CLK/validade | Checks globais/por ciclo; original 392 e bancada dirigida | PASS |
| P10 — seleção de uma WL correta | Decoder + qualificação + driver | Ondas e auditor independente, com mudança viva de endereço | PASS |
| P11 — diferencial observado no ensaio | BL/BLB e SA reais | 160 observações; mínimo com sinal esperado 1,753725363 V | PASS |
| P12 — diferencial mínimo contra offset/ruído/mismatch | Não definido/caracterizado | Medição nominal não define critério mínimo | NOT_EVALUATED |
| P13 — DOUT_RAW, FF_D, Q e DATA coerentes | SA, mux, FF e tri-state | `capture_baseline/`, `capture_directed/`, `directed/` | PASS |
| P14 — escrita, retenção e leitura reais | 1.493 MOS; nenhum storage comportamental | 128 bits originais e 160 novos, idle/retorno/readback | PASS |
| P15 — 00/FF/AA/55 e palavras distintas | Bancada original 35 ciclos | `reports/phase2/extracted_access_singlethread/checks.csv` | PASS |
| P16 — walking-one/zero | 16 padrões distribuídos nas quatro linhas | `directed/bench.spice` e 160 bits lidos incluindo readback final | PASS |
| P17 — todos os padrões em todas as linhas no elétrico | Não executado exaustivamente | Cobertura distribuída explicitamente limitada | NOT_RUN |
| P18 — TT/1,8 V/27 °C e modelos identificados | Lib/temp/VDD reais | Bancada/hashes e guardas de condição/probes | PASS |
| P19 — GDS completo e referências resolvidas | Top HD + núcleo | Reimportação, 1.493 MOS, DRC/LVS e reconstrução | PASS |
| P20 — DRC do arquivo entregue | Magic 8.3.684, sky130A, drc(full) | GDS original e reconstruído: zero DRC | PASS |
| P21 — LVS com W/L/terminais | PDK setup com tolerância explícita | Match único; gate/bulk/W/L errados rejeitados | PASS |
| P22 — LEF sobre metal real | 16 pinos e 46 regiões de acesso | Checagem geométrica/parser OpenROAD, arquivos preservados | PASS |
| P23 — reprodução de fontes | Script e dependências explícitas | Tcl/LEF determinísticos; GDS normalizado e SPICE iguais; `reproduction/` | PASS |
| P24 — layouts 8/16/32 palavras | Não implementados neste protótipo | Nenhuma afirmação física dessas configurações | NOT_RUN |
| E01 — contadores derivados de dados executados | Logs/traces brutos | 128/392 reconciliados; 1.332 checks dirigidos reanalisados | PASS |
| E02 — ausência/NaN/netlist pós-run rejeitados | Guardas estritas | Dez adulterações de cópias rejeitadas; `evidence_guards/` | PASS |
| E03 — GDS diferente não herda aceite | Selo `verified_files` | Mutante fora do núcleo rejeitado; `package_negative.json` | PASS |
| E04 — falhas parciais/colisão não preservam falso PASS | Lifecycle/locks/guardas pré-escrita | Quatro CLIs e 117 métodos Python sem skips | PASS |
| E05 — PEX RC/PVT/potência/yield/Liberty | Excluídos desta rodada | Não executados nem declarados aprovados | NOT_EVALUATED |

NOT_RUN/NOT_EVALUATED não são PASS implícito. Parecer no
[quadro de aceite](phase2_review_20261104_acceptance.md).
