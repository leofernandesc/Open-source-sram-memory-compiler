# P5 — cobertura nominal dos arcos tCLK_TO_DATA da v6

Data: 25/11/2026. A análise `tools/phase3_p5_tclk_arc_coverage.py` leu o piloto físico v6 `build/phase3/timing_v6_tclk_to_data.json`, verificou seus arquivos de entrada e preservou os eventos sem transição. Relatório derivado: `build/phase3/timing_v6_tclk_arc_coverage_20261125.json`, SHA-256 `a0184bcdf54b79c8b999dca9a9e3df0be94ffd136d12243b27590c1c4767121f`.

| Bit | Subidas medidas | Descidas medidas |
|---|---:|---:|
| DATA0 | 3 | 3 |
| DATA1 | 3 | 3 |
| DATA2 | 3 | 3 |
| DATA3 | 3 | 3 |
| DATA4 | 3 | 2 |
| DATA5 | 4 | 3 |
| DATA6 | 3 | 2 |
| DATA7 | 4 | 3 |

As contagens são iguais em TT, SS e FF: 16/16 combinações bit × polaridade têm pelo menos duas transições reais no ponto piloto de 1,8 V, 27 °C e 10 fF/lane. São 48 eventos medidos e 24 eventos sem comutação por corner. Cada evento sem comutação permanece `NOT_CHARACTERIZED` para atraso; a cobertura de um arco em outros ciclos não atribui valor a esse evento. O JSON contém mínimo, média, máximo e contagem por arco, além dos hashes das ondas, fixtures e observadores já preservados.

Isso elimina a lacuna de *exercitação nominal* por bit/polaridade do piloto tCLK_TO_DATA. Ainda faltam protocolo de caracterização aprovado, sweeps de slew/carga/PVT, limites por arco, transições dirigidas quando uma condição da grade não comutar, setup/hold e comparação Liberty contra SPICE. O estado permanece `PROVISIONAL` e `NOT_CHARACTERIZED` para qualificação elétrica.

Reprodução a partir da raiz do checkout:

```bash
python3 tools/phase3_p5_tclk_arc_coverage.py --output build/phase3/timing_v6_tclk_arc_coverage_<novo_id>.json
```
