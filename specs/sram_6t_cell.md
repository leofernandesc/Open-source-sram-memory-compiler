# Célula SRAM 6T — especificação inicial

## Escopo

Capturar no Xschem uma célula SRAM single-port 6T para SKY130A, formada por:

- dois inversores CMOS cruzados;
- dois transistores NMOS de acesso controlados por `WL`;
- alimentação nominal `VDD = 1.8 V`;
- sinais externos `BL`, `BLB`, `WL`, `VDD` e `VSS`;
- nós internos `Q` e `QB`.

## Inventário de dispositivos

| Instância | Tipo | D | G | S | B | Função |
|---|---|---|---|---|---|---|
| M1 | `pfet_01v8` | Q | QB | VDD | VDD | pull-up de Q |
| M2 | `nfet_01v8` | Q | QB | VSS | VSS | pull-down de Q |
| M3 | `pfet_01v8` | QB | Q | VDD | VDD | pull-up de QB |
| M4 | `nfet_01v8` | QB | Q | VSS | VSS | pull-down de QB |
| M5 | `nfet_01v8` | Q | WL | BL | VSS | acesso de BL |
| M6 | `nfet_01v8` | QB | WL | BLB | VSS | acesso de BLB |

Os parâmetros iniciais são `L=0.15 um`, `W=0.42 um` e `nf=1`. Esses valores
servem apenas como ponto de partida; a estabilidade de leitura, writability,
leakage e área deverão ser medidos antes de congelar o dimensionamento.

## Critérios da primeira captura

1. Os seis dispositivos devem usar símbolos `sky130_fd_pr` e bulk explícito.
2. `Q` e `QB` devem estar cruzados nos gates dos inversores.
3. `BL` e `BLB` devem conectar somente aos drains/sources dos transistores de acesso.
4. A célula deve ser simétrica visualmente e sem pinos de alimentação implícitos.
5. A simulação inicial deve verificar retenção, leitura e escrita em `tt`, a 1.8 V.

## Limites atuais

O ambiente ainda não possui `xschem`, `ngspice`, `magic`, `netgen` ou o pacote
completo do SKY130A instalado. O arquivo será capturado agora com referências
compatíveis com a biblioteca padrão do open_pdks; a netlist e as simulações só
serão consideradas validadas após a instalação/descoberta dessas ferramentas.
