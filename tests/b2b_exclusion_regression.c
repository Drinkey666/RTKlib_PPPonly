#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do {if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s:%d\n",n,__LINE__);}}while(0)
int main(void)
{
    const uint8_t codes[]={CODE_L7D,CODE_L7P,CODE_L7Z};int i,f,j;
    prcopt_t opt;solopt_t sol=solopt_default;char error[256];obsd_t obs={0};
    rtk_t *rtk=(rtk_t*)calloc(1,sizeof(rtk_t));nav_t *nav=(nav_t*)calloc(1,sizeof(nav_t));
    smartphone_ppp_configure(&opt,&sol);
    CHECK("B_VERIFIED profile",smartphone_ppp_select_profile(&opt,"B_VERIFIED",error,sizeof(error)));
    for(i=0;i<3;i++)for(f=0;f<NFREQ;f++)CHECK("B2b rejected independent of storage slot",!ppp_signal_supported(SYS_CMP,f,codes[i],&opt));
    CHECK("B2I remains separate and supported",ppp_signal_supported(SYS_CMP,1,CODE_L7I,&opt));
    CHECK("B2a remains supported",ppp_signal_supported(SYS_CMP,2,CODE_L5P,&opt));
    CHECK("GPS L5 unchanged",ppp_signal_supported(SYS_GPS,2,CODE_L5Q,&opt));
    CHECK("GAL E5a unchanged",ppp_signal_supported(SYS_GAL,2,CODE_L5Q,&opt));
    opt.ppp_physical_atmosphere=1;
    for(i=0;i<3;i++)CHECK("alternate estimator cannot enable B2b",!ppp_signal_supported(SYS_CMP,1,codes[i],&opt));
    opt.ppp_physical_atmosphere=0;
    rtkinit(rtk,&opt);obs.sat=satid2no("C01");obs.time=gpst2time(2442,526432.);
    obs.code[0]=CODE_L2I;obs.P[0]=22000000.;obs.code[1]=CODE_L7D;obs.P[1]=22000001.;obs.L[1]=1e8;
    rtk->sol.time=obs.time;rtk->sol.rr[0]=6378137.;rtk->ssat[obs.sat-1].azel[1]=PI/2;
    initx(rtk,5.,1.,II(obs.sat,&opt));j=IB(obs.sat,1,&opt);
    for(i=0;i<3;i++) {
        obs.code[1]=codes[i];udbias_ppp(rtk,&obs,1,nav);
        CHECK("RINEX-like B2b input cannot initialize carrier state",rtk->x[j]==0.&&rtk->P[j+j*rtk->nx]==0.);
    }
    rtkfree(rtk);free(rtk);free(nav);
    printf("B2B_EXCLUSION_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
