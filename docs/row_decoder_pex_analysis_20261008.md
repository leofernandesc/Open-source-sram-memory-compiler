# Análise elétrica do decoder após extração — 08/10/2026

> Evidência histórica de 39f5ebc, anterior às correções remotas de 7ad0348.
> O [handoff de compactação](row_decoder_layout_compaction_20261008.md) contém
> o estado da geometria atual, cujo novo PEX está pendente.

Atualização posterior: as simulações diagnósticas propostas foram executadas.
Resultados, waveforms e convergência estão em
[`row_decoder_pex_diagnostics_20261008.md`](row_decoder_pex_diagnostics_20261008.md).
O texto abaixo preserva a análise anterior às novas simulações.

O decoder dinâmico chega à linha correta nos 13 casos registrados. Quatro
casos SS/1,62 V/−40 °C ultrapassam o critério experimental de estabilização
da WL em 1 ns. A regressão temporal aparece principalmente antes da saída
DEC. O roteamento de redes internas por toda a largura da célula é um candidato
forte para explicar a carga adicional, mas sua contribuição causal ainda
precisa de uma comparação controlada de simulações.

Esta análise usa artefatos existentes; não executa nova simulação, extração,
DRC ou LVS. Nenhum schematic, layout, modelo ou limite do checker foi alterado.

## Fontes e reprodução

- Revisão analisada: `39f5ebc`, branch `feature/peripherals`.
- Especificação: `specs/technical_specification.md`, seções 6, 9, 10 e 20.
- Campanha: `sims/row_decoder/results/row_decoder_pex_output_pfets_3um_20261008/`.
- PEX: `layout/row_decoder/archive/precompact_20261008/pex/row_decoder_pex.spice`.
- SHA-256 do PEX: `c3e39efae880fd46fddd0d610f9dd789a3beeee847c62ba2fbdaa1bf88419128`.
- Analisador: `sims/row_decoder/analyze_row_decoder_pex.py`, apenas biblioteca
  padrão Python; confere o hash e a conclusão da campanha antes de analisar.
- Tabelas e hashes dos arquivos de entrada:
  `sims/row_decoder/results/row_decoder_pex_analysis_20261008/`.

```bash
python3 sims/row_decoder/analyze_row_decoder_pex.py
```

A campanha contém nove transições TT/1,8 V/27 °C e quatro diagonais
SS/1,62 V/−40 °C. Usa Gear, passo máximo de 5 ps, bordas de 50 ps, endereço
externo estabelecido 2 ns antes da avaliação, fase alta de 5 ns e intervalo
de pré-carga de 10 ns. O PEX substitui somente o decoder: quatro buffers de
WL permanecem esquemáticos, cada um com carga estimada de 17,4 fF.

## O que falhou e o que passou

Os 1.456 checks funcionais/temporais do baseline passam. No PEX, oito checks
falham: duas janelas de WL selecionada por caso lento, nas avaliações `prime`
e `test`. Todos estão classificados como `settling_allowance_only=True`.
Os outros 1.448 checks passam, inclusive linha não selecionada, nível final,
pré-carga e recuperação dos quatro nós dinâmicos.

O código verifica o **mínimo da janela que começa 1 ns após o cruzamento de
50% de PCLK**, terminando antes da borda de descida. Não é apenas uma amostra
isolada em 1 ns. O limite é `0,9 × VDD = 1,458 V` nos casos lentos.

| Caso lento | Mínimo WL em prime (V) | Mínimo WL em test (V) | DEC a 90%, test (ps) | WL a 90%, test (ps) | Excesso sobre 1 ns (ps) |
|---|---:|---:|---:|---:|---:|
| 00 → 11 | 1,251 | 1,201 | 688,57 | 1.141,66 | 141,66 |
| 11 → 00 | 1,255 | 1,204 | 680,74 | 1.140,28 | 140,28 |
| 01 → 10 | 1,328 | 1,252 | 652,66 | 1.120,54 | 120,54 |
| 10 → 01 | 1,306 | 1,319 | 620,02 | 1.088,92 | 88,92 |

Em TT, o maior atraso WL a 90% é 796,35 ps. As linhas não selecionadas têm
pico máximo de 55,00 mV na matriz PEX, abaixo dos respectivos limites de
10% de VDD. Isso demonstra o comportamento observado nessas condições, sem
qualificar todas as condições de uso.

**Correção de interpretação:** o prazo de 1 ns é um screen experimental do
testbench, documentado em `docs/row_decoder_contract_characterization.md`.
A especificação não fixa esse prazo nem a frequência máxima: a frequência
será resultado da caracterização. As quatro falhas devem continuar registradas;
nenhum limite foi relaxado. Elas não demonstram, por si sós, seleção de linha
errada ou uma violação de frequência já aprovada para a macro.

## Onde o atraso adicional aparece

Nos casos lentos, o baseline chega a DEC a 90% em 143,02–150,40 ps e a WL em
672,15–679,28 ps. Com o PEX, esses intervalos passam a 620,02–688,57 ps e
1.088,92–1.141,66 ps, respectivamente.

Comparando os cruzamentos de **50%**, o aumento medido em DEC corresponde a
83,75–85,11% do aumento medido em WL nos casos lentos; em TT, a 89,64–90,99%.
Esse quociente localiza a maior regressão antes de DEC. Ele não é uma divisão
independente da dissipação ou do atraso de cada estágio. A carga de entrada
do WL driver e o slew recebido continuam influenciando o decoder.

Portanto, redimensionar somente o buffer de WL não é a primeira ação sustentada
pelos dados. Ainda não é possível separar a parcela da descarga N, da carga
do inversor de saída e do acoplamento usando apenas os resumos existentes.

## Capacitâncias e roteamento

`build_layout.py` cria uma trilha M3 por rede entre as coordenadas internas
400 e 44.500, independentemente dos terminais realmente atendidos. O
`route_row_decoder.tcl` confirma esse padrão, inclusive em `N0..N3`,
`net1..net4`, `EVAL_GND` e `DEC0..DEC3`. São conexões globais até para redes
que poderiam ficar locais ao respectivo ramo.

| Rede | Soma de C incidentes (fF) | Parcela ligada diretamente ao port VSS (fF) |
|---|---:|---:|
| N0 | 18,525 | 0,000 |
| N1 | 18,620 | 0,000 |
| N2 | 19,720 | 1,021 |
| N3 | 18,736 | 0,000 |
| net1 | 27,716 | 11,966 |
| net2 | 32,067 | 16,288 |
| net3 | 35,377 | 19,518 |
| net4 | 36,768 | 20,875 |
| EVAL_GND | 61,409 | 36,420 |
| DEC0 | 36,562 | 21,900 |
| DEC1 | 32,872 | 18,134 |
| DEC2 | 33,229 | 18,455 |
| DEC3 | 41,180 | 31,478 |
| A0B | 22,923 | 0,000 |
| A1B | 23,145 | 0,000 |
| A0T | 20,727 | 0,000 |
| A1T | 20,893 | 0,000 |

As somas incluem capacitores de acoplamento e excluem as capacitâncias
intrínsecas dos modelos MOS. Não são uma carga efetiva constante: o efeito
depende do movimento das outras redes. Uma parcela zero para VSS não significa
ausência de carga, pois há acoplamento com VDD e outros sinais.

É **inferido** que a extensão dessas conexões contribui para atraso,
acoplamento e assimetria entre linhas. A topologia dinâmica continua indicada
pela especificação; esta evidência favorece investigar o roteamento antes
de voltar a aumentar todos os transistores.

## As resistências altas significam uma alimentação de 127 kΩ?

Não. Os **393 resistores presentes neste PEX pertencem à rede VSS**. O
log do extrator registra 22 redes extraídas e somente uma rede emitida como
rede resistiva. N0..N3 e DEC0..DEC3 permanecem equipotenciais no arquivo atual;
não há resistores explícitos nessas redes. Assim, este PEX contém R-C, mas
não representa uma distribuição resistiva de todas as redes de sinal.

O maior resistor individual vale 127,231 kΩ. Isso não é a resistência total
entre um transistor e VSS. Uma redução DC da rede, com MOS e C removidos e
VSS como referência, considera todos os caminhos paralelos:

| Contato ligado à rede VSS | R equivalente DC ao port VSS (Ω) |
|---|---:|
| M8, footer de avaliação | 9,392 |
| M10, inversor DEC0 | 11,721 |
| M15, inversor DEC1 | 17,550 |
| M20, inversor DEC2 | 23,376 |
| M25, inversor DEC3 | 29,201 |

Os contatos de difusão ligados a VSS apresentam 2,403–33,663 Ω; os contatos
de bulk dos NFETs, 234,265–321,768 Ω. A orientação D/S emitida pelo Magic
pode ser oposta à do schematic; o analisador identifica os dispositivos pela
conectividade. Esses valores são uma análise DC da rede resistiva isolada,
não uma medição de ground bounce nem um descarte de efeitos transitórios.
Não sustentam atribuir a falha a um único resistor de 127 kΩ.

## Avisos de tensão e margem

Cinco casos PEX excedem o screen experimental de magnitude de 1,95 V.
O pior extremo de cada caso se concentra em M1/M2, o inversor original de A0:

| Caso | MOS no schematic | Tensão no PEX | Pico assinado (V) | Instante (ns) |
|---|---|---|---:|---:|
| TT 00 → 10 | M2 | VGS | −2,092 | 18,000 |
| TT 00 → 11 | M2 | VDS | −2,126 | 18,000 |
| TT 11 → 00 | M1 | VDS | +2,186 | 18,000 |
| SS 00 → 11 | M2 | VDS | −1,9505 | 18,000 |
| SS 11 → 00 | M1 | VDS | +2,000 | 18,000 |

O endereço termina sua transição em 18 ns e a segunda avaliação de PCLK
começa em 20 ns. Portanto, esses extremos ocorrem na mudança do endereço,
durante a pré-carga; não são apenas um artefato inicial de `uic` em t=0.
Acoplamento e carga das redes de endereço são candidatos a investigar, mas
os extremos não permitem identificar sozinhos o caminho causal.

Há um capacitor explícito `C183 A0B A1B 5.48408f`. Os inversores originais
M1/M2 ainda têm W=0,42 µm. No caso TT 00 → 10, A0 permanece em zero e
X5/M2 tem o gate em A0 e o terminal S emitido pelo Magic em A0B. Logo, o
VGS de −2,092 V registrado corresponde a **A0B ≈ 2,092 V**, embora a
alimentação seja 1,8 V e A0 não tenha mudado. No caso TT 11 → 00, X20/M1
tem D em VDD e S em A0B: seu VDS de +2,186 V corresponde a
**A0B ≈ −0,386 V**. Esses valores são derivados dos extremos de tensão
e das fontes ideais declaradas, não uma waveform nova. Eles reforçam a
investigação de acoplamento e capacidade de manter os níveis das redes de
endereço; não provam qual capacitor isolado causa a excursão.

O campo `output_vgs_peak_v`/`model_upper_result` do checker usa o máximo de
N0..N3. Em um circuito idealmente aterrado isso aproxima a tensão gate/rail
do NFET de saída; no PEX não é uma varredura completa dos biases locais.
Seu PASS não elimina os avisos de magnitude nem qualifica a faixa assinada
dos modelos e a confiabilidade dos dispositivos.

Outro ponto crítico: o pior tempo de WL até 10% na pré-carga é **999,896 ps**.
A diferença para o screen de 1 ns é apenas **0,104 ps**, menor que o passo
máximo de 5 ps usado. O PASS registrado não demonstra margem numérica ou
elétrica suficiente nesse ponto; é necessária comparação com passo mais fino.

## O que as iterações de sizing ensinaram

| Pré-carga / stack / PMOS de saída (µm) | WL a 90%, SS (ps) | WL a 10% na pré-carga, SS (ps) |
|---|---:|---:|
| 1 / 1 / 2 | 1.253,28–1.314,34 | 1.290,05–1.405,96 |
| 2 / 2 / 2 | 1.165,98–1.234,68 | 930,69–988,97 |
| 2 / 2 / 3, atual | 1.088,92–1.141,66 | 942,69–999,90 |

As comparações mantêm o stimulus e a carga, mas incluem layouts/PEX regenerados.
O aumento de 2 para 3 µm do PMOS de saída melhora a avaliação e piora a
pré-carga medida. Não existe evidência para continuar aumentando W indiscriminadamente.
A seleção de maior margem e robustez exige atender também à pré-carga,
ao acoplamento e aos avisos de tensão.

A qualificação pré-layout extensa do B7 anterior não se transfere
automaticamente ao sizing atual de pré-carga/stack/saída. A matriz atual tem
somente 13 casos TT/SS; FF e o conjunto completo de históricos, slews e
perturbações ainda não foram qualificados com este PEX.

## Próximas ações propostas

1. Reexecutar casos específicos com o **PEX existente**, guardando waveforms:
   `slow_00_to_11` para estabilização/pré-carga e `tt_11_to_00` para o pico
   de tensão. Comparar 5 ps com um passo mais fino e registrar tolerâncias.
   Não aumentar apenas o timeout nem usar a interpolação como prova de margem.
2. Fazer comparações diagnósticas em decks descartáveis: PEX completo,
   mesma rede C com VSS resistivo colapsado, e mesma rede R sem os capacitores
   explícitos do extrator. Conservar modelos, dimensões, carga, estímulos e
   critérios. Essas versões artificiais servem para atribuir a regressão;
   nunca substituem o PEX completo na qualificação.
3. Se as comparações confirmarem o efeito de carga/acoplamento, compactar
   o placement por ramo e rotear localmente N0..N3, net1..net4 e as saídas
   DEC; revisar EVAL_GND e a proximidade das redes de endereço. Retestar
   avaliação e pré-carga antes de escolher novos W/L.
4. Depois de uma alteração física, repetir DRC/LVS e **fazer nova extração**.
   Essa etapa deve ser avisada previamente para execução na máquina adequada.
   A presente análise não exige outra extração.
5. Repetir a comparação completa com o novo PEX, ampliar a qualificação
   TT/SS/FF e fechar as margens de endereço/pré-carga. Um eventual orçamento
   diferente de 1 ns precisa de justificativa de temporização da macro e
   revisão; não transformar o atraso observado em um novo limite aprovado.

As waveforms `.raw` da campanha não estão versionadas. Esta análise não
reconstitui traços transitórios a partir dos CSVs nem atribui Fmax à SRAM.
Carga física de linha, buffers WL extraídos, controle de acesso válido,
registradores e geração física de PCLK continuam fora desta evidência.
