/* Numerical and transactional tests, no PPP product/weight parameter changes. */
#include <stdio.h>
#include <float.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s line=%d\n",n,__LINE__);}}while(0)
static int poison_after_trial(void *ctx,const double *x,double *v,double *H)
{v[0]=NAN;H[0]=1.0;return 0;}
static int linear(void *ctx,const double *x,double *v,double *H)
{v[0]=3.0-x[0];H[0]=1.0;return 0;}
int main(void)
{
    double x[3]={1,0,7},P[9]={2,.25,0,.25,1,0,0,0,0};
    double H[3]={1,1,9},v=2,R=1,xb[3],Pb[9];
    double cov[4]={1,1+4*DBL_EPSILON,1+4*DBL_EPSILON,1};
    double bad[4]={1,1.1,1.1,1},scaled[4]={1E20,.1,.1,1E-20};
    double singular[4]={1,1,1,1},zero[4]={0,0,0,2};
    int info,it;
    CHECK("PSD near roundoff boundary accepted without repair",numeric_covariance_psd(cov,2)==0 &&
        cov[1]==1+4*DBL_EPSILON);
    CHECK("significant indefinite covariance rejected",numeric_covariance_psd(bad,2)==FILTER_NOT_PSD);
    CHECK("unit scaling preserves PSD classification",numeric_covariance_psd(scaled,2)==0);
    scaled[1]=scaled[2]=1.1;
    CHECK("unit scaling preserves nonPSD classification",numeric_covariance_psd(scaled,2)==FILTER_NOT_PSD);
    CHECK("rank deficient PSD accepted",numeric_covariance_psd(singular,2)==0);
    CHECK("inactive zero covariance accepted",numeric_covariance_psd(zero,2)==0);
    zero[1]=zero[2]=1E-20;
    CHECK("nonzero inactive cross covariance rejected",numeric_covariance_psd(zero,2)==FILTER_NOT_PSD);
    CHECK("nonsymmetric covariance rejected",numeric_covariance_psd((double[]){1,.2,.5,1},2)==FILTER_BAD_COV);
    CHECK("NaN covariance rejected",numeric_covariance_psd((double[]){NAN},1)==FILTER_NAN_COV);
    CHECK("Inf covariance rejected",numeric_covariance_psd((double[]){INFINITY},1)==FILTER_NAN_COV);
    memcpy(xb,x,sizeof x);memcpy(Pb,P,sizeof P);
    info=filter_physical(x,P,H,&v,&R,3,1);
    CHECK("normal positive definite update",info==0 && numeric_covariance_psd(P,3)==0);
    CHECK("finite posterior state",numeric_finite(x,3));
    CHECK("zero valued active state updated",x[1]!=0);
    CHECK("inactive state and variance preserved",x[2]==7 && P[8]==0);
    /* PH= [2.25,1.25,0], S=4.5; posterior x is hand-verifiable. */
    CHECK("normal gain/state equation",fabs(x[0]-2)<1E-14 && fabs(x[1]-5.0/9)<1E-14);
    CHECK("Joseph equals exact covariance",fabs(P[0]-.875)<1E-14 && fabs(P[4]-(1-1.5625/4.5))<1E-14);
    {
        double xx[2]={1,2},pp[4]={1,1.1,1.1,1},hh[2]={1,0},vv=1,rr=1;
        double save[4];memcpy(save,pp,sizeof pp);
        CHECK("bad prior rejected before update",filter_physical(xx,pp,hh,&vv,&rr,2,1)==FILTER_PSD_PRIOR);
        CHECK("bad prior failure is atomic",xx[0]==1 && xx[1]==2 && !memcmp(pp,save,sizeof pp));
    }
    {
        double xx=1,pp=2,hh[2]={1,2},vv[2]={1,-2},rr[4]={1,.3,.3,2};
        info=filter_physical(&xx,&pp,hh,vv,rr,1,2);
        CHECK("correlated R gives exact state update",info==0 && fabs(xx-(1-4/11.51))<1E-14);
        CHECK("Joseph includes offdiagonal R",fabs(pp-3.82/11.51)<1E-14 && numeric_covariance_psd(&pp,1)==0);
        xx=1;pp=1;hh[0]=1;vv[0]=1;rr[0]=0;
        CHECK("PSD zero R accepted when S invertible",
            filter_physical(&xx,&pp,hh,vv,rr,1,1)==0 && xx==2 && pp==0);
        xx=1;pp=1;hh[0]=hh[1]=1;vv[0]=vv[1]=1;
        memset(rr,0,sizeof rr);
        CHECK("singular S rejected with PSD R",filter_physical(&xx,&pp,hh,vv,rr,1,2)!=0);
        CHECK("singular S failure is atomic",xx==1 && pp==1);
    }
    {
        double xx=1,pp=1,hh[2]={1,1},vv[2]={1,1},rr[4]={1,2,2,1};
        CHECK("bad R rejected before update",filter_physical(&xx,&pp,hh,vv,rr,1,2)==FILTER_PSD_R);
        CHECK("bad R leaves prediction unchanged",xx==1 && pp==1);
    }
    {
        double xx=1,pp=1,hh=1,vv=NAN,rr=1;
        CHECK("NaN innovation protected",filter_physical(&xx,&pp,&hh,&vv,&rr,1,1)==FILTER_NAN_INPUT);
        CHECK("NaN failure atomic",xx==1 && pp==1);
        vv=INFINITY;
        CHECK("Inf innovation protected",filter_physical(&xx,&pp,&hh,&vv,&rr,1,1)==FILTER_NAN_INPUT);
        CHECK("Inf failure atomic",xx==1 && pp==1);
        vv=DBL_MAX;hh=.1;pp=1E4;
        CHECK("overflow after valid input rejected",filter_physical(&xx,&pp,&hh,&vv,&rr,1,1)==FILTER_NAN_STATE);
        CHECK("overflow does not partially commit",xx==1 && pp==1E4);
        /* Subsequent finite prediction (fixed Q) and next update recover. */
        pp+=.1;vv=1;hh=1;
        CHECK("next epoch prediction/update can continue",filter_physical(&xx,&pp,&hh,&vv,&rr,1,1)==0 &&
            numeric_finite(&xx,1) && numeric_covariance_psd(&pp,1)==0);
    }
    {
        double xx=1,pp=1,hh=1,vv=2,rr=1;
        info=ppp_iekf_update_core(&xx,&pp,&hh,&vv,&rr,1,1,poison_after_trial,NULL,&it,1);
        CHECK("later IEKF iteration failure propagated",info==FILTER_NAN_INPUT && it==2);
        CHECK("earlier IEKF trial does not commit",xx==1 && pp==1 && hh==1 && vv==2);
        info=ppp_iekf_update_core(&xx,&pp,&hh,&vv,&rr,1,1,linear,NULL,&it,1);
        CHECK("next IEKF epoch succeeds once from retained prior",info==0 && xx==2 && pp==.5 && it==2);
    }
    CHECK("posterior transaction gate rejects significant nonPSD",
        ppp_covariance_gate(bad,2,1,1)==FILTER_PSD_POSTERIOR);
    CHECK("prior transaction gate rejects significant nonPSD",
        ppp_covariance_gate(bad,2,1,0)==FILTER_PSD_PRIOR);
    CHECK("legacy gate unchanged",ppp_covariance_gate(bad,2,0,1)==0);
    CHECK("failure reasons traceable",!strcmp(filter_reason(FILTER_PSD_POSTERIOR),"NON_PSD_POSTERIOR"));
    printf("%d passed, %d failed\n",passed,failed);return failed?1:0;
}
