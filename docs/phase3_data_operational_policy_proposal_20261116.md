# P3-DATA-002 — política operacional nominal de DATA

**Revisão r0 — PROPOSTA PARA REVISÃO, 16/11/2026.** Não é aprovação formal do
proprietário, ativação do perfil A ou aprovação global da SRAM.

Base: branch `feature/phase3-infra-leonardo`, HEAD
`ebf60a2725e8a40857323d3bbfd93c587ef52f77`, preservando o estado local.
Relaciona-se a [P3-DATA-001](phase3_data_verification_policy_decision_20261116.md),
ao [plano A](phase3_functional_a_implementation_plan_20261116.md), ao
[relatório A](phase3_functional_a_implementation_20261116.md) e à
[proposta temporal](phase3_data_timing_contract_proposal_20261116.md).

## 1. Decisão proposta e alcance

Adotar **O1a**, definir O2 por eventos fixos da bancada, separar as partes
funcional/elétrica de A10 em O3 e validar precondições de ensaio em O4.
Implementar essas escolhas em `phase3_nominal_bench_v1`, perfil experimental
separado de `phase2_qualification_v1` e de `phase3_functional_a_v1`.

A autorização recebida permite preparar e testar a proposta. Não fornece uma
assinatura de homologação. `approval=PROPOSED` e `global_gate_enabled=false`
permanecem obrigatórios. Um resultado funcional experimental PASS não modifica
o resultado de nenhum outro perfil nem qualifica B.

O domínio é somente o contexto pinado de 18 ciclos/370 ns: 4×8, SKY130A,
TT/1,8 V/27 °C, clock experimental de 20 ns/50%, slew de 50 ps, 10 fF/bit e
devices/junctions. Há 6 escritas, 9 leituras e 3 ciclos inativos, incluindo
condicionamento. Não se declara cobertura elétrica de SS/FF, RC distribuído,
oito combinações de controle, todas as máscaras ou todas as transições de palavras.

Fontes executáveis da proposta:

- [Política JSON pinada](../characterization/phase3/nominal_bench_v1.json).
- [Compilador de eventos/janelas](../tools/phase3/nominal_bench_plan.py).
- [Avaliador nominal](../tools/phase3/nominal_bench.py).

A fixture selecionada é
`reports/phase2/direct_abutment_20261111/qualification_v1/bench.spice`, SHA-256
`58809d4edca7002170644e4a7b006a945a4c489139e8b48c56af721af9b7d342`.
Não é editada. A seleção continua ancorada nos seletores e recibos existentes,
conferidos por `selected_inputs`.

## 2. Auditoria por decisão

| Decisão | Sustentação existente | Critério de bancada proposto | Referência/cobertura | Bloqueio e limite |
|---|---|---|---|---|
| O1a | Técnica §§6/15, DIG-05; temporal §§3/4: nova palavra depois da descida e propagação | Adotar as observações externas já usadas em `sample_ns` e `rise_ns+16,3` | Primeira amostra em/depois do instante agendado e antes da perturbação seguinte; 72 bits em cada grupo | Ponto ausente antes da próxima fase é ERROR; não procurar a primeira amostra correta. Não garante `tREAD_VALID` público |
| O2 | DIG-06/08 e tabela Consecutive reads; retenção e estabilidade com enable mantido | Monitorar intervalos entre observações/perturbações programadas e os estados de enable neles | Tabela da seção 3; 626 observações próprias, oito bits em cada intervalo aplicável | Fonte/record divergente, intervalo vazio ou amostragem incompleta impedem conclusão. Não usar acomodação de DATA/Q para recortar janelas |
| O3 | Técnica §§4/6/16; DIG-06/07/08; temporal §§4/6/8 | A10-F verifica retenção, direção, ausência de contenção e nova palavra nos pontos aplicáveis; A10-E conserva recuperação sem orçamento | 3 write→read, 1 idle→read, 9 restaurações CSb, oito bits: 104 oportunidades funcionais e 104 recuperações explicitamente não qualificadas | Nenhum prazo de 1 ns para DATA antigo após retomada. Não equivale a dispensar Q ou permitir palavra nova errada |
| O4 | DIG-01/02/05/06/07, binding sequência 1–5 | Conferir programação PWL, fontes observáveis, capturas, corrente/propriedade e integridade dos arquivos; manter o envelope interno existente como screen experimental | Todos os ciclos/capturas; 14 fontes observáveis; checks internos e de corrente existentes | Estímulo/evidência inválida é ERROR de ensaio. Setup/hold público e máximos de I/O continuam não caracterizados |

As fontes normativas são a [especificação técnica](../specs/technical_specification.md),
o [contrato digital](../specs/sram_4x8_digital.md), o
[contrato temporal](../specs/sram_4x8_timing_contract.md) e o
[binding físico](../specs/phase2_physical_interface.md). Esta proposta não os altera.
A inclusão dos intervalos contínuos abaixo é uma formalização de bancada que
precisa de aprovação operacional; não há promessa nova de atraso máximo da macro.

## 3. O2: tabela explícita de eventos, janelas e transições

Definições por leitura, em ns:

- `R = rise_ns`: início da rampa de subida do CLK público, não CLK50.
- `F = fall_ns = R+10`: início da rampa de descida pública.
- `S = sample_ns = R+11`: observação histórica da nova palavra.
- `P = weak_on_ns = R+11,5`: início da ativação da sonda oposta.
- `M = mask_ns = R+12,5`; `U = restore_ns = R+14`.
- `W = weak_off_ns = R+15,5`; `T = R+16,3`: observação histórica após a sonda.
- `E`: primeiro evento posterior a T que pode terminar a obrigação de estabilidade:
  mudança real de CSb/OEb/WEb, ativação de um driver de teste, próxima descida de
  leitura ou fim do transiente. Pontos PWL que repetem o mesmo valor não são mudanças.
- `G`: próxima descida pública que captura read; sem outra leitura, fim do transiente.

O compilador obtém eventos e fins de rampas dos pares PWL e confere sua
correspondência com os registros. Rampas dos acessos têm 50 ps; não se converte
25 ps de diferença entre PWL/CLK50 em nova guarda. O pós-sonda T é um **ponto de
observação preexistente do checker**, não um tempo escolhido a partir do raw.

| ID/fase | Intervalo e inclusividade | Q / DATA / direção exigidos |
|---|---|---|
| Q_NEW / DATA_NEW | Primeira amostra `t≥S`, necessariamente `t<P` | Q e DATA com a nova palavra conhecida; sem interpolar DATA ou saltar amostra inválida |
| DATA_NEW_STABLE | `[S,P)` | DATA novo correto em todas as amostras, READ_Q válido alto e TE_B válido baixo |
| Q_RETAIN | `[S,G)`; fim do transiente incluído se não houver outra leitura | Q conserva o resultado, incluindo escrita/idle/máscara. Complementa o monitor A existente até a captura **local** correspondente |
| DATA_POST | Primeira amostra `t≥T`, necessariamente `t<E` | Palavra registrada correta após a sonda; ponto nominal de ensaio, não máximo garantido de recuperação |
| DATA_POST_STABLE | `[T,E)`; fim do transiente incluído quando E for o fim | DATA correto, READ_Q alto e TE_B baixo. Se E for a próxima descida de read com enable mantido, também é obrigação A05 de palavra anterior |
| Atualização legal de leitura | `[F,S)` | Não exigir DATA novo instantaneamente em F. Captura local, envelope interno e retenção antes da captura continuam verificados; em S a palavra nova é obrigatória |
| Bits sem mudança lógica na captura | `[F,S)` | Q deve manter o nível se o bit anterior conhecido e o novo esperado forem iguais; DATA também, se a continuidade de enable estiver estabelecida. São 20 intervalos de Q e 12 de DATA, definidos pelo scoreboard, não pelo waveform |
| Sonda intencional | `[P,M)` | Q retido; check de corrente em `[R+12,R+12,35]`, inclusivo, preservado |
| Transição da máscara | `[M,M_fim)` | Q retido; sem liberação física instantânea presumida |
| Máscara estável | `[M_fim,U)` | Q retido; checks existentes de corrente/voltagem de liberação em `[R+13,2,R+13,8]`, inclusivos |
| Transição de restauração | `[U,U_fim)` | Q retido; sem máximo B de enable |
| Restauração ainda com sonda | `[U_fim,W)` | Q retido; corrente de condução em `[R+14,7,R+15,2]`, inclusivo, sem alegar nível lógico normal sob carga oposta |
| Desligamento da sonda | `[W,W_fim)` | Q retido; evento programado, não acomodação medida |
| Recuperação após sonda | `[W_fim,T)` | Recuperação elétrica não qualificada; palavra obrigatória no ponto T já existente |
| Retomada capturada após write/idle | `[R,F)` | Retenção do Q anterior quando conhecido; DATA antigo sem deadline aprovado. Recuperação B permanece NOT_CHARACTERIZED |

Os checkers compartilhados mantêm também os pontos de Q em `R+12`, `R+13,5`,
`R+14,8` e `R+16,3`, todas as verificações de exclusão/pré-carga e a detecção
de sobreposição entre host forte e ebuf. Não se retira um teste porque a
respectiva fase não promete um nível normal de DATA sob sonda intencional.

Fora da captura, Q não pode se corromper brevemente e voltar ao valor correto
antes da amostra seguinte. O monitor já existente em A começa no S programado
e vai até a captura local seguinte de cada bit, detectada pelo clock local;
esse clock é referência interna independente de DATA, não um instante de
acomodação escolhido para o novo plano. Os **novos** limites da tabela são
programados. O período F→S não pode esconder uma atualização na subida: as
janelas de Q/A05 atravessam a subida e terminam na descida/captura correspondente.
Bits que não comutam não recebem uma dispensa para glitches durante F→S, nem
recebem atraso zero fictício. A exceção de propagação é para mudança lógica legal,
não para apagar a obrigação de retenção de um bit cujo resultado permanece igual.

Exemplos de limites produzidos sem consultar DATA:

| Leitura | DATA_NEW_STABLE | DATA_POST_STABLE | Justificativa do fim |
|---|---|---|---|
| c6 | `[141;141,5)` | `[146,3;160)` | Read→read; próximo F; inclui subida de 150 ns |
| c7 | `[161;161,5)` | `[166,3;167)` | Controles deixam read para escrita em 167 ns |
| c11 | `[241;241,5)` | `[246,3;247)` | Próximo idle retira read em 247 ns |
| c17 | `[361;361,5)` | `[366,3;370]` | Última leitura; inclui o fim declarado |

Cada fronteira tem origem e inclusividade explícitas. Uma falha logo antes do
fim continua FAIL; uma perturbação intencional iniciada exatamente no fim não
é julgada pela janela anterior. A janela de atualização não é ampliada conforme
o dado observado. Pulsos menores que a resolução do transiente não são garantidamente
detectáveis; resolução é requisito de evidência, não tolerância elétrica.

## 4. Revisão formal proposta de A10 e efeito no legado

**A10-F, funcional nominal:** para retomadas capturadas, Q deve permanecer
retido quando já houver resultado conhecido, direção deve ser legal, não pode
haver contenção e a nova palavra deve passar em DATA_NEW. Para máscaras, Q não
é apagado, sondas demonstram direção/liberação e DATA_POST deve apresentar a
palavra registrada. Os 104 vínculos por cenário/ciclo/bit permanecem no inventário.
Na primeira leitura não se inventa uma palavra anterior conhecida.

**A10-E, elétrico:** início de condução, saída de Z, recuperação da palavra
anterior e máximos por arco continuam NOT_CHARACTERIZED. Há 104 oportunidades
registradas, sem `deadline_ns`, sem zero e sem orçamento derivado de TT.
O resultado de A10 não é simplesmente PASS: o objeto mantém `functional_status`
separado e o estado elétrico não caracterizado.

Os 64 checks históricos de DATA anterior continuam no comparador, com os
veredictos originais. Os 40 de read→read recebem um vínculo aditivo às novas
janelas contínuas A05, que são mais extensas que a janela antiga e avaliadas
independentemente. Os 24 de retomadas com Q anterior conhecido recebem uma
proposta aditiva de alcance B pendente, sem mudar seus resultados.

Os quatro FAILs originais não são apagados ou convertidos. A nova política
pode apresentar observações funcionais nominais corretas enquanto o legado
continua FAIL e B continua não qualificado. A integridade exige exibir todos
esses resultados juntos. As oito falhas do diagnóstico curto também permanecem
intactas; o perfil de 18 ciclos não passa a aceitar aquele contexto por semelhança.

## 5. O4: precondições e limitações de captura

A programação PWL deve corresponder a CLK, comando, endereço e payload dos
registros. CLK/CSb/OEb/WEb, HOST_EN, HOST_WEAK_EN e HOST[7:0] observáveis devem
cumprir os níveis existentes em seus platôs. Só as rampas PWL programadas ficam
fora do teste de platô. ADDR externo não está salvo como probe nesse contexto:
sua programação é auditada pelo deck pinado e confrontada com ADDR_Q capturado;
isso não se apresenta como medida analógica direta de setup/hold externo.

Permanecem obrigatórios os checks internos de pedido/endereço/DIN_Q, células
conhecidas, captura local, retenção, WL/WE/PRECH/sense e corrente/propriedade.
O envelope conservador do FF TT/25 °C contra o transiente TT/27 °C é um screen
experimental já existente, sem equivalência a setup/hold público da SRAM.

Fonte/record divergente é erro de precondição, não prova de defeito do DUT.
Falta de vetor, intervalo, identidade, amostras ou pin íntegro é ERROR/BLOCKED,
nunca PASS por cobertura reduzida. O verificador recusa lacunas superiores ao
passo de transiente declarado de 10 ps, considerando somente a quantização
numérica da exportação; não aumenta limiares elétricos nem tolerâncias de timing.

## 6. Aprovações e integração posterior

Dependem de aprovação explícita:

1. Alcance O1a e adoção de **ambos** os pontos históricos como contrato nominal.
2. Fronteiras, inclusividade, transições e extensão de estabilidade de O2.
3. Desdobramento A10-F/A10-E e classificação normativa aditiva, sem revisão dos
   veredictos antigos; B continua pendente.
4. Precondições/limitações O4 e alcance de captura experimental, sem setup/hold público.
5. Autorização posterior para registrar o perfil como gate operacional e sua
   relação com A. Nada muda o padrão legado nesta etapa.

A proposta torna as escolhas operacionais concretas para homologação nominal.
Se for desejada validade contínua após enable **antes** dos pontos adotados, falta
definir e aprovar essa janela/obrigação adicional ou um orçamento B. Ela permanece
não qualificada, sem limite inventado. Outro consumidor, corner, carga, slew ou
extração requer novo domínio/contexto e decisão; estes resultados não são datasheet.

Não se executa SPICE, PVT ou Liberty nem se realiza commit/merge/push. O perfil
experimental somente produz avaliação offline identificada como tal; o gate A
existente permanece bloqueado e os estados/códigos públicos permanecem preservados.
