# Experimento Monte Carlo - Inversor CMOS SKY130A

## Configuração do Monte Carlo
1. **Biblioteca e Compatibilidade:** Utilizou-se o modelo contínuo do PDK (`combined/continuous/sky130.lib.spice`) com `.options ngbehavior=ps`, seguindo o padrão validado nas simulações do projeto.
2. **Habilitação das Variações Estatísticas:** Carregou-se o corner `.lib ".../sky130.lib.spice" mc` e definiu-se explicitamente `.param mc_pr_switch=1` e `.param mc_mm_switch=1`, ativando simultaneamente a variação global de processo (*process*) e o descasamento local (*mismatch*) entre os transistores PMOS e NMOS.
3. **Amostragem Independente e Medição:** O script `run_mc.py` executou 10 chamadas independentes do simulador (`ngspice -b`), garantindo que o gerador gaussiano interno (`agauss`) sorteasse novos parâmetros em cada rodada. Em cada amostra, realizou-se uma varredura DC (`0 V` a `1.8 V`, passo de `1 mV`) e extraiu-se a tensão de chaveamento `Vm` no ponto onde `V(out) = V(in)`.
