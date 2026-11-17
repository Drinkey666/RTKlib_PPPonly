"""One read-only Oct25 observer: sparse committed code equations + selected updates.

No source model change, no tuning, no new weighting, no production executable overwrite.
"""
import csv, gzip, json, os, re, shutil, subprocess, sys
from pathlib import Path
from four_sample_diagnosis import ROOT, read, save, sha, np, log_open
from colocated_code_reference_trial import protect
from build_filter_first_diagnostic import DEV, FLAGS, text_sections
from replay_verified_integration import events, archive

OUT = ROOT/'validation/oct25_east_bias_v1'
BASE = ROOT/'validation/android_live_20261025_v1'
PARENT = ROOT/'validation/admission_history_causal_v1/build'
OBJECTS = ROOT/'validation/signal_admission_v1/build/objects'
sys.path.insert(0,str(ROOT/'tools'))
from ppp_preset import environment


def build():
    b=OUT/'build';src=b/'source';src.mkdir(parents=True,exist_ok=True)
    if (b/'manifest.json').exists():
        old=read(b/'manifest.json');assert sha(b/'observer.exe')==old['exe'];return b/'observer.exe'
    for p in (PARENT/'source').glob('*.h'):(src/p.name).write_bytes(p.read_bytes())
    (src/'ppp.c').write_bytes((PARENT/'source/ppp.c').read_bytes())
    cg=(ROOT/'tests/code_geometry_history_observer.h').read_text()
    snap=(ROOT/'tests/admission_history_diag.h').read_text()
    snap=snap.replace('1,31,61,62,63,105,106,107,120,121,301,601,1341',
        '1,2,3,4,5,6,7,8,9,10,16,31,61,91,121,181,241,301,451,601,901,1201,1549')
    cg=re.sub(r'\bah_', 'cg_ah_', cg)
    snap=re.sub(r'\bah_', 'snap_ah_', snap)
    wrappers='''
static void ah_begin(const rtk_t*r,const obsd_t*o){cg_ah_begin(r,o);snap_ah_begin(r,o);}
static void ah_state(const char*s,const rtk_t*r){snap_ah_state(s,r);}
static void ah_seed_mask(const obsd_t*o,double*p){(void)o;(void)p;}
static int ah_update_mask(const obsd_t*o,int f){(void)o;(void)f;return 0;}
static void ah_seed(const rtk_t*r,const obsd_t*o,int f,int sf,double p,double g,double I,double L,double s,double old,int slip){(void)r;(void)o;(void)f;(void)sf;(void)p;(void)g;(void)I;(void)L;(void)s;(void)old;(void)slip;}
static void ah_capture(const rtk_t*r,int tr,const double*x,const double*P,const double*H,const double*v,const double*R,int m,const ppp_innovation_meta_t*z){cg_ah_capture(r,tr,x,P,H,v,R,m,z);snap_ah_capture(r,tr,x,P,H,v,R,m,z);}
static void ah_commit(const rtk_t*r){cg_ah_commit(r);snap_ah_commit(r);}
'''
    (src/'admission_history_diag.h').write_text(cg+'\n'+snap+'\n'+wrappers,encoding='utf-8')
    flags=FLAGS.replace('/Isrc','')+f' /I"{src}"'
    objs=' '.join('"'+str(b/'ppp_on.obj' if p.stem=='ppp' else p)+'"' for p in sorted(OBJECTS.glob('*.obj')))
    cmd=['@echo off',f'call "{DEV}" -arch=x64 -host_arch=x64 >nul',
      f'cl {flags} /DENABLE_SIGNAL_ADMISSION_TRIAL /DENABLE_ADMISSION_HISTORY_CAUSAL /c "{src/"ppp.c"}" /Fo"{b/"ppp_on.obj"}"','if errorlevel 1 exit /b 1',
      f'cl {flags} /c "{src/"ppp.c"}" /Fo"{b/"ppp_off.obj"}"','if errorlevel 1 exit /b 1',
      f'link /NOLOGO /SUBSYSTEM:CONSOLE /MACHINE:X64 /OUT:"{b/"observer.exe"}" {objs} winmm.lib ws2_32.lib comdlg32.lib user32.lib gdi32.lib shell32.lib advapi32.lib ole32.lib oleaut32.lib uuid.lib','if errorlevel 1 exit /b 1']
    (b/'build.cmd').write_text('\n'.join(cmd),encoding='utf-8')
    result=subprocess.run(['cmd','/c',str(b/'build.cmd')],cwd=ROOT,capture_output=True)
    (b/'build.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout.decode(errors='replace')[-3500:]
    assert text_sections(b/'ppp_off.obj')==text_sections(PARENT/'ppp_ref.obj')
    save(b/'manifest.json',dict(exe=sha(b/'observer.exe'),header=sha(src/'admission_history_diag.h'),
        macro_off_text_equal=True,parent_source=sha(PARENT/'source/ppp.c'),
        reused_objects={p.name:sha(p) for p in OBJECTS.glob('*.obj') if p.stem!='ppp'}))
    return b/'observer.exe'


def main():
    formal=protect();OUT.mkdir(exist_ok=True);exe=build();case=OUT/'OBSERVE';case.mkdir(exist_ok=True)
    if (case/'run.json').exists():
        rec=read(case/'run.json');assert rec['control_passed'];print('Exact observer already complete; no replay.');return
    inputs=read(BASE/'pc_live_window/manifest.json')['files']
    raw=case/'live_window_raw.txt'
    with gzip.open(BASE/'inputs/live_window_raw.txt.gz','rb') as a,raw.open('xb') as b:shutil.copyfileobj(a,b)
    refreceipt=read(BASE/'pc_live_window/solution.csv.session.json')
    assert sha(raw)==refreceipt['input_sha256']['TXT'];inputs['TXT']=str(raw)
    env=environment(os.environ,inputs)
    output=case/'solution.csv';trace=case/'solution.trace'
    env.update(RTK_PPP_SIGNAL_ADMISSION='OFF',RTK_PPP_ADMISSION_HISTORY='OBSERVE',
        RTK_PPP_ADMISSION_HISTORY_DIR=str(case),RTK_PPP_OUTPUT=str(output),
        RTK_PPP_TRACE=str(trace),RTK_PPP_TRACE_LEVEL='2')
    with (case/'console.log').open('wb') as log:
        result=subprocess.run([str(exe),'--source','txt-fast','--no-gui'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,result.returncode
    def rows(p):
        with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
    old=rows(BASE/'pc_live_window/solution.csv');new=rows(output);assert len(old)==len(new)==1549
    fields=[k for k in old[0] if k!='processing_ms']
    assert all(all(a[k]==b[k] for k in fields) for a,b in zip(old,new)),'Observer changed solution'
    with log_open(BASE/'pc_live_window/solution.csv.stat') as f:a=f.read()
    with (case/'solution.csv.stat').open() as f:b=f.read()
    assert a==b,'Observer changed complete STAT'
    assert events(trace)==events(BASE/'pc_live_window/solution.csv.trace')
    with log_open(BASE/'pc_live_window/solution.csv.obs.csv') as f:a=f.read()
    with (case/'solution.csv.obs.csv').open() as f:b=f.read()
    assert a==b,'Observer changed observation conversion'
    assert protect()==formal
    save(case/'run.json',dict(control_passed=True,epochs=1549,full_solution_non_timing_exact=True,
        full_STAT_exact=True,full_obs_exact=True,full_events_exact=True,executable=sha(exe),inputs=inputs,
        input_sha256={k:sha(v) for k,v in inputs.items()},formal_files_unchanged=len(formal),
        source='same-window RAW, not RINEX',new_readonly_replays=1,parameter_changes=False))
    for p in [raw,trace,case/'solution.csv.stat',case/'solution.csv.obs.csv',case/'code_factors.bin',case/'updates.bin',case/'states.csv',case/'stages.csv']:
        archive(p)
    print('READONLY OBSERVER EXACT; 1549 epochs, snapshots and code rows saved.',flush=True)


if __name__=='__main__':main()
