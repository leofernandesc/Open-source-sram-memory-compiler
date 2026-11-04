# Auditoria técnica da Fase 2 — 2026-11-04

**Parecer: APROVADO COM RESSALVAS**, para revisão da equipe e dos orientadores.
O protótipo físico 4×8 foi reproduzido e funciona nos experimentos TT declarados.
Foram encontrados e corrigidos defeitos relevantes de auditoria/empacotamento;
não foi demonstrado defeito funcional ou estrutural no GDS original. Este
parecer não encerra formalmente a fase nem qualifica fabricação ou frequência.

## 1. Escopo, método e preservação

Duas passagens: inspeção sem alterações da implementação e, depois, lapidação
controlada. O [diagnóstico inicial](phase2_review_20261104_initial.md) registra
os resultados negativos anteriores às correções. Foram examinados RTL, modelos,
testbenches, scripts Yosys/OpenROAD/Magic/Netgen/ngspice, referências SPICE,
GDS/LEF/DEF/MAG, manifestos e os dados brutos efetivamente disponíveis.

Nenhuma célula, seleção ou prova congelada da Fase 1 foi alterada. Não houve
commit, push, merge, PR, instalação, limpeza de dados, Monte Carlo, varredura
PVT, PEX RC ou início da Fase 3. A extração executada foi de conectividade e
geometria de junções, necessária ao LVS e à bancada transistor-level.

## 2. Git e referência inicial

Branch `integration/phase2-4x8`, HEAD
`3b0675b6fe42c79561be6e710e328ce95b8b6f81`; sem diferenças staged.
No início, `.gitignore` e `tools/sram-eda` tinham modificações e a entrega
Fase 2 estava untracked. Isso foi preservado, sem checkout destrutivo.
O [registro inicial](../reports/phase2/review_20261104/initial.json) contém
estado Git, diferenças e hashes de 233 arquivos; foram copiadas 58 fontes
antes das mudanças. Sua identidade é
`63e32296cdc2c2bd507acdba50af7da63b64e581d3ee43265eae65cf4ab272b8`.
As versões anteriores dos dois verificadores problemáticos foram retidas em
`reports/phase2/review_20261104/source_before/`, sem reconstrução de logs.

## 3. Arquitetura encontrada

`rtl/sram_controller.v:14` captura endereço, operação e dados de escrita na
subida. `rtl/sram_4x8_wrapper.v:28` captura a leitura na descida; sua saída
combina READ capturado e controles vivos. Somente `001` lê e `010` escreve.
Os seis outros controles capturados não acessam a memória. Desabilitar os
controles vivos após uma captura válida mascara DATA, sem cancelar o acesso.

Há 12 FF de requisição (2 endereço, 8 escrita, 2 operação) e 8 FF de saída.
Não há segunda captura na fronteira da macro nem latência adicional de ciclo.
Há oito tri-states HD reais. Os registradores não têm reset. Leituras de
posições não escritas são desconhecidas no modelo funcional e não recebem
expectativa de conteúdo conhecido nas simulações elétricas.

A referência lógica `row_decoder_2to4` não substitui a célula física. O
decoder selecionado tem 33 MOS: inclui complementos e buffers verdadeiros de
endereço, quatro caminhos dinâmicos, footer e quatro PMOS keepers. A ordem
formal congelada é `VDD PCLK A0 A1 DEC0 DEC1 DEC3 DEC2 VSS`; a conexão nominal
continua DEC0/1/2/3 → endereços 00/01/10/11. A montagem lê os pinos formais;
o LVS expandido e os acessos elétricos verificam o resultado.

## 4. Inventário e localização

| Fonte/artefato | Responsabilidade |
|---|---|
| `release/phase1_current.json` | Seleção imutável das seis famílias |
| `rtl/`, `tb/`, `synth/` | Contrato executável, referência independente e mapeamento |
| `physical/phase2/macro_binding.v` | Fases HD e ligação do núcleo; sem armazenamento comportamental |
| `tools/phase2_core.py`, `tools/run_phase2_fabric.py` | Montagem 4×8 e roteamento customizado |
| `tools/run_phase2_place.py`, `tools/finish_phase2_layout.py` | Integração HD, CTS, PDN e acabamento |
| `physical/phase2/experimental.sdc` | Clock experimental, sem IO/timing caracterizado |
| `physical/phase2/delivery.json` | Arquivos exatos da entrega e hashes |
| `physical/phase2/history/` | Índices anteriores e inventários legados explícitos |
| `reports/phase2/review_20261104/` | Evidências selecionadas desta revisão |

Os bancos ODB e transientes extensos ficam em `build/phase2/`, ignorado.
Isso não é dependência inicial da reprodução: o novo script reconstrói os
bancos. O transiente original completo também existe como gzip lossless
portável; o novo transiente dirigido permanece local, com hash e comando para
reprodução. Não foram acrescentados grandes dumps novos à entrega Git.

## 5. RTL, síntese e GLS

Nova síntese Yosys 0.44 com `sky130_fd_sc_hd__tt_025C_1v80.lib`. `tribuf` é
executado antes de `synth`; o techmap usa `sky130_fd_sc_hd__ebufn_1`, cujo
TE_B é ativo baixo. Há inversão explícita do enable. O piloto exercita 0/1/Z
em oito checks e sua inversão deliberada falha no scoreboard correto.

O wrapper mapeado mantém uma macro customizada, 20 FF e oito tri-states,
sem latches inesperados ou array de armazenamento convertido em FF. A
fronteira funcional e a física têm o mesmo contrato de requisições capturadas.
Na implementação física o núcleo é realmente expandido em MOS congelados.

Foram reproduzidos 15.619 checks/2.504 transações, 2.048 operações pseudoaleatórias,
todos os oito controles e suas 64 transições ordenadas. A GLS do netlist
roteado também passou. São execuções distintas da mesma cobertura, não
31.238 testes exclusivos. Usam modelos HD com alimentação explícita e atraso
zero, o scoreboard em `tb/sram_ref_model.sv` e substituto funcional de armazenamento.

Avisos Yosys foram inspecionados: o aviso de suporte limitado a tri-state
não é aceito como prova de mapeamento; o inventário e o piloto comprovam oito
ebufn reais. Expressões não suportadas de alguns FF de scan/enable da Liberty
referem-se a células não utilizadas; os FF selecionados são `dfxtp_1`.
Não se inferiu ausência de problemas somente por serem warnings.

A regressão RTL completa repetiu 154.303 checks (modelos 4/8/16/32, wrapper 4×8
e controlador). A consolidação passou em 117 métodos Python: 107 em tools e
10 de reconciliação. Existem testes de arquivos, modelos sintéticos, mocks,
invocações de CLI e testes reais Icarus; esses 117 não equivalem a 117 simulações
SPICE ou verificações físicas. DRC/LVS/síntese/GLS reais estão separados nas
evidências da [matriz](phase2_review_20261104_requirements.md).

## 6. Estrutura física e contagem independente

`tools/review_phase2_structure.py` não importa o grafo do gerador. Confere
aliases extraídos, terminais/modelos/bulks dos MOS de acesso e coordenadas
reais dos canais. Confirma 32 bitcells, quatro linhas fisicamente ordenadas,
oito colunas ordenadas, oito pares BL/BLB distintos, periféricos das colunas,
SA_OUT para o bit correspondente e Q do registrador para o tri-state correto.
Cada WL controla oito bitcells, portanto **16 gates de acesso**, não oito.

| Grupo | MOS |
|---|---:|
| 32 bitcells + decoder + 4 WL + 8 precharge + 8 write + 8 sense | 401 |
| 20 FF HD, 24 MOS/FF | 480 |
| Lógica HD de captura/feedback, inversão de clock e tri-state | 328 |
| Fases/adaptadores HD, incluindo 80 inversores de atraso | 266 |
| 3 buffers CTS HD, 6 MOS/buffer | 18 |
| Controle/adaptadores transistor-level customizados novos | 0 |
| 1.256 taps + 11.439 fillers | 0 MOS no SPICE desses masters |
| **Total extraído antes de redução** | **1.493** |

São 12.860 instâncias no top hierárquico; o núcleo customizado é uma delas,
contendo 61 instâncias de folhas. Instâncias físicas não são contagem de MOS.
Netgen reduz 34 dispositivos em paralelo e compara 1.459 dispositivos
equivalentes: HVT PMOS 550→529, NFET regular 679→666, PFET regular 184 e
special NFET 80 inalterados. Isso não elimina portas/bulks do teste.

## 7. Controle e simulações elétricas

A macro usa READ_Q/WRITE_Q como pedidos. Em `macro_binding.v:19–33`, os taps
24/40/60/80 separam liberação da pré-carga, escrita, avaliação e regeneração;
PCLK/WE respeitam CLK e validade. SCLK persiste após a descida para preservar
a captura. As wordlines são qualificadas com PCLK. Esses atrasos são uma
implementação experimental, não uma solução qualificada de todos os corners.

O modelo elétrico contém os 1.493 MOS do GDS, com as áreas/perímetros de
junção extraídos. Não há array comportamental, sense comportamental, reset,
`.ic`, `.nodeset` ou fonte ideal em nós internos. Fontes/chaves da bancada
representam alimentação, clock/controles e o mestre externo do barramento.

O experimento usa TT/1,8 V/27 °C, rampa de 1 ns, transições externas de 50 ps,
clock de 20 ns e duas capturas inativas iniciais. A primeira leitura não
escrita não afirma conteúdo zero. Isso demonstra a partida ensaiada, não
todos os estados iniciais ou a duração mínima de condicionamento.

**Campanha original:** 35 ciclos/710 ns, 128 bits lidos e 392 checks adicionais.
Os 392 são: três globais, 35 de WL na fase baixa, 35 de pré-carga pronta,
10 de WL inativa, 10 de fases inativas, 25 de linhas não selecionadas,
25 de seleção, 25 de exclusão escrita/sense, 128 de referência setup/hold
e 96 probes alto/baixo de barramento através de 1 kΩ.

**Campanha dirigida nova:** 41 ciclos/830 ns, **1.332 checks totais, incluindo
160 bits lidos**, sem falhas. Inclui 16 padrões walking-one/zero distribuídos
entre as quatro linhas, leituras após idle, mudança de endereço após captura,
mudança de DATA durante escrita habilitada no mestre, mascaramento vivo de
leitura capturada e restauração da saída após a captura na descida. Não testa
todos os padrões em todas as linhas nem substitui PVT/estatística.

São 160 checks de DATA lido, 160 de Q capturado, 160 de máscara viva,
288 de retenção do último Q, 128 de DIN capturado, 72 de endereço capturado
e 364 checks de protocolo/captura. Não se soma novamente o subconjunto de
160 leituras ao total 1.332.

BL/BLB foram observadas diretamente. O menor diferencial com sinal esperado
no início de SCLK (cruzamento de 20% de VDD) foi **1,753725363 V**. É medição
com interconexões ideais no TT, não diferencial mínimo exigido, margem contra
offset, garantia estatística ou resultado com todos os parasitas.

## 8. Caminho de captura e limites de temporização

SA_OUT e DOUT_RAW são o mesmo nó nesse binding; o mux de feedback precede D
do FF. Q registrado e DATA através do tri-state são observações diferentes.
O ensaio dirigido verifica ambas, inclusive Q preservado antes de uma nova
captura e DATA liberado durante mascaramento vivo.

Na análise bruta original, o menor intervalo de nível lógico válido antes da
captura local foi 7,438 ns em DOUT_RAW e 7,240 ns em FF_D. Na dirigida,
7,439 ns e 7,248 ns. O nível permaneceu válido por **pelo menos 2 ns** após
a captura: a observação foi limitada a essa janela, não se mediu hold mínimo.
Os CSVs contêm flags de limite inferior para bits que não comutaram.

A referência setup/hold é o máximo das tabelas TT/25 °C do `dfxtp_1`:
0,6206849 ns/0,1409486 ns. É um screen conservador de referência comparado
à simulação TT/27 °C, não caracterização formal de setup/hold nessa temperatura.
O clock externo e a chegada local são distinguídos nas medidas.

O SDC declara 20 ns e duty 50%; a origem periódica é arbitrária, enquanto a
bancada espera alimentação/condicionamento antes da primeira borda. Há um
orçamento aproximado de meio ciclo subida→descida. IO delays, uncertainty e
arcos/capacitâncias temporais da macro não foram caracterizados. Não existem
STA completo, SDF validado ou Fmax comprovada.

## 9. DRC, LVS, GDS e reprodução

Nova reimportação do GDS original: Magic 8.3.684, `sky130A.magicrc`, estilo
`drc(full)` e checagem euclidiana; zero violações. LVS com
`sky130A_setup.tcl`: correspondência única sem property errors, black box ou
placeholder funcional. Tolerância dimensional de 1% e redução de paralelos
do PDK estão explícitas; AD/AS/PD/PS são descartados no comparador, não na
simulação elétrica. A quantização de 0,975→0,98 µm do sense, já presente na
Fase 1, está dentro dessa tolerância e não foi modificada.

O top completo, em cópias, foi submetido a quatro defeitos reais: gate
desconectado, bulk incorreto, W+20% e L+20%. Todos rejeitados por diagnóstico
correspondente, mesmo quando Netgen retorna código zero. Alguns defeitos
terminam com `Top level cell failed pin matching` após o mismatch esperado;
o novo runner reconhece esse formato sem confundi-lo com falha de ferramenta.
As primeiras tentativas de classificação ficaram preservadas.

A reprodução completa partiu das fontes, gerou o núcleo, fez place/route,
acabamento, reimportação, DRC/LVS e GLS. O GDS canônico coincide com o
original após normalizar somente timestamps. O SPICE extraído, inclusive
geometrias de junção, é **idêntico byte a byte**. A reprodução não repetiu
SPICE desnecessariamente nem foi selecionada sobre a entrega original.

## 10. Falhas encontradas e correções

| ID | Severidade | Evidência inicial | Correção confirmada |
|---|---|---|---|
| R01 | P1 | `NaN` no CSV aceito | `phase2_evidence.py:20` exige finitude; negativo real rejeitado |
| R02 | P1 | Inventário vazio e netlist pós-run alterada aceitos | `audit_phase2.py:70` exige arquivos/probes/counters, reconcilia hashes pré-run, bancada, header e condição; dez negativos rejeitados |
| R03 | P1 | GDS adulterado fora do subcell empacotado | `phase2_evidence.py:62` e `package_phase2.py:48` vinculam payload ao selo; o mesmo GDS adulterado agora falha |
| R04 | P2 | Dependência de ODB ignorado e clock embutido | Reprodução de fontes executada; dependências explícitas, SDC experimental e artefatos públicos necessários ao acabamento |
| R05 | P2 | BL não observada; cobertura elétrica dirigida incompleta | Nova campanha de 1.332 checks e métricas de BL/BLB/captura |
| R06 | P2/P3 | Documentação corrente e inventário de ambiente defasados | README/interfaces/ambiente/execução corrigidos sem reescrever históricos |
| R07 | P2 preventivo | Output igual ao input podia invalidar o relatório antes da rejeição | Quatro entrypoints agora rejeitam antes de escrever; teste real de CLI preserva o hash do input |

Não foi encontrado P0 no circuito original. Os P1 de evidência estavam
presentes mesmo com o antigo PASS; por isso o aceite antigo não foi usado
como substituto da auditoria. Os inventários legados são registros datados
de revisão, não logs retroativamente atribuídos aos produtores.

## 11. Rastreabilidade e prontidão

O aceite revisado reconcilia dados brutos e sela os arquivos efetivos. Há
guardas contra entrada/artefato ausente, condição/probes incorretos, alteração
durante auditoria e reuso de payload diferente após o aceite. Hashes locais
não são assinatura contra um atacante que reescreva todos os registros.
O dump original lossless permanece portável; a análise adicional requer seu
raw local ou uma nova execução documentada, não apenas o CSV ilustrativo.

Fontes e layout não foram alterados para obter PASS mais fácil. As mudanças,
suas invalidações e os testes estão no [resumo de mudanças](phase2_review_20261104_changes.md).
O [quadro de aceite](phase2_review_20261104_acceptance.md) separa F2-DIG/F2-FIS.
Permanecem a aprovação da equipe, o contrato temporal público e as limitações
de caracterização/modelo já declaradas. Nenhuma afirmação de robustez completa,
yield, potência caracterizada ou confiabilidade de fabricação é feita.
