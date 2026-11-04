# Fase 2 — diagnóstico inicial da auditoria (passagem 1)

Esta passagem não modificou fontes, seleção da Fase 1 ou evidências anteriores.
Data e estado exatos estão em `reports/phase2/local/review_20261104/initial.json`:
branch `integration/phase2-4x8`, HEAD `3b0675b6fe42c79561be6e710e328ce95b8b6f81`,
nenhuma diferença staged; `.gitignore` e `tools/sram-eda` modificados e a
implementação da Fase 2 untracked. Foram registrados hashes de 233 arquivos e
copiadas 58 fontes antes de alterações. SHA-256 do registro inicial:
`63e32296cdc2c2bd507acdba50af7da63b64e581d3ee43265eae65cf4ab272b8`.

O notebook tinha aproximadamente 2,7–3,1 GiB disponíveis, swap de 4 GiB
parcialmente utilizada e 3,4 GiB livres em disco. Nenhum dado foi apagado.
O container existente contém Yosys 0.44, OpenROAD ee9759486, Magic 8.3.684,
Netgen 1.5.293, ngspice 44.2 e Icarus 13.0 de desenvolvimento. São versões
observadas, não uma garantia associada apenas ao nome da imagem.

## Resultados preliminares conferidos

* RTL: protocolo `001`/`010`, captura de requisição na subida e saída na
  descida, sem reset e sem dupla captura na fronteira da macro.
* Nova síntese SKY130HD/GLS: 15.619 checks, 2.504 transações; piloto tri-state
  de 8 checks e rejeição da polaridade invertida. Saída em
  `reports/phase2/local/review_20261104/digital`.
* Nova importação do GDS original, DRC e LVS expandido: PASS, zero DRC e
  1.493 MOS, em `reports/phase2/local/review_20261104/gds`. Sem PEX RC.
* A auditoria antiga reproduziu PASS para 128/392 verificações a partir da
  forma de onda existente. Esse PASS não foi tomado como prova suficiente
  dos mecanismos de integridade: os testes negativos abaixo expuseram falhas.

## Constatações e plano de correção

| ID | Nível | Localização inicial | Evidência e impacto | Correção e verificações afetadas |
|---|---|---|---|---|
| R01 | P1 | `tools/audit_phase2.py:electrical` | CSV com `voltage_v=nan` foi aceito; `abs(NaN)>tolerância` é falso. | Exigir valores finitos e tipos válidos. Repetir análise bruta e negativos em cópias; circuito e GDS não mudam. |
| R02 | P1 | `tools/audit_phase2.py:electrical` | Inventário `artifacts={}` e netlist modificada com hash posterior atualizado foram aceitos; `artifacts_before_run` não é reconciliado. | Exigir evidências obrigatórias e conferir as identidades pré-execução. Repetir análise/negativos; preservar os 128/392 históricos. |
| R03 | P1 | `tools/package_phase2.py:main` | Retornou `LOCAL_REVIEW_CANDIDATE` para cópia do GDS com metal5 adicional cruzando trilhos de alimentação; só o subcell customizado foi comparado. | Vincular cada arquivo entregue ao inventário efetivamente auditado, rejeitar ausência/mudança e emitir FAIL sem selo de entrega. Repetir empacotamento e adulterações, mantendo intactos os arquivos originais. |
| R04 | P2 | `tools/run_phase2_place.py`, `tools/finish_phase2_layout.py`, dispatcher | Acabamento depende de `build/phase2/.../routed.odb` ignorado; comandos finais não constituem uma reprodução completa após clone. Não há SDC independente: clock de 20 ns está embutido em Tcl. | Documentar/implementar caminho completo de fontes a entrega, dependências explícitas e clock experimental rastreável; provar equivalência das restrições sem inventar IO delays ou STA da macro. |
| R05 | P2 | `tools/run_phase2_access.py:bench`, documentação elétrica | Campanha histórica não observa BL/BLB diretamente e não inclui walking-one/zero transistor-level. GLS contém esses padrões; isso não mede diferencial elétrico nem perturbação de entradas no circuito real. | Acrescentar bancada nominal dirigida, sem alterar o circuito nem inventar diferencial mínimo. Registrar amplitude observada, captura e cobertura; execução sequencial com preflight. |
| R06 | P2/P3 | `README.md`, `docs/sram_4x8_interfaces.md`, scripts de execução | Textos atuais dizem que síntese/GLS e macro integrada ainda são futuras; guardas de recursos não cobrem todas as entradas pesadas. | Corrigir somente textos atuais, preservar históricos e tornar verificações de recursos uniformes; conferir comandos em ambiente existente. |

Nenhum defeito P0 ou defeito elétrico/estrutural do GDS original foi demonstrado
nesta passagem. Isso não significa ausência de defeitos: a revisão detalhada
de conectividade, parâmetros, limites temporais e cobertura continua na passagem 2.

Os negativos originais estão em `initial_negative_probes.json` e
`package_negative_before.json`, no diretório local da revisão. Só cópias foram
alteradas. O segundo registra explicitamente o SHA do GDS adulterado e o
retorno incorreto do empacotador. Não são logs reconstruídos de ferramentas.

## Limites da lapidação autorizada

Corrigir guardas de evidência, dependências e documentação não altera critérios
elétricos nem exige redesenhar as seis células. Se uma incompatibilidade física
ou funcional exigir isso, ela será registrada para decisão da equipe. O
resultado inicial é **NÃO APROVADO — CORREÇÕES NECESSÁRIAS** quanto à auditoria
e ao empacotamento; os resultados positivos originais permanecem históricos.
