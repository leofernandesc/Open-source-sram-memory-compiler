# Fase 3 — Preflight de SCLK em TT e auditoria final do SNM

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
A referência temporal continua capturando a leitura na descida de CLK.
[Especificação técnica](../specs/technical_specification.md) · [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Contrato de caracterização](phase3_characterization_contract.md)

## A. Diagnóstico offline da fixture anterior

Na referência de 250 ns e na tentativa anterior, o ngspice
reportou matriz singular em `xdut.rc7913`, tentou gmin e
source stepping e concluiu o ponto de operação transiente.
Ambos usaram Gear, KLU, as mesmas tolerâncias e passo máximo
de 25 ps. A primeira intervenção estava programada para 211 ns.
Antes de 0,325 ns, a referência tem cinco registros de progresso
e 24 amostras no waveform. A tentativa interrompida tem 128
registros de progresso e nenhum waveform. A mediana do
incremento entre esses registros caiu de 59,6 para 2,11 ps.
Esses registros não correspondem aos passos internos de integração.
[Referência concluída](../build/phase3/data3_tt_20261120/simulation.json) · [Laudo da tentativa anterior](phase3_sclk_contraste_snm_20261120.md)

O adaptador anterior deslocava o terminal de R60, R68 e R76
para três nós novos e ligava cada nó à carga por uma fonte B
de tensão. Também adicionava a fonte de máscara e três de
replay. Cada fonte ideal de tensão acrescenta uma corrente
incógnita e uma equação de restrição. Com máscara zero,
as três restrições permanecem na matriz embora tenham 0 V
à direita. Com máscara um, o nó da fonte participa do
próprio comando e a equação fixa a tensão na carga.
Não foi encontrado um laço fechado de fontes ideais
de tensão. Um condicionamento pior por novas variáveis
e restrições algébricas é a hipótese principal. A malha
PWL anterior com nós do waveform também altera a lista
de eventos futuros. Sem rastreamento interno de LTE, passos
rejeitados e iterações, o mecanismo exato fica indeterminado.
As bordas da intervenção ainda não tinham ocorrido no
trecho lento. [Manual do ngspice 44, fontes independentes](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf) · [Deck anterior](../build/phase3/sclk_tt_contrast_run_20261120/sclk_fixture.spice)

O grafo resistivo indica que R80 é compartilhado pelos
oito senses, enquanto R87 (6,46438 Ω) liga a raiz de
distribuição `n0` ao ramo `n6`, que alcança somente os
gates `t17/t18/t19` do sense 3 por R68/R76/R60. Os MOS
consumidores são X235/X351/X521. A rede de distribuição
ainda contém acoplamentos físicos. O tap 80 compartilhado
com a pré-carga deve permanecer intacto.

A alteração experimental escolhida é uma única fonte
independente de corrente PWL em paralelo a R87. No
sentido raiz→ramo, o comando é `ΔV(t)/R87`, equivalente
a somar `ΔV` em série no ramo quanto à relação corrente–tensão.
Isso preserva os nós, R/C e terminais originais e acrescenta
somente injeção no vetor de correntes. A fonte é exatamente
zero na partida. Com deslocamento zero, sua contribuição
seria zero em toda a análise. O comando usa a diferença
entre a curva arquivada dos três gates transladada em 182 ps
e a curva original, com amostragem regular. O nó n6 não
foi salvo na referência. Assim, a entrega do atraso nos
três gates e a ausência de efeitos colaterais exigem
verificação no waveform.

## B. Intervenção e verificações estruturais

O candidato é a macro espaçada do ECO de Danilo, reconstruída de
`42f0b5128d7e5dde4385731e85fa504a6ee005a7`, com PEX padrão.
O preflight integrado de TT verificou 23 referências de proveniência.
O novo preflight verificou os sete artefatos preparados e três
referências de origem. Valores de identidade:

| Artefato | SHA-256 |
|---|---|
| GDS | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| PEX padrão | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| Binding original | `40f4cc2f0da257b8435bcd387b938fcaba2b7456c3a74b3b350446fd5a434fc3` |
| Waveform TT de referência | `7f6c050f11fa89a59b9b131143ba782536165bdde920b9b45259cdefd33a8646` |

Remover a nova fonte da cópia experimental recupera o binding original
byte a byte. No deck externo completo, muda somente o include. O deck
curto muda também a duração para 14 ns. Os parâmetros permanecem SKY130A
TT, 1,8 V, 27 °C, 10 fF/bit, CLK de 20 ns, slew de 50 ps e passo máximo
de 25 ps. Nenhum modelo, tolerância, estímulo ou sonda foi alterado.

A fonte contém 3.203 pontos em um único cartão lógico de 97.932 bytes
com 535 linhas de continuação. O comando só é aplicado entre 211–219
e 231–239 ns, com zero nos limites e retorno antes da desativação
programada. Seu pico de corrente de compensação é 69,336 mA, por causa
da impedância de 6,46438 Ω do ramo. Essa corrente pertence à bancada
e não é uma medida de potência da macro. A prova de isolamento é
topológica. Durante a intervenção, somente a observação do ramo a
montante, da pré-carga e dos demais senses poderia limitar efeitos
indiretos. O cálculo para atraso zero foi verificado em teste de
software. [Preflight selado](../build/phase3/sclk_r87_20261120/preflight.json)

## C. Preflight de partida

Foi executado **um** transiente curto em ngspice **44.2/KLU**, com um
CPU, no container EDA `sram-xschem`. O tempo operacional excedeu
120 s sem marcador `Reference value` no log. O monitor enviou
SIGTERM. O processo terminou com retorno `−15` após **120,305 s**.
O log tem 0 bytes e o simulador não produziu waveform. O tempo
interno simulado é desconhecido. O `0,0 ns` registrado na guarda é o
valor de decisão para progresso não observado. O monitor não chegou
à guarda de 300 s/10 ns. A comparação dos controles compartilhados
no waveform também ficou indisponível.

Na referência, o mesmo ngspice registrou a solução do ponto de operação
e o avanço do transiente até 250 ns, concluído em 1.509,703 s. Não há
marcas de tempo de parede para a inicialização no log arquivado e não
é possível comparar o tempo exato até 1 ns. Com a fonte independente,
as três restrições de tensão foram removidas, mas a instrumentação
ainda acrescenta um cartão PWL grande. Leitura e expansão do cartão,
inicialização do simulador e progresso não descarregado no log são
possibilidades. A ausência de log e de amostragem do processo impede
distingui-las. O resultado demonstra que esta fixture falhou na guarda
operacional. O log não demonstra erro de convergência elétrica.

Gate **`BLOCKED`**. Não houve segunda partida nem execução de 250 ns.
[Tentativa](../build/phase3/sclk_r87_20261120/startup/attempt.json) · [Recibo](../build/phase3/sclk_r87_20261120/startup/result.json) · [Log](../build/phase3/sclk_r87_20261120/startup/ngspice.log) · [Gate](../build/phase3/sclk_r87_20261120/startup_gate.json)

## D. Contraste TT — INCONCLUSIVO

O atraso de 182 ps foi programado, mas sua entrega aos gates não pôde
ser medida. Não há evidência nova de correção, de manutenção da falha
sob deslocamento nem de efeitos colaterais. As duas leituras históricas
continuam falhas. As marcas abaixo são do waveform arquivado, sem a
intervenção. Os cruzamentos a 20%, 50% e 80% servem para comparar
formas de onda. A corrente que indicaria o início de condução dos
samplers e do tail exigiria evidência própria.

| Observação na referência TT | c16 | c17 |
|---|---:|---:|
| WL80 no acesso BL (ns) | 214,216 | 234,209 |
| BLB−BL passa a positivo até a captura (ns) | 214,121 | 234,113 |
| SCLK20 do tail (ns) | 214,153 | 234,153 |
| BLB−BL em SCLK20 do tail (mV) | +15,1 | +19,9 |
| BLB−BL em SCLK50 do tail (mV) | +360,5 | +373,2 |
| Inversão do diferencial do latch (ns) | 214,579 | 234,590 |
| Captura local (ns) | 220,058 | 240,058 |
| D na captura (V) | 1,803 | 1,803 |
| Q do registrador / DATA3 na observação (V) | 1,800 / 1,800 | 1,800 / 1,800 |
| Palavra esperada / observada | `0xF0` / `0xF8` | `0xF0` / `0xF8` |

Q da bitcell ficou entre −7 e +147 mV e QB ficou entre 1,772 e
1,832 V entre 120,55 e 241,50 ns, incluindo as duas avaliações.
Os reads predecessores c14 e c15 retornaram `0xAA` e `0x0F`.
A primeira divergência funcional continua na regeneração do sense
3, antes de D e do registrador. A relação temporal WL–SCLK permanece
uma hipótese. [Análise TT anterior](phase3_data3_tt_snm_piloto_20261120.md) · [Amostras anteriores](../build/phase3/data3_tt_diagnosis_final_20261120/read_transition_samples.csv)

## E. Monte Carlo — as seis VTCs recuperadas offline

Foram conferidos 406 recibos com suas sementes registradas pelo
ngspice, hashes do manifesto, logs, decks e VTCs. Os 406 decks
foram reconstruídos byte a byte a partir da folha 6T canônica
e da configuração arquivada. As tentativas têm retorno original
zero, e cada log registra 1.801 pontos no sweep de 0 a 1,8 V com
passo de 1 mV.
Hold usa `WL=0` e Read usa `WL=VDD`, com `BL=BLB=VDD` em ambos.
Os seis transistores estão presentes nos dois modos.
[Manifesto Hold](../build/phase3/snm_nominal_hold_batch01_20261120/manifest.json) · [Manifesto Read](../build/phase3/snm_nominal_read_batch01_20261120/manifest.json)

Os 18 arquivos do fechamento de modelos coincidem com cada manifesto.
Plataforma SKY130A Volare `0fe599b2afb6708d281543108caf8310912f54af`,
biblioteca contínua SHA-256
`c7e9fe87ffc2685bc56da02f92cd48b1403a5e9da85cc7978027fb0ca347d581`.
`tt_mm` usa parâmetros TT de FET com `MC_MM_SWITCH=1`, mismatch local
entre instâncias, e `MC_PR_SWITCH=0`, sem sorteio global de processo.
Condições experimentais de 1,8 V e 27 °C, bitcell esquemática.
Os dados antigos de `sf_mm` ficam separados.

### Critério de extração

O motivo original, `Butterfly endpoint signs are ambiguous`, foi
reproduzido exatamente nas seis seeds. O extrator descartava como
insignificante a diferença de uma extremidade do domínio rotacionado
por ela estar abaixo de 100 nV. As curvas nessas regiões ainda
continham um cruzamento. O procedimento novo testa a existência e a
unicidade desse cruzamento independentemente do critério antigo.

1. Constrói (h(x)=R(L(x))-x) para as VTCs lineares por trechos, nos
   nós de L e nas pré-imagens dos nós de R. Três zeros são as três
   interseções da butterfly e delimitam dois lóbulos. Os rails da
   bancada DC passiva em 0 e VDD dão os sinais não estritos de (h)
   nos extremos.
2. Cada tensão de saída tem limite de arredondamento igual a meia
   unidade de sua última casa impressa. A auditoria usa o maior por
   curva, 5 nV para estes arquivos. A composição tem erro limitado
   por (e_R+\max|R'|e_L), além do arredondamento aritmético.
   Onde o sinal permanece ambíguo, verifica o sentido estrito da
   derivada (R'L'-1) para todas as inclinações plausíveis sob a
   quantização. Tangências, cruzamentos adicionais não resolvidos
   ou curvas incompletas não viram SNM zero.
3. Com os lóbulos delimitados, mantém a medição geométrica do
   maior quadrado em cada lóbulo no espaço rotacionado. A SNM é o
   menor dos dois lados. Um único cruzamento certificado demonstraria
   monoestabilidade e SNM zero. A auditoria certifica a topologia
   dos interpolantes sob erro de impressão e não estabelece um limite
   para a discretização física da curva, tolerâncias do solucionador,
   variação global, parasitas ou condições da macro integrada.

### Reclassificação aditiva

Em todas as linhas, a rejeição original foi por sinais ambíguos em
uma extremidade. As seis VTCs contêm 1.801 pontos completos, finitos
e monotônicos, com três interseções certificadas. Os valores dos
lóbulos e margens são expressos em mV. A diferença indicada na
coluna de extremidade é em nV, com sinal na coordenada rotacionada.

| Seed | Diferença na extremidade rejeitada (nV) | Lóbulo 1 | Lóbulo 2 | SNM | Veredito |
|---:|---:|---:|---:|---:|---|
| 30005 | −98,995 | 458,761 | 391,725 | 391,725 | `VALID` |
| 30021 | +84,853 | 394,360 | 450,673 | 394,360 | `VALID` |
| 30053 | +98,995 | 402,501 | 457,141 | 402,501 | `VALID` |
| 30090 | +98,995 | 395,208 | 444,292 | 395,208 | `VALID` |
| 30148 | +98,995 | 411,337 | 448,036 | 411,337 | `VALID` |
| 30192 | −98,995 | 445,444 | 422,489 | 422,489 | `VALID` |

O mesmo procedimento também recupera as 400 margens originalmente
aceitas, incluindo as seeds adjacentes às seis rejeições. A diferença
máxima por amostra foi 3,33×10⁻¹⁶ V em Hold e zero em Read. Os
extremos foram verificados nas respectivas VTCs. Hold 20057 =
655,439 mV e 20185 = 701,742 mV. Read 30009 = 381,598 mV e 30033
= 439,523 mV. Nenhum extremo mudou e não houve SNM zero nem rejeição
residual no conjunto auditado. [Resultado por seed e recibos](../build/phase3/snm_endpoints_final_20261120/audit.json)

| Estatística (mV) | Hold original e revisado | Read original, 200/206 | Read revisado, 206/206 |
|---|---:|---:|---:|
| Média | 684,740 | 409,961 | 409,756 |
| Desvio-padrão amostral | 8,473 | 10,690 | 10,761 |
| Mediana | 685,271 | 410,573 | 410,356 |
| Mínimo / máximo | 655,439 / 701,742 | 381,598 / 439,523 | 381,598 / 439,523 |
| P05 / P25 | 669,142 / 680,332 | 392,397 / 402,553 | 392,211 / 402,354 |
| P75 / P95 | 689,629 / 697,775 | 416,791 / 426,198 | 416,778 / 426,073 |
| IC bootstrap 95% da média | [683,568, 685,909] | [408,505, 411,441] | [408,335, 411,224] |

O IC usa 10.000 reamostragens. A inclusão das seis margens reduz
a média de Read em 0,205 mV. Os arquivos originais das 200 válidas
e das seis rejeições continuam intactos. A auditoria tem 200 Hold e
206 Read válidas e supera o mínimo de 200 por modo no domínio testado.
A especificação, seção 20, ainda deixa a temperatura nominal em aberto.
O uso de `tt_mm` e do ponto experimental precisa ser homologado, e
as dimensões 8×8 e 32×8 exigidas para os resultados da macro continuam
fora desta evidência. O alvo de Read SNM de 0,4 V é determinístico.
Nenhuma taxa de aprovação estatística ou rendimento é inferida.
[Hold original](../build/phase3/snm_campaign_results_20261120/hold/summary.json) · [Read original](../build/phase3/snm_campaign_results_20261120/read/summary.json)

## F. Situação e decisão

| Frente | Estado |
|---|---|
| Funcional SS | Evidência anterior preservada, 9/9 leituras, 6/6 escritas e 18/18 períodos de propriedade observados. |
| Funcional TT | `FAIL` histórico, 7/9 leituras no integrado e `0xF8` duas vezes no recorte. Contraste atual `INCONCLUSIVO`. |
| Funcional FF | Validação integrada do mesmo candidato pendente. |
| Hold e Read SNM | Auditoria `VERIFIED` para 200 Hold e 206 Read no domínio esquemático `tt_mm`. Homologação estatística pendente. |
| Setup/hold e potência | `NOT_CHARACTERIZED`. |
| Liberty | Pendente das métricas qualificadas. |
| Qualificação elétrica geral | `NOT_CHARACTERIZED`. |

O atraso controlado ainda não foi avaliado eletricamente nas duas
leituras. Não há evidência causal para autorizar um ECO. A próxima
investigação mínima é **instrumentar a partida da fixture R87**, com
marcas de parede na leitura/expansão do deck, no ponto de operação
e no primeiro avanço transiente. Se o cartão PWL concentrar a demora,
reduzir pontos redundantes nas regiões constantes e manter o
deslocamento único de 182 ps com a mesma fidelidade nas bordas. A
etapa termina com um ensaio curto capaz de demonstrar progresso e
equivalência dos controles compartilhados, antes de expor a macro a
outro contraste de 250 ns. Nenhuma ação futura foi executada nesta
rodada. As seis rejeições de Read foram resolvidas e o impedimento
remanescente para qualificação é o domínio experimental, não a
quantidade ou a integridade das amostras.

## Execução e reprodução

| Etapa | Tempo observado |
|---|---|
| Auditoria offline da fixture anterior | Cerca de 2 min 34 s, até registrar a hipótese inicial |
| Seleção do ramo, implementação e preparo | Cerca de 1 min 32 s após o registro inicial |
| Ensaio curto em SPICE | 120,305 s de parede, 1 tentativa |
| Transiente TT completo | 0 tentativas |
| Auditoria SNM offline | 7,59 s de parede no replay final. Zero execuções DC novas. |

Comandos do preparo e do ensaio efetuado. Para reproduzir o preparo
em outro local, use um diretório de saída novo no checkout contendo
as dependências abaixo. O gate do resultado arquivado bloqueia o
comando `full`.

```bash
run=build/phase3/sclk_r87_20261120
PYTHONDONTWRITEBYTECODE=1 python3 tools/phase3_sclk_r87.py prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/phase3_sclk_r87.py startup --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 tools/audit_phase3_snm_endpoints.py \
  --build build/phase3 --output build/phase3/snm_endpoints_final_20261120
```

Passaram **30 testes de software distintos**, sendo oito novos e 22
existentes. Os quatro arquivos de teste exercitam a preparação TT, o
piloto SNM, o contraste anterior, o bloqueio do transiente longo,
a rejeição do ramo compartilhado, curvas com dois lóbulos, um
cruzamento e topologia não resolvida. `git diff --check` e
`git diff --cached --check` passaram. A branch mantém o HEAD indicado
no início, com alterações locais preexistentes e os arquivos novos
desta rodada. Não houve commit, merge ou push.

Arquivos locais desta entrega:

- `tools/phase3_sclk_r87.py` e `tools/audit_phase3_snm_endpoints.py`.
- `tests/test_phase3_sclk_r87_snm_endpoints.py` e este relatório.
- `build/phase3/sclk_r87_20261120/`, com decks, log vazio original,
  recibos e gate, e `build/phase3/snm_endpoints_final_20261120/`, com
  o JSON de auditoria e a evidência da regressão de software.

O ZIP desta rodada contém os arquivos novos e um inventário SHA-256.
Para reanálise em checkout separado, combine-o com os ZIPs
`phase3_validacao_integrada_ss_20261119.zip`,
`phase3_fechamento_barramento_ss_20261120.zip`,
`phase3_tt_snm_20261120.zip`, `phase3_data3_tt_snm_piloto_20261120.zip`
e `phase3_sclk_contraste_snm_20261120.zip`. Nesta ordem, o último
pacote histórico fornece o índice final, os 406 checkpoints e as VTCs.
A receita de auditoria offline usa as VTCs arquivadas e dispensa o
simulador. A reprodução em uma árvore limpa do HEAD com os cinco
pacotes e os arquivos novos gerou o mesmo SHA-256 do adaptador,
do deck de 250 ns e do JSON de auditoria. [Auditoria](../build/phase3/snm_endpoints_final_20261120/audit.json) · [Regressão](../build/phase3/snm_endpoints_final_20261120/tests.log) · [Reprodução](../build/phase3/snm_endpoints_final_20261120/reproduction.json)
