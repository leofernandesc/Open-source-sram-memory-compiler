# Fase 2 — estado da rodada complementar

## Referência e resultado

Estado encontrado: branch `integration/phase2-4x8`, árvore limpa e HEAD
`4ffbbf571bdff1c995de5bd2815083b3a0eda3d0`. GitHub confirmou PR #7 aberto
sobre `develop`; PR #8 aberto em Draft sobre `integration/phase1-six-cells`.
Esses metadados e 260 hashes iniciais estão em
[`initial.json`](../reports/phase2/extension_20261104/initial.json).
A ordem de integração permanece PR7 → PR8; nenhuma branch protegida foi alterada.

**Parecer: pronta para revisão, com as ressalvas experimentais anteriores.**
Não foi demonstrado defeito funcional da SRAM nesta rodada. Não representa
aprovação formal da equipe ou dos orientadores. F2-DIG conserva aceite
funcional; F2-FIS conserva aceite experimental TT/1,8 V/27 °C, sem wire RC.

| Frente | Resultado desta rodada | Evidência |
|---|---|---|
| Cobertura | Duas lacunas específicas identificadas e exercitadas | [Matriz](phase2_coverage_extension.md) |
| C1 | PASS 1.150 checks incluindo 72 bits lidos | `c1_sequences/results.json` |
| C2 | PASS 1.281 checks incluindo 48 bits lidos | `c2_bus/results.json` |
| Piloto C1 | PASS 309 checks; subconjunto de C1 | `c1_pilot/results.json` |
| Temporização | 820 screens adicionais e eventos nominais medidos | [Relatório](phase2_timing_extension.md) |
| Estrutura | 1.493 MOS preservados e segunda passagem terminal/CMOS | `structure_corrected/results.json` |
| Observadores | 15 testes novos; 63 relevantes no conjunto | `regression_tests.txt` |
| Evidência | Oito adulterações rejeitadas em cópias | `tampering/results.json` |
| Reprodução anterior | Worktree limpo + sete raws restaurados; auditorias aprovadas | `clean_reproduction/results.json` |
| Apresentação | Revisão incremental dos mesmos 22 slides | [PPTX/PDF e roteiro](../presentations/phase2/extension_20261104/README.md) |

Os caminhos abreviados acima ficam em
[`reports/phase2/extension_20261104/`](../reports/phase2/extension_20261104/).
Não agregamos piloto, reanálises e bits novamente aos totais das campanhas.
Os 1.332 checks dirigidos e 3.383 da partida anteriores são preservados,
não substituídos pelos novos. Não foi repetido place-and-route, DRC/LVS ou
extração: a geometria e o circuito selecionados são as mesmas entradas seladas.

## Rastreabilidade e limites

Os relatórios anteriores descrevem o estado técnico de suas respectivas
rodadas. Frases históricas como "publicação pendente" não foram reescritas:
o commit 4ffbbf5 e PR8 já existiam no início deste trabalho. Esta nota e o
histórico dos commits complementares registram o estado mais recente.
Os manifestos de `release/phase2_experimental/` não foram regenerados para
incluir esta rodada. A extensão possui inventário e provas próprios.

Foram preservados dois resultados negativos de **observadores**, não do DUT:
a suposição inicial de enable único e uma janela de DATA inadequada para a
campanha antiga que retira o enable vivo. Causas e versões estão nos relatórios
de cobertura/tempo. Falhas iniciais de montagem do worktree no container e
ausência de raws também permanecem registradas. Não foram promovidas a PASS
sem executar novamente o procedimento correspondente.

O piso de corrente é diagnóstico. Não foram caracterizados tEN/tDIS máximos,
turnaround, setup/hold externos, frequência máxima, RC de fios, PVT, potência,
yield, estatística de partida ou fabricação. Os taps permanecem 24/40/60/80.
Os itens para revisão humana permanecem **PENDENTES**, no
[checklist da equipe](phase2_team_review_checklist.md).

## Reprodução leve

Usar o ambiente do [guia original](phase2_reproduction_guide.md). Executar na
raiz do projeto; os comandos seguintes não lançam nova simulação elétrica:

```sh
./tools/sram-eda python3 -m unittest discover -s tools/tests -p 'test_phase2_*.py' -v
./tools/sram-eda python3 tools/review_phase2_extension_structure.py --output reports/phase2/local/extension_structure_reproduced
./tools/sram-eda python3 tools/verify_phase2_extension.py --sources reports/phase2/extension_20261104/c1_pilot reports/phase2/extension_20261104/c1_sequences reports/phase2/extension_20261104/c2_bus --output reports/phase2/local/extension_raw_reproduced
./tools/sram-eda python3 tools/analyze_phase2_extension_timing.py --sources reports/phase2/extension_20261104/c1_sequences reports/phase2/extension_20261104/c2_bus --output reports/phase2/local/extension_timing_reproduced
```

Os verificadores de raw exigem os transientes completos. O pacote anterior
continua no formato descrito pelo guia original. A extensão usa **o mesmo
formato lossless e o mesmo verificador por whitelist**, sem extrair nomes
arbitrários de um tar. Os três novos raws têm índice, hash e destinos em
[`raw_bundle.json`](../reports/phase2/extension_20261104/raw_bundle.json).
O pacote é local/opcional, não foi hospedado no GitHub. Para transportá-lo,
solicitar ao responsável o arquivo de hash indicado e usar:

```sh
./tools/sram-eda python3 tools/bundle_phase2_extension_raw.py --verify /path/mounted/in/container/raw_extension_20261104.tar.gz
./tools/sram-eda python3 tools/bundle_phase2_extension_raw.py --restore /path/mounted/in/container/raw_extension_20261104.tar.gz
```

Não se sobrescreve raw conflitante. Restauração usa somente destinos esperados
sob `build/phase2`. Sem pacote, os dados podem ser **regenerados** em pastas
novas pelos comandos abaixo; isso gera novos receipts e não autoriza trocar
hashes históricos ou afirmar identidade bit a bit entre versões de ferramenta.

## Regeneração elétrica, separada da auditoria

Conferir RAM, swap e disco antes de executar. As campanhas foram sequenciais,
com uma thread ngspice/OMP/BLAS, timeout de 2.400 s por processo, sem construir
layout. O runner verifica os modelos da PDK e os hashes do DUT selado antes
e depois. Os limites mínimos de preflight são 1 GiB de RAM disponível e
512 MiB de disco; prever folga adicional para os raws. Não remover caches
ou dados anteriores para satisfazê-los.

```sh
./tools/sram-eda python3 tools/run_phase2_extension.py --campaign sequences --pilot --output reports/phase2/local/c1_pilot_reproduced
./tools/sram-eda python3 tools/run_phase2_extension.py --campaign sequences --output reports/phase2/local/c1_reproduced
./tools/sram-eda python3 tools/run_phase2_extension.py --campaign bus --output reports/phase2/local/c2_reproduced
```

Cada comando exige diretório inexistente. Timeout/recurso insuficiente tem
classificação separada; saída incompleta não produz PASS elétrico. .ic/nodeset
não são usados. A partida mantém rampa de 1 ns e dois ciclos inativos nesta
rodada, sem repetir os cinco ensaios históricos ou procurar um mínimo.

## Alcance do checkout limpo

Foi criado worktree destacado de 4ffbbf5, com 13.491 arquivos rastreados. A
primeira montagem encontrou o `.git` apontando para metadados absolutos do
host. Um container novo, com o worktree em `/work` e esse diretório de
metadados montado somente para leitura, resolveu a identificação do Git.
A imagem existente foi reutilizada sem downloads; PATH e PDK foram definidos
explicitamente para SKY130A.

Após criar o diretório de cache exigido pelo auditor antigo, a ausência de
raws foi corretamente classificada como incompleta. O bundle anterior foi
restaurado num cache antes vazio; a auditoria elétrica anterior e os 3.383
checks de partida passaram. Os 48 testes Python anteriores também passaram.
Esse resultado demonstra **reanálise da entrega publicada** na mesma imagem
Linux/PDK. Não demonstra regeneração integral do SPICE num clone, execução
Windows, outro PDK ou simulações novas sem acesso a seus raws.

Em seguida, o mesmo worktree foi avançado, sem alterações locais, ao commit
`2397898` desta extensão. Um novo container restaurou os três raws complementares
num cache onde eles ainda não existiam. A reanálise C1/piloto/C2, os 820 screens
temporais e os 63 testes Python passaram. Os quatro CSV/JSON de medição
(`phase.csv`, `capture.csv`, `bus.csv`, `checks.json`) reproduziram exatamente
os arquivos selecionados. O worktree permaneceu sem alterações rastreadas.
Ver [`clean_extension/results.json`](../reports/phase2/extension_20261104/clean_extension/results.json).
Continua sendo reprodução da análise, não novas simulações do DUT.
