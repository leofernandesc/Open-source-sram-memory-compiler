run_id:      memory-ip_20261124_130441
design_name: SKY130 SRAM 4x8 Phase 3 closure
tool:        Python 3.10/NumPy 1.26 evidence analysis; verified SRAM EDA container with ngspice 44.2 and SKY130A
start_time:  2026-11-24T09:04:41-04:00
last_stage:  p3_integrated_ff_candidate_diagnostic
status:      IN_PROGRESS
active_stage: p2_protocol_and_witness_review
offline_audit_status: COMPLETED; candidate SS high-resolution c12 and integrated FF diagnostic subsequently completed
p1_status:   COMPLETED
p2_status:   INCONCLUSIVE_PENDING_PROTOCOL_REVIEW
p3_status:   PARTIAL_FF_FUNCTIONAL_PASS_OWNERSHIP_INCONCLUSIVE
p0_status:   COMPLETED
p0_snapshot: /home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124
p0_manifest: /home/danilo_cunha/projetos/ueletronica/phase3_evidence_20261124/manifest.json
p0_files:    2717
p0_bytes:    1807007816
p0_manifest_verification: PASS; 2717 files and 1807007816 bytes rehashed, 0 mismatches
signoff_achieved: false
status_note: P0 snapshot and 126-file historical source delta are SHA-256 verified. P1 topology, lane coverage, and receipt gates PASS; raw ownership remains inconclusive, with TT c2 bits 4/7 supported only by a diagnostic static-payload supplement. Candidate SS c12 high-resolution replay completed at 10 ps max step: seven lanes meet the 50 ps witness, bit6 has a 51.677 ps interpolated region but only 45.050 ps conservative native witness; all lanes release by 247.655195 ns. P2 remains INCONCLUSIVE pending protocol/method review; threshold unchanged. Candidate integrated FF replay passes all 18 functional operations, while ownership is inconclusive in c2 write and c10 read_to_write; c12 ownership passes in FF only. This run uses PEX a1e812..., distinct from the legacy runner's expected PEX 12c41..., and its provenance is recorded. SNM is provisional, Liberty is uncharacterized, and 8x8/32x8 physical characterization remains pending. Electrical qualification is NOT_CHARACTERIZED. No signoff is claimed.
last_audit: 2026-11-24 controlled SS c12 replay and integrated FF functional diagnostic
last_audit_status: COMPLETED; P2 inconclusive and P3 partial; details/evidence paths recorded in docs/phase3_plano_fechamento_20261124.md
host_environment: Python 3.12.3; docker binary available; EDA tools absent from host PATH
container_environment: VERIFIED via ./tools/sram-eda --check; sram-xschem image isaiassh/unic-cass-tools:1.1.0; ngspice 44.2; Magic 8.3.613; Netgen 1.5.293; SKY130A required files PASS
dimension_gate: 8x8 and 32x8 characterized results required by technical specification; physical campaigns not found in preserved Phase 3 inventory; Fase 4 timing creates formal scope dependency
p2_simulation_gate: candidate SS replay done at 10 ps maximum native step; bit6 misses the unchanged conservative 50 ps floor; protocol/method review required before another controlled run
