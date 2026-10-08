"""Freeze hashes and compact results of the completed robust PPP replay."""
from pathlib import Path
import csv, hashlib, json, re
import run_phase1_replay as txt
import run_phase1_rinex as rinex

root=txt.ROOT
out=root/'validation/robust'
replay=json.loads((out/'replay_summary.json').read_text(encoding='utf-8'))
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def csv_rows(name):
    with (out/name).open(newline='',encoding='utf-8-sig') as f:
        records=list(csv.reader(f))
    return records[1:] if records and not records[0][0].isdigit() else records
def state_records(name):
    return [s[s.index('$PPP_STATE,'):] for s in (out/name).read_text(errors='replace').splitlines()
            if '$PPP_STATE,' in s]
def weight_types(name):
    totals={'CODE':0,'PHASE':0};changed={'CODE':0,'PHASE':0}
    for line in (out/name).read_text(errors='replace').splitlines():
        if '$PPP_HUBER,' not in line:continue
        fields=dict(re.findall(r'([A-Za-z_0-9]+)=([^,]+)',line))
        kind=fields['type'];totals[kind]+=1
        changed[kind]+=float(fields['w'])<1
    return {'rows':totals,'downweighted':changed}
source_names=['PPP_only/ppp_position.c','src/ppp.c','src/ppp_innovation_diag.c',
 'src/rnx2rtkp.c','src/rtkcmn.c','src/rtklib.h','src/smartphone_ppp_config.c',
 'src/smartphone_ppp_config.h','tests/robust_regression.c','tests/run_robust_tests.ps1',
 'tests/run_robust_replay.py','tests/run_robust_diag.py','tests/prepare_robust_evidence.py']
outputs=['TXT_A_new.csv','TXT_B_new.csv','TXT_C_repeat1.csv','TXT_C_repeat1.csv.stat',
 'TXT_C_repeat1.trace','TXT_C_diag.csv','TXT_C_diag.csv.stat','TXT_C_diag.innovation.csv',
 'RINEX_A_new.pos','RINEX_B_new.pos','RINEX_C_repeat1.pos',
 'RINEX_C_repeat1.pos.stat','RINEX_C_repeat1.trace']
checks={mode:replay['txt'][mode]['checks'] for mode in ['A','B']}
checks.update({f'rinex_{mode}':replay['rinex'][mode]['checks'] for mode in ['A','B']})
diagnosed=txt.compare(csv_rows('TXT_C_repeat1.csv'),csv_rows('TXT_C_diag.csv'))
assert (diagnosed['numeric_rows_equal_excluding_wall_time'] and
    digest(out/'TXT_C_repeat1.csv.stat')==digest(out/'TXT_C_diag.csv.stat'))
rinex_a=[s for s in (out/'RINEX_A_new.pos').read_text(errors='replace').splitlines() if s and not s.startswith('%')]
rinex_c=[s for s in (out/'RINEX_C_repeat1.pos').read_text(errors='replace').splitlines() if s and not s.startswith('%')]
assert len(rinex_a)==len(rinex_c)==1200
tests={}
for label,loc in [('phase1_C','validation/phase1/test_results.txt'),
                  ('phase2_C','validation/phase2/test_results.txt'),
                  ('phase2_5_C','validation/phase2_5/test_results.txt'),
                  ('robust_C','validation/robust/test_results.txt')]:
    text=(root/loc).read_text(errors='replace')
    tests[label]=re.search(r'RESULT passed=\d+ failed=\d+',text).group()
evidence={'reference_commit':'93de551','date':'2026-10-08',
 'reference_executable_sha256':replay['reference_executable_sha256'],
 'new_executable_sha256':replay['new_executable_sha256'],
 'tests':tests,'A_B_regression':checks,
 'C':{'txt':replay['txt']['C_1'],'txt_repeat':replay['txt']['C_2'],
       'rinex':replay['rinex']['C_1'],'rinex_repeat':replay['rinex']['C_2'],
       'txt_vs_A':txt.compare(csv_rows('TXT_A_new.csv'),csv_rows('TXT_C_repeat1.csv')),
       'txt_diag_vs_off':diagnosed,
       'txt_diag_state_equal':state_records('TXT_C_repeat1.trace')==state_records('TXT_C_diag.trace'),
       'rinex_C_equal_A':rinex_a==rinex_c,
       'txt_weight_types':weight_types('TXT_C_repeat1.trace'),
       'rinex_weight_types':weight_types('RINEX_C_repeat1.trace')},
 'inputs':{'txt':{k:digest(v) for k,v in txt.PRODUCTS.items()},
           'rinex':{k:digest(v) for k,v in rinex.FILES.items()}},
 'sources':{name:digest(root/name) for name in source_names},
 'outputs':{name:digest(out/name) for name in outputs}}
assert evidence['C']['txt_diag_state_equal']
path=root/'docs/PPP_ROBUST_EVIDENCE.json'
path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(path,flush=True)
