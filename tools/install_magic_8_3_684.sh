#!/usr/bin/env bash
set -euo pipefail

readonly version="8.3.684"
readonly prefix="/opt/magic/${version}"
readonly source_url="https://opencircuitdesign.com/magic/archive/magic-${version}.tgz"

if [[ "${EUID}" -ne 0 ]]; then
    printf 'Run this script as root inside the sram-xschem container.\n' >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    printf 'This installer expects the Debian/Ubuntu-based project container.\n' >&2
    exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl m4 python3 \
    libx11-dev tcl-dev tk-dev libcairo2-dev zlib1g-dev libncurses-dev

build_dir="$(mktemp -d "/tmp/magic-${version}.XXXXXX")"
trap 'rm -rf "$build_dir"' EXIT

archive="${build_dir}/magic-${version}.tgz"
curl --fail --location --retry 3 --output "$archive" "$source_url"
tar -xzf "$archive" -C "$build_dir"

cd "${build_dir}/magic-${version}"
./configure --prefix="$prefix"
make
make install

magic_bin="${prefix}/bin/magic"
if [[ ! -x "$magic_bin" ]]; then
    printf 'Expected Magic executable was not installed: %s\n' "$magic_bin" >&2
    exit 1
fi

version_output="$("$magic_bin" --version 2>&1)"
if [[ "$version_output" != *"${version}"* ]]; then
    printf 'Unexpected Magic version output: %s\n' "$version_output" >&2
    exit 1
fi

{
    printf 'Magic version: %s\n' "$version_output"
    printf 'Source URL: %s\n' "$source_url"
    printf 'Source archive SHA-256: '
    sha256sum "$archive" | awk '{print $1}'
    printf 'Executable: %s\n' "$magic_bin"
    printf 'Executable SHA-256: '
    sha256sum "$magic_bin" | awk '{print $1}'
} | tee "${prefix}/BUILD-INFO.txt"

printf '\nInstalled Magic %s. Select it by prepending %s/bin to PATH.\n' \
    "$version" "$prefix"
