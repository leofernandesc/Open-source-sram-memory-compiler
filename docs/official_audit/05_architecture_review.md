# Auditoria de arquitetura e compromissos adicionais da Fase 2

Data: 05/11/2026. Etapa 2 de 3. Implementação examinada:
`3d148806ba16fcf6d9c5e46d1cefb975dfcc11d6`. A conformidade com a proposta
oficial é tratada em [04](04_technical_evidence_audit.md). Este documento
avalia os compromissos internos adicionais sem atribuí-los retroativamente
ao Marco 2 e sem modificar o circuito.

## 1. Arquitetura e protocolo efetivamente implementados

Foram confrontados [contrato digital](../../specs/sram_4x8_digital.md),
[interface física](../../specs/phase2_physical_interface.md),
[contrato temporal](../../specs/sram_4x8_timing_contract.md),
[controlador](../../rtl/sram_controller.v),
[wrapper](../../rtl/sram_4x8_wrapper.v) e
[binding físico](../../physical/phase2/macro_binding.v).

| Elemento | Implementação constatada | Limite da conclusão |
|---|---|---|
| Interface | CLK, ADDR[1:0], DATA[7:0] bidirecional, CSb/OEb/WEb, VDD/VSS | Protótipo físico 4×8; modelos RTL maiores não demonstram layouts maiores |
| Leitura | Somente `001`; operação/endereço capturados na subida; leitura durante alto; registro na descida | Tempos externos de setup/hold não qualificados |
| Escrita | Somente `010`; endereço/dado capturados na mesma subida | Mudanças externas posteriores não devem substituir os valores capturados |
| Outros comandos | `000`, `011`, `100`, `101`, `110`, `111`: nenhum acesso | Captura inativa não exige apagar conteúdo ou último resultado |
| Registro de saída | Atualiza na descida somente para leitura capturada; conserva o último resultado | Durante nova leitura, DATA pode expor o resultado anterior até a nova captura |
| Máscara viva | Driver habilitado por `READ_Q && !CSb && !OEb && WEb` | Mudar controles vivos pode liberar DATA sem cancelar a operação interna |
| Sem reset | Nenhum reset externo; memória/FF podem começar desconhecidos | Não existe conteúdo zero garantido nem partida universal caracterizada |
| Seleção física | Decoder dinâmico de 33 MOS, keepers, quatro qualificadores e quatro WL drivers | Decoder lógico de referência não substitui esse caminho no SPICE/layout |

A captura é única: 2 FF de endereço, 8 de DIN e 2 de operação na subida;
8 FF de saída na descida, total **20 FF**. O mux de realimentação preserva
o resultado de leitura; não é outra etapa de pipeline. O núcleo físico recebe
`ADDR_Q`, `DIN_Q`, `READ_Q`, `WRITE_Q` e devolve `DOUT_RAW`, sem recapturar
essas requisições num ciclo extra.

Na GLS, `sram_4x8_macro_model.v` representa funcionalmente o armazenamento.
Na integração física, `macro_binding.v` substitui a fronteira por fases,
adaptadores HD e `leaf_fabric` com as folhas reais. A black box de síntese
é apropriada nessa fronteira. O comentário “not bound yet” ainda presente
em `rtl/sram_4x8_macro_bb.v` é histórico/desatualizado; não descreve o estado
do fluxo físico selecionado e não foi corrigido nesta auditoria.

## 2. RTL, síntese e GLS — alcance verificado

### 2.1 Independência e cobertura

O [scoreboard](../../tb/sram_ref_model.sv) mantém seu próprio armazenamento
esperado, flags de palavras escritas e decodificação dos dois comandos válidos.
Não consulta hierarquia interna ou funções do DUT. O
[testbench](../../tb/tb_sram_4x8.sv) altera endereço/dado/controles após a subida,
inspeciona resultado anterior/novo e liberação do barramento, lê posições não
escritas como indefinidas, cobre endereços, 20 padrões dirigidos, os oito
comandos, 64 transições ordenadas e 2.048 operações pseudoaleatórias por run.
Um array esperado em scoreboard é oráculo de teste, não substituto físico.

Foram recalculados os resumos a partir dos logs em
[regressão RTL](../../reports/digital/phase2_review_20261104/results.json),
com `run_digital_regression.reconcile_core_results`:

- **154.303 checks**, cinco execuções de memória (modelos 4/8/16/32 e wrapper
  4×8), mais 96 verificações do controlador incluídas no total.
- Seis profundidades ilegais e seis modelos deliberadamente defeituosos
  produzem as falhas esperadas e identificadas no escopo do scoreboard.
- Os hashes dos logs conferem. O total é número de asserções executadas,
  não número de acessos, amostras físicas ou ensaios independentes.

**Ressalva atual:** `verify_core_inputs` não aprova o conjunto inteiro de
entradas atuais porque o documento de interfaces recebeu seis linhas de
links após o snapshot. O diff e os dois hashes estão em [04, §7](04_technical_evidence_audit.md#7-rastreabilidade-e-achados-transversais).
Todos os demais insumos coincidem, incluindo código/testbench. Logo, a
regressão funcional registrada é sustentada para o mesmo RTL; não se concede
um PASS novo irrestrito ao seu pacote atual de proveniência. Essa distinção
é necessária para não contornar o próprio mecanismo de evidência.

### 2.2 Mapeamento real e tri-state

O auditor `mapped_inventory` foi executado sobre o JSON efetivamente
selecionado em [digital](../../reports/phase2/review_20261104/digital/results.json).
Encontrou 20 `dfxtp_1`, oito `ebufn_1`, oito `clkinv_1`, 16 `mux2_1`, oito
`nand2_1`, dois `nor3b_1` e uma macro SRAM. Não há latch transparente,
primitiva genérica não resolvida ou 32 bitcells convertidas em FF.
Os 20 FF pertencem à interface, não substituem os 32 bits customizados.

Os scripts Yosys usam `tribuf`/techmap próprio, Liberty SKY130HD
TT/25 °C/1,8 V e modelos Verilog HD para simulação. Alimentação e corpos são
ligados explicitamente a VPWR/VPB=VDD e VGND/VNB=VSS. O piloto mapeado contém
um ebufn real e registra **oito checks** de 0/1/Z; seu mutante de polaridade
produz `FATAL ... tri-state DATA=0 expected=z`, não um falso sucesso.

O warning de suporte limitado a tri-state do Yosys foi investigado: a prova
é a célula real mapeada, sua polaridade e o comportamento testado, não a
ausência de warning. As mensagens sobre expressões de células scan não usadas
e tri-states ignorados pelo ABC não significam mapeamento ausente: o ebufn é
preservado pelo mapeamento explícito. Não se descartou warning sem confrontar
a netlist resultante.

Os registros nativos `RESULT` de
[wrapper_gls.txt](../../reports/phase2/review_20261104/digital/wrapper_gls.txt)
e [gls.txt roteado](../../reports/phase2/routed_gls/gls.txt) foram reconciliados
com seus recibos: **15.619 checks por execução**, 2.504 transações, mesma
semente/cobertura. Não se somam para anunciar 31.238 testes exclusivos.
Usam o wrapper/registradores mapeados, modelos HD e macro funcional.
Não é GLS com SDF ou validação da temporização elétrica da macro.

## 3. Clock e controle físico de fases

### 3.1 Origem e representação do clock

O clock de **50 MHz é uma fonte externa ideal da bancada**, descrita por PWL:
20 ns entre subidas, fase alta/baixa de 10 ns, transições de 50 ps. Não é
gerado pela cadeia de inversores. A bancada histórica aguarda a alimentação
e executa ciclos inativos antes do acesso. O
[SDC experimental](../../physical/phase2/experimental.sdc) declara
`create_clock -period 20 -waveform {0 10}`. A origem absoluta do SDC não
descreve a sequência de energização SPICE.

As fontes examinadas identificam 20 ns como condição experimental herdada
do protótipo. **Não se encontrou justificativa quantitativa de sistema para
a escolha de 50 MHz**, nem exigência de tal frequência na proposta oficial.
Não se inventa que decorreu de Fmax, otimização ou orçamento qualificado.
O ensaio demonstra funcionamento nessa condição ideal de interconexão;
não estabelece frequência máxima ou frequência mínima suportada.

O caminho subida→descida dispõe de aproximadamente meio ciclo, mas o dado
deve estar estável no **clock local** do FF, não numa descida pública ideal.
O registrador selecionado é positivo; inversão/distribuição física implementa
a captura pública na descida. O roteamento usa três buffers CTS. A chegada
local foi observada nos transientes extraídos, separadamente do clock público.

O SDC não fornece atrasos externos, uncertainty e arcos/capacitâncias
caracterizados da macro. A Liberty geométrica usada para colocar o fabric
não é uma Liberty temporal qualificada. Não há evidência de STA completo
ou fechamento de timing do caminho de leitura da SRAM.

### 3.2 Relações físicas constatadas

O binding contém 80 inversores HD preservados, com taps **24/40/60/80**.
Eles são posições na cadeia, não tempos em ns. Denotando por Dk o tap k:

```text
valid  = READ_Q OR WRITE_Q
release_phase = CLK AND D24
PRECH = valid AND (release_phase OR D80)    [baixo: pré-carrega/equaliza]
WE    = WRITE_Q AND CLK AND D40
PCLK  = valid AND CLK AND D60               [baixo: pré-carga do decoder]
SCLK  = READ_Q AND D80                      [baixo: amostra; alto: regenera]
ROWr  = DECr AND PCLK
```

São relações de circuito, não um modelo ideal de atrasos garantidos.
[run_phase2_place.py](../../tools/run_phase2_place.py), trecho de proteção/CTS,
impede cancelamento dos inversores e trata as fases como dados/controles.
A propagação de clock é interrompida nos 83 pinos declarados: 80 entradas
da cadeia e três entradas das portas de fase; CTS balanceia CLK, não tenta
balancear PCLK/PRECH/SCLK como
clocks de FF. O histórico de uma rota que introduziu buffers indevidos é
separado do candidato final.

Os riscos conceituais são sensibilidade a slew, cargas, variações de processo,
alimentação/temperatura e RC de fios: as relações dependem de atrasos físicos,
não apenas de equivalência booleana. Nenhum desses riscos é classificado
como defeito nominal sem evidência. As janelas ensaiadas são positivas, mas
não há rastreamento PVT nem adaptação automática de fase demonstrados.

### 3.3 Evolução da sobreposição de pré-carga/escrita

[phase_guard_review/results.json](../../reports/phase2/phase_guard_review/results.json)
foi lido com os hashes de origem e a definição de limiares:

| Contexto | Guarda PRECH80↑ → WE20↑ | Interpretação |
|---|---:|---|
| Piloto inicial `access_pilot_klu` | −232,897 ps | WE começa antes de a pré-carga atingir o nível liberado; tentativa rejeitada |
| Piloto corrigido `access_guard40_pilot` | +167,388 ps | WE deslocado ao tap 40, sem alterar as seis folhas |
| Top final, campanha anterior | Aproximadamente +212 ps | Outro objeto/carga/roteamento; não é o mesmo piloto |
| C1/C2 finais, recalculados agora | +211,3 a +212,9 ps | Mesmos taps atuais, sequência positiva nas escritas observadas |

Os dois primeiros valores foram auditados como evidência histórica identificada;
seus pilotos não foram simulados outra vez. Os números do top final foram
recalculados a partir dos raws. Leitura correta isoladamente teria ocultado a
primeira sobreposição: o histórico ilustra por que se examinam fases internas.
A correção já estava na referência auditada; **não se alterou tap nesta etapa**.

## 4. Sense amplifier e caminho até DATA

O SA selecionado é um latch regenerativo diferencial com amostragem PMOS:
SCLK baixo amostra BL/BLB; SCLK alto inicia a regeneração. A rede real contém
sete MOS por coluna. Sua saída `SA_OUT` é conectada ao `DOUT_RAW` correspondente;
o mux de retenção leva o valor à entrada `FF_D`; o FF positivo com clock
invertido atualiza `FF_Q`; o ebufn entrega o registro ao barramento quando
a máscara permite. Esses pontos não são temporalmente equivalentes.

Nos 15 ciclos de leitura C1/C2, o mínimo diferencial assinado entre os oito
pares por ciclo foi **1,737 V** no cruzamento SCLK20↑ e **1,571 V** 50 ps
antes desse cruzamento. Portanto, os casos observados chegam ao sense com
diferencial já grande e de polaridade correta. Isso sustenta uma ativação
nominal conservadora em relação ao desenvolvimento do diferencial.
Não demonstra offset mínimo, melhor instante possível de sense, SNM, ausência
de kickback fora do caso testado ou oportunidade de otimização comprovada.
SCLK20 é uma referência de medição; a condução analógica não muda idealmente
num único limiar.

Os gráficos existentes [read_path](../../reports/phase2/extension_20261104/figures_revised/read_path.png)
e [capture_to_data](../../reports/phase2/extension_20261104/figures_revised/capture_to_data.png)
são ilustrativos dos raws reais identificados. As conclusões numéricas desta
etapa vieram dos dados completos, não da leitura visual desses PNG.

### 4.1 Medidas nominais recalculadas

Método: `analyze_phase2_extension_timing.measure`, em C1 e C2, antes de
comparar com [timing_final](../../reports/phase2/extension_20261104/timing_final/results.json).
Clock público/local e CSb usam 50%; PRECH liberado/WL válida, 80%; início
WE/SCLK e WL liberada, 20%. Cruzamentos interpolados; validade lógica
baixo −0,18..0,36 V e alto 1,44..1,98 V. O transiente usa passo máximo
10 ps; o início de validade é limitado pela amostragem, não uma precisão
física de frações arbitrárias de ps.

| Medida | Faixa ou mínimo observado C1/C2 | Amostras e significado |
|---|---:|---|
| PRECH80↑ → WE20↑ | 211,3..212,9 ps | 14 escritas; guarda positiva |
| WL80↑ → SCLK20↑ | 238,5..243,9 ps | 15 leituras; WL antes do sense |
| WL20↓ → PRECH80↓ | 2,1962..2,1978 ns | 29 acessos; recuperação |
| WE20↓ → PRECH80↓ | 2,2904..2,2908 ns | 14 escritas; encerramento antes da pré-carga |
| DOUT_RAW válido antes da captura local | Mínimo 7,4346 ns | 120 observações bit/ciclo; valores já estáveis têm limite inferior marcado |
| FF_D válido antes da captura local | Mínimo 7,2402 ns | Mesmas 120 observações; inclui mux/caminho até o FF |
| Clock local50↑ após CLK público50↓ | 0,2301..0,2466 ns | 120 observações; skew/atraso local explícito |
| FF_Q válido após clock local | 0,1900..0,2227 ns | 60 bits que realmente mudaram entre resultados conhecidos |
| DATA válido após CLK público50↓ | **0,4888..0,5488 ns** | Mesmos 60 bits com mudança e driver habilitado; não tEN de saída |

Os 484 screens adicionais de C1 e 336 de C2 foram recalculados sem falhas:
pré-carga dos quatro nós dinâmicos e das 16 bitlines antes de cada acesso,
mais estabilidade posterior de RAW/FF_D. Eles usam os mesmos transientes,
**não são 820 novos acessos elétricos**. Ao menos 2 ns de estabilidade
posterior foi observado na janela inspecionada; não é hold mínimo requerido.

A referência do `dfxtp_1` é o máximo das tabelas Liberty TT/25 °C:
setup 0,6206849 ns e hold positivo 0,1409486 ns. A simulação é TT/**27 °C**.
Comparar esses valores com a janela observada é screening de envelope,
não STA qualificado ou medida de setup/hold público. Não se transforma
7,24 ns de disponibilidade interna em especificação externa do protótipo.

Um ensaio analítico histórico de DATA antes da restauração da máscara viva
foi rejeitado e preservado em `timing_original_access`. Não é falha do DUT:
a bancada mantinha a saída desabilitada naquela janela. A reanálise posterior
`timing_original_internal` restringe-se aos nós internos. C1/C2 medem DATA
com habilitação e janela adequadas; não se usou o resultado antigo inválido
para aprovar ou reprovar o caminho público.

## 5. Barramento e campanhas C1/C2

### 5.1 Hipóteses e cobertura efetiva

Os decks e as expectativas foram confrontados com a
[matriz de cobertura](../phase2_coverage_extension.md), não inferidos dos
nomes dos testes. A função `verify_phase2_extension.verify_case` confirmou
hashes das entradas/modelos, SPICE do mesmo DUT, decks regenerados idênticos,
snapshots, término nativo ngspice, número de linhas, raw, checks e contadores.
O recálculo usou os transientes locais completos:

| Campanha | Hipótese exercitada | Resultado recalculado |
|---|---|---|
| [C1](../../reports/phase2/extension_20261104/c1_sequences/results.json) | Leituras repetidas da mesma linha, escritas complementares adjacentes, READ→WRITE→READ, alternância e retorno de idle; estado conhecido das outras palavras | **1.150 checks, 72 bits lidos incluídos, zero falhas** |
| [C2](../../reports/phase2/extension_20261104/c2_bus/results.json) | Direção/máscara viva, FF_Q retido, habilitação física, mestre externo e correntes sob probes definidos | **1.281 checks, 48 bits lidos incluídos, zero falhas** |

O piloto C1 é subconjunto, não terceira campanha independente. Os contadores
incluem condições internas e bits lidos; estes não são somados novamente.
As outras palavras só têm valor esperado depois de escritas. A netlist DUT
retém os 1.493 MOS/modelos/junções, sem `.ic`, `.nodeset`, fonte interna
impondo Q ou bitcell/sense comportamentais.

Identidades dos transientes efetivamente lidos:

```text
C1 7e11801037e7e1f616d60e47f65fee9e567c9c85d2181429c40e9c89e2197305
C2 e3662caeb1a0b8d816c2825c37b2207127e519d858de9abecb15a4f190f8f071
```

### 5.2 O que as correntes demonstram

Em C2, fontes externas de 0 V medem correntes nos caminhos de mestre/probe.
O mestre usa chave de 1 Ω; o probe de oposição, 1 kΩ; roff=1e12 Ω.
Não há capacitor explícito de carga de DATA e os fios não têm RC detalhado.
O piso de 50 µA corresponde ao desvio instrumental de 50 mV/1 kΩ.
Alta impedância não é inferida de um nó flutuante arbitrário.

Com driver habilitado, o probe oposto causa corrente detectável; com CSb
inativo, a corrente estacionária cai ao piso e DATA acompanha o probe.
FF_Q é observado separadamente e preservado. A carga de oposição pode
retirar DATA da faixa lógica válida enquanto o driver está habilitado:
é **calibração de observabilidade**, não uma operação legal nem aprovação
de capacidade de saída contra carga DC de 1 kΩ.

| Medida C2 recalculada | Observação | Limitação |
|---|---:|---|
| Desabilitação após CSb50↑ | 0,1332..0,1842 ns, 48 observações | Corrente estabilizada abaixo do piso sob probe, não tDIS garantido |
| Reabilitação após CSb50↓ | 0,6288..0,6319 ns, 48 observações | Condução observável sob oposição; não validade lógica completa |
| Separação TE_B80↑ → HOST_EN20↑ | 0,1259..0,4261 ns, 16 observações | Estímulos com guardas declaradas de 0,3/0,6 ns; não turnaround mínimo |

Nos handoffs executados não houve amostra com mestre forte habilitado
e ebufn ainda habilitado pelos limiares de screening, nem corrente
estacionária de conflito acima do critério. Picos de carga capacitivos não
foram chamados automaticamente de contenção. Isso não prova ausência de
condução simultânea para qualquer slew/guarda, nem leakage industrial.
O mestre deve respeitar o contrato e esperar a liberação do barramento.

## 6. Validação elétrica anterior e partida

Foram reexecutadas apenas as **análises** dos dados existentes:

| Evidência | Conferência realizada agora | Resultado e alcance |
|---|---|---|
| [Acesso original](../../reports/phase2/extracted_access_singlethread/results.json) | `audit_phase2.electrical`, inputs/modelos, checks CSV e protocolo contra raw completo | **128 bits lidos + 392 checks de protocolo**, zero falhas; total 520 |
| [Dirigida](../../reports/phase2/review_20261104/directed/results.json) | Hash do raw, recálculo `analyze` e igualdade com checks registrados | **1.332 checks totais, incluindo 160 bits lidos**, zero falhas |
| [Partida reduzida](../../reports/phase2/final_polish_20261104/startup_reduced/results.json) e [estendida](../../reports/phase2/final_polish_20261104/startup_extended/results.json) | `verify_phase2_startup_review.verify_case`, cinco raws, decks regenerados, modelos e checks | **3.383 checks totais, incluindo 240 bits lidos**, cinco cenários sem falhas |

Detalhe da partida recalculada:

| Cenário | Rampa | Capturas inativas adicionais | Checks / bits lidos incluídos | Resultado |
|---|---:|---:|---:|---|
| r1_idle0 | 1 ns | 0 | 637 / 48 | Aprovado nas condições ensaiadas |
| r1_idle2 | 1 ns | 2 | 681 / 48 | Aprovado nas condições ensaiadas |
| r5_idle2 | 5 ns | 2 | 681 / 48 | Aprovado nas condições ensaiadas |
| r10_idle2 | 10 ns | 2 | 681 / 48 | Aprovado nas condições ensaiadas |
| r1_idle3 | 1 ns | 3 | 703 / 48 | Aprovado nas condições ensaiadas |

Mesmo “idle0” espera **9 ns após o fim da rampa** até a primeira subida;
não demonstra funcionamento instantâneo ao energizar. Há escrita inicial
com padrões 00/FF/AA/55 distribuídos pelos quatro endereços, readback,
reescrita complementar, preservação de palavras conhecidas e retorno de idle.
Estados iniciais internos não são impostos. A primeira palavra não escrita
não é obrigada a ter zero. Não se mediram partida mínima universal,
metastabilidade estatística ou distribuição de estados iniciais de fabricação.

Todas as simulações acima são TT, VDD=1,8 V, 27 °C, conectividade e geometria
de junções extraídas. Não são PEX RC detalhado das interconexões. A validade
nominal observada não garante setup/hold externos, Fmax, PVT, potência,
yield ou confiabilidade de fabricação.

## 7. Revisão estrutural e qualidade das evidências

A auditoria independente por terminais/coordenadas é descrita em
[04, §5](04_technical_evidence_audit.md#5-fase-2--cadeia-do-gerador-até-o-bloco-verificado).
Sua contagem foi recalculada com as definições SPICE PDK, não inferida
exclusivamente de um contador do gerador:

| Grupo | MOS |
|---|---:|
| Folhas customizadas selecionadas | 401 |
| 20 FF HD × 24 MOS | 480 |
| Captura/feedback, inversões de clock e tri-state HD | 328 |
| Fases/adaptadores HD, incluindo 80 inversores | 266 |
| 3 buffers CTS × 6 MOS | 18 |
| Controle transistor-level customizado adicional | 0 |
| **Total antes de fusões LVS** | **1.493** |

Os 1.256 taps e 11.439 fillers não acrescentam MOS nas definições SPICE
usadas. O top tem 12.860 instâncias hierárquicas, incluindo esses elementos
e um fabric de 61 folhas; contagem de instâncias não é contagem de MOS.
O LVS compara 1.459 dispositivos equivalentes depois das fusões documentadas.

A segunda análise estrutural demonstra os oito complementos DIN_B, ligação
de saída bit a bit e polaridade da máscara CMOS. Há **oito redes TE_B
distintas**, cada uma implementando a mesma função NAND de READ_Q e live_read.
Um checker histórico que exigia uma rede física única foi corrigido; o
resultado rejeitado continua em `extension_20261104/structure`. Replicação
da função de enable não é defeito do protocolo nem contenção por si só.

Os negativos físicos de gate/bulk/W/L têm falhas nativas no objeto correto;
os oito negativos de adulteração da extensão verificam contador, raw,
estímulo, artefato ausente, circuito, log incompleto, checks e snapshot.
Foram inspecionados código, diagnósticos e identidades preservadas, sem
modificar originais ou executar novamente Netgen. Sete testes leves de
integridade foram executados agora, inclusive alteração de GDS, evidência
ausente, inventário vazio, números não finitos e recibo parcial: todos passam.
São testes de verificadores; não se anunciam como ensaios físicos do DUT.

Os 117 testes Python de uma rodada anterior e os 63 da extensão são registros
de conjuntos e datas distintos, com fixtures sintéticas, testes de metadata
e alguns de ferramentas. Não foram todos reexecutados nesta auditoria nem
somados como evidência elétrica. Quantidade de checks não substitui análise
de estímulos, oracle e cobertura.

### Disponibilidade e reprodução dos dados

O raw original está versionado em gzip lossless. Os raws de partida,
dirigida e C1/C2 estão em `build/phase2/`, ignorados, com índices/hashes e
bundles opcionais locais. Estavam disponíveis e foram lidos integralmente
agora. Um clone sem eles pode conferir identidades/logs/figuras, mas não
recalcular sozinho toda a análise elétrica antes de restaurar o bundle ou
regenerar as campanhas. Recortes CSV/PNG não substituem os transientes.

[clean_extension/results.json](../../reports/phase2/extension_20261104/clean_extension/results.json)
registra worktree limpo em `2397898`, restauração dos três raws, reanálise
e igualdade das quatro tabelas selecionadas. É evidência histórica de
**reanálise com bundle na mesma imagem/PDK**, não regeneração integral SPICE
sem cache, portabilidade Windows ou outro ambiente. Essa reconstrução limpa
não foi repetida nesta etapa.

## 8. Avaliação dos compromissos internos e riscos

| Compromisso | Conclusão desta auditoria | Ressalva |
|---|---|---|
| RTL/protocolo | Implementação e logs funcionais sustentados | Proveniência estrita atual do conjunto RTL rejeita documento modificado após run |
| Síntese/tri-state/GLS | Mapeamento real, macro preservada, 0/1/Z e 15.619 checks sustentados | Zero delay; não STA ou simulação transistor-level |
| Controle/fases físico | Ordem nominal sustentada pelos transientes e recuperação | Cadeia fixa sensível a PVT/RC/slew; não qualificação temporal completa |
| Leitura/escrita integrada | Armazenamento, seleção, diferencial, captura e barramento demonstrados nos casos ensaiados | Interconexão ideal quanto a RC distribuído |
| Partida | Cinco condições demonstradas sem inicialização artificial | Não é tSTARTUP mínimo ou robustez estatística |
| DRC/LVS/GDS | Evidência expandida e ligada ao mesmo top | Limites do deck/modelos, W/L e redução explicitados |
| Reprodutibilidade | Identidades e reanálise atual; reprodução física histórica corroborada | Ambiente Magic lateral e raws opcionais requerem preparo explícito |

Não se encontrou falha funcional nova do circuito selecionado. Permanecem
riscos arquiteturais e limites de caracterização, separados de defeitos
demonstrados. A ressalva de hash documental deve ser resolvida no fluxo de
evidências sem apagar o registro antigo. A aprovação humana dos integrantes
e orientadores continua pendente; este relatório não a substitui.
