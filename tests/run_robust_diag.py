"""Check that C's CSV describes the R actually passed into filter()."""
import csv, math, re
from pathlib import Path
import run_phase1_replay as replay

OUT=replay.ROOT/'validation/robust'
OUT.mkdir(parents=True,exist_ok=True)
replay.OUT=OUT
path=OUT/'TXT_C_diag.innovation.csv'
replay.PRODUCTS['INNOVATION_DIAG']=str(path)
rows,summary=replay.run('TXT_C_diag',replay.ROOT/'x64/Release/PPP_only.exe','C',epochs=600)
replay.PRODUCTS.pop('INNOVATION_DIAG',None)
trace=(OUT/'TXT_C_diag.trace').read_text(errors='replace')
weights={}
for line in trace.splitlines():
    if '$PPP_HUBER,' not in line: continue
    fields=dict(re.findall(r'([A-Za-z_0-9]+)=([^,]+)',line))
    key=(int(fields['week']),round(float(fields['tow']),3),int(fields['trial']),int(fields['row']))
    assert key not in weights
    weights[key]=fields
matched=downweighted=constraints=0
with path.open(newline='',encoding='utf-8') as f:
    for row in csv.DictReader(f):
        key=(int(row['week']),round(float(row['tow']),3),int(row['trial']),int(row['row']))
        assert row['baseline']=='C'
        obsvar,pred,sii=(float(row[k]) for k in ['obs_var','pred_var','Sii'])
        assert row['finite_flag']=='1' and all(math.isfinite(x) for x in [obsvar,pred,sii])
        assert math.isclose(sii,pred+obsvar,rel_tol=1e-11,abs_tol=1e-9)
        if row['measurement_class'] in ('GNSS_CODE','GNSS_PHASE'):
            w=weights[key]
            assert math.isclose(obsvar,float(w['R_eff']),rel_tol=1e-13,abs_tol=1e-13)
            assert row['signal'] and row['sat']
            matched+=1
            downweighted+=float(w['w'])<1
        else:
            assert key not in weights
            constraints+=1
assert matched==len(weights) and matched>0 and downweighted>0
assert summary['failure_epochs']==0 and summary['nonfinite_numeric_fields']==0
print({'epochs':summary['epochs'],'matched_GNSS_rows':matched,
       'downweighted':downweighted,'constraint_rows':constraints},flush=True)
