# Deliberação F1-04 — aceite com ressalva operacional

**Data:** 11/11/2026  
**Decisão registrada:** aceite do cumprimento da verificação isolada das variantes finais, **com ressalva de funcionamento PEX do sense amplifier em pequenos diferenciais**, autorizado pelo responsável pelo projeto nesta conversa.  
**Ratificação coletiva/orientador:** não comprovada neste registro.

## Fundamentação

A cadeia célula congelada → SHA-256 → deck ngspice → transiente → critérios e resultados foi reconstituída em `docs/phase1_final_isolated_20261111.md`. O WL driver foi aprovado em 6/6 casos. O sense esquemático foi aprovado em 12/12; a PEX passou em 8/12, com 4/4 casos de 5 mV reprovados ao considerar as duas avaliações por caso. Nenhum FAIL é renomeado ou apagado.

A investigação `docs/sense_pex_small_signal_investigation.md` demonstrou contribuição causal da assimetria capacitiva. Em TT/1,8 V/27°C, a PEX aprovou as duas polaridades e cargas nos pontos ensaiados a partir de 20 mV. A caracterização não determina offset garantido ou PVT.

A SRAM 4×8 com abutment, no transiente nominal de 72 bits examinados, mostrou pelo menos 1,571 V de diferencial assinado 50 ps antes de SCLK20. Esse valor não estabelece margem universal: o circuito integrado não incluiu todos os RC distribuídos.

## Deliberação

- **Manter** a folha de sense selecionada, sua PEX e os layouts congelados.
- **Aceitar** como satisfeito, com a exceção operacional anotada, o objetivo documental de comprovação isolada de F1-04 para a entrega nominal da Fase 2.
- **Preservar** 4 FAIL originais de 5 mV e todos os critérios publicados. O aceite não converte os 12 testes PEX em 12 PASS.
- **Transferir para a Fase 3** a qualificação do circuito completo com RC, TT/SS/FF, margens de timing, potência e eventual revisão do sense apenas caso o funcionamento necessário seja comprometido.
- Não alegar conclusão histórica dentro do prazo original de F1.
- A aprovação individual acima **não substitui** ata/assinatura dos quatro integrantes ou orientador.

**Estado:** `USER_ACCEPTED_WITH_EXCEPTION_TEAM_RATIFICATION_PENDING`.

Referências: `release/phase2_current.json`, `docs/phase1_final_isolated_20261111.md`, `docs/sense_pex_small_signal_investigation.md`.
