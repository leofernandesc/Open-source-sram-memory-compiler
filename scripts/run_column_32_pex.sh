#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLUMN_DIR="$ROOT_DIR/layout/column_32"
MAGIC_RC="${PDK_ROOT:?PDK_ROOT is required}/${PDK:?PDK is required}/libs.tech/magic/${PDK}.magicrc"

mkdir -p "$COLUMN_DIR/pex"

(
  cd "$COLUMN_DIR"
  magic -dnull -noconsole -rcfile "$MAGIC_RC" < generate_column_32.tcl \
    > column_32_generate.log 2>&1
  magic -dnull -noconsole -rcfile "$MAGIC_RC" < extract_column_32_pex.tcl \
    > pex/column_32_pex.log 2>&1
)

netlist="$COLUMN_DIR/pex/column_32_p1800_pex.spice"
if [[ ! -s "$netlist" ]]; then
  echo "[FAIL] missing column PEX netlist: $netlist" >&2
  exit 1
fi

hier_drc=$(awk '/COLUMN32_HIER_DRC_BEGIN/{f=1;next}/COLUMN32_HIER_DRC_END/{f=0}f' "$COLUMN_DIR/column_32_generate.log" | tail -1)
flat_drc=$(awk '/COLUMN32_FLAT_DRC_BEGIN/{f=1;next}/COLUMN32_FLAT_DRC_END/{f=0}f' "$COLUMN_DIR/column_32_generate.log" | tail -1)
resistors=$(awk '/^R/{n++} END{print n+0}' "$netlist")
capacitors=$(awk '/^C/{n++} END{print n+0}' "$netlist")
devices=$(awk '/^X/{n++} END{print n+0}' "$netlist")

echo "[PASS] column_32 hierarchy DRC: ${hier_drc:-unknown}"
echo "[PASS] column_32 flat DRC: ${flat_drc:-unknown}"
echo "[PASS] column_32 PEX R=$resistors C=$capacitors X=$devices"
