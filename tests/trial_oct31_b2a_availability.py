"""Private CLI bridge exposing the replay's existing raw-signal exclusion option."""
from pathlib import Path
import csv, gzip, hashlib, json, os, shutil, subprocess, sys, time
from run_oct31_reference_diagnosis import ROOT, OUT, CONFIG, EXE, CASES, environment, sha, save

BUILD = OUT / 'b2a_build'
BASE = ROOT / 'validation/observation_generation_2023_v1/pc_obj'
TRIAL = BUILD / 'trial.exe'

def build():
    BUILD.mkdir(parents=True, exist_ok=False)
    source = ROOT/'src/pc_txt_replay.c'
    original = source.read_text(encoding='utf-8-sig')
    marker = '    if (max_epochs) ARG("--max-epochs", limit);'
    assert original.count(marker) == 1
    injected = ('    /* Explicit private diagnostic only; default bridge arguments unchanged. */\n'
                '    { const char *excluded=getenv("OCT31_EXCLUDE_RAW_SIGNAL");\n'
                '      if(excluded && *excluded) ARG("--exclude-raw-signal",excluded); }\n')
    modified = original.replace('char *args[48];', 'char *args[52];').replace(marker,injected+marker)
    private = BUILD/'pc_txt_replay.c'
    private.write_text(modified,encoding='utf-8')
    objects=sorted(BASE.glob('*.obj'))
    assert len(objects)==32 and any(p.name=='pc_txt_replay.obj' for p in objects)
    link=' '.join(f'"{p}"' for p in objects if p.name!='pc_txt_replay.obj')
    command=BUILD/'build.cmd'
    command.write_text('@echo off\ncall "E:/Program Files/Microsoft Visual Studio/2022/Professional/Common7/Tools/VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul\n'
        f'cl /nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS /DENAGLO /DNFREQ=4 /DWIN32 /DTRACE /DNDEBUG /DDLL /D_LIB /I"{ROOT/"src"}" /c "{private}" /Fo"{BUILD/"pc_txt_replay.obj"}"\n'
        'if errorlevel 1 exit /b 1\n'
        f'link /NOLOGO /OUT:"{TRIAL}" "{BUILD/"pc_txt_replay.obj"}" {link} winmm.lib ws2_32.lib comdlg32.lib user32.lib gdi32.lib\n',encoding='utf-8')
    identities={str(p):sha(p) for p in objects+[source,ROOT/'src/rtklib.h',ROOT/'src/gnss_replay.c',ROOT/'src/gnss_adapter.c',ROOT/'src/ppp.c',ROOT/'src/rtkcmn.c',EXE]}
    with (BUILD/'build.log').open('wb') as log:
        result=subprocess.run(['cmd','/c',str(command)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    save(BUILD/'build.json',dict(returncode=result.returncode,private_source_sha256=sha(private),
         source_before=identities,compiler_layout='NFREQ=4; ENAGLO; no ENAQZS; v143/x64; original fixed-clock objects',
         scope='Only private pc_txt_replay bridge; existing exclusion before adapter; production/core unchanged.'))
    assert result.returncode==0
    assert all(sha(p)==h for p,h in identities.items())

def run(name,excluded=None,limit=None,device='k70'):
    config=json.loads(CONFIG.read_text(encoding='utf-8'))
    files=dict(config['files'],TXT=str(CASES[device][0]))
    folder=OUT/name;folder.mkdir(exist_ok=False)
    solution=folder/'solution.csv'
    env=environment(os.environ,files)
    env.pop('OCT31_EXCLUDE_RAW_SIGNAL',None)
    env.update(RTK_PPP_OUTPUT=str(solution),RTK_PPP_TRACE=str(folder/'solution.trace'),RTK_PPP_TRACE_LEVEL='2')
    if excluded:env['OCT31_EXCLUDE_RAW_SIGNAL']=excluded
    command=[str(TRIAL),'--source','txt-fast','--no-gui']
    if limit:command+=['--max-epochs',str(limit)]
    start=time.monotonic()
    with (folder/'console.log').open('wb') as log:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    receipt=dict(command=command,returncode=result.returncode,wall_seconds=time.monotonic()-start,
        excluded_raw_signal=excluded,device=device,reference_used_in_filter=False,exe_sha256=sha(TRIAL))
    save(folder/'run.json',receipt)
    assert result.returncode==0
    with solution.open() as f:rows=list(csv.DictReader(f))
    if not excluded:
        with CASES[device][1].open() as f:expected=list(csv.DictReader(f))[:limit]
        assert len(rows)==len(expected)
        assert all(all(r[k]==s[k] for k in r if k!='processing_ms') for r,s in zip(rows,expected))
        receipt['control_exact_except_processing_ms']=True
    else:
        assert len(rows)==3710
        with Path(str(solution)+'.obs.csv').open() as f:
            obs=list(csv.DictReader(f))
        system,signal=excluded.split(':')
        assert not any(r['sat'].startswith(system) and r['signal']==signal for r in obs)
        receipt['excluded_signal_absent_from_observations']=True
    receipt.update(completed=True,epochs=len(rows),solution_sha256=sha(solution))
    receipt['compressed_logs']={}
    for p in [folder/'solution.trace',Path(str(solution)+'.stat'),Path(str(solution)+'.obs.csv')]:
        digest=sha(p);target=Path(str(p)+'.gz')
        with p.open('rb') as src,gzip.open(target,'wb',compresslevel=5) as dst:shutil.copyfileobj(src,dst)
        with gzip.open(target,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
        receipt['compressed_logs'][p.name]=dict(path=str(target),uncompressed_sha256=digest)
        p.unlink()
    save(folder/'run.json',receipt)
    print(name,json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':
    build()
    run('bridge_control120',limit=120)
    run('k70_without_b2a',excluded='C:5P')
