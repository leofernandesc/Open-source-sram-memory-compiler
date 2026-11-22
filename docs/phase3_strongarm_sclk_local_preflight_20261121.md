# Fase 3 · Preflight do acionador físico de SCLK para o StrongARM em coluna 4×1

**`BOUNDARY_NOT_DEFENSIBLE` · Contraste `NOT_RUN`.** O PEX de C identifica o acionador nativo e o caminho até R87. Nos waveforms examinados, faltam a tensão no tap 80, que comanda o estágio, e a tensão no nó interno que comanda seu inversor de saída. Reproduzir a fase nominal a partir de SCLK downstream sujeitaria o contraste à temporização da própria saída que ele precisa medir. A bancada ativa de 169 ns permanece como referência. Nesta rodada foram realizadas zero simulações e zero alterações de circuito. [Preflight e hashes](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/preflight.json)

## Acionador e caminho extraído

A vista lógica roteada instancia `macro_core.sense_drive` como `sky130_fd_sc_hd__and2_4`, com `A=READ_Q` e `B=tap80`. No binding, os gates de A são `rc6252/rc6253`. B é `rc8464`, saída dos dispositivos X255/X1285 alimentados pelo tap 79 (`rc8463`). O AND de 12 MOS é composto por um NAND (X241, X658, X1160 e X1274) e um inversor de saída. O gate comum do inversor é `rc7285`. Seus quatro NMOS `nfet_01v8` têm W/L de 0,65/0,15 µm e os quatro PMOS `pfet_01v8_hvt` têm 1,00/0,15 µm. O inventário identifica terminais de bulk, drenadores distribuídos e parâmetros de junção por dispositivo. Os 1.749 cartões X, 16.187 R e 12.371 C do binding conferiram com o PEX selado após o mapeamento de nomes. [Vista lógica](../reports/phase2/local/phase3_danilo_ss_ff2_spaced_layout/final.v) · [Inventário de cartões](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/inventario_sclk.csv)

```text
READ_Q / rc6252, rc6253 ─┐
                         NAND do AND2_4 → rc7285 → inversor de saída → rede SCLK
tap 80 / rc8464 ─────────┘
rc8603 → R103 → rc8566 → R81 → rc8565 → R82 → rc8564
       → R80 → rc8563 → R91 → rc8562 → R87 → rc8571
                               rc8571 → R76 → rc8585  X351, tail original
                               rc8571 → R68 → rc8584  X235, sampler original
                               rc8571 → R60 → rc8586  X521, sampler original
```

No caminho resistivo acima, `rc8603 → rc8562` soma 468,576 Ω. R87 tem 6,464 Ω e R76 tem 387,618 Ω, totalizando 862,658 Ω por esse caminho até o gate do tail original. O acionador injeta corrente por outros terminais em paralelo. A soma de percurso serve para rastrear a conectividade, enquanto a impedância de saída depende dos MOS, da fase e dos caminhos paralelos. Após R87, os quatro nós do ramo original somam 1,439 fF explícitos para VSS. A distribuição completa contém 45 nós resistivos, 48 R e 24 gates do sense original, dos quais 21 pertencem às outras sete colunas. As somas incidentes no grupo são 25,107 fF para VDD, 52,630 fF para VSS, 7,548 fF para PRECH e 49,117 fF para outros nós. São somas das placas no PEX. O efeito de cada acoplamento depende da tensão da outra placa e do estado dos MOS. [Inventário anterior por ramo](../build/phase3/sclk_v2_integration_preflight_20261121/final/branches.csv) · [Inventário desta rodada](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/inventario_sclk.csv)

### Carga efetiva do StrongARM

No deck ativo, um único nó SCLK aciona XTAIL (NMOS de 0,98/0,15 µm) e quatro PMOS de reset (cada um com 0,84/0,15 µm). A área geométrica de gate somada é 0,651 µm². A bancada ativa arquivada não mediu a corrente da fonte de SCLK. O protótipo anterior, com BL/BLB também impostas, mediu a corrente nessa fonte e entregou 9,39–9,41 fC líquidos por janela de avaliação. O pico em módulo foi 14,28–14,81 µA na avaliação e 32,89–33,54 µA na janela de reset. O quociente de carga por 1,8 V fica próximo de 5,22 fF e descreve aquele ensaio. A representação adequada para um futuro contraste local é ligar os cinco gates modelados ao acionador e medir a corrente resultante, pois sua carga depende da polarização e da transição dos nós internos. [Deck da coluna ativa](../build/phase3/sense3_strongarm_active_column_tt_20261121/run/bench.spice) · [Modelos de carga do StrongARM](../build/phase3/sense3_strongarm_active_column_tt_20261121/run/strongarm.spice) · [Correntes do protótipo anterior](../build/phase3/sense3_strongarm_tt_20261121/analysis.json)

## Fronteira e impedimento

| Fronteira | Evidência | Decisão nesta rodada |
|---|---|---|
| Entrada B do AND | `rc8464` aparece no PEX. O nó e seu predecessor `rc8463` estão ausentes dos quatro waveforms de C inspecionados. | Falta a tensão de entrada durante o histórico. |
| Entrada A do AND | `rc6243` tem waveform como proxy de READ_Q. A distância pelo percurso resistivo até os dois gates do AND é 1,646/1,850 kΩ. | Preserva a referência lógica do deck ativo. A sonda no gate exato melhoraria a atribuição do atraso ao estágio. |
| Entrada do inversor final | `rc7285` é o nó interno do AND2_4. Nenhum dos registros examinados o salvou. | O estágio final isolado também carece de um estímulo independente. |
| Saída física | `rc8605` é a ponta BL do sampler 0, após R84. `rc8585` é o gate do tail original do bit 3. `rc8562` aparece no arquivo do ensaio R87 integral. Os três são pontos posteriores ao AND. | São referências de comparação. Usá-los como comando do próprio AND contaminaria a fase e acrescentaria a propagação do estágio. |
| PRECH | C131 de 7,54814 fF liga `rc8562` a `rc8467`. PRECH é comandada por `valid_access AND (clk_released OR tap80)`. O proxy `rc8510` está a 655,853 Ω de percurso de `rc8467`. | A placa PRECH precisa de terminação na rede ativa ou replay no nó físico, com alcance explícito. Sua tensão no ponto de acoplamento ficou sem observação. |
| BL/BLB e caminho de escrita | C143, C144 e C164 (0,89884/1,10819/0,01702 fF) ligam ponto de tronco `rc8562` a `rc8212/rc8200/rc7173` no PEX. A coluna ativa os mantém em `sclk_root`, alimentado por replay de `rc8605`, além do SCLK ideal separado em `rc8585`. | Uma futura fonte física deve manter os três cartões, referindo essas placas ao tronco correspondente e sem duplicá-las. Nenhuma placa deve ir a VSS por conveniência. |
| Outros sete senses e alimentação | Existem as cargas ativas, os acoplamentos e o retorno completo no PEX de C. Nesta rodada o recorte pedido limita-se ao bit 3 e a VDD/VSS ideais. | O modelo local qualificaria a resposta de um acionador a um StrongARM. A impedância da distribuição com todos os consumidores e os retornos compartilhados continuaria a exigir integração. |

Em c15/c16/c17, na referência SCLK20, o proxy de READ_Q estava em aproximadamente 1,793 V e `clk_released` em 1,800 V. PRECH em `rc8510` já estava aproximadamente em 1,812 V. Com `clk_released` alto, a função OR mascara a borda ascendente do tap 80. As sondas arquivadas identificam o protocolo e observam a fase na saída, mas não fornecem a entrada necessária para um teste independente. Uma cópia do v2, um repetidor alimentado pelo SCLK já observado ou uma reconstrução da saída via atraso de PWL avaliariam outro protocolo de acionamento. Recriar a cadeia de atraso e suas cargas externas ampliaria o contraste além da fronteira local proposta. Esta limitação existe mesmo antes de considerar o efeito dos outros sete sense amplifiers. [Cabeçalhos inspecionados](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/cabecalhos_waveforms.txt) · [Amostras pareadas](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/referencia_c15_c17.csv) · [Preflight v2](phase3_preflight_integracao_sclk_v2_20261121.md)

## Referência mensurável e contraste

Os tempos abaixo usam o eixo histórico de C. No trecho funcional, o tempo local da bancada de 169 ns é o eixo histórico menos 78 ns. As bordas usam 20%, 50% e 80% de 1,8 V. As sobreposições são diagnósticas, com o marcador de 1 µA. Os relatórios e waveforms da bancada anterior foram verificados contra seus recibos. [Referência da coluna ativa](phase3_strongarm_coluna_ativa_tt_20261121.md) · [CSV de medições](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/referencia_c15_c17.csv)

| Ciclo | Captura (ns) | Subida 20/50/80% (ns) | Descida 80/50/20% (ns) | D / Q | Margem de D (ns) | Sobreposição tail/reset (ps) | Pico tail (µA) |
|---|---:|---|---|---|---:|---:|---:|
| c15 | 200,058 | 194,153 / 194,406 / 194,804 | 204,071 / 204,161 / 204,270 | 1 / 1 | 5,475 | 400 | 88,72 |
| c16 | 220,058 | 214,153 / 214,407 / 214,806 | 224,070 / 224,160 / 224,269 | 0 / 0 | 5,267 | 388 | 88,64 |
| c17 | 240,058 | 234,153 / 234,407 / 234,806 | 244,069 / 244,158 / 244,268 | 0 / 0 | 5,293 | 393 | 88,79 |

| Critério | SCLK ideal arquivado | SCLK físico local |
|---|---|---|
| c15 / c16 / c17 | PASS / PASS / PASS | `NOT_RUN` |
| Margem mínima de D | 5,267 ns | Sem medição |
| Subida 20–80% e descida 80–20% | 651–653 ps e 199 ps | Sem medição |
| Sobreposição tail/reset e pico do tail | 388–400 ps e 88,64–88,79 µA | Sem medição |
| Carga no tail durante a sobreposição | 16,48–16,56 fC | Sem medição |
| Retenção e recuperação | Verificadas na coluna ativa | Sem medição |
| Modelo de SCLK | Ideal no gate, proxy ideal adicional para acoplamentos | Topologia rastreada. Entrada temporal e placa PRECH ainda sem observação. |

O contraste fica em aberto para as três leituras e para o efeito da impedância nas bordas, nas margens e na recuperação. A simultaneidade tail/reset segue como risco observado com SCLK ideal. Nesse ensaio, a retenção e a recuperação foram demonstradas. A parcela de carga de condução direta no intervalo não foi determinada. Ainda falta evidência para autorizar um estudo de integração física fundamentado em um PASS com acionador local.

## Próxima evidência mínima

Em uma captura futura de referência TT de C, registrar **`rc8464` (tap 80)** no mesmo eixo do ensaio ativo, do condicionamento inicial às escritas e a c17, junto de `rc6252/rc6253` (READ_Q), `rc8467` (placa PRECH de C131), `rc8562` e do CLK de captura. A sonda `rc7285` acrescentaria uma referência direta caso se opte por testar somente o inversor final. Essa captura é a menor evidência adicional para reavaliar o preflight sem sintetizar a fase pela saída. Com a fronteira apoiada por essas sondas, o primeiro ensaio deve continuar sendo um único TT 4×1, com os cinco gates reais, as quatro escritas, c15–c17 e os probes de borda, corrente e recuperação. SS/FF e a integração em C ficam condicionados ao resultado desse ensaio.

## Preservação e reprodução

Nenhum netlist foi criado para simulação nesta rodada. O pacote inclui os resultados da auditoria, CSVs, cabeçalhos usados para determinar a disponibilidade de sondas, cópia do deck de referência, hashes e recibos. A seção de artefatos do manifesto aponta para os waveforms completos originais. No repositório, com Python 3 e NumPy, executar:

```bash
area=build/phase3/sense3_strongarm_local_sclk_tt_20261121
PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1 python3 "$area/audit_sclk.py" --output /tmp/strongarm_sclk_preflight
cmp "$area/preflight.json" /tmp/strongarm_sclk_preflight/preflight.json
```

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. C segue como referência, com `FAIL` TT e `PASS` SS no escopo integrado. FF segue pendente. B′ permanece inconclusivo em c16/c17, SCLK v2 e StrongARM continuam experimentais, Monte Carlo segue concluído no domínio experimental e a qualificação geral permanece `NOT_CHARACTERIZED`. Liberty segue pendente. [Estado do Git e recibos](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/)
