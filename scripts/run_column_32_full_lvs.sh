#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLUMN_DIR="$ROOT_DIR/layout/column_32_full"
MAGIC_RC="${PDK_ROOT:?PDK_ROOT is required}/${PDK:?PDK is required}/libs.tech/magic/${PDK}.magicrc"
NETGEN_SETUP="${NETGEN_SETUP:-/dev/null}"

(
  cd "$COLUMN_DIR"
  magic -dnull -noconsole -rcfile "$MAGIC_RC" < extract_flat_lvs.tcl \
    > extract_flat_lvs.log 2>&1

  cat \
    ../bitcell_6t/bitcell_6t_flat_extracted.spice \
    ../precharge/precharge_flat_extracted.spice \
    ../sense_amp/sense_amp_flat_extracted.spice \
    ../write_driver/write_driver_flat_extracted.spice \
    column_32_full_reference_top.spice \
    > column_32_full_reference.spice

  netgen -batch lvs \
    "column_32_full_v2_flat_extracted.spice column_32_full_v2_flat" \
    "column_32_full_reference.spice column_32_full_reference" \
    "$NETGEN_SETUP" \
    column_32_full_lvs.log \
    > column_32_full_netgen.out 2>&1
)

if ! grep -q "Final result: Circuits match uniquely" "$COLUMN_DIR/column_32_full_lvs.log"; then
  echo "[FAIL] column_32_full LVS did not match uniquely" >&2
  tail -80 "$COLUMN_DIR/column_32_full_lvs.log" >&2
  exit 1
fi

echo "[PASS] column_32_full LVS: Circuits match uniquely"
