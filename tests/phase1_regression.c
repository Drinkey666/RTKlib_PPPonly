/* White-box lifecycle and numerical regressions; no reference coordinates. */
#include <stdio.h>
#include <string.h>
#include "../src/ppp.c"
extern int reference_filter(double *,double *,const double *,const double *,const double *,int,int);
static int passed,failed;
#define CHECK(name,condition) do { if(condition){passed++;printf("PASS %s\n",name);}else{failed++;printf("FAIL %s (line %d)\n",name,__LINE__);} }while(0)
static void numerical_tests(void)
{
    double bad[]={NAN,INFINITY,-INFINITY},x,p,h=1.0,r=1.0,v;
    double xa[3]={1,2,0},xb[3],pa[9]={2,.2,0,.2,3,0,0,0,0},pb[9];
    double hh[6]={1,.5,0,-.2,1,0},vv[2]={.25,-.7},rr[4]={1,.1,.1,2};
    int i,info;
    for(i=0;i<3;i++) {
        x=2.0;p=1.0;v=bad[i];info=filter(&x,&p,&h,&v,&r,1,1);
        CHECK(i==0?"NaN innovation atomic failure":i==1?"Inf innovation atomic failure":"-Inf innovation atomic failure",
            info==FILTER_NAN_INPUT && x==2.0 && p==1.0);
    }
    x=1;p=1;v=2;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("finite scalar unchanged",info==0 && x==2 && p==.5);
    memcpy(xb,xa,sizeof(xa));memcpy(pb,pa,sizeof(pa));
    info=filter(xa,pa,hh,vv,rr,3,2);
    CHECK("finite matrix bitwise 97a57a9 equality",!info && !reference_filter(xb,pb,hh,vv,rr,3,2) &&
        !memcmp(xa,xb,sizeof(xa)) && !memcmp(pa,pb,sizeof(pa)));
    x=1;p=1;h=0;r=0;v=1;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("singular inverse preserves x/P",info!=0 && x==1 && p==1);
    h=1;r=1;x=1;p=NAN;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("NaN covariance reason",info==FILTER_NAN_COV && x==1 && isnan(p));
    p=-1;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("negative variance rejected",info==FILTER_BAD_COV && x==1 && p==-1);
    p=1;r=INFINITY;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("Inf R rejected",info==FILTER_NAN_COV && x==1 && p==1);
    r=1;h=NAN;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("NaN H rejected",info==FILTER_NAN_INPUT && x==1 && p==1);
    h=2;p=1E308;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("finite input overflow rejected",info==FILTER_NAN_COV && x==1 && p==1E308);
    x=1;p=1;h=1E-3;r=1E-12;v=1E308;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("posterior state overflow atomic failure",info==FILTER_NAN_STATE && x==1 && p==1);
    x=0;p=1;h=1;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("no active state explicit failure",info==FILTER_NO_ACTIVE && x==0 && p==1);
    pa[0]=pa[4]=pa[8]=1;pa[1]=1;pa[3]=0;
    CHECK("asymmetric covariance rejected",numeric_covariance(pa,3)==FILTER_BAD_COV);
    x=INFINITY;p=1;info=filter(&x,&p,&h,&v,&r,1,1);
    CHECK("Inf prior state rejected",info==FILTER_NAN_STATE && isinf(x) && p==1);
}
static void fixture(rtk_t *rtk,obsd_t *obs,int clean,int nf)
{
    prcopt_t opt;
    smartphone_ppp_configure(&opt,NULL);opt.nf=nf;
    opt.ppp_baseline=clean?PPP_BASELINE_A_CLEAN:PPP_BASELINE_B_LEGACY;
    strcpy(opt.pppopt,"-PREPROC=1 -DOPPSM=0 -DOPPSLIP=0.5 -MWTHRES=0");
    rtkinit(rtk,&opt);memset(obs,0,sizeof(*obs));
    obs->sat=satno(SYS_GPS,1);obs->rcv=1;obs->time=gpst2time(2400,140);
    obs->code[0]=CODE_L1C;obs->L[0]=2E7*FREQL1/CLIGHT;
    obs->P[0]=20000110;obs->SNR[0]=35000;
    rtk->sol.time=obs->time;rtk->sol.rr[0]=6378137;
    rtk->ssat[0].azel[1]=PI/2;
    initx(rtk,100,1,IB(1,0,&rtk->opt));
    initx(rtk,5,1,II(1,&rtk->opt));
}
static void lifecycle_tests(rtk_t *rtk,nav_t *nav)
{
    obsd_t obs,three[3];int bi,i,f;
    fixture(rtk,&obs,1,1);bi=IB(1,0,&rtk->opt);
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("continuous phase retains ambiguity",rtk->x[bi]==100 && !rtk->ssat[0].ppp_arc_pending[0]);
    obs.LLI[0]=LLI_SLIP;obs.time=timeadd(obs.time,1);
    rtk->P[bi]=rtk->P[bi*rtk->nx]=.2;
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("slip full P/L new arc",fabs(rtk->x[bi]+100)<1E-7 && !rtk->ssat[0].ppp_arc_pending[0] && rtk->P[bi]==0);
    obs.P[0]=0;obs.time=timeadd(obs.time,1);
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("slip missing P invalidates old arc",rtk->x[bi]==0 && rtk->P[bi+bi*rtk->nx]==0 && rtk->ssat[0].ppp_arc_pending[0]);
    obs.LLI[0]=0;obs.time=timeadd(obs.time,1);
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("pending survives flag clearing",rtk->x[bi]==0 && rtk->ssat[0].ppp_arc_pending[0]);
    obs.P[0]=20000110;obs.time=timeadd(obs.time,1);
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("later P/L reinitializes pending arc",fabs(rtk->x[bi]+100)<1E-7 && !rtk->ssat[0].ppp_arc_pending[0]);
    rtk->ssat[0].pt[0][0]=obs.time;rtk->ssat[0].ph[0][0]=obs.L[0];
    obs.time=timeadd(obs.time,61);obs.P[0]+=10;
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("elapsed long gap restarts arc",(rtk->ssat[0].ppp_slip_evidence[0]&PPP_EVIDENCE_GAP) && fabs(rtk->x[bi]+110)<1E-7);
    rtk->ssat[0].outc[0]=31;obs.P[0]=0;
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("outage counter leaves pending arc",rtk->x[bi]==0 && rtk->ssat[0].ppp_arc_pending[0]);
    rtkfree(rtk);
    fixture(rtk,&obs,0,1);bi=IB(1,0,&rtk->opt);obs.LLI[0]=LLI_SLIP;obs.P[0]=0;
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    obs.time=timeadd(obs.time,1);obs.LLI[0]=0;obs.P[0]=20000110;
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("B LEGACY old arc behavior explicitly recoverable",rtk->x[bi]==100 && !rtk->ssat[0].ppp_arc_pending[0]);
    rtkfree(rtk);
    for(i=0;i<2;i++) {
        fixture(rtk,&obs,i,3);obs.code[2]=CODE_L5Q;
        obs.L[2]=(2E7-1)*FREQL5/CLIGHT;obs.D[0]=obs.D[2]=1;
        rtk->ppp_start_time=gpst2time(2400,100);rtk->ssat[0].gf[1]=.25;
        for(f=0;f<3;f+=2){rtk->ssat[0].ppp_dop_valid[f]=1;rtk->ssat[0].ppp_dop_time[f]=timeadd(obs.time,-1);rtk->ssat[0].ppp_doppler[f]=1;}
        precheck_obs_ppp(rtk,&obs,1,nav);
        CHECK(i?"GF missing phase history does not falsely defer":"B LEGACY GF deferral recoverable",
            i?(rtk->ssat[0].slip[0] && rtk->ssat[0].slip[2]):(!rtk->ssat[0].slip[0] && !rtk->ssat[0].slip[2]));
        rtkfree(rtk);
    }
    fixture(rtk,&obs,1,3);
    rtk->ppp_start_time=gpst2time(2400,100);
    for(i=0;i<3;i++) {
        ssat_t *ss=&rtk->ssat[i];three[i]=obs;three[i].sat=(uint8_t)(i+1);
        three[i].code[2]=CODE_L5Q;three[i].L[2]=(2E7-1)*FREQL5/CLIGHT;
        three[i].D[0]=three[i].D[2]=1;
        ss->gf[1]=gfmeas(&three[i],nav,2);
        for(f=0;f<3;f+=2) {
            ss->ppp_dop_valid[f]=1;ss->ppp_dop_time[f]=ss->pt[0][f]=timeadd(obs.time,-1);
            ss->ppp_doppler[f]=1;ss->ph[0][f]=three[i].L[f]+1;
        }
    }
    three[0].L[2]+=10;
    precheck_obs_ppp(rtk,three,3,nav);
    CHECK("GF yields only to executed Doppler pair",!rtk->ssat[0].slip[0] && rtk->ssat[0].slip[2] &&
        (rtk->ssat[0].ppp_slip_evidence[0]&PPP_EVIDENCE_DOPPLER));
    CHECK("phase history retained after startup",rtk->ssat[1].pt[0][0].time!=0);
    rtkfree(rtk);
    fixture(rtk,&obs,1,1);bi=IB(1,0,&rtk->opt);
    obs.L[0]=0;obs.LLI[0]=LLI_SLIP;
    precheck_obs_ppp(rtk,&obs,1,nav);udbias_ppp(rtk,&obs,1,nav);
    CHECK("confirmed LLI without phase still invalidates",rtk->x[bi]==0 && rtk->ssat[0].ppp_arc_pending[0]);
    rtkfree(rtk);
}
static void transaction_tests(rtk_t *rtk,nav_t *nav)
{
    obsd_t obs;double *before,*cov;int bi,info;
    fixture(rtk,&obs,1,1);bi=IB(1,0,&rtk->opt);
    before=mat(rtk->nx,1);cov=mat(rtk->nx,rtk->nx);
    matcpy(before,rtk->x,rtk->nx,1);matcpy(cov,rtk->P,rtk->nx,rtk->nx);
    obs.P[0]=NAN;info=rtkpos(rtk,&obs,1,nav);
    CHECK("PPP raw NaN rejects without zero masking",!info && rtk->ppp_failure==FILTER_NAN_INPUT && rtk->sol.stat==SOLQ_NONE &&
        !memcmp(before,rtk->x,rtk->nx*sizeof(double)) && !memcmp(cov,rtk->P,(size_t)rtk->nx*rtk->nx*sizeof(double)));
    obs.LLI[0]=LLI_SLIP;info=rtkpos(rtk,&obs,1,nav);
    CHECK("confirmed slip survives rejected NaN packet",!info && rtk->ppp_failure==FILTER_NAN_INPUT &&
        rtk->x[bi]==0 && rtk->ssat[0].ppp_arc_pending[0]);
    obs.P[0]=20000110;obs.LLI[0]=LLI_SLIP;
    initx(rtk,6378137,1,0);initx(rtk,1,1,1);initx(rtk,1,1,2);initx(rtk,2,1,IT(&rtk->opt));
    rtk->opt.prn[2]=NAN;rtk->tt=1;
    pppos(rtk,&obs,1,nav);
    CHECK("invalid prediction restores prior but not old slip arc",rtk->ppp_failure==FILTER_NAN_COV &&
        rtk->x[0]==6378137 && rtk->x[IT(&rtk->opt)]==2 && rtk->x[bi]==0 && rtk->ssat[0].ppp_arc_pending[0] &&
        !numeric_covariance(rtk->P,rtk->nx) && rtk->sol.stat==SOLQ_NONE);
    rtk->opt.prn[2]=1E-4;obs.LLI[0]=0;obs.time=timeadd(obs.time,1);
    pppos(rtk,&obs,1,nav);
    CHECK("no-measurement failure keeps finite prediction",rtk->ppp_failure==PPP_FAILURE_NO_OBS &&
        numeric_finite(rtk->x,rtk->nx) && !numeric_covariance(rtk->P,rtk->nx) && rtk->sol.stat==SOLQ_NONE);
    free(before);free(cov);rtkfree(rtk);
}
static void residual_tests(rtk_t *rtk,nav_t *nav)
{
    obsd_t obs;double rs[6]={20200000,14000000,18000000,0,0,0};
    double dts[2]={0},satvar[1]={1},dr[3]={0},azel[2],v[2],R[4],*H;
    int svh[1]={0},exc[1]={0},nv;unsigned char mexc[MAXOBS*2*NFREQ]={0};
    fixture(rtk,&obs,1,1);rtk->opt.posopt[0]=rtk->opt.posopt[2]=0;
    initx(rtk,6378137,1,0);initx(rtk,1,1,1);initx(rtk,1,1,2);initx(rtk,2,1,IT(&rtk->opt));
    H=mat(rtk->nx,2);
    nv=ppp_res(0,&obs,1,rs,dts,satvar,svh,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,azel,NULL,NULL);
    CHECK("synthetic finite PPP residual control",nv==2 && numeric_finite(v,2) && !numeric_covariance(R,2));
    dts[0]=NAN;
    nv=ppp_res(1,&obs,1,rs,dts,satvar,svh,dr,exc,mexc,nav,rtk->x,rtk,NULL,NULL,NULL,azel,NULL,NULL);
    CHECK("postfit NaN cannot pass reject gate",nv==FILTER_NAN_INPUT && rtk->ppp_failure==FILTER_NAN_INPUT);
    dts[0]=0;rtk->opt.err[1]=NAN;
    nv=ppp_res(0,&obs,1,rs,dts,satvar,svh,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,azel,NULL,NULL);
    CHECK("PPP R0 NaN gets NAN_COV failure",nv==FILTER_NAN_COV && rtk->ppp_failure==FILTER_NAN_COV);
    free(H);rtkfree(rtk);
}
int main(void)
{
    rtk_t *rtk=(rtk_t *)calloc(1,sizeof(rtk_t));nav_t *nav=(nav_t *)calloc(1,sizeof(nav_t));
    prcopt_t opt;char error[128];ppp_policy_t a,b;
    traceopen("validation/phase1/regression.trace");tracelevel(4);
    numerical_tests();lifecycle_tests(rtk,nav);transaction_tests(rtk,nav);residual_tests(rtk,nav);
    smartphone_ppp_configure(&opt,NULL);b=smartphone_ppp_policy(&opt);
    smartphone_ppp_select(&opt,"A",NULL,error,sizeof(error));a=smartphone_ppp_policy(&opt);
    CHECK("A disables experimental features and corrects lifecycle",a.corrected_lifecycle && !a.legacy_weighting && !a.quality_learning && !a.smoothing && !a.atmosphere_constraints && !a.empirical_guards && !a.startup_qc);
    CHECK("B retains legacy features",b.legacy_weighting && b.quality_learning && b.smoothing && b.atmosphere_constraints && b.empirical_guards && !b.corrected_lifecycle);
    CHECK("C cannot be accidentally enabled",!smartphone_ppp_select(&opt,"C",NULL,error,sizeof(error)));
    opt.ppp_baseline=MODE_D_ADAPTIVE_R;CHECK("D validation rejects unimplemented mode",!smartphone_ppp_validate(&opt,error,sizeof(error)));
    smartphone_ppp_configure(&opt,NULL);opt.err[1]=NAN;
    CHECK("R0 NaN is not masked by variance floor",isnan(varerr(1,SYS_GPS,PI/2,35,0,1,&opt)) &&
        !smartphone_ppp_validate(&opt,error,sizeof(error)));
    smartphone_ppp_configure(&opt,NULL);opt.maxout=300;strcpy(opt.pppopt,"-ARCGAP=12.5");
    CHECK("elapsed arc gap has seconds independent of maxout epochs",smartphone_ppp_policy(&opt).arc_gap_seconds==12.5 &&
        smartphone_ppp_validate(&opt,error,sizeof(error)));
    {
        ssat_t ss={0};double effective=2,w;
        smartphone_ppp_configure(&opt,NULL);ss.ppp_cmc_code_weak[0]=1;
        ss.ppp_res_quality[0][1].weak=1;
        opt.ppp_baseline=PPP_BASELINE_A_CLEAN;
        w=apply_legacy_robust_ppp(&opt,&ss,0,1,8,&effective);
        CHECK("A actual R ignores sticky CMC/persistent/current penalties",w==1 && effective==2);
        opt.ppp_baseline=PPP_BASELINE_B_LEGACY;effective=2;
        w=apply_legacy_robust_ppp(&opt,&ss,0,1,8,&effective);
        CHECK("B actual R preserves history and separates epoch weight",effective==128 && w==1.0/4);
        CHECK("reject rule stays separate from robust weight",reject_postfit_ppp(1,9) && !reject_postfit_ppp(0,9));
    }
    traceclose();free(rtk);free(nav);
    printf("RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
