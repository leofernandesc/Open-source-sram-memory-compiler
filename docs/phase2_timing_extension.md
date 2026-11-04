# Fase 2 — análise temporal complementar

## Escopo e método

Circuito: top extraído selecionado de 1.493 MOS, sem mudança de topologia,
dimensões, junções, registradores ou taps 24/40/60/80. TT, VDD=1,8 V, 27 °C;
clock de 20 ns, alto/baixo de 10 ns; rampas de estímulo de 50 ps. Conectividade
e junções extraídas, **sem RC detalhado das interconexões**. ngspice 44.2,
Gear, KLU, reltol=1e-4 e passo máximo de 10 ps. Uma simulação por vez.

As medidas provêm dos raws completos, identificados por SHA-256, não dos
CSVs ilustrativos. O
[analisador](../tools/analyze_phase2_extension_timing.py) exige transiente
completo, valores finitos, tempo crescente e eventos únicos nas janelas
declaradas. Cruza 50% para clock/CSb, 80% para PRECH desligado/WL válida e
20% para início WE/SCLK ou liberação de WL/WE. Interpola cruzamentos entre
amostras; o início de validade do dado é a primeira amostra válida após a
última inválida. Apresentamos aproximadamente três algarismos significativos:
as muitas casas dos CSVs não são precisão física nem estudo de convergência.

Baixo válido: −0,18..0,36 V; alto: 1,44..1,98 V. Dados já válidos no início
da janela recebem flag; nesse caso a janela disponível é um **limite
inferior**, não o instante de resolução. Não medimos propagação de um bit
que não mudou nem atribuímos atraso zero a ele. A primeira leitura tem
registro anterior desconhecido e não integra a medida FF_Q/DATA de mudança.

Referências de CLK: a queda pública a 50% ocorre 25 ps após o início da PWL.
O clock local do FF positivo, após inversão/CTS, é medido separadamente.
SA_OUT e RAW são o mesmo nó neste binding; FF_D inclui mux, FF_Q inclui
captura e DATA inclui ebufn/enable. Não são quatro nomes para um único atraso.

## Comparação quantitativa

| Relação / unidade | Cinco partidas anteriores, reanalisadas | C1/C2 novos | Interpretação |
|---|---:|---:|---|
| PRECH80↑ → WE20↑ / ps | 211,7..213,3 | 211,3..212,9 | Guarda positiva nos writes ensaiados |
| WL80↑ → SCLK20↑ / ps | 237,6..243,7 | 238,5..243,9 | Ordem de ativação nominal |
| WL20↓ → PRECH80↓ / ns | 2,1969..2,1982 | 2,1962..2,1978 | Recuperação antes da pré-carga |
| WE20↓ → PRECH80↓ / ns | 2,2904..2,2908 | 2,2904..2,2908 | Escrita termina antes da pré-carga |
| RAW válido antes do clock local / ns | mínimo 7,4380 | mínimo 7,4346 | Janela disponível, não setup requerido |
| FF_D válido antes do clock local / ns | mínimo 7,2422 | mínimo 7,2402 | Inclui caminho do mux |
| Clock público50↓ → clock local50↑ / ns | Medido por bit nos novos CSVs | 0,230..0,247 | Atraso local, não outro ciclo |
| Clock local50↑ → FF_Q válido / ns | 0,190..0,223 | 0,190..0,223 | Somente mudanças reais conhecidas |
| Clock público50↓ → novo DATA válido / ns | 0,489..0,554 nas partidas | 0,489..0,549 | Enable já ativo; carga da bancada |

Fontes atuais:
[`timing_selected/results.json`](../reports/phase2/extension_20261104/timing_selected/results.json),
[`phase.csv`](../reports/phase2/extension_20261104/timing_selected/phase.csv),
[`capture.csv`](../reports/phase2/extension_20261104/timing_selected/capture.csv)
e [`bus.csv`](../reports/phase2/extension_20261104/timing_selected/bus.csv).
Cada linha indica campanha, ciclo, operação/linha ou bit; os extremos
registram os casos completos, usando mínimo para guardas e máximo para atrasos.
A reanálise das partidas anteriores está em
[`timing_original_startup/`](../reports/phase2/extension_20261104/timing_original_startup/).

As diferenças de décimos de ps entre ensaios não demonstram uma nova margem
física: dependem de estado, alinhamento da malha e interpolação. A conclusão
sustentada é que a ordem das fases permaneceu correta nestes estímulos.
Foram examinados 29 acessos válidos novos e 120 bits lidos em C1/C2.
Os 820 screens adicionais incluem recuperação antes de cada acesso e
estabilidade de RAW/FF_D por 2 ns após captura; não são novas transações.

### Antes do sense

Nos oito pares por leitura, o menor diferencial **com sinal esperado** foi
aproximadamente 1,571 V 50 ps antes de SCLK cruzar 20%, e 1,737 V nesse
cruzamento. Essas medidas pertencem ao modelo sem RC de fios e aos estados
escritos. Não são offset mínimo, sensibilidade, read-SNM, imunidade a ruído
ou margem estatística do SA. O valor no cruzamento já pode conter efeitos
do início da condução/regeneração; por isso também registramos a observação
50 ps anterior e mostramos o traço real.

### Referência de captura

As janelas originais foram reconfirmadas na reanálise interna: RAW mínimo
~7,438 ns; FF_D ~7,240 ns. A referência `dfxtp_1` da Liberty usa 1 ns como
unidade, TT/1,8 V/**25 °C**, setup máximo 0,6206849 ns e hold máximo
0,1409486 ns; o SPICE está a **27 °C**. As janelas excedem essa referência
nos ensaios, mas a comparação não é STA qualificado nem setup/hold público
da SRAM. Os ≥2 ns posteriores são limite da observação, não hold mínimo.
Ver [contrato](../specs/sram_4x8_timing_contract.md) e
[unidades](../reports/phase2/final_polish_20261104/reference_units.json).

## Barramento: calibração e handoff

Medidores externos de 0 V preservam a resistência dos switches de bancada:
1 Ω para mestre, 1 kΩ para probe, roff=1e12 Ω. Não há capacitor de carga
externo adicionado em DATA; a carga vem das conexões/junções/modelos presentes
e desses caminhos externos. É uma condição de carga específica, não um load
comercial caracterizado. A unidade de corrente foi conferida antes de C2
com divisor resistivo e fonte de 0 V, separado da SRAM.

| Observação C2 | Intervalo nominal | Referência e limite |
|---|---:|---|
| Desativação por máscara viva | 0,133..0,184 ns | CSb50↑ → corrente do probe ≤50 µA, permanecendo abaixo |
| Reativação por máscara viva | 0,629..0,632 ns | CSb50↓ → corrente do probe >50 µA, permanecendo acima |
| Liberação antes do mestre, guarda de estímulo 0,3 ns | cerca de 0,126 ns | TE_B80↑ → HOST_EN20↑ nos oito bits |
| Liberação antes do mestre, guarda de estímulo 0,6 ns | cerca de 0,426 ns | Mesma referência; não turnaround mínimo |

Esses tempos são **cruzamentos de corrente instrumental**, não limites
qualificados `tDATA_DISABLE`/`tDATA_ENABLE`. Sob a carga oposta de 1 kΩ,
DATA pode deixar de ser nível lógico válido mesmo com ebufn habilitado:
a calibração exige corrente observável e FF_Q preservado, não capacidade
de dirigir 1 kΩ contra outro driver. As leituras normais são verificadas
fora desse intervalo. Após máscara, corrente e tensão próximas do probe
são exigidas em conjunto; tensão de nó flutuante sozinha não prova Z.

No handoff forte não houve amostra com HOST_EN>20% e TE_B<80%, nem corrente
estacionária acima do piso declarado. Não se infere ausência absoluta de
qualquer corrente, resposta entre amostras, pior caso PVT ou guarda zero.

## Contextos históricos e análises rejeitadas

O piloto inicial tinha guarda WE/PRECH de **−232,897 ps** e foi rejeitado.
O piloto com tap40 teve **+167,388 ps**. O top final anterior teve cerca de
**+212 ps**, reproduzido nos testes novos. São três contextos distintos;
não os agrupamos como uma distribuição da macro final. Fonte:
[`phase_guard_review/results.json`](../reports/phase2/phase_guard_review/results.json).

A tentativa inicial de aplicar também a janela DATA até queda+1,25 ns à
campanha dirigida antiga foi rejeitada pelo analisador
([recibo](../reports/phase2/extension_20261104/timing_original_access/results.json)).
Naquela bancada os controles vivos são retirados na fase alta e restaurados
somente em subida+11 ns, isto é, **queda+1 ns**. No caso examinado, DATA0
ainda estava em ~2,004 V em queda+1,25 ns; esse ponto não era o sample de
readback previsto, que ocorre em queda+2 ns. Portanto não se pode interpretar
essa janela nova como atraso do caminho com saída previamente habilitada.

Preservamos a análise rejeitada e sua fonte. Reexecutamos explicitamente
**somente medidas internas** nessa bancada, excluindo disponibilidade DATA
([`timing_original_internal/`](../reports/phase2/extension_20261104/timing_original_internal/)).
Os checks elétricos originais permaneceram aprovados pela auditoria dos
raws no checkout limpo. Nenhum critério funcional foi reduzido e nenhum
PASS histórico foi reescrito para acomodar a diferença de bancada.

## Gráficos e reprodução

- [Sequências e armazenamento C1](../reports/phase2/extension_20261104/figures_revised/consecutive_access.png).
- [Liberação PRECH/WE C1](../reports/phase2/extension_20261104/figures_revised/write_guard.png).
- [Caminho de leitura C2](../reports/phase2/extension_20261104/figures_revised/read_path.png).
- [Máscara e corrente C2](../reports/phase2/extension_20261104/figures_revised/bus_mask_current.png).
- [Clock local, FF_Q e DATA C2](../reports/phase2/extension_20261104/figures_revised/capture_to_data.png).

Os PNGs são gerados de dados completos; `figures_revised/sources.json` fornece origem,
janela, colunas, escala e hashes. A corrente usa escala symlog (região linear ±30 µA) para mostrar simultaneamente o pico de conexão e os níveis estacionários; as amostras não foram alteradas. Exemplos e restauração dos raws estão no
[índice da rodada](phase2_extension_state_20261104.md).

O contrato público mantém os parâmetros externos pendentes. Esta extensão
acrescenta medidas nominais, não Fmax, especificação de turnaround, PVT,
RC detalhado, estatística de partida ou qualificação de fabricação.
