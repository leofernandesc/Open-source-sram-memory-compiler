# Ambiente de ferramentas SRAM / SKY130A

O checkout usa o container Docker `sram-xschem`, que monta a raiz deste
repositório em `/work`. O container já inclui SKY130A/open_pdks, Xschem, ngspice,
Magic, Netgen, Icarus Verilog, GTKWave, Python e gdstk. Alguns executáveis em
`/opt` não estavam no `PATH`, e executar um script Python diretamente no host
fazia seus subprocessos procurarem `xschem` no Ubuntu do host.

No checkout conferido em 2026-10-08, o container `sram-xschem` usa
`isaiassh/unic-cass-tools:1.1.0`, com este repositório montado em `/work`.
O `--check` confirma executáveis e arquivos SKY130A instalados; a tag sozinha
não comprova o conteúdo do PDK.

A imagem fornece Magic 8.3.613 no `PATH`. A extração detalhada do decoder
exige Magic 8.3.684; `tools/install_magic_8_3_684.sh` instala essa versão ao
lado da versão da imagem, sem reconstruir o PDK. O helper
`tools/extract_row_decoder.sh` seleciona explicitamente 8.3.684 e valida a
versão antes de iniciar o fluxo.

Use `tools/sram-eda` para executar comandos dentro do container com `PDK=sky130A`,
`PDK_ROOT=/opt/pdks` e o `PATH` corrigido. O lançador também confere se o
container está usando este checkout em `/work`.

## Checar o ambiente

Na raiz do repositório:

```bash
./tools/sram-eda --check
```

## Abrir ferramentas gráficas

```bash
./tools/sram-eda xschem cells/wordline_driver/wl_driver.sch
./tools/sram-eda magic -rcfile /opt/pdks/sky130A/libs.tech/magic/sky130A.magicrc
```

O mesmo lançador pode iniciar Magic ou GTKWave com os argumentos apropriados
para o layout ou waveform que será aberto. Ao iniciar Xschem, Magic ou GTKWave,
ele atualiza a montagem `/tmp/xauth` a partir do `XAUTHORITY` da sessão atual.
Isso evita usar um caminho Mutter/Xwayland temporário que ficou obsoleto quando
o container foi criado. O lançador só remove uma pasta de origem antiga se ela
estiver vazia e instala o cookie com permissões restritas ao usuário.

## Rodar scripts e simuladores

Execute o Python dentro do container para que scripts que chamam Xschem/ngspice
como subprocessos encontrem as ferramentas:

```bash
./tools/sram-eda python3 sims/run_leaf_peripheral_smoke.py \
  --blocks wl_driver \
  --corners tt \
  --vdd-values 1.8 \
  --temps-c 27 \
  --wl-cap-ff 17.4 50 \
  --output /tmp/wl_driver_smoke_tt.csv
```

Para uma sessão interativa já configurada:

```bash
./tools/sram-eda
```

Dentro dela, `xschem`, `ngspice`, `magic`, `netgen`, `iverilog`, `vvp`,
`gtkwave` e `python3` estarão no `PATH`; `PDK` e `PDK_ROOT` também estarão
definidos.

Scripts que chamam ferramentas externas devem ser iniciados pelo lançador (ou
dentro da sessão interativa), não com `python3` diretamente no host.
