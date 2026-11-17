#include <stdio.h>
#include "ppp_estimator_under_test.c"
#include "gnss_adapter.h"
#include "gnss_signal_policy.h"
static int passed,failed;
#define CHECK(n,c) do {if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s:%d\n",n,__LINE__);}}while(0)
int main(int argc,char **argv)
{
    prcopt_t opt;solopt_t sol=solopt_default;char error[256];obsd_t obs={0},original;
    nav_t *nav=(nav_t*)calloc(1,sizeof(nav_t));rtk_t *rtk=(rtk_t*)calloc(1,sizeof(rtk_t));
    double z[NFREQ]={0},azel[]={0,PI/2},L[NFREQ],P[NFREQ],Lc,Pc,expected0,expected3,gamma0,gamma3;
    int sat=satid2no("C19"),n0,n3,rcb;
    smartphone_ppp_configure(&opt,&sol);
    CHECK("B_VERIFIED uses four slots",smartphone_ppp_select_profile(&opt,"B_VERIFIED",error,sizeof(error))&&opt.nf==4);
    CHECK("B1I is admitted",gnss_ppp_signal_allowed(SYS_CMP,0,CODE_L2I));
    CHECK("B1C is admitted simultaneously",gnss_ppp_signal_allowed(SYS_CMP,3,CODE_L1P));
    CHECK("B2a remains admitted",gnss_ppp_signal_allowed(SYS_CMP,2,CODE_L5P));
    CHECK("B2b remains excluded",!ppp_signal_supported(SYS_CMP,1,CODE_L7D,&opt)&&!gnss_ppp_signal_allowed(SYS_CMP,1,CODE_L7D));
    CHECK("IQ Q policy unchanged",!gnss_ppp_signal_allowed(SYS_CMP,2,CODE_L5Q));
    CHECK("B1C code model exists",ppp_code_modelled(SYS_CMP,3,CODE_L1P,&opt));
    CHECK("B1C receiver bias is independent of B2a",ppp_ifb_index(SYS_CMP,3,CODE_L1P,&opt)==RCB_BDS_C1P&&RCB_BDS_C1P!=RCB_BDS_C5P);
    obs.sat=sat;obs.time=gpst2time(2442,526432.);obs.code[0]=CODE_L2I;obs.code[3]=CODE_L1P;
    obs.P[0]=22000000.;obs.P[3]=22000002.;obs.L[0]=1e8;obs.L[3]=1e8+10000.;obs.SNR[0]=obs.SNR[3]=40000;
    nav->nosb=nav->nosbmax=2;nav->osbs=(codeosb_t*)calloc(2,sizeof(codeosb_t));
    nav->osbs[0].start=nav->osbs[1].start=timeadd(obs.time,-1);
    nav->osbs[0].end=timeadd(obs.time,100);nav->osbs[1].end=timeadd(obs.time,1);
    nav->osbs[0].bias=2.;nav->osbs[1].bias=1.;nav->osb_head[sat-1][CODE_L2I]=1;nav->osb_head[sat-1][CODE_L1P]=2;
    original=obs;corr_meas(&obs,nav,azel,&opt,z,z,NULL,0.,L,P,&Lc,&Pc);
    CHECK("B1I uses its own OSB",P[0]==obs.P[0]-2.);
    CHECK("B1C uses C1P OSB instead of B1I OSB",P[3]==obs.P[3]-1.);
    CHECK("B1I carrier actual wavelength",L[0]==obs.L[0]*CLIGHT/1561098000.);
    CHECK("B1C carrier actual wavelength",L[3]==obs.L[3]*CLIGHT/1575420000.);
    CHECK("Raw measurement stays unchanged",!memcmp(&obs,&original,sizeof(obs)));
    rtkinit(rtk,&opt);rtk->sol.time=obs.time;rtk->sol.rr[0]=6378137.;rtk->ssat[sat-1].azel[1]=PI/2;
    n0=IB(sat,0,&opt);n3=IB(sat,3,&opt);rcb=ID(RCB_BDS_C1P,&opt);
    initx(rtk,5.,1.,II(sat,&opt));initx(rtk,4.,100.,rcb);
    gamma0=SQR(FREQL1/1561098000.);gamma3=SQR(FREQL1/1575420000.);
    expected0=L[0]-P[0]+2*gamma0*5.;expected3=L[3]-(P[3]-4.)+2*gamma3*5.;
    udbias_ppp(rtk,&obs,1,nav);
    CHECK("B1I and B1C ambiguity indices differ",n0!=n3);
    CHECK("B1I ambiguity initializes independently",fabs(rtk->x[n0]-expected0)<1e-7);
    CHECK("B1C ambiguity includes its own RCB",fabs(rtk->x[n3]-expected3)<1e-7);
    CHECK("B1C ambiguity initial covariance retained",rtk->P[n3+n3*rtk->nx]==VAR_BIAS);
    obs.time=timeadd(obs.time,2);corr_meas(&obs,nav,azel,&opt,z,z,NULL,0.,L,P,&Lc,&Pc);
    CHECK("expired C1P OSB removes only B1C code",P[3]==0.&&P[0]!=0.&&L[3]!=0.);
    initx(rtk,0.,0.,n3);expected3=L[3]-P[0]+(gamma3+gamma0)*5.;udbias_ppp(rtk,&obs,1,nav);
    CHECK("phase-only B1C uses B1I reference without C1P RCB",fabs(rtk->x[n3]-expected3)<1e-7);
    CHECK("reference seeding does not replace B1I ambiguity",fabs(rtk->x[n0]-expected0)<1e-7);
    obs.code[3]=CODE_L7D;initx(rtk,0.,0.,n3);udbias_ppp(rtk,&obs,1,nav);
    CHECK("B2b cannot enter under B1C storage slot",rtk->x[n3]==0.);
    if(argc>1) {
        pcvs_t pcvs={0};pcv_t *pcv;int prns[]={6,7,11,12,19},i;double pco[3];
        const double ep[]={2026,10,31,0,0,0};gtime_t time=epoch2time(ep);
        CHECK("current ANTEX loads",readpcv(argv[1],&pcvs));
        for(i=0;i<5;i++) {
            pcv=searchpcv(satno(SYS_CMP,prns[i]),"",time,&pcvs);
            CHECK("B1C C01 calibration present for actual satellite",pcv&&pcv_antex_pco(pcv,1,pco));
            CHECK("B1C slot 3 stores C01 PCO",pcv&&!memcmp(pcv->off[3],pco,sizeof(pco)));
            CHECK("B1I retains its separate C02 PCO",pcv&&pcv_antex_pco(pcv,2,pco)&&!memcmp(pcv->off[0],pco,sizeof(pco)));
        }
        free(pcvs.pcv);
    }
    rtkfree(rtk);free(rtk);free(nav->osbs);free(nav);
    printf("B1C_INTEGRATION_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
