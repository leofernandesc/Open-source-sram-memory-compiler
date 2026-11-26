# P5 — ensaios exploratórios de potência idle e estática na v6

Data: 25/11/2026. Estes ensaios continuam o plano de fechamento da Fase 3. A identidade física permanece PEX SHA-256 `a1e812f717b91089596a10380eb14b53991678513d6db795e28383d02912474f`, GDS registrado no preflight P4 e binding SHA-256 `3b6f7205476b79d02754ba081a7d2eb2ef9d372670daf26067d3d0cb5745e76d`. O domínio 1,8 V, 27 °C, período 20 ns e carga 10 fF/lane continua piloto, pendente de aprovação da equipe.

## Preparação

O gerador `tools/phase3_p5_power_quiet.py` deriva cada deck de `build/phase3/integrated_v6_idle_247p5/{TT,SS,FF}/`, verifica os hashes das entradas e copia os mesmos `binding.spice`, `fabric.spice` e 319 hashes de modelos. Não altera o PEX nem os replays P4. Os ciclos de escrita anteriores ao instante 241,5 ns estabelecem um estado conhecido, conforme a função validada em P4. A partir de 241,5 ns, a sonda fraca externa é desligada antes do ciclo idle. Após 247,55 ns, os controles e dados externos permanecem fixos: CSb/OEb/WEb em 1,8 V, host forte e fraco desabilitados. O deck idle conserva CLK ativo; o deck static mantém CLK em 0 V após 260,05 ns. Ambos terminam em 300 ns.

`P_IDLE` integra `−V(VDD)·I(VDD_SRC)` de 270 a 290 ns, um ciclo de 20 ns estabilizado. `P_STATIC` usa a mesma integral de 280 a 295 ns, com CLK parado. As bordas são interpoladas entre amostras nativas adjacentes; a média é a energia da janela dividida por seus exatos 20 ou 15 ns. O integrador usa trapézios. O relatório inclui faixa dos controles, CLK e VDD, número de amostras e hashes de deck, PEX, modelos, log e onda. Host e sondas têm fontes separadas e não entram em `I(VDD_SRC)`; os periféricos internos da macro entram. A potência idle inclui a atividade de clock e dos circuitos internos. Não se subtrai baseline ou leakage.

O ensaio inicial TT com janela curta de 255–265 ns foi interrompido após 56 s, retorno −15 e sem onda. Ele permanece em `build/phase3/p5_power_quiet_v6_20261125/idle/TT/` como diagnóstico inconclusivo. A campanha válida para análise usa `build/phase3/p5_power_quiet_v6_fullcycle_20261125/`.

Comando a partir da raiz `projeto-sram` para executar um deck já preparado:

```bash
./tools/sram-eda python3 /work/tools/phase3_p5_power_quiet.py idle SS --threads 8 --run-prepared
```

Para criar uma variante ainda inexistente, usar a mesma CLI com `--prepare-only` antes. Os diretórios preparados existentes recusam nova preparação. O runner confere os 319 modelos e os hashes das entradas, registra o hash do simulador e preserva o recibo antes de publicar a medição. Só executar um transiente físico por vez nesta máquina: o TT com uma thread usou cerca de 1,64 GiB de RSS, enquanto a memória disponível para novos processos estava em torno de 1,6 GiB.

O integrador foi exercitado com ondas sintéticas de corrente constante de −1 mA, VDD=1,8 V e amostras que cruzam as bordas das duas janelas. Recuperou 1,8 mW e durações de 20/15 ns. Este check valida aritmética e parsing, sem substituir o resultado SPICE.

## Resultados e limites

Recibos por corner e modo ficam em `build/phase3/p5_power_quiet_v6_fullcycle_20261125/{idle,static}/{TT,SS,FF}/receipt.json`. O ensaio com oito threads tem o subdiretório `threads8/` antes do modo.

| Corner | Modo | Janela | Média | Estado |
|---|---|---:|---:|---|
| TT | idle, CLK ativo | 270–290 ns | **139,866 µW** | `PROVISIONAL`; retorno 0, onda 300 ns, 319 modelos, 1.164 amostras nativas na janela |
| TT | static, CLK parado | 280–295 ns | **0,21446 µW** | `PROVISIONAL`; retorno 0, onda 300 ns, 319 modelos, 600 amostras nativas na janela |
| SS | idle, CLK ativo | 270–290 ns | **141,944 µW** | `PROVISIONAL`; retorno 0, onda 300 ns, 319 modelos, 1.051 amostras nativas na janela |
| SS | static, CLK parado | 280–295 ns | — | Em execução |
| FF | idle e static | — | — | Decks preparados; aguardam a fila |

TT idle levou 1.552,74 s com uma thread. A análise independente tem SHA-256 `a79d98baddd4fd860bb98bfee790d4fe9dde69d6c5b1114bfee9d72be61214be` e lê o recibo `2d6f9f899ddc225402ace1e11486d0b58335c83ee618e9202fb5ed1854f8a708` e a onda `79900ee9aff019c1de0c3194593d6545a47b6c0815a16fb170ffbe0069d71e69`. Na janela, CSb/OEb/WEb = 1,8 V, host forte e fraco = 0 V, CLK alterna entre 0 e 1,8 V e VDD = 1,8 V. A potência instantânea pode ser negativa durante devolução momentânea de carga; a média integrada é positiva. O script de análise foi aperfeiçoado durante a simulação para interpolar as bordas exatas; `analysis.json` preserva a análise final e referencia o recibo e a onda brutos.

TT static levou 1.354,74 s com oito threads, pico de RSS do processo filho de 1.644.992 KiB. O recibo tem SHA-256 `4e9ad42f606d09462a7a2f5f1bc98bb5ba80e276ed91819a65a497bcf1414fa0` e a onda `313e719273bc970c9ef236edde537605df7ab7afa647877b2b2aa47ac9fcbc94`. O integrador independente reproduziu exatamente o resultado do recibo. CLK=0 V, CSb/OEb/WEb=1,8 V, host forte/fraco=0 V e VDD=1,8 V durante toda a janela. O tempo foi menor que o TT idle de uma thread, mas os estímulos diferem após 260 ns; essa comparação não isola o efeito do número de threads.

SS idle levou 1.396,30 s com oito threads, pico de RSS de 1.647.768 KiB. A onda tem SHA-256 `a369516cf10630db34a41c88470a5d87fb8f6262885bab48a1c3f9e30ea75881`, o log `a12c4b04b4483d549d2f98fddda308b4d0ac605c44a52e58c310fef08a1e86b8` e o recibo `threads8/idle/SS/receipt.json`. Na janela: CSb/OEb/WEb e VDD a 1,8 V, host forte/fraco desligados, CLK alternando. Não houve erros; retorno 0, todas as entradas foram preservadas e 319 modelos conferidos.

Os ensaios são `PROVISIONAL`. Como a sonda está desligada, o próprio deck de potência não mede impedância do barramento; a liberação foi verificada separadamente no P4 sob outro estímulo. Falta revisão da equivalência elétrica desse desligamento e do estado armazenado na janela. Estes valores não qualificam P5 nem substituem aprovação de domínio PVT, sweeps de carga/slew, timing por arco, setup/hold, SNM pós-layout ou Liberty.
