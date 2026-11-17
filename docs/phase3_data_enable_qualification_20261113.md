# Qualificação experimental da reabilitação de DATA — Fase 3

Referência nominal: 13/11/2026. Campanha executada nessa data em America/Manaus;
consolidação e conferência final retomadas em 16/11/2026. Nome do documento
mantido conforme solicitado. Nenhuma nova simulação foi iniciada na retomada.

## 1. Resultado e decisão

**A reabilitação foi medida experimentalmente, mas o contrato numérico de
aprovação permanece pendente. O smoke funcional original não está aprovado.**

Uma campanha nominal curta, com 10 ciclos/210 ns, cobriu os oito bits nas duas
direções de transição e um controle sem comutação. Ela foi executada duas vezes:
a primeira revelou perda de resolução na exportação ASCII; a repetição mudou
somente a precisão de impressão, preservando todas as amostras e as 16 medições
nativas. Não houve mudança de circuito, células, carga, clock ou critérios.

Resultados principais da repetição:

- **Simulador PASS/0**, 16 medições nativas PASS e CSV com 16 linhas.
- Retomadas com padrões opostos: palavra antiga válida cerca de **1,09776 ns
  após CLK50**, estável por cerca de **9,123 ns observados** até a captura seguinte.
- Propagação local TE_B50→DATA50: aproximadamente **0,134 ns em descida** e
  **0,229 ns em subida**. Esses valores não incluem a latência CLK→READ_Q/TE_B.
- Verificador compartilhado, sem alterações: **719 PASS e 8 FAIL**. Os 8 são
  exclusivamente o check da antiga janela de 1 ns: pares em c5, ímpares em c7.
- **32/32 novas leituras PASS**, 48 checks de retenção de Q PASS; replay do
  smoke original idêntico: 1.736 PASS/4 FAIL e 72/72 novas leituras PASS.
- **50 testes de software PASS** após a repetição, zero erros ou skips.

Não se demonstrou corrupção da memória, captura antecipada ou erro lógico de
retenção nesses cenários. Os FAILs representam violações reais da janela usada
pelo observer, e não foram descartados ou convertidos em PASS. O que permanece
sem fundamento é tratar esse offset de bancada como limite físico garantido.

## 2. Referências e arquitetura efetivamente verificada

Branch `feature/phase3-infra-leonardo`; HEAD preservado
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`. Baseline
`origin/release/phase2-acceptance-20261111`, commit
`89901e7e258b6955f6752163b918a296079466fa`.

Foram retomados os relatórios `phase3_first_sram_smoke_20261113.md` e
`phase3_data_window_diagnostic_20261113.md`, a especificação técnica, contrato
digital, contrato de caracterização, RTL, binding, netlist selecionada e
verificadores da Fase 2. A cadeia de 51 entradas selecionadas foi reconferida.

Binding utilizado: `reports/phase2/direct_abutment_20261111/qualification_v1/binding.spice`,
SHA-256 `f4b502bcf1c99fb18d02ebad712878ebf83c0a4cec04987d2dce3d9645baa510`.
Modelo principal: `/opt/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice`,
SHA-256 `5efa041a988893c1a3580d0ecd57870ea3146b27741c7d42b56baaa336b9549e`.
A proveniência completa e as dependências estão nos manifestos, planos e inventário.

O wrapper captura controles/endereço/escrita na subida e atualiza `read_data_q`
na descida. A saída é `DATA = (read_q && live_read) ? read_data_q : Z`, com
`live_read = !CSb && !OEb && WEb`. O caminho real contém registrador `dfxtp_1`,
lógica de seleção/retenção e buffer `ebufn_1`; não liga DOUT_RAW diretamente a DATA.
Os 80 inversores e taps de fase foram preservados integralmente.

Quatro propriedades distintas:

| Propriedade | Exigência/análise |
|---|---|
| Retenção interna | Q deve guardar o último read até a próxima captura; não depende de o pino estar habilitado |
| Visibilidade externa | DATA só é dirigido pela SRAM quando read capturado e controles live permitem |
| Recuperação após reabilitação | Tem latência de captura/enable e acomodação analógica, dependente de direção/carga |
| Nova palavra de leitura | Depende da avaliação/sense e da captura na descida, mais propagação de saída |

**Não há exigência de que DATA continue com a palavra antiga durante a escrita.**
A SRAM deve liberar o pino para o host apresentar novos dados; exigir retenção
contínua nesse intervalo conflitaria com o barramento bidirecional. A retenção
continua sendo exigida internamente. Em leituras consecutivas com habilitação
mantida, a visibilidade da palavra antiga permanece parte do contrato.

Isso não autoriza comportamento arbitrário após enable: retenção errada,
direção incorreta, contenção, ausência de recuperação ou nova leitura incorreta
não podem ser aprovadas por falta de um prazo de 1 ns. A janela temporal de
conformidade precisa, porém, de uma referência e de um limite independentes.

## 3. Metodologia e condições

ngspice 44.2, executável `/opt/ngspice/ngspice-44.2/bin/ngspice`,
SHA-256 `af05592b4adc21e9c792b8bbda0d3ddb0a86bfccf80c8e6e5c5e7c366184fe77`;
Python 3.10.12, container existente `sram-xschem`, launcher `tools/sram-eda`.
SKY130A, TT, 1,8 V, 27 °C provisórios; clock 20 ns/50%, slew 50 ps e 10 fF/bit.
Extração de dispositivos/junções; sem RC distribuído completo, ruído estatístico,
variação de tensão/temperatura ou outros corners.

O estímulo foi produzido pela função existente `phase2_extension.deck('bus')`,
com sequência local substituída somente no processo de preparação. Não se editou
o gerador compartilhado. As sondas de corrente e a calibração de oposição da
fixture existente foram preservadas; estão desligadas nos intervalos de retomada.

| Ciclos | Estímulo |
|---|---|
| 0–1 | Idle de partida |
| 2–3 | Escrita 0x55 na linha 0 e leitura que inicializa legitimamente o registrador |
| 4–5 | Escrita 0xAA na linha 1 e retomada de leitura; restaura 0x55 antes da captura |
| 6–7 | Escrita 0x55 na linha 0 e retomada inversa; restaura 0xAA antes da captura |
| 8–9 | Escrita/leitura 0x55 na linha 0; controle sem mudança de valor |

Isso reexercita o mecanismo dos quatro FAILs originais nos bits pares e adiciona
o espelho nos bits ímpares. São 24 casos bit/retomada, dos quais 16 têm transição
mensurável. O histórico inicial foi encurtado; não se afirma que ele é idêntico ao
smoke de 18 ciclos. Os 72 checks originais foram reavaliados no seu próprio raw.

Não foram usados `.ic`, `.nodeset` nem memória/registrador preenchidos manualmente.
Os estados necessários resultam das escritas e leituras reais. O caso cobre
somente linhas 0/1; não representa nova campanha de cobertura completa do array.

Simulação: `tran 10p 210n 0 10p`, CPU/thread únicos, memória virtual até 4.096 MiB,
timeout de 1.800 s e limite de 512 MiB por arquivo. Foram preservados os dois runs.
A repetição começou em `2026-11-13T20:02:56.650832-04:00` e terminou em
`2026-11-13T20:13:18.807704-04:00`; o runner registrou 620.828 s de execução.

## 4. Validade, estabilidade e referências de medição

Foram reutilizadas as funções de cruzamento/validade e o checker existentes:
`analyze_phase2_extension_timing.crossing/valid` e `phase2_extension.check`,
que chama `phase2_access_checks.check`. Nenhum verificador elétrico foi duplicado.

Critérios existentes, sem alteração:

- Baixo: −0,18…0,36 V; alto: 1,44…1,98 V, correspondendo aos limiares
  funcionais de 20%/80% de 1,8 V com os limites externos já usados pelo checker.
- Propagação: cruzamentos de 50% VDD, interpolados entre amostras.
- Início operacional da recuperação: saída da faixa do valor imposto durante
  a escrita, por 20% em subida ou 80% em descida. Não é o primeiro dV/dt infinitesimal.
- Entrada na faixa correta: 80% em subida ou 20% em descida, para o bit do Q antigo.
- Estabilidade observada: todas as amostras ficam na faixa correta, desde a entrada
  medida até a próxima captura local. O fim é uma borda de clock independente de DATA.

Foram observados todos os oito bits; a validade da palavra usa o último a entrar
na faixa correta. Não se exige um dwell arbitrário inventado; reporta-se a duração
estável disponível. O critério de medição encontra a acomodação no waveform;
**não usa esse instante para escolher uma janela de PASS e aprovar a si próprio**.

A desabilitação/reabilitação é referenciada pelo controle local TE_B50, com
TE_B80/20 adicional nos artefatos. **Isso não mede exatamente o instante físico
em que a impedância se torna alta/baixa.** O prazo completo de liberação em alta
impedância requer caracterização própria; os checks de corrente existentes apenas
confirmam direção/liberação nas suas janelas e condições de sonda.

No caso de mesma palavra, DATA já podia estar correto pela carga/host antes do
enable. Não se fabricou atraso zero: os cruzamentos de propagação são ausentes,
`NOT_CHARACTERIZED`, e a validade de tensão é reportada como observação censurada.

## 5. Tempos de desabilitação, recuperação e validade da palavra

Tempos absolutos em ns. Faixas nas colunas de controle/início abrangem os oito bits.
A coluna final é uma diferença experimental relativamente ao CLK50 público, não
um novo limite de aprovação.

| Caso | Dado imposto na escrita → Q antigo restaurado | TE_B50 desabilita | TE_B50 reabilita | Início 20/80 da recuperação | Todos válidos, interpolado | CLK50→todos válidos (ns) |
|---|---|---|---|---|---|---|
| c5 | 0xAA → 0x55 | 87.160490–87.160883 | 110.767340–110.768185 | 110.867084–110.893905 | 111.122761 | 1.097761 |
| c7 | 0x55 → 0xAA | 127.160548–127.160941 | 150.767362–150.768206 | 150.867105–150.893917 | 151.122774 | 1.097774 |
| c9 | 0x55 → 0x55 | 167.160548–167.160941 | 190.767526–190.768085 | Não comuta / censurado | Já válido antes do enable; sem instante de transição | NOT_CHARACTERIZED |

| Caso | Primeira amostra válida após enable (ns) | Última amostra estável (ns) | Próxima captura local mais cedo (ns) | Duração observada (ns) | Amostra da nova leitura (ns) |
|---|---:|---:|---:|---:|---:|
| c5 | 111.128651 | 120.251555 | 120.255138 | 9.122903 | 121.004457 |
| c7 | 151.128651 | 160.251555 | 160.255138 | 9.122904 | 161.004017 |
| c9 | 190.776817 | 200.251555 | 200.255153 | 9.474738 | 201.004698 |

Para c9, “primeira amostra” significa a primeira inspecionada depois da última
habilitação local; **não** o início físico da validade, que já era anterior.
Nos três casos, todos os bits permaneceram estáveis nos intervalos avaliados e
Q conservou o valor anterior até a borda local de captura de cada bit. Esses
24 intervalos individuais foram reconferidos em `capture_bounds.json`.

As novas palavras foram confirmadas nas amostras listadas. Em c5/c7 as primeiras
amostras estáveis da nova palavra são 120,817565 e 160,820046 ns, depois das descidas
públicas e antes da sonda oposta. Em c9, a igualdade antes/depois não permite medir
quando a captura se tornou visível: não há transição a cronometrar.

A sonda oposta é ligada em `rise_ns+11,5` na fixture original. Não se exige
validade de leitura normal através dessa perturbação de calibração, nem se a usa
para explicar os FAILs da fase alta; ela estava desligada durante a recuperação.

## 6. Medições nativas e correlação com o waveform

As 16 linhas em `run_precision/metrics.csv` foram realmente emitidas por `meas tran`
no ngspice e interpretadas pelo runner, em segundos. Definição declarada:
**TE_B do próprio bit descendo a 50% → DATA do bit cruzando 50% na direção de
restauração do Q antigo**. É propagação local exploratória, não um arco público
Liberty nem tACCESS. Não foi configurado máximo de desempenho; PASS da linha
significa número finito produzido, coerente com a direção e o limite mínimo zero.

| Caso | Bit | Direção em DATA | Native TE_B50→DATA50 (ns) | TE_B50→válido 20/80 (ns) | CLK50→válido 20/80 (ns) |
|---|---:|---|---:|---:|---:|
| c5 | 0 | rise | 0.2289498 | 0.355421138 | 1.097760960 |
| c5 | 1 | fall | 0.1339986 | 0.173599665 | 0.916784587 |
| c5 | 2 | rise | 0.2289498 | 0.355421138 | 1.097760960 |
| c5 | 3 | fall | 0.1339986 | 0.173599665 | 0.916784587 |
| c5 | 4 | rise | 0.2289498 | 0.355421138 | 1.097760960 |
| c5 | 5 | fall | 0.1339986 | 0.173599665 | 0.916784587 |
| c5 | 6 | rise | 0.2289498 | 0.355421138 | 1.097760960 |
| c5 | 7 | fall | 0.1339986 | 0.173599665 | 0.916784587 |
| c7 | 0 | fall | 0.1339980 | 0.173599019 | 0.916805497 |
| c7 | 1 | rise | 0.2289406 | 0.355412123 | 1.097773950 |
| c7 | 2 | fall | 0.1339980 | 0.173599019 | 0.916805497 |
| c7 | 3 | rise | 0.2289406 | 0.355412123 | 1.097773950 |
| c7 | 4 | fall | 0.1339980 | 0.173599019 | 0.916805496 |
| c7 | 5 | rise | 0.2289406 | 0.355412123 | 1.097773950 |
| c7 | 6 | fall | 0.1339980 | 0.173599019 | 0.916805496 |
| c7 | 7 | rise | 0.2289406 | 0.355412123 | 1.097773950 |

Os dados nativos foram comparados aos cruzamentos do raw exportado. A maior
diferença foi 4,285e−17 s, dentro dos brackets reais de amostragem. Essa comparação
verifica consistência de método/unidades, não estabelece precisão física de fs.
O passo máximo de integração é 10 ps, com passos adaptativos menores.

## 7. Falha de serialização e correção isolada

Primeira execução: ngspice PASS, 16 medidas PASS, mas o checker recusou o raw por
um par de tempos não crescentes. As linhas 14005/14006 imprimiram ambas
`1.27627774e-07 s`, com diferença de até 0,11300536 V nos valores. O erro foi
preservado em `analysis_attempt1_error.json`; nenhuma linha foi descartada.

A repetição acrescentou somente `set numdgt=15` ao testbench. Os tempos reais
exportados são `1.276277736451058e-07` e `1.276277744387545e-07 s`, separados por
7,93648696e−16 s. Os tempos de **todas** as 23.019 linhas, arredondados ao formato
anterior, reproduzem o vetor temporal antigo. Nenhum par não crescente restou.
As 16 medições nativas permaneceram exatamente iguais. Isso comprova colisão
por precisão de impressão, não uma mudança do circuito ou do estímulo.

O primeiro raw, de 56.744.321 bytes, foi preservado. O segundo, de 81.559.865 bytes,
contém as mesmas 23.019 linhas/154 colunas, com maior precisão de representação.
Não se mudou o critério estrito de tempo crescente, não se interpolou um tempo
faltante artificialmente e não se alterou o exportador/checker compartilhado.
A correção foi apenas na instrumentação do novo testbench diagnóstico.

## 8. Resultado funcional, manifesto e retorno da CLI

| Evidência | Resultado |
|---|---|
| Novo caso de 10 ciclos, checker compartilhado | 727 checks: 719 PASS / 8 FAIL |
| FAILs preservados | c5 bits 0/2/4/6; c7 bits 1/3/5/7, todos em `previous_data_visible_before_new_capture` |
| Novas leituras / Q capturado | 32/32 PASS em cada grupo |
| Retenção de Q / sobreposição host-saída | 48/48 PASS; 8/8 PASS |
| Corrente estável do host / envelope de captura | 32/32 PASS em cada grupo |
| Replay original sem alterar o raw | 1.736 PASS / 4 FAIL; 72/72 novas leituras PASS |
| Software após correção de exportação | 50 PASS, zero erros, falhas ou skips |

O perfil curto não foi apresentado ao adapter imutável que exige 18 ciclos/370 ns.
Foi usado o contrato existente de configuração sem adapter automático; o checker
compartilhado foi chamado **separadamente, com os registros e stop corretos**.
Assim, não se inventou um recibo de fixture aprovado para obter PASS no runner.

O manifesto do runner registra simulador PASS, medição PASS e validação automática
NOT_CHARACTERIZED; o estado global é NOT_CHARACTERIZED e a CLI retorna 1. Isso é
correto, mas **não significa ausência de falha nos checks separados**: eles são
FAIL, estão integralmente preservados e impedem aprovação da campanha/smoke.
O relatório e `analysis_summary.json` expõem ambos os resultados sem substituir
ou editar o manifesto original. Não houve exit 0 indevido para execução real.

CSV/JSON públicos permanecem compatíveis: 15 colunas, 16 medições reais, unidades
`s`, transição e bit explícitos; caso sem comutação não recebe valor fictício.
SHA-256 do raw com precisão corrigida:
`e42ba42da5cc9931a969805b8cae16cb9b869fbac98a1964bd13e999b09ec4d0`.
SHA-256 do manifesto:
`d56993b35b4909c339da57b1d9a75454682d0fb3eb660f1cd7e0a6d501795877`.
Logs, comando, versões, entradas copiadas, hashes e retorno estão preservados.

## 9. Prazo de 1 ns e critério recomendado

O prazo atual usa `rise_ns+1` a partir do **início do PWL**. Neste ensaio,
CLK50 está 25 ps depois; a janela inicia em CLK50+0,975 ns. Mesmo redefinir esse
início para CLK50+1 ns não resolveria a acomodação observada até aproximadamente
CLK50+1,09777 ns. A diferença não é apenas um problema de referência digital.

O offset de 1 ns tem uso como janela da bancada existente, mas não possui
fundamento documentado como limite físico garantido para DATA após write→read.
As novas medições o contradizem como previsão universal, nos dois sentidos e
nos oito bits. Isso não autoriza aumentar o valor para 1,1/1,2 ns apenas para passar.

Recomendação objetiva, sem aplicá-la automaticamente à baseline:

1. **Manter obrigações funcionais independentes:** retenção interna até captura,
   exclusão de direção, endereço/operador capturados corretos, read registrado
   após a descida e palavra nova correta. Defeitos nesses pontos são FAIL mesmo
   quando não existe orçamento de habilitação.
2. **Separar leituras contínuas de retomadas:** com enable mantido, verificar a
   retenção da palavra no pino. Depois de write/idle/máscara, verificar um arco de
   habilitação específico, sem confundi-lo com a atualização da nova palavra.
3. Definir o parâmetro **`T_REENABLE_VALID`**: tempo entre a última condição externa
   necessária para read e a entrada da palavra antiga inteira nas faixas 20/80,
   permanecendo nelas até a captura seguinte. Neste experimento os controles live
   já estão estáveis; a referência externa é CLK50. Restaurar OEb/CSb enquanto
   READ_Q já está ativo é outro arco e exige outra referência/ensaio.
4. Reportar também **`T_ENABLE_LOCAL50`** (TE_B50→DATA50 por bit) e a acomodação
   local até 20/80. Eles explicam o caminho, mas não substituem o prazo público.
5. Uma futura verificação de deadline deve receber **um orçamento independente,
   explícito e aplicável à configuração/corner/VDD/temperatura/slew/carga/arco**.
   Então comparar DATA com o Q retido a partir desse deadline até a captura
   independente, exigindo todas as amostras válidas e registrando margem. Nunca
   selecionar a janela a partir do próprio instante medido de acomodação para PASS.
6. Sem orçamento aprovado/qualificado, esse requisito temporal é
   NOT_CHARACTERIZED; não converter os FAILs históricos em PASS. Se não houver
   recuperação antes da captura ou se a palavra nova estiver errada, bloquear a
   qualificação e investigar o comportamento; a ausência de 1 ns não permite
   aprovar saída indefinidamente inválida ou contenção.

As evidências são suficientes para definir os eventos, os limiares e uma
**janela experimental nominal**. Não bastam para estabelecer um novo máximo
garantido: apenas dois padrões opostos, dois endereços, uma carga e uma condição
foram testados; não há margem independente ou caracterização de variabilidade.
O máximo observado de 1,097773950 ns é resultado, **não especificação**.

Não foi comprovada uma contradição lógica que admita corrigir o verificador
simplesmente retirando o offset. O check é mais restritivo que o contrato numérico
atual, mas fechar o deadline depende de uma decisão temporal de projeto e sua
qualificação. Alterá-lo agora substituiria essa decisão por um valor escolhido
sobre os dados que se quer aprovar. Portanto, não se editou o verificador compartilhado
nem a especificação oficial. Uma metodologia futura deve ser versionada, manter
os recibos antigos e preservar todos os requisitos e FAILs de referência.

## 10. Reprodução e arquivos

Todos os novos artefatos locais estão sob
`reports/phase3/data_enable_qualification_20261113_01/` (ignorado pelo Git pela
política existente). Comandos principais efetivamente executados:

```bash
tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/prepare_experiment.py
tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/data_enable_qualification_20261113_01/prepare/config.json \
  --output reports/phase3/data_enable_qualification_20261113_01/run

# Após preservar e diagnosticar a colisão temporal:
tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/prepare_precision.py
tools/sram-eda python3 tools/run_phase3.py \
  --config reports/phase3/data_enable_qualification_20261113_01/prepare_precision/config.json \
  --output reports/phase3/data_enable_qualification_20261113_01/run_precision

tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/analyze_precision.py
tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/compare_precision.py
tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/check_capture_bounds.py
tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/plot_precision.py
tools/sram-eda python3 reports/phase3/data_enable_qualification_20261113_01/tests_precision/run_tests.py
```

Os wrappers Python registraram horários, stdout/stderr e códigos em
`invocation.json`, `invocation_precision.json` e nos diretórios de testes.
Os destinos já existem; para repetir, preparar novos nomes/cópias dos scripts
locais com destino novo. Não sobrescrever os resultados preservados.

![Waveforms reais de reabilitação nos oito bits](../reports/phase3/data_enable_qualification_20261113_01/analysis_precision/enable_waveforms.png)

A figura usa amostras reais, não curvas sintéticas. A linha vermelha é CLK50+1 ns
apenas para comparação; a janela antiga começa ainda 25 ps antes. SVG, CSV de
medições e JSON por bit/caso acompanham a figura.

## 11. Validação final e pendências

As suítes `test_phase3*.py`, `test_phase2_evidence.py`, `test_phase2_output_safety.py`,
`test_phase2_extension.py`, `test_phase2_startup.py` e `test_phase2_protocol.py`
foram executadas no container EDA: **50 PASS** após a correção. As fixtures
sintéticas/mocks desses testes são software e não substituem as simulações reais.

O smoke original de 370 ns não foi repetido: não houve correção do seu critério
funcional ou circuito. Seu replay preserva as 72 leituras e os quatro FAILs; não
foi apresentado como 72 novas leituras simuladas. A única correção foi de precisão
no novo testbench isolado, e esse mesmo ensaio de 210 ns foi efetivamente repetido.

**PASS:** integridade, execução SPICE, 16 medições numéricas, correção comprovada
de serialização, recuperação/estabilidade observadas, novas leituras e 50 testes.
**FAIL:** 8 checks da antiga janela no diagnóstico; 4 no replay original.
**NOT_CHARACTERIZED:** deadline garantido de reabilitação, atraso físico exato de
liberação em alta impedância, propagação sem comutação, timing completo e potência.
**NOT_RUN:** PVT, novos loads/slews, SNM, RC distribuído e Liberty.

Próxima etapa: revisar o requisito de habilitação com a equipe e aprovar uma
metodologia/orçamento independente para TT, mantendo o presente envelope como
evidência experimental. Só depois versionar a verificação correspondente e repetir
o smoke integral. Para PVT, adaptar e qualificar os checks nominais; não extrapolar
este máximo. Nenhuma alteração de célula, buffer, fixture elétrica ou arquitetura
foi justificada para execução automática nesta investigação.

Criado: este documento e o diretório diagnóstico indicado. Os dois relatórios
anteriores foram preservados. Nenhum arquivo de produção, célula, layout, controle
temporal, seletor de release, netlist ou recibo histórico foi alterado. HEAD continua
`ebf60a2`; nenhum commit, merge ou push.

**Conclusão: comportamento nominal observado compatível com retenção e leitura
síncrona nos casos testados, sem defeito lógico comprovado; aprovação do smoke
permanece bloqueada pela lacuna do contrato temporal e pelos FAILs não resolvidos.**
