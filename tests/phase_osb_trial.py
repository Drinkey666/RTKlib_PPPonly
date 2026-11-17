"""Build, validate and replay the isolated phase-OSB candidate.

No production sources/objects/executables are replaced. Same inputs and model
parameters as the frozen Oct31 baseline; explicit RTK_PPP_PHASE_OSB OFF/ON.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv,gzip,hashlib,json,os,shutil,subprocess,sys,time
from run_oct31_reference_diagnosis import ROOT,CASES,CONFIG,sha,save,environment

OUT=ROOT/'validation/phase_osb_trial_v1'
BUILD=OUT/'build'
BASE=ROOT/'validation/observation_generation_2023_v1/pc_obj'
DEV='E:/Program Files/Microsoft Visual Studio/2022/Professional/Common7/Tools/VsDevCmd.bat'
FLAGS='/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS /DENAGLO /DNFREQ=4 /DWIN32 /DTRACE /DNDEBUG /DDLL /D_LIB'

def build():
    BUILD.mkdir(parents=True,exist_ok=False)
    original=(ROOT/'src/ppp.c').read_text(encoding='utf-8-sig')
    marker='static void corr_meas(const obsd_t* obs, const nav_t* nav, const double* azel,'
    phase='                - phw * CLIGHT / freq[i];'
    configure='    ppp_innovation_core_begin(rtk->nx,obs,n,opt->nf,rtk);'
    epoch='    nsmooth = uddoppsm_ppp(rtk, obs, n, nav, rs);'
    for m in [marker,phase,configure,epoch]:assert original.count(m)==1,m
    private=original.replace(marker,'#include "phase_osb_candidate.h"\n\n'+marker)
    private=private.replace(phase,'                - phw * CLIGHT / freq[i]\n                - posb_phase_correction(obs->time,obs->sat,obs->code[i]);')
    private=private.replace(configure,'    if(!posb_configure()) {rtk->ppp_failure=FILTER_NAN_INPUT;rtk->sol.stat=SOLQ_NONE;\n        trace(2,"$PPP_FAILURE,reason=PHASE_OSB_CONFIG,stage=PPP_ENTRY\\n");return;}\n'+configure)
    private=private.replace(epoch,'    posb_epoch(rtk,obs,n);\n'+epoch)
    source=BUILD/'ppp.c';source.write_text(private,encoding='utf-8')
    (BUILD/'phase_osb_candidate.h').write_bytes((ROOT/'tests/phase_osb_candidate.h').read_bytes())
    objects=sorted(BASE.glob('*.obj'));assert len(objects)==32
    identity={str(p):sha(p) for p in objects+list((ROOT/'src').glob('*.h'))+list((ROOT/'src').glob('*.c'))}
    save(BUILD/'source_before.json',identity)
    link=' '.join(f'"{p}"' for p in objects if p.name!='ppp.obj')
    command=BUILD/'build.cmd'
    command.write_text('@echo off\n'+f'call "{DEV}" -arch=x64 -host_arch=x64 >nul\n'
        f'cl {FLAGS} /I"{ROOT/"src"}" /I"{BUILD}" /c "{source}" /Fo"{BUILD/"ppp.obj"}"\n'
        'if errorlevel 1 exit /b 1\n'
        f'link /NOLOGO /OUT:"{BUILD/"trial.exe"}" "{BUILD/"ppp.obj"}" {link} winmm.lib ws2_32.lib comdlg32.lib user32.lib gdi32.lib\n',encoding='utf-8')
    with (BUILD/'build.log').open('wb') as log:r=subprocess.run(['cmd','/c',str(command)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert r.returncode==0,'Inspect build/build.log'
    assert all(sha(p)==h for p,h in identity.items())
    save(BUILD/'manifest.json',dict(returncode=0,exe_sha256=sha(BUILD/'trial.exe'),private_ppp_sha256=sha(source),
        header_sha256=sha(BUILD/'phase_osb_candidate.h'),ABI='unchanged; NFREQ4 ENAGLO no ENAQZS; v143 x64',
        reused_objects=31,model_defaults_unchanged=True))
    print('candidate build passed',flush=True)

def unit():
    folder=OUT/'unit';folder.mkdir(exist_ok=True)
    (folder/'validation/phase2').mkdir(parents=True,exist_ok=True)
    (folder/'ppp_estimator_under_test.c').write_bytes((BUILD/'ppp.c').read_bytes())
    (folder/'phase_osb_candidate.h').write_bytes((BUILD/'phase_osb_candidate.h').read_bytes())
    suites=['phase1','phase2','physical_atmosphere','rapppid_estimator','covariance_fix','phase_osb_candidate']
    names=['rtkcmn','trace','preceph','ephemeris','ionex','sbas','sofa','tides','pntpos','ppp_ar','ppp_position','smartphone_ppp_config','ppp_innovation_diag']
    objects=' '.join(f'"{BASE/(n+".obj")}"' for n in names)
    for suite in suites:
        text=(ROOT/'tests'/(suite+'_regression.c')).read_text(encoding='utf-8-sig')
        if suite=='phase1':text=text.replace('#include "../src/ppp.c"','#include "ppp_estimator_under_test.c"')
        (folder/(suite+'_regression.c')).write_text(text,encoding='utf-8')
    results={}
    for suite in suites:
        reference=f' "{ROOT/"tests/filter_reference_97a57a9.c"}"' if suite in ['phase1','phase2'] else ''
        command=folder/(suite+'.cmd')
        command.write_text('@echo off\n'+f'call "{DEV}" -arch=x64 -host_arch=x64 >nul\n'
            f'cl {FLAGS} /I"{ROOT/"src"}" /I"{folder}" /Fe"{folder/(suite+".exe")}" /Fo"{folder.as_posix()}/" "{folder/(suite+"_regression.c")}"{reference} {objects} /link /OPT:REF winmm.lib ws2_32.lib\n',encoding='utf-8')
        with (folder/(suite+'.build.log')).open('wb') as log:r=subprocess.run(['cmd','/c',str(command)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        assert r.returncode==0,f'{suite}: build failed'
        env={k:v for k,v in os.environ.items() if not k.startswith('RTK_PPP_')};env['RTK_PPP_PHASE_OSB']='OFF'
        r=subprocess.run([str(folder/(suite+'.exe'))],cwd=folder,env=env,capture_output=True)
        (folder/(suite+'.results.txt')).write_bytes(r.stdout+r.stderr)
        assert r.returncode==0,f'{suite}: test failed'
        results[suite]=r.stdout.decode(errors='replace').splitlines()[-1]
        save(folder/'results.json',results);print(suite,results[suite],flush=True)

def replay(case,mode,limit=None):
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'));files=dict(cfg['files'],TXT=str(CASES[case][0]))
    identity={k:dict(path=str(p),sha256=sha(p)) for k,p in files.items()}
    name=mode if limit is None else mode+f'_prefix{limit}'
    folder=OUT/case/name;folder.mkdir(parents=True,exist_ok=False)
    output=folder/'solution.csv';exe=BUILD/'trial.exe'
    env=environment(os.environ,files)
    env.update(RTK_PPP_OUTPUT=str(output),RTK_PPP_TRACE=str(folder/'solution.trace'),RTK_PPP_TRACE_LEVEL='2',
               RTK_PPP_PHASE_OSB=mode.upper(),RTK_PPP_PHASE_OSB_FILE=files['BIA'],RTK_PPP_PHASE_OSB_DIAG=str(folder/'phase_osb'))
    command=[str(exe),'--source','txt-fast','--no-gui']
    if limit:command+=['--max-epochs',str(limit)]
    receipt=dict(case=case,mode=mode,command=command,exe_sha256=sha(exe),inputs=identity,
        reference_used_in_filter=False,parameters='same B_VERIFIED; R/Q/P0/GIM and legacy QC thresholds unchanged')
    save(folder/'run.json',receipt)
    with (folder/'preflight.log').open('wb') as log:r=subprocess.run(command+['--check-files'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    receipt['preflight_returncode']=r.returncode;save(folder/'run.json',receipt);assert r.returncode==0
    print(case,mode,'started',flush=True);start=time.monotonic()
    with (folder/'console.log').open('wb') as log:r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    receipt.update(returncode=r.returncode,wall_seconds=time.monotonic()-start);save(folder/'run.json',receipt);assert r.returncode==0
    with output.open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==(limit or 3710)
    if mode=='off':
        with CASES[case][1].open() as f:expected=list(csv.DictReader(f))[:limit]
        assert len(rows)==len(expected)
        diff=[(i+1,k) for i,(a,b) in enumerate(zip(rows,expected)) for k in a if k!='processing_ms' and a[k]!=b[k]]
        assert not diff,diff[:10]
        receipt['baseline_fields_exact_except_processing_ms']=True
    receipt.update(completed=True,epochs=len(rows),Q=dict(__import__('collections').Counter(x['Q'] for x in rows)),solution_sha256=sha(output))
    receipt['compressed_logs']={}
    for p in [folder/'solution.trace',Path(str(output)+'.stat'),Path(str(output)+'.obs.csv')]:
        digest=sha(p);target=Path(str(p)+'.gz')
        with p.open('rb') as src,gzip.open(target,'wb',compresslevel=5) as dst:shutil.copyfileobj(src,dst)
        with gzip.open(target,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
        receipt['compressed_logs'][p.name]=dict(path=str(target),uncompressed_sha256=digest);p.unlink()
    assert all(sha(v['path'])==v['sha256'] for v in identity.values())
    save(folder/'run.json',receipt);print(case,mode,'completed',receipt['Q'],flush=True)

def pipeline(case):
    replay(case,'off');replay(case,'on')

if __name__=='__main__':
    stage=sys.argv[1]
    if stage=='build':build()
    elif stage=='unit':unit()
    elif stage=='prefix':
        replay('k70','off',120);replay('iq','off',120)
    elif stage=='replay':
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(pipeline,['k70','iq']))
    else:raise ValueError(stage)
