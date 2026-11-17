"""Compare newly available archived RTS products on frozen actual Oct25 code rows.

No full RTS positioning replay. All comparison and control profiles use exactly
the common rows; global clock offsets are eliminated by the existing nuisance H.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import csv,gzip,math
from collections import Counter,defaultdict
from four_sample_diagnosis import ROOT,read,save,np,P
from colocated_code_reference_trial import protect,csvwrite
import analyze_oct21_code_geometry_history as sparse
from audit_code_geometry_identifiability import project
from audit_oct21_physical_component_projection import solve_multi

OUT=ROOT/'validation/oct25_east_bias_v1'
BASE=ROOT/'validation/android_live_20261025_v1'


def main():
    protect();ref=read(BASE/'reference.json');la=math.radians(ref['latitude_deg']);lo=math.radians(ref['longitude_deg'])
    rot=np.array([[-math.sin(lo),math.cos(lo),0],[-math.sin(la)*math.cos(lo),-math.sin(la)*math.sin(lo),math.cos(la)],[math.cos(la)*math.cos(lo),math.cos(la)*math.sin(lo),math.sin(la)]])
    model={}
    for kind,filename in [('NRT','native_model.csv.gz'),('RTS_CLOCK','native_model_rts_clock.csv.gz'),('RTS_PAIR','native_model_rts_pair.csv.gz')]:
        with gzip.open(OUT/'query'/filename,'rt') as f:model[kind]={(int(a['epoch']),a['sat'],a['signal']):a for a in csv.DictReader(f)}
    with (BASE/'live/ppp_b_verified_1792906436690.solution.csv').open() as f:qualities={i+1:int(a['Q']) for i,a in enumerate(csv.DictReader(f))}
    results=[];missing={};differences=[];sparse.OUT=OUT;pp=list(sparse.packets())
    for kind in ['RTS_CLOCK','RTS_PAIR']:
        stack=[];lost=Counter();matched=0;by=defaultdict(list);orbit=defaultdict(list)
        for p in pp:
            if p['elapsed']<60 or qualities[p['epoch']]!=6:continue
            rows=[]
            for z in p['rows']:
                k=p['epoch'],z['sat'],z['signal']
                if k in model[kind]:rows.append(z)
                else:lost[z['sat']]+=1
            ids=sorted({int(k) for z in rows for k in z['ix']});idx={k:i for i,k in enumerate(ids)};B=np.zeros((len(rows),len(ids)))
            sig=np.sqrt([z['R'] for z in rows]);A=np.array([z['hp'] for z in rows])@rot.T/sig[:,None];Y=[]
            for j,z in enumerate(rows):
                k=p['epoch'],z['sat'],z['signal'];a,b=model['NRT'][k],model[kind][k]
                qa=float(a['corrected_P_m'])-float(a['model_without_receiver_states_m']);qb=float(b['corrected_P_m'])-float(b['model_without_receiver_states_m'])
                Y.append([qa,qb,qb-qa]);matched+=1
                by[z['sat']].append(float(b['sat_clock_m'])-float(a['sat_clock_m']))
                orbit[z['sat']].append(float(np.linalg.norm(np.array([float(b[c])-float(a[c]) for c in ['sat_X','sat_Y','sat_Z']]))))
                B[j,[idx[int(k)] for k in z['ix']]]=z['coef']
            a,y,_,_=project(A,np.array(Y)/sig[:,None],B/sig[:,None]);stack.append(np.linalg.qr(np.c_[a,y],mode='r'))
        a=np.vstack([z[:,:3] for z in stack]);y=np.vstack([z[:,3:] for z in stack]);x,res=solve_multi(a,y)
        assert np.max(abs(x[:,1]-x[:,0]-x[:,2]))<1e-6
        result=dict(kind=kind,matched_rows=matched,unmatched_rows_by_sat=dict(lost),
            NRT_common_rows_ENU_m=x[:,0].tolist(),RTS_common_rows_ENU_m=x[:,1].tolist(),
            change_ENU_m=x[:,2].tolist(),normal_relative_residual=res,
            warning='Not a complete PPP rerun or an independently truth-calibrated RTS reference. Orbit COM/APC/frame conventions are not fully certified; do not interpret raw common clock offset as position error.')
        results.append(result)
        for sat,values in by.items():differences.append(dict(kind=kind,sat=sat,N=len(values),clock_difference_median_m=float(np.median(values)),
            clock_difference_min_m=min(values),clock_difference_max_m=max(values),max_orbit_coordinate_difference_m=max(orbit[sat])))
    csvwrite(OUT/'RTS_product_satellite_differences.csv',differences)
    save(OUT/'RTS_product_comparison.json',dict(results=results,filter_calls=0,default_changes=False,
        downloaded_after_capture=True,formal_files_unchanged=len(protect())))
    for r in results:print(r)


if __name__=='__main__':main()
