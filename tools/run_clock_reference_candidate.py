"""Explicit, reversible Raw-only clock-reference candidate. Formal entry is unchanged."""
from pathlib import Path
import os,sys,subprocess,json,datetime
from ppp_preset import environment,ROOT

def main():
    exe=ROOT/'validation/fullbias_reference_fix_v1/build_v3/trial.exe'
    manifest=exe.parent/'manifest.json'
    if not exe.exists() or not manifest.exists():raise SystemExit('Build tests/build_fullbias_reference_fix.py first.')
    import hashlib
    receipt=json.loads(manifest.read_text())
    if hashlib.sha256(exe.read_bytes()).hexdigest()!=receipt['exe_sha256']:raise SystemExit('Candidate executable fingerprint mismatch.')
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h for p,h in receipt['fingerprint'].items()):
        raise SystemExit('Candidate build inputs changed; rebuild and validate before running.')
    if '--source' in sys.argv[1:]:raise SystemExit('This entry fixes source=txt-fast. Supply original Raw TXT, not --source rinex.')
    if os.environ.get('RTK_PPP_OBS'):raise SystemExit('Clock-reference candidate requires original Raw TXT, not an existing RINEX file. Clear RTK_PPP_OBS.')
    # Keep only product/input/output selections, never inherit old experimental algorithms.
    keys=['TXT','NAV','SP3','CLK','BIA','IONEX','VMF_FIRST','VMF_SECOND','OROGRAPHY','ATX','OUTPUT','TRACE','TRACE_LEVEL']
    selected={k:os.environ['RTK_PPP_'+k]for k in keys if os.environ.get('RTK_PPP_'+k)}
    if selected.get('OUTPUT') and Path(selected['OUTPUT']).exists():raise SystemExit('Choose a NEW RTK_PPP_OUTPUT; existing result will not be overwritten.')
    env=environment(os.environ,selected)
    folder=ROOT/'validation/fullbias_reference_fix_v1/manual'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder.mkdir(parents=True,exist_ok=False)
    env.update(RTK_PPP_CLOCK_REFERENCE_TRIAL='1',RTK_PPP_CLOCK_REFERENCE_LOG=str(folder/'clock_reference.csv'))
    print('CLOCK_REFERENCE_CANDIDATE / B_VERIFIED / Raw TXT only',flush=True)
    print('Formal run_b_verified.cmd is unchanged. Choose a NEW result file.',flush=True)
    print('Clock reference log:',folder/'clock_reference.csv',flush=True)
    return subprocess.call([str(exe),'--source','txt-fast',*sys.argv[1:]],cwd=ROOT,env=env)

if __name__=='__main__':raise SystemExit(main())
