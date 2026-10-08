"""Phase 2 second-entry regression, complete 1200-epoch RINEX input."""
import run_phase1_rinex as runner
from run_phase1_replay import ROOT,digest
from summarize_phase2 import analyze
import json
runner.OUT=ROOT/'validation/phase2'
summary={'inputs':[dict(path=p,sha256=digest(p)) for p in runner.FILES.values()]}
for mode in ['A','B']:
 runner.FILES.pop('INNOVATION_DIAG',None)
 old=runner.run('rinex_'+mode+'_ac99aba',runner.OUT/'PPP_only_ac99aba.exe',mode)
 path=runner.OUT/('rinex_'+mode+'_diag_on.innovation.csv')
 runner.FILES['INNOVATION_DIAG']=str(path)
 new=runner.run('rinex_'+mode+'_diag_on',ROOT/'x64/Release/PPP_only.exe',mode)
 _,_,diag=analyze(path,False)
 checks={k:old[k]==new[k] for k in ['numeric_rows','state_sha256','input_epoch_records','Q','reject_events','detector_slip_events','legacy_slip_reinitializations']}
 checks['no_failure']=not new['failure_records'];assert all(checks.values())
 summary[mode]={'checks':checks,'diagnostics':diag,'runs':[{k:v for k,v in r.items() if k not in ['numeric_rows','input_epoch_records']} for r in [old,new]]}
 print(mode,checks,flush=True)
(runner.OUT/'rinex_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
