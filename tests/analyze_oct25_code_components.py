"""Fixed-row/R/H physical components on new Oct25 data, no filter operations."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import csv,gzip,math
from collections import Counter
from four_sample_diagnosis import ROOT,read,save,np,P
from colocated_code_reference_trial import protect,csvwrite
import analyze_oct21_code_geometry_history as sparse
from audit_code_geometry_identifiability import project
from audit_oct21_physical_component_projection import solve_multi

OUT=ROOT/'validation/oct25_east_bias_v1'
BASE=ROOT/'validation/android_live_20261025_v1'
NAMES=['RAW_RANGE_CLOCK','NEGATIVE_ANTENNA','NEGATIVE_OSB','CODE_FALLBACK_REMAINDER','NEGATIVE_MODEL_TROP',
       'NEGATIVE_GIM_IONO','RAW_MODEL_TARGET','ACTUAL_USED_TARGET','USED_MINUS_RAW_MODEL','NRT_MINUS_RTS_OSB_ONLY']


def main():
    protect();ref=read(BASE/'reference.json');la=math.radians(ref['latitude_deg']);lo=math.radians(ref['longitude_deg'])
    rot=np.array([[-math.sin(lo),math.cos(lo),0],[-math.sin(la)*math.cos(lo),-math.sin(la)*math.sin(lo),math.cos(la)],[math.cos(la)*math.cos(lo),math.cos(la)*math.sin(lo),math.sin(la)]])
    origin=np.array(P.ecef(ref['latitude_deg'],ref['longitude_deg'],ref['ellipsoidal_height_m']))
    def bia(path):
        out={}
        for s in path.read_text().splitlines():
            if not s.startswith(' OSB'):continue
            a=s.split()
            if a[3].startswith('C'):
                j=a.index('ns');out[a[2],a[3]]=float(a[j+1])*.299792458
        return out
    rt=bia(BASE/'inputs/WUM0MGXRTS_20262980000_01D_05M_OSB.BIA')
    nr=bia(OUT/'products/WUM0MGXNRT_20262970700_01D_01D_OSB.BIA')
    gauge=[]
    for product,table in [('RTS',rt),('NRT',nr)]:
        for system,s1,s2,f1,f2 in [('G','C1W','C2W',1575.42,1227.60),('E','C1C','C5Q',1575.42,1176.45),('C','C2I','C6I',1561.098,1268.52)]:
            alpha=f1*f1/(f1*f1-f2*f2)
            values=[alpha*table[s,s1]+(1-alpha)*table[s,s2] for s in {s for s,c in table if s[0]==system} if (s,s1) in table and (s,s2) in table]
            gauge.append(dict(product=product,system=system,reference_signals=s1+'/'+s2,satellites=len(values),max_abs_IF_clock_gauge_m=max(abs(v) for v in values)))
    save(OUT/'bias_clock_gauge_audit.json',dict(reference_gauges=gauge,note='Both products satisfy these zero-IF code gauges to tabular precision. Not a full phase/antenna or all-signal compatibility certificate.'))
    with gzip.open(OUT/'query/native_model.csv.gz','rt') as f:
        models={(int(r['epoch']),r['sat'],r['signal']):r for r in csv.DictReader(f)}
    with (BASE/'live/ppp_b_verified_1792906436690.solution.csv').open() as f:
        qualities={i+1:int(row['Q']) for i,row in enumerate(csv.DictReader(f))}
    sparse.OUT=OUT;allp=list(sparse.packets());cache=[];matched=0;missing=[];fallback=Counter();snapshot=[]
    for p in allp:
        rr=p['rows'];ids=sorted({int(k) for r in rr for k in r['ix']});index={k:i for i,k in enumerate(ids)}
        B=np.zeros((len(rr),len(ids)));hp=np.array([r['hp'] for r in rr]);sigma=np.sqrt([r['R'] for r in rr]);A=hp@rot.T/sigma[:,None]
        target=np.array([r['v'] for r in rr])+hp@(p['x']-origin);Y=[]
        for i,r in enumerate(rr):
            model=models.get((p['epoch'],r['sat'],r['signal']))
            if model is None:missing.append((p['epoch'],r['sat'],r['signal']));continue
            m={k:float(v) for k,v in model.items() if k.endswith('_m') or k in ['OSB_status']}
            raw=m['raw_P_m']-m['geometry_m']+m['sat_clock_m'];ant=-m['sat_antenna_m']-m['rx_antenna_m'];osb=-m['OSB_m']
            other=m['corrected_P_m']-m['raw_P_m']-ant-osb;trp=-m['trop_m'];ion=-m['iono_m'];rawtarget=raw+ant+osb+other+trp+ion
            assert abs(rawtarget-(m['corrected_P_m']-m['model_without_receiver_states_m']))<2e-8
            codekey=r['sat'],'C'+r['signal']
            assert (codekey in rt)==(codekey in nr),('Availability differs: no pure OSB-only comparison',codekey)
            delta=-(nr.get(codekey,0.)-rt.get(codekey,0.))
            Y.append([raw,ant,osb,other,trp,ion,rawtarget,target[i],target[i]-rawtarget,delta]);matched+=1
            fallback[int(m['OSB_status'])]+=1
            B[i,[index[int(k)] for k in r['ix']]]=r['coef']
        assert not missing,missing[:5]
        B/=sigma[:,None];Y=np.array(Y)/sigma[:,None];a,z,_,_=project(A,Y,B)
        # Small QR compression preserves all projected normal equations for later windows.
        full=np.c_[a,z];factor=np.linalg.qr(full,mode='r')
        if qualities[p['epoch']]==6:cache.append((p['elapsed'],factor))
    results=[];maxnormal=0.
    for start,end in [(0,60),(60,300),(300,900),(900,1550),(60,1550),(300,1550)]:
        ff=[v for t,v in cache if start<=t<end];a=np.vstack([v[:,:3] for v in ff]);Y=np.vstack([v[:,3:] for v in ff]);x,normal=solve_multi(a,Y);maxnormal=max(maxnormal,normal)
        assert np.max(abs(x[:,0:6].sum(axis=1)-x[:,6]))<1e-6
        assert np.max(abs(x[:,7]-x[:,6]-x[:,8]))<1e-6
        for i,name in enumerate(NAMES):results.append(dict(start_s=start,end_s=end,component=name,E_m=x[0,i],N_m=x[1,i],U_m=x[2,i],normal_relative_residual=normal))
    csvwrite(OUT/'code_physical_components.csv',results)
    save(OUT/'component_summary.json',dict(actual_rows_matched=matched,missing_rows=missing,OSB_status_counts=dict(fallback),
        max_normal_equation_relative=maxnormal,components=results,
        warning='Projected physical components are neither correction errors nor PPP trajectory changes. USED_MINUS_RAW includes smoothing and state/position linearization differences, not a certified pure smoother ablation.',
        filter_calls=0,default_changes=False,formal_files_unchanged=len(protect())))
    for r in results:
        if r['start_s']==60 and r['end_s']==1550:print(r['component'],r['E_m'],r['N_m'],r['U_m'])


if __name__=='__main__':main()
