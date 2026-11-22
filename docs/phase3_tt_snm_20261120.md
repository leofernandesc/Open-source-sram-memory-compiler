# Fase 3 — Validação integrada TT e auditoria Monte Carlo de SNM

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
O escopo é a SRAM 4×8 e a bitcell 6T esquemática. A condição nominal é o
ponto de bancada de 27 °C. A especificação deixa a temperatura nominal
do produto para confirmação. [Especificação técnica, §§7 e 20](../specs/technical_specification.md)

## A. Validação integrada TT

### Identidade e preflight

A execução usa a geometria espaçada da integração de Danilo
(`42f0b51` como origem do ECO), com o PEX padrão selado de 16.187
resistores. O preflight revalidou os hashes da preparação SS, a
cadeia física já arquivada e a cobertura da fixture. GDS, LEF,
Verilog roteado, PEX, binding, carga, sondas, fixture e controles
são os mesmos. O diff do deck tem uma única troca, a seção
`ss` por `tt` na diretiva `.lib`. A seção `tt` do modelo
instalado deixa mismatch e processo aleatório desligados.

| Entrada | SHA-256 |
|---|---|
| GDS | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| Verilog roteado | `eafcca0a89d53392e8cc1bbe380e87df8f4479f58a04a5132d62e2246d1a74a1` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Fixture integrada | `f92bfbadd3c7af8ef4309884613258608657b00f5fa9a8ce371f0c4d4c00533d` |
| Modelo raiz ngspice | `5efa041a988893c1a3580d0ecd57870ea3146b27741c7d42b56baaa336b9549e` |

Condições TT/1,8 V/27 °C, 10 fF por bit, período de 20 ns, fase alta
de 10 ns, slew de 50 ps, passo máximo de 25 ps e horizonte de
370 ns. O simulador é ngspice 44.2 com KLU em um CPU. A fixture
tem nove leituras, seis escritas, três ciclos inativos e cobre os
quatro endereços. A guarda experimental de 1,5 ns permanece fixa.
[Preparação TT](../build/phase3/integrated_tt_20261120/preparation.json)

O analisador de operação confere endereço, wordline, sense, D, Q,
escrita/readback e palavra estável. A propriedade é julgada pelo
observador revisado, com corrente e polaridade por ramo, tensão
no pino e estado do driver, exigindo ≥3 amostras nativas e ≥50 ps
de continuidade. Em SS, exigir 100 ps em vez de 50 ps deixa quatro
bits inconclusivos em cada um dos ciclos 8, 10 e 12 sob sonda.
Esse teste de sensibilidade permanece à parte. A janela diagnóstica
de ±100 ps não estabelece um prazo público de leitura. A regra de
direção exige liberação efetiva antes de dirigir DATA. A guarda e os
limiares de instrumentação são parâmetros de bancada.
[Contrato temporal, §6](../specs/sram_4x8_timing_contract.md#6-troca-de-direção-do-barramento) · [Integração SS](phase3_validacao_integrada_ss_20261119.md) · [Reanálise SS](phase3_fechamento_barramento_ss_20261120.md)

Comandos do preflight e da tentativa autorizada:

```bash
run=build/phase3/integrated_tt_20261120
timeout 120s tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/run_phase3_integrated_tt.py prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/run_phase3_integrated_tt.py simulate --output "$run" --timeout 2700
```

### Resultado — VERIFIED, com FAIL funcional

Uma tentativa executou os **370 ns** e gerou **22.730 amostras** em
**41 min 13 s**. O ngspice retornou 0. A saída tem SHA-256
`2125aae7f92e94e81ca686c0519be5695ba72f370c0f7b0bcfefc8875a0cd1fd`.
As análises de operação e de propriedade retornaram 1. O veredito
integrado revisado é **FAIL**. A qualificação elétrica geral continua
`NOT_CHARACTERIZED`. [Recibo da simulação](../build/phase3/integrated_tt_20261120/simulation.json) · [Observador de propriedade](../build/phase3/integrated_tt_review_20261120/review.json)

| Verificação | TT | SS, referência |
|---|---:|---:|
| Palavras esperadas estáveis e sense/D/Q corretos | 7/9 | 9/9 |
| Captura de dados de escrita antes de WE20 | 48/48 bits | 48/48 bits |
| Escritas confirmadas por readback | 5/6, três linhas | 6/6, quatro linhas |
| Endereços exercitados | 4/4 | 4/4 |
| Operações | 15 PASS, 2 FAIL, 1 INCONCLUSIVO | 18 PASS |
| Propriedade com o observador revisado | 15 PASS, 3 INCONCLUSIVO | 18 PASS |
| Contenção forte sustentada comprovada na sequência legal | 0 | 0 |
| Janela diagnóstica ±100 ps | 70/72, DATA3 em c16/c17 | 65/72, DATA7 |
| Desde CLK↓50, nas seis transições de palavra aprovadas em ambos | 0,589–0,617 ns | 0,875–0,911 ns |

Tabela completa de TT. Os tempos depois de CLK↑50 e CLK↓50
referem-se ao início da palavra **completa** e válida antes da
sonda. A última coluna mostra a latência após a descida em SS. A
escrita mostra a palavra capturada em DIN. O readback de c5 não foi
confirmado, embora DIN esteja correto.

| Ciclo | Operação | End. | Esperado → observado | Operação TT | Propriedade TT | TT após ↑ / ↓ (ns) | SS após ↓ (ns) | Janela TT |
|---:|---|---:|---|---|---|---|---:|---:|
| 0 | Idle | — | — | PASS | PASS | — | — | — |
| 1 | Idle | — | — | PASS | PASS | — | — | — |
| 2 | Escrita | 0 | AA → AA | PASS, c6 confirma | INCONCLUSIVO | — | — | — |
| 3 | Escrita | 1 | 55 → 55 | PASS, c7 confirma | PASS | — | — | — |
| 4 | Escrita | 2 | 0F → 0F | PASS, c15 confirma | PASS | — | — | — |
| 5 | Escrita | 3 | F0 → F0 | INCONCLUSIVO no readback | PASS | — | — | — |
| 6 | Leitura | 0 | AA → AA | PASS | PASS | 10,617 / 0,617 | 0,911 | 8/8 |
| 7 | Leitura | 1 | 55 → 55 | PASS | PASS | 10,591 / 0,591 | 0,875 | 8/8 |
| 8 | Escrita | 0 | 55 → 55 | PASS, c9 confirma | PASS | — | — | — |
| 9 | Leitura | 0 | 55 → 55 | PASS, sem comutação | PASS | — | — | 8/8 |
| 10 | Escrita | 1 | AA → AA | PASS, c11 confirma | PASS | — | — | — |
| 11 | Leitura | 1 | AA → AA | PASS | PASS | 10,617 / 0,617 | 0,911 | 8/8 |
| 12 | Idle | — | — | PASS | PASS | — | — | — |
| 13 | Leitura | 0 | 55 → 55 | PASS | PASS | 10,592 / 0,592 | 0,875 | 8/8 |
| 14 | Leitura | 1 | AA → AA | PASS | PASS | 10,617 / 0,617 | 0,911 | 8/8 |
| 15 | Leitura | 2 | 0F → 0F | PASS | PASS | 10,589 / 0,589 | 0,875 | 8/8 |
| 16 | Leitura | 3 | F0 → F8 | **FAIL** | INCONCLUSIVO | — | 0,911 | 7/8 |
| 17 | Leitura | 3 | F0 → F8 | **FAIL** | INCONCLUSIVO | — | — | 7/8 |

Nas seis leituras comparáveis com comutação, TT antecipou a
palavra estável em **0,283–0,294 ns**. Em c9, a palavra repetida
`0x55` foi confirmada estável após a captura local até a sonda,
de 200,067 a 201,500 ns em TT. Sem transição observável do dado,
`tACCESS` e a latência a partir da descida ficam sem valor.
Os tempos observados são provisórios e não fixam Fmax nem um
limite público. [Tabela de dados e janelas TT × SS](../build/phase3/integrated_tt_comparison_20261120/cycles_tt_vs_ss.csv)

### Classificação das divergências

**Defeito funcional em c16/c17, linha 3, bit 3.** A linha e o
endereço registrados estavam corretos. O primeiro estágio
com resultado lógico errado é a **resolução do sense**. Nos
dois ciclos o sense está em 1,798 V e D em aproximadamente
1,803 V na captura local, em 340,058 ns e 360,058 ns. Q e o
pino ficam em aproximadamente 1,800 V na janela de leitura
sem o host, quando o esperado era 0 V. A saída errada permanece
até a observação antes da sonda. O segundo FAIL também recebe
a etiqueta de retenção pelo analisador, que conservou a última
palavra integral aprovada como referência. A inspeção de c17
demonstra o mesmo erro em sense/D do bit 3, sem evidência de uma
segunda causa independente em Q. Os dois FAILs diagnósticos
correspondem ao erro lógico, sem demonstração de um novo prazo
normativo violado.

| Ciclo/corner | WL80 da sonda da linha 3 (ns) | SCLK20 local bit 3 (ns) | SCLK20 − WL80 (ps) | BLB−BL a −50 ps de SCLK20 (mV) | BLB−BL em SCLK20 (mV) | Sense em captura |
|---|---:|---:|---:|---:|---:|---|
| c16 TT | 334,197 | 334,154 | −42,8 | −3,9 | +15,8 | Errado, 1 |
| c17 TT | 354,190 | 354,154 | −35,5 | −2,0 | +20,8 | Errado, 1 |
| c16 SS | 336,151 | 336,266 | +114,4 | +77,4 | +122,3 | Correto, 0 |
| c17 SS | 356,143 | 356,268 | +125,6 | +88,0 | +134,0 | Correto, 0 |

Em TT a ordem relativa das referências muda. No início da rampa
local do sense, o diferencial correto é menor e a WL medida
ainda está entre 1,25 V e 1,28 V. Mais tarde, as bitlines já
mostram o sentido esperado, mas o par do sense resolve para o
estado errado. Esse é um indício forte de insuficiência de
margem na avaliação/regeneração relativa a WL, com dependência
da coluna e do padrão. SCLK20 é uma referência de medição da
rampa, e a sonda de WL é da linha, sem medir o gate da bitcell
específica. As evidências atuais não separam completamente
controle, parasitas diferenciais, offset do sense e o estado
armazenado. No c5, DIN do bit 3 está correto antes de WE20 e,
com WL ativa, BL3/BLB3 estão próximos de 0/1,8 V de 115 ns até
perto do fim da fase alta. Os nós de armazenamento da bitcell
da linha 3 e coluna 3 não estão no waveform. Portanto a escrita
interna de c5 fica **inconclusiva**, mesmo com entradas corretas
e indícios de desenvolvimento de diferencial no sentido
esperado. [Trilha por estágio](../build/phase3/integrated_tt_comparison_20261120/read_path_tt_ss.csv) · [Timeline DATA3 e escrita](../build/phase3/integrated_tt_comparison_20261120/data3_timeline.csv)

**Limitações de medição de propriedade.** Nos ciclos 16 e 17,
a sonda fraca aplica o complemento da palavra esperada. No bit
3 esse nível coincide com o bit incorreto efetivo. TE_B está
ativo, mas a sonda mede só cerca de 0,32 µA, sem a oposição
necessária para certificar drive pelo método. A liberação após
a máscara foi comprovada. No ciclo 2, DATA4 e DATA7 já estavam
nos níveis esperados quando o host forte ligou. Houve corrente
na macro de cerca de 53 e 52 µA na primeira amostra, com
`TE_B` em aproximadamente 1,799 V. O pulso decaiu abaixo do
piso em menos de 5 ps. É compatível com acomodação de carga,
mas não satisfaz a prova de comutação entre níveis exigida
pelo observador. O caso fica INCONCLUSIVO, sem contenção
sustentada comprovada. Nos handoffs de leitura para escrita
c8 e c10, os oito bits foram liberados com margens observadas
de pelo menos 0,933 e 0,926 ns, respectivamente. A condição de
100 ps em TT não adicionou inconclusivos de condução além de
DATA3 em c16/c17. A regra de 50 ps e o controle negativo SS
de 300 ps permaneceram inalterados. [Pulso do ciclo 2](../build/phase3/integrated_tt_comparison_20261120/tt_cycle2_switch.csv)

Reprodução offline com os recibos e waveforms arquivados. Os
diretórios de saída dos analisadores precisam ser novos.

```bash
# Em cópia da tentativa TT, o primeiro comando só escreve se validation.json ainda não existir.
python3 tools/analyze_phase3_integrated_ss.py build/phase3/integrated_tt_20261120
python3 tools/review_phase3_bus_ss.py build/phase3/integrated_tt_20261120 \
  --output build/phase3/integrated_tt_review_replay
python3 tools/compare_phase3_integrated_tt.py \
  --tt build/phase3/integrated_tt_20261120 \
  --tt-review build/phase3/integrated_tt_review_20261120/review.json \
  --ss build/phase3/integrated_ss_20261119_preflight \
  --ss-review build/phase3/bus_review_ss_20261120_report/review.json \
  --output build/phase3/integrated_tt_comparison_replay
```

## B. Monte Carlo de SNM — PROVISIONAL

### Inventário histórico e validade das séries

Os dois CSVs criados em `2535e81` contêm 200 registros com seeds
1001–1200, unidades V e mV coerentes e uma condição fixa por série. Os
decks do script histórico são temporários. A auditoria encontrou os
CSVs e o relatório de 8.4, sem VTCs, logs por seed ou cadeia de hashes
do PDK para os 400 registros. A revisão `c5c0ac6` substituiu
`.control setseed` por `.options seed=... seedinfo` no gerador, sem
atualizar os CSVs. O relatório histórico registra repetição idêntica
de quatro amostras. A falta desses artefatos impede verificar essa
associação entre curvas e seeds no ambiente atual. [Relatório histórico, §8.4](relatorio_validacao_bitcell_6t_sky130.md#84-monte-carlo-de-mismatch-local-triagem-de-snm)

| Série pré-layout | Condição | Linhas | Mínimo | Média | Desvio amostral | Mediana | Máximo | P05 / P95 | IC 95% da média¹ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hold | `sf_mm`, 1,62 V, −40 °C | 200 | 541,229 | 569,536 | 10,468 | 569,460 | 600,905 | 552,649 / 586,105 | 568,075–570,993 |
| Read | `sf_mm`, 1,62 V, 125 °C | 200 | 269,936 | 300,933 | 11,065 | 301,462 | 330,733 | 282,692 / 318,089 | 299,402–302,436 |

Valores em mV. ¹ Intervalo por bootstrap percentil, 10.000
reamostragens com RNG reproduzível. Descreve cada CSV sob a hipótese
de amostras independentes. A auditabilidade histórica dessa hipótese
continua pendente. [Hold histórico](../sims/bitcell_hold_snm_mismatch_sf_1p62_minus40.csv) · [Read histórico](../sims/bitcell_read_snm_mismatch_sf_1p62_125.csv) · [Gráfico e curvas piloto](../build/phase3/snm_audit_final_20261120/snm_historico_e_piloto.png)

**Reaproveitamento.** As 200 linhas de Hold e as 200 de Read servem como
triagem e comparação histórica em suas próprias condições. Nenhuma
amostra histórica foi qualificada para contar na campanha definitiva.
Os casos frescos do piloto verificam o método nos pontos históricos.
Para a proposta `tt_mm`, ainda há **0/200 por condição**. A meta de
engenharia de Read SNM ≥0,4 V refere-se ao ponto nominal determinístico
TT/1,8 V. Seu uso como limiar de aprovação de uma distribuição
`sf_mm` ou `tt_mm` exigiria uma decisão estatística adicional.
[Contrato da bitcell](../specs/sram_6t_cell.md)

### Modelo e topologia auditados

- A biblioteca usada pelos scripts históricos e pelo piloto é
  `libs.tech/combined/continuous/sky130.lib.spice` no SKY130A Volare
  `0fe599b2afb6708d281543108caf8310912f54af`. Seu SHA-256 é
  `c7e9fe87ffc2685bc56da02f92cd48b1403a5e9da85cc7978027fb0ca347d581`.
  Os manifestos do piloto registram os hashes de sua cadeia de
  includes. A biblioteca do ensaio integrado usa o wrapper
  `libs.tech/ngspice`.
- No wrapper instalado, `sf_mm` usa o corner slow-fast com
  `parameters_fet_sf.spice`, `MC_MM_SWITCH=1` e `MC_PR_SWITCH=0`.
  Em `tt_mm` os parâmetros centrais mudam para
  `parameters_fet_tt.spice` e os switches continuam 1/0. Em `sf`
  ambos estão desligados. Em `mc` o switch de processo é 1 e o de
  mismatch é 0. São distribuições condicionais diferentes.
- Em `models_fet.spice`, as expressões dos wrappers
  `nfet_01v8` e `pfet_01v8` incluem termos de limiar
  `MC_MM_SWITCH * AGAUSS(...) / sqrt(l*w*mult)` por instância.
  A variação global aciona parâmetros comuns do modelo com
  `MC_PR_SWITCH`. O piloto demonstra perturbações distintas nos dois
  lados do mesmo inversor equivalente e entre seeds. Duas realizações
  distintas testam a ativação e a reprodutibilidade do mecanismo, sem
  estabelecer a qualidade das caudas ou a independência empírica de
  toda a série de 200.
- O histórico gera as duas metades da 6T com dimensões
  WPU/WPD/WACC de 0,42/1,26/0,60 µm e L de 0,15 µm, consistentes com
  a folha canônica. Para Hold, o deck histórico **omite** os
  transistores de acesso. É uma aproximação com a célula isolada,
  sem as fugas dos transistores desligados. Em Read ambos os acessos
  estão presentes, com WL=VDD e BL=BLB=VDD mantidos por fontes ideais.
  Esse é o ponto DC de Read SNM do ensaio. A descarga dinâmica das
  bitlines e a operação integrada da macro têm verificações próprias.
  [Folha 6T](../release/phase1/cells/bitcell_6t/bitcell_6t.spice) · [Gerador histórico](../sims/run_bitcell_snm_mismatch.py)

### Borboleta e piloto reproduzido

O método usa as duas VTCs independentes, com a VTC direita espelhada,
e mede o menor dos dois maiores quadrados inscritos. O extrator
rotaciona 45°, interpola no domínio comum e encontra as interseções
que delimitam os lóbulos. Em cada lóbulo fechado maximiza a separação
na direção da diagonal. Dividir por √2 dá o lado do quadrado em V.
O extrator anterior dividia o domínio simplesmente em `u<0` e
`u>0` e usava distância absoluta. Em um teste monostável de
controle, por exemplo, retornou 0,25 V sem dois lóbulos fechados.
O novo extrator registra zero físico quando a varredura completa
demonstra uma única interseção e distingue traço incompleto,
topologia ambígua e convergência inválida. O arredondamento das VTCs
nos trilhos é tratado no limite da precisão textual, com teste
dedicado. [Seevinck, List e Lohstroh, 1987](https://doi.org/10.1109/JSSC.1987.1052809)

| Modo | Seed | Histórico (mV) | Piloto, lóbulo menor (mV) | Delta (mV) | Vtrip E / D do piloto (mV) |
|---|---:|---:|---:|---:|---:|
| Hold | 1001 | 560,026 | 571,725 | +11,700 | 602,62 / 621,71 |
| Hold | 1002 | 558,432 | 556,403 | −2,029 | 588,32 / 648,24 |
| Read | 1001 | 295,797 | 285,242 | −10,554 | 744,24 / 767,24 |
| Read | 1002 | 305,388 | 319,788 | +14,401 | 749,05 / 735,98 |

Foram feitas **cinco execuções DC por modo**. Em cada modo houve duas
seeds distintas em `sf_mm`, uma repetição exata de 1001, e seeds
1001/1002 em `sf` com os switches estatísticos desligados. Todos os
logs confirmam o número da seed e todos os sweeps têm 1.621 pontos.
A repetição teve a mesma SHA-256 das curvas. Seeds diferentes em
`sf_mm` mudaram as curvas e os pontos de inversão. Em `sf` as duas
seeds geraram curvas idênticas com SNM de 577,761 mV (Hold) e
312,029 mV (Read). Cada tentativa levou cerca de 1,4 s no ngspice
44.2. [Manual ngspice, opções SEED e SEEDINFO](https://ngspice.sourceforge.io/docs/ngspice-45-manual.pdf)

Nas dez curvas retidas, o extrator com interseções e o algoritmo
histórico no mesmo waveform diferiram menos de 0,001 mV. A comparação
offline de 1 mV com 2 mV
mudou os resultados em até 0,004 mV. Os deltas de 2 a 14 mV contra
os CSVs históricos persistem. A mudança documentada na semeadura e
a ausência de recibos originais impedem atribuir precisamente os
deltas ao PDK, à versão do simulador ou ao RNG histórico. Durante a
implementação, a classificação provisória de Hold perdeu interseções
junto aos trilhos. As dez curvas foram reavaliadas offline após corrigir
esse caso. Os logs, VTCs e a versão preliminar do analista foram
preservados junto ao resultado auditado, sem simulações extras.
[Auditoria e hashes](../build/phase3/snm_audit_final_20261120/audit.json)

### Campanha definitiva proposta, ainda pendente

1. Confirmar o domínio estatístico. A especificação exige ≥200 amostras
   de SNM e lista TT/SS/FF para caracterização geral. Ela não escolhe
   o corner estatístico nem o limite estatístico de aceitação. A
   proposta operacional inicial é separar dois lotes esquemáticos
   `tt_mm` em 1,8 V/27 °C, um Hold e um Read. Manter `sf_mm` e
   processo global como estudos separados quando forem necessários.
2. Congelar o deck derivado da folha 6T. Em Hold, WL=0 e BL/BLB em VDD
   mantêm os dois transistores de acesso modelados, com sua fuga.
   Em Read, WL=VDD e BL/BLB em VDD ideal definem o ponto de leitura
   estática. Validar as curvas iniciais em cada modo e documentar
   esses vieses antes de completar os lotes. A versão 6T canônica
   passou no preflight de software e seu piloto nominal está pendente.
   Os manifestos nominais preparados têm zero tentativas e exportam
   `NOT_CHARACTERIZED`.
3. Predeclarar 220 seeds por modo em blocos separados, por exemplo
   Hold 20001–20220 e Read 30001–30220. Uma instância de ngspice por
   seed, timeout de 60 s e lotes de até 50 limitam interferência.
   A triagem atual levou ~1,4 s por execução DC. Reservar tempo
   adicional para convergência, revalidação inicial e exportação.
4. Preservar logs, VTCs, deck, condição, seed, versão e hashes por
   tentativa. Retomar do último checkpoint e repetir somente
   falhas de execução autorizadas, com a mesma seed em nova tentativa.
   Um zero físico comprovado integra a distribuição. Uma amostra
   inválida fica registrada fora da contagem válida. Informar
   tentadas, válidas, zeros e inválidas. Encerrar com ≥200 válidas
   em cada modo, conferindo os manifestos.
5. Exportar CSV/JSON, histograma, média, desvio amostral, mínimo,
   máximo, mediana, P05/P25/P75/P95 e intervalo de confiança da média.
   Usar as borboletas para conferir casos extremos e zeros. Não
   extrapolar rendimento industrial. Para um resultado pós-layout,
   usar o PEX equivalente e validar bias local, orientação da
   bitcell e VTCs sob o caminho extraído. A campanha esquemática da
   bitcell, por si só, não atende ao escopo final para arrays 8×8 e
   32×8 nem qualifica estabilidade dinâmica.

Exemplo para a execução posterior após confirmar o domínio, começando
pelos cinco casos iniciais. Use um diretório distinto para cada modo.

```bash
mode=hold
seed_base=20001
# Para Read, use mode=read e seed_base=30001.
run="build/phase3/snm_tt_mm_${mode}_v1"
tools/sram-eda python3 tools/run_phase3_snm.py init --profile nominal-proposed \
  --mode "$mode" --seed-base "$seed_base" --count 220 --output "$run"
tools/sram-eda python3 tools/run_phase3_snm.py run --limit 5 --timeout 60 --output "$run"
# Para retomar, use o mesmo comando run em novos lotes, sem repetir init.
tools/sram-eda python3 tools/run_phase3_snm.py export --output "$run" --target "${run}_export_01"
```

Para reproduzir somente a auditoria offline a partir do pacote local:

```bash
timeout 30s tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 \
  python3 tools/audit_phase3_snm.py \
  --hold build/phase3/snm_pilot_hold_20261120 \
  --read build/phase3/snm_pilot_read_20261120 \
  --initial-sources build/phase3/snm_pilot_initial_analysis_sources_20261120 \
  --output build/phase3/snm_audit_replay
```

## C. Decisão de engenharia

1. **TT falhou funcionalmente** no endereço 3. Sete palavras
   passam, cinco escritas têm readback confirmado e não há prova
   de contenção forte na sequência legal. O escopo de propriedade
   tem três resultados inconclusivos.
2. **SS continua com 9/9 leituras, 6/6 escritas e 18/18 em
   propriedade.** TT tem saídas válidas mais rápidas nas leituras
   aprovadas em comum, com falha real do bit 3 nos dois readbacks
   da linha 3. A janela de saída e os atrasos não explicam essa
   divergência.
3. **Há um motivo técnico para investigar uma mudança**, centrada
   na avaliação de leitura. A próxima execução para resolver TT
   é um caso curto pós-layout que reproduza c5/c16 com o estado
   predecessor relevante, registrando os nós de armazenamento,
   a WL no gate da bitcell, BL/BLB nos terminais do sense e o
   pico de regeneração. Um contraste controlado com SCLK mais
   tarde, em ensaio separado, pode testar a hipótese depois de
   localizar a divergência. Critério: confirmar a palavra
   armazenada e determinar se diferencial correto anterior à
   regeneração elimina o erro sem alterar a captura. Se a
   hipótese se confirmar, comparar opções de temporização ou
   controle de leitura antes de autorizar um ECO. A variante
   NAND4BB de direção não é uma correção demonstrada para este
   defeito.
4. **As séries SNM servem para triagem.** Os dados disponíveis
   verificam a estrutura dos dois CSVs e o piloto comprova o
   funcionamento do RNG no PDK atual. Não há validação
   amostra a amostra dos 400 valores com seus traços originais.
   Nenhum entra na contagem definitiva.
5. **Hold/Read ainda precisam do domínio estatístico aprovado
   e ≥200 amostras válidas por modo.** Próxima execução
   estatística proposta, após essa decisão, são os cinco casos
   iniciais de cada lote `tt_mm` com acesso explicitamente
   modelado nos dois modos. Conferir as VTCs, zeros e checkpoints
   antes de completar os lotes. PEX de bitcell/array é uma
   extensão separada de caracterização.
6. **FF permanece pendente.** Para comparação diagnóstica com a
   candidata atual, executar uma vez a mesma fixture e o mesmo
   observador com `.lib ff`, mantendo os hashes físicos. O FF
   deve ser atribuído à geometria simulada. Se houver mudança
   de implementação depois do diagnóstico TT, a validação de
   corners da revisão corrigida deve usar os artefatos dessa
   nova revisão em comum.

**Software e escopo.** Passaram 26 testes pertinentes, sendo
11 novos para preflight TT, SNM e retomada, quatro do fixture e
do verificador integrado e 11 do observador de barramento.
`git diff --check` passou. Foram adicionados o preparador TT, a
comparação offline, o extrator de SNM, o runner de campanha,
a auditoria e a suíte nova. Fizemos uma execução integrada TT
e cinco execuções DC piloto por modo. FF, campanha completa de
SNM, ECO, nova extração, setup/hold, potência e Liberty ficaram
fora da execução. Geometria, resultados históricos e commits
permanecem preservados.

O pacote local `phase3_tt_snm_20261120.zip` contém os novos
scripts, os resultados TT, a comparação, os 10 decks/VTCs/logs
do piloto, os dois preflights nominais e os testes. A reprodução
completa usa também os pacotes anteriores, com as entradas
físicas pinadas, o waveform SS e seus controles arquivados.

| Pré-requisito de replay | SHA-256 |
|---|---|
| `phase3_validacao_integrada_ss_20261119.zip` | `2710b17f3413c3eda672fa4b269f85de5452b80acc376df0eb60a0782ae122de` |
| `phase3_fechamento_barramento_ss_20261120.zip` | `c2e07bc773f564e81a2f47627afb14d056a925bbfc64aacfbffa016178f2d1cd` |
