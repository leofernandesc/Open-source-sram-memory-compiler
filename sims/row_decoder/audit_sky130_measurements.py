#!/usr/bin/env python3
"""Pin and audit independent SKY130 MDM measurements without inferring missing metadata."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

COMMIT='1f7214f2f81a0629303947a07e1ec00a28ae8a33'
TREE='3a541a65f1c09567b32cf957d04ca8b281d44e95'
REPO='google/skywater-pdk-sky130-raw-data'


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(data):return hashlib.sha256(data).hexdigest()


def git_blob_sha(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def download(url):
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'SRAM-measurement-coverage-audit'})
            return urllib.request.urlopen(request,timeout=30).read()
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)


def geometry(name):
    match=re.search(r'_(nfet|pfet)_01v8_w([\dp.]+)u_l([\dp.]+)u_m(\d+)\(',name)
    require(match is not None,f'No nominal geometry: {name}')
    return dict(kind='n' if match[1]=='nfet' else 'p',w_um=float(match[2].replace('p','.')),
                l_um=float(match[3].replace('p','.')),multiplicity_label=int(match[4]))


def parse_mdm(text):
    """Read each DB's named columns and fixed biases; never assume column order."""
    defaults={};inside_header=False;records=[];constants={};columns=None;inside_db=False
    for number,line in enumerate(text.splitlines(),1):
        value=line.strip();parts=value.split()
        if value=='BEGIN_HEADER':inside_header=True;continue
        if value=='END_HEADER':inside_header=False;continue
        if inside_header:
            if 'CON' in parts and parts[0].upper() in ('VG','VD','VS','VB'):
                defaults[parts[0].upper()]=float(parts[parts.index('CON')+1])
            continue
        if value=='BEGIN_DB':
            require(not inside_db,'Nested MDM database')
            inside_db=True;constants=dict(defaults);columns=None;continue
        if value=='END_DB':inside_db=False;continue
        if not inside_db or not value or value.startswith('!'):continue
        if parts[0]=='ICCAP_VAR':constants[parts[1].upper()]=float(parts[2]);continue
        if value.startswith('#'):
            columns=value[1:].split();columns=[v.upper() for v in columns];continue
        require(columns is not None and len(parts)==len(columns),f'Unexpected MDM row at line {number}')
        row={**constants,**{k:float(v) for k,v in zip(columns,parts)}}
        require(all(k in row for k in ('VG','VD','VS','VB','ID')),f'Missing measured variable at line {number}')
        require(all(math.isfinite(v) for v in row.values()),f'Nonfinite measured row at {number}')
        require(max(abs(row[k]) for k in ('VG','VD','VS','VB'))<=5,'Unexpected core-device bias')
        row.update(VGS=row['VG']-row['VS'],VDS=row['VD']-row['VS'],VBS=row['VB']-row['VS'])
        records.append(row)
    require(records and not inside_db,'Empty or incomplete measurement database')
    return records


def write_csv(path,records):
    require(bool(records),'Empty audit CSV')
    keys=list(dict.fromkeys(k for r in records for k in r))
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=keys);writer.writeheader();writer.writerows(records)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache-dir',type=Path,default=Path.home()/'.cache/sram-characterization/sky130_raw_data_20261029')
    p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args();out=args.output_dir
    require(not out.exists(),'Use a new output directory')
    url=f'https://api.github.com/repos/{REPO}/git/trees/{TREE}?recursive=1'
    tree_data=download(url);tree=json.loads(tree_data)
    require(not tree.get('truncated'),'Incomplete upstream inventory')
    entries=[r for r in tree['tree'] if r['type']=='blob' and re.match(r'^sky130_fd_pr/cells/[np]fet_01v8/[^/]+\.mdm$',r['path'])]
    ancillary=['LICENSE','README.rst','docs/sky130-testtile-proprietary/README.rst',
               'docs/sky130-testtile-proprietary/sky130-testtile-pad-documentation.csv']
    entries.extend(next(r for r in tree['tree'] if r['path']==name) for name in ancillary)
    require(len(entries)==212,'Upstream pinned inventory differs from expected 208 MDM + four source documents')
    out.mkdir(parents=True);(out/'tree.json').write_bytes(tree_data)
    manifest=dict(status='DOWNLOADING',complete=False,repository=REPO,commit_sha=COMMIT,tree_sha=TREE,
                  api_url=url,tree_sha256=sha(tree_data),files=[])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    def obtain(item):
        relative=Path(item['path']);require('..' not in relative.parts and not relative.is_absolute(),'Unsafe upstream path')
        cache=args.cache_dir/relative
        data=cache.read_bytes() if cache.exists() else None
        source=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/'+urllib.parse.quote(item['path'])
        if data is None or git_blob_sha(data)!=item['sha']:data=download(source)
        require(git_blob_sha(data)==item['sha'],f'Upstream blob/hash mismatch: {relative}')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(data)
        target=out/'upstream'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        return dict(path=item['path'],git_blob_sha=item['sha'],sha256=sha(data),bytes=len(data),url=source)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(obtain,item) for item in entries]
        for future in as_completed(futures):
            manifest['files'].append(future.result())
            if len(manifest['files'])%40==0:print('Verified upstream files',len(manifest['files']),flush=True)
    manifest['files'].sort(key=lambda r:r['path'])
    audits=[];off_rows=[];zero_rows=[]
    for item in manifest['files']:
        if not item['path'].endswith('.mdm'):continue
        geom=geometry(item['path']);records=parse_mdm((out/'upstream'/item['path']).read_text())
        audit=dict(file=item['path'],**geom,rows=len(records),temperature_c='UNKNOWN_NOT_IN_MDM_HEADER')
        for bias in ('VGS','VDS','VBS'):
            audit[bias.lower()+'_min_v']=min(r[bias] for r in records)
            audit[bias.lower()+'_max_v']=max(r[bias] for r in records)
        audit['nfet_negative_vgs_rows']=sum(r['VGS']<0 for r in records) if geom['kind']=='n' else 0
        audit['pfet_positive_vgs_rows']=sum(r['VGS']>0 for r in records) if geom['kind']=='p' else 0
        audit['abs_id_max_a']=max(abs(r['ID']) for r in records)
        audits.append(audit)
        # Only nominal m=1 records support the single-device envelope used below.
        # Larger m labels are retained but not assumed to document array wiring.
        if geom['multiplicity_label']==1:
            for row in records:
                entry=dict(file=item['path'],**geom,**row)
                if abs(row['VGS'])<=1e-12:off_rows.append(entry)
                if max(abs(row[b]) for b in ('VGS','VDS','VBS'))<=1e-12:zero_rows.append(entry)
    write_csv(out/'file_coverage.csv',audits)
    write_csv(out/'single_device_vgs_zero.csv',off_rows)
    write_csv(out/'single_device_zero_bias_residuals.csv',zero_rows)
    coverage={}
    for kind in ('n','p'):
        group=[r for r in audits if r['kind']==kind]
        off=[r for r in off_rows if r['kind']==kind and abs(r['l_um']-0.15)<1e-9]
        zero=[r for r in zero_rows if r['kind']==kind and abs(r['l_um']-0.15)<1e-9]
        coverage[kind]=dict(files=len(group),rows=sum(r['rows'] for r in group),
            vgs_min_v=min(r['vgs_min_v'] for r in group),vgs_max_v=max(r['vgs_max_v'] for r in group),
            reverse_gate_rows=sum(r['nfet_negative_vgs_rows']+r['pfet_positive_vgs_rows'] for r in group),
            zero_vgs_l015_single_rows=len(off),zero_bias_l015_single_rows=len(zero),
            zero_vgs_abs_id_max_a=max(abs(r['ID']) for r in off),
            zero_bias_abs_id_max_a=max(abs(r['ID']) for r in zero),
            metadata_limit='Temperature/corner and complete physical test-tile layout are not established by these MDM records.')
    manifest.update(status='MEASURED_COVERAGE_AUDIT',complete=True,files_count=len(manifest['files']),
        mdm_files=len(audits),coverage=coverage,
        finding='The pinned measured gate-bias coverage does not establish accuracy for the decoder negative-NFET/positive-PFET VGS states.',
        current_interpretation='Observed VGS=0 and zero-bias residuals are not certified leakage or instrument-noise bounds. No m>1 per-device normalization is used.',
        script_sha256=sha(Path(__file__).read_bytes()))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(coverage,indent=2))


if __name__=='__main__':main()
