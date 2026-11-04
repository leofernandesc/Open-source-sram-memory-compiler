#!/usr/bin/env bash
# Each action is explicit: no extraction/long campaign starts by default.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
action="${1:-help}"
if [[ $# -gt 0 ]]; then shift; fi
case "$action" in
  digital) tool=run_phase2_digital.py ;;
  pilot) tool=run_phase2_physical_pilot.py ;;
  fabric) tool=run_phase2_fabric.py ;;
  binding) tool=run_phase2_binding.py ;;
  access) tool=run_phase2_access.py ;;
  route) tool=run_phase2_place.py; set -- --route "$@" ;;
  layout) tool=finish_phase2_layout.py ;;
  gds) tool=verify_phase2_gds.py ;;
  gls) tool=run_phase2_routed_gls.py ;;
  extracted-access) tool=run_phase2_extracted_access.py ;;
  audit) tool=audit_phase2.py ;;
  evidence-guards) tool=verify_phase2_evidence_guards.py ;;
  top-lef) tool=export_phase2_top_lef.py ;;
  pack-raw) tool=pack_phase2_evidence.py ;;
  package) tool=package_phase2.py ;;
  *) printf '%s\n' 'Usage: scripts/run_phase2.sh {digital|pilot|fabric|binding|access|route|layout|gds|gls|extracted-access|top-lef|pack-raw|evidence-guards|audit|package} [options]'
     exit 0 ;;
esac
case "$action" in
  route|fabric|layout|gds|access|extracted-access)
    "$root/tools/sram-eda" python3 tools/phase2_resources.py
    ;;
esac
exec "$root/tools/sram-eda" env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 "tools/$tool" "$@"
