#!/usr/bin/env python3
"""Run the archived C250 observers with all eight lanes classified StrongARM."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

import numpy as np

if not hasattr(np, "trapezoid"):
    # NumPy 1.x names the same composite trapezoidal integrator trapz.
    np.trapezoid = np.trapz
if not hasattr(hashlib, "file_digest"):
    def file_digest(stream, digest, /, *, _bufsize=2**18):
        result = hashlib.new(digest)
        for block in iter(lambda: stream.read(_bufsize), b""):
            result.update(block)
        return result
    hashlib.file_digest = file_digest


ROOT = Path(__file__).resolve().parents[1]
TRIPLE = ROOT / "build/phase3/strongarm_triple_20261122"
sys.path.insert(0, str(TRIPLE))

import analyze_triple  # noqa: E402


def main(run: Path) -> None:
    analyze_triple.BITS = tuple(range(8))
    analyze_triple.main(run)
    sys.path.insert(0, str(ROOT / "build/phase3/strongarm_functional_closure_20261122"))
    import closure_prepare  # noqa: E402
    closure_prepare.FF = run
    import qualify_c250  # noqa: E402
    qualify_c250.summarize(run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    main(parser.parse_args().run)
