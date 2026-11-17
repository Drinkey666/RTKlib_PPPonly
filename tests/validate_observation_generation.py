"""Raw -> actual C adapter / JVM audit / emitted RINEX; no PPP or parameter fitting."""
from pathlib import Path
import csv,gzip,subprocess,json,math,statistics,hashlib,datetime,decimal,struct
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/observation_generation_2023_v1'
INPUTS={
 'K70_early':Path('E:/RTKLIB_Data/k70/RawData_20261018_082050.txt'),
 'K70_late':Path('E:/RTKLIB_Data/k70/RawData_20261018_084040.txt'),
 'K70_oct21':Path('E:/RTKLIB_Data/10.21/RawData_20261021_102241.txt'),
 'K70_oct25':ROOT/'validation/android_live_20261025_v1/inputs/RawData_20261025_133353.txt'}
SYS={1:'G',3:'R',6:'E',5:'C',4:'J'}
C=299792458.
def val(x):return None if x in ('','null') else float(x)
def quantile(x,q):
 x=sorted(x);return x[min(len(x)-1,int((len(x)-1)*q))] if x else None
def stats(x):
 return {'N':len(x),'median':statistics.median(x) if x else None,'p95_abs':quantile(list(map(abs,x)),.95),'max_abs':max(map(abs,x),default=None)}
def rnx(path):
 types={};output={};tick=None;system=None
 opener=gzip.open(path.with_suffix(path.suffix+'.gz'),'rt',encoding='utf-8') if not path.exists() else path.open(encoding='utf-8')
 with opener as f:lines=f.read().splitlines()
 for l in lines:
  if l[60:].strip()=='SYS / # / OBS TYPES':
   if l[0]!=' ':system=l[0];types[system]=[]
   types[system]+=l[6:60].split()
  elif l.startswith('>'):
   a=l.split();base=datetime.datetime(*map(int,a[1:6]))
   tick=int((base-datetime.datetime(1980,1,6)).total_seconds())*10**9+int(decimal.Decimal(a[6])*10**9)
  elif tick is not None and l[:1] in types:
   for i,t in enumerate(types[l[0]]):
    field=l[3+16*i:3+16*(i+1)].ljust(16)
    output[tick,l[:3],t]=(val(field[:14].strip()),int(field[14]) if field[14].strip() else 0)
 return output
def main():
 report={};failures=[]
 for name,path in INPUTS.items():
  native=OUT/f'{name}.native.csv.gz'
  with gzip.open(native,'wb') as w:
   process=subprocess.Popen([str(OUT/'native_probe.exe'),str(path)],stdout=subprocess.PIPE)
   while data:=process.stdout.read(1024*1024):w.write(data)
   assert process.wait()==0
  with gzip.open(OUT/f'{name}.kotlin.csv.gz','rt',encoding='utf-8') as f:ka=list(csv.DictReader(f))
  bysource={int(a['source_row']):a for a in ka};rn=rnx(OUT/f'{name}.rnx')
  raw={i:l.split(',') for i,l in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1) if l.startswith('Raw,')}
  raw_checks=0;references={}
  for a in ka:
   r=raw[int(a['source_row'])]
   if not a['rx_ns']:continue
   assert int(r[2])==int(a['time_nanos']) and int(r[5])==int(a['raw_full_bias'])
   exact=decimal.Decimal(int(r[2])-int(a['reference_full_bias']))-decimal.Decimal(a['reference_bias'])+decimal.Decimal(r[12] or '0')
   got=decimal.Decimal(a['rx_ns'])+decimal.Decimal(a['rx_fraction_ns'])
   assert abs(exact-got)<decimal.Decimal('0.000001')
   ref=(a['reference_full_bias'],a['reference_bias'])
   if a['segment'] in references:assert references[a['segment']]==ref
   else:references[a['segment']]=ref
   f=val(a['frequency_hz']);lam=C/f
   if a['L']:
    assert int(r[19])&1 and not int(r[19])&6
    assert abs(float(a['L'])-float(r[20])/lam)<1e-8
   if a['D']:assert abs(float(a['D'])+float(r[17])/lam)<1e-8
   raw_checks+=1
  diffs={'P':[],'L':[],'D':[]};nm=0;lli_diff=0;missing=0;rnx_checks=0;rnx_max={'P':0.,'L':0.,'D':0.}
  for a in ka:
   if not a['rx_ns'] or not a['signal']:continue
   ns=int(a['rx_ns']);tick=(ns//100+(1 if ns%100+float(a['rx_fraction_ns'])>=50 else 0))*100
   sat=f"{SYS[int(a['system'])]}{int(a['svid']):02d}"
   for typ,rtyp in [('P','C'),('L','L'),('D','D')]:
    wanted=val(a[typ]);got=rn.get((tick,sat,rtyp+a['signal']))
    if wanted is None:continue
    if got is None or got[0] is None:failures.append([name,'RINEX_MISSING',a['source_row'],typ]);continue
    error=abs(wanted-got[0]);rnx_max[typ]=max(error,rnx_max[typ]);rnx_checks+=1
    if error>.000501:failures.append([name,'RINEX_ROUNDING',a['source_row'],typ,error])
    if typ=='L' and got[1]!=int(a['lli']):failures.append([name,'RINEX_LLI',a['source_row']])
  last_phase={};lli_explained=0;slots={}
  with gzip.open(native,'rt',encoding='utf-8') as f:native_rows=list(csv.DictReader(f))
  for n in native_rows:slots.setdefault((n['sat'],n['slot']),set()).add(n['signal'])
  for n in native_rows:
    a=bysource.get(int(n['source_row']))
    if not a or a['signal']!=n['signal']:missing+=1;continue
    nm+=1
    for typ in diffs:
     nv=float(n[typ]);kv=val(a[typ]);kv=kv if kv is not None else 0.
     if typ=='D':kv=struct.unpack('f',struct.pack('f',kv))[0]
     d=abs(nv-kv);diffs[typ].append(d)
     if d>1e-7:failures.append([name,'C_JVM',n['source_row'],typ,d])
    cn0=float(raw[int(n['source_row'])][16]);expected_cn0=min(65535,math.floor(cn0/.001+.5))*.001 if math.isfinite(cn0) and cn0>0 else 0.
    if abs(float(n['CN0'])-expected_cn0)>1e-7:failures.append([name,'CN0_STORAGE_UNIT',n['source_row']])
    slotkey=(n['sat'],n['slot']);previous_signal=last_phase.get(slotkey)
    if int(n['lli'])!=int(a['lli']):
     lli_diff+=1
     if int(a['system'])==5 and slots[slotkey]=={'1P','2I'} and (int(n['lli'])^int(a['lli']))==1:lli_explained+=1
     else:failures.append([name,'UNEXPLAINED_LLI',n['source_row'],previous_signal,n['signal'],n['lli'],a['lli']])
    if float(n['L'])!=0:last_phase[slotkey]=n['signal']
  previous={};cp=[];ld=[];cp_by_epoch={};status={};epochs=set();ld_groups={};ld_examples=[]
  for a in ka:
   status[a['status']]=status.get(a['status'],0)+1;epochs.add(a['time_nanos'])
   key=(a['system'],a['svid'],a['signal'],a['segment'])
   p,l,d=val(a['P']),val(a['L']),val(a['D']);f=val(a['frequency_hz'])
   old=previous.get(key);previous[key]=a
   if old is None or not f or int(a['lli'])&1 or int(old['lli'])&1:continue
   dt=((int(a['rx_ns'])-int(old['rx_ns']))+float(a['rx_fraction_ns'])-float(old['rx_fraction_ns']))*1e-9
   op,ol,od=val(old['P']),val(old['L']),val(old['D'])
   if not (0<dt<=1.5 and l is not None and ol is not None):continue
   lm=(l-ol)*C/f
   if d is not None and od is not None:
    e=lm+.5*(d+od)*C/f*dt;ld.append(e);ld_groups.setdefault((a['system'],a['signal']),[]).append(e)
    ra,rb=raw[int(a['source_row'])],raw[int(old['source_row'])]
    direct=float(ra[20])-float(rb[20])-.5*(float(ra[17])+float(rb[17]))*dt
    assert abs(direct-e)<1e-6,('Raw vs generated phase-Doppler diagnostic',a['source_row'])
    if abs(e)>100 and len(ld_examples)<2:
     ld_examples.append({'source_row':a['source_row'],'previous_source_row':old['source_row'],
      'system':a['system'],'svid':a['svid'],'signal':a['signal'],'dt_s':dt,
      'raw_ADR_increment_m':float(ra[20])-float(rb[20]),'raw_PRR_integral_m':.5*(float(ra[17])+float(rb[17]))*dt,
      'raw_difference_m':direct,'generated_difference_m':e})
   if p is not None and op is not None:
    error=p-op-lm;cp.append(error);cp_by_epoch.setdefault(a['time_nanos'],[]).append(error)
  epoch_stats={e:{'N':len(x),'median':statistics.median(x)} for e,x in cp_by_epoch.items() if len(x)>=3}
  report[name]={'input':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'raw_field_checks':raw_checks,
    'raw_supported_rows':len(ka),'callbacks':len(epochs),'native_common_rows':nm,'native_unmapped':missing,
    'native_jvm_max':{k:max(v,default=0) for k,v in diffs.items()},'native_jvm_lli_differences':lli_diff,'lli_explained_by_native_slot_switch':lli_explained,
    'rinex_value_checks':rnx_checks,'rinex_rounding_max':rnx_max,'statuses':status,
    'continuous_phase_doppler_m':stats(ld),'phase_doppler_by_signal':{str(k):stats(v) for k,v in ld_groups.items()},
    'phase_doppler_raw_source_examples':ld_examples,'continuous_code_phase_increment_m':stats(cp),
    'epoch_common_code_phase_increment':epoch_stats}
  print(name,'rows',len(ka),'native common',nm,'LLI diff',lli_diff,'failures',len(failures),flush=True)
 (OUT/'validation_results.json').write_text(json.dumps({'datasets':report,'failures':failures},indent=2),encoding='utf-8')
 assert not failures,f'{len(failures)} comparison failures; inspect JSON'
if __name__=='__main__':main()
