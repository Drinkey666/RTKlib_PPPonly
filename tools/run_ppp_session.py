"""Recorded B_VERIFIED PC replay, with a separate opt-in recovery executable.
Historical/archive replay is not certification of real-time product availability.
The existing forecast_ppp.py entry retains its strict receipt/prediction gate.
"""
import argparse,csv,json,os,subprocess,sys,hashlib
from datetime import datetime
from pathlib import Path
from ppp_preset import ROOT,PATH,PROFILE,environment
from forecast_ppp import clock_pair

PRODUCTS={'NAV','SP3','CLK','BIA','IONEX','VMF_FIRST','VMF_SECOND','OROGRAPHY','ATX'}

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def plan(manifest,output,recovery=False,parent=None):
    source=manifest.get('source','rinex')
    if source not in ('rinex','txt-fast','txt-realtime'):raise ValueError('Unknown observation source')
    if manifest.get('max_epochs',0)!=0 or isinstance(manifest.get('max_epochs',0),bool):
        raise ValueError('This recorded entry processes the complete file; max_epochs must be integer 0')
    if set(manifest)-{'source','files','usage','note','max_epochs','availability'}:
        raise ValueError('Unknown manifest fields; model/threshold/truth overrides are not allowed')
    if manifest.get('usage') not in (None,'ARCHIVED_REGRESSION'):
        raise ValueError('For strict availability-certified forecast use forecast_ppp.py; do not rename archived replay as live')
    files=manifest.get('files',{})
    expected=PRODUCTS|({'OBS'} if source=='rinex' else {'TXT'})
    if set(files)!=expected:raise ValueError('files must contain exactly '+','.join(sorted(expected)))
    if 'profile' in manifest or 'environment' in manifest:raise ValueError('Model overrides are not allowed in a file manifest')
    paths={k:str(Path(v).resolve(strict=True)) for k,v in files.items()}
    if any(not Path(v).is_file() for v in paths.values()):raise ValueError('Inputs must be files')
    pair=clock_pair(paths['SP3'],paths['CLK'])
    archived=manifest.get('usage')=='ARCHIVED_REGRESSION'
    if not pair['same_wum_nrt_issue'] or (not pair['extclk_declared'] and not archived):
        raise ValueError('This entry requires matching WUM NRT SP3/EXTCLK forecast products; no FIN fallback')
    output=Path(output).resolve()
    targets=[output,output.with_name(output.stem+'_events.pos')]
    targets += [Path(str(output)+s) for s in ['.stat','.trace','.products.log','.session.json','.console.log','.obs.csv','.stat.gz','.trace.gz','.obs.csv.gz']]
    for p in targets:
        if p.exists():raise ValueError('Refuse to overwrite existing output: '+str(p))
        if str(p).lower() in {s.lower() for s in paths.values()}:raise ValueError('Output overlaps an input')
    exe=ROOT/('validation/recovery_session/build/trial.exe' if recovery else 'x64/Release/PPP_only.exe')
    if not exe.is_file():raise ValueError('Build required executable: '+str(exe))
    env=environment(os.environ if parent is None else parent,paths,recovery)
    env.update(RTK_PPP_OUTPUT=str(output),RTK_PPP_TRACE=str(output)+'.trace',RTK_PPP_TRACE_LEVEL='2')
    return dict(source=source,executable=str(exe),output=str(output),files=paths,profile=dict(PROFILE),recovery='BRIDGE3_SESSION' if recovery else 'OFF',
      executable_sha256=sha(exe),preset_sha256=sha(PATH),input_sha256={k:sha(p) for k,p in paths.items()},clock_forecast_provenance=pair,
      usage='ARCHIVED_REGRESSION' if archived else 'ARCHIVED_REPLAY_EXTCLK_HEADER_ONLY',
      command=[str(exe),'--source',source,'--no-gui']),env

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--recovery-trial',action='store_true');ap.add_argument('--prepare-only',action='store_true')
    a=ap.parse_args()
    try:r,env=plan(json.loads(a.manifest.read_text(encoding='utf-8-sig')),a.output,a.recovery_trial)
    except (ValueError,OSError) as e:ap.error(str(e))
    r.update(status='PREPARED',filter_started=False,availability='ARCHIVED_REPLAY_NOT_HISTORICAL_AVAILABILITY_CERTIFICATION',
       created_local=datetime.now().isoformat(),manifest=str(a.manifest.resolve()),native_preflight='performed inside native entry before filtering')
    if a.prepare_only:print(json.dumps(r,ensure_ascii=False,indent=2));return 0
    a.output.parent.mkdir(parents=True,exist_ok=True);receipt=Path(r['output']+'.session.json')
    def save():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    with receipt.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
    if not all(sha(p)==r['input_sha256'][k] for k,p in r['files'].items()):raise RuntimeError('Input changed before launch')
    with Path(r['output']+'.console.log').open('xb') as log:
        process=subprocess.run(r['command'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    r.update(returncode=process.returncode,status='NATIVE_FAILED' if process.returncode else 'COMPLETE')
    configs=[]
    trace=Path(r['output']+'.trace')
    if trace.is_file():
        with trace.open(encoding='utf-8',errors='replace') as f:
            for line in f:
                if 'PPP_CONFIG,' in line:configs.append(line.split('PPP_CONFIG,',1)[1].strip())
                if len(configs)>=2:break
    r['effective_native_config']=configs
    actual=Path(r['output'])
    r['filter_started']=False
    if actual.is_file():
        if r['source']=='rinex':
            data=[s.split() for s in actual.read_text(encoding='utf-8',errors='replace').splitlines() if s.strip() and not s.startswith('%')]
            r['epochs']=len(data);r['filter_started']=bool(data)
            from collections import Counter
            r['Q']=dict(Counter(s[5] for s in data))
        else:
            with actual.open(encoding='utf-8-sig') as f:data=list(csv.DictReader(f))
            r['epochs']=len(data);r['filter_started']=bool(data)
    r['inputs_unchanged']=all(sha(p)==r['input_sha256'][k] for k,p in r['files'].items())
    r['executable_unchanged']=sha(r['executable'])==r['executable_sha256']
    r['preset_unchanged']=sha(PATH)==r['preset_sha256']
    if process.returncode==0 and (not configs or not any('repairs=B_VERIFIED_v2' in s and 'covariance=JOSEPH_B_MASK' in s for s in configs)):
        r['status']='CONFIG_UNVERIFIED'
    if process.returncode==0 and not r.get('epochs',0):r['status']='NO_SOLUTION'
    if not r['inputs_unchanged'] or not r['executable_unchanged'] or not r['preset_unchanged']:r['status']='IDENTITY_CHANGED'
    r['outputs']={str(p):sha(p) for p in [actual,trace,Path(str(actual)+'.stat'),Path(str(actual)+'.products.log'),Path(str(actual)+'.obs.csv')] if p.is_file()}
    save();print(json.dumps(dict(status=r['status'],epochs=r.get('epochs',0),receipt=str(receipt)),ensure_ascii=False))
    return 0 if r['status']=='COMPLETE' else 2

if __name__=='__main__':raise SystemExit(main())
