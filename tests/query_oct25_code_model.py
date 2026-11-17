"""Physical model query at the confirmed point, reading exact live obs identities.
No filter, no parameter changes, no new products; shared model primitives are not
an independent certification of the physical model or product absolute reference.
"""
import os,sys,gzip,subprocess,shutil
from pathlib import Path
from four_sample_diagnosis import ROOT,read,save,sha
from colocated_code_reference_trial import protect,OBJECTS
from build_filter_first_diagnostic import DEV,FLAGS
from build_four_sample_policy_probe import once
from replay_verified_integration import archive
sys.path.insert(0,str(ROOT/'tools'))
from ppp_preset import environment
OUT=ROOT/'validation/oct25_east_bias_v1'
BASE=ROOT/'validation/android_live_20261025_v1'


def main():
    protect();q=OUT/'query';q.mkdir(exist_ok=True)
    if (q/'run.json').exists():print('Physical query cached; no rerun.');return
    source=(ROOT/'validation/colocated_code_reference_v1/query/query.c').read_text()
    loader='''
static int live_csv(const char *path,obs_t*o){
 FILE*f=fopen(path,"r");char line[512],sat[8],sig[8];int week,slot,lli,code;double tow,P,L,D,CN;obsd_t*z=NULL;
 if(!f)return 0;fgets(line,sizeof(line),f);
 while(fgets(line,sizeof(line),f)){
  if(sscanf(line,"%d,%lf,%7[^,],%7[^,],%d,%lf,%lf,%lf,%lf,%d,%d",&week,&tow,sat,sig,&slot,&P,&L,&D,&CN,&lli,&code)!=11)return 0;
  int s=satid2no(sat);gtime_t t=gpst2time(week,tow);if(!s||slot<1||slot>NFREQ||obs2code(sig)!=code)return 0;
  if(!z||z->sat!=s||fabs(timediff(t,z->time))>1E-7){
   if(o->n==o->nmax){o->nmax+=4096;o->data=realloc(o->data,(size_t)o->nmax*sizeof(obsd_t));if(!o->data)return 0;}
   z=o->data+o->n++;memset(z,0,sizeof(*z));z->time=t;z->sat=s;z->rcv=1;
  }
  int k=slot-1;z->code[k]=code;z->P[k]=P;z->L[k]=L;z->D[k]=(float)D;z->SNR[k]=(uint16_t)floor(CN/SNR_UNIT+.5);z->LLI[k]=lli;
 }
 fclose(f);return o->n>0;
}
'''
    source=once(source,'int main(int argc,char **argv) {',loader+'\nint main(int argc,char **argv) {')
    source=once(source,'if(!readrnxt(argv[1],1,zero,zero,0,opt.rnxopt[0],&all,nav,&sta))return 7;sortobs(&all);','if(!live_csv(argv[1],&all))return 7;sortobs(&all);')
    source=once(source,'for(h=0;h<3;h++){','for(h=0;h<1;h++){')
    source=once(source,'if(status!=1)continue;','/* Keep the actual legacy fallback, including absent OSB. */')
    (q/'query.c').write_text(source,encoding='utf-8')
    (q/'ppp_estimator_under_test.c').write_bytes((ROOT/'src/ppp.c').read_bytes())
    names=['rtkcmn','trace','preceph','ephemeris','ionex','sbas','sofa','tides','pntpos','ppp_ar','ppp_position','smartphone_ppp_config','ppp_innovation_diag','rinex']
    objs=' '.join('"'+str(OBJECTS/(n+'.obj'))+'"' for n in names)
    command=f'@echo off\ncall "{DEV}" -arch=x64 -host_arch=x64 >nul\ncl {FLAGS} /I"{q}" /Fe"{q/"query.exe"}" /Fo"{q.as_posix()}/" "{q/"query.c"}" {objs} /link /OPT:REF winmm.lib ws2_32.lib\n'
    (q/'build.cmd').write_text(command,encoding='utf-8');p=subprocess.run(['cmd','/c',str(q/'build.cmd')],cwd=ROOT,capture_output=True)
    (q/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stdout.decode(errors='replace')[-2500:]
    raw=q/'live_obs.csv'
    with gzip.open(BASE/'live/ppp_b_verified_1792906436690.obs.csv.gz','rb') as a,raw.open('xb') as b:shutil.copyfileobj(a,b)
    inputs=read(BASE/'pc_live_window/manifest.json')['files'];env=environment(os.environ,inputs);ref=read(BASE/'reference.json')
    cmd=[str(q/'query.exe'),str(raw),str(ref['latitude_deg']),str(ref['longitude_deg']),str(ref['ellipsoidal_height_m']),str(q/'native_model.csv')]
    with (q/'console.log').open('wb') as log:p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert p.returncode==0,p.returncode
    save(q/'run.json',dict(returncode=0,query_exe_sha256=sha(q/'query.exe'),source_sha256=sha(q/'query.c'),
        input_obs_sha256=sha(raw),native_model_sha256=sha(q/'native_model.csv'),reference=ref,
        filter_calls=0,additional_PPP_replays=0,formal_files_unchanged=len(protect())))
    archive(raw);archive(q/'native_model.csv');print('Actual live-observation physical query complete.',flush=True)


def product_query(kind):
    protect();q=OUT/'query';assert kind in ('RTS_CLOCK','RTS_PAIR')
    inputs=read(BASE/'pc_live_window/manifest.json')['files']
    inputs['CLK']=str(OUT/'products/WUM0MGXRTS_20262980000_01D_05S_CLK.CLK')
    if kind=='RTS_PAIR':inputs['SP3']=str(OUT/'products/WUM0MGXRTS_20262980000_01D_05M_ORB.SP3')
    tag='rts_clock' if kind=='RTS_CLOCK' else 'rts_pair';dest=q/f'native_model_{tag}.csv'
    if not Path(str(dest)+'.gz').exists():
        raw=q/f'live_obs_{tag}.csv'
        with gzip.open(BASE/'live/ppp_b_verified_1792906436690.obs.csv.gz','rb') as a,raw.open('xb') as b:shutil.copyfileobj(a,b)
        ref=read(BASE/'reference.json');cmd=[str(q/'query.exe'),str(raw),str(ref['latitude_deg']),str(ref['longitude_deg']),str(ref['ellipsoidal_height_m']),str(dest)]
        with (q/f'{tag}_console.log').open('wb') as log:p=subprocess.run(cmd,cwd=ROOT,env=environment(os.environ,inputs),stdout=log,stderr=subprocess.STDOUT)
        assert p.returncode==0,p.returncode
        archive(raw);archive(dest)
    with gzip.open(str(dest)+'.gz','rb') as f:digest=__import__('hashlib').file_digest(f,'sha256').hexdigest()
    save(q/f'{tag}_run.json',dict(kind=kind,filter_calls=0,query_exe_sha256=sha(q/'query.exe'),
        model_uncompressed_sha256=digest,inputs={k:v for k,v in inputs.items() if k!='TXT'},
        downloaded_after_capture=True,RTS_reference_not_independently_certified=True))
    print(kind,'cached model available; no repeated query or PPP replay.')


if __name__=='__main__':
    if len(sys.argv)>1:product_query(sys.argv[1])
    else:main()
