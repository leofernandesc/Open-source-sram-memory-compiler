# P5 — piloto de energia da v6 física

Data: 25/11/2026. A integração numérica foi feita offline sobre os três waveforms físicos v6 de 370 ns em [`build/phase3/power_v6_247p5/`](../build/phase3/power_v6_247p5/), pelo `tools/phase3_power_integrated_pilot.py`.

## Método

Em cada ciclo completo de 20 ns, foi integrada a potência fornecida `−V(VDD) × I(VDD_SRC)`. Foram excluídos os dois ciclos de inicialização. Para cada corner foram usados nove ciclos de leitura e seis de escrita. A energia inclui clock, pré-carga e leakage, sem subtração de baseline. A carga e o estímulo são os do replay integrado de 247,5 ns. Cada relatório preserva o hash do recibo, da onda e da fixture de entrada.

## Resultados

| Corner | Leitura média (9 ciclos) | Faixa | Escrita média (6 ciclos) | Faixa |
|---|---:|---:|---:|---:|
| TT | 16,646 pJ/ciclo | 13,740–21,237 pJ | 11,060 pJ/ciclo | 10,329–11,968 pJ |
| SS | 15,000 pJ/ciclo | 13,147–17,433 pJ | 11,244 pJ/ciclo | 10,575–12,313 pJ |
| FF | 19,041 pJ/ciclo | 15,412–25,158 pJ | 11,050 pJ/ciclo | 10,301–11,970 pJ |

## Proveniência

| Corner | Hash do recibo do replay | Hash da waveform | Hash do relatório de energia |
|---|---|---|---|
| TT | `d1ae71d80766f328f76d104e473dd967e13a9f5f50185b387fa30b32daf3b13d` | `917ebc34decbbc893b5edceb1d2d8e494d2a0efd0978b305d4e7d50123f167` | `047fed7c484351dbb158e3d41b8e8db55600cd41f19644282f8fe70b7fdf881f` |
| SS | `37948fd77b2025a52a8970b815ec4245654f88ac1fb303b8844b34de31654cff` | `be6472e048f7765ea349fe5fcda3b60c984b6937e45a56d0bd682f3fd18cae54` | `0ddaa3fd044bfadd0ab9445b3a680218803fff9e0b2d3dabbe5c035cee56669b` |
| FF | `6e4d2c926b986b783a445b0cce6f9ae8aa9a93d309514e99ea29f1ed1a62f26d` | `3c79a30a14555ab0c0fa62204fb4d39ea15568d342d20cd5a2add252d8aa59c0` | `e789716bf2b2628efbf4553beeca2df123409f7467944c714d1187e8bdf96df0` |

Os três resultados estão marcados `PROVISIONAL` e `electrical_qualification=NOT_CHARACTERIZED`. Eles não medem `P_STATIC`, `P_IDLE` qualificada, energia sem leakage, nem tabelas de potência Liberty. O evento c12 não serve como amostra de `P_IDLE`: a sonda fraca usada na medição de liberação fica habilitada até 266,5 ns, atravessando o ciclo idle iniciado em 247,5 ns. O próximo piloto de potência idle precisa de uma execução sem essa sonda, com clock ativo e estado conhecido; `P_STATIC` requer outra janela com clock parado. O piloto também não determina setup/hold, limites de slew/carga ou SNM pós-layout.

## Próximas medidas P5

1. Congelar domínio PVT, VDD, temperatura, slew, cargas, período e tolerâncias na PEX v6 aceita em P4.
2. Medir `P_STATIC` com clock parado e `P_IDLE` com clock ativo, estado armazenado e janelas explicitados.
3. Medir `tACCESS`, `tCLK_TO_DATA`, `tDIS` e setup/hold por arco, bit e polaridade, preservando medidas ausentes quando não há transição.
4. Caracterizar SNM Hold/Read no escopo físico exigido, com método, processo, seeds e estatística homologados.
5. Gerar Liberty a partir das medições aprovadas e validar sintaxe, arcos, unidades, tabelas e pontos contra SPICE.

