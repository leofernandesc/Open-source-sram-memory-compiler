# Revisão das análises recentes do decoder — 08/10/2026

Branch: `feature/peripherals`. Revisão das conclusões registradas até `3b9e52a`.
A consulta ao remoto encontrou o checkpoint de Danilo `d7a6ebb` em
`origin/feat/sram-6t-cell`; nenhuma branch dele foi modificada ou integrada.

## Resultado da revisão

Podemos prosseguir com a caracterização do decoder atual. Os números
arquivados foram reproduzidos, mas a documentação e as dependências do plano
precisavam de ajustes. Esta revisão não justifica mudar a topologia ou o
sizing para simplesmente eliminar uma tela numérica. A qualificação final
continua dependendo de margens acordadas, condições adicionais e carga física.

Foram reprocessados os 116 waveforms das três matrizes de ponto de operação
e do refinamento FF. Os extremos assinados, contagens, hashes de waveforms,
netlists e manifests coincidem com os arquivos arquivados. Todos os 15.312
checks funcionais desses conjuntos estão registrados como PASS. O vínculo
do PEX ao esquemático e layout atuais também passou na checagem de proveniência.

| Condição | Checks baseline / PEX | Pico de magnitude baseline / PEX | Maior atraso WL até 90% no PEX |
|---|---:|---:|---:|
| TT / 1,8 V / 27 °C, 1 ps | 1.664 / 2.560 | 1,945748 / 1,877775 V | 561,777 ps |
| SS / 1,62 V / −40 °C, 1 ps | 1.664 / 2.560 | 1,766599 / 1,716479 V | 817,504 ps |
| FF / 1,8 V / 125 °C, 1 ps | 1.664 / 2.560 | 1,954645 / 1,879693 V | 494,785 ps |
| FF, dez pares refinados, 0,5 ps | 1.040 / 1.600 | 1,954674 / 1,879681 V | 494,780 ps |

A tela customizada de magnitude continua apontando dez casos baseline FF;
todos os casos PEX passam essa tela. O seu resultado continua distinto dos
checks funcionais. As condições acima são três pontos PVT selecionados, com
50 ps nas bordas ideais, 2 ns de antecedência de endereço e 17,4 fF por WL;
não representam uma matriz completa de processo × tensão × temperatura × carga.

Evidência consolidada: [verificação dos arquivos](../sims/row_decoder/results/decoder_analysis_review_20261008/artifact_review.json).
O PEX permanece com SHA-256
`8ee6b99aabf94bde9a1de2a13f0c040cda41dd55bb9568672e38a7f6bb54a6dc`.

## Correção: terminais externos e estados internos do BSIM4

`audit_signed_device_domain.py` mede os quatro terminais externos do
subcircuito MOS. Sua escolha de source conforme polaridade e tensão é uma
convenção útil de screening. Entretanto, o BSIM4 calcula suas diferenças de
tensão em `dNodePrime`, `sNodePrime`, `gNodePrime` e `bNodePrime`, conforme o
[código ngspice 44.2](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ld.c#L364-L372).
Os modelos instalados têm resistência de extensão (`rsh`, `nrd`, `nrs`) e
`rbodymod=1`. Portanto, a auditoria externa não mede exatamente o bias interno
do canal; as frases anteriores que equiparavam os dois foram corrigidas.

Para verificar o efeito, foi executada uma simulação adicional do baseline
FF `11→00`, com ponto de operação e passo máximo de 0,5 ps. O deck arquivado
recebeu somente seis probes de estado interno: `vgs`, `vds` e `vbs` de M12
NFET e M1 PFET. Os hashes dos modelos coincidem com os do ensaio original;
ngspice retornou 0, os 104 checks funcionais passaram e todas as traces
externas originais são bit a bit iguais às arquivadas.

| Medida no probe | Terminais externos | Estado interno orientado do modelo |
|---|---:|---:|
| M12 `VGS` no pico de `VGD`, 5,03325 ns | −0,670351 V | −0,674755 V |
| M12 `VDS` no mesmo ponto | +1,284323 V | +1,279922 V |
| M1 `VBS` mínimo após 1 ns | −0,141914 V | −0,120427 V |

Nesse probe, o NFET ainda apresenta `VGS` negativo e o PFET ainda apresenta
`VBS` inferior a −0,10 V em estados internos. A diferença externa/interna
não elimina os achados, mas altera os valores. Este resultado cobre dois
dispositivos de um caso baseline FF; não qualifica os 45 dispositivos de
todas as matrizes nem os estados internos do PEX.

As variáveis `@vgs`, `@vds` e `@vbs` são estados normalizados pela polaridade;
o pós-processamento orienta a fonte usando o sinal do `@vds` e converte para
volts assinados físicos. As leituras são definidas no
[código de consulta BSIM4](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ask.c#L192-L200),
e a inversão de canal está no
[load BSIM4](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5ld.c#L983-L997).

Evidências: [resumo e hashes](../sims/row_decoder/results/decoder_analysis_review_20261008/intrinsic_probe/summary.json),
[CSV externo/interno](../sims/row_decoder/results/decoder_analysis_review_20261008/intrinsic_probe/external_intrinsic_bias.csv),
[deck](../sims/row_decoder/results/decoder_analysis_review_20261008/intrinsic_probe/case.spice) e
[pós-processamento](../sims/row_decoder/results/decoder_analysis_review_20261008/intrinsic_probe/analyze_probe.py).
Raw e log permanecem ignorados pelo Git, com hashes no resumo.

## Interpretação das telas, avisos e convergência

A descrição dos avisos FF está correta: o ngspice limita `A2` a 1 e define
`A1=0`, enquanto os checks de `Eta0` e `Pdibl1/2` negativos apenas avisam.
Foram corrigidos links que usavam números de linha da página renderizada
em lugar das linhas do arquivo: [Eta0/A2](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L471-L498)
e [Pdibl](https://github.com/imr/ngspice/blob/ngspice-44.2/src/spicelib/devices/bsim4v5/b4v5check.c#L566-L575).
Os hashes e metadados dos resultados históricos foram preservados.

As [faixas SKY130](https://github.com/google/skywater-pdk/blob/main/docs/rules/device-details.rst#L4-L100)
são apresentadas como domínio de validade dos modelos SPICE. A ausência de
uma linha específica para `VGD` nessa tabela não demonstra que qualquer
excursão gate/drain seja aceitável. Mantemos a tela customizada e o achado de
4,674 mV como diagnóstico pendente de critério; não o transformamos em limite
de confiabilidade nem o removemos para obter PASS.

O refinamento de 1 para 0,5 ps confirma estabilidade nesses passos usando
Gear. Ele não prova independência do método de integração, tolerâncias ou
modelo. Também, os campos `baseline_accepted`/`pex_accepted` dos CSVs indicam
apenas PASS nos três critérios automáticos do runner, e não aprovação final
da equipe ou liberação de todas as faixas assinadas.

## Limites da cobertura e atualização de Danilo

O bench admite 1 ns para acomodação de saídas. A maior queda da WL até 10%
após a borda de pré-carga é 789,557 ps no PEX SS. A integração deve definir a
relação temporal entre CLK, PCLK, habilitação de acesso e pré-carga de BL/BLB;
a atual medição não verifica todas as condições idle/disabled/invalid do
contrato da SRAM nem o gerador físico de PCLK.

A consulta remota encontrou layouts e PEX de bitcell e linha de oito bits
na branch de Danilo. Seu checkpoint `d7a6ebb` e
`docs/cwl_pre_layout_estimate.md` declaram que a primeira PVT de carga WL de
08/10 inicializou o estado em taps resistivos de acesso. Os 102,873935 fF e
94 fF adicionais dessa rodada são diagnósticos inválidos para aceite; os
resultados de 07/10 foram marcados como históricos supersedidos. O próximo
insumo é a medição corrigida inicializando os nós de saída da latch (`.t0`),
com proveniência e interfaces revisadas pelos responsáveis.

Esse problema de inicialização não invalida nossos waveforms do decoder,
que usam capacitores lumped e não incluem bitcells. Mantém aberta a aplicação
desses resultados à carga física real. A pendência do plano foi atualizada
de layout ausente para carga física corrigida e aprovada.

## Sequência recomendada

1. Prosseguir com captura/endereço/PCLK para o sizing atual e medir
   sensibilidade a carga WL e a bordas finitas. Pontos adicionais, inclusive
   50/100 fF, são experimentos de sensibilidade, não cargas físicas aprovadas.
2. Repetir ruído injetado, retenção e duração das fases para o sizing atual.
   Cobrir temperaturas e tensões cruzadas nos corners, sem assumir que os
   três pontos já medidos são os piores para todas as métricas. Refinar
   numericamente os pontos críticos que apresentarem novas dúvidas.
3. Em paralelo, documentar os critérios de aceitação do modelo e ampliar os
   probes intrínsecos dirigidos aos extremos relevantes do PEX. A decisão
   final de sizing/margem depende desses critérios; os ensaios exploratórios
   podem continuar com suas limitações explícitas.
4. Consumir a carga WL corrigida do responsável e verificar os quatro caminhos
   decoder → driver → linha física e a sequência de controle. Rever sizing
   somente se uma condição definida falhar ou a margem acordada for insuficiente.
5. Atualizar DRC/LVS/PEX quando houver mudança física. O PEX atual pode ser
   reutilizado para os próximos testes do decoder preservado.

## Reprodução do probe

No ambiente EDA, o deck já preserva as fontes e os seis probes adicionais:

```bash
./tools/sram-eda python3 -c 'import subprocess; from pathlib import Path; p=Path("sims/row_decoder/results/decoder_analysis_review_20261008/intrinsic_probe").resolve(); r=subprocess.run(["ngspice", "-n", "-b", "case.spice"], cwd=p, capture_output=True, text=True, timeout=300); (p/"ngspice.log").write_text(r.stdout+r.stderr); raise SystemExit(r.returncode)'
./tools/sram-eda python3 sims/row_decoder/results/decoder_analysis_review_20261008/intrinsic_probe/analyze_probe.py
```

Para repetir a auditoria das matrizes preservadas, use o comando
`audit_signed_device_domain.py` do relatório de ponto de operação, gravando
as novas saídas em `/tmp` para preservar os manifests e hashes anteriores.
