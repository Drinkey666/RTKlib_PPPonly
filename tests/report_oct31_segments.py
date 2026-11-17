"""Saved-only error analysis of Oct31 independent segments, using the App reference."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import csv,gzip,hashlib,json,math,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'validation/filter_prior_r_causal/plot_dependencies'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
DATA=Path('E:/RTKLIB_Data/10.31')
OUT=DATA/'results_B_verified_fixed_clock'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def ecef(lat,lon,h):
 lat,lon=np.deg2rad([lat,lon]);a=6378137.;e2=1-(1-1/298.257223563)**2;n=a/np.sqrt(1-e2*np.sin(lat)**2)
 return np.array([(n+h)*np.cos(lat)*np.cos(lon),(n+h)*np.cos(lat)*np.sin(lon),(n*(1-e2)+h)*np.sin(lat)])
def rms(x):return float(np.sqrt(np.mean(np.square(x)))) if len(x) else None
def sustained(t,good,status):
 start=None;previous=None
 for ti,ok,q in zip(t,good,status):
  if not ok or q!=6:start=None;previous=ti;continue
  if start is None or previous is None or ti-previous>1.5:start=float(ti)
  if ti-start>=60-1e-7:return {'entered_seconds':start,'confirmed_seconds':float(ti)}
  previous=ti
 return None
def main():
 cfg=read(OUT/'configuration.json');ref=cfg['reference'];r0=ecef(ref['latitude_deg'],ref['longitude_deg'],ref['height_m'])
 lat,lon=np.deg2rad([ref['latitude_deg'],ref['longitude_deg']])
 rotation=np.array([[-np.sin(lon),np.cos(lon),0],[-np.sin(lat)*np.cos(lon),-np.sin(lat)*np.sin(lon),np.cos(lat)],
   [np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]])
 assert np.max(np.abs(rotation@rotation.T-np.eye(3)))<1e-14
 manifest=read(DATA/'split_10min/split_manifest.json');items=[];arrays={}
 for part in manifest['parts']:
  n=part['part'];folder=OUT/f'part{n:02d}';run=read(folder/'run.json');assert run.get('completed')
  with (folder/'solution.csv').open() as f:rows=list(csv.DictReader(f))
  xyz=np.array([[float(r[k]) for k in ['x_m','y_m','z_m']] for r in rows]);enu=(xyz-r0)@rotation.T
  assert np.max(np.abs(np.linalg.norm(enu,axis=1)-np.linalg.norm(xyz-r0,axis=1)))<1e-7
  gpsns=int(Decimal(part['first_gps_ns']));week,ns=divmod(gpsns,604800*10**9);tow=ns/1e9
  t=np.array([(int(r['week'])-week)*604800+float(r['tow'])-tow for r in rows]);q=np.array([int(r['Q']) for r in rows])
  h=np.linalg.norm(enu[:,:2],axis=1);d=np.linalg.norm(enu,axis=1);valid=q>0;ppp=q==6
  assert len(rows)==part['epochs'] and np.all(np.isfinite(enu))
  stats={}
  for label,mask in [('all_valid',valid),('PPP_all',ppp),('PPP_first60',ppp&(t<60)),('PPP_last60',ppp&(t>t[-1]-60)),('PPP_last300',ppp&(t>t[-1]-300))]:
   stats[label]={'N':int(sum(mask)),'H_RMS_m':rms(h[mask]),'U_RMS_m':rms(enu[mask,2]),'3D_RMS_m':rms(d[mask]),
    'mean_ENU_m':np.mean(enu[mask],axis=0).tolist() if np.any(mask) else None}
  indexes=np.flatnonzero(ppp);last=int(indexes[-1]) if len(indexes) else None
  events=Counter();numeric=Counter();resets=0
  with gzip.open(folder/'solution.trace.gz','rt',encoding='utf-8',errors='replace') as f:
   for l in f:
    for tag in ['$PPP_REJECT,','$PPP_FAILURE,','$ARC_RESET,','$ARC_PENDING_INIT,','$ARC_REINITIALIZED,','$PPP_ARC_RESET,']:
     if tag in l:events[tag]+=1
    for reason in ['NAN_INPUT','NAN_STATE','NAN_COV','NON_PSD','PSD_FAIL','ASYMMETRIC']:
     if reason in l:numeric[reason]+=1
  item={'part':n,'input_file':part['file'],'start_beijing':part['first_beijing_time'],'end_beijing':part['last_beijing_time'],
   'input_epochs':len(rows),'PPP_epochs':int(sum(ppp)),'Q_counts':run['Q_counts'],'statistics':stats,
   'final_PPP_ENU_m':enu[last].tolist() if last is not None else None,'final_H_m':float(h[last]) if last is not None else None,
   'final_3D_m':float(d[last]) if last is not None else None,'maximum_PPP_H_m':float(max(h[ppp])) if np.any(ppp) else None,
   'maximum_PPP_3D_m':float(max(d[ppp])) if np.any(ppp) else None,
   'H1m_sustained60s':sustained(t,h<1,q),'3D1m_sustained60s':sustained(t,d<1,q),
   'trace_events':dict(events),'numeric_reason_mentions':dict(numeric),'solver_returncode':run['returncode']}
  items.append(item);arrays[n]=(t,enu,h,d,q)
  with (folder/'errors_enu.csv').open('w',newline='',encoding='utf-8') as f:
   w=csv.writer(f);w.writerow(['epoch','week','tow','elapsed_s','Q','E_m','N_m','U_m','horizontal_error_m','3d_error_m','ns','nobs'])
   for i,r in enumerate(rows):w.writerow([i+1,r['week'],r['tow'],t[i],int(q[i]),*enu[i],h[i],d[i],r['ns'],r['nobs']])
 plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10})
 fig,axes=plt.subplots(4,2,figsize=(14,14),layout='constrained');colors=['#c43b4d','#1a9068','#2868b5']
 for ax,item in zip(axes.flat,items):
  n=item['part'];t,enu,h,d,q=arrays[n]
  for k,label in enumerate(['E 东','N 北','U 高程']):
   y=enu[:,k].copy();y[q!=6]=np.nan;ax.plot(t,y,color=colors[k],lw=1.2,label=label)
   ax.scatter(t[q==5],enu[q==5,k],marker='x',color=colors[k],s=14,alpha=.55)
  ax.axhline(0,color='.35',lw=.7);ax.grid(alpha=.22);ax.set_xlabel('本段起算时间 / s');ax.set_ylabel('相对 App 参考误差 / m')
  ax.set_title(f"第{n}段 · {item['start_beijing'][11:19]}—{item['end_beijing'][11:19]} · PPP {item['PPP_epochs']}/{item['input_epochs']}")
 axes.flat[0].legend(ncol=3);axes.flat[-1].axis('off')
 axes.flat[-1].text(.02,.97,'独立初始化；同一 B_VERIFIED 配置\n\n参考：WGS84 / 椭球高\n30.76717661111111° N\n103.97949563888889° E\nh = 486.963 m\n\n实线：PPP(Q6)；叉号：SPP(Q5)\n保留启动误差，未裁剪曲线\n第7段为不足10分钟尾段',va='top',transform=axes.flat[-1].transAxes,fontsize=12)
 fig.suptitle('10月31日：7段独立 PPP 的完整 E/N/U 曲线',fontsize=17);fig.savefig(OUT/'segment_enu_full.png',dpi=170);plt.close(fig)
 fig,axes=plt.subplots(3,1,figsize=(13,11),layout='constrained')
 for item in items:
  n=item['part'];t,enu,h,d,q=arrays[n]
  for ax,y in zip(axes,[h,enu[:,2],d]):
   yy=y.copy();yy[q!=6]=np.nan;ax.plot(t,yy,label=f'第{n}段',lw=1.2)
 for ax,label in zip(axes,['水平误差 / m','U 误差 / m','三维误差 / m']):ax.set_ylabel(label);ax.grid(alpha=.22);ax.set_xlabel('本段起算时间 / s')
 axes[0].axhline(1,color='.4',ls='--',lw=.8);axes[1].axhline(0,color='.4',lw=.8);axes[2].axhline(1,color='.4',ls='--',lw=.8)
 axes[0].legend(ncol=7,fontsize=9);fig.suptitle('同配置、独立初始化：水平 / 高程 / 三维误差比较',fontsize=16)
 fig.savefig(OUT/'segment_comparison_full.png',dpi=170);plt.close(fig)
 summary={'reference':ref,'error_definition':'ENU from WGS84 ECEF, relative to current App stored reference; not a new independent survey verification',
  'independent_initialization':True,'input_epochs':sum(x['input_epochs'] for x in items),'PPP_epochs':sum(x['PPP_epochs'] for x in items),
  'all_segments_time_covered':all(p['fully_covered'] for p in cfg['parts']),'parts':items}
 save(OUT/'accuracy_summary.json',summary)
 with (OUT/'accuracy_summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
  columns=['part','epochs','PPP','E_final_m','N_final_m','U_final_m','H_final_m','3D_final_m','H_RMS_PPP_m','U_RMS_PPP_m','3D_RMS_PPP_m','H_RMS_last60_m','U_RMS_last60_m','H1m_60s_enter_s','3D1m_60s_enter_s']
  w=csv.writer(f);w.writerow(columns)
  for x in items:
   a=x['statistics']['PPP_all'];b=x['statistics']['PPP_last60'];w.writerow([x['part'],x['input_epochs'],x['PPP_epochs'],*x['final_PPP_ENU_m'],x['final_H_m'],x['final_3D_m'],a['H_RMS_m'],a['U_RMS_m'],a['3D_RMS_m'],b['H_RMS_m'],b['U_RMS_m'],(x['H1m_sustained60s']or{}).get('entered_seconds'),(x['3D1m_sustained60s']or{}).get('entered_seconds')])
 table=['|段|PPP/输入历元|末E m|末N m|末U m|末水平m|全程水平RMS m|全程U RMS m|末60s水平RMS m|',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for x in items:
  a=x['statistics']['PPP_all'];b=x['statistics']['PPP_last60'];e,n,u=x['final_PPP_ENU_m'];table.append(f"|{x['part']}|{x['PPP_epochs']}/{x['input_epochs']}|{e:+.3f}|{n:+.3f}|{u:+.3f}|{x['final_H_m']:.3f}|{a['H_RMS_m']:.3f}|{a['U_RMS_m']:.3f}|{b['H_RMS_m']:.3f}|")
 report=f'''# 10月31日10分钟分段 PPP 对比

用户上一条实际生成7段：6个10分钟窗口＋109历元尾段，共3710历元。本次全部时间覆盖，全部独立初始化回放完成，不把尾段当完整10分钟样本。

## 参考与计算

按用户“使用程序设置参考”的要求，读取手机 `ppp_manual_reference.xml/reference_wgs84_dms`：WGS84纬度30.76717661111111°、经度103.97949563888889°、椭球高486.963 m。该参考只用于输出后的误差计算，没有注入滤波。这里报告相对App保存参考的误差，不新增独立测量认证。

采用WGS84 ECEF转ENU，验证旋转正交性和三维差向量长度不变。E/N/U分别为东/北/Up；水平为sqrt(E²+N²)，三维为sqrt(E²+N²+U²)。完整历元CSV包含全部状态，PPP统计仅Q6，SPP/Q0另计；没有为压低误差删启动段。各段独立冷启动，不继承前段状态，所以不同于一小时连续解。

## 产品覆盖

原App下载的day303 RTS BIA虽然文件头有day304，内部C/L记录都仅覆盖day303至day304 00:00 GPST，不能覆盖本次02:13:52—03:15:41 GPST。未外推、未忽略检查。

官方已存在day304 RTS BIA，PC控制连接可取SIZE但数据通道超时；复用手机已安装的HistoricalRtsDownloadTest下载成功，没有安装/替换App或改GNSS/PPP设置。新文件155827字节，gzip CRC通过；码OSB覆盖day304 00:00—24:00，已有相位OSB覆盖00:00—04:00。浮点PPP采用码OSB，未实现/开启相位OSB固定。旧产品保留。

NRT SP3覆盖10/30 00:00—10/31 23:55，30s CLK实际AS记录覆盖至11/1 00:01；IONEX及VMF3 H00/H06覆盖全部观测。逐段官方预检全部通过（带警告），没有绕过。输入路径、SHA、实际范围见configuration.json；下载回执在上级products目录。

覆盖通过不代表混合产品参考约定已完全认证。该钟差是PANDA-CLKDEN、30s文件；结果不作为纯预报钟差或采集当时全部产品可用性的认证。预检仍报告BIA时间系统缺少声明（读取器按GPST）、ATX/CLK参考未完全核实及部分信号PCO/PCV缺失/旧模型回退。沿用现有B_VERIFIED行为，未换天线模型、阈值或弱化检查来改善曲线。

## 配置

使用已通过观测生成回归的 FIXED_CLOCK_2023 独立EXE：`{cfg['executable']}`，SHA256 `{cfg['executable_sha256']}`。B_VERIFIED、B、CORRECTED、PPP_COMMON、LEGACY、GEC、NF=4，GLO/E5b实验关闭；未更改R/Q/P0/GIM/抗差/Joseph。实时/Raw准入表仍没有B1C，不能宣称此次同时使用了B1I+B1C。

## 定量结果

{chr(10).join(table)}

全部Q统计和首60s/末60s/末300s、最大误差、均值、末ENU见accuracy_summary.json；末段只有约109秒，完整RMS与600秒段不能作相同观测长度的严格排名。

收敛诊断预先定义为H<1m、3D<1m各自连续60秒的Q6解，缺测/非PPP会中断，不反馈到滤波；进入时刻与确认时刻均记录。未用末点替代完整收敛判断。

## 图和逐历元结果

- `segment_enu_full.png`：各段完整E/N/U，保留启动大误差。
- `segment_comparison_full.png`：各段H/U/3D叠图。
- `part01`至`part07/solution.csv`、`errors_enu.csv`：解及逐历元误差。
- 每段run.json、预检日志、products.log；trace/状态/观测大表已校验gzip后删除本轮冗余明文，原始观测/产品不动。

本轮只进行了请求的解算与比较，没有按结果调参、采集码相预处理、卫星屏蔽或模型修补。
'''
 if (OUT/'height_restart_evidence.json').exists():
  control=read(OUT/'height_restart_evidence.json')
  report+=f'''\n## 补充：连续一小时对照\n\n随后为回答高程问题增加一次3710历元连续处理，同EXE/产品/参数；首600历元与第1段精确一致。连续末水平{control['continuous_final_H_m']:.3f}m、U={control['continuous_final_ENU_m'][2]:+.3f}m；末300秒U均值{control['continuous_last300_U_mean_m']:.3f}m、轨迹标准差{control['continuous_last300_U_std_m']:.4f}m（不是绝对精度）。\n\n最后109秒独立处理末U−6.258m，同一时刻连续处理−3.492m，两个处理使用相同钟参考；重新初始化/历史丢失造成该窗口额外约2.765m处理差异。其余2—6段首FullBias参考不同，差异不能全归为单一P0作用。\n\n持续的约3.49m相对参考残差尚未唯一归因，不以调参或再延长时间保证消除。详细报告见HEIGHT_RESTART_REPORT.md，图continuous_vs_restart.png。\n'''
 (OUT/'REPORT.md').write_text(report,encoding='utf-8');(ROOT/'docs/OCT31_10MIN_SEGMENT_COMPARISON.md').write_text(report,encoding='utf-8')
 print('Report saved:',OUT/'REPORT.md')
 for x in items:print(x['part'],x['final_PPP_ENU_m'],x['final_H_m'],x['statistics']['PPP_all']['H_RMS_m'])
if __name__=='__main__':main()
