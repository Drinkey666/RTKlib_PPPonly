"""Same-input PC fast regression; never uses reference/truth coordinates.
Run with bundled Python from the project root. Outputs validation/phase1/.
"""
from pathlib import Path
import os, subprocess, csv, json, hashlib, collections, re, math, time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/phase1'
PRODUCTS={
 'TXT':r'E:\RTKLIB_Data\OBS\RawData_20260922_141724.txt',
 'NAV':r'E:\RTKLIB_Data\NAV\BRDC00WRD_S_20262650000_01D_MN.rnx',
 'SP3':r'E:\RTKLIB_Data\SP3\WUM0MGXNRT_20262641000_02D_05M_ORB.SP3',
 'CLK':r'E:\RTKLIB_Data\CLK\WUM0MGXNRT_20262641000_02D_05M_CLK.CLK',
 'BIA':r'E:\RTKLIB_Data\BIA\WUM0MGXRTS_20262650000_01D_05M_OSB.BIA',
 'IONEX':r'E:\RTKLIB_Data\IONEX\COD0OPSP0D_20262650000_01D_01H_GIM.INX',
 'VMF_FIRST':r'E:\RTKLIB_Data\tro\VMF3_20260922.H06',
 'VMF_SECOND':r'E:\RTKLIB_Data\tro\VMF3_20260922.H12',
 'OROGRAPHY':r'E:\RTKLIB_Data\tro\orography_ell_5x5',
 'ATX':r'E:\RTKLIB_Data\Tables\igs20.atx',
}
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def run(name,exe,mode=None,lifecycle=None,epochs=180):
 result=OUT/(name+'.csv');trace=OUT/(name+'.trace');console=OUT/(name+'.log')
 env={k:v for k,v in os.environ.items() if not k.startswith('RTK_PPP_')}
 env.update({'RTK_PPP_'+k:v for k,v in PRODUCTS.items()})
 env.update(RTK_PPP_OUTPUT=str(result),RTK_PPP_TRACE=str(trace),RTK_PPP_TRACE_LEVEL='3')
 if mode:env['RTK_PPP_BASELINE']=mode
 if lifecycle:env['RTK_PPP_LIFECYCLE']=lifecycle
 cmd=[str(exe),'--source','txt-fast','--no-gui','--max-epochs',str(epochs)]
 start=time.monotonic()
 with console.open('wb') as f:
  proc=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
 if proc.returncode:raise RuntimeError(f'{name} exit={proc.returncode}; see {console}')
 rows=list(csv.reader(result.open(encoding='utf-8-sig')))
 if rows and not rows[0][0].isdigit():rows=rows[1:]
 text=trace.read_text(encoding='utf-8',errors='replace')
 failures=[line for line in text.splitlines() if '$PPP_FAILURE,' in line]
 state=[line[line.index('$PPP_STATE,'):] for line in text.splitlines() if '$PPP_STATE,' in line]
 weights=[line for line in text.splitlines() if '$PPP_R,' in line]
 clean_rows=all(all(float(re.search(r'(?:^|,)'+key+r'=([^,]+)',l)[1])==target
   for key,target in [('w',1),('w_history',1),('eta',1),('legacy_time_add',0)]) and
   float(re.search(r',R0=([^,]+)',l)[1])==float(re.search(r',R_eff=([^,]+)',l)[1]) for l in weights)
 summary=dict(name=name,epochs=len(rows),valid=sum(int(r[2])!=0 for r in rows),
  Q=dict(collections.Counter(r[2] for r in rows)),last=rows[-1][:-1],
  nonfinite_numeric_fields=sum(not math.isfinite(float(v)) for r in rows for v in r[:-1]),
  failure_epochs=len(failures),failure_reasons=dict(collections.Counter(re.search(r'reason=([^,]+)',l)[1] for l in failures)),
  reject_events=text.count('$PPP_REJECT,'),slip_checks=text.count('$SLIP_CHECK,'),
  legacy_slip_reinitializations=len(re.findall(r'\$AMBRESET,[^\n]*,SLIP,',text)),
  arc_reset=text.count('$ARC_RESET,'),arc_pending=text.count('$ARC_PENDING_INIT,'),arc_reinitialized=text.count('$ARC_REINITIALIZED,'),
  detector_slip_events=len(re.findall(r'detslp_ll: slip detected|detslp_gf: slip |\$PRE_MW_SLIP,|\$PRE_DOP_SLIP,',text)),
  state_dump_sha256=digest(str(result)+'.stat'),obs_dump_sha256=digest(str(result)+'.obs.csv'),
  last_main_state=state[-1] if state else None,R_rows=len(weights),all_R_rows_clean=bool(weights) and clean_rows,
  wall_seconds=time.monotonic()-start,
  executable_sha256=digest(exe),command=cmd)
 print(json.dumps({k:summary[k] for k in ['name','epochs','valid','Q','failure_reasons','wall_seconds']},ensure_ascii=False),flush=True)
 return rows,summary
def compare(a,b):
 aa={tuple(r[:2]):r for r in a};bb={tuple(r[:2]):r for r in b};keys=aa.keys()&bb.keys()
 valid=[k for k in keys if int(aa[k][2]) and int(bb[k][2])]
 return dict(common_epochs=len(keys),common_valid_epochs=len(valid),
  numeric_rows_equal_excluding_wall_time=all(aa[k][:-1]==bb[k][:-1] for k in keys),
  Q_differences=sum(aa[k][2]!=bb[k][2] for k in keys),ns_differences=sum(aa[k][3]!=bb[k][3] for k in keys),
  max_coordinate_component_difference_m=max((abs(float(aa[k][i])-float(bb[k][i])) for k in valid for i in [5,6,7]),default=0),
  max_coordinate_3d_difference_m=max((math.sqrt(sum((float(aa[k][i])-float(bb[k][i]))**2 for i in [5,6,7])) for k in valid),default=0))
if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True)
 summary={'input_files':[dict(path=p,sha256=digest(p)) for p in PRODUCTS.values()]}
 baseline=OUT/'PPP_only_97a57a9.exe';new=ROOT/'x64/Release/PPP_only.exe'
 if not baseline.exists():raise RuntimeError('Preserve the 97a57a9 executable before building.')
 old,so=run('legacy_97a57a9',baseline)
 b,sb=run('B_legacy',new,'B')
 a,sa=run('A_repeat1',new,'A')
 a2,sa2=run('A_repeat2',new,'A')
 bc,sbc=run('B_corrected',new,'B','CORRECTED')
 summary.update(runs=[so,sb,sa,sa2,sbc],B_vs_97a57a9=compare(old,b),A_repeat=compare(a,a2),
  B_corrected_vs_97a57a9=compare(old,bc),B_state_dump_equal=so['state_dump_sha256']==sb['state_dump_sha256'],
  A_state_dump_equal=sa['state_dump_sha256']==sa2['state_dump_sha256'],
  all_observation_dumps_equal=len({s['obs_dump_sha256'] for s in [so,sb,sa,sa2,sbc]})==1)
 (OUT/'replay_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in summary.items() if k not in ['runs','input_files']},indent=2),flush=True)
 if not (summary['B_vs_97a57a9']['numeric_rows_equal_excluding_wall_time'] and summary['B_state_dump_equal'] and
   summary['A_repeat']['numeric_rows_equal_excluding_wall_time'] and summary['A_state_dump_equal'] and
   summary['all_observation_dumps_equal'] and sa['all_R_rows_clean'] and sa2['all_R_rows_clean'] and
   all(s['nonfinite_numeric_fields']==0 and s['failure_epochs']==0 for s in [sb,sa,sa2,sbc]) and
   so['reject_events']==sb['reject_events'] and so['detector_slip_events']==sb['detector_slip_events']):
  raise RuntimeError('Phase 1 replay regression failed; inspect replay_summary.json')
