# Fase 3 — comparação física das arquiteturas 4×8

Revisão de 25/11/2026. Dados verificados no snapshot histórico
`../phase3_evidence_20261124/` e nos replays locais de 247,5 ns.
Esta análise serve de entrada para a decisão de P3. A escolha e o aceite
da geometria definitiva permanecem abertos.

| Critério | v6 híbrida, 3 StrongARM | Candidata virtual, 8 StrongARM |
| --- | --- | --- |
| Lanes de sense | StrongARM nas colunas 3, 6, 7 e sense nativo nas outras cinco | StrongARM nas oito colunas, sendo cinco núcleos virtuais |
| Geometria física | GDS 540 × 380 µm, área de contorno 205.200 µm² | Nenhum GDS correspondente à topologia de oito núcleos |
| Vistas físicas | GDS, LEF, extração RC e correspondência LVS verificados historicamente | Binding SPICE com cinco núcleos e buffers adicionados sobre a RC da v6 |
| DRC e LVS | 0 erros DRC e `Circuits match uniquely` na evidência histórica | Ainda requer novo layout, DRC, LVS e PEX |
| C250 | PASS em TT, SS e FF na v6 física | PASS em TT, SS e FF na candidata virtual |
| Integrado 370 ns em 247,5 ns | Ainda sem validação integral na PEX da própria v6 com o protocolo atualizado | Função 18/18 por corner, 9 leituras × 8 bits, TT/SS/FF, três recibos `COMPLETED` |
| Ownership da candidata | Sem resultado final homologado sob 247,5 ns | TT c2 e FF c2/c10 inconclusivos nas lanes registradas em P2 |
| Timing, potência e SNM pós-layout | Pendente no domínio definitivo | Pendente, inclusive extração das cinco lanes físicas faltantes |

## Identidade e custo físico conhecido

O GDS da v6 tem SHA-256
`315c2ebceb2bc4cf258fa63be2279843805db3010637d0c273aea9db12813e37`,
o LEF tem
`39f09e853f89e7693523588c5c2d28fb217c8c9710fd18cd09b2bd813be0d5c7`
e a PEX tem
`a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f`.
Os três hashes foram recalculados diretamente nos arquivos do snapshot.
O GDS corresponde às três posições de StrongARM do arquivo
`strongarm_triple_20261122/physical/fabric_v6/placement.json`.

A comparação `physical/extracted_loads.json` registra capacitâncias explícitas
incidentes na rede. De referência nativa para v6, SCLK passou de
134,40188 fF para 151,20699 fF (+16,80511 fF, +12,504%) e PRECH de
107,16584 fF para 108,21869 fF (+1,05285 fF, +0,982%). Esses valores
excluem a capacitância interna MOS e não estimam as novas rotas da candidata
com oito StrongARM.

O gerador virtual insere cinco núcleos StrongARM de 11 MOS e dez buffers
de quatro MOS cada. O inventário do gerador registra diferença líquida de
+60 MOS após substituição dos elementos nativos. Essa estimativa é uma
contagem de dispositivos do modelo, não é uma medição de área, energia,
atraso ou carga física da ECO.

## Encaminhamento técnico

A v6 é a única variante com geometria verificável disponível. A candidata
de oito StrongARM tem evidência funcional integrada mais ampla no protocolo
atualizado. Para comparar desempenho e robustez, ambas precisam de resultados
funcionais e de ownership sob o mesmo estímulo e de valores elétricos
extraídos de suas respectivas geometrias.

O gate P3 requer decisão registrada de arquitetura e um conjunto coerente
de vistas físicas. Se a escolhida for a v6, P4 exige replays completos
na PEX v6 com o binding de três StrongARM. Se for a arquitetura de oito,
P3 exige implementar as cinco lanes restantes no GDS, distribuir SCLK,
alimentação e rotas, e obter DRC=0, LVS único e nova PEX assinada antes
de P4. O gate P2 continua aberto por 12 lanes sem witness bruto de condução.

Fontes locais de conferência.

- `../phase3_evidence_20261124/build/phase3/strongarm_triple_20261122/physical/macro_v6/`
- `../phase3_evidence_20261124/build/phase3/strongarm_triple_20261122/physical/fabric_v6/placement.json`
- `../phase3_evidence_20261124/build/phase3/strongarm_triple_20261122/physical/extracted_loads.json`
- `tools/phase3_prepare_virtual_eight_strongarm.py`
- `build/phase3/diagnostics/p2_review_matrix_20261125_v3.json`
