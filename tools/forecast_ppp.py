"""Forecast-only PC session gate. The existing PPP executable is not modified.

Run --check-files first, then verify prediction markers and hash-bound historical
receipt times. A successful audit permits --run; missing evidence never becomes
an implicit FIN fallback. All audit times are explicitly GPST.
"""
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
KEYS=('OBS','NAV','SP3','CLK','BIA','IONEX','VMF_FIRST','VMF_SECOND','OROGRAPHY','ATX')
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ppp_preset import PROFILE,environment

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def gpst(value):
    # Naive datetime intentionally denotes GPST, never Windows local/UTC time.
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?',value):
        raise ValueError('Expected YYYY-MM-DD HH:MM:SS[.ffffff] in GPST')
    return datetime.fromisoformat(value)

def native_window(report):
    line=next((s for s in report.splitlines() if s.startswith('PPP_CHECK,INFO,OBS,reason=LOADED,')),None)
    if not line:raise ValueError('Native preflight did not establish OBS time span')
    return tuple(datetime.strptime(re.search(k+r'=([^,]+)',line)[1],'%Y/%m/%d %H:%M:%S.%f') for k in ('start','end'))

def prediction_audit(path,begin,end,satellites):
    grid=[];flags=[];system=None
    with Path(path).open(encoding='ascii',errors='strict') as stream:
        for line in stream:
            if line.startswith('%c ') and system is None:system=line[9:12].strip()
            if line.startswith('*'):
                a=line[1:].split();epoch=datetime(*map(int,a[:5]))+timedelta(seconds=float(a[5]))
                if grid and epoch<=grid[-1]:raise ValueError('SP3 grid must be strictly increasing')
                grid.append(epoch);flags.append({})
            elif line.startswith('P') and grid:
                text=line.rstrip('\r\n').ljust(80)
                flags[-1][text[1:4].strip()]=(text[79],text[75])
    if system!='GPS':raise ValueError('Forecast gate currently supports explicit GPS SP3 time only')
    if not grid or begin<grid[0] or end>grid[-1]:raise ValueError('SP3 does not bracket observation span')
    if not satellites:raise ValueError('Native preflight reported no enabled satellites')
    first=max(0,bisect_right(grid,begin)-1);last=min(len(grid)-1,bisect_left(grid,end))
    counts=Counter();supported=set()
    for i in range(first,last+1):
        for sat in satellites:
            if sat not in flags[i]:continue  # actual missing-product handling remains native preflight/PPP
            orbit,clock=flags[i][sat];counts['orbit='+orbit+';sp3_clock='+clock]+=1;supported.add(sat)
    pure=bool(counts) and all(k=='orbit=P;sp3_clock=P' for k in counts)
    starts=[grid[i] for i in range(len(grid)) if any(o=='P' for o,c in flags[i].values())]
    start=min(starts) if starts else None
    return dict(predicted_bracketing_records_only=pure,time_system=system,counts=dict(counts),
        bracket_start=grid[first].isoformat(' '),bracket_end=grid[last].isoformat(' '),
        predicted_segment_start=start.isoformat(' ') if start else None,
        prediction_age_hours=(begin-start).total_seconds()/3600 if start else None,
        supported_satellites=sorted(supported),
        scope='Observation interval and bracketing SP3 records; does not require all interpolation nodes to be predicted. All file versions must already be available.')

def clock_pair(sp3,clk):
    # Restrict this initial workflow to actual WUM NRT family/issue matches.
    pattern=r'^(WUM0MGXNRT_\d{11})_'
    a=re.match(pattern,Path(sp3).name);b=re.match(pattern,Path(clk).name)
    header=[]
    with Path(clk).open(encoding='ascii',errors='strict') as f:
        for line in f:
            header.append(line.rstrip())
            if 'END OF HEADER' in line or len(header)>=512:break
    return dict(same_wum_nrt_issue=bool(a and b and a[1]==b[1]),
        extclk_declared=any('PANDA-EXTCLK' in s and 'PGM / RUN BY / DATE' in s for s in header),
        generation_header=next((s for s in header if 'PGM / RUN BY / DATE' in s),None),
        scope='Separate CLK has no per-record P flag. Inference requires matching WUM issue plus EXTCLK header and native time coverage; not a generic CLK forecast detector.')

def receipt_audit(files,availability,begin,hashes):
    rows=[]
    for key in KEYS[1:]:
        record=availability.get(key,{})
        reason=None;received=None
        try:received=gpst(record.get('received_gpst'))
        except (ValueError,TypeError):reason='RECEIPT_TIME_UNKNOWN'
        if not reason and record.get('sha256')!=hashes[key]:reason='RECEIPT_HASH_MISMATCH'
        if not reason and not record.get('evidence'):reason='RECEIPT_EVIDENCE_UNSPECIFIED'
        if not reason and received>begin:reason='FILE_RECEIVED_AFTER_OBSERVATION_START'
        rows.append(dict(product=key,status='FAIL' if reason else 'PASS',reason=reason or 'RECEIVED_BEFORE_START',
            received_gpst=received.isoformat(' ') if received else None,evidence=record.get('evidence')))
    return rows

def audit(files,availability,begin,end,satellites):
    hashes={key:digest(files[key]) for key in KEYS}
    prediction=prediction_audit(files['SP3'],begin,end,satellites)
    clock=clock_pair(files['SP3'],files['CLK'])
    receipts=receipt_audit(files,availability,begin,hashes)
    reasons=[]
    if not prediction['predicted_bracketing_records_only']:reasons.append('OBS_NOT_IN_PREDICTED_SEGMENT')
    if not clock['same_wum_nrt_issue'] or not clock['extclk_declared']:reasons.append('FORECAST_CLK_PROVENANCE_UNCONFIRMED')
    if any(r['status']!='PASS' for r in receipts):reasons.append('PRODUCT_AVAILABILITY_NOT_ESTABLISHED')
    return dict(status='BLOCKED' if reasons else 'PASS',reasons=reasons,sha256=hashes,
        observation_begin_gpst=begin.isoformat(' '),observation_end_gpst=end.isoformat(' '),
        prediction=prediction,clock=clock,availability=receipts,
        limits='Receipt assertions are supplied evidence, not independently authenticated publication timestamps. This entry fixes one initial product bundle; timed product replacement is not implemented.')

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path,help='JSON with files, availability, source and max_epochs')
    parser.add_argument('--run',action='store_true',help='Run formal B_VERIFIED only after all forecast/availability checks pass')
    args=parser.parse_args();m=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    if set(m.get('files',{}))!=set(KEYS):parser.error('files must contain exactly '+','.join(KEYS))
    if m.get('source','rinex') not in ('rinex','txt-fast'):parser.error('source must be rinex or txt-fast')
    files={k:str(Path(v).resolve(strict=True)) for k,v in m['files'].items()}
    max_epochs=m.get('max_epochs',0)
    if isinstance(max_epochs,bool) or not isinstance(max_epochs,int) or max_epochs<0:parser.error('max_epochs must be a nonnegative integer')
    if m.get('source','rinex')=='rinex' and max_epochs:
        parser.error('RINEX uses the supplied full file; max_epochs must be 0. Use a separate observation prefix file if required.')
    out=ROOT/'validation/forecast_sessions'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');out.mkdir(parents=True,exist_ok=False)
    exe=ROOT/'x64/Release/PPP_only.exe'
    env=environment(os.environ)
    env.update({'RTK_PPP_'+k:v for k,v in files.items()})
    if m.get('source','rinex')=='txt-fast':
        env['RTK_PPP_TXT']=env.pop('RTK_PPP_OBS')
    env.update(RTK_PPP_OUTPUT=str(out/'solution.pos'),RTK_PPP_TRACE=str(out/'solution.trace'))
    command=[str(exe),'--source',m.get('source','rinex'),'--no-gui']
    if max_epochs:command+=['--max-epochs',str(max_epochs)]
    with (out/'preflight.console.log').open('wb') as log:
        run=subprocess.run(command+['--check-files'],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    report=Path(str(out/'solution.pos')+'.products.log')
    text=report.read_text(encoding='utf-8',errors='replace') if report.exists() else ''
    (out/'native_preflight.products.log').write_text(text,encoding='utf-8')
    try:
        begin,end=native_window(text)
        satellites=set(re.findall(r'PPP_CHECK,(?:INFO|WARN),SATELLITE,reason=AVAILABILITY,sat=([A-Z]\d+)',text))
        result=audit(files,m.get('availability',{}),begin,end,satellites)
    except (ValueError,OSError) as e:
        result=dict(status='BLOCKED',reasons=['FORECAST_AUDIT_FAILED'],error=str(e))
    result.update(native_preflight_returncode=run.returncode,filter_started=False,profile=PROFILE,
        files=files,executable_sha256=digest(exe),manifest=str(args.manifest.resolve()))
    if run.returncode:
        result['status']='BLOCKED';result['reasons'].append('NATIVE_PREFLIGHT_FAILED')
    if args.run and result['status']=='PASS':
        if not all(digest(files[k])==h for k,h in result['sha256'].items()):
            result['status']='BLOCKED';result['reasons'].append('INPUT_CHANGED_AFTER_AUDIT')
        else:
            with (out/'solver.console.log').open('wb') as log:
                process=subprocess.run(command,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            result.update(filter_started=True,solver_returncode=process.returncode)
            if process.returncode:result['status']='SOLVER_FAILED'
    (out/'forecast_session.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],reasons=result['reasons'],filter_started=result['filter_started'],report=str(out/'forecast_session.json')),ensure_ascii=False))
    return 0 if result['status']=='PASS' else 2

if __name__=='__main__':raise SystemExit(main())
