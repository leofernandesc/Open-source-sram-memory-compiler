# Fase 3 — Preflight de integração elétrica do driver SCLK v2

**`COMPACT_BOUNDARY_PARTIALLY_DEFINED`.** É possível definir um núcleo menor em torno de R87, com os acionadores nativos e as redes distribuídas de SCLK e PRECH. A integração ainda depende de representar as cargas ativas dos outros sete senses, os retornos e os acoplamentos nas fronteiras. A análise identificou esses caminhos no PEX e quantificou a malha resistiva de alimentação. **Nenhum contraste está autorizado por este preflight.** Foram executadas zero simulações e nenhum deck foi gerado. [Manifesto](../build/phase3/sclk_v2_integration_preflight_20261121/final/manifest.json)

## Topologia e cargas

O PEX integral da geometria C tem SHA-256 `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`. O mapa de nomes `rc…` foi reconciliado com a extração original e o binding TT arquivado. A especificação estabelece VDD nominal de 1,8 V e separação funcional entre avaliação e pré-carga. Os picos de corrente e marcadores de bancada servem para comparação. [Especificação](../specs/technical_specification.md) · [Resultado v2 no recorte](phase3_driver_local_sclk_v2_tt_20261121.md)

O `sense_drive` (AND2_4) recebe READ_Q nos gates `rc6252/6253` e o tap 80 em `rc8464` (`phase_delay[79].delay_cell.Y`). O NAND nativo é composto por X241, X658, X1160 e X1274. X541, X614, X632, X881, X1455, X1522, X1542 e X1664 acionam a rede distribuída de SCLK. Por exemplo, um caminho do acionador até a entrada de R87 é `rc8603 → rc8566 → rc8565 → rc8564 → rc8563 → rc8562`. Os dois troncos adjacentes `rc8562/8563` ligam-se por R91 de 2,6105 Ω. A posição proposta para o v2 é entre `rc8562` e a terminação original a montante de R87. Os três resistores locais R68/R60/R76 e os gates permanecem a jusante. [Cartões R](../build/phase3/sclk_v2_integration_preflight_20261121/final/control_resistors.csv) · [Cartões MOS, pinos D/G/S/B](../build/phase3/sclk_v2_integration_preflight_20261121/final/active_devices.csv)

| Coluna | SCLK, ramo e bifurcação local | Gates BL / BLB / tail | PRECH, ramo e bifurcação local | Gates carga BL / BLB / equalizador |
|---:|---|---|---|---|
| 0 | R84 · rc8574 | rc8605 / rc8577 / rc8606 | R185 · rc8479 | rc8510 / rc8511 / rc8482 |
| 1 | R85 · rc8573 | rc8578 / rc8580 / rc8579 | R186 · rc8478 | rc8483 / rc8484 / rc8485 |
| 2 | R86 · rc8572 | rc8581 / rc8583 / rc8582 | R187 · rc8477 | rc8486 / rc8487 / rc8488 |
| 3 | R87 · rc8571 | rc8584 / rc8586 / rc8585 | R188 · rc8476 | rc8489 / rc8490 / rc8491 |
| 4 | R88 · rc8570 | rc8588 / rc8590 / rc8589 | R189 · rc8475 | rc8493 / rc8494 / rc8495 |
| 5 | R89 · rc8569 | rc8591 / rc8593 / rc8592 | R190 · rc8474 | rc8496 / rc8497 / rc8498 |
| 6 | R90 · rc8568 | rc8594 / rc8596 / rc8595 | R191 · rc8473 | rc8499 / rc8500 / rc8501 |
| 7 | R83 · rc8567 | rc8597 / rc8600 / rc8599 | R184 · rc8472 | rc8502 / rc8504 / rc8505 |

Cada rede de controle tem **45 nós resistivos, 48 R e 24 gates**. Os ramos SCLK pesam 6,46438 Ω, com 6,89938 Ω na coluna 7. Em PRECH são 4,97115 Ω, com 5,40615 Ω na coluna 7. Em R87, da bifurcação local ao tail há 387,618 Ω e aos samplers 566,852/567,159 Ω. Entre o acionador nativo e os gates do sense 3, os caminhos resistivos mínimos somam aproximadamente 863 Ω até o tail e 1.042 Ω até os samplers. A rede tem caminhos paralelos. Esses somatórios identificam rotas e não representam impedância de acionamento.

| Rede | C direto para grupos VDD / VSS | C para a outra rede | C para terceiros |
|---|---:|---:|---:|
| SCLK | 25,107 / 52,630 fF | 7,548 fF | 49,117 fF |
| PRECH | 46,709 / 37,756 fF | 7,548 fF | 15,153 fF |

Os 188 capacitores incidentes não nulos preservam pares de placas distintos. C131 de **7,54814 fF** liga `rc8562` a `rc8467` e é contado uma vez no inventário. C178 e C186 ligam SCLK ao nó de SA do sense 3 e a NTAIL com 4,28661 e 0,19503 fF, respectivamente. C380/C381 acoplam PRECH a BLB/BL da coluna 3 com 0,629/1,027 fF. A jusante de R87, os quatro capacitores explícitos somam 1,439 fF, todos para VSS. A carga de gate e a realimentação pelos MOS e seus terminais ativos continuam além desses capacitores. Nas outras sete colunas, mantê-los como cargas fixas perderia a dependência de polarização e a resposta de BL/BLB e latch por Cgs/Cgd. [Inventário C](../build/phase3/sclk_v2_integration_preflight_20261121/final/control_couplings.csv) · [Caminhos e gates reais](../build/phase3/sclk_v2_integration_preflight_20261121/final/branches.csv)

PRECH é acionado pelo AND2_4 nativo `precharge_drive`, com NAND X400/X743/X812/X1523 e inversor de saída de oito MOS. Os gates de entrada estão em `rc7919/7920` (valid_access) e `rc8512` (precharge_phase). A rede de `rc8512` vem do OR de `clk_released` e do **mesmo tap 80 `rc8464`**. Assim, C131 é o caminho capacitivo direto entre as saídas. O tap comum, os acoplamentos pelas bitlines/latches e a alimentação são caminhos indiretos. Na coluna 3, PRECH chega aos PMOS X1352/X1645 e ao equalizador X374. É preciso manter a ordem de corrente entre X351 e esses dispositivos. Os 126–127 ps observados no recorte no marcador de 1 µA são uma referência diagnóstica. [Conectividade RTL](../physical/phase2/macro_binding.v) · [Topologia verificada no PEX](../build/phase3/sclk_v2_integration_preflight_20261121/final/manifest.json)

## Alimentação

O v2 ainda não tem pontos de conexão VDD/VSS definidos em layout. O recorte liga a alimentação do driver ao VDD/VSS ideais da bancada e reproduz a tensão de retorno do tail em `rc5874`. Portanto, o driver não injeta sua corrente transitória na malha real. Como referências de localização elétrica, o latch 3 usa `rc1713/rc3090` em VDD e o tail usa `rc5874` em VSS. A pré-carga 3 usa `rc1935/rc1937`. Os acionadores centrais têm, por exemplo, `rc2927/rc5423` (SCLK) e `rc2916/rc5401` (PRECH). Esses nós têm caminhos nativos verificados até os pinos públicos. A ligação real do v2 deve ser estabelecida antes de decidir quais deles podem servir como portas de uma redução.

A malha VDD tem **3.054 nós e 6.350 R**. VSS tem **2.721 nós e 6.943 R**. A solução linear em DC usou os cartões R originais e fixou somente o pino público como referência. Diagnósticos de autoimpedância no terminal VDD de X1267 do latch, no terminal de X1352 e no terminal de X614 do acionador de SCLK são **169,10 Ω**, **127,90 Ω** e **354,37 Ω**. Em VSS, `rc5874` tem **23,09 Ω**, `rc5423` tem **8,04 Ω** e `rc5401` tem **8,30 Ω**. Os valores se referem a terminais do PEX, incluindo a resistência local de contato. O menor caminho R de `rc5874` ao pino vale 45,77 Ω. Os caminhos paralelos explicam a diferença.

A transferência resistiva entre o retorno do tail 3 e os outros tails varia de **11,93 a 13,13 Ω** na mesma matriz. Em VDD, a transferência entre os terminais de X1267 e X1352 é **17,76 Ω**. Entre os retornos dos acionadores centrais SCLK e PRECH, a transferência VSS é **2,20 Ω**. Isso comprova compartilhamento DC, com valores condicionados ao ponto de injeção. A extração contém **3.054 cartões C entre grupos VDD/VSS**, somando cerca de **9,91 pF**, além de capacitores para sinais. Fixar o rail local eliminaria a troca de carga com essa rede. A soma dos C distribuídos e a matriz DC não fornecem a impedância transitória no ponto do v2 nem a resposta às correntes simultâneas da macro. [Caminhos resistivos e referência de sonda](../build/phase3/sclk_v2_integration_preflight_20261121/final/supply_paths.csv) · [Matrizes DC e C incidentes](../build/phase3/sclk_v2_integration_preflight_20261121/final/manifest.json)

## Fronteira proposta e terminações

O menor núcleo a considerar parte do recorte funcional de sense 3, mantém ativos os acionadores nativos de SCLK/PRECH e seus caminhos compartilhados, liga o v2 somente em R87 e conserva as duas redes distribuídas com suas placas de acoplamento. A matriz de armazenamento, a escrita e o datapath das demais colunas só poderiam ficar fora se suas portas entregassem a carga dinâmica e o histórico necessários à pergunta elétrica. A opção compacta independe de recriar o datapath completo. Sua equivalência de fronteira continua em aberto.

| Fronteira | Nó PEX e elementos a preservar | Omissão ou modelo | Classe e alcance |
|---|---|---|---|
| Ponto de inserção e carga local | rc8562 → v2 → R87 → rc8571 e R68/R60/R76, gates X235/X521/X351, C locais | Troca do acionamento direto somente neste ramo | `EXACT` na conectividade do ramo e cartões passivos do PEX. A posição física de alimentação ainda é uma fronteira distinta |
| Acionamento e controle comuns | rc8562/8563, acionador SCLK, rc8464, rc8512, acionador PRECH e C131 | Preservar a lógica nativa até portas justificadas. As tensões exatas de entrada e suas impedâncias ficam sem modelo | `UNRESOLVED` nas entradas e realimentação compartilhada. O replay de rc8605 em rc8562 já usado no recorte é um proxy |
| Carga local de bitline e regeneração | rc8202/8216, rc5990, rc8022, rc7187 e componentes do sense 3 | Replay histórico de BL/BLB, omissão da impedância ativa do array | `JUSTIFIED_EQUIVALENT` somente para reprodução funcional no recorte TT validado. Resposta incremental da matriz e realimentação em uma integração permanecem `UNRESOLVED` |
| Cargas das outras sete colunas | 21 gates nos outros ramos de SCLK, mais BL/BLB, latch e rails nos terminais ativos | Futuro modelo de carga por ramo, dependente da fase e preservando portas de acoplamento | `UNRESOLVED`. Um total de C perderia a distribuição, o estado dos MOS e o acoplamento de retorno |
| Pré-carga local e compartilhada | rc8467, R188, rc8489/8490/8491, trio de PMOS da coluna 3, C131 e malhas de rail | Manter acionador ativo e portas dos outros sete ramos de pré-carga; cargas ativas omitidas ainda sem equivalente | `UNRESOLVED` para verificar a ordem de desativação sob carga |
| Alimentação e retornos | VDD/VSS públicos, portas nativas de sense/prech e futuro tie do v2 | Rede DC rastreada. Equivalente RC multiporta com carga restante somente após definir e validar as portas | `UNRESOLVED`. A redução atual não tem ponto físico do v2 nem dados de corrente/impedância incremental para qualificação |
| Demais placas acopladas aos controles | 65 grupos resistivos externos incidentes a SCLK/PRECH | Nenhuma terminação nova aplicada. Identidade e observabilidade inventariadas | `UNRESOLVED` para as placas omitidas. Há tensão arquivada em algum nó de 39 grupos, com só um grupo sondado numa placa exata |

O número 65 contabiliza apenas os grupos externos imediatamente incidentes às duas redes de controle. Preservar cones a montante e terminais dependentes de estado pode aumentar o número de portas. Tensão observada em outro ponto resistivo é um proxy. Mesmo uma tensão observada na placa exata não revela a corrente incremental quando a carga muda. O recorte anterior passou a 840 MOS e 252 grupos sem modelo ao expandir a malha. A auditoria atual não fechou placas com fontes ou terra e não reproduziu o caso de VCUT205. [Mapa de grupos](../build/phase3/sclk_v2_integration_preflight_20261121/final/frontier_inventory.csv) · [Histórico do recorte carregado](phase3_reconstrucao_recorte_sclk_tt_20261120.md)

## Alcance, veredito e próxima decisão

1. **Bancada compacta.** Há um núcleo defensável, com fronteiras críticas pendentes. O estado é `COMPACT_BOUNDARY_PARTIALLY_DEFINED`.
2. **SCLK.** Rotas, acoplamentos e acionador físico têm base para representação distribuída. A carga dinâmica em cada ramo e as entradas compartilhadas ainda bloqueiam a equivalência.
3. **Alimentação.** O compartilhamento e as resistências em DC estão demonstrados. As conexões físicas do v2, impedância transitória e correntes omitidas ainda impedem estimar queda de alimentação da integração.
4. **PRECH.** O PEX identifica o caminho direto, o tap compartilhado e os retornos. Preservar esses caminhos permitiria testar a ordem X351/PRECH com as correntes nativas. O recorte de 59 ns sozinho fixa as formas de onda externas que poderiam responder à mudança.
5. **Outros sete senses.** Uma redução qualificada de carga permitiria observar perturbações de acionamento e rails. Correção funcional dos outros senses exige representar sua regeneração e as entradas de leitura, fora do escopo dessa redução.
6. **Contraste v2.** Adiar. O único dado que justificaria retomar é uma referência dinâmica multiporta na fronteira agrupada, com as portas físicas de alimentação do v2 definidas, que inclua SCLK, PRECH e os retornos sob mudanças representativas de carga. Os waveforms atuais não fornecem essa resposta incremental. Até lá, preservar o resultado funcional do recorte e suspender a integração, sem expandir novamente a bancada.

C permanece como referência, com `FAIL` em TT, `PASS` em SS no escopo ensaiado e FF pendente. SNM `tt_mm` concluído no domínio experimental, com homologação pendente. Qualificação geral `NOT_CHARACTERIZED`, Liberty pendente. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.

Três testes de software verificaram ramificação real e a matriz DC com retorno comum e caminhos paralelos. Duas gerações produziram inventários idênticos byte a byte. A análise gera inventários, sem escrever deck ou tocar no PEX. [Testes](../build/phase3/sclk_v2_integration_preflight_20261121/tests.log)

```sh
out=$(mktemp -d build/phase3/sclk_v2_integration_check.XXXXXX)
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/tools \
  python3 /work/tools/audit_phase3_sclk_v2_integration.py "/work/$out"
```
