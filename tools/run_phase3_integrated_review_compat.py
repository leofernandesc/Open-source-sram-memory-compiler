#!/usr/bin/env python3
"""Run the archived integrated observer on Python 3.10 / NumPy 1.26."""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "build/phase3/strongarm_functional_closure_20261122"
TRIPLE = ROOT / "build/phase3/strongarm_triple_20261122"
for directory in (ROOT / "tools", TRIPLE, CLOSURE):
    sys.path.insert(0, str(directory))
if not hasattr(hashlib, "file_digest"):
    def file_digest(stream, name):
        digest = hashlib.new(name)
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        return digest
    hashlib.file_digest = file_digest
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz
from integrated_review import analyze
print(analyze(Path(sys.argv[1])))
