# Handoff técnico · Open-Source SRAM Memory Compiler

**Data da auditoria** 22/11/2026. **Branch de trabalho** `integration/phase3-danilo-ss`. **Base conferida** `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.

O melhor checkpoint físico para retomar o projeto é a **macro 4×8 v6 com três StrongARM**, aprovada em DRC/LVS e no C250 pós-layout em TT, SS e FF. A regressão de 18 ciclos da v6 está `NOT_RUN` nos três corners. O fechamento funcional permanece `INCONCLUSIVE` por cobertura. A qualificação elétrica permanece `NOT_CHARACTERIZED` e a Liberty caracterizada está pendente. A geometria **C** original e as variantes investigadas continuam como referências separadas.

O commit de base contém a infraestrutura da Fase 3. A integração da geometria C, a v6, os resultados e parte dos scripts continuam no working tree, em diretórios ignorados e nos pacotes locais. **Preparar o checkout recuperado e validar o inventário é a primeira ação.** A recomendação técnica é estudar oito StrongARM após ratificação da equipe, mantendo o checkpoint de três. [Estado funcional](phase3_fechamento_funcional_strongarm_20261122.md) · [Inventário e recuperação](#parte-l--estado-local-e-recuperação-do-projeto)

## Parte A — Visão geral do projeto

### A1. Objetivo e organização

O projeto desenvolve um compilador aberto que recebe a configuração da memória e gera suas vistas lógicas e físicas de forma reprodutível. A abstração de compilador permite reutilizar células selecionadas, descrever a conectividade estrutural e regenerar hierarquia e modelos ao mudar a profundidade. A geração física depende do empilhamento da matriz, da implementação dos periféricos escaláveis, da integração digital e das verificações de cada configuração.

A tecnologia escolhida é **SKY130A**, com alimentação nominal de núcleo de **1,8 V**. A SRAM é síncrona single-port 1RW. Cada acesso seleciona uma única linha, que contém uma palavra de oito bits. Cada bit usa uma célula estática de seis transistores, formada por dois inversores realimentados e dois transistores de acesso. Há um par diferencial BL/BLB e um circuito de sense por coluna. A interface tem `CLK`, `ADDR`, `CSb`, `OEb`, `WEb`, `DATA[7:0]`, `VDD` e `VSS`. `DATA` é bidirecional e os controles com sufixo `b` são ativos em nível baixo. O 4×8 usa `ADDR[1:0]`. [Especificação §§1–7, 18 e 21](../specs/technical_specification.md) · [Contrato digital](../specs/sram_4x8_digital.md)

| Ferramenta ou vista | Papel no fluxo |
|---|---|
| Python | Seleção de células, geração de matriz/hierarquia e conectividade, montagem de decks, ensaios automatizados, análise e rastreabilidade. |
| Magic | Instancia e roteia a geometria customizada, importa e exporta máscaras, executa DRC e extrai conectividade e parasitas. |
| Netgen | Compara o circuito extraído com a referência esquemática em LVS. Conferir redes, dispositivos e parâmetros, além do relatório de correspondência. |
| ngspice | Resolve o circuito ao nível de transistores com modelos SKY130A e parasitas. Produz tensões, correntes, medidas e waveforms. |
| Yosys | Sintetiza e mapeia a lógica digital para células SKY130HD. A matriz e seus periféricos customizados são integrados como bloco físico. |
| OpenROAD | Posiciona e roteia a lógica digital, trata alimentação e integra o fabric usando abstrações físicas e restrições. |
| Verilog | Modela o comportamento lógico e representa as conexões estruturais para síntese e regressão. Icarus Verilog executa as simulações lógicas. |
| GDSII | Geometria entregue para inspeção de máscaras e verificação física. |
| LEF | Abstração de contorno, pinos e obstruções consumida no floorplan e roteamento. |
| PEX | Netlist extraída, identificada pela geometria e opções de extração, usada nas simulações elétricas pós-layout. |
| Liberty | Modelo de biblioteca com arcos, restrições de tempo e potência para ferramentas digitais. A vista simplificada exigida deve derivar de medidas qualificadas. |

O **núcleo de memória** é a matriz 6T. Os **periféricos customizados** selecionam a linha, condicionam e acionam bitlines e resolvem o diferencial. A **lógica digital** captura comando/endereço/dados, produz os sinais de fase e controla a entrega do resultado ao barramento. O [README](../README.md) descreve a base versionada e o handoff da Fase 2. Os [relatórios de integração da Fase 3](phase3_danilo_ss_integration_20261118.md) e da [v6](phase3_triple_strongarm_20261122.md) registram os avanços físicos locais posteriores.

### A2. Dimensões

| Configuração | Organização prevista | Estado demonstrado no inventário atual |
|---|---|---|
| 4×8 | Quatro linhas × oito bits, 32 bitcells, dois bits de endereço | Referência de integração lógica e física. C e v6 possuem artefatos próprios e evidências elétricas separadas. |
| 8×8 | Oito linhas, 64 bitcells, três bits de endereço | Prevista. Geração física completa, verificação e caracterização desta dimensão pendentes. |
| 16×8 | Dezesseis linhas, 128 bitcells, quatro bits de endereço | Prevista. Geração física completa, verificação e caracterização desta dimensão pendentes. |
| 32×8 | Trinta e duas linhas, 256 bitcells, cinco bits de endereço | Prevista. Geração física completa, verificação e caracterização desta dimensão pendentes. |

A seção 20 da especificação pede resultados de caracterização para pelo menos **8×8 e 32×8**, e a seção 21 prevê as quatro profundidades no compilador. A infraestrutura reconhece esses nomes de configuração. Implementação do decoder maior, geração física e dados experimentais dessas dimensões permanecem entregas próprias. O cronograma histórico previa geração física ampliada na etapa posterior. A ordem e o enquadramento nas entregas precisam ser registrados pela equipe e orientadores. [Especificação §§1, 20–24](../specs/technical_specification.md) · [Contrato de caracterização](phase3_characterization_contract.md) · [Entrega parcial](phase3_entrega_parcial_marco3_20261123.md)

### A3. Como funciona um acesso no 4×8

1. **Captura de entrada.** Na subida de `CLK`, a lógica registra endereço e comando e, em escrita, a palavra conduzida externamente. O decoder dinâmico 2→4 seleciona uma linha sob a fase de avaliação `PCLK`. O driver amplifica o comando da linha até a WL, habilitando os dois MOS de acesso de cada bitcell da linha.
2. **Preparação e leitura.** `PRECH` comanda os PMOS que carregam e equalizam BL/BLB na fase apropriada. Com a pré-carga liberada e WL ativa, a bitcell cria o diferencial. `SCLK` ativa a regeneração. O valor de `SA` segue ao mux de retenção e ao pino `D` do registrador de saída. A captura local corresponde à **descida do CLK público**, com atraso de inversão e distribuição. O `Q` mantém a palavra entre leituras, inclusive com `DATA` em alta impedância.
3. **Escrita.** Os write drivers colocam dados complementares em BL/BLB durante `WE` e a WL selecionada. A mudança de comando vivo após a subida pode desligar a saída externa, enquanto endereço, comando e palavra já capturados governam o acesso em andamento. Após a escrita, a célula preserva o estado por realimentação e a macro retorna à pré-carga.
4. **Propriedade do barramento.** Leitura é `CSb/OEb/WEb = 001` e escrita é `010`. `011` é idle, `000` é inválido e `CSb=1` desabilita. A macro só dirige `DATA` quando **READ_Q e o comando vivo de leitura** estão ativos. Durante escrita, idle, desabilitado e inválido, a saída permanece em alta impedância. Antes de o host dirigir uma escrita ele deve aguardar a liberação efetiva. A partida sem reset externo deixa os conteúdos iniciais indefinidos até condicionamento ou escrita.

Externamente interessam palavras válidas, captura e propriedade. Internamente, as C de bitline, R de interconexão, carga de clock, variação de MOS, slopes, margem do latch e overlap entre drivers determinam se os bits chegam estáveis e se o barramento se libera. A análise elétrica precisa localizar a divergência entre célula, BL/BLB, regeneração, D, Q e pino. `20 ns` de período, `1,8 V` e `27 °C` são condições de ensaio, com limites públicos ainda em caracterização. [Especificação §§4–16](../specs/technical_specification.md) · [Contrato temporal §§2–10](../specs/sram_4x8_timing_contract.md)

## Parte B — Histórico da Fase 3

### B1. Ponto de partida e extração RC

A versão **A** é o protótipo 4×8 direct-abutment da Fase 2, selecionado em `release/phase2_current.json`. O trabalho da Fase 3 tomou a base `89901e7` de `release/phase2-acceptance-20261111`. A teve aceitação experimental nominal com conectividade/junções e sem RC distribuído nas interconexões. Ao incluir RC integral, apareceram atrasos e inversões que o ensaio nominal simples não capturava. O relatório upstream de A registra 32 PASS e 40 FAIL por bit na janela de ensaio. A auditoria reconciliou os casos conhecidos, mas o PEX e waveform exatos desse transiente longo foram documentados como indisponíveis localmente. Ensaios diagnósticos locais de A com RC de sinais e trilhos ideais localizaram vários erros já em D/Q. A comparação apontou `SCLK20` chegando cerca de 214–222 ps antes do `WL80` observado naquele ensaio. Os valores pertencem a A e àquelas sondas. [Seleção da base](../release/phase2_current.json) · [Auditoria de A, B, B′ e C](phase3_auditoria_comparativa_arquitetura_4x8_20261120.md)

### B2. Da contribuição de Danilo à versão C

| Revisão | Identificação | Evidência e alcance |
|---|---|---|
| **A** | 4×8 direct-abutment da Fase 2. `evaluation.C` no tap 60, `ebufn_1` e `dfxtp_1`. | DRC/LVS e nominal históricos. A investigação RC registrou problemas de ordem entre WL e SCLK. |
| **B** | Primeiro ECO físico de Danilo, relatado no ref `origin/feature/phase3-rc-timing-danilo` em `42f0b51`. `evaluation.C` usa tap 48, os inversores de captura usam CLK público e as saídas usam `ebufn_8`. | Relatórios upstream disponíveis. As vistas e waveforms nativos pareáveis dessa revisão foram identificados como indisponíveis no inventário local histórico. O commit final citado atualiza o relatório de corners. |
| **B′** | Reconstrução independente por `tools/rebuild_phase3_danilo_eco.py`, com os mesmos conceitos de controle e `dfxtp_1`. | Vistas e recibos próprios. O ensaio de 170 ns cobre c6/c7. O contraste longo TT de 250 ns com C parou em 85,8258 ns, antes das leituras discriminantes, e ficou inconclusivo. |
| **C** | Variante espaçada `danilo_ss_ff2_spaced`, com `dfxtp_2`, `ebufn_8`, distribuição de DATA, afastamento DATA1/CLK e RC selado. | DRC zero e LVS único históricos, 1.749 MOS. Integrado TT/SS comparável. Controle FF C250 disponível em etapa posterior. Continua como referência de comparação e rollback. |

O tap 48 adiantou a avaliação de linha sem trocar o tap 80 que participa de `sense_drive` e da lógica de pré-carga. A distribuição de captura de saída parte do CLK público. A escolha de `dfxtp_2` e o espaçamento de C pertencem às revisões locais posteriores ao B original. As novas rotas de DATA reduziram comprimento observado e acoplamento com o clock, incluindo `CLK–DATA1`. Essas mudanças permitiram chegar ao controle e à coleta de evidências usados no StrongARM. As escolhas são rastreadas com seus benefícios e riscos. Uma alternativa pode substituir uma decisão de Danilo se a equipe preservar o controle comparável e demonstrar a melhoria. [Reconstrução, rota e RC](phase3_danilo_ss_integration_20261118.md) · [Contraste B′/C](phase3_contraste_b_prime_c_tt_20261121.md)

### B3. Falhas funcionais comprovadas em C

| Corner e fixture de C | Evidência |
|---|---|
| TT integrado e TT C250 | c16/c17 esperavam `0xF0` e produziram `0xF8`. A divergência é DATA3, na linha 3. A célula reteve o estado correto e BLB−BL tinha a polaridade esperada. O latch desenvolveu primeiro o diferencial no sentido favorável, depois inverteu a decisão antes da captura. D, Q e DATA propagaram o bit errado. |
| SS integrado de 18 ciclos | 9/9 leituras, 6/6 escritas por readback e 18/18 ciclos de propriedade pelo observador revisado. O resultado vale para C e para as condições registradas. |
| FF C250 pareado sem StrongARM | c15 esperava `0x0F` e produziu `0xCF`, com senses dos bits 6 e 7 incorretos antes de D/Q. c16/c17 também produziram `0xF8` por DATA3. O controle confirmou que a falha dos bits 6 e 7 já ocorria em C original. |

O erro de C é uma decisão lógica errada e sustentada. A ordem dos eventos separa essa falha de atraso isolado no pino. O relatório de entrega parcial com data de apresentação planejada 23/11 registra **C e o corte de 21/11**, anterior aos controles FF e à v6. A ausência de FF naquele relatório era ausência de ensaio integrado na data de corte. O FF posterior é **C250**, que tem escopo próprio. [Localização de DATA3](phase3_data3_tt_snm_piloto_20261120.md) · [TT/SS](phase3_auditoria_temporal_tt_ss_20261121.md) · [Controle FF original](phase3_controle_ff_e_layout_strongarm_20261122.md)

### B4. Investigações que guiaram a arquitetura

| Investigação | O que foi demonstrado e o que ficou em aberto |
|---|---|
| Rotas, cargas e janela de observação | Os ajustes de pino, FF e roteamento distinguiram atraso Q→DATA de decisão errada. As sondas até o sense, D e Q evitaram estudar só a tensão externa. Um resultado de janela diagnóstica permaneceu separado do veredito funcional. |
| Relação WL–SCLK | A ordem de chegada e o estado de NTAIL, SA/SAB e samplers afetam a regeneração. O diferencial instantâneo em BL/BLB explica parte do comportamento e a conclusão causal depende do contraste e das sondas. |
| `+182 ps` no tail | No recorte TT de 59 ns, com c15 de condicionamento, os samplers preservaram as transições e atrasar somente o tail deslocou a inversão sem corrigir c16/c17. |
| `+182 ps` coordenados | O atraso nos dois samplers e no tail corrigiu c16/c17 no recorte. No primeiro 1 µA da cauda houve polarização interna mais favorável que no atraso só do tail, mesmo com amplitude de BLB−BL ligeiramente menor. Isso sustentou a hipótese de temporização coordenada naquele recorte. |
| Drivers locais SCLK v1/v2 | Ambos usaram um inversor assimétrico. O v1 usou `inv_4` e o v2 `inv_2`. Ambos corrigiram c16/c17 em recortes. No v2, D ficou correto por cerca de 4,99 ns até a captura e houve pico do tail em torno de 314 µA, contra cerca de 133 µA do controle do recorte. O preflight de integração ficou `COMPACT_BOUNDARY_PARTIALLY_DEFINED`. Carga, acoplamento, retorno e impedância compartilhados de SCLK/PRECH impediram promover o driver a ECO da macro. |
| Rebalanceamento SA/SAB | Dois buffers desacoplaram a carga identificável do mux, preservaram c15 e recuperação, e c16/c17 continuaram errados naquela configuração. `REBALANCE_NOT_SUFFICIENT` é do contraste com aquela fronteira e buffers. |
| StrongARM em recortes | A topologia de 11 MOS funcionou em TT de coluna ativa 4×1 com entrada de SCLK histórica. A captura de sinais internos recuperou uma referência de SCLK da macro C. O controle reduzido do acionador com terminações representativas na rede compartilhada ficou `BOUNDARY_NOT_DEFENSIBLE`. A validação avançou com ECO virtual dentro da macro completa. |
| Um StrongARM em DATA3 | O ECO virtual corrigiu DATA3 em TT/SS/FF. O FF continuou a falhar nos senses nativos 6/7 em c15, reproduzindo o defeito preexistente de C. A célula StrongARM isolada obteve DRC zero, LVS único, PEX distribuído e PASS em TT na coluna ativa. |
| Três StrongARM | O ECO virtual em 3/6/7 corrigiu todas as palavras da C250 nos três corners. A integração física v6 teve DRC/LVS, PEX próprio e C250 pós-layout TT/SS/FF posteriormente aprovados. |

Os rótulos A/B/C da auditoria de contraste de **sinais do sense** se referem a ensaios da mesma geometria C, e se distinguem das revisões físicas A/B/B′/C do histórico. Os drivers v1/v2 e o rebalanceamento permanecem experimentos úteis, preservados fora da macro v6. [Atraso conjunto e tail-only](phase3_auditoria_causal_sense3_tt_20261121.md) · [Driver v1](phase3_driver_local_sclk_tt_20261120.md) · [Driver v2](phase3_driver_local_sclk_v2_tt_20261121.md) · [Limites de integração](phase3_preflight_integracao_sclk_v2_20261121.md) · [Rebalanceamento](phase3_contraste_rebalanceamento_sense3_tt_20261121.md) · [Coluna ativa](phase3_strongarm_coluna_ativa_tt_20261121.md) · [ECO virtual completo](phase3_eco_virtual_strongarm_macro_completa_20261122.md)

## Parte C — Arquitetura física atual

### C1. ECO físico de três StrongARM

| Colunas | Sense ativo por coluna |
|---|---|
| 0, 1, 2, 4, 5 | Sense original de 7 MOS com amostragem PMOS e latch regenerativo. |
| 3, 6, 7 | StrongARM de 11 MOS `strongarm_tt_v0`. |

A macro usa duas arquiteturas de sense amplifier e **um sense ativo por coluna**. As 32 bitcells continuam com a topologia 6T. A nova célula recebe BL/BLB, SCLK, VDD e VSS e produz SA/SAB complementares. Em `SCLK` baixo quatro PMOS reinicializam os nós intermediários e regenerativos e o tail fica desligado. Na avaliação, o tail habilita o caminho de descarga, a diferença BL/BLB polariza os dois ramos e o latch regenera a decisão. A polaridade de `SA` é compatível com a rota antiga até o mux. Cada uma das três células tem dois `sky130_fd_sc_hd__buf_1` explícitos, um para SA e um para SAB. SA segue ao `DOUT` antigo, mux de retenção e FF de captura, e o complemento bufferizado termina em rota local. O clock e a alimentação vêm da rede física compartilhada de C. Os drivers locais v1/v2 ficaram fora da topologia integrada. O esquema de referência tem cabeçalho `strongarm_tt_v0 BL BLB SCLK VDD VSS SA SAB`. [Esquema SPICE da célula](../build/phase3/strongarm_isolated_and_native_ff_20261122/physical/reference.spice) · [ECO v6](phase3_triple_strongarm_20261122.md)

A colocação reutilizou a hierarquia e o contorno da macro C. A revisão substituiu a estrutura `leaf_fabric` no GDS, preservando o nível superior, as bitcells, a lógica, os cinco senses originais e os caminhos públicos. O script `physical/fabric_v6/fabric.tcl` instancia o arranjo e os núcleos StrongARM na faixa junto aos periféricos. A etapa física ajustou os escapes de metal e os retornos locais de VSS. Após reimportar o GDS, quatro contatos externos de dreno/fonte PMOS por buffer foram afastados 10 nm dos gates com extensão do enclosure de difusão. Os W/L e o núcleo StrongARM permaneceram os mesmos. O LEF manteve 16 pinos e os obstáculos existentes, conferidos contra a geometria v6 e lidos pelo OpenROAD. [Mapa de colocação](../build/phase3/strongarm_triple_20261122/physical/fabric_v6/placement.json) · [Relatório de integração física](phase3_triple_strongarm_20261122.md)

### C2. Validação física e efeitos de carga

O GDS v6 integrado e reimportado tem contorno **540 × 380 µm**, **DRC zero** e **LVS com correspondência única**. A extração distribuída tem **1.785 MOS, 16.442 resistores e 12.612 cartões C**. Desses cartões, 10.556 são positivos e 2.056 têm valor zero. A auditoria conferiu 5.247 pares em relação à exportação capacitiva após restaurar os valores subattofarad registrados na extração bruta. A visão DC do PEX com resistores contraídos também teve LVS único, com VDD e VSS separados. A normalização dos 16 pinos entre a exportação e o binding preserva os cartões elétricos. Esses recibos pertencem à v6 e documentam geometria, conectividade e extração, com caracterização elétrica futura. [Recibo GDS/DRC/LVS](../build/phase3/strongarm_triple_20261122/physical/macro_v6/gds_check/results.json) · [Manifesto PEX](../build/phase3/strongarm_triple_20261122/physical/pex_verified/manifest.json)

O inventário extraído de **C original → v6 física** mede a capacitância explícita incidente na rede resistivamente conectada de SCLK **134,40 → 151,21 fF**. O acoplamento explícito para PRECH permaneceu em torno de **7,54 fF**. As somas são de placas que cruzam grupos resistivos e excluem a capacitância intrínseca dos MOS. O modelo distribuído, os estados de comutação e o acoplamento determinam o atraso e a corrente reais. O resultado compara estas duas geometrias e não autoriza extrapolar carga, atraso ou corrente para oito StrongARM. [Inventário de cargas C/v6](../build/phase3/strongarm_triple_20261122/physical/extracted_loads.json)

### C3. Caminhos e identidades

Os caminhos abreviados nesta seção usam `T=build/phase3/strongarm_triple_20261122` e `F=build/phase3/strongarm_functional_closure_20261122`. O inventário de transferência registra os caminhos completos, tamanhos e SHA-256 das evidências, incluindo logs.

| Artefato | Caminho sob o checkout | SHA-256 ou recibo |
|---|---|---|
| GDS integrado v6 | `T/physical/macro_v6/sram_4x8.gds` | `315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37` |
| LEF v6 | `T/physical/macro_v6/sram_4x8.lef` | `39f09e853f89e7693523588c5c2d28fb217c8c9710fd18cd09b2bd813be0d5c7` |
| PEX físico v6 | `T/physical/pex_verified/extracted_rc.spice` | `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f` |
| Binding pós-layout comum | `T/physical_qualification/FF/binding.spice`, `F/c250/{TT,SS}/binding.spice`, `F/integrated/TT/binding.spice` | `3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d` |
| Fonte de layout e referência LVS | `T/physical/fabric_v6/{fabric_hier.mag,fabric.tcl,placement.json}`, `T/physical/macro_v6/macro_reference.spice` | Inventário `artifact_map.csv` e manifesto de GDS `results.json` |
| DRC e LVS da macro | `T/physical/macro_v6/gds_check/{magic.log,lvs_verified.log,results.json}` | SHA no `results.json`, ligado ao GDS acima |
| LEF e correspondência PEX | `T/physical/macro_v6/{lef_delta.json,lef_openroad.log}`, `T/physical/pex_verified/{manifest.json,dc_lvs.log}` | SHA do GDS, do LEF e do PEX cruzados em `F/identity.json` |
| C original | `reports/phase2/local/phase3_danilo_ss_ff2_spaced_{gds,lef}/` e `build/phase3/danilo_ss_ff2_spaced_pex_sealed/` | GDS `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365`, PEX `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |

Em SPICE, respeitar a ordem `ADDR0 ADDR1 CLK CSb DATA0 … DATA7 OEb VDD VSS WEb` no binding. Usar `map.json` para as sondas correspondentes ao PEX da variante. Um nome `rc…` identificado em C e um `pnode…` identificado no binding v6 são endereços de observação de netlists específicas. [Auditoria física de v6](../build/phase3/strongarm_functional_closure_20261122/identity.json)

## Parte D — Situação funcional atual

| Corner | C250 pós-layout v6 | Escritas | Leituras | Menor margem conjunta SA/SAB e D até a captura | Regressão v6 de 18 ciclos |
|---|---|---:|---:|---:|---|
| TT | PASS | 6/6 | 4/4 | 4,609 ns | `NOT_RUN` |
| SS | PASS | 6/6 | 4/4 | 1,827 ns | `NOT_RUN` |
| FF | PASS, replay do waveform selado | 6/6 | 4/4 | 6,116 ns | `NOT_RUN` |

Nos três corners c14–c17 retornaram **`0xAA`, `0x0F`, `0xF0`, `0xF0`**. Os oito caminhos passaram em D/Q e DATA e os 48 pares Q/QB relativos às seis escritas preservaram o estado nas janelas observadas. A C250 escreve nas quatro linhas e lê três. A cobertura de leitura das quatro linhas e a propriedade em todos os handoffs dependem da fixture de 18 ciclos. O C250 usou os modelos SKY130A em 1,8 V e 27 °C, Gear/KLU e passo máximo de 25 ps. Ausência de oposição sustentada durante as escritas normais e host aberto durante a leitura foram observados no C250. [Relatório de fechamento C250](phase3_fechamento_funcional_strongarm_20261122.md) · [Resultado estruturado](../build/phase3/strongarm_functional_closure_20261122/results.json)

A simultaneidade tail/reset na subida, medida com marcador diagnóstico de 1 µA, foi **186–234 ps em TT**, **109–186 ps em SS** e **453–468 ps em FF**. Os picos observados de tail chegaram a 119,9 µA, 82,5 µA e 158,7 µA, respectivamente. O observador confirmou a recuperação do StrongARM e das BL/BLB após as leituras. Não observou overlap tail/pré-carga na queda nesses pontos com o mesmo marcador. As métricas servem para comparação, com potência, energia e efeito PVT sujeitos à caracterização. [Medições por bit](../build/phase3/strongarm_functional_closure_20261122/electrical_by_lane.csv)

**Custo registrado.** O TT completo da v6 levou cerca de 65 min, SS cerca de 70 min e FF histórico 46 min 34 s. A primeira tentativa TT parou em 67,1 ns por desligamento do host e foi repetida com o deck e o binding idênticos. O contêiner voltou pelo launcher, com recuperação da montagem de Xauthority. O intervalo até retomar a execução ficou fora da janela ativa da campanha. Após SS, a projeção do integrado TT de 370 ns era **101,8 min** e restavam **87,1 min** ativos. O lançamento foi adiado. O deck integrado TT está preparado e preserva operações, guarda de 1,5 ns e sondas de observação. A projeção usou tempos medidos naquele notebook e poderá variar com o ambiente. [Registro de progressão](../build/phase3/strongarm_functional_closure_20261122/campaign.jsonl) · [Retomada](../build/phase3/strongarm_functional_closure_20261122/REPRODUCAO.md)

A entrega de C250 nos três corners é um marco experimental concluído. Para considerar a candidata final funcionalmente validada no escopo do projeto, faltam as evidências do protocolo integrado, nove palavras de leitura, seis escritas com readback, cobertura das quatro linhas e propriedade nos 18 ciclos. A qualificação elétrica, os limites públicos e a Liberty têm gates adicionais.

## Parte E — Discussão sobre uniformização dos sense amplifiers

### E1. Por que estudar oito StrongARM

Uma arquitetura única por coluna pode reduzir a variação de arcos entre bits por topologia, permitir repetição regular de máscaras e rotas e simplificar a geração por scripts. Também pode reduzir regras especiais de seleção de colunas, aumentar a reutilização de testes e modelos, diminuir o custo de manutenção e facilitar a estrutura das tabelas de caracterização. A regularidade pode ajudar quando o compilador passa a atender outras profundidades. Esses são **benefícios esperados**, sujeitos a medições. Aumentar a profundidade ainda muda o comprimento e a carga de BL/BLB, mesmo com a largura de oito bits preservada.

### E2. Riscos e evidência disponível

As cinco substituições restantes mudariam a distribuição de capacitâncias, as cargas intrínsecas de gate e a impedância vista pelo driver de SCLK. A forma da borda, atraso e skew até cada coluna podem mudar, assim como acoplamento e recuperação relativos a PRECH. A topologia de entrada também pode alterar a carga de BL/BLB e o kickback, e o reset interno pode mudar corrente dinâmica, pico de tail, droop de VDD/VSS e tempo de retorno dos nós regenerativos. A célula e seus buffers ocupam espaço e impõem novos escapes, conexões de alimentação e obstáculos para roteamento.

As medidas **134,40 → 151,21 fF** de capacitância explícita incidente em SCLK comparam **C original e v6 física de três StrongARM**. A soma exclui as capacitâncias intrínsecas e não representa por si só C efetiva, slew ou corrente. O efeito de adicionar mais cinco células depende do mapa físico, dos ramos retirados, de acoplamentos, da rede de distribuição e das condições de bias. Três células aprovadas em C250 sustentam o estudo de oito e fixam o controle pareável. [Cargas extraídas](../build/phase3/strongarm_triple_20261122/physical/extracted_loads.json) · [Relatório v6](phase3_triple_strongarm_20261122.md)

### E3. Estado da decisão

**Uniformizar em oito StrongARM é uma direção experimental recomendada, pendente de ratificação pela equipe.** A versão de oito células ainda não foi implementada nem validada. A v6 híbrida de três StrongARM é o melhor checkpoint físico demonstrado em C250. Manter os seus hashes e o ZIP recuperável como fallback e controle comparável. A seleção da arquitetura definitiva requer uma decisão registrada após o experimento e antes de investir na caracterização final.

### E4. Experimento futuro com gates

1. **Selar a referência.** Recuperar v6, C, netlist do núcleo e os dois ZIPs de resultados. Conferir os hashes e o PASS C250 por corner.
2. **Auditar a distribuição.** Mapear os oito ramos de SCLK, os oito pares BL/BLB, retornos, PRECH e mux até D por coluna. Registrar o que permanece, que ramos e terminais antigos saem e que novas cargas interagem. Identificar sondas que referenciam nós removidos.
3. **Montar o ECO virtual.** Criar uma variante isolada com oito núcleos StrongARM idênticos aos selecionados e os buffers explicitamente rastreados. Preservar o circuito público, condicionamento e o procedimento de observação do C250. Fixar D/Q, palavras completas, retenção e recuperação como gates. Auditar a carga comum antes de lançar ngspice.
4. **Comparar os oito bits em TT/SS/FF.** Usar a v6 híbrida como controle. Registrar a decisão antes de D, captura em Q, pinos, margem de regeneração, recuperação, corrente, slew e desvio entre colunas. Entre corners, manter geometria virtual, fixture e observadores, trocando a seção do modelo conforme o manifesto. A primeira divergência sustentada bloqueia a promoção até diagnóstico. Pontos não mensuráveis permanecem `INCONCLUSIVO`.
5. **Integrar fisicamente se houver evidência.** Em nova variante, preservar a referência anterior, produzir fonte Magic/Tcl e GDS, verificar DRC e LVS com a netlist virtual promovida, conferir LEF/pinos e extrair PEX novo pela metodologia selada. Comparar extensão e ocupação antes de considerar compactação.
6. **Validar o PEX da candidata.** Primeiro reproduzir os casos discriminantes C250 e as condições em cada corner. Depois executar a regressão integrada de 18 ciclos nas três seções do modelo, com nove leituras, seis escritas/readbacks e 18 verificações de propriedade. Guardar resultados por lane e por ciclo.

### E5. Ordem das próximas decisões

| Opção | Benefício | Custo e condição |
|---|---|---|
| **A — Completar os 18 ciclos da híbrida** | Aumenta a cobertura da geometria que já tem DRC/LVS/PEX e passa C250 em TT/SS/FF. O deck integrado TT está preparado. | Consome horas de máquina. Uma substituição posterior reinvalida o resultado para o novo PEX. Faz sentido se a equipe precisar primeiro de uma candidata híbrida funcional com cobertura integrada. |
| **B — Investigar a uniformização primeiro** | Permite decidir a arquitetura, usar a híbrida como controle e direcionar a caracterização à geometria escolhida. | Adiciona riscos físicos e elétricos e pode exigir revisões. O primeiro gate é o ECO virtual pareado, com uma decisão após a evidência. |

A recomendação discutida com Leonardo é **priorizar B**, mantendo A executável e a v6 preservada. A equipe precisa ratificar a sequência antes de mudanças arquiteturais. Não foi iniciado nenhum ECO de oito StrongARM nesta auditoria.

## Parte F — Cuidados com falsos erros

A interface consome palavras digitais e exige que o dado pertença à operação certa, no momento de observação aplicável e com a propriedade correta do barramento. O ensaio analógico verifica se níveis e correntes permitem essa decisão. Um cruzamento sozinho descreve um nó em um instante. Ele pode refletir comutação normal, acoplamento, transição de estado ou mudança de carga.

- **Erro funcional verificável.** Estado errado sustentado na célula, sense, D, Q ou DATA no ponto em que o contrato exige o valor, falha de readback ou contenção comprovada. Os `0xF8` e `0xCF` de C são exemplos.
- **Violação temporal verificável.** O valor ou a segurança do barramento chega fora de um requisito explicitamente aplicável. Registrar o ponto físico, borda de referência, banda válida, estabilidade e a fonte desse requisito. O valor público de `tREAD_VALID`, o pior disable e os tempos de setup/hold ainda precisam de caracterização e homologação.
- **Métrica diagnóstica.** Os limiares 20/80% de VDD e as janelas da fixture ajudam a observar resolução. As correntes de referência de 1 µA para simultaneidade interna e de 50 µA em sonda de 1 kΩ para o barramento são marcadores de ensaio. Ausência de evidência suficiente recebe `INCONCLUSIVO`, por exemplo quando o waveform não confirma duração ou quando a informação se reduz a uma excursão ambígua.

**Caso DATA7.** Em C integrado SS, os sete FAILs por bit na janela de ±100 ps ocorreram em c6/c7/c11/c13/c14/c15/c16. As palavras foram verificadas completas em intervalos estáveis no ponto funcional antes da sonda. O resultado legado permanece no CSV. A revisão de propriedade separa corrente de deslocamento de oposição entre drivers usando tensão, `TE_B`, polaridade, três amostras nativas e pelo menos 50 ps de testemunho. Preserva 15 PASS e três INCONCLUSIVO do observador original e registra 18 PASS para a revisão. [Relatório integrado de C](phase3_validacao_integrada_ss_20261119.md) · [Auditoria de barramento](phase3_fechamento_barramento_ss_20261120.md)

**Caso das guardas.** O controle de estresse com guarda de 300 ps em C SS comprovou sobreposição de condução macro/host. O controle de 1,5 ns demonstrou liberação antes da tomada pelo host e ausência de sobreposição no escopo ensaiado. A guarda de **1,5 ns** integra a fixture congelada, com os limites de produto ainda pendentes e a v6 sem regressão equivalente executada. [Auditoria 300 ps/1,5 ns](phase3_fechamento_barramento_ss_20261120.md#3-validação-cruzada-nos-18-ciclos) · [Contrato §6](../specs/sram_4x8_timing_contract.md#6-troca-de-direção-do-barramento)

| Estado | Política |
|---|---|
| `PASS` | Evidência suficiente de que o requisito aplicável foi atendido, com o valor, a estabilidade e o intervalo exigidos. |
| `FAIL` | Violação real demonstrada. Corrigir o diagnóstico, localizar o primeiro desvio e preservar o caso mesmo se a diferença de tempo ou tensão for pequena. |
| `INCONCLUSIVO` | Dados insuficientes ou ambíguos. Identificar o marcador ou observação que falta e preferir investigação offline antes de repetir uma simulação. |

Use os oito bits simultaneamente para `tACCESS` e o `DATA50` de um bit que realmente comuta para `tCLK_TO_DATA`. Durante a leitura, a palavra anterior pode estar em DATA antes de Q ser atualizado. Para validar a nova palavra, primeiro confirmar SA, D na captura local, Q e estabilidade de DATA antes da sonda. [Contrato temporal §§3, 4 e 8](../specs/sram_4x8_timing_contract.md) · [Contrato de caracterização](phase3_characterization_contract.md)

## Parte G — Monte Carlo e SNM

A campanha experimental foi da **bitcell 6T esquemática** em SKY130A, `tt_mm`, **1,8 V**, **27 °C** e 1.801 pontos de DC por curva com passo de 1 mV. Hold usa WL desativada. Read usa WL ativa e bitlines em VDD na bancada de SNM. PVT seleciona condições de processo global, tensão e temperatura. Mismatch modela diferenças locais de parâmetros entre dispositivos. Nesse `tt_mm`, a base de FET é TT, mismatch local está ativo e a variação global de processo está desativada. Dados históricos `sf_mm` pertencem a outro domínio e permanecem separados.

A SNM mede a estabilidade estática da célula pelo método VTC/butterfly. As curvas de transferência e as curvas espelhadas delimitam dois lóbulos. O maior quadrado inscrito define a margem de cada lóbulo. A menor das duas margens caracteriza a condição simulada. A recuperação offline certificou três cruzamentos dos interpolantes monotônicos, considerando o arredondamento da exportação, e aplicou o mesmo método geométrico. O erro de quantização do arquivo e as limitações da discretização física são fontes distintas de incerteza. [Método e auditoria](phase3_sclk_preflight_auditoria_snm_20261120.md)

| Modo | Válidas originais → auditadas | Média SNM | Desvio-padrão amostral |
|---|---:|---:|---:|
| Hold | 200 → 200 | 684,740 mV | 8,473 mV |
| Read | 200 → 206 | 409,756 mV | 10,761 mV |

As seis seeds Read **30005, 30021, 30053, 30090, 30148 e 30192** foram originalmente rejeitadas por ambiguidade numérica nas extremidades dos lóbulos. O replay das VTCs arquivadas recuperou a classificação sem executar seeds novas. O histórico de rejeição, os valores originais e as estatísticas da amostra ampliada coexistem no recibo. Existem 406 curvas com resultados auditáveis, suficientes para o mínimo experimental de 200 por modo. A campanha autoriza afirmar a SNM no domínio esquemático ensaiado. A validade estatística para a macro pós-layout, rendimento, variação global e condições adicionais depende de nova justificativa e decisão dos orientadores. [Auditoria por seed](../build/phase3/snm_endpoints_final_20261120/audit.json) · [Recibo de reprodução](../build/phase3/snm_endpoints_final_20261120/reproduction.json)

**Pendências com orientadores.** Homologar a seção de modelos, ponto nominal, população e escopo da amostragem. Definir se a próxima entrega requer ensaio da bitcell extraída ou outro nível e condições. Confirmar a temperatura nominal oficial, a meta de robustez entre desempenho/potência/área e a estratégia e cronograma de decoder para 8×8–32×8. Preservar os 200 Hold e 206 Read antes de abrir qualquer trabalho novo de Monte Carlo. [Especificação §§20 e 24](../specs/technical_specification.md)

## Parte H — Matriz de requisitos da Fase 3

Estados de PASS desta matriz sempre referem-se ao artefato e à janela indicados. Os dados diagnósticos de C podem orientar a configuração, enquanto os números finais precisam vir da geometria aprovada. Congelar a versão física antes de gerar a Liberty definitiva.

| Nº | Requisito | Estado atual | Evidência | Próxima ação | Dependências | Critério de conclusão |
|---:|---|---|---|---|---|---|
| 1 | Seleção do sense definitivo | `PENDENTE DE DECISÃO` | v6 híbrida C250 PASS. Uniformização proposta. | Ratificar A/B em reunião e, se B, preparar ECO virtual pareado. | Checkout recuperado, baseline e critérios de E. | Decisão registrada com resultados por bit em TT/SS/FF, trade-offs e fallback. |
| 2 | Integração física | Implementada para v6 experimental | GDS `macro_v6`, `fabric_v6`, mapa de células. | Se houver outra arquitetura, gerar nova variante, com scripts e pinos identificados. | Gate funcional virtual e escolha de arquitetura. | GDS/LEF/netlist e construção reproduzíveis, sem descaracterizar o contrato. |
| 3 | DRC | PASS da v6 | `gds_check/magic.log`, zero. | Repetir apenas em nova geometria ou se prova física estiver inválida. | GDS reimportado e techfile SKY130A fixado. | Zero violações registradas, com hash e ambiente. |
| 4 | LVS | PASS da v6 | `lvs_verified.log`, `dc_lvs.log`, únicos. | Comparar extraído e referência se houver versão nova. | Netlist de referência revisada e GDS com identidade. | Correspondência única de redes/dispositivos e parâmetros aprovados. |
| 5 | PEX | Distribuído e selado para v6 | `pex_verified/manifest.json`, 1.785 MOS, 16.442 R, 12.612 C. | Arquivar identidade e extrair novamente caso a geometria mude. | GDS com DRC/LVS e opções pinadas. | Hashes cruzados GDS–LEF–PEX, binding e auditoria RC aprovados. |
| 6 | Validação pós-layout TT/SS/FF | PASS C250 v6 | `F/c250/*/qualification.json` e FF selado anterior. | Usar resultados como controle e ampliar cobertura. | Mesmo PEX e protocolo por corner. | PVT funcional ensaiado nas fixtures aprovadas da candidata final. |
| 7 | Regressão integrada | `NOT_RUN` para v6, TT/SS/FF | `F/integrated/TT/preflight.json`, não há recibo de simulação. | TT em nova janela, depois SS e FF conforme gates ou em nova candidata aprovada. | C250 PASS e arquitetura selecionada, orçamento e modelos. | Nove leituras corretas, seis escritas com readback, quatro linhas e retenção nos três corners. |
| 8 | Propriedade do barramento | C SS 18/18, v6 integrado pendente | `review_phase3_bus_ss.py`, controles de 300 ps e 1,5 ns, C250 de v6 só cobertura complementar. | Executar revisão de propriedade no integrado da candidata. | Guarda histórica e sondas `TE_B`, host, macro e weak. | Drive/liberação e alta impedância testemunhados nos 18 ciclos, sem contenção sustentada. |
| 9 | Tempo de acesso | Provisório em C para leituras válidas | `phase3_caracterizacao_minima_20261119.md`, contrato e campos `tACCESS`. | Medir da subida pública até a nova palavra inteira válida e estável. | Candidata funcional, PEX, observador por palavra e pontos PVT/slew/carga. | Matriz validada, falhas e releituras sem comutação separadas. |
| 10 | Tempo de desabilitação | Diagnóstico em C SS | Sonda e controle de `CSb/OEb/WEb` do relatório de caracterização mínima. | Medir cruzamentos dos controles e liberação sustentada, por espécie de arco e polaridade. | Contrato, PEX final, carga e guardas. | Determinar pior liberação no domínio aprovado com evidência de Hi-Z. |
| 11 | Setup | Pendente | Margens internas de D em C250 e limites ainda abertos em §8 do contrato temporal. | Aproximar cada entrada de captura e medir primeira perda de operação válida. | Critérios e banda homologados por clock, entrada e PVT. | Matriz de setup dos pinos capturados e validação de fronteira. |
| 12 | Hold | Pendente | Contrato de escrita/leitura e guarda experimental. | Varrer deslocamento após a borda de captura para comando, endereço e DATA de escrita. | Mesma validação de armazenamento e propriedade. | Matriz de hold com região válida e casos censurados/ambíguos registrados. |
| 13 | Potência estática | Pendente | Corrente exploratória de C idle com clock ativo. | Medir alimentação em estado estável, clock parado e estado conhecido. | Domínio aprovado, geometria final e janela de repouso. | Potência estática por estado e corner documentada. |
| 14 | Potência dinâmica | Exploratória em C | Integrais históricas de corrente em janelas de operação. | Separar condições de atividade, clock, carga e repouso. | Estado funcional e sinal de alimentação rastreável. | Potência dinâmica por operação e condição, com baseline e unidade definidos. |
| 15 | Energia por operação | Exploratória em C | Relatório Marco 3 com integrais em 20 ns e alcance provisório. | Integrar potência da fonte em janelas comparáveis de leitura, escrita e idle. | Definir fronteiras de pré-carga/clock e separação de leakage. | Energia estimada por operação reproduzível, válida para cada ponto. |
| 16 | SNM | Hold 200 e Read 206, experimental | `snm_endpoints_final_20261120/audit.json`. | Preservar VTCs e decidir recortes estático e pós-layout que a entrega exige. | Estratégia e temperatura definidas com orientadores. | Método, domínio e resultados aprovados para o escopo requerido. |
| 17 | Homologação Monte Carlo | Pendente | Campanha esquemática `tt_mm` e auditoria offline de seis seeds Read. | Formalizar mismatch local, variação global, tamanho e alcance das amostras. | Decisão dos orientadores e política de modelos. | Registro aprovado de domínio, número mínimo e interpretação estatística. |
| 18 | Slew e carga | Pontos isolados e estimativas | Contrato propõe 5/10/20 fF. v6 em 10 fF para os ensaios observados. | Fixar a grade por arco e corner e validar pontos-limite. | PEX, setup/hold, `tACCESS`, `tDIS`, potência e protocolo. | Ondas e medidas repetíveis com coordenadas/unidades e cobertura. |
| 19 | Geração Liberty | Pendente | Contrato v1, `.lib` de interface não caracterizada para roteamento da Fase 2. | Gerar vista simplificada dos dados aprovados com semântica de porta/memória. | Matrizes elétricas e domínio da biblioteca. | Arcos e tabelas medidos, compatíveis com os estados de leitura/escrita/tri-state. |
| 20 | Validação Liberty | Pendente | Contrato define consumo futuro. | Analisar sintaxe, unidades, direção, arcos e comparar pontos selecionados com evidência SPICE. | Liberty derivada e validação do modelo Verilog. | Leitura correta em ferramentas-alvo, dados rastreáveis e limites explicitados. |
| 21 | Configurações adicionais | Pendente | Especificação prevê 4/8/16/32 palavras e resultados pelo menos 8×8/32×8. | Planejar decoder maior e geração, DRC/LVS/PEX e validação de cada geometria. | Estratégia de decoder e marcos acordados. | Gerar vistas requeridas e provar caracterização nas dimensões aplicáveis. |
| 22 | Documentação e entrega | Handoff e checkpoints disponíveis. Entrega final pendente. | Este documento, matriz, pacote e recibos históricos. | Versionar fontes/receitas e preparar artefatos aprovados após a decisão da equipe. | Auditoria de transferência, validação e caracterização. | Outro membro reproduz os resultados, revisores aprovam escopo e a entrega identifica sua geometria. |

Quando o candidato final for selecionado, preencher os resultados com a identificação do ensaio, versão, unidade, estado e definição já previstos pelo contrato. Os CSVs da infraestrutura distinguem medida localizada de aprovação funcional da macro e confiança dos limites públicos. [Especificação §§19–21](../specs/technical_specification.md) · [Contrato de caracterização](phase3_characterization_contract.md) · [Tabela histórica de métricas de C](phase3_entrega_parcial_marco3_20261123.md#b4-temporização-potência-e-liberty)

## Parte I — Futuras otimizações de área

### I1. Arranjo conferido na revisão v6

O GDS v6 tem 540 × 380 µm. A leitura estrutural do GDS e a comparação entre `fabric_v6/fabric.tcl` e `fabric_v6/fabric_hier.mag` confirmaram **32 instâncias** e coordenadas idênticas da matriz. `placement.json` fixa a unidade em **5 nm**. `bitcell_6t.mag` registra `FIXED_BBOX 0 0 3450 2800`. O incremento horizontal de 3.450 unidades corresponde a **17,25 µm**, e o vertical de 2.800 a **14,00 µm**. O arranjo ocupa **aproximadamente 138 × 56 µm** pelos limites das instâncias. Seus limites estão abutidos no fabric. A ocupação interna da célula, as separações dos periféricos, as margens da macro, o roteamento e a alimentação têm possibilidades de compactação próprias. [Conferência de pitch/GDS](../build/phase3/handoff_equipe_20261122/layout_eda_identity.json)

### I2. Três níveis planejados

1. **Reposicionar periféricos.** Primeiro estudo de área, contra a geometria funcional aprovada. Reduzir espaçamento entre matriz, precharge, write drivers, senses e demais circuitos. Preservar inicialmente o desenho interno da bitcell. Medir contorno, comprimento de nets críticas, pinos e ocupação. Tratar variações de RC como hipóteses de impacto na leitura.
2. **Compactar a bitcell 6T.** Revisar a geometria interna e o pitch junto aos acessos e regras de DRC. Qualificar DRC/LVS/PVT e as margens pós-layout da folha e matriz que mudaram. O custo inclui novos PEXs e sensibilidade de WR/READ/SNM.
3. **Otimização global.** Reavaliar floorplan, alimentação e retornos, roteamento de sinais, integração da lógica e regras de uso de metal. Manter a interface lógica e comparar resultados físicos e elétricos em variante independente.

### I3. Ordem e automação

**Primeiro fechar a funcionalidade, depois estudar a compactação.** Manter ECOs funcionais e mudanças de posicionamento em variantes separadas, para atribuir diferenças. Para iniciar nível 1, preservar uma geometria com resultados TT/SS/FF e regressão integrada. Movimento que altere geometria, conexão ou parasitas requer repetir os gates afetados, incluindo DRC/LVS/PEX e ensaios comparáveis. A geometria final deve ser definida antes de congelar números de caracterização e Liberty, reduzindo retrabalho.

Python/Tcl descrevem enumeração de células, coordenadas, pitch e ligações. Magic executa as instâncias e o roteamento local do fabric custom. A lógica digital é posicionada e roteada pelo OpenROAD ao redor do bloco com sua abstração LEF e restrições. O floorplan da matriz estabelece dimensões e coordenadas de bitcells, WL, bitlines e periféricos. É uma oportunidade futura parametrizar pitch, ancoragens e escapes por profundidade, em vez de manter valores especiais por coluna e configuração. As coordenadas v6 servem como referência, com parametrização do layout ainda em aberto. [Guia de reprodução da Fase 2](phase2_reproduction_guide.md) · [Scripts e montagem v6](phase3_triple_strongarm_20261122.md)

## Parte J — Procedimentos operacionais

### J1. Ambiente reproduzível

| Componente | Identidade conferida ou evidência |
|---|---|
| Container | `sram-xschem`, imagem `isaiassh/unic-cass-tools:1.0.7`, ID e digest local `sha256:921d95e8cd03b8fbe5cec683ea14add4c1b6e0db1d5d05187fac7deb16b5e0f8`. Checkout montado em `/work`. Registrar o digest e conferir montagem/pré-requisitos no novo host. |
| PDK | `PDK=sky130A`, `PDK_ROOT=/opt/pdks`. O link `/opt/pdks/sky130A` resolve à revisão Volare `0fe599b2afb6708d281543108caf8310912f54af`. Os 319 SHA-256 de `model_hashes.json` de v6 FF conferiram no container atual. O PDK vem do ambiente EDA. |
| SPICE | ngspice **44.2 KLU**, `/opt/ngspice/ngspice-44.2/bin/ngspice`. `run_once.py` lança com `-n -b`. C250 e fixture integrada registram Gear/KLU, modelos, condições e sucesso no recibo da execução. |
| Magic | **8.3.703** na trilha DRC e RC da macro v6, em `build/phase3/magic-8.3.703-opt`. O checkpoint C inclui essa instalação local e seu wrapper `/work/…`. A imagem também tem Magic **8.3.684** em `/opt`, usado em parte do fluxo. Para reproduzir a trilha do GDS v6, seguir os recibos e usar a versão correspondente. |
| Netgen | **1.5.293**, com `/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl`. O DRC usa `/opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc` e sua tecnologia SKY130A. |
| OpenROAD e Yosys | OpenROAD `v2.0-25787-gee9759486` no recibo LEF da v6. Yosys **0.44** na imagem. Uso histórico para implementação da lógica. |
| Visualização e verificação digital | Xschem, Magic, Icarus Verilog e GTKWave disponíveis via launcher. Inspecione a versão local conforme a operação que pretende repetir. |
| Python host | Python 3.12 e NumPy **2.4.6** verificados no host para as análises offline. Os analisadores de v6 usam `numpy.trapezoid`, portanto o replay pede NumPy 2.x. `PYTHONPATH=tools` expõe módulos locais e `PYTHONDONTWRITEBYTECODE=1` evita caches no checkout. |
| Python no EDA | **3.10.12**, NumPy **1.26.4**, gdstk **0.9.62**, Matplotlib **3.10.8**. Use esse ambiente para o runner, geometria e gráficos com dependências verificadas. Use NumPy 2.x para reanalisar integrais e critérios v6, em ambiente analítico separado quando necessário. |

O launcher `tools/sram-eda` ajusta `PATH`, `PDK_ROOT`, `PDK` e valida a montagem. O nome padrão usado pelos scripts de campanha é `sram-xschem`. Em um notebook diferente, criar ou disponibilizar o container com a raiz do checkout correta, mesmo digest ou conteúdo equivalente e os modelos pinados. As regras e o compilador do Magic 8.3.703 foram registrados com a fonte upstream `2c6d97b2f21003fa1778d5658eb02b32724399ab`, configuração Tcl/Tk e `CFLAGS=-O2`. A cópia binária incluída em C pertence ao Linux x86_64 e ao ambiente registrado. Se a plataforma mudar, recompilar com a receita e verificar a identidade declarada. [Ambiente e launcher](../tools/ENVIRONMENT.md) · [Receita Magic](phase3_danilo_ss_integration_20261118.md#reprodução) · [Identidade PDK/pitch](../build/phase3/handoff_equipe_20261122/layout_eda_identity.json)

### J2. Conferir, reproduzir e inspecionar

**Inspeção Git e dos arquivos.** Executar a partir da raiz do checkout.

```bash
git branch --show-current
git rev-parse HEAD
git branch -avv
git status --porcelain=v1 --untracked-files=all
git diff HEAD --stat
git diff --cached --stat
git ls-files --others --exclude-standard
git rev-list --left-right --count HEAD...refs/remotes/origin/feature/phase3-infra-leonardo
```

**Hash e localização de resultados.** Na área que recebeu os quatro pacotes, checar o SHA-256 do ZIP e os hashes internos do pacote novo antes de restaurar. O script de recuperação confere novamente os três ZIPs históricos e cada membro copiado.

```bash
sha256sum -c phase3_handoff_equipe_20261122.zip.sha256
unzip -tq phase3_handoff_equipe_20261122.zip
# Na raiz da cópia extraída do pacote de handoff
sha256sum --quiet -c SHA256SUMS
# Na raiz do checkout recuperado
T=build/phase3/strongarm_triple_20261122
F=build/phase3/strongarm_functional_closure_20261122
sha256sum "$T/physical/macro_v6/sram_4x8.gds" "$T/physical/macro_v6/sram_4x8.lef" \
  "$T/physical/pex_verified/extracted_rc.spice"
python3 -m json.tool "$F/results.json"
python3 -m json.tool "$F/identity.json"
rg --files -g waveform.dat -g currents.dat "$T/physical_qualification" "$F/c250"
```

**Reprodução offline e testes.** Rodar na cópia recuperada ou em uma cópia de ensaio. Os analisadores regeneram JSONs de análise e CSVs. Manter os waveforms e recibos originais intactos. A validação de propriedade histórica vem do waveform de C SS, enquanto o resultado de TT/SS/FF C250 é da v6.

```bash
export PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1
T=build/phase3/strongarm_triple_20261122
F=build/phase3/strongarm_functional_closure_20261122
python3 "$F/closure_prepare.py" identity
python3 "$F/test_closure.py" -v
python3 -m unittest discover -s tests -p 'test_phase3_rc_bus_ss.py' -v
python3 -m unittest discover -s tests -p 'test_phase3_rc_integrated_ss.py' -v
for c in TT SS; do
  python3 "$T/analyze_triple.py" "$F/c250/$c"
done
for c in TT SS FF; do
  python3 "$F/qualify_c250.py" "$c"
done
python3 "$F/electrical_summary.py"
python3 tools/audit_phase3_snm_endpoints.py --build build/phase3 \
  --output build/phase3/handoff_snm_replay_novo
cmp build/phase3/snm_endpoints_final_20261120/audit.json \
    build/phase3/handoff_snm_replay_novo/audit.json
```

**Layouts.** Para abrir a geometria aprovada, usar o GDS `T/physical/macro_v6/sram_4x8.gds`. Para estudar as coordenadas do fabric, usar o MAG hierárquico `T/physical/fabric_v6/fabric_hier.mag`, que precisa das folhas vizinhas. A reimportação preservada está em `T/physical/macro_v6/gds_check/integrated_flat.mag`. Em sessão gráfica, na raiz do checkout:

```bash
./tools/sram-eda magic -rcfile /opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc
```

No console do Magic, ler o GDS e carregar o topo para inspeção. Para o fabric editável, navegar ao diretório `physical/fabric_v6` e carregar `fabric_hier`. Evitar salvar sobre as vistas do checkpoint.

```tcl
gds read build/phase3/strongarm_triple_20261122/physical/macro_v6/sram_4x8.gds
load sram_4x8_wrapper
```

### J3. Execuções demoradas, interrupção e retomada

O ngspice passa por preparação de deck/modelos, solução de ponto de operação, integração transiente, exportação e análise offline. Nos transientes completos houve vários minutos de `DECK_OR_OP` antes da primeira indicação `Reference value`. Verifique log, uso de CPU, tamanho de arquivos e avanço consecutivo do tempo simulado no `progress.jsonl`. Um único valor estacionário ou uma preparação longa não demonstram travamento. Procure ausência persistente de progresso em vários intervalos, erros fatais ou falta de CPU juntamente com falta de avanço. O `monitor_progress.py` registra fase e tempo físico observado, e o recibo final cruza saída do processo, alcance do horizonte, log e waveform. Depois do último `Reference value` ainda pode ocorrer a exportação de `waveform.dat` e `currents.dat`.

O primeiro TT v6 saiu por desligamento do notebook, sem salvar a onda. O replay válido foi um novo lançamento com deck/binding idênticos, mantendo os logs da tentativa. Para ambiente recém-reiniciado, `env -u XAUTHORITY tools/sram-eda ngspice --version` confirma o simulador e usa a recuperação headless documentada da montagem. Os scripts registram tentativas e usam lock para evitar concorrência ou sobreposição de resultados. Uma tentativa existente deve ser diagnosticada e preservada antes de escolher outro diretório de saída. A regra da campanha protege o FF C250 reaproveitado de repetição. Antes de lançar, conferir capacidade, duração estimada e gates já satisfeitos. Quando a execução for adiada, registrar fase, motivo, parâmetros e comando de retomada. [Procedimento da campanha](../build/phase3/strongarm_functional_closure_20261122/REPRODUCAO.md)

**Retomada futura se for aprovada a Opção A.** O comando a seguir é para uma nova janela autorizada. Ele reusa os PASS C250 e admite apenas a primeira regressão integrada TT. Aumente a janela apenas com autorização e considerando tempo medido e recursos. Este comando não foi executado no handoff.

```bash
env -u XAUTHORITY tools/sram-eda ngspice --version
F=build/phase3/strongarm_functional_closure_20261122
PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1 python3 "$F/continue_campaign.py" \
  --until integrated/TT --authorized-minutes 120
```

### J4. Gate para cada nova geometria

Gerar GDS e vistas de referência em variante identificada. Reimportar o GDS e executar DRC. Comparar a conectividade com a referência correspondente em LVS. Extrair PEX novo e conferir GDS–LEF–PEX, pinos, binding e hashes. Aplicar a validação funcional e elétrica pertinente. O `pex_verified` de uma geometria anterior continua útil para replay e comparação. Qualquer mudança de geometria ou conectividade invalida sua aplicação como PEX da nova variante. [Receita v6](../build/phase3/strongarm_triple_20261122/REPRODUCAO.md)

## Parte K — Primeiros passos para o próximo responsável

- [ ] Conferir branch `integration/phase3-danilo-ss` e HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.
- [ ] Identificar os dois diffs rastreados, os arquivos untracked e as dependências ignoradas no inventário.
- [ ] Receber o ZIP novo e os três checkpoints históricos necessários para recuperação.
- [ ] Verificar SHA-256 de pacotes e vistas. Restaurar em checkout separado e validar a `working_tree.patch`.
- [ ] Ler a [especificação](../specs/technical_specification.md) e os [contratos digital](../specs/sram_4x8_digital.md) e [temporal](../specs/sram_4x8_timing_contract.md).
- [ ] Ler este handoff e localizar a [matriz de pendências](#parte-h--matriz-de-requisitos-da-fase-3).
- [ ] Conferir PASS de C250 em TT/SS/FF via replay e a ausência de recibo integrado da v6.
- [ ] Entender as opções A e B para os sentidos de leitura e as diferenças entre C e v6.
- [ ] Ratificar com a equipe se a ordem será cobertura integrada da híbrida ou estudo de oito StrongARM primeiro.
- [ ] Escolher uma única tarefa técnica autorizada, com ganho de informação e custo conhecidos.
- [ ] Registrar os critérios de `PASS`, `FAIL` e `INCONCLUSIVO` antes de executar.
- [ ] Preservar hashes, artefatos, v6 e C como referências anteriores.
- [ ] Executar a etapa escolhida, registrar ambiente, progresso, medição e limites.
- [ ] Documentar o resultado e comunicá-lo à equipe, com decisão de continuar ou bloquear o próximo gate.

**Primeira tarefa sugerida após ratificação de B.** Auditoria das cinco substituições restantes para preparar um ECO virtual de oito StrongARM. Usar a v6, o mapa de ramos extraídos e a referência SPICE da célula de 11 MOS. Entregar um mapa por lane de SCLK/BL/BLB/SA/D, inventário de cargas e sondas válidas e um preflight de fixture congelado. O critério é conseguir explicar cada terminal de conexão e como o resultado será comparado à híbrida, sem alterar a v6. Só depois decidir se o ECO virtual está pronto para simulação. A sugestão fica para a próxima pessoa e não foi executada nesta rodada. Se a equipe ratificar A, iniciar apenas o integrado TT preparado, conforme J3.

## Parte L — Estado local e recuperação do projeto

### L1. Git e comparação de referências

Neste notebook, a branch ativa é `integration/phase3-danilo-ss`, em `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. O índice está limpo. O commit é o fechamento versionado da infraestrutura Fase 3 em 16/11/2026. Nenhum commit posterior ao HEAD registrado nos checkpoints está no topo desta branch. Os avanços físicos e as campanhas posteriores foram mantidos localmente. Não foi encontrado `AGENTS.md` aplicável na raiz ou nos caminhos de trabalho auditados.

| Ref local ou espelho de remoto | Posição conferida | Relação com a base de handoff |
|---|---|---|
| `integration/phase3-danilo-ss` | `8e1d961` | Branch ativa, **sem upstream**. Nenhuma `origin/integration/phase3-danilo-ss` no cache auditado. |
| `feature/phase3-infra-leonardo` e `origin/feature/phase3-infra-leonardo` | `8e1d961` | Base de infraestrutura idêntica. Um clone com acesso a esse ref recupera o commit de base. |
| `origin/feature/phase3-rc-timing-danilo` | `42f0b51` | Histórico de RC de Danilo, divergência de 5 commits do lado da base atual e 11 do lado desse ref. Serve de origem para B. |
| `origin/release/phase2-acceptance-20261111` | `89901e7` | Baseline versionada selecionada para iniciar a Fase 3. |
| `feature/phase2-direct-abutment` | `826978a` | Fonte histórica de A. |
| `origin/main` | `edeeb0b` | Ref cacheado. A base atual tem 40 commits exclusivos e esse ref tem um na comparação simétrica. |

O remoto configurado é `git@github.com:leofernandesc/Open-source-sram-memory-compiler.git`. A auditoria foi offline e compara **refs locais cacheados**. Cabeça e disponibilidade do servidor no instante da transferência ficam `NÃO VERIFICADO` até a próxima pessoa consultar o GitHub. Recusar uma atualização automática para `main` ou uma troca de branch no checkout que guarda alterações locais. Para prosseguir, restaurar a branch a partir do commit exato em um checkout novo. [Refs auditados](../build/phase3/handoff_equipe_20261122/git_refs.txt) · [Estado Git inicial](../build/phase3/handoff_equipe_20261122/git_status_before.txt)

### L2. O que ficou fora do commit

A captura de working tree tem **dois arquivos rastreados modificados**, `.gitignore` e `tools/export_phase2_top_lef.py`. `.gitignore` passa a ignorar `/build/phase3/`. O exportador local acrescenta `--verified-geometry`, verifica o GDS por hash e exige um novo diretório de saída local. A `working_tree.patch` preserva as duas mudanças e o índice vazio foi registrado. Há **117 arquivos não rastreados preexistentes**. São **47 em `tools/`, 27 em `tests/`, 41 em `docs/` e 2 em `characterization/phase3/experiments/`**. Este novo Markdown é a única adição visível no status Git desta rodada. Os helpers e recibos novos estão no diretório ignorado `build/phase3/handoff_equipe_20261122/`.

A auditoria contabilizou **29.062 caminhos ignorados preexistentes**. O agrupamento por diretório está em `ignored_groups.csv`. A seleção explícita para transferência está em `artifact_map.csv` e `recovery.json`. Caches, intermediários e demais ensaios exploratórios mantidos no notebook ficam separados do conjunto restaurável. O inventário inclui artefatos grandes por SHA-256, tamanho, membro e pacote. Algumas instruções e recibos históricos de restauração só existem no ZIP fonte, por exemplo `restauro/LEIA-ME.md` e `restauro/checkpoint_recheck.json` do checkpoint C. `zip_only.csv` lista ausências no caminho auditado, sem inferir que uma cópia com outro nome seja impossível. [Working tree](../build/phase3/handoff_equipe_20261122/working_tree.csv) · [Mapa de artefatos](../build/phase3/handoff_equipe_20261122/artifact_map.csv) · [Ocorrências só em ZIP](../build/phase3/handoff_equipe_20261122/zip_only.csv)

| Item | Caminho | Git rastreia? | Disponível no remoto? | Necessário para reprodução? | Como recuperar? |
|---|---|---|---|---|---|
| Código base e contratos | `README.md`, `specs/`, `release/`, `tools/run_phase3.py`, `tools/phase3/` | Sim, no HEAD | Base presente no ref cacheado `origin/feature/phase3-infra-leonardo` | Sim | Clone e selecionar o SHA exato. |
| Patch do checkout | `.gitignore`, `tools/export_phase2_top_lef.py` | Arquivos base sim, diffs locais | Base em Git, diffs fora do HEAD | Sim para estado completo e extensão do exportador | `working_tree.patch`, verificação de hash e aplicação em cópia. |
| Código de integração e análise local | `tools/rebuild_phase3_danilo_eco.py`, `tools/run_phase3_eco_pex.py`, `tools/analyze_phase3_integrated_ss.py`, `tools/review_phase3_bus_ss.py`, `tools/{run_phase3_snm,phase3_snm_measure,audit_phase3_snm_endpoints}.py` e demais 47 | Não | Fora da base cacheada | Sim para reprodução e manutenção | Incluído no ZIP novo com lista exata de 117 e SHA por arquivo. |
| Testes, docs históricos e netlists de experimento | `tests/test_phase3_*.py`, `docs/phase3_*`, `characterization/phase3/experiments/sclk_local_driver_{v1,v2}.spice` | Os 27 testes, 41 docs novos e dois experimentos listados são untracked | Fora da base cacheada | Sim para rastreabilidade e testes relevantes | Incluídos no ZIP novo. Preservar o caráter experimental dos drivers. |
| Scripts e base física da v6 | `T/{prepare_triple.py,run_once.py,monitor_progress.py,analyze_triple.py}`, `T/physical/` | Não, ignorados | Fora da base cacheada | Sim | ZIP `triple_strongarm`; `recovery.json` escolhe membros com digest exato. Contém fonte Magic/Tcl, mapa, netlists e provas de v6. |
| GDS, LEF e PEX físicos | `T/physical/macro_v6/`, `T/physical/pex_verified/` | Não, ignorados | Fora da base cacheada | Sim para identidade, simulação e variante | ZIP `triple_strongarm`; usar hashes da Parte C e não trocar por PEX virtual. |
| Núcleo StrongARM e controle FF C | `build/phase3/strongarm_isolated_and_native_ff_20261122/physical/`, `FF_native/` | Não, ignorados | Fora da base cacheada | Sim para auditar a linhagem e montar novo ECO virtual | Componentes essenciais em `triple_strongarm`. ZIP `controle_ff_e_layout_strongarm` é complementar para o signoff isolado, experimentos e ondas adicionais. |
| Binding, decks e fixture corrente | `F/c250/{TT,SS}/`, `T/physical_qualification/FF/`, `F/integrated/TT/`, `build/phase3/integrated_ss_20261119_preflight/fixture.json` | Não, ignorados | Fora da base cacheada | Sim | ZIP de fechamento, ZIP triplo e checkpoint C. O integrado TT tem preflight v6, sem simulação. |
| Waveforms, correntes e logs essenciais | `F/c250/{TT,SS}/{waveform.dat,currents.dat,ngspice.log}`, equivalentes no FF físico e nos controles de C | Não, ignorados | Fora da base cacheada | Sim para auditoria/replay | Membros e arquivos exatos em `critical_files.csv` e `artifact_map.csv`. Nunca repetir SPICE só para recuperar uma forma de onda íntegra. |
| Resultados JSON/CSV e manifestos | `F/{results.json,identity.json,electrical_by_lane.csv,artifact_manifest.json}`, análises por corner, `T/manifest.json` | Não, ignorados | Fora da base cacheada | Sim | ZIP de fechamento e ZIP triplo. Conferir hashes antes da análise e usar cópia para reescrever derivados. |
| Checkpoint C e infraestrutura de teste | `reports/phase2/local/phase3_danilo_ss_ff2_spaced_*`, `build/phase3/danilo_ss_ff2_spaced_pex_sealed/`, integrados de C | Não, ignorados | Fora da base cacheada | Sim para controle comparável e recuperação de dependências | ZIP `checkpoint_C` e componentes de C também no ZIP triplo. |
| SNM completo | `build/phase3/snm_nominal_{hold,read}_batch01_20261120/`, `snm_campaign_results_20261120/`, `snm_endpoints_final_20261120/` | Não, ignorados | Fora da base cacheada | Sim para preservar 406 amostras e reanalisar | ZIP `checkpoint_C`; dados extraídos e auditoria revisada disponíveis sem rerun. |
| Executável Magic otimizado | `build/phase3/magic-8.3.703-opt/` | Não, ignorado | Fora da base cacheada | Sim para reproduzir exatamente o fluxo de extração v6, dispensável no replay Python | ZIP `checkpoint_C` inclui o build; usar a receita pinada em outra plataforma. |
| Experimentos intermediários locais | Primeiras iterações `T/physical/fabric_v1`–`fabric_v5`, `T/physical/macro/` e vista bruta redundante `pex_raw/phase3_rc_flat.mag` | Não, ignorados | Fora da base cacheada | Parciais, para investigação histórica | Recibos selecionados nos ZIPs e entradas `NOTEBOOK_ONLY` no mapa. A geometria final `integrated_flat.mag` cobre a referência física de v6. Preservar no notebook ou em backup adicional se a equipe exigir o histórico completo de tentativas. |
| ZIPs históricos e patches de recuperação | `~/Downloads/phase3_*.zip` e `.zip.sha256`; `restauro/` dentro de C | Fora do repositório | Não avaliado no servidor | Três ZIPs são obrigatórios para restaurar o recorte auditável do handoff | Transferir os ZIPs e seus verificadores, priorizando L3. O índice registra 46 pacotes. |

Para arquivos grandes, [tabela de transferência crítica](../build/phase3/handoff_equipe_20261122/critical_files.csv) registra o caminho completo, tamanho em bytes, SHA-256, ZIP/membro e ambiente ou dados dependentes. O [inventário integral do recorte](../build/phase3/handoff_equipe_20261122/artifact_map.csv) inclui o restante das evidências e as fontes locais excluídas da recuperação padrão. Os [pacotes históricos](../build/phase3/handoff_equipe_20261122/historical_packages.csv) têm controle de SHA-256. Os três de recuperação e a entrega parcial também foram abertos e tiveram CRC conferido nesta auditoria.

### L3. Conjunto mínimo para transferir

1. `phase3_handoff_equipe_20261122.zip` e seu SHA-256. Contém o handoff, patch rastreado, todos os arquivos untracked preexistentes, inventários, helper de recuperação e recibos. Os arquivos no `build/phase3/` aqui são material de auditoria e o pequeno complemento de índices da v6.
2. `phase3_fechamento_funcional_strongarm_20261122.zip` e seu SHA-256. Guarda C250 TT/SS, ampliação da evidência, scripts de qualificação e retomada integrada.
3. `phase3_triple_strongarm_20261122.zip` e seu SHA-256. Guarda a v6, a prova física, PEX, FF físico, controles e módulos auxiliares dos analisadores.
4. `phase3_revisao_sense_sky130_checkpoint_C_20261121.zip` e seu SHA-256. Guarda C, integrados históricos, parte dos diagnósticos, binário Magic e a campanha completa de SNM.
5. Acesso ao commit de base e à imagem EDA com o PDK. O PDK, credenciais, caches e logs irrelevantes ficam fora da entrega.

O `phase3_entrega_parcial_marco3_20261123.zip` fica como leitura de contexto, também preservado em C. Para retomar tarefas específicas de folhas, captura de SCLK ou controles de guarda, o índice aponta os ZIPs complementares, como `phase3_controle_ff_e_layout_strongarm_20261122.zip`, `phase3_captura_sclk_e_avanco_strongarm_20261121.zip` e `phase3_fechamento_barramento_ss_20261120.zip`. O ZIP novo evita duplicar arquivos volumosos já preservados por SHA-256. O plano copia apenas membros selecionados e compara os hashes por caminho. Quando diferentes ZIPs trouxerem o mesmo caminho, usar o membro do manifesto de recuperação, e preservar os outros ZIPs como históricos.

### L4. Restaurar em outra máquina

1. Copiar os quatro ZIPs e sidecars para uma pasta de entrada e verificar `sha256sum -c` para cada arquivo. Reservar espaço para o clone e mais de 1 GiB para evidências descompactadas. Em verificação isolada esparsa, só são materializados os diretórios Git necessários e as evidências do manifesto.
2. Criar um checkout separado a partir do GitHub ou de uma cópia Git com o objeto de base. Na cópia nova, criar `integration/phase3-danilo-ss` em `8e1d961d65054b59f9032ed5f9338d9ee4353c33` se a branch ainda não estiver disponível. Conferir identidade, índice e working tree antes de aplicar a recuperação.
3. Extrair **somente o ZIP novo de handoff** em uma pasta de staging vazia. Conferir o `SHA256SUMS` interno. O script abaixo recebe o checkout e a pasta com os outros três ZIPs. Primeiro usar `--dry-run`, depois executar a restauração. O helper recusa conflitos de bytes e caminhos fora do checkout, valida o branch/HEAD, aplica o patch no checkout recuperado e copia as entradas por tamanho e hash. Alias de arquivo legados do GDS transferidos como cópias regulares continuam com o mesmo conteúdo e identidade.

```bash
# Paths para a área de entrada, staging já extraído e clone limpo
entrada=/caminho/entrega
staging=/caminho/staging
checkout=/caminho/checkout
h=build/phase3/handoff_equipe_20261122
PYTHONDONTWRITEBYTECODE=1 python3 "$staging/$h/restore.py" \
  --repo "$checkout" --archives "$entrada" --dry-run
PYTHONDONTWRITEBYTECODE=1 python3 "$staging/$h/restore.py" \
  --repo "$checkout" --archives "$entrada"
```

4. Guardar a pasta de staging e os ZIPs juntos com seus hashes. Esse caminho contém os inventários e o relatório, e o script coloca o Markdown do handoff no checkout. Na cópia restaurada repetir J2 e só então preparar uma nova tarefa. Se a identidade, modelo ou patch divergirem, separar os checkouts e registrar qual entrada falta antes de tentar reproduzir outra etapa. [Recibo da recuperação isolada](../build/phase3/handoff_equipe_20261122/recovery_test.log)

O teste local em clone esparso restaurou os três checkpoints selecionados e o working tree. Reproduziu byte a byte os três `qualification.json` da v6 e o `audit.json` das 406 amostras de SNM. Também reaplicou o observador de propriedade aos dados históricos de C SS e confirmou os 18 resultados. A primeira tentativa revelou a necessidade de incluir `analyze_capture.py` e seu módulo auxiliar no recorte, ambos recuperados do ZIP triplo. Esse teste verifica portabilidade dos dados e análises sem novas simulações. [Log da restauração e replay](../build/phase3/handoff_equipe_20261122/recovery_test.log)

### L5. Continuidade, risco e plano de versionamento

**Um clone do GitHub sozinho não recupera a integração atual.** Ele entrega o código base e as referências versionadas. A equipe também precisa do ZIP novo, dos três checkpoints históricos, acesso ao ambiente EDA e dos resultados do plano de recuperação. A recuperação deve ser testada por outra pessoa antes de depender dela para mudanças físicas. Se o notebook ficar indisponível antes de uma entrega das cópias e hashes, há risco de perda dos diffs, ferramentas, netlists e PEX experimentais, waveforms e resultados locais. Após a entrega testada, o risco remanescente se concentra em intermediários explicitamente `NOTEBOOK_ONLY` e em artefatos externos sem segunda cópia confirmada. A entrega desta rodada é local. Disponibilidade em armazenamento do grupo ainda está `NÃO VERIFICADO`.

**Faz sentido preparar commits revisáveis depois da transferência, com autorização.** Planejar uma branch de publicação preservando os checkpoints e separar conteúdos por assunto. O inventário ajuda a escolher membros explícitos para cada commit.

| Ordem proposta | Escopo do commit futuro | Condição antes de publicar |
|---|---|---|
| 1 | Manutenção de regras de ignore e extensão do exportador LEF, em commits pequenos se houver donos distintos. | Confirmar que diretórios de build e cópias de PDK ficam fora e que o exportador valida hash, caminhos e output novo. |
| 2 | Infraestrutura de integração/PEX e análises de propriedade e funcionalidade, com seus testes. | Testar em checkout limpo, sem dependência silenciosa de paths pessoais ou arquivos faltantes. |
| 3 | Fontes e receitas selecionadas da integração física e do StrongARM, referências das folhas, manifestos compactos e scripts de reprodução. | Colocar fontes essenciais hoje em `build/` em local versionável após revisão. Referenciar artefatos pesados em armazenamento aprovado por hash. Preservar C e v6. |
| 4 | SNM e auditorias de metodologia, relatórios de Fase 3 e handoff. | Revisar escopo de cada resultado, links para artefatos compartilhados e o caráter experimental das decisões. |
| 5 | Novos ECOs e caracterização em branches experimentais separadas. | Aprovação da sequência A/B, critérios congelados e resultados pareados. Commits futuros da Liberty dependem da caracterização homologada. |

Manter arquivos de modelo licenciados conforme o ambiente, sem incluir cópias integrais do PDK ou dados de sessão. A conclusão desta rodada é a documentação e preservação da transferência. A arquitetura, as fixtures, GDS/LEF/PEX e as evidências históricas continuam as mesmas.
