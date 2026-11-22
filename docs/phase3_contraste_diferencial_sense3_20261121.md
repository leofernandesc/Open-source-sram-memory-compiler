# Fase 3 — Préflight do contraste diferencial no sense amplifier 3 em TT

**Controle histórico `VALIDATED` · Bancada para o contraste `NOT_READY` · Contraste `NOT_RUN` · Suficiência diferencial `INCONCLUSIVE`.** Nas duas leituras, antecipar a trajetória diferencial em 182 ps exigiria aproximadamente 2,006 V na fronteira BLB no marcador SCLK20, com VDD de 1,8 V e modo comum fixo. Durante toda a janela inicial de equivalência, o modo comum já está acima de VDD. Foram executadas zero simulações.

## Identidade e controle

O recorte padrão da geometria C preserva 36 MOS, 493 resistores e 968 capacitores. Foram conferidos o GDS, o LEF, o PEX, a preparação integrada TT, o binding com sondas, a referência TT reduzida, os recibos, os decks e as formas de onda do controle e do contraste ideal anterior. O fechamento instalado dos modelos SKY130A coincide com os 319 hashes arquivados. As condições do recorte são TT, 1,8 V, 27 °C, Gear/KLU e passo máximo de 25 ps. O tempo nesta análise refere-se ao transiente TT reduzido original. O recorte de 59 ns mapeia o tempo local 0–59 ns para 188–247 ns. [Manifesto](../build/phase3/sense3_diff_advance_20261121/manifest.json) · [Gate histórico](../build/phase3/sense3_preconditioned_20261120/control_gate.json)

- GDS `b610c30b563c5830900792440e4f4295777029cfd9ab4496072f7d22fdab3365`.
- LEF `1b5250a4a1726a9e14b21d6ea5de8884c60f7750a10e20c8537cb6e4bac63091`.
- PEX padrão `12c41d1a01c4af859668809fd92817d4e80318f4c170fae3a72e83870e7df95a`.
- Controle, 13.980 amostras, `5954927da87434f44fe067d422c9e55769b62051d01225ef9587ed9ea6199fd5`. [Deck e estímulos](../build/phase3/sense3_preconditioned_20261120/control/) · [Sondas e análise do recorte](phase3_precondicionamento_sense3_tt_20261120.md)

As fontes existentes são `VPORT0 rc8202 VSS` e `VPORT1 rc8216 VSS`, nas fronteiras de replay da coluna 3. Os terminais nos samplers são `rc8210` e `rc8222`, atrás da malha RC retida. A resistência efetiva da malha passiva é aproximadamente 475,6 Ω para cada lado. O recorte mantém o mesmo histórico de SCLK, PRECH, VDD e das demais fronteiras. Em c15, sense e D ficam altos e SAB baixo de 199,5 a 200 ns. NTAIL passa de 1,433 V em 188 ns para 1,130 V em 208 ns após a avaliação e recuperação. O erro máximo contínuo de NTAIL frente à referência em c16/c17 foi 12,7/13,2 mV, dentro do envelope histórico de 30,169 mV. [Manifesto anterior](../build/phase3/sense3_preconditioned_20261120/manifest.json) · [Validação do recorte](phase3_precondicionamento_sense3_tt_20261120.md)

## Intervenção proposta e limite físico

Foi fixada a antecipação de **182 ps** para comparar com o deslocamento inverso e de mesma magnitude do experimento anterior. Naquele contraste, o SCLK tardio encontrou BLB−BL de 229/239 mV nos terminais do sense no marcador local de 20%, com decisão correta sustentada. Na proposta atual, o alvo de fronteira é `Δ'(t) = Δ(t + 182 ps)`, com o SCLK original. O alvo nas fontes e a tensão resultante nos terminais internos são grandezas distintas. [Contraste ideal arquivado](../build/phase3/sense3_preconditioned_20261120/contrast_gate.json) · [Auditoria TT × SS](phase3_auditoria_temporal_tt_ss_20261121.md)

Manter o modo comum das fontes em `CM(t)` deixa um único par possível para cada alvo, `BL' = CM − Δ'/2` e `BLB' = CM + Δ'/2`. Com VSS em 0, existe par dentro dos trilhos apenas se `|Δ'| ≤ 2 min(CM, VDD − CM)`. O cálculo usa os nós da união dos PWLs originais e deslocados e resolve as interseções lineares. Como a condição usa trechos lineares, o bloqueio na janela inicial vale também entre amostras. A janela de ±50 ps em torno do SCLK20 da referência foi reutilizada do controle. Ela serve para localizar a avaliação inicial da bancada, sem definir um prazo público.

| Grandeza nas fronteiras | c16 | c17 |
|---|---:|---:|
| Janela inicial arquivada (ns) | 214,103–214,203 | 234,103–234,203 |
| CM no SCLK20 do controle (V) | 1,859 | 1,855 |
| Δ original → alvo no SCLK20 (mV) | +39 → +293 | +46 → +304 |
| BLB original → requerida no SCLK20 (V) | 1,879 → 2,005 | 1,878 → 2,007 |
| BLB requerida no marcador de 1 µA do tail (V) | 2,015 | 2,014 |
| Menor excesso do alvo acima de 1,8 V na janela inicial (mV) | +178 | +182 |
| Primeiro instante em que o alvo cabe nos trilhos no intervalo auditado (ns) | 214,667 | 234,663 |
| Inversão já observada no latch do controle (ns) | 214,587 | 234,597 |

O excesso original em BLB chega a aproximadamente 79 mV no intervalo auditado. A trajetória calculada adicionaria cerca de 127–129 mV a BLB no marcador SCLK20 em relação ao próprio histórico, alcançando um valor acima até do máximo original da fronteira. Preservar `Δ'` e limitar BLB a VDD exigiria reduzir CM em pelo menos 205/207 mV nesse instante. O resultado decorre da soma das tensões nas fontes. Uma transição suave ou um avanço menor ainda encontraria CM acima do trilho durante toda a janela inicial. Começar após 214,667/234,663 ns testaria uma perturbação posterior à inversão observada. [Curvas calculadas](../build/phase3/sense3_diff_advance_20261121/trajectories.csv) · [Gráfico comparativo](../build/phase3/sense3_diff_advance_20261121/rail_feasibility.png)

## Regeneração medida no controle

| Medição | c16 | c17 |
|---|---:|---:|
| NTAIL antes da subida pública (V) | 1,1483 | 1,1476 |
| SCLK20 / SCLK50 do tail (ns) | 214,154 / 214,408 | 234,154 / 234,408 |
| BLB−BL interno em SCLK20 → marcador de 1 µA (mV) | +15,4 → +146,5 | +20,5 → +157,2 |
| CM interno em SCLK20 → marcador de 1 µA (V) | 1,873 → 1,788 | 1,870 → 1,781 |
| Primeiro sinal favorável de SAB−SA (ns) | 214,171 | 234,161 |
| Primeiro marcador de condução do tail a 1 µA (ns) | 214,277 | 234,278 |
| Inversão do sinal de SAB−SA (ns) | 214,587 | 234,597 |
| Pico de corrente na faixa de condução medida (µA) | 133,23 | 133,18 |
| Captura local da referência (ns) | 220,058 | 240,058 |
| D na captura de referência (V) | 1,800 | 1,800 |
| Decisão errada estável até captura (limite conservador) | ≥5,26 ns | ≥5,24 ns |

A primeira separação favorece o zero esperado. A inversão produz um um lógico sustentado em D antes da captura. A resolução vem dos pontos nativos e da interpolação linear. No trecho ampliado, o maior intervalo entre amostras é cerca de 13 ps. SCLK20 indica fase da forma de onda e 1 µA é um marcador de corrente da bancada. O JSON conserva as bordas de subida e descida e slew dos três gates. O CSV conserva também SCLK compartilhado, PRECH, NTAIL, alimentação e ambas as bitlines nos marcadores. [Tabela de marcadores](../build/phase3/sense3_diff_advance_20261121/markers.csv)

| Critério | Controle TT | Diferencial antecipado |
|---|---|---|
| SCLK local e compartilhado, PRECH e VDD | Formas de onda e deck verificados | Fontes preservadas no plano. Equivalência elétrica sem medição |
| CM de BL/BLB | Medido na fronteira e nos terminais | CM fixo na reconstrução matemática. Bloqueio nos trilhos na janela inicial |
| BLB−BL na avaliação | Positivo e crescente | Alvo de fronteira calculado. Entrega aos samplers sem medição |
| NTAIL e corrente do tail | Estado inicial validado e corrente medida | Sem medição da intervenção |
| Polaridade inicial e final, D | Inicial favorável, final incorreta, D alto até captura | Sem decisão observada em c16 ou c17 |

## Conclusão e próxima tarefa

O teste de suficiência ficou bloqueado pela fronteira de replay. A evidência temporal anterior e a correção com SCLK tardio permanecem válidas no escopo original. Este preflight deixa em aberto se antecipar o diferencial seria suficiente e quanto a dinâmica do latch contribui para a inversão. Também permanece em aberto se uma intervenção que corrija c16 mudaria naturalmente a condição inicial de c17.

**Próxima tarefa única** — localizar no PEX e na referência TT uma fronteira BL/BLB a montante dos samplers com impedância rastreável e margem nos trilhos para o avanço diferencial durante a janela inicial. O critério é identificar os nós e caminhos de acoplamento, verificar o par admissível com o modo comum arquivado e manter condições para revalidar o controle c15–c17 com SCLK original. Se a fronteira não existir no replay, o teste de diferencial isolado continua bloqueado nesta formulação.

C segue como referência de integração com `FAIL` funcional TT e `PASS` em SS no escopo ensaiado. B′ segue inconclusivo para c16/c17. O driver v1 segue em espera. Monte Carlo experimental permanece com 200 Hold e 206 Read válidas. Qualificação geral `NOT_CHARACTERIZED`. Branch `integration/phase3-danilo-ss`, HEAD `8e1d961d65054b59f9032ed5f9338d9ee4353c33`.

## Reprodução

O pacote contém os decks e waveforms históricos utilizados, manifesto, CSVs, gráfico, analisador, testes e hashes. Como o gate de alimentação falhou, o alvo calculado ficou em CSV e o único deck SPICE incluído para o novo plano é o controle histórico. O contraste ideal anterior permanece disponível como evidência arquivada.

```sh
out=$(mktemp -d build/phase3/sense3_diff_check.XXXXXX)
tools/sram-eda env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/tools \
    python3 /work/tools/phase3_sense3_diff_advance.py "/work/$out"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest discover \
    -s tests -p test_phase3_sense3_diff_advance.py -v
```

Cinco testes de software passaram. Novos arquivos rastreáveis nesta rodada são este relatório, `tools/phase3_sense3_diff_advance.py` e `tests/test_phase3_sense3_diff_advance.py`. Artefatos derivados ficam em `build/phase3/sense3_diff_advance_20261121/`. O diff dos arquivos já rastreados foi conferido contra a abertura da rodada. O recibo no pacote registra a comparação do Git, a duração e a integridade do ZIP.
