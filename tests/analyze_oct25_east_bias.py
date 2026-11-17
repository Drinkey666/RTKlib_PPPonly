"""Read-only spatial and same-prior evidence for the new Oct25 east bias.

The code profile is NOT a PPP coordinate correction or an independent solution.
Delete-row diagnostics freeze the captured prior, weights and accepted membership.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import csv,json,math
from collections import Counter,defaultdict
from pathlib import Path
from four_sample_diagnosis import ROOT,read,save,np,P
from colocated_code_reference_trial import protect,csvwrite
import analyze_oct21_code_geometry_history as sparse
from analyze_admission_history_causal import packets,native,labels,solve
from audit_code_geometry_identifiability import project,fit,tests as geometry_tests

OUT=ROOT/'validation/oct25_east_bias_v1'
BASE=ROOT/'validation/android_live_20261025_v1'


def main():
    protect();tests=geometry_tests();ref=read(BASE/'reference.json')
    la=math.radians(ref['latitude_deg']);lo=math.radians(ref['longitude_deg'])
    rot=np.array([[-math.sin(lo),math.cos(lo),0],[-math.sin(la)*math.cos(lo),-math.sin(la)*math.sin(lo),math.cos(la)],[math.cos(la)*math.cos(lo),math.cos(la)*math.sin(lo),math.sin(la)]])
    origin=np.array(P.ecef(ref['latitude_deg'],ref['longitude_deg'],ref['ellipsoidal_height_m']))
    sparse.OUT=OUT;allp=list(sparse.packets());print('COMMITTED_CODE_EPOCHS',len(allp),flush=True)
    assert len(allp)==1549  # three committed epochs are later displayed as degraded SPP
    with (BASE/'live/ppp_b_verified_1792906436690.solution.csv').open() as f:
        qualities={i+1:int(row['Q']) for i,row in enumerate(csv.DictReader(f))}
    factors=[];ledger=[];group_stats=defaultdict(list);epoch_fits=[]
    for p in allp:
        rows=p['rows'];indices=sorted({int(k) for z in rows for k in z['ix']});index={k:i for i,k in enumerate(indices)}
        hp=np.array([z['hp'] for z in rows]);sigma=np.sqrt([z['R'] for z in rows]);B=np.zeros((len(rows),len(indices)))
        for j,z in enumerate(rows):B[j,[index[int(k)] for k in z['ix']]]=z['coef']
        A=hp@rot.T/sigma[:,None];y=(np.array([z['v'] for z in rows])+hp@(p['x']-origin))/sigma
        B/=sigma[:,None];a,b,rank,err=project(A,y,B);F=sparse.reduce_factor(a,b)
        factors.append(dict(epoch=p['epoch'],Q=qualities[p['epoch']],t=p['elapsed'],F=F,A=A,y=y,B=B,rows=rows))
        e=rot@(p['xp']-origin);pre=rot@(p['x']-origin);d=e-pre
        ledger.append(dict(epoch=p['epoch'],elapsed_s=p['elapsed'],Q=qualities[p['epoch']],prior_E_m=pre[0],post_E_m=e[0],update_E_m=d[0],
            prior_N_m=pre[1],post_N_m=e[1],update_N_m=d[1],prior_U_m=pre[2],post_U_m=e[2],update_U_m=d[2],
            posterior_sigma_E_m=np.sqrt((rot@p['cov']@rot.T)[0,0]),code_rows=len(rows),trial=p['trial']))
        ff=fit(a,b);epoch_fits.append(dict(epoch=p['epoch'],elapsed_s=p['elapsed'],**ff))
        for j,z in enumerate(rows):group_stats[z['sat'],z['signal']].append((p['elapsed'],z['v'],z['R']))
    csvwrite(OUT/'position_update_ledger.csv',ledger);csvwrite(OUT/'instant_code_profiles.csv',epoch_fits)
    windows=[(0,60),(60,300),(300,900),(900,1550),(60,1550),(300,1550)]
    profiles=[]
    for start,end in windows:
        ff=[p for p in factors if start<=p['t']<end and p['Q']==6]
        out=fit(np.vstack([p['F'][:,:3] for p in ff]),np.concatenate([p['F'][:,3] for p in ff]))
        profiles.append(dict(start_s=start,end_s=end,epochs=len(ff),**out))
    csvwrite(OUT/'code_spatial_profiles.csv',profiles);print('SPATIAL_PROFILES',json.dumps(profiles),flush=True)
    # Group influence on a reprofiled, code-only spatial diagnostic. Never a full PPP ablation.
    ff=[p for p in factors if p['t']>=60 and p['Q']==6]
    base=fit(np.vstack([p['F'][:,:3] for p in ff]),np.concatenate([p['F'][:,3] for p in ff]))
    variants=[('CONSTELLATION',s) for s in ['G','E','C']]
    variants += [('SATELLITE',s) for s in sorted({z['sat'] for p in ff for z in p['rows']})]
    influences=[]
    for kind,name in variants:
        pieces=[];removed=0
        for p in ff:
            keep=[j for j,z in enumerate(p['rows']) if not ((z['sat'][0] if kind=='CONSTELLATION' else z['sat'])==name)]
            removed+=len(p['rows'])-len(keep)
            if not keep:continue
            a,b,_,_=project(p['A'][keep],p['y'][keep],p['B'][keep]);pieces.append(sparse.reduce_factor(a,b))
        out=fit(np.vstack([p[:,:3] for p in pieces]),np.concatenate([p[:,3] for p in pieces]))
        influences.append(dict(kind=kind,name=name,removed_code_rows=removed,**out,
            delta_E_from_full_m=out.get('E',float('nan'))-base['E']))
    csvwrite(OUT/'code_profile_group_influence.csv',influences)
    print('SPATIAL_INFLUENCE',json.dumps(sorted(influences,key=lambda x:abs(x['delta_E_from_full_m']),reverse=True)[:10]),flush=True)

    # Frozen native filter updates, with the same verified Joseph implementation as production.
    call=native();checks=[];contributions=[];row_effects=[];group_effects=[];state_updates=[]
    for p in packets(OUT/'OBSERVE'):
        xp,cov,K,S=call(*[p[k] for k in ['x','P','H','v','R']])
        assert np.array_equal(xp,p['xp']) and np.array_equal(cov,p['Pp']),(p['epoch'],'native mismatch')
        pos=[int(np.where(p['ix']==k)[0][0]) for k in (0,1,2)];KE=rot@K[pos,:]
        inc=rot@(xp[pos]-p['x'][pos]);prior=rot@(p['x'][pos]-origin);post=rot@(xp[pos]-origin)
        residual=np.linalg.norm(K@S-p['P']@p['H'])/np.linalg.norm(p['P']@p['H'])
        checks.append(dict(epoch=p['epoch'],native_x_P_exact=True,solve_relative_residual=float(residual),
            sum_Kv_vs_state_increment_m=float(np.max(abs(KE@p['v']-inc)))))
        classes={1:'CODE',2:'PHASE',3:'IONO_PRIOR',4:'TROP_PRIOR'}
        # Actual meta enum order is verified against the production header below.
        masks=defaultdict(list)
        for j,z in p['meta'].items():masks[z['class']].append(j)
        for klass,jj in masks.items():
            dx=KE[:,jj]@p['v'][jj]
            contributions.append(dict(epoch=p['epoch'],elapsed_s=p['elapsed'],measurement_class=klass,rows=len(jj),
                prior_E_m=prior[0],post_E_m=post[0],delta_E_m=dx[0],delta_N_m=dx[1],delta_U_m=dx[2],
                total_E_update_m=inc[0],note='Same-update K*v ledger; not final trajectory attribution'))
        wv=solve(S,p['v'])
        for j,z in p['meta'].items():
            ej=np.zeros(len(p['v']));ej[j]=1.;wj=solve(S,ej);cond=wv[j]/wj[j];effect=-KE[:,j]*cond
            row_effects.append(dict(epoch=p['epoch'],elapsed_s=p['elapsed'],row=j,sat=z['sat'],signal=z['signal'],
                measurement_class=z['class'],v_m=p['v'][j],R_m2=p['R'][j,j],Sii_m2=S[j,j],u=p['v'][j]/np.sqrt(S[j,j]),
                direct_Kv_E_m=KE[0,j]*p['v'][j],conditional_v_m=cond,remove_E_m=effect[0],remove_N_m=effect[1],remove_U_m=effect[2]))
        for name,remove in [('ALL_CODE',[j for j,z in p['meta'].items() if z['class']=='1']),
                            ('ALL_PHASE',[j for j,z in p['meta'].items() if z['class']=='2']),
                            ('ALL_VIRTUAL',[j for j,z in p['meta'].items() if z['class'] not in ['1','2']])]:
            keep=[j for j in range(len(p['v'])) if j not in remove]
            if not remove or not keep:continue
            x2,_,_,_=call(p['x'],p['P'],p['H'][:,keep],p['v'][keep],p['R'][np.ix_(keep,keep)])
            d=rot@(x2[pos]-xp[pos]);group_effects.append(dict(epoch=p['epoch'],elapsed_s=p['elapsed'],removed=name,rows=len(remove),
                delta_E_m=d[0],delta_N_m=d[1],delta_U_m=d[2],note='Local frozen-prior/weights/selection; not a full rerun'))
        for name,mask in labels(p).items():
            ids=np.where(mask)[0];d=xp[ids]-p['x'][ids]
            state_updates.append(dict(epoch=p['epoch'],elapsed_s=p['elapsed'],group=name,
                states=len(ids),max_abs_update_m=float(max(abs(d))) if len(ids) else 0.,
                mean_update_m=float(np.mean(d)) if len(ids) else 0.))
    for name,rows in [('native_update_checks.csv',checks),('snapshot_class_update_ledger.csv',contributions),
                      ('snapshot_local_row_removal.csv',row_effects),('snapshot_local_group_removal.csv',group_effects),
                      ('snapshot_state_updates.csv',state_updates)]:csvwrite(OUT/name,rows)
    print('LOCAL_CODE_REMOVALS',json.dumps([x for x in group_effects if x['removed']=='ALL_CODE']),flush=True)
    print('EARLY_ROW_REMOVALS',json.dumps(sorted([x for x in row_effects if x['epoch']<=61],key=lambda x:abs(x['remove_E_m']),reverse=True)[:16]),flush=True)
    save(OUT/'summary.json',dict(code_epochs=len(allp),code_rows=sum(len(p['rows']) for p in allp),
        profiles=profiles,top_code_profile_group_influence=sorted(influences,key=lambda x:abs(x['delta_E_from_full_m']),reverse=True)[:10],
        captured_updates=len(checks),native_updates_bitexact=True,geometry_tests=tests,
        max_solve_relative_residual=max(x['solve_relative_residual'] for x in checks),
        max_Kv_reconstruction_m=max(x['sum_Kv_vs_state_increment_m'] for x in checks),
        formal_files_unchanged=len(protect()),default_algorithm_changed=False))


if __name__=='__main__':main()
