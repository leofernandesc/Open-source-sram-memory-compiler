# Validação manual de DRC e LVS — SRAM 6T / SKY130A

**Registro de 08/10/2026.** Este roteiro reproduz as verificações físicas da
bitcell e da coluna G7. Os resultados informados pelo operador e os logs
versionados são identificados separadamente; comandos sugeridos para uma nova
execução não representam verificações já realizadas.

## Ambiente e diretórios

Use o container de ferramentas SKY130A com o projeto montado em
`/home/designer/shared`. O nome do container pode variar; descubra-o no host
com `docker ps` e entre no container correspondente com `docker exec -it
<NOME_DO_CONTAINER> bash` (os comandos abaixo são executados **dentro** dele).

```bash
export PDK=sky130A
export PDK_ROOT=/opt/pdks
test -f "$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc"
cd /home/designer/shared
```

`%` é o prompt da **console Tcl do Magic**; `$` é o prompt do **shell Bash**.
Comandos `cd`, `magic` e `netgen` devem ser executados no Bash. Para evitar
problemas ao colar várias linhas no Tkcon, salve as instruções em um arquivo
`.tcl` e use `source /caminho/arquivo.tcl` na console Tcl. `Ctrl+V` pode não
colar nessa console; `@codex` ou `@codex` precedido de `%` não é um comando do
Magic. Não inclua o símbolo `%` ao digitar os comandos.

## 1. DRC da bitcell 6T no Magic

No Bash, dentro do container:

```bash
cd /home/designer/shared/layout/bitcell_6t
magic -rcfile "$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc" bitcell_6t_routed_hier.mag
```

Na console Tcl do Magic, execute as linhas abaixo **sem** o `%`:

```tcl
load bitcell_6t_routed_hier
drc euclidean on
drc style drc(full)
drc on
select top cell
expand
box select
drc check
drc catchup
drc count total
```

Antes de interpretar o resultado, confirme que a janela exibe a bitcell
`bitcell_6t_routed_hier`, com geometria carregada, hierarquia expandida e
seleção abrangendo a célula. Um DRC de célula vazia ou de uma caixa muito
pequena também poderia retornar zero. Para evitar colagem de múltiplas linhas,
é possível criar `/tmp/sram_bitcell_drc.tcl` com esse bloco e executar
`source /tmp/sram_bitcell_drc.tcl` no prompt Tcl.

**Resultado informado em 08/10/2026:** a console gráfica exibiu
`Total DRC errors found: 0`. A evidência veio da captura da execução manual
na conversa; não há um novo log dessa execução anexado ao repositório. Esse
resultado não substitui a verificação da seleção/cobertura geométrica.

## 2. DRC completo da coluna G7 — hierárquica e flat

No **Bash**, dentro do container:

```bash
cd /home/designer/shared/layout/column_32_full_g7_wpre2p52_final
magic -dnull -noconsole \
  -rcfile "$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc" \
  < audit_full_drc.tcl | tee /tmp/sram_g7_drc_manual.log
```

O script do repositório carrega separadamente
`column_32_full_g7_wpre2p52` e
`column_32_full_g7_wpre2p52_flat`, seleciona/expande cada célula e executa
`drc(full)`. O resultado **observado manualmente em 08/10/2026** foi:

```text
FULL_G7_DRC_column_32_full_g7_wpre2p52=0
FULL_G7_DRC_column_32_full_g7_wpre2p52_flat=0
```

Há também evidência reprodutível no repositório em
`layout/column_32_full_g7_wpre2p52_final/audit_full_drc_requal.log`, com os
mesmos resultados. Zero significa ausência de violações **nas regras e na
geometria examinadas**, não certificação de fabricação.

## 3. LVS da coluna G7 com Netgen

### 3.1. Primeira comparação manual (histórica, `/dev/null`)

No mesmo diretório, a primeira comparação manual foi:

```bash
netgen -batch lvs \
  "column_32_full_g7_wpre2p52_flat_extracted.spice column_32_full_g7_wpre2p52_flat" \
  "column_32_full_g7_reference.spice column_32_full_g7_wpre2p52_reference" \
  /dev/null \
  /tmp/sram_g7_lvs_manual.log
```

**Resultado observado em 08/10/2026:** ambos os lados apresentaram `212`
instâncias MOS (`136` NMOS, `76` PMOS) e `82` redes. O Netgen concluiu com
`Final result: Circuits match uniquely.`; a consulta do log temporário
confirmou essa linha. O repositório contém evidência correlata em
`layout/column_32_full_g7_wpre2p52_final/column_32_full_g7_requal_lvs.log`.

**Limite dessa comparação histórica:** `/dev/null` não carrega o setup de
LVS SKY130A. O Netgen criou *placeholders/black boxes* para subcircuitos MOS
indefinidos. Essa primeira conferência foi complementada pela execução abaixo.

### 3.2. Comparação manual confirmada com setup SKY130A

**Executado manualmente em 08/10/2026, dentro do container de ferramentas.**
O arquivo de setup existe no container em
`/opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl`. Esse caminho não
existe necessariamente no host WSL. O operador executou a comparação:

```bash
cd /home/designer/shared/layout/column_32_full_g7_wpre2p52_final
NETGEN_SETUP="$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl"
test -f "$NETGEN_SETUP" || { echo "Setup Netgen não encontrado: $NETGEN_SETUP"; exit 1; }
netgen -batch lvs \
  "column_32_full_g7_wpre2p52_flat_extracted.spice column_32_full_g7_wpre2p52_flat" \
  "column_32_full_g7_reference.spice column_32_full_g7_wpre2p52_reference" \
  "$NETGEN_SETUP" \
  /tmp/sram_g7_lvs_sky130_manual.log
grep 'Final result:' /tmp/sram_g7_lvs_sky130_manual.log
```

**Resultado apresentado pelo operador:** o Netgen imprimiu
`Reading setup file /opt/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl`,
contou `212` MOS (`136` NMOS e `76` PMOS) e `82` redes **em cada lado** e
concluiu:

```text
Final result: Circuits match uniquely.
```

O operador confirmou a mesma mensagem por `grep` e salvou uma cópia do log
completo no diretório compartilhado:

```bash
cp /tmp/sram_g7_lvs_sky130_manual.log \
  /home/designer/shared/layout/column_32_full_g7_wpre2p52_final/lvs_sky130_manual.log
```

**Localização da evidência:** no checkout do projeto, o arquivo está em
`layout/column_32_full_g7_wpre2p52_final/lvs_sky130_manual.log`. Ele existe
localmente, mas arquivos `*.log` são ignorados pelo Git; por isso, essa cópia
não constitui um artefato versionado. O resultado acima também foi apresentado
diretamente na saída de terminal do operador.

**Limite da comparação com setup SKY130A:** apesar de o Netgen ter lido o
setup, a saída continuou avisando `Call to undefined subcircuit` para
`sky130_fd_pr__nfet_01v8` e `sky130_fd_pr__pfet_01v8`, com criação de
*placeholders*. O log registrou células MOS como *black boxes* e a saída
mostrou avisos `No property ... found` para propriedades como `mult`, `nf`,
`area` e `perim`. Portanto, **o match estrutural com o setup carregado foi
confirmado**, mas essa execução não demonstra comparação completa dos modelos
primitivos ou de suas propriedades geométricas. Uma verificação com esses
avisos resolvidos exigiria evidência adicional.

## 4. Alcance do aceite

As observações manuais corroboram o DRC G7 hierárquico/flat e o LVS estrutural
com setup SKY130A carregado, registrados na Fase 1. O aceite de engenharia
da bitcell/leafs também depende
das extrações PEX e das matrizes elétricas já registradas em
[`phase1_leaf_cell_closure.md`](phase1_leaf_cell_closure.md). A verificação do
decoder **dinâmico** 2→4 e da macro 4×8 pertence à Fase 2: o candidato
`cells/row_decoder_2to4.spice` ainda não tem layout, DRC ou LVS próprios.
