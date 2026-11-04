#!/usr/bin/env bash
# Rebuild an unselected candidate from frozen leaves and RTL, never cached ODBs.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
output="${1:-}"
electrical="${2:-}"
if [[ -z "$output" || "$output" == "--help" ]]; then
  printf '%s\n' 'Usage: scripts/reproduce_phase2_4x8.sh reports/phase2/local/<new-run> [--with-electrical]'
  printf '%s\n' 'Default: synthesis/GLS + full generation/route/DRC/LVS. Electrical option is a long TT SPICE run.'
  exit 0
fi
if [[ -n "$electrical" && "$electrical" != "--with-electrical" ]]; then exit 2; fi
./tools/sram-eda python3 - "$output" <<'PY'
import sys
from pathlib import Path
out=Path(sys.argv[1]).resolve();base=Path.cwd()/'reports/phase2/local'
if not out.is_relative_to(base) or out==base or out.exists():
    raise SystemExit('Use a new output directory under reports/phase2/local; existing evidence is preserved')
out.mkdir(parents=True)
PY
./scripts/run_phase2.sh digital --output "$output/digital"
./scripts/run_phase2.sh binding --output "$output/binding"
./scripts/run_phase2.sh fabric --output "$output/fabric"
./scripts/run_phase2.sh route --fabric-report "$output/fabric" --binding-report "$output/binding" --output "$output/route"
./scripts/run_phase2.sh layout --route-report "$output/route" --output "$output/layout"
./scripts/run_phase2.sh gds --layout-report "$output/layout" --output "$output/gds"
./scripts/run_phase2.sh gls --layout-report "$output/layout" --output "$output/gls"
if [[ "$electrical" == "--with-electrical" ]]; then
  ./scripts/run_phase2.sh extracted-access --gds-report "$output/gds" --layout-report "$output/layout" --output "$output/access"
fi
./tools/sram-eda python3 - "$output" "$electrical" <<'PY'
import json,sys,hashlib
from pathlib import Path
out=Path(sys.argv[1]);stages=['digital','binding','fabric','route','layout','gds','gls']
if sys.argv[2]:stages.append('access')
states={n:json.loads((out/n/'results.json').read_text()) for n in stages}
expected=['PASS','PASS_MAPPING_ONLY','PASS_LEAF_FABRIC','ROUTED_VERIFICATION_PENDING','LAYOUT_MATCH_REIMPORT_PENDING','PASS_GEOMETRY_LVS','PASS_FUNCTIONAL_ROUTED_GLS']
if sys.argv[2]:expected.append('PASS_EXTRACTED_NOMINAL_ACCESS')
if [states[n]['status'] for n in stages]!=expected:raise SystemExit('Reproduction incomplete; inspect individual receipts')
record={'status':'REPRODUCED_UNSELECTED_CANDIDATE','scope':'No selector, delivery manifest or frozen source changed',
        'electrical':'PASS' if sys.argv[2] else 'NOT_RUN','stages':{n:states[n]['status'] for n in stages},
        'receipts':{n:hashlib.sha256((out/n/'results.json').read_bytes()).hexdigest() for n in stages},
        'gds_sha256':hashlib.sha256((out/'gds/sram_4x8.gds').read_bytes()).hexdigest()}
(out/'reproduction.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
PY
