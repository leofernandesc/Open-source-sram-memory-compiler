"""Bounded local resource preflight, without stopping services or deleting data."""
import os
from pathlib import Path
import shutil


def preflight(root,minimum_disk_mb=512,minimum_memory_mb=1024):
    memory={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1);memory[key]=int(value.strip().split()[0])*1024
    disk=shutil.disk_usage(root)
    result={'available_memory_mb':round(memory['MemAvailable']/2**20),
            'free_disk_mb':round(disk.free/2**20),'logical_cpus':os.cpu_count(),
            'swap_total_mb':round(memory.get('SwapTotal',0)/2**20),
            'swap_free_mb':round(memory.get('SwapFree',0)/2**20),
            'thread_limit':1,'minimum_disk_mb':minimum_disk_mb,'minimum_memory_mb':minimum_memory_mb}
    if disk.free<minimum_disk_mb*2**20 or memory['MemAvailable']<minimum_memory_mb*2**20:
        raise ValueError('Resource preflight failed; preserve results and use another machine: '+str(result))
    return result


if __name__=='__main__':
    import json
    print(json.dumps(preflight(Path(__file__).resolve().parents[1]),sort_keys=True))
