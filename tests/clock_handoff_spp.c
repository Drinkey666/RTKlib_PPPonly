/* Exercise real rtkpos handoff with deterministic SPP/PPP callbacks. */
#define rtkpos handoff_rtkpos
#define rtkinit handoff_rtkinit
#define rtkfree handoff_rtkfree
#define rtkopenstat handoff_rtkopenstat
#define rtkclosestat handoff_rtkclosestat
#define rtkoutstat handoff_rtkoutstat
#define pntpos clock_mock_pntpos
#define pntpos_startup clock_mock_pntpos
#define pppos clock_mock_pppos
#include "../PPP_only/ppp_position.c"
#undef rtkpos
#undef rtkinit
#undef rtkfree
#undef rtkopenstat
#undef rtkclosestat
#undef rtkoutstat
#undef pntpos
#undef pntpos_startup
#undef pppos
#include <stdio.h>
static int reject_spp,ppp_called;
int clock_mock_pntpos(const obsd_t *obs,int n,const nav_t *nav,const prcopt_t *opt,
    sol_t *sol,double *azel,ssat_t *ssat,char *msg)
{
    sol->dtr[0]=999999/CLIGHT;sol->rr[0]=6378137+1000;
    sol->time=obs[0].time;sol->stat=SOLQ_SINGLE;
    return !reject_spp;
}
void clock_mock_pppos(rtk_t *rtk,const obsd_t *obs,int n,const nav_t *nav){ppp_called++;}
int clock_handoff_spp_tests(void)
{
    static rtk_t rtk;static nav_t nav;obsd_t obs={0};prcopt_t opt;
    int bad=0;char error[128];
    smartphone_ppp_configure(&opt,NULL);smartphone_ppp_select(&opt,"C",NULL,error,sizeof(error));
    handoff_rtkinit(&rtk,&opt);
    obs.time=gpst2time(2400,100);obs.sat=1;obs.rcv=1;obs.code[0]=CODE_L1C;obs.P[0]=2E7;
    rtk.x[0]=6378137;rtk.P[0]=1;rtk.sol.rr[0]=6378137;
    rtk.sol.dtr[0]=12345/CLIGHT;rtk.ppp_clock_valid=1;rtk.ppp_clock_m=12345;
    handoff_rtkpos(&rtk,&obs,1,&nav);
    if(rtk.sol.dtr[0]!=12345/CLIGHT || rtk.sol.rr[0]!=6378137 || !rtk.ppp_spp_clock_valid || !ppp_called)bad++;
    printf("%s isolated accepted SPP does not overwrite trusted PPP solution\n",bad?"FAIL":"PASS");
    reject_spp=1;ppp_called=0;rtk.sol.dtr[0]=12345/CLIGHT;
    handoff_rtkpos(&rtk,&obs,1,&nav);
    if(rtk.sol.dtr[0]!=12345/CLIGHT || rtk.ppp_spp_clock_valid || !ppp_called)bad++;
    printf("%s failed SPP cannot leak candidate to PPP\n",bad?"FAIL":"PASS");
    reject_spp=0;rtk.ppp_clock_valid=0;
    handoff_rtkpos(&rtk,&obs,1,&nav);
    if(rtk.sol.dtr[0]!=999999/CLIGHT)bad++;
    printf("%s initial accepted SPP remains usable for bootstrap\n",bad?"FAIL":"PASS");
    handoff_rtkfree(&rtk);return bad;
}
