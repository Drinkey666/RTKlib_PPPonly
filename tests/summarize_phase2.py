"""Offline descriptive statistics; never imports or writes estimator state.

Use FIRST_PREFIT only, including observations later rejected (no selection by u).
std uses ddof=1; percentiles use linear interpolation of the empirical order
statistics. Temporal evidence uses adjacent epochs within the same satellite,
actual signal, observation type and stage, excluding resets/slips/rejects/failures.
"""
from pathlib import Path
import csv, json, math, collections, statistics
from run_phase1_replay import digest
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/phase2'

def percentile(a,p):
    a=sorted(a);k=(len(a)-1)*p;lo=int(k);hi=min(lo+1,len(a)-1)
    return a[lo]+(a[hi]-a[lo])*(k-lo)

def stats(rows):
    v=[float(r['v']) for r in rows];u=[float(r['u']) for r in rows];au=list(map(abs,u))
    return dict(sample_count=len(u),mean_v=statistics.mean(v),std_v=statistics.stdev(v) if len(v)>1 else None,
        mean_u=statistics.mean(u),std_u=statistics.stdev(u) if len(u)>1 else None,
        median_abs_u=statistics.median(au),p95_abs_u=percentile(au,.95),p99_abs_u=percentile(au,.99),
        abs_u_gt1=sum(a>1 for a in au)/len(au),abs_u_gt2=sum(a>2 for a in au)/len(au),abs_u_gt3=sum(a>3 for a in au)/len(au))

def correlation(rows):
    tracks=collections.defaultdict(list)
    for r in rows:tracks[(r['baseline'],r['sys'],r['signal'],r['obs_type'],r['stage'],r['sat'])].append(r)
    results=[]
    for key,track in tracks.items():
        pairs=[];previous=None
        for r in sorted(track,key=lambda r:int(r['epoch'])):
            eligible=(r['finite_flag']=='1' and r['legacy_reject_flag']=='0' and r['slip_flag']=='0'
                and r['arc_status'] not in ['ARC_PENDING_INIT','ARC_REINITIALIZED','UNINITIALIZED']
                and r['epoch_failure']=='0' and r['combined']=='0' and r['inactive_state_support']=='0')
            if eligible and previous and int(r['epoch'])==int(previous['epoch'])+1 and 0<float(r['elapsed_s'])-float(previous['elapsed_s'])<=1.5:
                pairs.append((float(previous['u']),float(r['u'])))
            previous=r if eligible else None
        if len(pairs)<20:continue
        a,b=zip(*pairs);ma,mb=statistics.mean(a),statistics.mean(b)
        va=sum((x-ma)**2 for x in a);vb=sum((x-mb)**2 for x in b)
        if not va or not vb:continue
        rho=sum((x-ma)*(y-mb) for x,y in pairs)/math.sqrt(va*vb)
        results.append(dict(zip(['baseline','sys','signal','obs_type','stage','sat'],key),pairs=len(pairs),lag1_pair_pearson=rho))
    return results

def analyze(path,check_source=True):
    rows=list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
    assert rows and all(None not in r and None not in r.values() for r in rows), 'CSV column mismatch'
    trialgroups=collections.defaultdict(list)
    for r in rows:trialgroups[(r['epoch'],r['trial'])].append(int(r['row']))
    assert all(a==list(range(len(a))) for a in trialgroups.values()),'non-contiguous residual row mapping'
    valid=[r for r in rows if r['finite_flag']=='1']
    for r in valid:
        v,p,R,S,u=map(lambda k:float(r[k]),['v','pred_var','obs_var','Sii','u'])
        assert all(math.isfinite(x) for x in [v,p,R,S,u]) and S>0
        assert math.isclose(S,p+R,rel_tol=2e-15,abs_tol=1e-15)
        assert math.isclose(u,v/math.sqrt(S),rel_tol=2e-15,abs_tol=1e-15)
    invalid=[r for r in rows if r['finite_flag']!='1']
    assert all(r['invalid_reason']!='OK' for r in invalid)
    first=[r for r in rows if r['sample_scope']=='FIRST_PREFIT']
    real=[r for r in first if r['measurement_class'] in ['GNSS_CODE','GNSS_PHASE']]
    assert all(r['signal'] and r['sat'] and r['sys'] and int(r['source_obs_index'])>=0 and float(r['frequency_hz'])>0 for r in real)
    pseudo=[r for r in first if r['measurement_class'] in ['IONO_PRIOR','TROP_PRIOR','OTHER_CONSTRAINT']]
    assert all(r['obs_type']=='PRIOR' and not r['signal'] and int(r['source_obs_index'])==-1 for r in pseudo)
    if check_source:
        obs_path=Path(str(path).replace('.innovation.csv','.csv.obs.csv'))
        source=collections.defaultdict(list)
        for r in csv.DictReader(obs_path.open(encoding='utf-8-sig')):source[(r['week'],r['tow'],r['sat'],r['signal'])].append(r)
        for r in real:
            match=source[(r['week'],r['tow'],r['sat'],r['signal'])]
            assert any(int(q['slot'])-1==int(r['frequency_slot']) and abs(float(q['CN0_dBHz'])-float(r['cn0_dbhz']))<1e-8 for q in match),'raw source mapping mismatch'
    finite_real=[r for r in real if r['finite_flag']=='1']
    grouped=collections.defaultdict(list)
    for r in finite_real:grouped[(r['baseline'],r['sys'],r['signal'],r['obs_type'],r['stage'])].append(r)
    table=[dict(zip(['baseline','sys','signal','obs_type','stage'],k),**stats(v)) for k,v in sorted(grouped.items())]
    aggregate=[]
    for mode in ['A','B']:
        for kind in ['P','L']:
            for stage in ['STARTUP','STEADY']:
                q=[r for r in finite_real if r['baseline']==mode and r['obs_type']==kind and r['stage']==stage]
                if q:aggregate.append(dict(baseline=mode,obs_type=kind,stage=stage,**stats(q)))
    examples=[r for r in finite_real if r['stage']=='STARTUP' and abs(float(r['v']))>=10 and abs(float(r['u']))<=1 and abs(float(r['v']))>5*float(r['sqrt_Rii'])]
    examples=sorted(examples,key=lambda r:abs(float(r['v'])),reverse=True)[:5]
    corr=correlation(finite_real)
    summary=dict(path=str(path),sha256=digest(path),total_rows=len(rows),first_prefit_rows=len(first),
        editing_retry_rows=len(rows)-len(first),real_first_rows=len(real),
        measurement_classes=dict(collections.Counter(r['measurement_class'] for r in first)),
        invalid_rows=len(invalid),invalid_reasons=dict(collections.Counter(r['invalid_reason'] for r in invalid)),
        inactive_state_support_rows=sum(r['inactive_state_support']=='1' for r in rows),
        negative_prediction_variance_rows=sum(float(r['pred_var'])<0 for r in valid),
        first_prefit_later_rejected=sum(r['legacy_reject_flag']=='1' for r in first),
        first_prefit_slip_rows=sum(r['slip_flag']!='0' for r in first),
        unknown_constraint_rows=sum(r['measurement_class']=='OTHER_CONSTRAINT' for r in rows),
        matrix_identity_and_mapping_checks='PASS',aggregate=aggregate,startup_examples=examples,
        continuous_track_correlation_count=len(corr),
        largest_absolute_correlations=sorted(corr,key=lambda r:abs(r['lag1_pair_pearson']),reverse=True)[:8])
    return table,corr,summary

def write_csv(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=='__main__':
    table=[];correlations=[];summaries=[]
    for mode in ['A','B']:
        t,c,s=analyze(OUT/(mode+'_diag_on.innovation.csv'));table+=t;correlations+=c;summaries.append(s)
    write_csv(ROOT/'docs/PHASE2_SIGNAL_STATS.csv',table)
    write_csv(ROOT/'docs/PHASE2_TEMPORAL_STATS.csv',correlations)
    (OUT/'innovation_summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in s.items() if k not in ['startup_examples','largest_absolute_correlations']} for s in summaries],indent=2),flush=True)
