"""Freeze A/B and exercise C on the same TXT and RINEX inputs.

This compares algorithm outputs and failure accounting; it never uses truth
coordinates or tunes the Huber cutoff from coordinate errors.
"""
from pathlib import Path
import json, math, re
import run_phase1_replay as txt
import run_phase1_rinex as rinex

OUT=txt.ROOT/'validation/robust'
OUT.mkdir(parents=True,exist_ok=True)
txt.OUT=rinex.OUT=OUT
old=OUT/'PPP_only_93de551.exe'
new=txt.ROOT/'x64/Release/PPP_only.exe'
if not old.exists(): raise RuntimeError('preserved 93de551 executable missing')

def state_records(name):
    return [s[s.index('$PPP_STATE,'):] for s in (OUT/(name+'.trace')).read_text(errors='replace').splitlines() if '$PPP_STATE,' in s]

def huber_trace(name):
    records=[]
    for line in (OUT/(name+'.trace')).read_text(errors='replace').splitlines():
        if '$PPP_HUBER,' not in line: continue
        fields=dict(re.findall(r'([A-Za-z_0-9]+)=([^,]+)',line))
        u,w,base,eff=(float(fields[k]) for k in ['u0','w','R_before','R_eff'])
        assert all(math.isfinite(x) for x in [u,w,base,eff])
        assert 0<w<=1 and base>=0 and math.isclose(eff,base/w,rel_tol=2e-14,abs_tol=1e-14)
        records.append((u,w,base,eff))
    return {'rows':len(records),'downweighted':sum(w<1 for _,w,_,_ in records),
            'minimum_weight':min((w for _,w,_,_ in records),default=None),
            'maximum_abs_u':max((abs(u) for u,_,_,_ in records),default=None)}

result={'reference_commit':'93de551','reference_executable_sha256':txt.digest(old),
        'new_executable_sha256':txt.digest(new),'txt':{},'rinex':{}}
for mode in ['A','B']:
    name=f'TXT_{mode}_93de551'; updated=f'TXT_{mode}_new'
    rows_ref,s_ref=txt.run(name,old,mode,epochs=600)
    rows_new,s_new=txt.run(updated,new,mode,epochs=600)
    checks=txt.compare(rows_ref,rows_new)
    checks.update(state_equal=state_records(name)==state_records(updated),
                  stat_equal=s_ref['state_dump_sha256']==s_new['state_dump_sha256'],
                  obs_equal=s_ref['obs_dump_sha256']==s_new['obs_dump_sha256'],
                  reject_equal=s_ref['reject_events']==s_new['reject_events'],
                  slip_equal=s_ref['detector_slip_events']==s_new['detector_slip_events'],
                  failure_equal=s_ref['failure_reasons']==s_new['failure_reasons'])
    assert all([checks['numeric_rows_equal_excluding_wall_time'],checks['state_equal'],
                checks['stat_equal'],checks['obs_equal'],checks['reject_equal'],
                checks['slip_equal'],checks['failure_equal']])
    result['txt'][mode]={'checks':checks,'reference':s_ref,'new':s_new}
for version in [1,2]:
    name=f'TXT_C_repeat{version}'
    rows,summary=txt.run(name,new,'C',epochs=600)
    # Phase-1's generic runner only counts the A/B `$PPP_R` format. C records
    # the pre-Huber variance and the final per-row variance separately.
    summary.pop('R_rows',None);summary.pop('all_R_rows_clean',None)
    result['txt'][f'C_{version}']={'summary':summary,'huber':huber_trace(name)}
    assert (summary['epochs']==600 and summary['nonfinite_numeric_fields']==0 and
        summary['failure_epochs']==0 and result['txt'][f'C_{version}']['huber']['rows']>0)
    if version==1: c_rows=rows;c_state=state_records(name);c_stat=summary['state_dump_sha256']
    else:
        assert txt.compare(c_rows,rows)['numeric_rows_equal_excluding_wall_time']
        assert c_state==state_records(name) and c_stat==summary['state_dump_sha256']
for mode in ['A','B']:
    name=f'RINEX_{mode}_93de551';updated=f'RINEX_{mode}_new'
    ref=rinex.run(name,old,mode);current=rinex.run(updated,new,mode)
    checks={k:ref[k]==current[k] for k in ['numeric_rows','state_sha256','input_epoch_records','Q','reject_events','detector_slip_events','legacy_slip_reinitializations','failure_records']}
    assert all(checks.values())
    result['rinex'][mode]={'checks':checks,'reference':{k:v for k,v in ref.items() if k not in ['numeric_rows','input_epoch_records']},
                          'new':{k:v for k,v in current.items() if k not in ['numeric_rows','input_epoch_records']}}
for version in [1,2]:
    name=f'RINEX_C_repeat{version}'
    run=rinex.run(name,new,'C')
    result['rinex'][f'C_{version}']={'summary':{k:v for k,v in run.items() if k not in ['numeric_rows','input_epoch_records']},
                                   'huber':huber_trace(name)}
    assert run['output_epochs']==1200 and not run['failure_records'] and result['rinex'][f'C_{version}']['huber']['rows']>0
    if version==1: rinex_c=run
    else:
        for key in ['numeric_rows','state_sha256','Q','reject_events','detector_slip_events','failure_records']:
            assert run[key]==rinex_c[key]
(OUT/'replay_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({source:{mode:entry.get('huber',entry.get('checks')) for mode,entry in result[source].items()}
                  for source in ['txt','rinex']},ensure_ascii=False,indent=2),flush=True)
