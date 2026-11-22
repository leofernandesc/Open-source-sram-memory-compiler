# Fase 3 — Diagnóstico da partida do ngspice em TT

Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
Esta rodada investiga onde a execução perde tempo, usando o prefixo
de 14 ns. As duas leituras de `0xF8` em TT e o diagnóstico da
regeneração do sense 3 vêm do ensaio anterior. O pulso experimental
começa após 211 ns, fora dos ensaios desta rodada.
[Diagnóstico do bit 3](phase3_data3_tt_snm_piloto_20261120.md) ·
[Primeiro contraste](phase3_sclk_contraste_snm_20261120.md) ·
[Tentativa R87](phase3_sclk_preflight_auditoria_snm_20261120.md)

## A. Monitor anterior

`tools/phase3_sclk_r87.py` iniciava diretamente `ngspice -n -b`
dentro do container EDA. O PID que o Python obtinha correspondia
ao subprocesso do simulador. O problema de observabilidade era a
saída combinada em arquivo regular e a interpretação de um único
tipo de registro. Na ausência de `Reference value`, a guarda aos
120 s registrava 0,0 ns para decidir a interrupção. O recibo final
preservava corretamente o avanço como desconhecido.

Com stdout redirecionado a arquivo, a biblioteca C pode reter
saída em buffer. Stderr e os pontos `Reference value` têm dinâmica
própria. O código do ngspice descarrega explicitamente o buffer
de stdout ao emitir esses registros em `OUTpData`, com intervalo
limitado por tempo de CPU e dependente de ponto disponível. Assim,
até um log vazio pode corresponder a CPU ocupada antes de haver
dados de análise para registrar. A ausência de marcador, por si
só, não distingue leitura do deck, elaboração, resolução inicial
ou progresso ainda não emitido. O log anterior também não contém
CPU, RSS ou I/O para reconstruir a atividade daquele processo.
[Código de saída do ngspice](https://raw.githubusercontent.com/imr/ngspice/master/src/frontend/outitf.c) ·
[Recibo anterior](../build/phase3/sclk_r87_20261120/startup/result.json)

## B. Instrumentação e controle

O novo wrapper `tools/diagnose_phase3_sclk_startup.py` usa
`stdbuf -o0 -e0` e dois pipes simultâneos. Preserva stdout e stderr
em arquivos separados, carimba os marcos com relógio de parede
UTC e mede deltas com relógio monotônico. Os timestamps vêm da
leitura dos pipes. Os arquivos escritos pelo coletor ainda usam
buffer e podem demorar a refletir uma chegada observada. `stdbuf` executa o
ngspice no mesmo PID. Cada amostra registra a identidade do
executável em `/proc/<pid>/exe`, CPU de usuário/sistema em conjunto,
RSS, VmHWM, estado, função de espera quando disponível, contadores
de I/O e o último tempo reportado. O recibo final mede a CPU total
do subprocesso também no intervalo entre a última amostra e a
saída. As amostras têm intervalo de cerca de 5 s.

Os três decks recebem os mesmos `echo` de diagnóstico. O primeiro
está no início de `.control` e comprova que a elaboração chegou
ao ponto de executar os comandos. Ele delimita em conjunto leitura,
pré-processamento, expansão de subcircuitos e construção do deck.
O segundo marca o despacho de `tran`; o terceiro, seu retorno.
Os avisos e o `Transient op` vêm do próprio ngspice. As marcas
`Transient op started` e `finished successfully` são do fallback
OPtran, posterior às primeiras tentativas de solução. O início
exato da primeira tentativa de ponto de operação fica `UNKNOWN`
sem marcador correspondente. `Initial Transient Solution` dá
evidência de que foi obtida uma solução inicial. O primeiro
`Reference value` positivo comprova avanço publicado no transiente.
Os marcos ausentes permanecem `UNKNOWN` (`null` no JSON). O único
limite de interrupção desta instrumentação é o relógio de parede.
[Manual do ngspice 44](https://ngspice.sourceforge.io/docs/ngspice-44-manual.pdf) ·
[Ordem dos comandos de controle](https://raw.githubusercontent.com/imr/ngspice/master/src/frontend/inp.c) ·
[Solução inicial e fallback](https://raw.githubusercontent.com/imr/ngspice/master/src/spicelib/analysis/cktop.c)

O preflight verificou o fechamento de 319 arquivos de modelos e
conferiu que tirar a fonte da variante C recupera byte a byte o
binding de A. A PWL da variante B tem dois pontos de corrente zero
e é identicamente nula também após o horizonte do ensaio. C é uma
cópia byte a byte do adaptador arquivado. `bench.spice` e
`fabric.spice` são idênticos nas três variantes. Parâmetros comuns:
ngspice 44.2/KLU, SKY130A TT, 1,8 V, 27 °C, 10 fF/bit, Gear,
passo máximo 25 ps, `reltol=1e-4`, `vabstol=1e-8`, `iabstol=1e-12`
e um CPU. O PEX padrão tem SHA-256
`12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`.
As mudanças de captura e de logging são comuns a A, B e C.
[Preflight com hashes](../build/phase3/sclk_startup_diagnostic_20261120/preflight.json)

## C. Comparação experimental

Tempos de parede em segundos a partir do lançamento de cada
processo. O teto é 180 s por execução, já incluindo a pequena
janela para encerrar o processo. `Reference value` comprova um
ponto de saída observado. Como o comando `wrdata` vem depois de
`tran`, um processo interrompido durante a análise não deixa o
waveform que esse comando escreveria.

| Métrica | A · Referência | B · Fonte zero | C · PWL original |
|---|---:|---:|---:|
| Primeiro conteúdo recebido (s) | 3,266 | 3,549 | 3,561 |
| Deck pronto / despacho de `tran` (s) | 105,102 / 105,103 | 112,350 / 112,350 | 113,104 / 113,105 |
| Primeira tentativa do ponto de operação | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| Início do fallback OPtran (s) | 106,549 | 113,735 | 114,530 |
| Ponto de operação inicial reportado (s) | 111,987 | 118,845 | 119,680 |
| Primeiro progresso positivo (s de parede) | 112,317 | 119,179 | 120,014 |
| Primeiro tempo simulado positivo reportado (ns) | 0,0016 | 0,0016 | 0,0016 |
| Maior tempo simulado observado (ns) | 11,1843 | 10,5737 | 10,4000 |
| CPU acumulada (s) | 179,326 | 179,419 | 179,417 |
| Pico de memória residente amostrado (KiB) | 1.609.068 | 1.609.172 | 1.609.100 |
| Encerramento (s) | 179,818 | 179,926 | 179,922 |
| Motivo / retorno | Teto de parede / −15 | Teto de parede / −15 | Teto de parede / −15 |

**Classificação A — preparação do deck antes da análise.**
Preparar o deck consumiu de 105 a 113 s, entre 58% e 63% do teto
observado em cada tentativa. A fase do despacho de `tran` até a
solução inicial levou de 6,50 a 6,88 s. O simulador continuou a
integração até o teto nos três ensaios. Nenhum chegou a 14 ns ou
gerou waveform. A delimitação observada não separa o custo exato
de pré-processamento, expansão e criação do circuito no frontend.

Cada PID foi amostrado 36 vezes. Todas as amostras mostraram
estado `R`, com CPU de aproximadamente um núcleo. Os contadores
de chamadas de leitura ficaram estáveis entre aproximadamente 5 s
e o fim da preparação, enquanto a memória crescia. Isso favorece
trabalho computacional na elaboração do deck em vez de espera
de I/O. A versão de referência também exibe esse custo. Os logs
de stderr, inclusive os avisos de matriz singular em `xdut.rc7913`,
são byte a byte iguais nas três variantes. O bloco impresso da
solução transiente inicial também coincide byte a byte
(SHA-256 `25bfaab71a74174a4720e8eea2e9c5b60582c26eb197fd1debf037aab5376473`).

Nesta comparação, B levou 7,25 s a mais que A até o deck ficar
pronto. Há uma execução por variante, de modo que a diferença
observada não estima uma penalidade reproduzível da fonte nula.
C acrescentou **0,75 s** a B nessa etapa e **0,83 s** até o
primeiro progresso positivo. A PWL longa não exibiu neste
prefixo um custo adicional de magnitude comparável aos mais de
100 s de preparação comum. Tampouco foi observado um novo erro
de convergência ou degradação severa de integração da fonte R87
antes do pulso. Isso não resolve a lentidão do adaptador anterior
com fontes comportamentais nem o custo durante a injeção real.

**Classificação D — guarda histórica insuficiente.** Em torno
de 120,6–120,7 s, B e C reportavam apenas 0,521 e 0,121 ns,
respectivamente, ainda com CPU próxima de 100%. A exigência
anterior de ultrapassar 1 ns em 120 s interromperia essas
execuções mesmo com avanço válido. O indicador anterior de
ausência de texto não permite reconstruir em que fase exata
estava o processo histórico no momento do SIGTERM.
[Comparação e marcos UTC](../build/phase3/sclk_startup_diagnostic_20261120/comparison.json) ·
[Amostras da referência](../build/phase3/sclk_startup_diagnostic_20261120/A_reference/samples.jsonl) ·
[Amostras da fonte zero](../build/phase3/sclk_startup_diagnostic_20261120/B_zero/samples.jsonl) ·
[Amostras da PWL original](../build/phase3/sclk_startup_diagnostic_20261120/C_original_pwl/samples.jsonl)

## D. Avaliação offline da PWL

| Propriedade | Resultado |
|---|---:|
| Pontos / timestamps distintos | 3.203 / 3.203 |
| Valores de corrente distintos | 3.182 |
| Tamanho do cartão lógico com quebras | 97.932 bytes |
| Linhas físicas / continuações | 535 / 534 |
| Pontos de corrente exatamente zero | 5 |
| Pontos interiores a trecho constante zero | 0 |
| Intervalo mínimo, presente em 3.200 pares | 5 ps |
| Hiatos entre grupos | 211 ns e 12 ns |
| Primeiro ponto de corrente não nula | 211,005 ns |
| Corrente no pico em módulo, orientação raiz→ramo | −69,336 mA a 214,220 ns |

Os pontos estão em ordem estrita e a interpolação é contínua.
Os nós podem introduzir eventos de fonte nas janelas tardias.
Até 14 ns, ambas as PWLs têm somente a corrente nula. Qualquer
custo adicional antes disso viria da preparação ou do processamento
da representação. O pulso ainda não chegou aos gates.
[Implementação dos breakpoints da fonte de corrente](https://raw.githubusercontent.com/imr/ngspice/master/src/spicelib/devices/isrc/isrcacct.c)

A colinearidade exata de três pontos pode ser demonstrada pelos
produtos cruzados das diferenças de tempo e corrente, usando os
literais decimais como racionais. A remoção iterativa reduz 206
pontos, cerca de 6,4%, e deixa **2.997**. O valor matemático de
`I(t)` permanece igual, mas a lista de eventos de integração
pode mudar. Não foi produzido nem simulado um contraste
compactado. Uma redução bem maior exigiria declarar e verificar
um erro aceitável de forma de onda e de atraso.

O pico equivale a cerca de 448 mV de comando ideal em série com
os 6,46438 Ω de R87. Esse é o equivalente de Thévenin da
instrumentação no ramo. Não é uma medição da tensão real em R87,
da corrente líquida a montante ou da corrente da macro. A soma
algébrica da fonte e da corrente em R87 determina a perturbação
líquida. O ramo chega somente aos três gates do sense 3, mas
troca corrente com a raiz compartilhada e pode influenciar
outros nós por essa raiz e pelas capacitâncias. Um contraste
causal interpretável exige medir o atraso e a forma dos três
gates, os sinais a montante e a pré-carga. Os 14 ns atuais
não exercitam a injeção nem demonstram esse isolamento elétrico.
[Métricas extraídas da fonte arquivada](../build/phase3/sclk_startup_diagnostic_20261120/preflight.json)

## E. Decisão de engenharia

**Corrigir o monitor.** A partida de C foi observável e produziu
dados de transiente mesmo com a PWL original. A regra antiga
teria interrompido B e C perto de 120 s apesar da atividade do
simulador. Use o PID e os marcos de fase para estabelecer atividade
e mantenha um teto explícito de parede. Uma guarda em tempo simulado
só passa a ser interpretável depois de comprovar a partida do
transiente. A evidência atual sustenta manter a forma da fonte para
o próximo contraste, com validação do pulso real. A validade elétrica
do pulso e a duração de um contraste completo continuam em aberto.

## F. Próxima tarefa mínima

Em rodada separada, executar **um contraste TT de 182 ps** no deck
reduzido de referência com monitoração por fase. Usar os waveforms
arquivados como controle e registrar a raiz comum de SCLK, os três
gates do sense 3, WL, pré-carga, sense, D/Q e as duas palavras.
O critério de aceitação do experimento é comprovar a entrega do
atraso local de 182 ps dentro da resolução de 25 ps registrada
no preflight anterior, preservar a desativação e os controles
compartilhados dentro da resolução acordada e obter as duas leituras
observáveis. Só então se classifica o resultado funcional. Uma
mudança elétrica relevante nos controles compartilhados torna o
contraste causal inconclusivo mesmo se aparecer `0xF0`.
[Critério de resolução já registrado](../build/phase3/sclk_r87_20261120/preflight.json)

## Entrega e reprodução

```bash
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 \
  python3 tools/diagnose_phase3_sclk_startup.py \
  --output build/phase3/sclk_startup_diagnostic_20261120
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests \
  -p 'test_phase3_sclk_startup.py' -v
```

O primeiro comando foi usado no checkout com a referência TT e
o preparo R87 já arquivados. Para repetir em outra rodada, use
um diretório de saída novo sob `build/phase3`. O executável,
o fechamento de modelos e a fonte R87 são verificáveis pelo
preflight e pelos recibos. Os três decks selados e os logs e
amostras por PID estão em `build/phase3/sclk_startup_diagnostic_20261120/`.
O ZIP local contém esses artefatos, este relatório, o monitor
novo, suas regressões e um inventário SHA-256.

A inspeção e a implementação até invocar o monitor levaram
cerca de 2 min 18 s. O wrapper mediu 1,17 s de preparo antes
do lançamento de A e 9 min 00,846 s de ponta a ponta, com três
ensaios curtos e sem repetição. A auditoria exata da PWL foi
incluída no preparo. Os tempos efetivos dos processos constam
da tabela da seção C. Nenhum transiente de 250 ns foi iniciado.

Passaram **cinco testes de software**. Foram verificados o
tratamento de log silencioso como `UNKNOWN`, o registro por
PID, a leitura de blocos partidos dos pipes, a redução PWL
por colinearidade exata e a rejeição de tempos duplicados.
Os scripts anteriores e seus recibos foram preservados. O
HEAD e a branch permanecem no estado inicial, junto com as
alterações locais preexistentes. Sem commit, push ou merge.
[Log dos testes](../build/phase3/sclk_startup_diagnostic_20261120/tests.log)

| Frente | Estado |
|---|---|
| Falha funcional TT | `FAIL`, `0xF8` em vez de `0xF0` nas duas leituras históricas |
| Hipótese causal de SCLK | `INCONCLUSIVO`, atraso não exercitado nesta rodada |
| Monte Carlo esquemático | Amostragem experimental concluída, 200 Hold e 206 Read |
| Qualificação elétrica da macro | `NOT_CHARACTERIZED` |
