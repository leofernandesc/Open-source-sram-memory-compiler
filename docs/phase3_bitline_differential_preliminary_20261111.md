# SRAM 4×8 com abutment — evolução preliminar de ΔV(BL–BLB)

Data: 11/11/2026. **Análise derivada de transientes existentes**, sem novas simulações.
Branch independente `analysis/phase3-bitline-differential-20261111`, baseada em `0cdd078`.

## Escopo e proveniência

- Fonte: `reports/phase1/sense_pex_small_signal_20261111/top_context_v1/top_edge_windows.npz`, que preserva todas as amostras nativas de nove janelas de leitura, de 0,3 ns antes até 0,7 ns depois de SCLK atingir 20%.
- Transientes: SRAM 4×8 com abutment; TT, 1,8 V, 27 °C; modelo transistor-level extraído com junções, **sem RC distribuído completo de interconexões/folhas**.
- Mapas de pinos BL/BLB/SCLK conferidos previamente em `top_context_v1/results.json`.
- Referência temporal deste levantamento: instante de cruzamento **80% de VDD pela WL selecionada**, em `reports/phase2/direct_abutment_20261111/audit_v1/timing.json`. Não é o início da borda de WL ou o cruzamento de 50%.
- Para cada operação e bit conhecido, medimos `ΔV_assinado = (BL−BLB) × (+1 se bit esperado 1, senão −1)`. Procuramos o primeiro cruzamento positivo de cada limiar, interpolando linearmente amostras adjacentes. Quando o primeiro ponto já supera o limiar, a observação é **censurada à esquerda** (não inventamos instante de cruzamento).
- **72 pares bitline/operação** = 9 leituras × 8 bits. Total de 432 registros de limiares.

## Tempos nominais observados

| | Cruzamento dentro da janela | Já acima no início da janela | Tempo do cruzamento relativo a WL80 |
|---|---:|---:|---:|
| 5 mV | 44/72 | 28/72 | −8,4 a −7,1 ps, apenas nos 44 cruzamentos observados |
| 10 mV | 44/72 | 28/72 | −7,5 a −6,1 ps, apenas nos 44 cruzamentos observados |
| 20 mV | 56/72 | 16/72 | −39,9 a −4,7 ps, apenas nos 56 cruzamentos observados |
| 50 mV | 72/72 | 0/72 | −7,1 a −0,5 ps |
| 100 mV | 72/72 | 0/72 | +3,5 a +5,2 ps |
| 200 mV | 72/72 | 0/72 | +14,6 a +20,4 ps |

Todos os limiares estavam superados até a ativação de SCLK no modelo observado. **Esses intervalos não equivalem a tempo de acesso garantido nem ao mínimo físico da bitcell.** A interpolação permite estimativas abaixo do passo entre amostras, mas não implica precisão metrológica em picossegundos.

As janelas registradas já começam com algum diferencial residual: em parte das leituras cerca de 19–22 mV em módulo. Por isso **5/10/20 mV não possuem tempos iniciais completos** e não se pode atribuir a geração de todo o diferencial à WL da nova leitura. Para resolver isso, é necessário o raw completo desde a pré-carga e o começo da ativação de WL.

### Relação com SCLK

- A WL selecionada chega a 80% aproximadamente **238,5–244,5 ps antes** de SCLK cruzar 20%.
- O diferencial assinado de 200 mV foi atingido em todas as observações **218,3–229,8 ps antes de SCLK20**.
- O diferencial assinado 50 ps antes de SCLK20 tinha mínimo de 1,571 V, conforme a qualificação anterior.

Isso **sugere**, mas **não comprova**, que SCLK pode ser antecipado. O circuito com SCLK adiantado ainda não foi simulado. Não mova apenas um marcador temporal nos transientes atuais para afirmar funcionamento: o sense altera as cargas e a evolução das bitlines ao ligar.

## Como reproduzir os cálculos

Novo analisador: `tools/analyze_phase3_bitline_differential.py` (somente leitura de dados existentes, geração de novos artefatos, sem ngspice).

Exemplo, em saída **nova**:

```sh
./tools/sram-eda python3 tools/analyze_phase3_bitline_differential.py \
  --output reports/phase3/bitline_differential_reproduced
```

Resultados calculados nesta análise: `reports/phase3/bitline_differential_20261111/threshold_crossings.csv` e `results.json`. O runner opcionalmente gera um gráfico com Matplotlib caso o pacote esteja instalado. A reprodução do gráfico no ambiente EDA não foi executada nesta análise.

## Próxima campanha necessária para caracterização completa

1. Utilizar o raw completo já preservado localmente, identificado no diagnóstico pelo SHA-256 `f5c19a6db9293edd792d73c4fe306c7782f9ad718fd66dfd0fa56872b75feb95`, ou regenerá-lo de forma rastreável.
2. Analisar cada bit desde antes da pré-carga/liberação de PRECH, a subida de WL (10/20/50/80%) e até SCLK, sem truncar a janela inicial. Relatar os diferenciais residuais anteriores à seleção, e distinguir o diferencial novo do já existente.
3. Repetir sob extração RC fisicamente apropriada ao candidato com abutment, preservando todas as folhas e ligações relevantes.
4. Executar uma varredura de ativação real de SCLK (por exemplo, deslocamentos de 0, −50, −100 e −150 ps como pontos **experimentais**, não recomendações de timing), com escrita/leitura, alternância de dados, comportamento do sense e estabilidade até a captura. Somente ampliar para antecipações maiores se os anteriores passarem.
5. Medir latência, consumo, corrente e margens; comparar TT/SS/FF e configurações maiores segundo o escopo da Fase 3. Se a temporização for alterada, revalidar as funções e invariantes de controle.

**Conclusão:** o 4×8 nominal tem desenvolvimento de diferencial muito rápido nos modelos atuais; a qualificação de antecipação de SCLK e dos tempos mínimos depende de simulação efetivamente retimada e caracterização RC/PVT. A limitação de 5 mV no sense PEX isolado não obriga redesenho com base nesses dados.
