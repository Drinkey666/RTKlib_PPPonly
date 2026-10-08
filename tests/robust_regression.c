/* Independent synthetic checks for C's pre-fit Huber update. */
#include <stdio.h>
#include <string.h>
#include "../src/ppp.c"
static int passed,failed;
#define CHECK(name,condition) do { if(condition){passed++;printf("PASS %s\n",name);}else{failed++;printf("FAIL %s (line %d)\n",name,__LINE__);} }while(0)
static int approx_equal(double a,double b)
{
    return fabs(a-b)<=1E-11*MAX(1.0,MAX(fabs(a),fabs(b)));
}
int main(void)
{
    double x[2]={1.0,2.0},p[4]={2.0,.5,.5,3.0},h[2]={1.0,1.0};
    double xx[2],pp[4],hh[2];
    double r[4],v[2],oldr[4],h2[4]={1,1,1,1};
    unsigned char mask[2]={1,0};
    prcopt_t opt;char error[128];int info;gtime_t stamp={0};
    memcpy(xx,x,sizeof(x));memcpy(pp,p,sizeof(p));memcpy(hh,h,sizeof(h));
    r[0]=1.0;v[0]=3.0*sqrt(7.0);
    info=apply_huber_robust_ppp(x,p,v,h,r,2,1,mask,NULL,stamp,0);
    CHECK("cross-covariance enters pre-fit S=hPh+R",!info && approx_equal(r[0],2.0));
    CHECK("robust weight is read-only on x P H v",!memcmp(x,xx,sizeof(x)) &&
        !memcmp(p,pp,sizeof(p)) && !memcmp(h,hh,sizeof(h)) && approx_equal(v[0],3.0*sqrt(7.0)));
    r[0]=1.0;v[0]=1.4*sqrt(7.0);
    info=apply_huber_robust_ppp(x,p,v,h,r,2,1,mask,NULL,stamp,0);
    CHECK("normal innovation keeps R bitwise",!info && r[0]==1.0);
    mask[0]=0;r[0]=1.0;v[0]=100.0;
    info=apply_huber_robust_ppp(x,p,v,h,r,2,1,mask,NULL,stamp,0);
    CHECK("constraint mask does not robustly inflate R",!info && r[0]==1.0);
    mask[0]=1;v[0]=3.0*sqrt(7.0);v[1]=100.0;
    r[0]=1.0;r[1]=r[2]=0.0;r[3]=5.0;mask[1]=0;
    info=apply_huber_robust_ppp(x,p,v,h2,r,2,2,mask,NULL,stamp,0);
    CHECK("GNSS row weighted while pseudo row stays fixed",!info && approx_equal(r[0],2.0) && r[3]==5.0 && r[1]==0 && r[2]==0);
    {
        double sx=1.0,sp=4.0,sh=1.0,sv=3.0*sqrt(5.0),sr=1.0;
        mask[0]=1;
        info=apply_huber_robust_ppp(&sx,&sp,&sv,&sh,&sr,1,1,mask,NULL,stamp,0);
        CHECK("scalar Huber uses prediction variance and w=1/2",!info && approx_equal(sr,2.0));
        info=filter(&sx,&sp,&sh,&sv,&sr,1,1);
        CHECK("weighted EKF gain and posterior match hand calculation",!info &&
            approx_equal(sx,1.0+4.0*sv/6.0) && approx_equal(sp,4.0/3.0));
    }
    r[0]=1.0;r[1]=r[2]=0.0;r[3]=5.0;memcpy(oldr,r,sizeof(r));
    mask[0]=mask[1]=1;v[1]=NAN;
    info=apply_huber_robust_ppp(x,p,v,h2,r,2,2,mask,NULL,stamp,0);
    CHECK("nonfinite later row fails without partial R edit",info==FILTER_NAN_INPUT && !memcmp(r,oldr,sizeof(r)));
    r[0]=0.0;v[0]=INFINITY;mask[1]=0;
    info=apply_huber_robust_ppp(x,p,v,h,r,2,1,mask,NULL,stamp,0);
    CHECK("infinite innovation fails without masking",info==FILTER_NAN_INPUT && r[0]==0.0);
    smartphone_ppp_configure(&opt,NULL);
    CHECK("explicit C selects Huber model",smartphone_ppp_select(&opt,"C",NULL,error,sizeof(error)) &&
        smartphone_ppp_validate(&opt,error,sizeof(error)) && opt.ppp_baseline==MODE_C_NEW_ROBUST &&
        !smartphone_ppp_policy(&opt).legacy_weighting && smartphone_ppp_policy(&opt).corrected_lifecycle);
    opt.ppp_baseline=MODE_D_ADAPTIVE_R;
    CHECK("D remains unavailable",!smartphone_ppp_validate(&opt,error,sizeof(error)));
    printf("RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
