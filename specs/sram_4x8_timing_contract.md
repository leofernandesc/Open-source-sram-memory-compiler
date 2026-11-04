# Contrato temporal público — protótipo SRAM 4×8

## 1. Escopo e autoridade

Este documento complementa, sem substituir, a
[especificação técnica](technical_specification.md), o
[contrato digital](sram_4x8_digital.md) e o
[binding físico](phase2_physical_interface.md). Aplica-se ao protótipo SKY130A
4×8, single-port 1RW, 1,8 V, sem reset externo. Preserva o decoder dinâmico
de 33 MOS e as seis famílias de células selecionadas na Fase 1.

**Definido funcionalmente** descreve o protocolo aprovado. **Experimental**
identifica estímulos ou medidas TT/1,8 V/27 °C, com conectividade e junções
extraídas dos 1.493 MOS, sem RC de interconexões. **Pendente** identifica um
limite numérico ainda não caracterizado. Este documento não é uma datasheet
de produção, não estabelece Fmax e não qualifica PVT, potência ou fabricação.

## 2. Interface e operações

Entradas: `CLK`, `ADDR[1:0]`, `CSb`, `OEb`, `WEb`. `DATA[7:0]` é
bidirecional; `VDD`/`VSS` são alimentação. `ADDR[1:0]` mapeia as linhas
0, 1, 2 e 3; não há column mux nem pino adicional de validade/reset.

| CSb | OEb | WEb | Pedido capturado na subida | Saída SRAM sob esses controles atuais |
|---:|---:|---:|---|---|
| 0 | 0 | 0 | Inválido; sem novo acesso | Desabilitada |
| 0 | 0 | 1 | Leitura | Habilitada somente se READ_Q também for 1 |
| 0 | 1 | 0 | Escrita | Desabilitada |
| 0 | 1 | 1 | Idle | Desabilitada |
| 1 | 0 | 0 | Desabilitado | Desabilitada |
| 1 | 0 | 1 | Desabilitado | Desabilitada |
| 1 | 1 | 0 | Desabilitado | Desabilitada |
| 1 | 1 | 1 | Desabilitado | Desabilitada |

"Sem novo acesso" refere-se ao pedido capturado naquela borda. Mudar controles
vivos depois de uma captura válida não cancela essa transação interna. A
habilitação efetiva de DATA é:

```text
drive_DATA = READ_Q AND NOT(CSb) AND NOT(OEb) AND WEb
```

READ_Q/WRITE_Q são registradores sem reset. Antes da primeira captura eles
não têm estado lógico garantido; controles vivos conhecidos e inativos
mascaram a saída no modelo funcional. A partida analógica é avaliada em
separado, depois da estabilização da alimentação.

## 3. Clock e responsabilidades de captura

| Evento | Responsabilidade |
|---|---|
| Antes da subida n | Mestre apresenta endereço, controles e, na escrita, DATA; respeita setup/hold ainda sem valores públicos qualificados |
| Subida n | Captura única de endereço/operação e dos dados de escrita |
| Fase alta n | Controle físico libera pré-carga, avalia decoder e executa acesso capturado |
| Descida n | Registrador de leitura captura DOUT_RAW, se READ_Q=1 |
| Após descida n | Novo resultado aparece em DATA após atrasos físicos, se ambos os enables de leitura permitirem |
| Fase baixa | Retorno seguro à pré-carga e preparação do próximo acesso |

A borda pública e a borda nos FF não são simultâneas: CTS, inversão de clock
e buffers têm atraso. A captura de saída usa `dfxtp_1` positivo com clock
fisicamente invertido. Os requisitos do dado interno referem-se ao clock
local desse FF; requisitos de entrada públicos referem-se a CLK público.

As bancadas usam período de **20 ns**, fases de **10 ns** e transições das
fontes de **50 ps**, equivalentes a **50 MHz no experimento**. Não são mínimos
de período/largura de pulso nem Fmax. Os instantes nominais de PWL marcam o
início da transição; cruzamentos de 50% ocorrem 25 ps depois para rampas de
50 ps. Não se misturam essas duas referências nas medidas.

## 4. Leitura ciclo a ciclo

1. O mestre libera seu driver de DATA e apresenta `001` e o endereço antes
   da subida. Setup/hold públicos continuam pendentes.
2. A subida captura endereço e READ_Q. Alterar ADDR depois do hold não troca
   a linha deste acesso. O endereço interno permanece registrado.
3. O circuito físico desliga a pré-carga, habilita avaliação/wordline e
   desenvolve diferencial em BL/BLB. SCLK habilita regeneração posteriormente.
4. A descida captura o novo resultado. Antes dela, DATA pode conter o
   **resultado da leitura anterior**, mesmo com o driver já habilitado.
5. Após os atrasos de captura/mux/driver, o mestre pode amostrar o novo
   resultado. Não existe um limite qualificado de `tREAD_VALID` nesta fase.
6. O registrador preserva esse resultado até outra leitura na descida,
   inclusive durante escritas e ciclos inativos. Mascarar a saída produz Z,
   não apaga o registrador. Restaurar leitura viva pode expor novamente seu
   conteúdo quando READ_Q ainda está ativo.

Tabela de eventos funcional — **não é uma forma de onda medida**:

```text
Evento                 subida n       descida n      subida n+1    descida n+1
Endereço capturado     A              A              B             B
Registro de saída      anterior       resultado(A)   resultado(A)  resultado(B)
DATA se drive_DATA=1   anterior       A após atraso  A             B após atraso
```

Os pontos físicos são distintos:

| Ponto | Relação com o resultado |
|---|---|
| SA_OUT | Saída elétrica do sense amplifier |
| DOUT_RAW | Mesmo nó de SA_OUT no binding selecionado; não há registrador entre ambos |
| FF_D | Saída do mux de seleção/feedback antes do FF; atraso e carga adicionais |
| FF_Q | Resultado armazenado na captura local associada à descida pública |
| DATA | FF_Q através do ebufn e do enable capturado/vivo; pode estar em Z |

Igualdade de valor lógico não implica igualdade de instante. Ler uma posição
nunca escrita não tem conteúdo conhecido; o modelo funcional retorna X e
os ensaios elétricos não exigem 00/FF dessa posição.

## 5. Escrita ciclo a ciclo

1. O mestre retira leitura viva e mantém seu driver desligado até a SRAM
   efetivamente liberar DATA. Só então dirige a palavra de escrita.
2. Apresenta `010`, endereço e dados antes da subida. Essa borda captura os
   três; os write drivers usam DIN_Q e seus complementos internos.
3. Durante a fase alta, WE e a WL selecionada efetuam a escrita sem dirigir
   as bitlines simultaneamente com a pré-carga. O mestre pode mudar os dados
   depois do hold público, ainda pendente numericamente; isso não recaptura DIN.
4. O acesso termina e as wordlines/write drivers liberam as linhas antes de
   a pré-carga voltar a conduzir. O modelo digital conclui a escrita na
   descida como convenção funcional, sem recapturar DATA nessa borda.

Desabilitar controles vivos depois da subida não aborta uma escrita já
capturada. Para impedir uma escrita, apresente um comando inativo na borda
de captura, respeitando setup/hold. A SRAM não deve dirigir DATA em escrita.

## 6. Troca de direção do barramento

Leitura→escrita: retirar leitura viva → aguardar liberação real da SRAM →
habilitar driver do mestre → estabelecer dado/setup → próxima subida.
Escrita→leitura: respeitar hold da escrita → desligar driver do mestre →
permitir leitura viva/capturada. DATA pode começar exibindo resultado antigo.

Não dirigir DATA enquanto a SRAM ainda o estiver dirigindo. `tDATA_DISABLE`,
`tDATA_ENABLE` e `tTURNAROUND` são pendentes; não se prescreve um intervalo
numérico arbitrário nem se alega Zero Bus Turn-around. Os probes de 1 kΩ
comprovam liberação nos instantes ensaiados, não caracterizam leakage nem
o pior atraso de desligamento. O modelo RTL não exige ciclo morto quando
as regras de propriedade são atendidas; isso não garante handoff instantâneo
no circuito elétrico.

## 7. Partida e condicionamento

Não existe reset externo e o conteúdo das bitcells e do registro de saída
não é garantido na energização. Não usar `.ic`, `.nodeset`, reset fictício
ou leitura inicial com expectativa de zero.

Procedimento experimental de referência: manter CLK baixo e controles
inativos durante a rampa de 1 ns; realizar duas capturas de `111` em clock
de 20 ns, antes do primeiro acesso. Na bancada histórica essas subidas
nominais são 10 e 30 ns, há uma leitura sem expectativa a 50 ns, e a primeira
escrita ocorre a 70 ns. Logo, o primeiro acesso não era a primeira escrita.
As wordlines e WE devem permanecer inativos, o decoder deve pré-carregar e
BL/BLB devem chegar à condição de pré-carga antes da avaliação.

Cinco ensaios adicionais passaram com rampas de 1/5/10 ns e 0/2/3 capturas
inativas nas combinações registradas em
[phase2_final_polish.md](../docs/phase2_final_polish.md). A condição curta
ensaiada foi rampa de 1 ns mais 9 ns de espera até a primeira escrita,
sem captura inativa anterior. Para reprodução nominal, mantém-se a recomendação
de duas capturas inativas; isso não é uma alegação estatística de superioridade.
Zero ciclos de condicionamento, quando ensaiado, **não significa zero tempo
de espera após alimentação**. A recomendação continua um procedimento nominal;
não existe `tSTARTUP` mínimo qualificado para todas as rampas/estados/PVT.

## 8. Parâmetros públicos

"Pendente" não equivale a zero. Não se usa setup/hold de um FF isolado como
setup/hold público da macro, que inclui caminhos de entrada e clock.

| Parâmetro | Definição e referência | Estado/valor | Condição/evidência e limite |
|---|---|---|---|
| tCLK | Entre subidas consecutivas de CLK público a 50% | Experimental: 20 ns | Bancadas originais/dirigida e SDC; não período mínimo |
| tHIGH | Subida→descida pública a 50% | Experimental: 10 ns | Mesmo ensaio; não largura mínima |
| tLOW | Descida→subida seguinte a 50% | Experimental: 10 ns | Mesmo ensaio; não tempo mínimo de recuperação |
| tSU_ADDR | ADDR válido antes da subida pública | Pendente | Captura funcional definida; sem sweep/limite macro |
| tH_ADDR | ADDR mantido depois da subida pública | Pendente | Perturbação tardia aprovada não caracteriza hold mínimo |
| tSU_CTRL | Comando válido antes da subida pública | Pendente | Caminhos combinacionais de decodificação e clock incluídos na futura medida |
| tH_CTRL | Comando estável depois da subida pública | Pendente | Mudança viva também afeta enable de saída independentemente da captura |
| tSU_DIN | DATA de escrita válido antes da subida pública | Pendente | Não substituir por setup D do dfxtp_1 |
| tH_DIN | DATA mantido depois da subida de escrita | Pendente | DIN_Q não é recapturado na descida |
| tREAD_VALID | Descida pública a 50%→novo DATA válido e estável, com driver habilitado | Pendente | Deve incluir clock local, FF_Q, ebufn, carga e slew; janelas internas abaixo não são esse atraso |
| tDATA_DISABLE | Retirada de enable vivo/capturado→SRAM deixa de dirigir DATA | Pendente | Probes em pontos discretos não estabelecem máximo |
| tDATA_ENABLE | Última condição de enable satisfeita→SRAM dirige DATA | Pendente | Não implica resultado da nova leitura disponível |
| tTURNAROUND | Guarda de propriedade entre desligamento de um driver e acionamento do outro | Pendente | Sem valor garantido nem ZBT |
| tSTARTUP | Alimentação/condicionamento até primeiro acesso legal | Procedimento experimental; mínimo pendente | Rampa/espera/capturas explicitadas acima e na campanha adicional |

## 9. Medições internas disponíveis

As janelas usam níveis válidos de 20%/80% de 1,8 V (baixo −0,18..0,36 V;
alto 1,44..1,98 V), em relação à subida de 50% do clock local do FF de saída.
Medem estabilidade **disponível**, não requisitos mínimos do dispositivo.

| Medida | Campanha original | Campanha dirigida | Interpretação |
|---|---:|---:|---|
| Menor janela válida anterior em SA_OUT/DOUT_RAW | 7,438005478 ns | 7,439470500 ns | Desde a primeira amostra válida após a última inválida até captura local, com discretização do transiente |
| Menor janela válida anterior em FF_D | 7,240390655 ns | 7,248137784 ns | Após mux; não setup público |
| Janela válida posterior inspecionada | ≥2 ns | ≥2 ns | Limite inferior da janela limitada a 2 ns; não hold mínimo |
| Referência setup D→CLK dfxtp_1 | 0,6206849 ns | Mesma referência | Maior entrada das tabelas TT/25 °C, não macro a 27 °C |
| Referência hold positivo D→CLK dfxtp_1 | 0,1409486 ns | Mesma referência | Maior entrada positiva TT/25 °C; não caracterização do ensaio TT/27 °C |

Bits já válidos no começo da observação têm flags de limite inferior no CSV.
A matriz da biblioteca inclui diversos slews e não equivale ao ponto físico
com carga/slew medidos. A comparação de referência passa no ensaio nominal;
isso não qualifica STA, outros corners ou setup/hold externo.

## 10. Ordenação interna e histórico

| Relação | Implementação e verificação |
|---|---|
| Liberação de pré-carga | Tap 24 e tap 80 formam PRECH; baixo pré-carrega |
| Escrita | WE qualificado por WRITE_Q, CLK e tap 40 |
| Avaliação | PCLK qualificado por validade, CLK e tap 60; baixo pré-carrega decoder |
| Wordlines | DEC qualificado por PCLK e passado ao driver; uma WL ativa por acesso |
| Sense | READ_Q e tap 80 geram SCLK; baixo amostra, alto regenera |
| Captura e recuperação | Clock local invertido captura antes de o sense perder o resultado; SCLK persiste além da descida |

Os números 24/40/60/80 são posições na cadeia de 80 inversores HD, **não ns**.
A ordenação requerida é PRECH liberado antes de WE/WL, endereço/complementos
estáveis antes da avaliação, diferencial antes do sense e dado válido na
captura local. WE/WL devem liberar antes da condução da pré-carga seguinte.

Historicamente, o primeiro piloto apresentou guarda WE20% versus PRECH80%
de **−232,897 ps**. Mover a qualificação de WE para tap 40 produziu
**+167,388 ps no piloto corrigido**. O binding atual já contém essa correção;
nenhum circuito é alterado nesta rodada. Esses números não são margens
universais nem resultados da geometria final. As verificações do top extraído
checam exclusão elétrica e prontidão no período baixo, não só readback final.

Na campanha adicional de partida do top extraído, 55 ciclos ativos forneceram
as seguintes observações interpoladas, sem novos limites de aceitação:

| Separação medida | Faixa observada |
|---|---:|
| PRECH80% liberado→WE20% ativo | 0,211682..0,213332 ns |
| WL20% liberada→PRECH80% conduzindo | 2,196910..2,198232 ns |
| WE20% liberado→PRECH80% conduzindo | 2,290378..2,290809 ns |
| WL80% ativa→SCLK20% regenerando | 0,237618..0,243742 ns |

O menor diferencial BL/BLB com sinal esperado por leitura no cruzamento
SCLK20% variou de 1,735510 a 1,750400 V. O mínimo global dessa campanha é
1,735510 V; não se deve substituí-lo pelo valor de outra bancada. A ausência
de wire RC, offset estatístico e outros corners impede tratá-lo como margem
garantida. Os eventos e fontes estão no
[relatório de medições](../reports/phase2/final_polish_20261104/events/results.json).

## 11. Evidências e reprodução

- Fontes: [controlador](../rtl/sram_controller.v),
  [wrapper](../rtl/sram_4x8_wrapper.v),
  [fases físicas](../physical/phase2/macro_binding.v).
- Identidade do circuito e condições:
  [manifesto de entrega](../physical/phase2/delivery.json) e
  [bancada original](../reports/phase2/extracted_access_singlethread/bench.spice).
- Captura reanalisada nesta rodada:
  [original](../reports/phase2/final_polish_20261104/capture_baseline/results.json),
  [dirigida](../reports/phase2/final_polish_20261104/capture_directed/results.json).
  Os CSVs e hashes do raw identificam exatamente cada medida.
- [Histórico da correção de fases](../reports/phase2/phase_guard_review/results.json).
- [Campanha de partida e interpretação](../docs/phase2_final_polish.md).

Para refazer as janelas, usar diretórios novos:

```sh
./tools/sram-eda python3 tools/analyze_phase2_capture_review.py --output reports/phase2/local/capture_new
./tools/sram-eda python3 tools/analyze_phase2_capture_review.py --source reports/phase2/review_20261104/directed --output reports/phase2/local/capture_directed_new
```

Esses comandos precisam dos transientes completos identificados nos receipts.
O excerpt decimado serve para visualização, não para reproduzir as medidas.
Parâmetros públicos pendentes exigem caracterização posterior e deliberação
da equipe; a aprovação deste contrato funcional não fornece esses números.
