"""Verify the second entry path on the complete 1200-epoch audit input."""
from run_phase1_replay import ROOT,OUT,digest
import os,subprocess,json,time,collections,re
FILES={
 'OBS':r'E:\RTKLIB_Data\OBS\K80-GNSS00GEO_R_20260760533_20M_01S_MO.rnx',
 'NAV':r'E:\RTKLIB_Data\NAV\BRDC00IGS_R_20260760000_01D_MN.rnx',
 'SP3':r'E:\RTKLIB_Data\SP3\WUM0MGXFIN_20260760000_01D_05M_ORB.SP3',
 'CLK':r'E:\RTKLIB_Data\CLK\WUM0MGXFIN_20260760000_01D_30S_CLK.CLK',
 'BIA':r'E:\RTKLIB_Data\BIA\WUM0MGXFIN_20260760000_01D_01D_OSB.BIA',
 'IONEX':r'E:\RTKLIB_Data\IONEX\COD0OPSFIN_20260760000_01D_01H_GIM.INX',
 'VMF_FIRST':r'E:\RTKLIB_Data\tro\VMF3_20260317.H00',
 'VMF_SECOND':r'E:\RTKLIB_Data\tro\VMF3_20260317.H06',
 'OROGRAPHY':r'E:\RTKLIB_Data\tro\orography_ell_5x5',
 'ATX':r'E:\RTKLIB_Data\Tables\igs20.atx'}
def run(name,exe,mode):
 out=OUT/(name+'.pos');tr=OUT/(name+'.trace')
 env={k:v for k,v in os.environ.items() if not k.startswith('RTK_PPP_')}
 env.update({'RTK_PPP_'+k:v for k,v in FILES.items()})
 env.update(RTK_PPP_OUTPUT=str(out),RTK_PPP_TRACE=str(tr),RTK_PPP_TRACE_LEVEL='3',RTK_PPP_BASELINE=mode)
 start=time.monotonic()
 with (OUT/(name+'.log')).open('wb') as f:
  r=subprocess.run([str(exe),'--source','rinex','--no-gui'],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(f'{name} exit={r.returncode}')
 rows=[l.strip() for l in out.read_text(encoding='utf-8',errors='replace').splitlines() if l and not l.startswith('%')]
 trace=tr.read_text(encoding='utf-8',errors='replace')
 result=dict(name=name,output_epochs=len(rows),numeric_rows=rows,state_sha256=digest(str(out)+'.stat'),
  Q=dict(collections.Counter(l.split()[5] for l in rows)),
  input_epoch_records=[l[l.index('rtkpos  :'):] for l in trace.splitlines() if 'rtkpos  :' in l],
  reject_events=trace.count('$PPP_REJECT,'),legacy_slip_reinitializations=sum('$AMBRESET,' in l and ',SLIP,' in l for l in trace.splitlines()),
  detector_slip_events=sum(trace.count(s) for s in ['detslp_ll: slip detected','detslp_gf: slip ','$PRE_MW_SLIP,','$PRE_DOP_SLIP,']),
  failure_records=[l for l in trace.splitlines() if '$PPP_FAILURE,' in l],wall_seconds=time.monotonic()-start)
 print(json.dumps({k:v for k,v in result.items() if k not in ['numeric_rows','failure_records','input_epoch_records']}),flush=True)
 return result
if __name__=='__main__':
 old=run('rinex_97a57a9',OUT/'PPP_only_97a57a9.exe','B')
 new=run('rinex_B',ROOT/'x64/Release/PPP_only.exe','B')
 summary=dict(inputs=[dict(path=p,sha256=digest(p)) for p in FILES.values()],
  common_input_records_equal=old['input_epoch_records']==new['input_epoch_records'],
  common_input_epochs=len(old['input_epoch_records']),
  numeric_rows_equal=old['numeric_rows']==new['numeric_rows'],state_dump_equal=old['state_sha256']==new['state_sha256'],
  runs=[{k:v for k,v in s.items() if k not in ['numeric_rows','input_epoch_records']} for s in [old,new]])
 (OUT/'rinex_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in summary.items() if k not in ['runs','inputs']}),flush=True)
 if not (summary['numeric_rows_equal'] and summary['state_dump_equal'] and summary['common_input_records_equal'] and
   not new['failure_records'] and old['reject_events']==new['reject_events'] and old['detector_slip_events']==new['detector_slip_events']):
  raise RuntimeError('RINEX regression failed; inspect rinex_summary.json')
