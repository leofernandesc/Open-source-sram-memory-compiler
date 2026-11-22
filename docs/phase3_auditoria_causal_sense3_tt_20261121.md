# Fase 3 — Auditoria causal comparativa do sense 3 em TT

**`JOINT_TIMING_HYPOTHESIS_STRENGTHENED`.** Em c16 e c17, B (atraso dos três gates) chega ao início da condução observável do tail com **191/197 mV** de polarização favorável entre SAB e SA. C (só tail) chega com **85/89 mV**, embora seu BLB−BL seja ligeiramente maior e o primeiro 1 µA do tail ocorra menos de 0,35 ps antes. A diferença de corrente nos samplers e de polarização do latch já é observável antes desse marco. Há fundamento para estudar um acionamento físico coordenado local. A macro permanece parcial no Marco 3. [Medições e hashes](../build/phase3/sense3_causal_audit_20261121/analysis.json)

## Compatibilidade

As letras A/B/C deste relatório identificam os três **ensaios do mesmo recorte** da macro física C. O PEX verificado tem SHA-256 `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`. Condições comuns SKY130A TT, 1,8 V, 27 °C, Gear/KLU, passo máximo de 25 ps, 36 MOS, 493 resistores e 968 capacitores. O tempo local de 0–59 ns corresponde a 188–247 ns na referência arquivada.

| Verificação | A — Controle | B — Três gates | C — Só tail |
|---|---|---|---|
| Recorte e fonte local | Controle histórico validado. VSHIFT = 0 V em R87 | Mesmo slice. VSHIFT em série antes de R87 | Mesmo slice após normalizar a inserção em série VTAIL antes de R76. R87 em 0 V |
| Deck principal, sondas e estímulos | Referência, 13.980 amostras | Mesmos hashes de `bench.spice` e `stimuli.spice`. 15.525 amostras | Mesmos hashes de `bench.spice` e `stimuli.spice`. 14.740 amostras |
| BL/BLB de fronteira, PRECH, VDD e SCLK a montante | Replay histórico | Diferença medida de até 0,34 µV | Diferença medida de até 0,29 µV |
| c15 e estado anterior à primeira intervenção | D correto em c15, NTAIL recuperado | D correto em c15, desvio máximo dos sinais verificados de 0,044 µV | D correto em c15, desvio máximo de 1,75 µV |
| NTAIL antes de c16 / c17 (V) | 1,148267 / 1,147638 | 1,148267 / 1,147620 | 1,148267 / 1,147638 |
| Descida e pré-carga | Referência | Bordas 20/50/80% dos gates até 0,475 ps da referência. Sem intervalo novo de tail acima de 1 µA durante a recuperação monitorada | Bordas equivalentes. Mesmo critério de recuperação atendido |

O ponto local `rc8571` fica **a jusante** da fonte de B e sua subida atrasa junto com os gates. Em C, a fonte fica depois da bifurcação e só atrasa o gate do tail. O SCLK compartilhado medido é `rc8562`, a montante das duas inserções. A posição da fonte local é uma diferença entre B e C. Ela preserva as resistências de ramo e pode mudar a resposta de carga do segmento comum. Os três ensaios usam o mesmo instante de captura arquivado na macro. Q, DATA, correntes separadas de junção e de deslocamento e resposta dos outros sete senses sob uma carga física local estão ausentes deste recorte. A recuperação interna de B depois de c16 foi diferente da de A/C, então c17 é repetição sob o histórico de cada ensaio. [Arquivos do controle e de B](phase3_precondicionamento_sense3_tt_20261120.md) · [Arquivos de C](phase3_contraste_tail_only_sense3_20261121.md)

## Tempo absoluto e relativo

| Ciclo / ensaio | Primeira separação favorável (ns) | Tail a 1 µA (ns) | Primeira inversão após 1 µA (ns / ps relativos) | Sense sustentado desde (ns) | D na captura (V) |
|---|---:|---:|---:|---:|---:|
| c16 A | 214,171 | 214,277 | 214,587 / +310 | 214,795, incorreto | 1,80045 |
| c16 B | 214,167 | 214,462 | Ausente até captura | 215,007, correto | 0,000196 |
| c16 C | 214,172 | 214,462 | 214,766 / +304 | 214,967, incorreto | 1,80045 |
| c17 A | 234,161 | 234,278 | 234,597 / +319 | 234,809, incorreto | 1,80045 |
| c17 B | 234,158 | 234,463 | Ausente até captura | 235,003, correto | 0,000197 |
| c17 C | 234,162 | 234,463 | 234,775 / +312 | 234,980, incorreto | 1,80045 |

Capturas em 220,058 e 240,058 ns. Em B, D entrou na banda baixa sustentada por volta de 215,291 e 235,287 ns, com pelo menos 4,76 ns antes da captura. Em A e C, D seguiu alto na janela avaliada. As primeiras polaridades favoráveis são cruzamentos de SAB−SA após o início da janela arquivada da avaliação. O teste funcional exige SA/SAB e D sustentados na polaridade esperada.

| Ensaio | Samplers antes/depois do tail em 20/50/80% | Skew máximo BL–BLB nos três marcadores | 1 µA relativo à subida 20% dos samplers |
|---|---|---:|---:|
| A | Ambos entre −0,2 e +1,5 ps do tail | 0,46 ps | +122 ps aprox. |
| B | Ambos entre −0,2 e +2,0 ps do tail, subida coordenada | 0,54 ps | +124 a +126 ps |
| C | Ambos adiantados de 180,5 a 181,9 ps em relação ao tail | 0,31 ps | +306 a +308 ps |

Por exemplo, em 50% a corrente de tail em A/B atingiu 1 µA cerca de 127–131 ps **antes** da borda dos samplers. Em C, o mesmo marcador ocorreu cerca de 54 ps **depois** da borda de 50% dos samplers. Os cruzamentos por gate, offsets assinados e intervalos aos respectivos 20%, 50% e 80% constam do CSV. Os três últimos dígitos de qualquer delta pequeno vêm da interpolação, com precisão física limitada pelos pontos nativos. [Tempos dos gates](../build/phase3/sense3_causal_audit_20261121/gates.csv) · [Séries até captura](../build/phase3/sense3_causal_audit_20261121/series.csv)

Foram usados os `id` arquivados de X235, X521 e X351. O primeiro `|Id| = 1 µA` de X351 no pulso de avaliação é um marco reprodutível, com a posição absoluta preservada. Corrente subumbral já circula antes dele. Para os samplers, as janelas de 10–90% do integral de `|Id|` descrevem a incidência temporal da corrente medida entre o começo da janela de avaliação e o fim da fase alta analisada. Esse integral quantifica corrente ao longo do tempo. A orientação distinta dos terminais e a falta de correntes capacitivas impedem usá-lo como carga líquida entregue ao latch.

| Ciclo | Janela 10–90% de X235 em A / B / C (ns) | Janela 10–90% de X521 em A / B / C (ns) |
|---|---|---|
| c16 | 214,161–214,373 / 214,190–214,443 / 214,162–214,385 | 214,143–214,409 / 214,225–214,561 / 214,152–214,473 |
| c17 | 234,158–234,370 / 234,185–234,439 / 234,159–234,381 | 234,143–234,409 / 234,223–234,560 / 234,151–234,471 |

[Gráfico em tempo absoluto](../build/phase3/sense3_causal_audit_20261121/absolute.png) · [Gráfico alinhado pelo tail](../build/phase3/sense3_causal_audit_20261121/relative.png)

## Primeira divergência mensurável entre B e C

**Observado.** Na subida original dos samplers de C, ainda antes de os tails B/C atingirem 10%, as correntes dos samplers já divergem. No SCLK20 de A, X521 mede aproximadamente 2,0/2,1 µA em B contra 5,3/5,4 µA em C, com magnitudes próximas de SAB−SA. No marco de 10% do tail de B, cerca de 196/197 ps antes de 1 µA, X235 ainda conduz **40,8/41,7 µA em B, contra 30,7/31,2 µA em C**. Os tails B/C medem cerca de 13 pA nesse mesmo instante. SAB−SA já é **64/70 mV em B, contra 42/47 mV em C**. Em B, SA está 28–30 mV mais baixo que em C e SAB está 7–8 mV mais baixo. A primeira divergência relevante está na evolução prévia das correntes dos samplers e da polarização do par. A inversão posterior é consequência observada na sequência, centenas de picossegundos mais tarde.

Na janela absoluta comum do tail20 de A até o primeiro 1 µA entre B/C, o integral de `|Id|` de X235 aumenta de **6,25/6,32 fC em C para 10,58/10,74 fC em B**. Para X521, varia de 1,85/1,87 fC para 1,94/1,96 fC. No primeiro 1 µA, X235 ainda mede 17,1/16,0 µA em B e 3,1/2,9 µA em C. NTAIL então está cerca de 18 mV mais baixo em B, apesar do NTAIL inicial praticamente idêntico. A diferença em SAB−SA já atingiu **+106/+108 mV** em favor de B, com a maior parcela devida à queda de SA. A e C mantêm perfis próximos de SAB−SA alinhados pelo tail e invertem por volta de +304 a +319 ps. B mantém a polaridade favorável, com SAB−SA por volta de +479/+499 mV em +400 ps, enquanto C está em −325/−283 mV. Os picos de X351 em A, B e C ficam, respectivamente, em **133, 158 e 136 µA**, aproximadamente. [Quadros de comparação e perfis relativos](../build/phase3/sense3_causal_audit_20261121/analysis.json)

**Inferência sustentada.** A temporização coordenada mantém a contribuição dos samplers na janela em que a polarização que chega ao latch ainda está sendo formada. A polarização interna favorável é maior já antes da condução pronunciada do tail e permanece favorável durante a regeneração. BLB−BL no primeiro 1 µA é 458/473 mV em B e 464/477 mV em C. Esse instantâneo de amplitude na entrada não explica a diferença funcional.

**Em aberto.** Os dados não separam a contribuição individual de cada sampler nem distinguem condução e injeção de carga pelas capacitâncias de porta. A diferença em modo comum do latch e NTAIL pode contribuir para a decisão posterior. Um desbalanceamento interno pode determinar a sensibilidade ao estado de entrada. A colocação diferente das fontes em B e C e o replay sem impedância ativa completa do array são limites adicionais. Os dados sustentam a relação temporal e a condição interna resultante no recorte. Atribuição exclusiva a um mecanismo, seleção de dimensionamento e extrapolação para a macro carregada permanecem pendentes.

## Decisão física

Há evidência suficiente **para estudar um acionamento conjunto local** no ramo privado dos três gates. Uma solução física teria de entregar a forma de onda eficaz sob carga, evitar interferência em PRECH e no SCLK dos outros sete senses e preservar a desativação. O aumento do pico de X351 em B já recomenda observar a carga e o slew reais. Um driver físico v1 em recorte corrigiu o sense com forma de onda bastante diferente e pico de aproximadamente 327 µA. Isso mantém v1 como evidência experimental. A alternativa de redesenhar o latch tem justificativa menor diante da correção obtida com a mesma estrutura e mudança de temporização. O Marco 3 permanece parcial enquanto a integração de TT e as demais pendências estiverem abertas. [Driver local experimental](phase3_driver_local_sclk_tt_20261120.md)

**Próximo ensaio justificável, condicionado à escolha de um candidato físico:** testar um único estágio local de retardo assimétrico no recorte já validado, substituindo apenas o acionamento ideal de R87 em B. Manter PEX, estímulos, c15 e critérios históricos. PASS exige subida coordenada dentro da faixa de B nos três gates, descida preservada, c16/c17 corretos até a captura e ausência de nova sobreposição com PRECH. Fora desse envelope, FAIL da transferência para o candidato. A carga sobre a rede global e os outros senses fica para uma etapa separada de integração.

## Estado preservado

| Item | Estado |
|---|---|
| Macro C em TT | `FAIL` funcional em c16/c17, linha 3 retorna `0xF8` em vez de `0xF0` |
| Macro C em SS | `PASS` funcional no escopo ensaiado, 9/9 leituras, 6/6 escritas confirmadas e 18/18 verificações de barramento |
| FF integrado | Pendente |
| Monte Carlo Hold/Read | Concluído no domínio experimental esquemático `tt_mm`, com 200 Hold e 206 Read. Homologação pendente |
| Qualificação elétrica da macro | `NOT_CHARACTERIZED` |
| Liberty | Pendente |

Zero simulações e nenhum deck novo. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`. Os dois testes offline cobrem a integral de corrente com cruzamento de zero e o suporte temporal das fontes. A correção da verificação inicial do nó pós-R87 em B aplicou o envelope já existente para a subida deliberadamente atrasada. Os dados e os envelopes foram preservados. [Recibos, gráficos e CSVs](../build/phase3/sense3_causal_audit_20261121/)

```sh
out=$(mktemp -d build/phase3/sense3_causal_check.XXXXXX)
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/tools \
  python3 /work/tools/audit_phase3_sense3_joint_timing.py "/work/$out"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest discover \
  -s tests -p test_phase3_sense3_joint_timing.py -v
```
