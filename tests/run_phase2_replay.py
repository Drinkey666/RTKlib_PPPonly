"""Phase 2 observational replay gate against the preserved ac99aba binary."""
from pathlib import Path
import json
import run_phase1_replay as base
base.OUT=base.ROOT/'validation/phase2'
OUT=base.OUT
old=OUT/'PPP_only_ac99aba.exe';new=base.ROOT/'x64/Release/PPP_only.exe'
OUT.mkdir(parents=True,exist_ok=True)
def run(name,exe,mode,diagnostic=False):
 return base.run(name,exe,mode,epochs=600)
# Add optional observer path to the existing runner through its product-env map.
evidence={'reference_commit':'ac99aba','input_files':[{'path':p,'sha256':base.digest(p)} for p in base.PRODUCTS.values()],'runs':[]}
for mode in ['A','B']:
 base.PRODUCTS.pop('INNOVATION_DIAG',None)
 ref,sref=run(mode+'_ac99aba',old,mode)
 off,soff=run(mode+'_diag_off',new,mode)
 base.PRODUCTS['INNOVATION_DIAG']=str(OUT/(mode+'_diag_on.innovation.csv'))
 on,son=run(mode+'_diag_on',new,mode,True)
 base.PRODUCTS.pop('INNOVATION_DIAG',None)
 checks={'vs_reference':base.compare(ref,on),'off_vs_on':base.compare(off,on),
   'state_dump_equal':len({s['state_dump_sha256'] for s in [sref,soff,son]})==1,
   'obs_dump_equal':len({s['obs_dump_sha256'] for s in [sref,soff,son]})==1,
   'event_counts_equal':all(sref[k]==soff[k]==son[k] for k in ['reject_events','detector_slip_events','arc_reset','arc_pending','arc_reinitialized','failure_epochs'])}
 states=[]
 for name in [mode+'_ac99aba',mode+'_diag_off',mode+'_diag_on']:
  states.append([l[l.index('$PPP_STATE,'):] for l in (OUT/(name+'.trace')).read_text(errors='replace').splitlines() if '$PPP_STATE,' in l])
 checks['main_states_equal']=states[0]==states[1]==states[2]
 evidence[mode]=checks;evidence['runs'] += [sref,soff,son]
 assert all(checks[k] for k in ['state_dump_equal','obs_dump_equal','event_counts_equal','main_states_equal'])
 assert checks['vs_reference']['numeric_rows_equal_excluding_wall_time'] and checks['off_vs_on']['numeric_rows_equal_excluding_wall_time']
 assert all(s['nonfinite_numeric_fields']==0 for s in [sref,soff,son])
 print(mode,checks,flush=True)
(OUT/'replay_summary.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
