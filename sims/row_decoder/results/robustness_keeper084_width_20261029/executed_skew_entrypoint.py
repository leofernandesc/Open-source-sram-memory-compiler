#!/usr/bin/env python3
"""Exercise SF/FS skew corners to expose keeper/evaluation contention."""
import json
from pathlib import Path
import sys
import run_decoder_robustness as study


if __name__=='__main__':
    for corner in ('sf','fs'):
        for vdd in (1.62,1.8):
            for temperature in (-40,27,125):
                study.POINTS[f'{corner}_{vdd:g}_{temperature:g}']=(corner,vdd,temperature)
    result=study.main()
    # The main runner records the full selected PVT tuples and native decks.
    # Bind this entrypoint too, since it extends the exposed profile inventory.
    out=Path(sys.argv[sys.argv.index('--output-dir')+1])
    path=out/'manifest.json';manifest=json.loads(path.read_text())
    manifest['skew_entrypoint_sha256']=study.pair.sha(Path(__file__))
    (out/'executed_skew_entrypoint.py').write_bytes(Path(__file__).read_bytes())
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    raise SystemExit(result)
