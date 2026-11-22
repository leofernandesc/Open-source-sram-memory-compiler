# Fase 3 · Referência temporal do acionador SCLK

**`SHORT_REFERENCE_NOT_DEFENSIBLE`.** A busca recuperou pontos de operação iniciais e referências de saída. A entrada B do AND2_4, os dois gates de A, o nó interno do inversor de saída e a placa PRECH de C131 continuam sem séries temporais em c15–c17. O circuito extraído identifica a cadeia que gera a fase, mas faltam fronteiras qualificadas para reproduzi-la em um recorte curto. Foram executadas **zero simulações SPICE**. O contraste StrongARM permanece `NOT_RUN` e o bloqueio `BOUNDARY_NOT_DEFENSIBLE` segue vigente. [Manifesto da auditoria](../build/phase3/sclk_temporal_reference_20261121/audit.json)

## 1. Inventário dos dados existentes

A busca examinou 1.201 cabeçalhos de tabelas locais e de membros de 25 ZIPs de Fase 3, além da conferência de decks e logs relevantes. A contagem inclui cópias e tabelas derivadas. Os únicos RAWs encontrados no escopo local eram de um ensaio anterior do decodificador de linhas. Nenhum dos cabeçalhos inspecionados expôs rótulos das cinco sondas internas faltantes. Os logs de C dão valores em `Initial Transient Solution` para elas. Esses pontos descrevem a solução inicial e não contêm a evolução da fase. O arquivo de resultados de R87 inclui também corrente, que foi produzida em um contraste com uma fonte Norton em paralelo a R87. [Inventário de cabeçalhos](../build/phase3/sclk_temporal_reference_20261121/archive_headers.csv) · [Pontos iniciais nos logs](../build/phase3/sclk_temporal_reference_20261121/initial_solution_only.csv)

O PEX selado foi comparado cartão a cartão ao binding de C. Os bindings dos integrados TT e SS têm SHA-256 idêntico ao diagnóstico TT de 250 ns. O prefixo `v(xdut.<nó>)` identifica o subcircuito `XDUT` do deck histórico. Nos recortes, os rótulos numéricos ou aliases genéricos também podem representar fontes reexecutadas, nós trocados ou cargas de outro circuito. O manifesto do recorte condicionado, por exemplo, classifica `rc7285` como agressor não observado e termina essa fronteira em um trilho. v1 e v2 substituem a excitação do sense local. Esses testes preservam observações úteis de sua própria bancada, sem fornecer uma medida nativa das entradas do acionador de C. [PEX, hashes e caminhos](../build/phase3/sclk_temporal_reference_20261121/audit.json) · [Manifesto do recorte condicionado](../build/phase3/sense3_preconditioned_20261120/manifest.json)

| Sinal necessário | Terminal físico em C | Evidência disponível | Alcance em c15–c17 |
|---|---|---|---|
| `rc8464`, B/tap 80 | `phase_delay[79].delay_cell.Y`, gates X658/X1274 e X167/X406 | Só solução inicial. PCLK `rc8375` usa tap 48 e PRECH é resultado de outra lógica. | Sem waveform da entrada ou resolução temporal para B. |
| `rc6252`, A/READ_Q NMOS | `_56_.A.t28`, X1160 | Só solução inicial no gate. `rc6243` é proxy do grupo READ_Q. O percurso até o gate soma 1,646 kΩ. | Proxy disponível nas quatro referências da tabela abaixo. Tensão e slew no gate ainda em aberto. |
| `rc6253`, A/READ_Q PMOS | `_56_.A.t29`, X241 | Só solução inicial no gate. O percurso do mesmo proxy soma 1,850 kΩ. | Mesma cobertura do proxy, com outro terminal físico. |
| `rc7285`, saída do NAND | `a_63967_14191#`, entrada comum dos oito MOS do inversor final | Só solução inicial em C. O recorte condicionado não contém essa forma de onda. | Sem waveform ou resolução temporal para esse nó. |
| `rc8467`, placa PRECH de C131 | `macro_core.precharge_drive.X.n0` | Só solução inicial. `rc8510`, tap físico de PRECH em outro ramo, está a 655,853 Ω de percurso. | Proxy disponível nas quatro referências. Diferença dinâmica entre as placas ainda em aberto. |
| `rc8562`, tronco SCLK | `macro_core.sense_drive.X.n0`, entrada de R87 e outra placa de C131 | Direto em R87 integral, cuja fonte Norton comuta durante o ensaio. Em C original, o proxy `rc8605` fica após R84, a 575,927 Ω de percurso. | As quatro referências contêm saída ou proxy. O contraste R87 fornece apoio contextual, com c16/c17 sob intervenção (nós PWL não nulos entre 211,005 e 238,995 ns). |
| `rc8585`, gate do tail original | `macro_core.sense_drive.X.t18`, X351 após R87 e R76 | Direto em C250 e R87. Os integrados de 370 ns têm `rc8584`, sampler da mesma coluna por outro ramo. | Três ciclos cobertos por C250 no terminal exato. |
| CLK público e captura | `CLK` no pino. `rc6338` (`_62_.Y`) no clock local usado no diagnóstico de DATA3 | Ambos diretos nas quatro referências. A captura local usa a transição correspondente à descida do CLK público. | Três ciclos cobertos. Manter as duas sondas e a associação local. |

O passo de saída é adaptativo. A mediana e o maior intervalo abaixo foram calculados dos timestamps arquivados em c15–c17. O maior intervalo é um limite do grid observado, sem atribuir a mesma incerteza a todos os cruzamentos. Os recortes de cerca de 59 ns usam um eixo deslocado e os protótipos StrongARM têm seus próprios circuitos. [Dados dos eixos e hashes dos waveforms](../build/phase3/sclk_temporal_reference_20261121/audit.json)

| Arquivo sob `build/phase3/` | Trecho completo (ns) | Janela c15–c17 (ns) | Pontos totais | Intervalo mediano / máximo (ps) |
|---|---:|---:|---:|---:|
| `data3_tt_20261120/waveform.dat` (C250 TT) | 0–250 | 190–245,55 | 15.322 | 13,60 / 25,00 |
| `integrated_tt_20261120/waveform.dat` | 0–370 | 310–365,55 | 22.730 | 13,57 / 25,00 |
| `integrated_ss_20261119_preflight/waveform.dat` | 0–370 | 310–365,55 | 20.539 | 17,59 / 25,00 |
| `sclk_r87_full_tt_20261120/waveform.dat` | 0–250 | 190–245,55 | 28.687 | 1,28 / 25,00 |

## 2. Dependências do recorte curto

A vista roteada e o PEX convergem na seguinte topologia:

```text
CLK público → distribuição local → rc6363/rc6364 → 80 inversores → rc8464
                                  tap 24 → release_phase
                                  tap 40 → write_drive
                                  tap 48 → evaluation/PCLK
rc8464 + READ_Q rc6252/rc6253 → NAND do AND2_4 → rc7285 → inversor final
      → rc8562 → R87 → ramo sense 3 → rc8585 (tail original)
rc8562 ← C131 de 7,54814 fF → rc8467 (distribuição PRECH)
```

Os 160 MOS da cadeia foram identificados seguindo pull-up e pull-down até os respectivos gates. Os gates de entrada do primeiro inversor pertencem à rede física do clock local, a 602,736 Ω de percurso entre `rc6363` e `rc6364`. O CLK no pino é conhecido, mas suas formas de onda nesses dois pontos não foram observadas. O inventário identifica os fanouts MOS dos taps 24, 40, 48 e 80. No tap 80, X167/X406 são cargas da `precharge_phase`, além de X658/X1274 do AND de SCLK. C194 de 0,01034 fF também conecta `rc8464` ao tronco, e C195 de 0,40455 fF liga o tronco a `rc7285`. [Cadeia extraída e fanouts](../build/phase3/sclk_temporal_reference_20261121/native_delay_chain.csv) · [Inventário de acoplamentos](../build/phase3/sense3_strongarm_local_sclk_tt_20261121/inventario_sclk.csv)

A fase lógica de tap 80 é derivada do clock. O PEX não mostra uma dependência lógica direta do dado armazenado. A evolução analógica depende do lançamento real do clock interno, das cargas e acoplamentos da cadeia e dos trilhos. PRECH, cuja lógica é `valid_access AND (clk_released OR tap80)`, chega a gates PMOS ligados a BL/BLB. Com `clk_released` já alto nas aberturas de c15–c17, a OR mascara a borda ascendente de tap 80. READ_Q pode permanecer alto durante as avaliações e ainda assim exigir seu histórico real de condução e recuperação. Somar capacitâncias ou forçar PRECH no lado de C131 a partir da sonda distante não qualifica essas dependências. [Auditoria anterior de C131 e das fases](phase3_strongarm_sclk_local_preflight_20261121.md)

O recorte teria de preservar a fase de lançamento, as cargas distribuídas da cadeia, o controle de READ_Q e os dois lados de C131, ou usar formas de onda independentes nas fronteiras que representam esses elementos. A rede extraída de SCLK tem 24 gates nativos, 21 deles fora do bit 3. A adequação de um modelo reduzido para essas cargas e para PRECH não foi demonstrada. O PEX oferece os valores, mas faltam condições de contorno para usar o recorte como gerador da referência. Também falta evidência de que ignorar as escritas ou partir já no ciclo 15 preserve o estado analógico. Os waveforms downstream de C250 podem controlar um futuro teste; derivar um estímulo de B a partir deles tornaria a comparação circular. **O gate de cinco minutos não foi aberto.** [Preflight v2 e distribuição compartilhada](phase3_preflight_integracao_sclk_v2_20261121.md)

## 3. Próxima execução única · captura instrumentada de C

O menor conjunto **a acrescentar** ao deck são seis sondas de tensão. Cinco cobrem as lacunas de A, B, NAND e PRECH. A sexta mede o tronco original sem a injeção do contraste R87. O plano preserva CLK público, captura local, gate do tail e proxies já salvos. [Plano de captura legível por máquina](../build/phase3/sclk_temporal_reference_20261121/capture_plan.json)

1. Copiar para diretório isolado `build/phase3/data3_tt_20261120/bench.spice`, `binding.spice` e `fabric.spice`. O bench SHA-256 começa por `853cd7b7` e o binding por `40f4cc2f`. Validar os hashes completos e o fechamento dos modelos SKY130 antes do despacho. A referência C250 já reproduziu o comportamento de C nos três reads de interesse.
2. Conferir a instância `XDUT`, os terminais X658/X1274, X1160/X241, o gate comum `rc7285`, C131 e R87 no binding. Adicionar a `.save` existente e aos vetores de exportação `v(xdut.rc8464)`, `v(xdut.rc6252)`, `v(xdut.rc6253)`, `v(xdut.rc7285)`, `v(xdut.rc8467)` e `v(xdut.rc8562)`. Conservar as sondas existentes, incluindo `v(CLK)`, `v(xdut.rc6338)`, `v(xdut.rc8585)`, DATA e D. Confirmar por diff que os cartões físicos e PWL permanecem idênticos. As sondas apenas registram vetores, sem inserir fontes ou cargas. A pausa pode afetar a malha adaptativa no ponto de observação.
3. Preservar a partida, as seis escritas e os ciclos de origem `0,1,2,3,4,5,8,10,14,15,16,17` no eixo de C250. Salvar desde 0 ns para manter o histórico do futuro replay. As janelas de leitura são 190–205,55, 210–225,55 e 230–245,55 ns. Usar TT, 27 °C, 1,8 V nominal, Gear/KLU e passo máximo de 25 ps, com PWL e tolerâncias de C250 intactas.
4. Na futura autorização, programar uma parada única em **245,55 ns**, um nó já existente de PWL da fixture após a recuperação de c17, antes dos 250 ns declarados. Após a pausa, exportar com `wrdata` para um arquivo temporário, conferir vetores, valores finitos, eixo crescente, cobertura do marcador e hash, então publicar por renomeação atômica. O arquivo é recuperável depois que a exportação fechar. Um erro antes do marcador pode perder o prefixo. A parada e exportação foram demonstradas com um circuito RC, e sua aplicação a C ainda requer a checagem do passo seguinte. Nenhuma retomada é necessária. RAW incremental e restauração de snapshot permanecem sem validação local e ficam fora deste plano. [Evidência da exportação RC](phase3_desempenho_ngspice_resultados_parciais_20261121.md)
5. Comparar a captura aos vetores **dos mesmos terminais** de C250 antes de aceitar os novos sinais. Preservar c15 = `0x0F` e c16/c17 = `0xF8`, a ordenação PRECH–SCLK–captura observável e os níveis estáveis. Medir 20/50/80% em subida e descida de SCLK, incluindo o slew, e guardar os pares de amostras que limitam cada cruzamento. Para o mesmo circuito, a compatibilidade temporal fica ligada à interseção dos brackets de cada marco comparável. Marcadores fora desse alcance e diferenças de forma que alterem a ordem ou a banda elétrica devem ser registrados e esclarecidos antes de usar a captura. O tronco sem injeção e as entradas novas não têm comparação direta histórica. A validade dessas sondas depende do mapeamento e do controle nos vetores já comuns. Preparar depois a tabela de fases de tap 80, READ_Q, NAND, tronco, placa PRECH e CLK local/público, mantendo resolução e incerteza por evento.
6. Reservar cerca de **25–35 min de parede** para a futura captura. C250 levou 1.509,70 s e o integrado TT de 370 ns levou 2.472,88 s, no ambiente registrado. A pausa economiza apenas a cauda após a última observação. A duração real dependerá da integração e da instrumentação. A cota de 5 min se aplica exclusivamente ao recorte curto desta rodada. [Recibo de C250](../build/phase3/data3_tt_20261120/simulation.json) · [Recibo de TT integrado](../build/phase3/integrated_tt_20261120/simulation.json)

## 4. Preservação e reprodução

A auditoria foi executada em `integration/phase3-danilo-ss` no HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. Só foram criados o relatório e seus artefatos de auditoria. O checkpoint C e os pacotes históricos tiveram seus hashes conferidos. C mantém `FAIL` TT e `PASS` SS no escopo integrado. FF e Liberty seguem pendentes. Monte Carlo permanece concluído no domínio experimental, com homologação pendente. Os resultados de StrongARM com SCLK ideal continuam válidos no recorte ensaiado e a qualificação da macro permanece `NOT_CHARACTERIZED`. [Recibos de integridade](../build/phase3/sclk_temporal_reference_20261121/offline_checks.log)

Na raiz do checkout, com Python 3 e NumPy:

```bash
area=build/phase3/sclk_temporal_reference_20261121
out=$(mktemp -d)
PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1 python3 "$area/audit_reference.py" \
  --downloads /home/leofernandesc/Downloads --output "$out"
cmp "$area/audit.json" "$out/audit.json"
```

O inventário considera o conjunto de arquivos presente na pasta Downloads. A reprodução byte a byte requer o mesmo conjunto de pacotes da auditoria. O ZIP desta rodada inclui a lista dos pacotes, o inventário, o plano e recibos. Os waveforms e PEX completos permanecem nos caminhos e hashes registrados.
