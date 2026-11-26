#include "../src/ppp.c"
#include "../src/gnss_adapter.h"
#include <stdio.h>
extern int reliability_spp_tests(void);
static int passed,failed;
#define CHECK(name,c) do {if(c){passed++;printf("PASS %s\n",name);}else{failed++;printf("FAIL %s line=%d\n",name,__LINE__);}}while(0)
static void raw_fixture(gnss_adapter_t *ctx,android_clock_t *clock,android_meas_t *m)
{
    gnss_adapter_init(ctx);memset(clock,0,sizeof(*clock));memset(m,0,sizeof(*m));
    clock->has_full_bias=1;clock->time_nanos=100000000000LL;
    clock->full_bias_nanos=-2400LL*604800000000000LL;
    m->constellation_type=1;m->svid=1;m->carrier_frequency_hz=FREQL1;
    strcpy(m->code_type,"C");m->state=9;m->received_sv_time_nanos=99930000000LL;
    m->received_sv_time_uncertainty_nanos=1;m->adr_state=ANDROID_ADR_VALID;
    m->adr_meters=2E7;m->adr_uncertainty_meters=.1;m->cn0_dbhz=35;
    m->pseudorange_rate_mps=-10;m->pseudorange_rate_uncertainty_mps=.1;
}
static void next_epoch(android_clock_t *c,android_meas_t *m)
{c->time_nanos+=1000000000LL;m->received_sv_time_nanos+=1000000000LL;}
static void adapter_tests(void)
{
    static gnss_adapter_t ctx;static nav_t nav;static rtk_t rtk;
    android_clock_t c;android_meas_t m,mm[2];obsd_t obs[2];gnss_adapter_stats_t st;
    prcopt_t opt;int n,bi;
    raw_fixture(&ctx,&c,&m);n=gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("normal P/L/D/CN0 preserved",n==1 && !obs[0].LLI[0] &&
        fabs(obs[0].P[0]-.07*CLIGHT)<1E-8 && obs[0].L[0]==m.adr_meters/(CLIGHT/FREQL1) &&
        obs[0].D[0]==(float)(10/(CLIGHT/FREQL1)) && obs[0].SNR[0]==35000);
    next_epoch(&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("continuous normal phase does not reset",!obs[0].LLI[0] && !ctx.pending_reset[0][0]);
    next_epoch(&c,&m);c.hardware_clock_discontinuity_count++;m.adr_state=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("clock discontinuity emits reset with missing phase",obs[0].L[0]==0 &&
        (obs[0].LLI[0]&LLI_SLIP) && (ctx.pending_reset[0][0]&1));
    smartphone_ppp_configure(&opt,NULL);opt.nf=1;opt.ppp_baseline=PPP_BASELINE_A_CLEAN;
    strcpy(opt.pppopt,"-PREPROC=1 -DOPPSM=0 -DOPPSLIP=0 -MWTHRES=0");
    rtkinit(&rtk,&opt);bi=IB(1,0,&opt);initx(&rtk,123,1,bi);initx(&rtk,5,1,II(1,&opt));
    rtk.sol.rr[0]=6378137;rtk.sol.time=obs[0].time;rtk.ssat[0].azel[1]=PI/2;
    precheck_obs_ppp(&rtk,obs,1,&nav);udbias_ppp(&rtk,obs,1,&nav);
    CHECK("adapter to PPP missing-phase event invalidates old ambiguity",rtk.x[bi]==0 && rtk.ssat[0].ppp_arc_pending[0]);
    next_epoch(&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("retained missing-phase event is not a new slip each epoch",!obs[0].LLI[0] && ctx.pending_reset[0][0]);
    next_epoch(&c,&m);m.adr_state=ANDROID_ADR_VALID;m.state=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("phase recovery without code keeps reset evidence",obs[0].L[0]!=0 && obs[0].P[0]==0 &&
        (obs[0].LLI[0]&LLI_SLIP) && ctx.pending_reset[0][0]);
    precheck_obs_ppp(&rtk,obs,1,&nav);udbias_ppp(&rtk,obs,1,&nav);
    CHECK("core stays pending until a valid ambiguity seed",rtk.x[bi]==0 && rtk.ssat[0].ppp_arc_pending[0]);
    next_epoch(&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("retained phase-only event is not repeatedly counted",!obs[0].LLI[0] && ctx.pending_reset[0][0]);
    next_epoch(&c,&m);m.state=9;gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("complete recovery transfers reset to core",(obs[0].LLI[0]&LLI_SLIP) && !ctx.pending_reset[0][0]);
    precheck_obs_ppp(&rtk,obs,1,&nav);udbias_ppp(&rtk,obs,1,&nav);
    CHECK("recovered P/L initializes a new ambiguity",rtk.x[bi]!=0 && rtk.x[bi]!=123 && !rtk.ssat[0].ppp_arc_pending[0]);
    next_epoch(&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("normal phase resumes after recovery",!obs[0].LLI[0]);rtkfree(&rtk);
    c.clock_discontinuity=1;gnss_adapter_convert(&ctx,&c,NULL,0,NULL,0,&st);
    c.clock_discontinuity=0;next_epoch(&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("synthetic clock reset survives empty callback",(obs[0].LLI[0]&LLI_SLIP) && !ctx.pending_reset[0][0]);
    c.hardware_clock_discontinuity_count++;c.has_full_bias=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);c.has_full_bias=1;
    next_epoch(&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("clock event survives unavailable clock bias",obs[0].LLI[0]&LLI_SLIP);
    next_epoch(&c,&m);c.hardware_clock_discontinuity_count++;m.adr_uncertainty_meters=10;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("ADR uncertainty rejection cannot consume reset",obs[0].L[0]==0 && ctx.pending_reset[0][0]);
    next_epoch(&c,&m);m.adr_uncertainty_meters=.1;gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("reset survives uncertainty recovery",obs[0].LLI[0]&LLI_SLIP);
    next_epoch(&c,&m);m.adr_state=ANDROID_ADR_RESET;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    next_epoch(&c,&m);m.adr_state=ANDROID_ADR_VALID;gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("ADR reset without VALID persists to next valid phase",(obs[0].LLI[0]&LLI_SLIP) && st.lli_android==1);
    next_epoch(&c,&m);m.svid=2;gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("satellite absent during clock reset restarts on return",obs[0].sat==2 && (obs[0].LLI[0]&LLI_SLIP));
    raw_fixture(&ctx,&c,&m);m.constellation_type=6;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);next_epoch(&c,&m);strcpy(m.code_type,"B");
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("actual signal switch cannot continue prior phase arc",obs[0].code[0]==CODE_L1B && (obs[0].LLI[0]&LLI_SLIP));
    next_epoch(&c,&m);m.adr_state=0;strcpy(m.code_type,"C");
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    next_epoch(&c,&m);m.adr_state=ANDROID_ADR_VALID;strcpy(m.code_type,"B");
    gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("code-only alternate signal does not invent phase switch",!obs[0].LLI[0]);
    raw_fixture(&ctx,&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    mm[0]=m;mm[1]=m;mm[1].svid=2;mm[1].adr_state|=ANDROID_ADR_SLIP;
    gnss_adapter_convert(&ctx,&c,mm,2,obs,1,&st);
    CHECK("output overflow preserves reset evidence",st.overflow==1 && (ctx.pending_reset[1][0]&2));
    mm[1].adr_state=ANDROID_ADR_VALID;gnss_adapter_convert(&ctx,&c,mm+1,1,obs,2,&st);
    CHECK("overflowed satellite carries reset when emitted",obs[0].sat==2 && (obs[0].LLI[0]&LLI_SLIP));
    gnss_adapter_init(&ctx);raw_fixture(&ctx,&c,&m);gnss_adapter_convert(&ctx,&c,&m,1,obs,2,&st);
    CHECK("new session clears old reset evidence",!obs[0].LLI[0]);
}
int main(void)
{
    int spp_fail=reliability_spp_tests();adapter_tests();
    printf("ADAPTER_RESULT passed=%d failed=%d\n",passed,failed);
    return failed+spp_fail?1:0;
}
