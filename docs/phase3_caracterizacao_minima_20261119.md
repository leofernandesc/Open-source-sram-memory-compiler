# Fase 3 — caracterização elétrica mínima da SRAM 4×8

19/11/2026 · `integration/phase3-danilo-ss` · HEAD `8e1d961`

**Resultado.** Foi validado um procedimento de replay para medir a palavra completa e a liberação de DATA no corner SS. As medições são utilizáveis como evidência experimental nas condições registradas. A qualificação da macro permanece `NOT_CHARACTERIZED`.

## A. Candidato e condições

A única geometria de trabalho é a variante espaçada do ECO reconstruído de Danilo (`42f0b51`). Ela conserva tap 48, inversores de captura ligados ao CLK público e `ebufn_8`. A variante usa `dfxtp_2` e o afastamento de DATA1 do clock. Foi selecionada pela correspondência verificada entre roteamento, reimportação GDS, LEF, dois PEXs da mesma geometria e transientes de leitura e de máscaras. Ela continua candidata experimental. A NAND4BB e os acessos físicos alternativos de DATA7 ficam fora do candidato.

| Artefato | SHA-256 |
|---|---|
| GDS reimportado | `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365` |
| LEF derivado desse GDS | `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091` |
| Verilog roteado | `eafcca0a89d53392e8cc1bbe380e87df8f4479f58a04a5132d62e2246d1a74a1` |
| PEX padrão selado | `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a` |
| PEX sem poda por atraso | `935a3b5a368a421f10a7b9956c35a45192940bc759778aff10eed2c810ef6479` |

Os recibos de **DRC zero, LVS único e LEF coerente** foram verificados por hash. O replay também confere a netlist de referência, o Verilog do layout e se a netlist realmente simulada é a tradução de nomes do PEX selado. O manifesto de saída contém os hashes de decks, waveforms, probes, logs e fechamento dos modelos. **VERIFIED** aplica-se à cadeia de evidência e aos checks de cobertura limitada.

Os quatro transientes reutilizados usaram SKY130A, **SS, 1,8 V, 27 °C, 10 fF por pino DATA, rampas de 50 ps, passo máximo de 25 ps**, ngspice 44.2 e extração Magic 8.3.703. A leitura usa oito ciclos e 170 ns, com período nominal de 20 ns e duty de 50%. A desabilitação usa duas bancadas v2 dirigidas de 108 ns, com pulsos altos de 10 ns e espaçamento próprio dos estímulos. [Contexto da integração](phase3_danilo_ss_integration_20261118.md) · [Recibos e parâmetros de origem](../build/phase3/characterization_minimum_ss_20261119_r3/observations.json)

O PEX padrão com corte de atraso padrão de 1 ps (16.187 resistores) é a referência operacional provisória. O PEX com `mindelay 0` e `force {DATA[7]}` (19.771 resistores) serve para sensibilidade. Ambos têm o mesmo GDS, comando de extração, versão e C-only bruto. A diferença de tempo observada não é um intervalo estatístico nem margem garantida. A fidelidade RC ainda é inconclusiva. [Auditoria e limitações](phase3_auditoria_falhas_20261119.md#4-escolha-do-modelo-rc)

## B. Medições

O JSON de replay distingue **MEASURED** para uma observação elétrica de waveform existente, **VERIFIED** para a verificação de evidência ou de um comportamento no escopo ensaiado, **PROVISIONAL** para a métrica dependente de modelo ou carga experimental e **NOT_CHARACTERIZED** quando falta evidência. O relatório usa segundos em máquina. As tabelas abaixo convertem para ns e ps. O replay não altera os estados do runner nem o CSV histórico de 14 colunas.

### Tempo de acesso da palavra

O procedimento verifica que o endereço solicitado ativou a única wordline esperada, confere sense e D na captura local e Q no intervalo válido, confirma o host forte desligado e a saída habilitada. Relaciona a expectativa a uma escrita anterior da mesma linha, com DIN pronto antes de WE20 e monitor de corrente aprovado. O início da palavra válida é o último dos oito instantes de entrada final nas faixas baixo ≤0,36 V e alto ≥1,44 V. Todos os bits devem permanecer válidos até o início da rampa programada da sonda, com suporte em amostras interiores. O timestamp de DATA resultante é comum às medidas a partir de CLK↑50 e CLK↓50.

O atraso por bit `tCLK_TO_DATA` usa CLK↓50 e o cruzamento de 50% após a captura local, quando atribuível à nova leitura. Bits que conservam o valor têm observação de estabilidade e atraso ausente. O valor da palavra não é esse atraso de cruzamento. As duas palavras foram verificadas mesmo quando a janela histórica mais curta reprovou bits. [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Contrato de caracterização](phase3_characterization_contract.md)

| Ciclo e palavra | tACCESS CLK↑50 padrão / sem poda | CLK↓50 → palavra válida padrão / sem poda | Estabilidade até a sonda padrão / sem poda | Δ sem poda | Resultado |
|---|---:|---:|---:|---:|---|
| 6 · linha 0 · 0xAA | 10,911 / 10,938 ns | 0,911 / 0,938 ns | 0,564 / 0,537 ns | +27,46 ps | MEASURED · PROVISIONAL |
| 7 · linha 1 · 0x55 | 10,875 / 10,919 ns | 0,875 / 0,919 ns | 0,600 / 0,556 ns | +43,98 ps | MEASURED · PROVISIONAL |

No PEX padrão, as palavras ficaram válidas de 140,935652 até 141,500 ns e de 160,900016 até 161,500 ns. DATA7 foi o último bit em ambas. Os intervalos de `tCLK_TO_DATA` dos bits com transição foram **766–821 ps** em c6 (quatro bits) e **773–841 ps** em c7 (oito bits). Os oito registros por palavra, tensões de captura, referências a CLK e todos os cruzamentos medidos estão no JSON. Essas observações não supõem um máximo de CLK→DATA ou um intervalo de amostragem garantido. Fmax depende ainda da janela do receptor, de setup/hold, dos mínimos de fase alta e baixa e das guardas do barramento. [Resultados por bit](../build/phase3/characterization_minimum_ss_20261119_r3/observations.json)

### Desabilitação e direção

Em cada máscara v2, o driver da SRAM estava ativo com 0xAA antes da mudança e a sonda de **1 kΩ** aplicava o complemento. Mede-se desde 50% do controle público até o instante final em que **as duas condições** se mantêm por bit: tensão de DATA na faixa da sonda e `|I_probe| ≤ 50 µA`. O intervalo termina 150 ps antes do fim da máscara, com verificação de recuperação. O tDIS observado do barramento é o mais tardio dos oito bits. TE_B80 é registrado para diagnóstico. Os valores representativos de alta impedância valem sob essa sonda, carga e sequência e não constituem garantia de leakage nem de corrente máxima.

| Controle isolado | tDIS observado dos bits | Último bit liberado | Resultado |
|---|---:|---:|---|
| WEb↓ | 821,0–1.067,5 ps | 1.067,5 ps | MEASURED · PROVISIONAL |
| OEb↑ | 642,6–888,2 ps | 888,2 ps | MEASURED · PROVISIONAL |
| CSb↑ | 635,5–881,6 ps | 881,6 ps | MEASURED · PROVISIONAL |

As **24 máscaras** foram verificadas no PEX padrão. A sensibilidade de tDIS ao PEX sem poda é **NOT_CHARACTERIZED**. Cada pino foi observado na polaridade de 0xAA, sem cobertura da palavra invertida em todos os pinos.

A guarda de **300 ps** continua ensaio de estresse. Na v2 com payload oposto, houve sobreposição nos oito bits, com 84–1.164 µA de corrente de oposição a +200 ps. O ensaio de **1,5 ns** teve 8/8 checks de handoff e 8/8 bits corretos no readback da escrita posterior. O restante da leitura da v2 conserva o FAIL histórico de janela. A regra aprovada exige liberação efetiva da SRAM antes de o host dirigir DATA e setup/hold de escrita. Os tempos de guarda da bancada não são requisitos públicos. [Contratos de interface](../specs/sram_4x8_digital.md#read-to-write-handoff) · [Waveforms e critérios de direção](phase3_data7_turnaround_20261119.md#desabilitação-medida-na-referência-com-rc-integral)

## C. Estado da Fase 3

| Frente | Medição existente e reaproveitamento | Falta e menor ensaio posterior |
|---|---|---|
| Leitura | Duas palavras SS medidas, quatro latências de palavra entre dois PEXs e 12 cruzamentos por perfil. Sondas de WL, sense, D/Q e DATA reutilizáveis. | Cobrir as quatro linhas, nove leituras, padrões complementares e os handoffs na mesma identidade física em um único transiente SS de 18 ciclos. |
| Escrita | Quatro escritas no replay curto, com 32/32 DIN prontos antes de WE20 e 32/32 checks de corrente. Duas linhas lidas nesse transiente. Readback do handoff de 1,5 ns verificado na v2. | Completar o readback das quatro linhas e reescritas no ensaio de 18 ciclos. A evidência atual dos quatro DIN não comprova por si só armazenamento nas quatro linhas. |
| Barramento | Três controles isolados, 24 verificações, tDIS provisório e ensaios comparativos de guardas. | Medir também o estado anterior complementar e verificar todas as trocas do transiente integrado. Qualificar tDIS por controle e carga antes de estabelecer guarda pública. |
| Setup/hold | A Fase 2 tem janelas disponíveis em D/sense e referência de FF local. Há bancos de captura de endereço e controle isolados. | Perturbar um sinal de ADDR/controle/DIN por vez em torno de CLK↑, mantendo os outros eventos fixos, e observar captura e readback. O primeiro ensaio curto deve estabelecer um par passa/falha em SS por classe. Setup/hold públicos **NOT_CHARACTERIZED**. |
| Fases alta e baixa | Os waveforms e `phase3_rc_read_path.py` observam WL, sense, captura e pré-carga no ritmo de 20 ns. | Ensaio dirigido de uma fase por vez, com a outra fixa. Verificar escrita e captura ao encurtar alta e recuperação/seleção ao encurtar baixa. Limites e Fmax **NOT_CHARACTERIZED**. |
| Potência | No PEX padrão, integrais exploratórias `−VDD·I(VDD_SRC)` em 20 ns de **14,58–15,13 pJ** em leitura e **10,71–11,51 pJ** em escrita. Idle com clock ficou em 0,148–0,195 mW. Esse total inclui leakage e pré-carga. `supply_energy` é reaproveitável. | Medir uma janela estática com clock parado e armazenamento conhecido, mais um par ativo/idle comparável. Definir a separação de leakage e dinâmica antes de qualificar. |
| TT/SS/FF | Há evidência histórica de TT/FF do protótipo de Danilo ou da reconstrução anterior e TT devices/junctions de outra geometria. O runner aceita os três corners. | Primeiro completar SS nesta geometria. Posteriormente repetir o mesmo caso com o mesmo GDS, PEX e método em TT/FF. PVT do candidato **NOT_CHARACTERIZED**. |
| SNM | As séries históricas read/hold da bitcell 6T têm 200 seeds cada em condições próprias de triagem pré-layout. | Reconciliar, fora desta rodada, a identidade e as condições de cada série com o escopo do Marco 3. As séries não estabelecem margem integrada. |
| Liberty | O contrato de 14 colunas e os manifestos permitem rastrear arcos e unidades. As referências de biblioteca dos FFs ajudam a desenhar os testes. | Implementar geração a partir de métricas e arcos qualificados, depois validar sintaxe, pinos, unidades, cobertura e tabelas contra as fontes. O menor primeiro teste é um arco qualificado de ponta a ponta no parser. **Nenhuma tabela estimada.** |

[Interface e requisitos elétricos](../specs/technical_specification.md) · [Janelas internas da Fase 2](../specs/sram_4x8_timing_contract.md#9-medições-internas-disponíveis) · [Planejamento e critérios do Marco 3](phase3_plan_to_20261123.md#4-critérios-de-aceite-do-marco-3)

## D. Decisão e reprodução

1. **É suficiente para iniciar um piloto sistemático em SS nesta geometria.** As duas palavras, o readback dirigido e a liberação de DATA sustentam o próximo ensaio com protocolo legal e critérios explícitos. A cobertura atual é parcial.
2. **Nenhum defeito físico ou lógico impeditivo foi comprovado neste escopo.** A sobreposição está documentada para a guarda de estresse. A fidelidade RC e a cobertura funcional restante ainda limitam o alcance da decisão.
3. **O Marco 3 completo continua pendente.** Faltam validação integrada, timing e setup/hold qualificados, potência estática/dinâmica, comparabilidade TT/SS/FF, decisão sobre a evidência de SNM no escopo devido e geração/validação da Liberty com dados reais. O tDIS medido ainda não fornece um máximo público.
4. **Próxima tarefa única recomendada.** Executar um transiente SS de 18 ciclos no candidato pinado, a 20 ns, com a ordem de propriedade verificada nos handoffs. Manter a fixture de estresse em seu próprio escopo. Concluir ao conferir as nove palavras completas e estáveis após captura, readback das quatro linhas e direção sem dupla condução no estímulo legal, preservando qualquer FAIL e os hashes em recibo. Essa tarefa não foi iniciada.

Reprodução offline a partir da raiz, com os artefatos selados das rodadas anteriores e um destino novo.

```bash
timeout 180s tools/sram-eda python3 tools/measure_phase3_access_disable.py \
  --output build/phase3/caracterizacao_minima_replay_novo
timeout 300s tools/sram-eda python3 tools/run_phase3_regressions.py \
  --output reports/phase3/caracterizacao_minima_regressao_nova
timeout 180s tools/sram-eda python3 -m unittest discover -s tests -p 'test_phase3_rc*.py' -v
```

A execução de replay foi repetida no host e no contêiner, com JSON idêntico e recusa de sobrescrita. A CLI de replay retorna 0 quando publicou o laudo offline. Esse código não altera a semântica do runner elétrico. Foram aprovados **165 testes de infraestrutura e 47 de RC/medição**, incluindo seis novos. Nesta rodada foram reutilizados **quatro transientes elétricos existentes** e realizadas **zero novas simulações SPICE, zero DRC/LVS e zero intervenções físicas**. A geometria, os artefatos, a branch e os vereditos anteriores foram preservados. [Script](../tools/measure_phase3_access_disable.py) · [Testes novos](../tests/test_phase3_rc_access_disable.py) · [Recibo de software](../reports/phase3/characterization_minimum_regression_20261119/summary.json)
