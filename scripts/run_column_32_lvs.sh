#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLUMN_DIR="$ROOT_DIR/layout/column_32"
MAGIC_RC="${PDK_ROOT:?PDK_ROOT is required}/${PDK:?PDK is required}/libs.tech/magic/${PDK}.magicrc"
NETGEN_SETUP="${NETGEN_SETUP:-/dev/null}"

(
  cd "$COLUMN_DIR"
  magic -dnull -noconsole -rcfile "$MAGIC_RC" < extract_column_32_lvs.tcl \
    > column_32_lvs_extract.log 2>&1
  cat ../bitcell_6t/bitcell_6t_flat_extracted.spice > column_32_p2652_reference.spice
  {
    echo '.subckt column_32_p2652_reference BL BLB VSS VDD WLOFF'
    for row in $(seq 0 31); do
      printf 'XBC%02d VDD BL BLB VSS WLOFF bitcell_6t_flat\n' "$row"
    done
    echo '.ends column_32_p2652_reference'
  } >> column_32_p2652_reference.spice
  netgen -batch lvs \
    'column_32_p2652_flat_extracted.spice column_32_p2652_flat' \
    'column_32_p2652_reference.spice column_32_p2652_reference' \
    "$NETGEN_SETUP" column_32_p2652_lvs.log \
    > column_32_p2652_netgen.out 2>&1
)

if ! grep -q 'Final result: Circuits match uniquely' "$COLUMN_DIR/column_32_p2652_lvs.log"; then
  echo '[FAIL] column_32 LVS did not match uniquely' >&2
  tail -40 "$COLUMN_DIR/column_32_p2652_lvs.log" >&2
  exit 1
fi
echo '[PASS] column_32 LVS: Circuits match uniquely'
