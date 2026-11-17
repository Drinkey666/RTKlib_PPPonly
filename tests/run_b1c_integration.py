"""Validate simultaneous B1I/B1C on existing Oct31 data; no Q alias or tuning."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv,gzip,json,os,shutil,subprocess,sys,time
from run_oct31_reference_diagnosis import ROOT,CASES,CONFIG,environment,sha,save
OUT=ROOT/'validation/b1i_b1c_integration_v1'
EXE=OUT/'pc_build/PPP_only.exe'

def bridge():
    import trial_oct31_b2a_availability as t
    t.OUT=OUT;t.BUILD=OUT/'control_bridge';t.BASE=OUT/'pc_obj';t.TRIAL=t.BUILD/'trial.exe';t.build()
    save(OUT/'bridge_manifest.json',dict(exe_sha256=sha(t.TRIAL),purpose='Expose existing C:1P ablation for control; rest of solver unchanged'))

def replay(device,control=False,limit=None,atx=None):
    config=json.loads(CONFIG.read_text(encoding='utf-8'));files=dict(config['files'],TXT=str(CASES[device][0]))
    if atx:files['ATX']=str(atx)
    name=device+('_without_b1c' if control else '_with_b1c')+(f'_prefix{limit}' if limit else '')+('_new_atx' if atx else '')
    folder=OUT/name;folder.mkdir(exist_ok=False);output=folder/'solution.csv'
    exe=OUT/'control_bridge/trial.exe' if control else EXE
    env=environment(os.environ,files);env.pop('OCT31_EXCLUDE_RAW_SIGNAL',None);env.pop('RTK_PPP_IQ_B2AQ_PHASE',None)
    env.update(RTK_PPP_OUTPUT=str(output),RTK_PPP_TRACE=str(folder/'solution.trace'),RTK_PPP_TRACE_LEVEL='2')
    if control:env['OCT31_EXCLUDE_RAW_SIGNAL']='C:1P'
    command=[str(exe),'--source','txt-fast','--no-gui']
    if limit:command+=['--max-epochs',str(limit)]
    identity={k:dict(path=str(p),sha256=sha(p)) for k,p in files.items()}
    receipt=dict(device=device,mode='without_b1c' if control else 'with_b1c',command=command,
        executable_sha256=sha(exe),inputs=identity,reference_used_in_filter=False,IQ_Q_alias=False,B2b_enabled=False,phase_OSB_enabled=False)
    save(folder/'run.json',receipt)
    with (folder/'preflight.log').open('wb') as f:r=subprocess.run(command+['--check-files'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    receipt['preflight_returncode']=r.returncode;save(folder/'run.json',receipt);assert r.returncode==0
    start=time.monotonic();print(name,'started',flush=True)
    with (folder/'console.log').open('wb') as f:r=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
    receipt.update(returncode=r.returncode,wall_seconds=time.monotonic()-start);save(folder/'run.json',receipt);assert r.returncode==0
    with output.open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==(limit or 3710),(name,len(rows))
    if control and not atx:
        with CASES[device][1].open() as f:expected=list(csv.DictReader(f))[:limit]
        diff=[(i+1,k) for i,(a,b) in enumerate(zip(rows,expected)) for k in a if k!='processing_ms' and a[k]!=b[k]]
        assert len(expected)==len(rows) and not diff,diff[:10];receipt['baseline_exact_except_processing_ms']=True
    receipt.update(completed=True,epochs=len(rows),Q=dict(__import__('collections').Counter(x['Q'] for x in rows)),solution_sha256=sha(output),compressed_logs={})
    for p in [folder/'solution.trace',Path(str(output)+'.stat'),Path(str(output)+'.obs.csv')]:
        digest=sha(p);target=Path(str(p)+'.gz')
        with p.open('rb') as src,gzip.open(target,'wb',compresslevel=5) as dst:shutil.copyfileobj(src,dst)
        with gzip.open(target,'rb') as f:assert __import__('hashlib').file_digest(f,'sha256').hexdigest()==digest
        receipt['compressed_logs'][p.name]=dict(path=str(target),uncompressed_sha256=digest);p.unlink()
    assert all(sha(v['path'])==v['sha256'] for v in identity.values())
    save(folder/'run.json',receipt);print(name,'completed',receipt['Q'],receipt['wall_seconds'],flush=True)

if __name__=='__main__':
    stage=sys.argv[1]
    if stage=='bridge':bridge()
    elif stage=='controls':
        for device in CASES:replay(device,control=True,limit=120)
    elif stage=='replay':
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(replay,CASES))
    else:raise ValueError(stage)
