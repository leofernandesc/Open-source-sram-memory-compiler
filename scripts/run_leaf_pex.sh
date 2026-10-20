#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TCL_SCRIPT="$ROOT_DIR/layout/extract_leaf_pex.tcl"
MAGIC_RC="${PDK_ROOT:?PDK_ROOT is required}/${PDK:?PDK is required}/libs.tech/magic/${PDK}.magicrc"

LEAVES=(
  bitcell_6t
  sense_amp
  precharge
  wl_driver
  write_driver
)

for cell in "${LEAVES[@]}"; do
  leaf_dir="$ROOT_DIR/layout/$cell"
  pex_dir="$leaf_dir/pex"
  log_file="$pex_dir/${cell}_pex.log"
  netlist="$pex_dir/${cell}_pex.spice"
  work_dir="$(mktemp -d "/tmp/sram-pex-${cell}.XXXXXX")"

  mkdir -p "$pex_dir"
  cp "$leaf_dir/${cell}_flat.mag" "$work_dir/${cell}_flat.mag"
  echo "[PEX] $cell"
  (
    cd "$work_dir"
    PEX_CELL="$cell" PEX_OUT="$netlist" \
      magic -dnull -noconsole -rcfile "$MAGIC_RC" < "$TCL_SCRIPT" > "$log_file" 2>&1
  )
  rm -rf "$work_dir"

  if [[ ! -s "$netlist" ]]; then
    echo "[FAIL] missing PEX netlist: $netlist" >&2
    exit 1
  fi

  resistors=$(awk '/^R/{n++} END{print n+0}' "$netlist")
  capacitors=$(awk '/^C/{n++} END{print n+0}' "$netlist")
  devices=$(awk '/^X/{n++} END{print n+0}' "$netlist")
  echo "[PASS] $cell R=$resistors C=$capacitors X=$devices"
done
