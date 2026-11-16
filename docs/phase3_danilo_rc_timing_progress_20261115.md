# Fase 3 — Danilo: extração RC, timing e potência

**Data do diagnóstico:** 15/11/2026 (America/Manaus)  
**Branch:** `feature/phase3-rc-timing-danilo`  
**Baseline congelada:** `origin/release/phase2-acceptance-20261111`, commit `89901e7e258b6955f6752163b918a296079466fa`  
**GDS de entrada:** `reports/phase2/direct_abutment_20261111/gds_v1/sram_4x8.gds`  
**SHA-256 do GDS:** `83e72aee8d45a9826751cdefd46dd062acc2a17ec0acfd33c07f218d20d8e64e`

## Escopo e evidências existentes

A atribuição da equipe para a Fase 3 coloca **Danilo** como responsável pela extração RC e pela caracterização temporal e de potência nos corners TT, SS e FF. As entregas são independentes das frentes de margem de leitura (André), Monte Carlo de SNM (Ícaro) e infraestrutura/Liberty (Leonardo). O Marco 3 é em **23/11/2026**. Este é o alinhamento mais recente para esta frente; o planejamento anterior em `docs/phase3_plan_to_20261123.md` registra uma distribuição preliminar distinta.

Todos os experimentos desta frente estão em `build/phase3/`, ignorado pelo Git, usando diretórios distintos por execução. Os arquivos da Fase 2 permanecem como entradas somente de leitura.

| Ensaio | Evidência local | Resultado e limite |
| --- | --- | --- |
| Magic, resistência distribuída em todas as redes | `build/phase3/rc_runs/20261115T190212Z-af649475/` e cópia requalificada `build/phase3/rc_requalified/20261116T014953Z-bdca57e3/` | 1.493 MOS, 300.400 R, 101.942 C; **somente estrutura RC**. A conectividade DC do VSS está aberta para os terminais MOS. |
| Magic, modo integrado `extract do resistance` | `build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a/` | **PASS_RC_NETLIST_STRUCTURE:** 1.493 MOS, 322.018 R, 101.005 C (48.111 capacitâncias nulas); VDD alcança 1.302 e VSS alcança 1.275 terminais MOS, sem curto entre os trilhos. SHA-256 do SPICE: `600f1ae686029e522d5d36299befc036e031e79c26e8c0725c0082752aaa8b27`. Ainda exige ensaio funcional. |
| Magic, resistência em sinais selecionados | `build/phase3/rc_runs/20261115T193552Z-e02e6d0d/` | 1.493 MOS, 743 R, 7.650 C; extração **parcial**, sem todos os resistores das alimentações. VDD alcança 1.302 e VSS alcança 1.275 terminais MOS, sem curto resistivo entre as fontes. |
| ngspice TT sobre RC completo com as malhas de alimentação distribuídas | `build/phase3/electrical_runs/20261116T025325Z-tt-bb698eaa/` | **FAIL (timeout de 900 s):** apenas 32,6098 ns do benchmark de 370 ns foram processados. Não houve resultados funcionais nem medidas de timing/potência. |
| ngspice TT com malhas de alimentação ideais e RC de sinais | `build/phase3/electrical_runs/20261116T031342Z-tt-f32929c7/` | **FAIL_FUNCTIONAL: 39 de 72 bits de leitura falharam**. Modelo diagnóstico com 1.493 MOS, 202 R e 5.073 C; sem IR drop e sem qualificação de timing/potência. |
| ngspice TT, 1,8 V, 27 °C, 10 fF por saída, sobre RC parcial | `build/phase3/electrical_runs/20261115T193658Z-tt-2028ca49/` | **FAIL_FUNCTIONAL: 38 de 72 bits de leitura falharam**. Os valores de timing/potência desse ensaio não são qualificáveis. |
| Controle sem RC distribuída, netlist transistorizada da Fase 2 | `build/phase3/diagnostics/20261116T014638Z-faa53b43/` | Estímulos e leituras de referência apresentam as palavras esperadas nos instantes originais de amostragem. Não validam a extração RC. |

## Bloqueador de conectividade

No `.ext` anterior à extração resistiva, o Magic registra equivalência entre `FILLER_131_1129.VNB` e `VSS`. O `.res.ext` completo marca o primeiro nó com `killnode`; no SPICE resultante, os terminais de vários MOS passam a `FILLER_21_0.VNB`, enquanto a extensa malha `VSS.n*` não possui caminho resistivo até os transistores. A auditoria de conectividade DC identifica **0 terminais MOS alcançáveis por VSS**, embora VDD alcance 1.302 terminais. Isso impede tratar o RC completo como um circuito eletricamente validado. A variante de RC parcial mantém ambos os trilhos conectados, mas falha na leitura funcional: os problemas são distintos. A evidência disponível não estabelece defeito físico no GDS; o comportamento ainda exige diagnóstico da extração Magic.

O teste do modo documentado do Magic 8.3.613 com `extract do resistance` antes de `extract all` **restabeleceu os caminhos DC** de ambas as fontes na extração RC completa. Foram verificados dispositivo, rede resistiva, capacitâncias, hash, e ausência de curto VDD–VSS. O diagnóstico em `build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a/` contém TCL, log, `.ext`, `.res.ext`, SPICE e manifesto com hashes. O gerador `tools/phase3_rc_extraction.py` passou a usar este fluxo para o perfil `all` e a rejeitar malhas de alimentação desconectadas ou em curto. Essas verificações não demonstram comportamento funcional, setup/hold ou potência.

O ensaio TT elétrico com esta extração completa excedeu o limite de 900 s e só avançou até 32,6098 ns. No SPICE, **321.816 de 322.018 resistores (99,94%)** pertencem às malhas de VDD/VSS. Isso explica o custo excessivo da resolução transiente, mas não permite inferir o comportamento funcional da SRAM. Para isolar a participação das malhas de alimentação, `phase3_rc_characterization.py` aceita o modo diagnóstico `--supply-model ideal`, que contrai as redes resistivas de VDD/VSS, conserva as resistências de sinais e agrega as capacitâncias restantes por par de nós. O SPICE diagnóstico tem 1.493 MOS, 202 resistores e 5.073 capacitores. **Esse modelo simplificado não representa IR drop nem substitui resultados sobre RC completo.**

O ensaio TT com alimentação idealizada foi concluído e **reprovou 39/72 bits** nos instantes de amostragem originais. No ciclo 6, a leitura de `0xAA` em 141 ns apresentou todas as saídas próximas de 0,2 V; no ciclo 7, a leitura de `0x55` em 161 ns apresentou saídas próximas de 1,8 V. Após o início da injeção fraca do host, aparecem outras palavras, portanto leituras posteriores não podem ser reinterpretadas como aprovação no instante exigido. Um controle com netlist da Fase 2 e a mesma carga externa de 10 fF apresentou `0xAA` em 141 ns e `0x55` em 161 ns. Os estímulos dos dois decks coincidem, salvo nomes de capacitores externos e o término mais cedo (170 ns) do controle.

Ensaios adicionais de isolamento, todos apenas diagnósticos e com alimentação idealizada, mantiveram as 202 resistências de sinal e a carga externa de 10 fF. Sem capacitâncias extraídas, as palavras em 141 ns (`0xAA`) e 161 ns (`0x55`) coincidem com a referência. Com apenas 1.413 pares de capacitores sinal–trilho (2,635 pF), a leitura em 141 ns falha: os bits altos ficam entre 0,477 V e 0,732 V. Com apenas 3.659 pares entre sinais (1,181 pF), as palavras amostradas são `0x22` em 141 ns e `0x14` em 161 ns, ambas incorretas. Nos dois ensaios com capacitores isolados, `rc701` ficaria puramente capacitivo; foi adicionado `R_DIAG_FLOAT_RC701=1e15 Ω` somente para estabilizar numericamente o ponto de operação. Esse componente não pertence ao PEX. A comparação indica que capacitâncias parasitas são dominantes na falha observada, sem qualificar o circuito nem apontar por si só qual parasita do PEX está errado.

Uma auditoria exploratória, usando a ordem das 1.493 instâncias MOS como correspondência e contraindo as **202 resistências de sinais** e as malhas de alimentação, encontrou **730 redes exatamente correspondentes às 730 redes do netlist transistorizado de referência da Fase 2**: nenhuma rede original dividida e nenhuma união indevida entre duas redes originais. Os parâmetros e a ordem das instâncias MOS também coincidiram. Isso afasta diferenças topológicas no limite de curto ideal como explicação imediata, mas não substitui LVS, nem valida valores resistivos/capacitivos, tempos de subida ou margem de leitura. As capacitâncias efetivas, somadas por pares após a simplificação, totalizam 14,739 pF; cerca de 10,923 pF estão diretamente entre VDD e VSS, com fontes ideais no ensaio diagnóstico.

Para uma nova extração reproduzível, a partir da raiz do checkout e com o contêiner EDA operacional:

```bash
./tools/sram-eda python3 tools/phase3_rc_extraction.py --profile all
```

Para ensaiar TT sobre uma extração cujo manifesto tenha passado na auditoria estrutural:

```bash
./tools/sram-eda python3 tools/phase3_rc_characterization.py \
  --extract-run build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a \
  --corner tt --load-ff 10
```

Para diagnosticar se as malhas distribuídas de alimentação são responsáveis pela falha ou lentidão, usando uma aproximação com VDD/VSS ideais:

```bash
./tools/sram-eda python3 tools/phase3_rc_characterization.py \
  --extract-run build/phase3/diagnostics/20261116T023044Z-integrated-resistance-aae3f01a \
  --corner tt --load-ff 10 --supply-model ideal --timeout 900
```

## Critérios para liberar TT, SS e FF

1. Reproduzir a RC a partir do GDS fixado, registrando script, logs, hashes e contagens de dispositivos/parasitas.
2. Demonstrar caminho DC do VDD **e do VSS** até terminais MOS e ausência de curto resistivo entre as fontes.
3. Executar primeiro TT no benchmark funcional existente, com os mesmos instantes de amostragem e cargas; exigir **72/72 bits corretos**.
4. Só após TT funcionalmente aprovado, executar SS e FF em série (`workers=1`) e calcular medidas definidas com unidades e referências de transição.
5. Entregar tabelas de tempo e energia/potência com proveniência, e marcar explicitamente `NOT_CHARACTERIZED` onde não houver estímulos ou medidas suficientes (incluindo setup/hold e potência estática, na instrumentação atual).

**Situação:** extração RC completa com conectividade DC de alimentação foi obtida; caracterização funcional TT/SS/FF **ainda não foi aprovada**. Não publicar resultados quantitativos de timing ou potência derivados do ensaio TT anterior funcionalmente reprovado.
