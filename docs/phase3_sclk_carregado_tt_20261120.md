# Fase 3 — Validação do driver local de SCLK com cargas compartilhadas em TT

**Controle carregado `INCONCLUSIVE` · Driver v1 carregado `NOT_RUN`.** O ngspice atingiu o limite de 12 minutos durante a solução inicial. A rodada confirmou a construção e a rastreabilidade do recorte. O funcionamento elétrico do recorte carregado permanece sem evidência transiente.

## Recorte e fronteiras

O recorte parte do PEX padrão do candidato espaçado, SHA-256 `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`. Contém **1.013 MOS, 14.810 resistores e 8.138 capacitores**. Os cartões retidos são cópias exatas do binding verificado. A seleção segue a conectividade resistiva e os terminais de canal dos MOS até os pontos de fronteira. A auditoria confirmou os 64 MOS de acesso e os 128 MOS dos latches das 32 células 6T. O controle preserva os FF de leitura, o caminho até D/Q, os circuitos de escrita, o decodificador, os drivers de WL, a cadeia que produz os controles, os oito senses e os 24 MOS locais de pré-carga/equalização. [Manifesto](../build/phase3/sclk_shared_loaded_20261120/manifest.json) · [Auditoria estrutural](../build/phase3/sclk_shared_loaded_20261120/preflight_audit.json)

O estágio original `sense_drive` gera o SCLK por dispositivos extraídos. A rede inclui 45 nós resistivamente ligados, os três gates por sense e R87 entre `rc8562` e `rc8571`. A pré-carga usa o controle original, com rede de 45 nós própria. Os estímulos entram no CLK público e nas 12 saídas capturadas arquivadas de modo, endereço e dados de escrita. SCLK, pré-carga, WL, BL/BLB e armazenamento respondem ao circuito. O manifesto identifica cada terminal e MOS de observação. [Ramo local e piloto isolado](phase3_driver_local_sclk_tt_20261120.md) · [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Especificação](../specs/technical_specification.md)

Para conservar a impedância dinâmica das bitlines, o prefixo desloca as escritas históricas c4 e c5 de 87–127 ns para 147–187 ns. Elas programam a linha 2 com `0x0F` e a linha 3 com `0xF0` pelo caminho real de escrita. A transição de fronteira em 187–188 ns ocorre com CLK baixo. De 188 a 247 ns o replay utiliza a sequência histórica de avaliação e recuperação de c15–c17. As células evoluem a partir do ponto de operação, com programação pelo prefixo. Não há `.ic`, `.nodeset` ou fontes nas bitlines ou nos nós de armazenamento. A auditoria conferiu os dados, endereços e o comando de escrita nas PWLs na fase alta das duas escritas. [Estímulos e sequência](../build/phase3/sclk_shared_loaded_20261120/stimuli.spice) · [Origem do replay](phase3_data3_tt_snm_piloto_20261120.md)

Foram excluídos 6.346 cartões, com inventário por elemento. O recorte conserva os resistores dos 5.775 nós das redes de VDD e VSS e os acoplamentos retidos pela seleção. Oito placas de acoplamento externas usam replay de sondas do mesmo grupo resistivo. Outras 185 placas externas ficam a VSS, conservando 580 capacitores com terminais de referência aproximados. As correntes comutadas dos blocos de interface e dos registros de entrada cortados estão ausentes. VDD/VSS são ideais nos pinos externos. Quedas e rebotes dentro da malha retida são observáveis, enquanto o droop da macro completa e o efeito de novas rotas ainda dependem de avaliação. [Elementos excluídos](../build/phase3/sclk_shared_loaded_20261120/removed.csv)

## Gate de equivalência

O resultado de referência é `0x0F`, `0xF8`, `0xF8` em c15, c16 e c17. Na macro TT original, o bit 3 é o único incorreto nas duas últimas leituras. O gate exige a mesma decisão sustentada do sense e em D antes da captura local, Q confirmado depois, WL correta e recuperação. Compara bordas 20/50/80% de SCLK, pré-carga e WL ativa por um envelope diagnóstico de ±25 ps. Para BL/BLB, reaproveita ±7,542 mV em torno da ativação, com o envelope relativo de 5% fora dessa vizinhança e 15,085 mV para modo comum. NTAIL do bit 3 usa 30,169 mV em c16/c17. Esses limites verificam fidelidade para a intervenção causal. A especificação funcional permanece a referência da macro. [Origem dos envelopes](phase3_precondicionamento_sense3_tt_20261120.md)

A comparação de recuperação registra as correntes de canal, a interseção temporal acima de 1 µA, a forma completa da desativação e a janela sustentada de retorno de BL/BLB e SA/SAB à banda alta. O marcador de corrente separa trechos para comparação no ensaio e não define uma especificação de contenção da macro.

## Execução e resultado

Foi executada **uma** simulação SPICE reduzida, apenas do controle. O deck programou um transiente de 100 ns, dos quais 41 ns correspondem ao prefixo e à junção de condicionamento. O restante reproduz 188–247 ns da referência. Condições de execução: SKY130A TT, 1,8 V, 27 °C, período de 20 ns, Gear, passo máximo de 25 ps e ngspice 44.2/KLU. [Comando, opções e sondas](../build/phase3/sclk_shared_loaded_20261120/control/attempt.json)

| Etapa | Observação |
|---|---|
| Preparação do circuito | O ngspice reconheceu o deck e iniciou a análise com KLU a 27 °C |
| Ponto de operação | `dynamic gmin stepping` iniciou e falhou. A última etapa registrada foi `true gmin stepping` |
| Recursos amostrados | CPU de 98,3%, RSS de 923.052 KiB e processo em execução após 9 min 42 s |
| Integração transiente | Sem `Reference value`, conclusão de `tran` ou waveform gravado. Progresso simulado indeterminado |
| Encerramento | `TIMEOUT` em **720,348 s**, retorno 1 do runner |
| Controle carregado | **`INCONCLUSIVE`** |
| Driver carregado | **`NOT_RUN`**. O gate rejeitou a inserção e o deck candidato carregado ficou sem geração |

[Log do ngspice](../build/phase3/sclk_shared_loaded_20261120/control/ngspice.log) · [Amostra operacional](../build/phase3/sclk_shared_loaded_20261120/operational_snapshot.txt) · [Recibo](../build/phase3/sclk_shared_loaded_20261120/control/result.json) · [Decisão do gate](../build/phase3/sclk_shared_loaded_20261120/decision.json)

A primeira limitação comprovada é a inicialização do recorte carregado. A referência iniciava com a rampa VDD de 0 a 1,8 V em 1 ns. O recorte carregado parte de um ponto de operação em 1,8 V antes das duas escritas, com 32 células ainda sem programação. Essa diferença é uma hipótese para a dificuldade de convergência inicial. A evidência disponível não isola a contribuição do estado biestável, das terminações do recorte ou do condicionamento matricial. O log não demonstra um defeito lógico do v1, cuja inserção foi bloqueada. [Deck carregado](../build/phase3/sclk_shared_loaded_20261120/control/bench.spice) · [Deck TT original](../build/phase3/data3_tt_20261120/bench.spice)

| Indicador | Controle carregado | Driver v1 carregado | Veredito |
|---|---|---|---|
| Sense 3, c16 | Sem waveform | Não executado | Inconclusivo |
| Sense 3, c17 | Sem waveform | Não executado | Inconclusivo |
| Outros sete senses | 21 gates mapeados para os sete senses, sem medições elétricas novas | Não executado | Inconclusivo |
| SCLK compartilhado | Estágio e distribuição extraídos retidos, sem medições | Não executado | Inconclusivo |
| WL | Drivers, resistores e carga dos acessos preservados, sem medições | Não executado | Inconclusivo |
| Pré-carga | 24 dispositivos locais retidos, sem medições de recuperação ou corrente | Não executado | Inconclusivo |
| Desativação e glitches | Sem waveform | Não executado | Inconclusivo |
| Correntes do tail e alimentação | Sondas definidas, sem amostras transientes | Não executado | Inconclusivo |

O subcircuito v1 e a definição da `inv_4` extraída da biblioteca foram preservados com os hashes de preparação. As medições anteriores do v1 isolado continuam separadas, inclusive D correto por aproximadamente 4,97 ns e o pico de tail de aproximadamente 327 µA. [Resultados isolados](phase3_driver_local_sclk_tt_20261120.md)

## Decisão de engenharia

**Estudo do ECO carregado `INCONCLUSIVE`.** A bancada carregada não produziu a evidência necessária para determinar o efeito do v1 sobre os demais senses, WL, pré-carga e alimentação.

**Próxima ação única:** executar um controle com a rampa histórica de alimentação no início do prefixo, preservando a malha extraída e os estímulos de c15–c17. O critério de conclusão é obter um waveform integral e satisfazer o gate de equivalência, incluindo a reprodução das palavras `0x0F`, `0xF8`, `0xF8`. Esta rodada encerrou após o timeout.

| Evidência histórica | Estado |
|---|---|
| Macro TT original | `FAIL` |
| Contraste ideal no sense 3 | `CORROBORATED` no recorte |
| Driver v1 isolado | `VIABLE_FOR_PHYSICAL_STUDY` |
| Macro física corrigida | Ainda não demonstrada |
| Monte Carlo esquemático | 200 Hold e 206 Read válidas no domínio experimental |
| Qualificação elétrica geral | `NOT_CHARACTERIZED` |

## Reprodução e integridade

**10/10 testes de software passaram**, cinco do recorte carregado e cinco regressões do driver isolado. Os testes verificam a seleção do driver físico, o replay, a alteração exclusiva de R87 no deck candidato e o bloqueio por evidência ausente ou adulterada. Os arquivos novos versionáveis são este relatório, `tools/phase3_sclk_loaded.py` e `tests/test_phase3_sclk_loaded.py`. A branch `integration/phase3-danilo-ss` conserva o HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33` e as alterações locais anteriores. [Testes](../build/phase3/sclk_shared_loaded_20261120/tests.log)

A reprodução requer o PDK e as referências TT arquivadas. Escolha um diretório novo para não sobrescrever evidências. O retorno 1 observado em `control` indica a interrupção. `analyze-control` emite o gate correspondente.

```bash
run=build/phase3/sclk_shared_loaded_reproduction
script=tools/phase3_sclk_loaded.py
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" prepare --output "$run"
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 "$script" control --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 "$script" analyze-control --output "$run"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sclk_loaded.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_phase3_sclk_local_driver.py' -v
```

| Artefato | SHA-256 |
|---|---|
| Manifesto | `9e72e7e98baf18ff93901d4f1880cca4a3e452cdbbc427010140b3bca8edf854` |
| Recorte | `3f2f9cd987ff7903609716cf193d4e17c9ed3d36e5f37096c7df6fd73c620eb1` |
| Recibo da simulação | `6940abbb4ccca1f191c369767e6a2f593d93ed2ac7a490ebb1f3e4ee5ba21dbd` |
| Gate de controle | `47771303f6674f911f39a4e51734e2283ead113ab21fe39609819fb6b0fdee98` |
