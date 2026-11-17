"""Plot evidence without altering any solver output or cropping the startup."""
import csv,math
from four_sample_diagnosis import ROOT,read,np,P
from colocated_code_reference_trial import csvwrite
OUT=ROOT/'validation/oct25_east_bias_v1'
BASE=ROOT/'validation/android_live_20261025_v1'


def main():
    with (BASE/'coordinate_time_series.csv').open(encoding='utf-8-sig') as f:
        live=[r for r in csv.DictReader(f) if r['case']=='PHONE_LIVE' and r['Q']=='6']
    comps=read(OUT/'component_summary.json')['components']
    fig=P.plt.figure(figsize=(11,8));ax=fig.add_subplot(211)
    ax.plot([float(r['elapsed_s']) for r in live],[float(r['E_m']) for r in live],color='#1d67a3',lw=1.5,label='Phone live East error')
    for name,color,style,label in [('RAW_MODEL_TARGET','#d07824','--','Raw code model profile'),('ACTUAL_USED_TARGET','#7d3c98',':','Used code profile')]:
        for i,(start,end) in enumerate([(0,60),(60,300),(300,900),(900,1550)]):
            z=next(r for r in comps if r['start_s']==start and r['end_s']==end and r['component']==name)
            ax.hlines(z['E_m'],start,end,color=color,ls=style,lw=2,label=label if i==0 else None)
    ax.axhline(0,color='gray',lw=.8);ax.set_ylabel('East (m)');ax.set_xlabel('Seconds since live start');ax.grid(alpha=.2);ax.legend(fontsize=9)
    ax.set_title('East bias forms after initialization and continues in the code equations')
    ax=fig.add_subplot(212)
    values=[]
    for name in ['RAW_MODEL_TARGET','ACTUAL_USED_TARGET']:
        values.append(next(r['E_m'] for r in comps if r['start_s']==60 and r['end_s']==1550 and r['component']==name))
    products=read(OUT/'RTS_product_comparison.json')['results']
    values.extend([products[0]['RTS_common_rows_ENU_m'][0],products[1]['RTS_common_rows_ENU_m'][0]])
    names=['Raw code model','Used code equations','RTS clock\n(common rows)','RTS orbit + clock\n(common rows)']
    bars=ax.bar(names,values,color=['#d07824','#7d3c98','#38856b','#58746b'],width=.65)
    for bar,x in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,x+.035,f'{x:.3f} m',ha='center',fontsize=10)
    ax.set_ylim(0,2.85);ax.set_ylabel('East code-space profile (m)');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    ax.set_title('After 60 s: nominal RTS product substitution does not remove the code-space bias')
    fig.text(.5,.013,'Code-space profiles are diagnostics, not PPP trajectories or coordinate corrections. Frozen H/R/accepted rows; reference supplied by user.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(ROOT/'docs/OCT25_EAST_BIAS_SOURCE_REPORT.png',dpi=160);P.plt.close(fig)


if __name__=='__main__':main()
