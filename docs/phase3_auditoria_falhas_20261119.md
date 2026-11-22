# Fase 3 — auditoria de falhas e critérios de aceitação

19/11/2026 · `integration/phase3-danilo-ss` · `8e1d961`

**Veredito.** Na geometria espaçada, 6/16 e 14/16 são contagens de bits válidos durante toda a janela do benchmark. Nas duas extrações, as palavras 0xAA e 0x55 estavam corretas no centro da janela e permaneceram válidas até a entrada programada da sonda. A reconstrução anterior do protótipo de Danilo também estabilizou as duas palavras, embora quatro bits ainda estivessem entre limiares no centro. O handoff com 300 ps sobrepõe drivers. Com 1,5 ns a referência cumpriu a ordem de liberação e acionamento no ensaio diagnóstico. Os FAILs históricos ficam registrados. A escolha de um PEX de referência e a qualificação elétrica continuam abertas.

## 1. Autoridade dos critérios

| Critério | Origem e o que o check demonstra |
|---|---|
| Operação e escrita na subida, leitura na descida, retenção de Q, nova palavra correta em DATA e alta impedância nos modos previstos | Requisitos funcionais da especificação §§4, 6, 12, 15 e 16 e DIG-01 a DIG-08. A saída pode propagar após a descida. Um valor incorreto após acomodação, captura incorreta ou driver ativo indevidamente em estímulo legal exige investigação funcional. |
| CLK/control a 50%; DATA baixo ≤0,36 V, alto ≥1,44 V | Convenções do contrato de caracterização em 1,8 V, aplicadas pelo analisador. 50% marca propagação. 20%/80% marca validade elétrica de bancada, sem especificar limiares de um receptor externo nem prazo de disponibilidade. Entre as faixas o valor é indeterminado sob esse critério. |
| Amostra da nova palavra em `S` e janela `[S−100 ps, S+100 ps]` | A fixture `bus` da Fase 2, commit `c46e611`, gera `S=subida nominal+11 ns`, isto é, descida nominal +1 ns. O analisador RC de `f993fb8` acrescentou ±100 ps, hoje com fronteiras interpoladas. Com a rampa de 50 ps, a abertura fica ~875 ps depois de CLK↓50. A janela reprova qualquer bit fora da faixa em seu intervalo completo. O contrato público §§3–8 deixa `tREAD_VALID` e Fmax pendentes. |
| Escopo P3-DATA-002 r1 | O1–O4 aprovam uma observação de bancada pinada em TT com extração devices/junctions e 18 ciclos. A autorização não estende o perfil aprovado a SS, a PEX RC distribuído ou ao ECO. O antigo ensaio de visibilidade **da palavra anterior** em subida+1 ns é outro check. |
| Proprietário no handoff e guarda do host | Liberação efetiva antes de o host ligar é requisito dos §§4/16, DIG-06/07 e contrato temporal §§5/6. O gerador da Fase 2 alterna 0,3 e 0,6 ns a partir do início das rampas em handoffs. O ciclo 8 usa 0,3 ns. Os 1,5 ns pertencem à bancada diagnóstica v2. Não há máximo público de disable/turnaround ou garantia de ZBT. |
| `TE_B`80, probe oposto de 1 kΩ, corrente ≤50 µA, prontidão de DIN | TE_B80 e HOST_EN>0,36 V são proxies internos no check original. A bancada v2 verifica isolamento por tensão/corrente, com corrente abaixo de 50 µA até o fim da máscara e recuperação subsequente. O check de corrente forte usa 50 µA a partir de `max(host_enable, payload)+0,25 ns`. Esses valores são diagnósticos, sem garantia de leakage. A ordem DIN estável antes do evento interno WE20 sustenta a escrita observada. DIN em subida+1 ns é legado diagnóstico e não demonstra setup/hold público. |

[Especificação](../specs/technical_specification.md) · [Contrato digital](../specs/sram_4x8_digital.md) · [Contrato temporal](../specs/sram_4x8_timing_contract.md) · [Contrato de caracterização](phase3_characterization_contract.md) · [Aprovação r1](phase3_data_operational_policy_approval_r1_20261116.md) · [Fixture e histórico de observação](../tools/phase2_extension.py#L59) · [Analisador RC](../tools/phase3_rc_characterization.py#L263)

## 2. Matriz de falhas

Nas leituras locais abaixo, o valor do sense e de D na captura local e o valor de Q no centro foram corretos para **todos os 16 bits** de cada execução. Todos os bits reprovados chegaram ao nível válido antes da sonda de cada leitura. A coluna de confiança se refere à constatação, dentro do escopo do artefato.

| Caso | Observação | Requisito aplicável | Classificação | Confiança | Ação necessária |
|---|---|---|---|---|---|
| Espaçada, padrão 25 ps, c6 DATA7 ↑ | Atraso de 35,65 ps após abertura. A 10 ps, 33,99 ps. DATA em S = 1,617–1,620 V, esperado 1. | Nova palavra após descida. Prazo de abertura local da fixture. | Caracterização pendente | Alta para o atraso nos dois passos | Medir contra orçamento válido. |
| Espaçada, padrão 25→10 ps, c7 DATA7 ↓ | 0,36017 V na abertura a 25 ps, 0,17 mV acima do limite. Margem −0,016 ps a 25 ps e +1,705 ps a 10 ps. DATA em S correto. | Limiar de medição e abertura da fixture. | Sensibilidade de medição | Alta | Preservar o FAIL de 25 ps e registrar a inversão. |
| Espaçada, sem poda, c6 DATA1/5/7 ↑ | Atrasos desde a abertura de 17,97/15,52/63,11 ps. DATA em S = 1,653/1,660/1,555 V. | Correção dos dados e prazo diagnóstico. | Sensibilidade de medição | Alta para efeito do perfil PEX. Fidelidade física aberta. | Validar referência RC. |
| Espaçada, sem poda, c7 DATA0/1/2/4/5/6/7 | Atrasos de 15,71/0,94/9,73/26,15/10,55/21,22/44,00 ps. Todos corretos em S. DATA1/5/7 são descidas. | Mesmo critério de c6. | Sensibilidade de medição | Alta para observação | Utilizar margem de palavra e não a contagem como especificação. |
| Reconstrução do protótipo de Danilo, padrão, c6 e c7 | 6/16 durante a janela e 12/16 em S. c6 DATA1 e DATA7 estavam em 1,409 e 1,253 V, c7 DATA4 e DATA6 em 1,225 e 0,952 V. São indefinidos em S sob 20%/80%. Ambas as palavras estabilizaram depois. Os outros seis FAILs ocorreram na janela, com valor correto em S. | Captura e nova palavra após atraso físico. O ponto S é diagnóstico neste PEX. | Caracterização pendente | Alta | Manter o risco de leitura tardia separado de corrupção de dado. |
| Variantes de rota | Distribuída sem afastamento c6 DATA1/5/7 e c7 DATA7. Par realocado c6 DATA1/5/7 e c7 DATA6. Met4 e acesso interno repetem os mesmos dez FAILs do PEX espaçado sem poda. Em S todas apresentam as duas palavras corretas. | Mesmo prazo de bancada. | Caracterização pendente | Alta | Usar tempos medidos como diagnóstico, manter variantes experimentais. |
| NAND4BB, c6 DATA1/5/7 | Atrasos de 2,61/21,38/27,67 ps na janela. Em S os três bits estavam corretos. c7 passou 8/8 durante a janela. | Nova leitura correta após delay. Nenhum máximo oficial violado. | Caracterização pendente | Alta | Considerar a regressão temporal em conjunto com os ganhos de handoff. |
| 31/72 em SS reportados por Danilo | Sete ciclos com reprovação registrada. O GDS, o PEX e os waveforms originais do transiente de 370 ns não estão disponíveis localmente. A reconstrução cobre dois ciclos de leitura com outra identidade física. | Regras de captura e estabilidade. | Inconclusivo | Alta para o limite da evidência | Manter a contagem como relatada. Sem generalização aos outros cinco ciclos. |
| Reconstrução de Danilo, 24 FAILs de DIN no observador antigo | Replay do mesmo raw deu 32/32 de prontidão antes de WE20 e 32/32 de corrente nas escritas. Os 24 FAILs de subida+1 ns foram preservados à parte. | Captura correta e DIN estável antes da escrita efetiva. | Caracterização pendente | Alta | Preservar os dois observadores e qualificar setup/hold público. |
| Distribuída sem afastamento, DATA1 nas quatro escritas | Picos de 70,25–70,65 µA no PEX RC junto a CLK, TE_B alto, sem erro de dado observado. O acoplamento extraído e a queda dos picos com o afastamento sustentam corrente de deslocamento. | Alta impedância funcional. 50 µA na janela do monitor é diagnóstico. | Sensibilidade de medição | Alta para o pico, média para atribuição | Caracterizar carga e corrente antes de atribuir contenção. |
| Handoff, referência, 300 ps | Oito flags de sobreposição na fixture original. Na v2 com payload oposto há corrente de oposição sustentada. | O host deve esperar a liberação efetiva. O máximo da macro está pendente. | Caracterização pendente | Alta para o evento de sobreposição | Qualificar tDIS e guarda. O estímulo curto não atende à ordem de propriedade observada. |

Nenhum caso local desta matriz demonstrou **falha funcional** persistente da SRAM ou **violação temporal comprovada** de um prazo exigido da macro. Esta classificação não altera os vereditos da fixture e não aprova a macro. Os casos individuais, inclusive tensões intermediárias e transições, estão no CSV do replay. [Bits e capturas](../build/phase3/auditoria_falhas_20261119/leituras_por_bit.csv)

## 3. Disponibilidade da palavra e Fmax

O replay usa o último dos oito instantes de entrada na faixa válida, exigindo permanência até a primeira rampa da sonda (141,500 ns em c6 e 161,500 ns em c7). Mede `CLK↓50→palavra válida` e `tACCESS observado` desde `CLK↑50`. A coluna DATA50 é a maior latência entre bits com cruzamento pós-descida inequívoco no sentido esperado **e** seguida de entrada em faixa válida. Ela não é mais um tempo de validade de palavra. Bits sem transição não recebem zero. Os quatro bits que comutaram em c6 e os oito de c7 estão discriminados no CSV por bit. As medidas são observações offline, sem promover as linhas `NOT_CHARACTERIZED` dos CSVs originais.

| Caso | c6 e c7 no ponto S | CLK↓50 → último DATA50, c6/c7 (ns) | CLK↓50 → palavra estável, c6/c7 (ns) | tACCESS observado, c6/c7 (ns) |
|---|---|---:|---:|---:|
| Protótipo Danilo reconstruído, 6/16 | 6/8 e 6/8 | 0,903 / 0,965 | 1,032 / 1,101 | 11,032 / 11,101 |
| Espaçada padrão 25 ps, 14/16 | 0xAA e 0x55 | 0,821 / 0,841 | 0,911 / 0,875 | 10,911 / 10,875 |
| Espaçada padrão 10 ps, 15/16 | 0xAA e 0x55 | 0,819 / 0,839 | 0,909 / 0,873 | 10,909 / 10,873 |
| Espaçada sem poda, 6/16 | 0xAA e 0x55 | 0,847 / 0,876 | 0,938 / 0,919 | 10,938 / 10,919 |
| NAND4BB, 13/16 | 0xAA e 0x55 | 0,816 / 0,840 | 0,903 / 0,872 | 10,903 / 10,872 |

**Respostas diretas.** (1) O 6/16 da geometria espaçada sem poda significa dez checks fora da janela, com 16/16 corretos em S. O outro 6/16, do protótipo reconstruído, tem quatro níveis ainda indefinidos em S e recuperação posterior. (2) O 14/16 tem a mesma correção de palavra em S que a espaçada sem poda e mais antecedência em relação à abertura. (3) Os nove transientes auditados entregaram as duas palavras esperadas antes da sonda, sem palavra errada persistente ou perda de informação observada nessas leituras. Não há observação de todas as linhas sob todas as condições nem evento de captura do consumidor com deadline público aprovado. O centro S é o único instante nominal especificado pela fixture para observar a nova palavra nesses ciclos. O maior atraso do caso reconstruído deixa 374 ps de estabilidade até a sonda em c7. [Palavras e intervalos](../build/phase3/auditoria_falhas_20261119/palavras.csv)

**(4) Fmax em SS.** Os 20 ns/50 MHz são uma condição aplicada. Falta qualificar o PEX e o domínio de carga, slew, tensão e temperatura, fixar a janela do receptor, medir o limite de fase alta para sense/escrita e captura, o de fase baixa para pré-carga/recuperação, e os orçamentos de setup/hold, palavra estável e direção. Só uma busca controlada de período e duty com sequências de leitura/escrita/máscara cobertas e margem explícita sustenta um limite. O incremento observado de até ~44 ps na palavra entre PEXs pode reduzir a margem do receptor. Não se deduz período mínimo invertendo `tACCESS`.

## 4. Escolha do modelo RC

Na mesma geometria espaçada (`b610c30b…`), as duas extrações usaram Magic 8.3.703, o mesmo executável registrado, `sky130A.magicrc`, 1.749 MOS e o mesmo C-only bruto, confirmado por hash. Ambos os Tcl usam `threshold 0`, `tolerance 1`, `simplify on`, `extout on`, `rthresh 0` e `cthresh 0`. O padrão mantém `mindelay=1 ps` do código do Magic. O outro explicitou `mindelay 0` e `force {DATA[7]}`. A comparação dos transientes fixa SS, 1,8 V, 27 °C, 10 fF/bit, período de 20 ns, slew de 50 ps e passo máximo de 25 ps nos dois casos.

O Magic estima o atraso RC para selecionar e exportar redes e para podar ramos terminais rápidos, fundindo nós. `mindelay 0` desativa esse corte por atraso e mantém outras simplificações. `force` contorna a seleção de exportação do nó, sem desativar a poda dos ramos. Os recibos dão 16.187 contra 19.771 resistores (**+3.584, +22,1%**), mantendo as mesmas contagens de terminais MOS acessíveis pelos trilhos e sem curto resistivo. O aumento não foi isolado como alteração de um único comando. A selagem recuperou 0,04869 e 0,10415 fF, respectivamente, de cartões subatto derivados dos arquivos do Magic. Ambas passaram a auditoria capacitiva por par, com 5.118 e 5.178 pares. Essa auditoria confere contabilização após a redução de nós. Não mede localização das capacitâncias, resistência de contato ou fidelidade dinâmica. Os dois logs registram singularidade no ponto DC inicial e conclusão pelo ponto inicial transiente.

Nesta geometria, desabilitar o corte junto ao `force` agravou a demora observada de palavra em ~27,46 ps (c6) e ~43,98 ps (c7). No PEX padrão, refinar 25 para 10 ps deslocou o cruzamento de DATA7 em ~1,7 ps e trocou apenas a classificação limítrofe da descida. Falta repetição sem poda a 10 ps. O passo máximo fixo compara os dois modelos na mesma configuração e não prova convergência numérica de cada um. Mais resistores ou menor contagem de FAILs não fornecem uma referência física independente. **A escolha entre os modelos é inconclusiva.** [Metadados e checks de integridade dos dois PEXs](../build/phase3/auditoria_falhas_20261119/rc_handoff.json) · [Diagnóstico anterior e histórico do extrator](phase3_danilo_rc_timing_progress_20261115.md#dupla-contagem-confirmada-no-magic-83613) · [Código local do Magic para seleção e poda](../build/phase3/magic-optimized-source/resis/ResRex.c#L2333)

## 5. Propriedade do barramento

Na fixture original, OEb↑ e WEb↓ começam em 167,000 ns. A chave forte de 1 Ω liga perto de 167,328 ns. Na referência espaçada o TE_B80 dos oito bits chega em 167,573–167,592 ns. A sobreposição estimada pelo marcador é de 245–264 ps. O payload coincide com a palavra anterior (0x55), portanto este caso isolado não prova oposição de valores. O replay v2 retirou a sonda fraca antes do handoff final e usou palavra de escrita oposta. O caso de 300 ps mostrou 322–351 ps entre o host ligar e TE_B80 e **84–1.164 µA** de corrente oposta ainda aos +200 ps. Com 1,5 ns houve margem de 848–874 ps para TE_B80, **0,8–4,3 µA** aos +200 ps, oito checks de direção aprovados e leitura de retorno 8/8. A corrente medida inclui deslocamento capacitivo.

| Controle isolado, ref. espaçada em SS | Até TE_B80 | Até `abs(I_probe)≤50 µA` sustentado | NAND4BB, até corrente sustentada |
|---|---:|---:|---:|
| WEb↓ a 50% | 908–937 ps | **821–1.068 ps** | 199–364 ps |
| OEb↑ a 50% | 731–760 ps | 643–888 ps | 263–399 ps |
| CSb↑ a 50% | 724–753 ps | 636–882 ps | 276–420 ps |

A corrente sustentada com o probe de 1 kΩ é a melhor evidência disponível de liberação efetiva sob a carga testada. A tensão correspondente também foi observada. TE_B80 é um marcador interno e não mede impedância sozinho. O valor de 1,5 ns demonstra separação de propriedade no estímulo ensaiado e readback correto. Setup/hold públicos ainda não permitem confirmar uma guarda universal. A sobreposição da guarda curta decorre de o host ligar antes de a referência liberar DATA. Não foi demonstrada sobreposição quando o host esperou a liberação no caso v2 ensaiado. [Waveforms e fonte dos ensaios](phase3_data7_turnaround_20261119.md#desabilitação-medida-na-referência-com-rc-integral)

**Decisão sobre `nand4bb_4`.** Manter como candidata experimental, com integração em espera. Melhorou disable e o handoff curto simultâneo, mas não há exigência pública de 300 ps e até as máscaras isoladas dessa variante ultrapassam 300 ps por corrente. A mudança acrescenta 190,18 µm² de área de células e desloca a chegada de alguns bits de leitura. A necessidade do ECO depende de um orçamento de turnaround validado e de uma comparação de leitura na geometria selecionada.

## 6. Decisão e encerramento

**Precisa ser corrigido**

- No ensaio de conformidade, a premissa de que o host pode assumir DATA em 300 ps precisa dar lugar a uma precondição de liberação verificada. A fixture de estresse e seus FAILs permanecem como evidência.

**Precisa ser caracterizado ou ter o critério revisado**

- Tensão e intervalo de observação do receptor, disponibilidade de palavra, `tDATA_DISABLE` por controle/carga, setup/hold e limites das duas fases. Separar em relatórios a janela de diagnóstico e qualquer orçamento de interface aprovado.

**Ainda não pode ser decidido**

- O PEX de referência, Fmax em SS, a necessidade de novos ECOs e a condição dos outros ciclos do protótipo original de Danilo.

**Única próxima tarefa recomendada** — verificar a fidelidade local do RC na geometria espaçada, em um único caso de controle físico do ramo DATA7 e sua conexão com Q/driver. Confrontar as duas redes RC já salvas no trecho que diverge com uma referência passiva independente do mesmo GDS, usando a resistência geométrica/contatos e a capacitância/acoplamento da vizinhança por regra verificada ou segundo extrator. Congelar de antemão os terminais e a incerteza do método. Concluir com R efetiva por polaridade, C incidente/acoplada e um erro por perfil para a mesma quantidade física. Se só um perfil concordar dentro da incerteza e a divergência explicar o atraso observado, há base para usá-lo nesse caminho. Se ambos concordarem ou se a referência não discriminar os perfis, registrar explicitamente a indeterminação da calibragem. Essa tarefa evita usar o número de FAILs como critério para escolher o extrator. Ela não foi iniciada nesta auditoria.

**Execução.** Nove waveforms de leitura e três de handoff foram reanalisados offline, com hashes dos manifests, waveforms, probes e arquivos derivados verificados. As duas cadeias PEX foram conferidas até os recibos. Não houve SPICE novo, alteração física, rerun de DRC/LVS, commit, push ou merge. Os 165 testes de infraestrutura e 41 de RC/ECO aprovados na rodada anterior são evidência de software/harness. Nesta rodada foram conferidos seus recibos, sem nova regressão nem promoção do veredito elétrico. Os scripts de replay estão no pacote desta auditoria. As evidências completas de entrada foram preservadas no pacote anterior `phase3_data7_turnaround_20261119.zip`.
