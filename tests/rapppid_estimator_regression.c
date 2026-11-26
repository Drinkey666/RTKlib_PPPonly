/* Algebraic/datum and transaction tests; no survey reference coordinates. */
#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s\n",n);}}while(0)
static int linear(void *unused,const double *at,double *v,double *H)
{v[0]=3-at[0];H[0]=1;return 0;}
static int nonlinear(void *unused,const double *at,double *v,double *H)
{v[0]=4-at[0]*at[0];H[0]=2*at[0];return 0;}
static int linear2(void *unused,const double *at,double *v,double *H)
{v[0]=10-at[0]-2*at[1];H[0]=1;H[1]=2;return 0;}
static int poison(void *unused,const double *at,double *v,double *H)
{v[0]=NAN;H[0]=1;return 0;}
static int changed(void *unused,const double *at,double *v,double *H)
{return PPP_FAILURE_IEKF_ROWS;}
static int oscillate(void *unused,const double *at,double *v,double *H)
{H[0]=1;v[0]=at[0]>1? -10:10;return 0;}
int main(void)
{
    prcopt_t a,b,w;char error[256];int ni,info;double x,P,H,v,R,ox,oP;
    rtk_t *rtk=calloc(1,sizeof(*rtk));double *state;double pos[]={.5,1.8,500},azel[]={0,.8};
    smartphone_ppp_configure(&a,NULL);a.ppp_baseline=PPP_BASELINE_A_CLEAN;b=a;w=a;
    CHECK("integrated selector",smartphone_ppp_select_estimator(&a,"INTEGRATED",NULL,NULL,NULL,error,sizeof(error)));
    CHECK("noncombined remains EST",a.ionoopt==IONOOPT_EST && NF(&a)==4);
    CHECK("integrated validated",smartphone_ppp_validate(&a,error,sizeof(error)));
    CHECK("fewer receiver states",ND(&a)==2 && ND(&b)==5 && NX(&b)-NX(&a)==3);
    CHECK("GPS datum secondary modelled without RCB",ppp_code_modelled(SYS_GPS,2,CODE_L5Q,&a) && ppp_ifb_index(SYS_GPS,2,CODE_L5Q,&a)==-1);
    CHECK("Galileo datum secondary modelled",ppp_code_modelled(SYS_GAL,2,CODE_L5Q,&a));
    CHECK("BDS pair modelled",ppp_code_modelled(SYS_CMP,0,CODE_L2I,&a)&&ppp_code_modelled(SYS_CMP,1,CODE_L7I,&a));
    CHECK("BDS residual codes get distinct states",ppp_ifb_index(SYS_CMP,2,CODE_L5P,&a)==0&&ppp_ifb_index(SYS_CMP,3,CODE_L1P,&a)==1);
    CHECK("actual code not storage slot",!ppp_code_modelled(SYS_GPS,0,CODE_L1X,&a)&&ppp_ifb_index(SYS_CMP,2,CODE_L7I,&a)==-1);
    CHECK("reference legacy mapping retained",ppp_ifb_index(SYS_GPS,2,CODE_L5Q,&b)==RCB_GPS_C5Q);
    /* Match malloc/Debug poison, rather than hiding missing initialization with calloc. */
    memset(rtk,0xCD,sizeof(*rtk));
    rtkinit(rtk,&a);
    CHECK("fresh poisoned session has no estimator lock",!rtk->ppp_estimator_locked && !rtk->ppp_estimator_flags);
    CHECK("fresh poisoned session clears atmospheric model history",
        rtk->ppp_trop_base==0.0 && rtk->ppp_trop_zhd==0.0 &&
        !rtk->ppp_trop_time.time && rtk->ppp_trop_time.sec==0.0);
    CHECK("profile locked before use",ppp_estimator_guard(rtk));
    rtk->opt.ppp_wet_correction=0;
    CHECK("live state cannot be reinterpreted as another basis",!ppp_estimator_guard(rtk));rtkfree(rtk);
    rtkinit(rtk,&a);
    CHECK("new session clears previous estimator lock",!rtk->ppp_estimator_locked && !rtk->ppp_estimator_flags);
    CHECK("new session can establish a new basis",ppp_estimator_guard(rtk));
    rtk->ppp_failure=PPP_FAILURE_IEKF_LIMIT;rtk->ssat[0].vsat[0]=1;
    rtk->ppp_clock_valid=1;rtk->ppp_clock_m=12;ppp_iekf_failed_evidence(rtk);
    CHECK("failed IEKF cannot leave accepted phase evidence",!rtk->ssat[0].vsat[0]&&rtk->ppp_clock_valid&&rtk->ppp_clock_m==12);
    rtkfree(rtk);
    a.ppp_baseline=PPP_BASELINE_B_LEGACY;
    CHECK("physical IONEX on effective ionosphere refused",!smartphone_ppp_validate(&a,error,sizeof(error)));
    a.ppp_baseline=PPP_BASELINE_A_CLEAN;a.ionoopt=IONOOPT_IFLC;
    CHECK("IF not admitted in new datum",!smartphone_ppp_validate(&a,error,sizeof(error)));a.ionoopt=IONOOPT_EST;
    {
        obsd_t ob={0};int index;
        rtkinit(rtk,&a);ob.sat=satno(SYS_CMP,25);ob.code[2]=CODE_L5P;
        uddcb_ppp(rtk,&ob,1);index=ID(0,&a);
        CHECK("unobserved RCB stays inactive",rtk->P[index+index*rtk->nx]==0);
        ob.P[2]=2E7;uddcb_ppp(rtk,&ob,1);
        CHECK("observed residual RCB initializes",rtk->P[index+index*rtk->nx]==VAR_IFB);
        index=ID(1,&a);CHECK("other RCB is not activated by wrong signal",rtk->P[index+index*rtk->nx]==0);
        rtkfree(rtk);
    }
    /* Gauge change preserves each original code/phase equation, without IF observations. */
    {
        double gamma[]={1,SQR(FREQL1/FREQL5),SQR(FREQL1/1207.14E6)},bias[]={5,11,17},B[]={100,200,300};
        double ion=7,clock=20,dI=(bias[1]-bias[0])/(gamma[1]-gamma[0]),dt=bias[0]-dI;
        int k;double maxerr=0,shifted[3];
        for(k=0;k<3;k++) {
            double newbias=bias[k]-dt-gamma[k]*dI,newB=B[k]-dt+gamma[k]*dI;
            double oldP=clock+gamma[k]*ion+bias[k],newP=clock+dt+gamma[k]*(ion+dI)+newbias;
            double oldL=clock-gamma[k]*ion+B[k],newL=clock+dt-gamma[k]*(ion+dI)+newB;
            maxerr=MAX(maxerr,MAX(fabs(oldP-newP),fabs(oldL-newL)));shifted[k]=newbias;
        }
        CHECK("raw code phase invariant under datum transformation",maxerr<1E-12);
        CHECK("two datum biases exactly removed",fabs(shifted[0])+fabs(shifted[1])<1E-12);
        /* With geometry known: [clock,I,B0,B1] is full rank for distinct gamma. */
        {double A[]={1,1,1,1, 1,gamma[1],-1,-gamma[1], 0,0,1,0, 0,0,0,1};
            CHECK("two-code datum removes clock/iono/bias nullspace",matinv(A,4)==0);}
    }
    x=0;P=1;H=1;v=2;R=1;info=filter_active(&x,&P,&H,&v,&R,1,1);
    CHECK("zero correction is active",!info&&x==1&&P==.5);
    x=0;P=1;CHECK("old zero-state convention retained",filter(&x,&P,&H,&v,&R,1,1)==FILTER_NO_ACTIVE&&x==0&&P==1);
    x=0;P=0;CHECK("uninitialized zero state stays inactive",filter_active(&x,&P,&H,&v,&R,1,1)==FILTER_NO_ACTIVE);
    {
        ppp_innovation_value_t dv;unsigned char gnss=1;
        x=0;P=1;H=1;v=1;R=1;
        info=ppp_diag_activation(&x,&P,&v,&H,&R,1,1,&dv,NULL,1);
        CHECK("diagnostics agree with zero-state active filter",!info&&!dv.inactive_state_support&&dv.Sii==2);
        info=apply_huber_robust_ppp_masked(&x,&P,&v,&H,&R,1,1,&gnss,NULL,gpst2time(2400,100),0,1);
        CHECK("existing Huber accepts valid zero wet state",!info&&R==1&&x==0&&P==1);
        info=apply_huber_robust_ppp(&x,&P,&v,&H,&R,1,1,&gnss,NULL,gpst2time(2400,100),0);
        CHECK("legacy Huber sentinel check preserved",info==FILTER_BAD_COV&&R==1);
    }
    /* Translation of total ZTD -> correction must preserve model, H and Q. */
    w.ppp_wet_correction=1;rtkinit(rtk,&w);rtk->ppp_trop_base=.2;
    rtk->ppp_trop_time=gpst2time(2400,100);pos2ecef(pos,rtk->x);
    rtk->ppp_trop_zhd=ppp_model_zhd(rtk->ppp_trop_time,pos);
    state=calloc(rtk->nx,sizeof(double));state[IT(&w)]=0;
    matcpy(state,rtk->x,3,1);
    CHECK("zero delta has meaningful total ZTD",fabs(ppp_total_trop(rtk,state)-(ppp_model_zhd(rtk->ppp_trop_time,pos)+.2))<1E-10);
    {
        double oldT,newT,var1,var2,d1[3]={0},d2[3]={0};state[IT(&w)]=.08;
        model_trop(gpst2time(2400,100),pos,azel,&w,state,.2,rtk->ppp_trop_zhd,d1,NULL,&newT,&var1);
        state[IT(&w)]=ppp_model_zhd(rtk->ppp_trop_time,pos)+.28;
        model_trop(gpst2time(2400,100),pos,azel,&b,state,0,0,d2,NULL,&oldT,&var2);
        CHECK("troposphere equation and derivative unchanged",fabs(oldT-newT)<1E-14&&var1==var2&&d1[0]==d2[0]);
    }
    {
        int it=IT(&w);double total,cov,expected_base,unused,z[]={0,PI/2};
        pos2ecef(pos,rtk->sol.rr);matcpy(rtk->x,rtk->sol.rr,3,1);rtk->tt=1;
        initx(rtk,0,.09,it);rtk->ppp_trop_base=.2;rtk->P[it]=rtk->P[it*rtk->nx]=.001;
        total=ppp_total_trop(rtk,rtk->x);cov=rtk->P[it];rtk->sol.time=gpst2time(2400,100);
        expected_base=sbstropcorr(rtk->sol.time,pos,z,&unused)-ppp_model_zhd(rtk->sol.time,pos);
        udtrop_ppp(rtk,rtk->sol.time);
        CHECK("valid zero delta not reinitialized",fabs((rtk->ppp_trop_base+rtk->x[it])-.2)<1E-14);
        CHECK("model base recentered",fabs(rtk->ppp_trop_base-expected_base)<1E-10);
        CHECK("cross covariance retained",rtk->P[it]==cov);
        CHECK("Q unchanged",fabs(rtk->P[it+it*rtk->nx]-(.09+SQR(w.prn[2])))<1E-15);
    }
    free(state);rtkfree(rtk);free(rtk);
    x=1;P=2;H=1;v=2;R=.5;ox=x;oP=P;
    info=ppp_iekf_update(&x,&P,&H,&v,&R,1,1,linear,NULL,&ni);
    CHECK("linear IEKF equals one KF",!info&&fabs(x-2.6)<1E-14&&fabs(P-.4)<1E-14);
    CHECK("relinearization occurs without covariance reuse",ni==2&&P>.39&&R==.5);
    {
        double xx[]={1,2},pp[]={4,1,1,9},hh[]={1,2},vv=5,rr=3;
        info=ppp_iekf_update(xx,pp,hh,&vv,&rr,2,1,linear2,NULL,&ni);
        CHECK("IEKF H layout and cross covariance match hand matrix",!info&&
            fabs(xx[0]-(1+30.0/47))<1E-14&&fabs(xx[1]-(2+95.0/47))<1E-14&&
            fabs(pp[0]-(4-36.0/47))<1E-14&&fabs(pp[1]-(1-114.0/47))<1E-14&&
            fabs(pp[3]-(9-361.0/47))<1E-14);
    }
    x=1;P=1;H=2;v=3;R=.25;
    info=ppp_iekf_update(&x,&P,&H,&v,&R,1,1,nonlinear,NULL,&ni);
    CHECK("nonlinear IEKF converges",!info&&ni>2&&ni<=PPP_IEKF_MAX_ITER);
    CHECK("prior term included in nonlinear MAP",fabs((x-1)-2*x*(4-x*x)/R)<.01);
    CHECK("covariance is one fixed-prior update",fabs(P-1/(1+H*H/R))<1E-12);
    x=1;P=2;H=1;v=2;R=.5;ox=x;oP=P;
    info=ppp_iekf_update(&x,&P,&H,&v,&R,1,1,poison,NULL,&ni);
    CHECK("NaN iteration fails atomically",info==FILTER_NAN_INPUT&&x==ox&&P==oP&&H==1&&v==2);
    info=ppp_iekf_update(&x,&P,&H,&v,&R,1,1,changed,NULL,&ni);
    CHECK("row change fails atomically",info==PPP_FAILURE_IEKF_ROWS&&x==ox&&P==oP);
    info=ppp_iekf_update(&x,&P,&H,&v,&R,1,1,oscillate,NULL,&ni);
    CHECK("nonconvergence fails atomically",info==PPP_FAILURE_IEKF_LIMIT&&x==ox&&P==oP&&ni==PPP_IEKF_MAX_ITER);
    v=INFINITY;info=ppp_iekf_update(&x,&P,&H,&v,&R,1,1,linear,NULL,&ni);
    CHECK("Inf innovation fails atomically",info==FILTER_NAN_INPUT&&x==ox&&P==oP);
    printf("ESTIMATOR_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
