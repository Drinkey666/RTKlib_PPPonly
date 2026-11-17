"""Independent Bias-SINEX lookup check and fixed-reference OFF/ON evaluation."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from decimal import Decimal
import csv,gzip,json,math,sys
from phase_osb_trial import ROOT,OUT,BUILD,sha,save
from report_oct31_segments import np,plt,ecef,rms
from analyze_oct31_reference_diagnosis import stats,errors

REFS=json.loads((ROOT/'validation/oct31_reference_diagnosis_v1/reference.json').read_text(encoding='utf-8'))
POINTS={p['id']:p for p in REFS['points']}

def load(case,mode):
    folder=OUT/case/mode
    r=json.loads((folder/'run.json').read_text(encoding='utf-8'));assert r['completed']
    with (folder/'solution.csv').open() as f:rows=list(csv.DictReader(f))
    t=np.array([int(x['week'])*604800+float(x['tow']) for x in rows]);q=np.array([int(x['Q']) for x in rows])
    xyz=np.array([[float(x[k]) for k in ['x_m','y_m','z_m']] for x in rows])
    assert np.all(np.isfinite(xyz)) and np.all(np.diff(t)>0)
    return dict(rows=rows,t=t,elapsed=t-t[0],q=q,xyz=xyz),r

def independent_events(case,bia):
    # Independent Python datetime/float parser, rather than native time/query functions.
    import re
    records=defaultdict(list)
    def time(s):
        year,day,seconds=map(int,s.split(':'))
        return (datetime(year,1,1)+timedelta(days=day-1,seconds=seconds)-datetime(1980,1,6)).total_seconds()
    with Path(bia).open(encoding='ascii',errors='replace') as f:
        for line in f:
            p=line.split()
            if not p or p[0]!='OSB':continue
            signal=next((s for s in p[3:] if re.fullmatch(r'L[0-9][A-Z]',s)),None)
            if not signal:continue
            ts=re.findall(r'\d{4}:\d{3}:\d{5}',line);lo,hi=map(time,ts)
            value=float(p[p.index('ns')+1])*.299792458
            records[p[2],signal].append((lo,hi,value))
    previous={};count=0;normal=0;switches=0;max_error=0.;gaps=0
    with (OUT/case/'on/phase_osb.events.csv').open() as f:
        for event in csv.DictReader(f):
            key=event['sat'],event['signal'];t=Decimal(int(event['week'])*604800)+Decimal(event['tow']);pool=records[key]
            matches=[r for r in pool if r[0]<=t<r[1]]
            expected=max(matches,key=lambda r:r[0])[2] if matches else 0.
            status=1 if matches else -1 if pool else 0
            actual=float(event['applied_m']);delta=float(event['N_translation_m'])
            assert status==int(event['status']),(case,key,t,status,event)
            max_error=max(max_error,abs(expected-actual));assert abs(expected-actual)<1E-9
            if key in previous:
                if status==previous[key]==1:
                    normal+=1;assert delta==0.,'Normal product update must not reset/translate N'
                elif (status==1)!=(previous[key]==1):switches+=1
            if status<0:gaps+=1
            previous[key]=status;count+=1
    with (OUT/case/'on/phase_osb.epochs.csv').open() as f:epochs=list(csv.DictReader(f))
    totals={k:sum(int(r[k]) for r in epochs) for k in ['phase_rows','valid','absent','outside_validity','datum_translations','record_updates']}
    assert totals['phase_rows']==totals['valid']+totals['absent']+totals['outside_validity']
    assert totals['record_updates']==count
    return dict(native_event_records_checked=count,max_bias_lookup_error_m=max_error,
        contiguous_record_updates_without_N_translation=normal,availability_transitions=switches,
        totals=totals,policy='No correction outside validity; original float carrier retained; only availability datum switches translate N; no extra rejection thresholds.')

def state_counts(case,mode):
    folder=OUT/case/mode;tags=Counter();reasons=Counter();ztd=[]
    with gzip.open(folder/'solution.trace.gz','rt',encoding='utf-8',errors='replace') as f:
        for line in f:
            for tag in ['$PPP_FAILURE,','$ARC_RESET,','$ARC_REINITIALIZED,','$PPP_REJECT,','$PHASE_OSB_CONFIG,']:
                if tag in line:tags[tag]+=1
            if '$PPP_FAILURE,' in line:reasons[line.split('reason=',1)[-1].split(',')[0]]+=1
    with gzip.open(folder/'solution.csv.stat.gz','rt') as f:
        for line in f:
            p=line.strip().split(',')
            if p[0]=='$TROP' and p[3]=='6':ztd.append(float(p[5]))
    return dict(trace_tag_counts=dict(tags),PPP_failure_reasons=dict(reasons),
        total_ZTD_first_last_m=[ztd[0],ztd[-1]],negative_total_ZTD_epochs=sum(x<0 for x in ztd))

def main():
    assert not (OUT/'summary.json').exists() or '--refresh' in sys.argv
    results={};arrays={}
    for case,point in [('k70','Pt40'),('iq','Pt42')]:
        variants={}
        for mode in ['off','on']:
            a,receipt=load(case,mode);e=errors(a,POINTS[point]);arrays[case,mode]=(a,e)
            alternatives=['Pt40','Pt39'] if case=='k70' else ['Pt42','Pt41']
            variants[mode]=dict(metrics=stats(a,e),references={p:stats(a,errors(a,POINTS[p])) for p in alternatives},
                               state=state_counts(case,mode),solution_sha256=sha(OUT/case/mode/'solution.csv'))
            with (OUT/case/mode/'errors_enu.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['gps_seconds','elapsed_s','Q','E_m','N_m','U_m']);w.writerows(zip(a['t'],a['elapsed'],a['q'],*e.T))
        a,e0=arrays[case,'off'];b,e1=arrays[case,'on'];assert np.array_equal(a['t'],b['t'])
        common=(a['q']==6)&(b['q']==6);late=common&(a['elapsed']>=a['elapsed'][-1]-300)
        off=json.loads((OUT/case/'off/run.json').read_text(encoding='utf-8'))
        on=json.loads((OUT/case/'on/run.json').read_text(encoding='utf-8'))
        assert off['baseline_fields_exact_except_processing_ms']
        assert off['compressed_logs']['solution.csv.obs.csv']['uncompressed_sha256']==on['compressed_logs']['solution.csv.obs.csv']['uncompressed_sha256']
        variants['comparison']=dict(Q_changed_epochs=int(sum(a['q']!=b['q'])),shared_Q6_epochs=int(sum(common)),
            last300_mean_position_change_ENU_m=np.mean((e1-e0)[late],axis=0).tolist(),
            max_shared_position_change_m=float(max(np.linalg.norm((e1-e0)[common],axis=1))),
            adapter_observation_CSV_byte_identical=True)
        variants['phase_OSB']=independent_events(case,on['inputs']['BIA']['path']);results[case]=variants
    before=json.loads((BUILD/'source_before.json').read_text(encoding='utf-8'));assert all(sha(p)==h for p,h in before.items())
    unit=json.loads((OUT/'unit/results.json').read_text(encoding='utf-8'))
    assert len(unit)==6 and all('failed=0' in x or '0 failed' in x for x in unit.values())
    summary=dict(date='2026-11-08',results=results,unit_results=unit,original_sources_and_objects_unchanged=True,
        candidate_exe_sha256=sha(BUILD/'trial.exe'),clock_phase_reference_compatibility='NOT_CERTIFIED: NRT PANDA-CLKDEN vs RTS PRIDE BIA; same agency is insufficient.',
        original_inputs_fixed=True,added_empirical_gates=0,added_forced_wait_seconds=0,added_automatic_product_boundary_arc_resets=0)
    save(OUT/'summary.json',summary)
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10})
    fig,axes=plt.subplots(3,2,figsize=(13,9),sharex='col',layout='constrained')
    for col,case in enumerate(['k70','iq']):
        for mode,color in [('off','#2166AC'),('on','#CB4B39')]:
            a,e=arrays[case,mode]
            for row,(k,label) in enumerate([(0,'东 E'),(1,'北 N'),(2,'高 U')]):
                ax=axes[row,col];ax.plot(a['elapsed']/60,np.where(a['q']==6,e[:,k],np.nan),color=color,lw=1.1,label=mode.upper())
                ax.axhline(0,color='.4',lw=.7);ax.grid(alpha=.2);ax.set_ylabel(label+' 误差 / m')
        axes[0,col].set_title(case.upper()+' · '+('Pt40' if case=='k70' else 'Pt42'));axes[0,col].legend()
        axes[2,col].set_xlabel('采集起点后 / min')
    fig.suptitle('10/31 相位 OSB 候选 OFF / ON\n同一 NRT SP3/CLK + RTS BIA；缺测保留浮点载波，无新增经验门限',fontsize=14)
    fig.savefig(OUT/'PHASE_OSB_OFF_ON.png',dpi=160);plt.close(fig)
    lines=['# 相位 OSB 独立候选接入与验证（2026-11-08）','',
        '## 接入与最小检查','',
        '生产源码/头文件、32个原对象和正式EXE均未替换。候选只编译私有ppp.c并复用31个对象，无nav_t/rtk_t ABI变化，NFREQ4/ENAGLO/no ENAQZS。开关RTK_PPP_PHASE_OSB=OFF/ON；关闭不读取相位文件。读取精确PRN/实际信号、GPST半开区间，ns转米；L_corr=L_raw*c/f−天线项−缠绕项−phase_OSB。相同corr_meas同时用于N初值和残差，没有重复施加。',
        '', '缺失或过期OSB不外推、明确标不可用，原始浮点载波仍保留。可用性在有改正/无改正之间切换时，按 N_new=N_old+b_old−b_new 转换已存在模糊度均值，协方差不变；新弧/确认周跳由原核心初始化。普通连续300秒记录更新直接使用新改正，不自动重置或平移N。不新增经验阈值、强制等待、全星/整历元拒绝，也不按真值调参。',
        '','## 回归与实际执行','',
        '原有215项核心回归与新增32项全部通过。最初phase2单测因独立工作目录缺少validation/phase2输出目录，有1项日志打开失败；补齐该夹具目录后完整重跑通过，首次记录保留。两机OFF前120期和完整3710期均逐字段复现原缓存（仅耗时不同）。两机ON各3710期，输入adapter观测CSV与OFF按解压SHA逐字节一致。',
        '','## 精度结果','',
        '每份结果均另按本机两个参考点评价；下表主参考为K70/Pt40、IQ/Pt42，沿用WGS84椭球高定义。',
        '','|设备/开关|Q6|末ENU / m|末300s H RMS / m|末300s U均值 / m|末300s 3D RMS / m|',
        '|---|---:|---|---:|---:|---:|']
    for case in ['k70','iq']:
        for mode in ['off','on']:
            m=results[case][mode]['metrics'];w=m['windows']['last300'];e,n,u=m['final_ENU_m']
            lines.append(f'|{case.upper()} {mode.upper()}|{m["Q"].get(6,0)}|{e:+.3f}, {n:+.3f}, {u:+.3f}|{w["H_RMS_m"]:.3f}|{w["mean_ENU_m"][2]:+.3f}|{w["D_RMS_m"]:.3f}|')
    lines+=['','## 覆盖、边界及失败','',
        '|设备|输入相位行|有效OSB|信号无记录|区间外/缺口|N参考平移|普通记录更新（不平移N）|',
        '|---|---:|---:|---:|---:|---:|---:|']
    for case in ['k70','iq']:
        a=results[case]['phase_OSB'];t=a['totals']
        lines.append(f'|{case.upper()}|{t["phase_rows"]}|{t["valid"]}|{t["absent"]}|{t["outside_validity"]}|{t["datum_translations"]}|{a["contiguous_record_updates_without_N_translation"]}|')
    lines+=['','这里是PPP入口看到的相位行覆盖，不冒称全是最终接受载波。所有原生记录选择/改正值事件用独立Python解析器逐项核对，最大误差见summary.json；普通记录更新不平移N的检查全部通过。实际PPP失败、弧段重启和总ZTD统计保存在summary.json，不能把日志行数当独立物理周跳数。',
        '','## 本次判定','',
        '候选真实施加了当前有效的相位OSB，但未满足两机整体精度改善的验收。末300秒K70 U均值−0.490→−0.371m、IQ −2.431→−2.398m；对应水平RMS分别0.718→0.784m、0.872→0.911m，东偏反而增大。IQ全程三维RMS为3.234→3.300m。不能用末点高程上移宣称修复成功。',
        '', 'K70水平持续1m进入时刻491→714s，三维2506→2624s；IQ水平仍117s、三维仍未达到。四个全程回放没有PPP_FAILURE，Q逐期不变。K70原有拒绝日志多1行；IQ多6行、ARC_REINITIALIZED多2行，ARC_RESET数不变。这是既有编辑与历史响应，并非新增产品边界强制断弧；不隐去这些变化。保留为独立候选，正式默认保持OFF。',
        '','## 产品参考边界','',
        '原组合保持NRT PANDA-CLKDEN轨钟与RTS PRIDE BIA。BIA没有声明可验证的SATELLITE_CLOCK_REFERENCE_OBSERVABLES，不能仅因同为WHU就认证兼容。已按PRIDE官方脚本的RTS路径尝试取同日匹配SP3/CLK，均网络超时，回执在product_reference/download_receipts.json；没有替换原产品或把超时当作产品不存在。当前ON/OFF证明此固定组合下的实现行为与数值效果，不能据较低误差反向认证产品兼容。',
        '','## 可复现与版本边界','',
        'tests/phase_osb_trial.py build / unit / prefix / replay；候选EXE在build/trial.exe，各run.json记录完整输入/程序身份。tests/report_phase_osb_trial.py生成独立查询核验和图表。仅独立PC候选，Android未移植、正式EXE未替换，R/Q/P0/GIM及原QC参数未改。',
        '', '产品方法参考：[IGS PPP-AR 工作组](https://www.igs.org/wg/ppp-ar/)；匹配产品路径依据本地PRIDE官方scripts/pdp3.sh及[官方仓库](https://github.com/PrideLab/PRIDE-PPPAR)。']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({c:{m:results[c][m]['metrics'] for m in ['off','on']} for c in results},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
