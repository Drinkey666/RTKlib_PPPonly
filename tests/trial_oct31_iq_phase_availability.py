"""Offline causal control: remove K70 common-signal phases absent on paired IQ.

Keep K70 code, Doppler, B2a, timestamps and remaining phase values unchanged.
No reference position is used for action generation. Not a deployed algorithm.
"""
import csv, gzip, json, os, subprocess, time
from pathlib import Path
from collections import Counter
from run_oct31_reference_diagnosis import ROOT, OUT, CONFIG, CASES, sha, save, environment
from trial_oct31_b2a_availability import BASE

BUILD=OUT/'phase_mask_build'
HOOK=r'''
static void oct31_phase_mask(obsd_t *obs,int n) {
    static FILE *fp;static int initialized,have,w,code;static double tow;
    static char sat[8];int i,f,week,found;double now;char id[8];const char *path;
    if(!initialized){initialized=1;path=getenv("OCT31_PHASE_ACTIONS");
        if(!path || !*path)return;
        fp=fopen(path,"r");if(!fp)exit(EXIT_FAILURE);
        have=fscanf(fp,"%d %lf %7s %d",&w,&tow,sat,&code)==4;
    }
    if(!fp || n<=0)return;
    now=time2gpst(obs[0].time,&week);
    while(have && week==w && fabs(now-tow)<1e-6){
        found=0;
        for(i=0;i<n;i++){satno2id(obs[i].sat,id);if(strcmp(id,sat))continue;
            for(f=0;f<NFREQ;f++)if(obs[i].code[f]==code && obs[i].L[f]!=0.){
                obs[i].L[f]=0.;found=1;
            }
        }
        if(!found)exit(EXIT_FAILURE);
        trace(2,"$OCT31_PHASE_MASK,%d,%.9f,%s,%d\n",w,tow,sat,code);
        have=fscanf(fp,"%d %lf %7s %d",&w,&tow,sat,&code)==4;
    }
    if(have && (week>w || (week==w && now>tow+1e-6)))exit(EXIT_FAILURE);
}
'''

def observations(case):
    with gzip.open(OUT/case/'solution.csv.obs.csv.gz','rt',encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def prepare():
    BUILD.mkdir(exist_ok=False)
    a,b=observations('k70'),observations('iq')
    # Pair only observations at almost identical GNSS events; retain unmatched K70 epochs.
    iq_times=sorted({float(r['tow']) for r in b})
    import bisect
    iq={(float(r['tow']),r['sat'],r['signal']):float(r['L_cycle']) for r in b}
    mapping={}
    for t in sorted({float(r['tow']) for r in a}):
        j=bisect.bisect_left(iq_times,t);options=[x for x in (j-1,j) if 0<=x<len(iq_times)]
        k=min(options,key=lambda x:abs(iq_times[x]-t))
        if abs(iq_times[k]-t)<=.01:mapping[t]=iq_times[k]
    common={'G1C','G5Q','E1C','E5Q','C2I'}
    actions=[r for r in a if r['sat'][0]+r['signal'] in common and float(r['L_cycle'])!=0
        and float(r['tow']) in mapping and not iq.get((mapping[float(r['tow'])],r['sat'],r['signal']),0.)]
    actions.sort(key=lambda r:(int(r['week']),float(r['tow']),r['sat'],int(r['code'])))
    (BUILD/'actions.txt').write_text(''.join(f"{r['week']} {r['tow']} {r['sat']} {r['code']}\n" for r in actions),encoding='ascii')
    save(BUILD/'actions.json',dict(count=len(actions),by_signal=dict(Counter(r['sat'][0]+'_'+r['signal'] for r in actions)),
        max_pair_dt_s=max(abs(t-u) for t,u in mapping.items()),actions_sha256=sha(BUILD/'actions.txt'),
        reference_used=False,scope='K70 phase-only deletion on shared signal types missing in same-time IQ input; B2a unchanged.'))
    original=(ROOT/'src/gnss_replay.c').read_text(encoding='utf-8-sig')
    marker='static int process_txt_epoch(const android_clock_t *clock,'
    call='    double adapter_ms = monotonic_ms() - t0;'
    assert original.count(marker)==original.count(call)==1
    private=original.replace(marker,HOOK+'\n'+marker).replace(call,'    oct31_phase_mask(obs,nobs);\n'+call)
    source=BUILD/'gnss_replay.c';source.write_text(private,encoding='utf-8')
    objects=sorted(BASE.glob('*.obj'));assert len(objects)==32
    identities={str(p):sha(p) for p in objects+[ROOT/'src/gnss_replay.c',ROOT/'src/rtklib.h']}
    link=' '.join(f'"{p}"' for p in objects if p.name!='gnss_replay.obj')
    command=BUILD/'build.cmd'
    command.write_text('@echo off\ncall "E:/Program Files/Microsoft Visual Studio/2022/Professional/Common7/Tools/VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul\n'
        f'cl /nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS /DENAGLO /DNFREQ=4 /DWIN32 /DTRACE /DNDEBUG /DDLL /D_LIB /DGNSS_REPLAY_EMBEDDED /I"{ROOT/"src"}" /c "{source}" /Fo"{BUILD/"gnss_replay.obj"}"\n'
        'if errorlevel 1 exit /b 1\n'
        f'link /NOLOGO /OUT:"{BUILD/"trial.exe"}" "{BUILD/"gnss_replay.obj"}" {link} winmm.lib ws2_32.lib comdlg32.lib user32.lib gdi32.lib\n',encoding='utf-8')
    with (BUILD/'build.log').open('wb') as log:
        result=subprocess.run(['cmd','/c',str(command)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0
    save(BUILD/'build.json',dict(returncode=0,unchanged_objects_and_sources=identities,
         private_source_sha256=sha(source),exe_sha256=sha(BUILD/'trial.exe')))
    assert all(sha(p)==h for p,h in identities.items())

def run(name,active=False,limit=None):
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'));folder=OUT/name;folder.mkdir(exist_ok=False)
    files=dict(cfg['files'],TXT=str(CASES['k70'][0]));env=environment(os.environ,files)
    env.pop('OCT31_PHASE_ACTIONS',None)
    if active:env['OCT31_PHASE_ACTIONS']=str(BUILD/'actions.txt')
    solution=folder/'solution.csv'
    env.update(RTK_PPP_OUTPUT=str(solution),RTK_PPP_TRACE=str(folder/'solution.trace'),RTK_PPP_TRACE_LEVEL='2')
    command=[str(BUILD/'trial.exe'),'--source','txt-fast','--no-gui']
    if limit:command+=['--max-epochs',str(limit)]
    start=time.monotonic()
    with (folder/'console.log').open('wb') as log:r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    receipt=dict(command=command,returncode=r.returncode,wall_seconds=time.monotonic()-start,active=active,
        reference_used_in_filter=False,exe_sha256=sha(BUILD/'trial.exe'))
    save(folder/'run.json',receipt);assert r.returncode==0
    with solution.open() as f:rows=list(csv.DictReader(f))
    if not active:
        with CASES['k70'][1].open() as f:expected=list(csv.DictReader(f))[:limit]
        assert len(rows)==len(expected) and all(all(a[k]==b[k] for k in a if k!='processing_ms') for a,b in zip(rows,expected))
        receipt['control_exact_except_processing_ms']=True
    else:
        assert len(rows)==3710
        expected=observations('k70')
        with open(str(solution)+'.obs.csv',encoding='utf-8-sig') as f:actual=list(csv.DictReader(f))
        assert len(actual)==len(expected)
        changes=0
        for a,b in zip(actual,expected):
            assert all(a[k]==b[k] for k in a if k!='L_cycle')
            if a['L_cycle']!=b['L_cycle']:
                assert float(a['L_cycle'])==0. and float(b['L_cycle'])!=0.;changes+=1
        actions=json.loads((BUILD/'actions.json').read_text(encoding='utf-8'))
        assert changes==actions['count']
        receipt['phase_only_deletions_verified']=changes
    receipt.update(completed=True,epochs=len(rows),solution_sha256=sha(solution))
    import shutil,hashlib
    for p in [folder/'solution.trace',Path(str(solution)+'.stat'),Path(str(solution)+'.obs.csv')]:
        digest=sha(p);target=Path(str(p)+'.gz')
        with p.open('rb') as src,gzip.open(target,'wb',compresslevel=5) as dst:shutil.copyfileobj(src,dst)
        with gzip.open(target,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
        p.unlink()
    save(folder/'run.json',receipt);print(name,json.dumps(receipt),flush=True)

if __name__=='__main__':
    prepare()
    run('phase_mask_control120',limit=120)
    run('k70_iq_phase_gaps',active=True)
