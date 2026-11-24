# Fase 3 — auditoria de entrada do ECO virtual com oito StrongARM

**Estado em 24/11/2026:** C250 virtual aprovado em TT/SS/FF. A regressão integrada TT completou os dados dos 18 ciclos e foi complementada por witness de payload estático. Em SS, dados também passaram, mas o checker de ownership ficou inconclusivo no read→idle do bit 6. O mesmo gap foi reproduzido no controle SS original v6 sem ECO virtual. FF integrado não foi executado. Qualificação elétrica continua `NOT_CHARACTERIZED`.

## Referências seladas

O controle é a macro híbrida v6. A auditoria usa a cópia recuperada em `integration/phase3-danilo-ss` no commit-base `8e1d961d65054b59f9032ed5f9338d9ee4353c33` e os artefatos do pacote `phase3_triple_strongarm_20261122.zip`.

| Vista | SHA-256 |
|---|---|
| GDS v6 | `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` |
| PEX distribuído v6 | `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` |
| Binding C250 TT/SS | `3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d` |
| Fixture C250 | `f92bfbadd3c7af8ef4309884613258608657b00f5fa9a8ce371f0c4d4c00533d` |

Os recibos em `build/phase3/strongarm_functional_closure_20261122/results.json` registram C250 `PASS` em TT, SS e FF; a regressão integrada de 18 ciclos continua `NOT_RUN` nos três corners. A qualificação elétrica permanece `NOT_CHARACTERIZED`.

## Conexões por lane

Os nós abaixo vêm do mapa C250, cuja identidade aponta para o GDS/PEX v6 acima. Os nomes `SA` e `SAB` são as rotas de saída antigas até mux/captura; no ECO virtual elas serão acionadas pelas saídas dos dois buffers. `D` e `Q` vêm do mapa integrado congelado. Os pnodes são identificadores deste binding e não devem ser reutilizados com outra extração.

| Bit | BL | BLB | SCLK local | VDD/VSS local | SA/SAB rota | NTAIL legado | D/Q captura | MOS nativos a remover |
|---:|---|---|---|---|---|---|---|---|
| 0 | `pnode8188` | `pnode8200` | `pnode8801` | `pnode1729` / `pnode6038` | `pnode6156` / `pnode8382` | `pnode6706` | `pnode6506` / `pnode6601` | `X508 X827 X1096 X1213 X1214 X1318 X1496` |
| 1 | `pnode8212` | `pnode8224` | `pnode8768` | `pnode1731` / `pnode6040` | `pnode6151` / `pnode8388` | `pnode6863` | `pnode6509` / `pnode6611` | `X63 X241 X261 X882 X1298 X1732 X1734` |
| 2 | `pnode8402` | `pnode8414` | `pnode8771` | `pnode1733` / `pnode6042` | `pnode6143` / `pnode8418` | `pnode7133` | `pnode6511` / `pnode6512` | `X824 X1072 X1358 X1491 X1492 X1614 X1778` |
| 4 | `pnode8432` | `pnode8444` | `pnode8780` | `pnode1735` / `pnode6046` | `pnode6130` / `pnode8448` | `pnode7501` | `pnode6527` / `pnode6643` | `X105 X283 X1070 X1337 X1656 X1773 X1774` |
| 5 | `pnode8260` | `pnode8272` | `pnode8783` | `pnode1737` / `pnode6049` | `pnode6119` / `pnode8454` | `pnode7653` | `pnode6528` / `pnode6654` | `X78 X404 X532 X533 X658 X836 X1590` |

Cada conjunto de sete foi identificado pela conectividade resistiva no binding: dois PMOS de regeneração, dois NMOS de latch, dois PMOS de amostragem BL/BLB e um NMOS de cauda. Os conjuntos são disjuntos. Isso confirma cinco lanes nativas completas e evita selecionar MOS de precharge, write-driver ou mux por proximidade de nó.

## Inventário de carga disponível

`physical/extracted_loads.json` compara o PEX C original com o PEX físico v6. Os valores são capacitâncias explícitas incidentes em grupos de nós conectados por resistores; não incluem capacitâncias intrínsecas dos MOS nem o efeito temporal da distribuição RC.

| Bit | BL C/v6 (fF) | BLB C/v6 (fF) | BL+BLB C/v6 (fF) |
|---:|---:|---:|---:|
| 0 | 55,7823 / 55,7823 | 56,3771 / 56,3771 | 112,1593 / 112,1593 |
| 1 | 56,1856 / 56,1856 | 56,1341 / 56,1341 | 112,3197 / 112,3197 |
| 2 | 57,5183 / 57,5183 | 58,2078 / 58,2078 | 115,7261 / 115,7261 |
| 4 | 61,8671 / 61,8496 | 62,9944 / 62,9966 | 124,8614 / 124,8462 |
| 5 | 64,2505 / 64,2505 | 65,5082 / 65,5082 | 129,7587 / 129,7587 |

No mesmo inventário, a capacitância explícita incidente no SCLK compartilhado é `134,40188 fF` em C e `151,20699 fF` em v6; o acoplamento explícito SCLK–PRECH é `7,54814 fF` em ambas. A v6 mede três StrongARM físicos. Esses números **não estimam** o acréscimo das cinco células restantes.

No ECO virtual, cada sense nativo de sete MOS dá lugar a um núcleo StrongARM de onze MOS e dois buffers `sky130_fd_sc_hd__buf_1` de quatro MOS cada. O modelo acrescenta 60 MOS ao binding, contando as definições dos dez buffers, mas não fornece a geometria nem os parasitas extraídos das cinco novas células. As placas RC antigas ficam como envelope comparável das rotas e serão substituídas pelo PEX da geometria física se o ECO avançar.

## Resultado C250 virtual e integrado TT

O primeiro deck foi descartado antes da execução: ligava os buffers aos pontos errados. A revisão confirmou que SA/SAB precisam de nós internos virtuais independentes; as saídas dos buffers retornam às rotas de saída SA/SAB legadas, enquanto D/Q permanecem pontos de captura downstream. O gerador foi corrigido com esse corte.

O preflight confirmou a remoção exata dos 35 MOS nativos, a inclusão de 55 MOS de núcleo e dez instâncias `buf_1`, e delta líquido de 60 MOS. Os 29.054 cartões R/C permanecem byte a byte idênticos e na ordem original. A bancada mantém estímulos e 250 ns; instrumenta BL/BLB, SCLK, NTAIL, SA/SAB do núcleo e rotas dos buffers, DI internos, D/Q de captura e correntes de tail/reset. O manifesto sela entradas e saídas do deck.

Os C250 virtual foram simulados e analisados em TT, SS e FF. Os três recibos registram `COMPLETED`, parada em 250 ns, fechamento de 319/319 hashes e observadores funcionais `PASS`. Isso permanece uma comparação exploratória sobre o envelope RC v6; os MOS e buffers virtuais não têm PEX próprio.

### Regressão integrada de 18 ciclos — TT

O replay foi preparado em `build/phase3/strongarm_eight_integrated_20261124/TT`, sobre a fixture imutável de 18 ciclos e o GDS/PEX v6 selado. O binding híbrido combina os três StrongARM físicos v6 (bits 3, 6 e 7) com os cinco StrongARM virtuais dos bits 0, 1, 2, 4 e 5. A simulação preserva a bancada de 370 ns e passo máximo de 25 ps.

O ngspice 44.2 concluiu em 1769,0 s, retorno 0, sem erros e com os 319 hashes de modelo conferidos. SHA-256 do waveform: `38f5db9a5f7d659bd470820c448c7579b2f81403d96eb4ed67e1ff559d60cc8b`. O observador integrado encontrou 18/18 ciclos de dados em `PASS`; as nove leituras tiveram D, Q e DATA corretos e 72/72 lanes aprovadas. Palavras medidas: `AA`, `55`, `55`, `AA`, `55`, `AA`, `0F`, `F0`, `F0`.

O resultado bruto agregado permanece `INCONCLUSIVO`: ownership passou em 17/18 ciclos; no primeiro write (ciclo 2), o checker não encontrou witness de corrente de carga para bits 4 e 7. A evidência paralela não aponta contenção: `overlap=false`, saída do host fraco desligada, gates desabilitados e sufixos de corrente quietos nos oito bits. A análise suplementar demonstra que DATA4 e DATA7 já estavam no nível esperado e estáveis, então não havia transição de payload a carregar. O witness suplementar fecha esse caso sem reescrever o resultado bruto; não é falha funcional.

O observer integrado bruto de TT não fechou todos os critérios; o witness suplementar justificou os dois bits sem transição e permitiu avançar para SS. Evidências derivadas: `simulation.json`, `analysis.json`, `cycles.csv`, `historical_observer.json`, `revised_ownership.json` e `static_payload_witness.json` sob o diretório TT acima. O observer foi executado com `tools/run_phase3_integrated_review_compat.py`, que fornece compatibilidade para Python 3.10/NumPy 1.26 sem alterar a lógica do analisador.

O checker original fica `INCONCLUSIVO` porque não reconhece bits estáticos como witness suficiente; o arquivo adicional `static_payload_witness.json` registra os níveis de DATA, limites lógicos e isolamento medidos. O suplemento não altera `analysis.json` nem substitui o observer histórico; apenas demonstra que não houve transição de payload a exigir corrente nos bits 4 e 7.

### Regressão integrada de 18 ciclos — SS e controle baseline

O replay virtual SS completou 370 ns em 1695,4 s, retorno 0, sem erros e com 319/319 hashes de modelo conferidos. SHA-256 do waveform: `2196c890c255b792f4dbd8c0aed013f04cd865718741da4ddc2982ea266cfd8d`. Os 18 ciclos de dados passaram e as nove leituras tiveram 72/72 lanes aprovadas. O resultado agregado do observer é `INCONCLUSIVO`: ownership passou em 17/18 ciclos; no ciclo 12 (`read_to_idle`), não houve witness de condução fraca no DATA6. A liberação final foi observada, sem overlap classificado pelo checker.

Para atribuir esse gap, a fixture original v6 — três StrongARM físicos nos bits 3, 6 e 7 e cinco sense nativos — foi preparada e simulada em SS, sem o ECO virtual. O controle completou 370 ns em 1665,2 s, retorno 0, sem erros e com os mesmos 319 hashes. SHA-256 do waveform: `ed57f28599a99c00661cc6dfb45bff0d1c190a5445b8e406859e14d6be083654`. O mesmo ciclo 12/bit 6 ficou `INCONCLUSIVO`, com liberação verificada e sem witness de condução; os nove ciclos de leitura também passaram 72/72 lanes.

No instante de desabilitação, o candidato mediu DATA6=1,4934 V, TE_B=0,0882 V, corrente weak-host=306,6 µA e corrente DUT=−367,8 µA; o controle v6 mediu DATA6=1,4960 V, TE_B=0,0888 V, 304,0 µA e −365,4 µA. A semelhança e o mesmo ciclo/bit inconclusivo indicam que a lacuna do witness precede o ECO virtual; isso não demonstra que o handoff esteja eletricamente qualificado. Evidências do controle: `build/phase3/strongarm_functional_closure_20261122/integrated/SS/`.

O suplemento de payload estático aplicado a SS não resolveu esse segundo tipo de witness: `static_payload_witness.json` retorna `INCONCLUSIVE` e não adiciona classificação para read→idle. Por isso, FF integrado não foi iniciado. A próxima ação é fechar o contrato de ownership para a transição read→idle com witness de condução observável, sem dispensar o requisito de propriedade do barramento; então repetir SS e avançar FF somente após o gate SS aprovado.

Para reproduzir os decks virtuais, no checkout recuperado:

```bash
python3 tools/phase3_prepare_virtual_eight_integrated.py --corner tt
python3 tools/phase3_prepare_virtual_eight_integrated.py --corner ss
```

No host, executar cada transiente serialmente no container isolado:

```bash
docker exec -w /work sram-phase3-eight-strongarm \
  python3 build/phase3/strongarm_triple_20261122/run_once.py \
  build/phase3/strongarm_eight_integrated_20261124/TT --stop-ns 370 --timeout 7200
```

Troque `TT` por `SS` para o segundo run. Para analisar, dentro do container:

```bash
python3 tools/run_phase3_integrated_review_compat.py \
  build/phase3/strongarm_eight_integrated_20261124/TT
python3 tools/phase3_audit_integrated_no_transition.py \
  build/phase3/strongarm_eight_integrated_20261124/TT
```

O controle baseline foi preparado com `python3 tools/run_phase3_integrated_deck_compat.py SS` e executado pelo mesmo `run_once.py`, com destino `build/phase3/strongarm_functional_closure_20261122/integrated/SS`.

Para reproduzir o preflight sem sobrescrever a saída existente, use outro diretório vazio:

```bash
python3 tools/phase3_prepare_virtual_eight_strongarm.py \
  --checkout /tmp/phase3-v6-handoff-20261122/historical-checkout \
  --output /tmp/phase3-v6-handoff-20261122/historical-checkout/build/phase3/strongarm_eight_virtual_20261123/TT
```

O estado `VIRTUAL_ECO_READY` confirma somente topologia e integridade estrutural do deck; não é resultado de ngspice. Os buffers usam o subcircuito arquivado `buf_1`; a capacitância e o acoplamento dos dispositivos inseridos não foram extraídos.

## Contrato de caracterização virtual

1. Usar o binding C250 v6 com a fixture TT selada; manter exatamente os mesmos estímulos, 250 ns, 1,8 V, 27 °C, carga de 10 fF/bit, slew de 50 ps, Gear/KLU e passo máximo de 25 ps. Para SS/FF, alterar somente a seção de modelo e registrar o manifesto de modelo conferido.
2. Remover somente os 35 MOS listados na tabela. Preservar cada cartão R/C e cada MOS não selecionado, byte a byte.
3. Instanciar em cada lane o StrongARM de referência `strongarm_tt_v0` com BL, BLB, SCLK local e rails da tabela. Usar nomes exclusivos para SA/SAB, DI_BL e DI_BLB do core. Reutilizar o NTAIL legado como terminal de cauda no modelo virtual.
4. Ligar SA/SAB do core às entradas de dois buffers não inversores; ligar as saídas desses buffers às rotas SA/SAB legadas. D/Q continuam downstream e não são o destino dos buffers.
5. A bancada instrumenta os nós diferenciais, clocks, rotas, captura, corrente de tail/reset; mantém os oito DATA e marcadores de propriedade do barramento e os probes da matriz.
6. O gerador valida hashes do PEX, binding, fixture e fonte StrongARM, inventário removido/inserido, cartões inalterados e diretório de saída novo. O primeiro run valida resolução dos vetores hierárquicos e hash da closure de modelos dentro do container.

Os pnodes continuam válidos apenas para o binding C250 TT derivado do PEX v6. Não copiar pnodes numéricos de outro corner, PEX ou variante.

## Limite deste gate

Embora o candidato tenha passado a comparação C250 TT/SS/FF, isso é evidência exploratória. Os dados funcionais integrados TT/SS passaram, mas os observers brutos de ownership permanecem inconclusivos; FF integrado, DRC/LVS do ECO, PEX físico dos cinco senses adicionados, seleção arquitetural final e qualificação elétrica permanecem pendentes. A geometria física de oito senses exige novos GDS/LEF/PEX e validação independente.

O container original `sram-xschem` permanece parado e montado no checkout `develop`. A instância isolada `sram-phase3-eight-strongarm` usa a imagem local `sha256:60ee83416df692d1dfc68aef79252ad6acd512c459ff63a0e075e908941a8650`, montada no checkout recuperado. O runner integrado conferiu 319 hashes no TT. A qualificação elétrica permanece `NOT_CHARACTERIZED`.
