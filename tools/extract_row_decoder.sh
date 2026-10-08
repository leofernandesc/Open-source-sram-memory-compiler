#!/usr/bin/env bash
# Run explicitly on the other machine; no automatic extraction from DRC/LVS.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"
for tool_dir in /opt/xschem/*/bin /opt/netgen/*/bin /opt/ngspice/*/bin; do
    if [[ -d "$tool_dir" ]]; then PATH="$tool_dir:$PATH"; fi
done
export PATH="/opt/magic/8.3.684/bin:$PATH" PDK_ROOT=/opt/pdks PDK=sky130A
if [[ "$(magic --version)" != '8.3.684' ]]; then
    printf 'Select/install Magic 8.3.684 before extracting.\n' >&2
    exit 1
fi
python3 layout/row_decoder/build_layout.py --skip-import --extract
python3 -c 'from layout.row_decoder.layout_provenance import require_current_pex; print("PEX provenance:", require_current_pex()["status"])'
sha256sum layout/row_decoder/pex/row_decoder_pex.spice
