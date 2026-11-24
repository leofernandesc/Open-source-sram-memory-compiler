#!/usr/bin/env python3
"""Prepare archived integrated fixtures on Python 3.10."""
from __future__ import annotations
import hashlib
import runpy
import sys
from pathlib import Path

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
sys.argv = ["integrated_deck.py", *sys.argv[1:]]
runpy.run_path(str(CLOSURE / "integrated_deck.py"), run_name="__main__")
