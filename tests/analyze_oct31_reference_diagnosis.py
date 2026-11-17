"""Audit four evaluation points, paired baselines and a single B2a ablation."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, gzip, json, math, sys
from run_oct31_reference_diagnosis import ROOT, OUT, CASES, sha, save
from report_oct31_segments import np, plt, ecef, rms, sustained

POINTS=json.loads((OUT/'reference.json').read_text(encoding='utf-8'))
POINTS={p['id']:p for p in POINTS['points']}
RUNS={'k70':('k70','Pt40'),'iq':('iq','Pt42'),'k70_without_b2a':('k70','Pt40'),
      'iq_without_c7i':('iq','Pt42'),'k70_iq_phase_gaps':('k70','Pt40')}
LABEL={'k70':'K70 · 原配置','iq':'IQ · 原配置','k70_without_b2a':'K70 · 去掉 B2a',
       'iq_without_c7i':'IQ · 去掉 C7I 码','k70_iq_phase_gaps':'K70 · 叠加 IQ 载波缺失'}

def csvwrite(path,header,rows):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)

def load(case):
    folder=OUT/case
    receipt=json.loads((folder/'run.json').read_text(encoding='utf-8'))
    assert receipt['completed'] and receipt['returncode']==0
    with (folder/'solution.csv').open() as f:rows=list(csv.DictReader(f))
    t=np.array([int(r['week'])*604800+float(r['tow']) for r in rows])
    q=np.array([int(r['Q']) for r in rows]); xyz=np.array([[float(r[k]) for k in ('x_m','y_m','z_m')] for r in rows])
    assert np.all(np.diff(t)>0) and np.all(np.isfinite(xyz))
    return dict(rows=rows,t=t,elapsed=t-t[0],q=q,xyz=xyz)

def rotation(point):
    a,b=np.deg2rad([point['latitude_deg'],point['longitude_deg']])
    rot=np.array([[-np.sin(b),np.cos(b),0],[-np.sin(a)*np.cos(b),-np.sin(a)*np.sin(b),np.cos(a)],
                  [np.cos(a)*np.cos(b),np.cos(a)*np.sin(b),np.sin(a)]])
    assert np.max(np.abs(rot@rot.T-np.eye(3)))<1e-14
    return rot

def errors(a,point):
    return (a['xyz']-ecef(point['latitude_deg'],point['longitude_deg'],point['height_m']))@rotation(point).T

def stats(a,enu):
    q=a['q'];t=a['elapsed'];valid=q==6;last=np.flatnonzero(valid)[-1]
    h=np.linalg.norm(enu[:,:2],axis=1);d=np.linalg.norm(enu,axis=1)
    windows={}
    for name,mask in [('full',valid),('first600',valid&(t<600)),('after600',valid&(t>=600)),('last300',valid&(t>=t[-1]-300))]:
        windows[name]=dict(N=int(mask.sum()),mean_ENU_m=np.mean(enu[mask],axis=0).tolist(),
            std_ENU_m=np.std(enu[mask],axis=0).tolist(),H_RMS_m=rms(h[mask]),U_RMS_m=rms(enu[mask,2]),
            D_RMS_m=rms(d[mask]))
    return dict(epochs=len(t),Q=dict(Counter(map(int,q))),final_ENU_m=enu[last].tolist(),
                final_H_m=float(h[last]),final_3D_m=float(d[last]),windows=windows,
                H_1m_60s=sustained(t,h<1,q),D_1m_60s=sustained(t,d<1,q))

def logs(case,a):
    folder=OUT/case;t0=a['t'][0];tend=a['t'][-1]
    inputs={};groups=defaultdict(list)
    with gzip.open(folder/'solution.csv.obs.csv.gz','rt',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            tow=float(r['tow']);week=int(r['week']);time=week*604800+tow
            key=(week,round(tow,3),r['sat'],int(r['slot']))
            assert key not in inputs
            inputs[key]=r['signal']
            groups[r['sat'][0]+'_'+r['signal']].append((time,float(r['P_m'])!=0,float(r['L_cycle'])!=0,
                int(r['LLI'])!=0,float(r['CN0_dBHz'])))
    signal={}
    for key,values in groups.items():
        v=np.array(values)
        signal[key]={}
        for window,mask in [('full',np.ones(len(v),bool)),('last300',v[:,0]>=tend-300)]:
            z=v[mask]
            if not len(z):continue
            signal[key][window]=dict(rows=len(z),P=int(sum(z[:,1])),L=int(sum(z[:,2])),
                LLI_nonzero=int(sum(z[:,3])),median_cn0_dbhz=float(np.median(z[:,4])))
    accepted=defaultdict(Counter);residuals=defaultdict(list);trop=[];rcb=defaultdict(list)
    matched=0;unmatched=0
    with gzip.open(folder/'solution.csv.stat.gz','rt') as f:
        for line in f:
            p=line.strip().split(',');tag=p[0]
            if tag=='$TROP' and p[3]=='6':
                trop.append((int(p[1])*604800+float(p[2]),float(p[5])))
            elif tag=='$RCB' and p[3]=='6':
                rcb[p[4]].append((int(p[1])*604800+float(p[2]),float(p[5])))
            elif tag=='$SAT':
                time=int(p[1])*604800+float(p[2]);key=(int(p[1]),round(float(p[2]),3),p[3],int(p[4]))
                if key not in inputs:
                    if p[9]=='1':unmatched+=1
                    continue
                label=p[3][0]+'_'+inputs[key]
                if p[9]=='1':
                    matched+=1
                    accepted[label]['full']+=1
                    if time>=tend-300:
                        accepted[label]['last300']+=1
                        residuals[label].append(float(p[8]))
    assert unmatched==0, unmatched
    for key,value in accepted.items():signal[key]['accepted_phase_rows']=dict(value)
    for key,v in residuals.items():
        signal[key]['last300_accepted_postfit_phase_cache']=dict(N=len(v),RMS_m=rms(np.array(v)),
            note='Final residual cache for accepted phase rows; not prefit innovation or independent accuracy.')
    trop=np.array(trop)
    trop_stats=dict(first_m=float(trop[0,1]),last_m=float(trop[-1,1]),min_m=float(min(trop[:,1])),
                    last300_mean_m=float(np.mean(trop[trop[:,0]>=tend-300,1])),
                    negative_total_ztd_epochs=int(sum(trop[:,1]<0)))
    csvwrite(folder/'trop_series.csv',['gps_seconds','elapsed_s','total_ZTD_m'],[(t,t-t0,z) for t,z in trop])
    rcb_stats={key:dict(first_m=v[0][1],last_m=v[-1][1],last300_mean_m=float(np.mean([x for t,x in v if t>=tend-300]))) for key,v in rcb.items()}
    events=Counter();failure=Counter()
    with gzip.open(folder/'solution.trace.gz','rt',encoding='utf-8',errors='replace') as f:
        for line in f:
            for tag in ['$PPP_FAILURE,','$ARC_RESET,','$ARC_REINITIALIZED,','$OBS_TIME_CONFLICT,']:
                if tag in line:events[tag]+=1
            if '$PPP_FAILURE,' in line:failure[line.split('reason=',1)[-1].split(',')[0]]+=1
    save(folder/'input_and_state_audit.json',dict(signals=signal,total_ZTD=trop_stats,
         receiver_code_bias=rcb_stats,events=dict(events),failure_reasons=dict(failure),
         stat_matched_accepted_phase_rows=matched))
    return dict(signals=signal,total_ZTD=trop_stats,receiver_code_bias=rcb_stats,events=dict(events))

def paired(a,b,ea,eb):
    pairs=[]
    for i,t in enumerate(a['t']):
        j=int(np.searchsorted(b['t'],t));candidates=[x for x in (j-1,j) if 0<=x<len(b['t'])]
        j=min(candidates,key=lambda x:abs(b['t'][x]-t))
        if abs(b['t'][j]-t)<=.01 and a['q'][i]==b['q'][j]==6:pairs.append((i,j))
    assert len({j for i,j in pairs})==len(pairs)
    ia,ib=np.array(pairs).T;delta=eb[ib]-ea[ia];times=a['t'][ia]
    mask=times>=min(a['t'][-1],b['t'][-1])-300
    csvwrite(OUT/'paired_device_errors.csv',['gps_seconds','dt_iq_minus_k70_s','dE_m','dN_m','dU_m'],
             [(a['t'][i],b['t'][j]-a['t'][i],*d) for (i,j),d in zip(pairs,delta)])
    return dict(paired_Q6_epochs=len(pairs),max_abs_time_offset_s=float(max(abs(b['t'][ib]-a['t'][ia]))),
        last300_N=int(sum(mask)),last300_mean_IQ_minus_K70_error_ENU_m=np.mean(delta[mask],axis=0).tolist(),
        last300_std_IQ_minus_K70_error_ENU_m=np.std(delta[mask],axis=0).tolist(),
        note='Same-time error difference about each device reference; not proof of a common physical root cause.')

def main():
    assert not (OUT/'summary.json').exists() or '--refresh' in sys.argv
    arrays={k:load(k) for k in RUNS};results={};primary={}
    for run,(device,point_id) in RUNS.items():
        a=arrays[run];enu=errors(a,POINTS[point_id]);primary[run]=enu
        alternatives=['Pt40','Pt39'] if device=='k70' else ['Pt42','Pt41']
        result=dict(primary_reference=point_id,point_assignment_status='provisional; both same-device points evaluated',
                    metrics=stats(a,enu),references={p:stats(a,errors(a,POINTS[p])) for p in alternatives},
                    diagnostics=logs(run,a),solution_sha256=sha(OUT/run/'solution.csv'))
        h=np.linalg.norm(enu[:,:2],axis=1);d=np.linalg.norm(enu,axis=1)
        csvwrite(OUT/run/'errors_enu.csv',['gps_seconds','elapsed_s','Q','E_m','N_m','U_m','H_m','3D_m'],
                 zip(a['t'],a['elapsed'],a['q'],*enu.T,h,d))
        results[run]=result
    comparison=paired(arrays['k70'],arrays['iq'],primary['k70'],primary['iq'])
    a,b=arrays['k70'],arrays['k70_without_b2a'];assert np.array_equal(a['t'],b['t'])
    shared=(a['q']==6)&(b['q']==6);late=shared&(a['elapsed']>=a['elapsed'][-1]-300)
    effect=primary['k70_without_b2a']-primary['k70']
    ablation=dict(changed_Q_epochs=int(sum(a['q']!=b['q'])),common_Q6_epochs=int(sum(shared)),
        last300_mean_position_change_ENU_m=np.mean(effect[late],axis=0).tolist(),
        max_common_position_change_m=float(max(np.linalg.norm(effect[shared],axis=1))),
        note='Removing B2a on K70 tests availability sensitivity on this record. It is not an IQ repair or sole-cause attribution.')
    extra={}
    for trial,base in [('iq_without_c7i','iq'),('k70_iq_phase_gaps','k70')]:
        x,y=arrays[base],arrays[trial];assert np.array_equal(x['t'],y['t'])
        m=(x['q']==6)&(y['q']==6);late=m&(x['elapsed']>=x['elapsed'][-1]-300)
        change=primary[trial]-primary[base]
        extra[trial]=dict(changed_Q_epochs=int(sum(x['q']!=y['q'])),common_Q6_epochs=int(sum(m)),
            last300_mean_position_change_ENU_m=np.mean(change[late],axis=0).tolist(),
            final_position_change_ENU_m=change[-1].tolist(),max_common_position_change_m=float(max(np.linalg.norm(change[m],axis=1))))
    identities=json.loads((OUT/'b2a_build/build.json').read_text(encoding='utf-8'))['source_before']
    assert all(sha(p)==h for p,h in identities.items())
    mask_build=json.loads((OUT/'phase_mask_build/build.json').read_text(encoding='utf-8'))
    assert all(sha(p)==h for p,h in mask_build['unchanged_objects_and_sources'].items())
    mask_actions=json.loads((OUT/'phase_mask_build/actions.json').read_text(encoding='utf-8'))
    summary=dict(date='2026-11-07',fresh_baseline_solver_runs=2,successful_private_control_solver_runs=3,ablation_solver_runs=3,
        reference_points=POINTS,runs=results,paired_devices=comparison,b2a_ablation=ablation,
        additional_ablations=extra,phase_mask_actions=mask_actions,
        harness_recovery='One phase-mask control completed solver and field checks, then postprocess lacked Path import. Fixed; separate retry passed. Original output and harness_failure.json retained.',
        validation=dict(coordinates_never_used_in_filter=True,baseline_fields_match_cached_except_processing_ms=True,
            private_bridge_control120_matches=True,production_algorithm_unchanged=True))
    save(OUT/'summary.json',summary)
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10})
    colors={'k70':'#2166AC','iq':'#C64B3D','k70_without_b2a':'#259776',
            'iq_without_c7i':'#A03C90','k70_iq_phase_gaps':'#DD971A'}
    fig,axes=plt.subplots(3,2,figsize=(14,9),sharex='col',layout='constrained')
    for run in RUNS:
        a=arrays[run];e=primary[run]
        for row,(k,label) in enumerate([(0,'东 E'),(1,'北 N'),(2,'高 U')]):
            for col in range(2):
                ax=axes[row,col]
                ax.plot(a['elapsed']/60,np.where(a['q']==6,e[:,k],np.nan),lw=1.15,color=colors[run],label=LABEL[run])
                ax.axhline(0,c='.45',lw=.7);ax.grid(alpha=.2);ax.set_ylabel(f'{label} 误差 / m')
    axes[0,0].set_title('完整启动与收敛过程');axes[0,1].set_title('最后 10 分钟（放大）')
    for row,k in enumerate([0,1,2]):
        ax=axes[row,1];ax.set_xlim(52,62)
        late=np.concatenate([primary[r][(arrays[r]['elapsed']>=52*60)&(arrays[r]['q']==6),k] for r in RUNS])
        padding=max(.02,float(np.ptp(late))*.1);ax.set_ylim(float(min(late))-padding,float(max(late))+padding)
    for ax in axes[-1]:ax.set_xlabel('各自起点后 / min')
    axes[0,0].legend(fontsize=8,ncol=2)
    fig.suptitle('10/31 新回放：K70 / IQ 与三个单因素对照\n参考暂用 Pt40 / Pt42；同机另一个点仅有毫米级差异',fontsize=14)
    fig.savefig(OUT/'ENU_COMPARISON.png',dpi=160);plt.close(fig)
    lines=['# 10/31 用户参考坐标下的重新解算与单因素诊断','',
        '按用户提供的四个测点评价。Pt39/Pt40 属于 K70，Pt41/Pt42 属于 IQ。具体时段映射尚未确认，因此每份解同时给出本机两个参考点；主图暂用 Pt40/Pt42，不取平均。沿用此前 WGS84 椭球高定义。',
        '','## 实际执行与身份','',
        '两机各 3710 历元重新解算；同一固定钟段 EXE、正式 B_VERIFIED、NRT SP3/CLK + RTS BIA，SSR 关闭。参考坐标仅作事后评价。两份新结果除耗时外逐字段复现各自旧缓存。',
        '','私有 CLI 桥接调用已有 --exclude-raw-signal，分别仅移除 K70 的 C5P 和 IQ 的 C7I 原始记录。另一个私有回放器只把 K70 在同刻 IQ 缺失的共同信号相位置为缺失，保留码、多普勒、时刻、其余相位以及 K70 B2a。三组关闭动作的 120 期控制全部逐字段复现原结果。没有修改生产源码、默认信号策略、R/Q/P0/GIM 或产品；未将 IQ 的 Q 强行改为 P。',
        '','## 重新评价','',
        '|回放|参考点|Q6历元|末 E / N / U（m）|末300秒 H RMS（m）|末300秒 U均值 / RMS（m）|',
        '|---|---|---:|---|---:|---|']
    for run,r in results.items():
        m=r['metrics'];w=m['windows']['last300'];e,n,u=m['final_ENU_m']
        lines.append(f'|{LABEL[run]}|{r["primary_reference"]}|{m["Q"].get(6,0)}|{e:+.3f} / {n:+.3f} / {u:+.3f}|{w["H_RMS_m"]:.3f}|{w["mean_ENU_m"][2]:+.3f} / {w["U_RMS_m"]:.3f}|')
    k70_point_distance=float(np.linalg.norm(ecef(*[POINTS['Pt39'][k] for k in ['latitude_deg','longitude_deg','height_m']])-ecef(*[POINTS['Pt40'][k] for k in ['latitude_deg','longitude_deg','height_m']])))
    lines+=['','## 同机参考点敏感性','',
        f'IQ Pt41/Pt42 经纬度相同、高程差 0.005 m；K70 Pt39/Pt40 三维距离 {k70_point_distance:.6f} m。summary.json 中分别列出四点的完整结果；它们不足以解释设备间米级垂向差异。',
        '','## 同时刻对照与状态','',
        f'两机 Q6 互不重复配对 {comparison["paired_Q6_epochs"]} 期，最大时间差 {comparison["max_abs_time_offset_s"]:.6f} s。末300秒 IQ−K70 的误差差 ENU 为 {comparison["last300_mean_IQ_minus_K70_error_ENU_m"]} m。',
        '','|回放|末总ZTD（m）|负总ZTD历元|', '|---|---:|---:|']
    for run,r in results.items():
        z=r['diagnostics']['total_ZTD'];lines.append(f'|{LABEL[run]}|{z["last_m"]:.4f}|{z["negative_total_ztd_epochs"]}|')
    lines+=['','这里的 $TROP 是总 ZTD，不是湿延迟。仅凭与高程同步变化，不能判定 ZTD 错误或把状态相关性当成物理根因。',
        '','## B2a 对照','',
        f'K70 去掉 B2a 后末300秒位置变化 ENU = {ablation["last300_mean_position_change_ENU_m"]} m，解状态变化 {ablation["changed_Q_epochs"]} 期。该结果量化本段缺少这组信号的影响，不能直接推出 IQ 的全部误差由 B2a 缺失造成。',
        '','## IQ C7I 与共同载波可用性对照','',
        f'IQ 去掉 C7I 记录，末300秒位置变化 ENU = {extra["iq_without_c7i"]["last300_mean_position_change_ENU_m"]} m。其接收机 C7I 码偏差状态虽约 −15 m，不能直接当作位置错误来源。该控制只检验本段这一组记录。',
        '',f'K70 叠加同刻 IQ 的共同信号缺相位模式，共置缺失 {mask_actions["count"]} 行，按频段为 {mask_actions["by_signal"]}。逐字段核对仅 L 变为零，P/D/LLI/时间/身份及剩余 L 完全不变，B2a 不变。末300秒位置变化 ENU = {extra["k70_iq_phase_gaps"]["last300_mean_position_change_ENU_m"]} m。这里只将相位可用性模式施加在 K70 观测上，未复制 IQ 的码误差、相位误差或完整跟踪历史。',
        '','逐频段输入 P/L、LLI、C/N0、实际接受相位行数及总ZTD/RCB见各回放 input_and_state_audit.json。验后残差缓存不能当作独立观测真值。',
        '','## 验证边界','',
        '三个单因素控制均未单独复现或消除末段约 1.94 m 的设备间高程误差差：K70 去 B2a 为 +0.090 m，K70 共同信号载波缺失为 −0.092 m，IQ 去 C7I 为 +0.000163 m。没有据此证明多种作用相互独立或联合效应为零，也不能把 K70 上的结果无条件外推为 IQ 机型规律。',
        '', '两机后段东向仍分别约 +0.648/+0.725 m，IQ 垂向持续约 −2.431 m。参考点修订、独立重放一致性以及本段总ZTD为正已核实；尚未找到可修改正式算法的确定代码错误。余下应聚焦本段共同信号的实际码/相位差异及其与位置、电离层、对流层状态的联合分配。下一次应复用本轮回放，只补共同观测方程/真实联合更新的最小诊断；不重复本轮三个单因素或按真值调参。',
        '', '本轮确认参考修订、同版本复现及三个可回退的单因素对照。没有证明通用米级修复或独立产品参考认证。当前同机两点差异不足以改变主要结论；精确点号对应仍保留为待确认项。原数据、旧结果和正式程序均保留。',
        '', '相位可用性控制第一次运行的解算和字段比对已成功，但压缩步骤因 Python 缺少 Path 导入失败。修正后独立重试通过，首次输出及 harness_failure.json 保留；这不是原生解算失败。',
        '','来源及可复现入口：run_oct31_reference_diagnosis.py、trial_oct31_b2a_availability.py、trial_oct31_iq_phase_availability.py、analyze_oct31_reference_diagnosis.py；每份 run.json 保存身份，build.json 保存链接对象身份。']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(metrics={k:dict(final=v['metrics']['final_ENU_m'],last300=v['metrics']['windows']['last300']) for k,v in results.items()},paired=comparison,ablation=ablation,additional=extra),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
