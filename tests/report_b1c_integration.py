"""Check actual B1I/B1C participation and evaluate a fixed-input replay."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,gzip,json,sys
from run_b1c_integration import ROOT,OUT,EXE,sha,save
from analyze_oct31_reference_diagnosis import load as baseline_load,errors,stats,POINTS
from report_oct31_segments import np,plt

def observations(folder):
    result={}
    with gzip.open(folder/'solution.csv.obs.csv.gz','rt') as f:
        for a in csv.DictReader(f):
            k=(a['week'],a['tow'],a['sat'],a['signal'],a['slot']);assert k not in result;result[k]=a
    return result

def main():
    results={};arrays={}
    for device,point in [('k70','Pt40'),('iq','Pt42')]:
        folder=OUT/(device+'_with_b1c');receipt=json.loads((folder/'run.json').read_text(encoding='utf-8'));assert receipt['completed']
        with (folder/'solution.csv').open() as f:rows=list(csv.DictReader(f))
        t=np.array([int(a['week'])*604800+float(a['tow']) for a in rows]);q=np.array([int(a['Q']) for a in rows])
        xyz=np.array([[float(a[k]) for k in ['x_m','y_m','z_m']] for a in rows]);assert np.all(np.isfinite(xyz))
        new=dict(rows=rows,t=t,elapsed=t-t[0],q=q,xyz=xyz);old=baseline_load(device);assert np.array_equal(t,old['t'])
        old_obs=observations(ROOT/'validation/oct31_reference_diagnosis_v1'/device);new_obs=observations(folder)
        extras=set(new_obs)-set(old_obs);assert set(old_obs)<=set(new_obs)
        assert all(old_obs[k]==new_obs[k] for k in old_obs),'existing signal changed in adapter'
        assert all(k[2].startswith('C') and k[3]=='1P' and k[4]=='4' for k in extras)
        assert not any(a['sat'].startswith('C') and a['signal'] in ['7D','7P','7Z','5Q'] for a in new_obs.values())
        extra=[new_obs[k] for k in sorted(extras)];by_sat=defaultdict(Counter)
        for a in extra:
            c=by_sat[a['sat']];c['rows']+=1;c['raw_P']+=float(a['P_m'])!=0;c['raw_L']+=float(a['L_cycle'])!=0
        identities={(a['week'],round(float(a['tow']),3),a['sat'],a['slot']):a for a in new_obs.values()}
        accepted=Counter();rcb=[];b1c_code_cache=0
        with gzip.open(folder/'solution.csv.stat.gz','rt') as f:
            for line in f:
                a=line.strip().split(',')
                if a[0]=='$RCB' and a[3]=='6' and a[4]=='BDS_C1P':rcb.append([float(a[5]),float(a[6])])
                if a[0]!='$SAT':continue
                key=(a[1],round(float(a[2]),3),a[3],a[4]);obs=identities.get(key)
                if obs is None:
                    assert a[9]!='1';continue
                if a[9]=='1':
                    assert float(obs['L_cycle'])!=0;accepted[a[3][0]+':'+obs['signal']]+=1
                    if obs['signal']=='1P' and obs['sat'].startswith('C'):by_sat[a[3]]['accepted_phase']+=1
                if obs['signal']=='1P' and obs['sat'].startswith('C') and float(a[7])!=0:b1c_code_cache+=1
        assert accepted['C:1P']>0 and accepted['C:2I']>0 and rcb
        assert max(abs(v[0]) for v in rcb)>.001,'C1P receiver bias never updated'
        tags=Counter()
        with gzip.open(folder/'solution.trace.gz','rt') as f:
            for line in f:
                p=line.find('$')
                if p>=0:tags[line[p:].split(',')[0].split()[0]]+=1
        assert tags['$PPP_FAILURE']==0
        e0=errors(old,POINTS[point]);e1=errors(new,POINTS[point]);arrays[device]=(old,new,e0,e1)
        late=(q==6)&(old['q']==6)&(new['elapsed']>=new['elapsed'][-1]-300)
        results[device]=dict(reference=point,baseline=stats(old,e0),with_B1C=stats(new,e1),
            alternative_reference=stats(new,errors(new,POINTS['Pt39' if device=='k70' else 'Pt41'])),
            Q_changed_epochs=int(sum(q!=old['q'])),last300_mean_delta_ENU_m=np.mean((e1-e0)[late],axis=0).tolist(),
            existing_adapter_rows_exact=len(old_obs),added_B1C_rows=len(extra),B1C_raw_P=sum(c['raw_P'] for c in by_sat.values()),
            B1C_raw_L=sum(c['raw_L'] for c in by_sat.values()),accepted_phase_by_signal=dict(accepted),
            B1C_nonzero_code_residual_cache_rows=b1c_code_cache,BDS_C1P_RCB_first_last_m=[rcb[0][0],rcb[-1][0]],
            BDS_C1P_RCB_std_first_last_m=[rcb[0][1],rcb[-1][1]],trace_tags=dict(tags),per_satellite=dict(by_sat),
            IQ_Q_admission_unchanged=True,B2b_excluded=True)
        current_folder=OUT/(device+'_with_b1c_new_atx')
        current_receipt=json.loads((current_folder/'run.json').read_text(encoding='utf-8'));assert current_receipt['completed']
        assert current_receipt['compressed_logs']['solution.csv.obs.csv']['uncompressed_sha256']==receipt['compressed_logs']['solution.csv.obs.csv']['uncompressed_sha256']
        with (current_folder/'solution.csv').open() as f:current_rows=list(csv.DictReader(f))
        ct=np.array([int(a['week'])*604800+float(a['tow']) for a in current_rows]);assert np.array_equal(ct,t)
        current=dict(rows=current_rows,t=ct,elapsed=ct-ct[0],q=np.array([int(a['Q']) for a in current_rows]),xyz=np.array([[float(a[k]) for k in ['x_m','y_m','z_m']] for a in current_rows]))
        ec=errors(current,POINTS[point]);accepted_current=Counter();current_rcb=[];current_satellites=Counter();current_tags=Counter()
        with gzip.open(current_folder/'solution.csv.stat.gz','rt') as f:
            for line in f:
                a=line.strip().split(',')
                if a[0]=='$RCB' and a[3]=='6' and a[4]=='BDS_C1P':current_rcb.append(float(a[5]))
                if a[0]!='$SAT' or a[9]!='1':continue
                obs=identities[a[1],round(float(a[2]),3),a[3],a[4]];assert float(obs['L_cycle'])!=0
                accepted_current[a[3][0]+':'+obs['signal']]+=1
                if a[3].startswith('C') and obs['signal']=='1P':current_satellites[a[3]]+=1
        with gzip.open(current_folder/'solution.trace.gz','rt') as f:
            for line in f:
                p=line.find('$')
                if p>=0:current_tags[line[p:].split(',')[0].split()[0]]+=1
        assert current_tags['$PPP_FAILURE']==0 and accepted_current['C:1P']>0 and accepted_current['C:2I']>0
        results[device]['with_B1C_current_ANTEX']=dict(metrics=stats(current,ec),accepted_phase_by_signal=dict(accepted_current),
            BDS_C1P_RCB_first_last_m=[current_rcb[0],current_rcb[-1]],B1C_accepted_by_satellite=dict(current_satellites),
            adapter_exact_to_original_ATX_run=True,Q_changed_from_baseline=int(sum(current['q']!=old['q'])),trace_tags=dict(current_tags))
        arrays[device]=(old,new,e0,e1,current,ec)
    summary=dict(date='2026-11-10',results=results,replay_executable_sha256=sha(EXE),standard_executable_sha256=sha(ROOT/'x64/Release/PPP_only.exe'),
        tests=json.loads((OUT/'unit/results.json').read_text(encoding='utf-8')),
        scope='B1I 2I and B1C 1P admitted simultaneously; same original products; no stochastic tuning or Q alias',
        antenna_risk='Original and current ATX separately replayed. Current date/identity/C01 coverage checked; NRT clock-reference compatibility not fully certified.')
    save(OUT/'summary.json',summary)
    with (OUT/'satellite_participation.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['device','sat','B1C_rows','raw_P','raw_L','accepted_phase'])
        for d,r in results.items():
            for sat,c in sorted(r['per_satellite'].items()):w.writerow([d,sat,*[c.get(k,0) for k in ['rows','raw_P','raw_L','accepted_phase']]])
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10})
    fig,axes=plt.subplots(2,2,figsize=(12,7),sharex='col',layout='constrained')
    for col,device in enumerate(['k70','iq']):
        old,new,e0,e1,current,ec=arrays[device]
        for a,e,label,color in [(old,e0,'原配置','#2166ac'),(new,e1,'加入 B1C · 原天线','#c34c38'),(current,ec,'加入 B1C · 更新天线','#16866c')]:
            values=[np.linalg.norm(e[:,:2],axis=1),e[:,2]]
            for row,v in enumerate(values):axes[row,col].plot(a['elapsed']/60,np.where(a['q']==6,v,np.nan),label=label,color=color,lw=1.1)
        axes[0,col].set_title(device.upper()+' · '+results[device]['reference']);axes[0,col].legend()
        axes[1,col].set_xlabel('采集起点后 / min')
        for row,label in enumerate(['水平误差 / m','高程误差 U / m']):
            axes[row,col].set_ylabel(label);axes[row,col].grid(alpha=.2)
    fig.suptitle('10/31 B1I 与 B1C 同时参与 PPP\n信号接入与天线更新分开对照；轨钟/BIA及参数不变，B2b排除，IQ Q暂停',fontsize=13)
    fig.savefig(OUT/'B1I_B1C_COMPARISON.png',dpi=160);plt.close(fig)
    print(json.dumps({d:{k:r[k] for k in ['added_B1C_rows','B1C_raw_L','accepted_phase_by_signal','BDS_C1P_RCB_first_last_m','Q_changed_epochs']} for d,r in results.items()},indent=2))
if __name__=='__main__':main()
