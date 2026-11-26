#define main unused_phase1_main
#include "phase1_regression.c"
#undef main
int clock_handoff_spp_tests(void);

int main(void)
{
    static rtk_t rtk;
    prcopt_t opt;char error[128];
    ppp_innovation_meta_t meta[8];double v[8],before[8],shift;
    unsigned char eligible[MAXSAT][NFREQ]={{0}};
    int i,peers,group,phase,ok;
    smartphone_ppp_configure(&opt,NULL);
    CHECK("B AUTO retains legacy SPP clock",!smartphone_ppp_policy(&opt).common_clock);
    smartphone_ppp_select(&opt,"C",NULL,error,sizeof(error));
    CHECK("C AUTO uses common clock",smartphone_ppp_policy(&opt).common_clock);
    smartphone_ppp_select_clock(&opt,"LEGACY_SPP",error,sizeof(error));
    CHECK("explicit legacy restores C previous clock policy",!smartphone_ppp_policy(&opt).common_clock);
    CHECK("invalid clock mode rejected",!smartphone_ppp_select_clock(&opt,"BAD",error,sizeof(error)));
    smartphone_ppp_select_clock(&opt,"PPP_COMMON",error,sizeof(error));
    rtkinit(&rtk,&opt);
    rtk.ppp_clock_valid=1;rtk.ppp_clock_m=12345;rtk.sol.dtr[0]=999999.0/CLIGHT;
    udclk_ppp(&rtk);
    CHECK("current SPP cannot overwrite committed PPP clock",rtk.x[IC(0,&opt)]==12345);
    CHECK("white-clock variance remains unchanged",rtk.P[IC(0,&opt)*(rtk.nx+1)]==VAR_CLK);
    rtk.ppp_clock_valid=0;udclk_ppp(&rtk);
    CHECK("first bootstrap can use accepted SPP",fabs(rtk.x[IC(0,&opt)]-999999)<1E-9);
    rtk.ppp_clock_valid=1;rtk.ppp_clock_m=0;udclk_ppp(&rtk);
    CHECK("physical zero clock has active-state representation",rtk.x[IC(0,&opt)]!=0 && fabs(rtk.x[IC(0,&opt)])<=1E-6);
    {
        obsd_t ob={0};int b=IB(1,0,&opt);ob.sat=1;ob.code[0]=CODE_L1C;
        initx(&rtk,20,1,b);
        CHECK("previous unaccepted phase cannot seed common clock",!ppp_clock_phase_ready(&rtk,&ob,0));
        rtk.ssat[0].vsat[0]=1;
        CHECK("continuous accepted phase can seed common clock",ppp_clock_phase_ready(&rtk,&ob,0));
        rtk.ssat[0].ppp_arc_pending[0]=1;
        CHECK("pending reset removes phase clock vote",!ppp_clock_phase_ready(&rtk,&ob,0));
        rtk.ssat[0].ppp_arc_pending[0]=0;ob.LLI[0]=LLI_SLIP;
        CHECK("confirmed slip removes phase clock vote",!ppp_clock_phase_ready(&rtk,&ob,0));
        ob.LLI[0]=0;
    }
    memset(meta,0,sizeof(meta));
    for(i=0;i<5;i++) {
        meta[i].sat=i+1;meta[i].sys=SYS_GPS;meta[i].source_obs_index=i;
        meta[i].frequency_slot=0;meta[i].measurement_class=INNOV_GNSS_PHASE;
        eligible[i][0]=1;v[i]=1500000;
    }
    memcpy(before,v,5*sizeof(double));
    ok=ppp_common_clock_seed(&rtk,v,meta,5,eligible,&shift,&peers,&group,&phase);
    CHECK("large genuine common clock jump is not clipped",ok && shift==1500000 && peers==5 && phase && group==0);
    CHECK("clock location leaves residual input read-only",!memcmp(before,v,5*sizeof(double)));
    v[0]+=1000000;
    ok=ppp_common_clock_seed(&rtk,v,meta,5,eligible,&shift,&peers,&group,&phase);
    CHECK("one contaminated phase vote cannot move common location",ok && shift==1500000);
    v[0]=-999999;
    ok=ppp_common_clock_seed(&rtk,v,meta,5,eligible,&shift,&peers,&group,&phase);
    CHECK("negative isolated phase fault cannot move common location",ok && shift==1500000);
    for(i=0;i<5;i++)v[i]=-1500000;
    ok=ppp_common_clock_seed(&rtk,v,meta,5,eligible,&shift,&peers,&group,&phase);
    CHECK("negative genuine clock jump is not clipped",ok && shift==-1500000);
    /* Multiple frequencies on one bad satellite must remain one vote. */
    for(i=0;i<4;i++){meta[i].sat=1;meta[i].frequency_slot=i;eligible[0][i]=1;v[i]=1000;}
    for(i=4;i<6;i++){meta[i]=meta[0];meta[i].sat=i-2;meta[i].frequency_slot=0;eligible[i-3][0]=1;v[i]=10;}
    ok=ppp_common_clock_seed(&rtk,v,meta,6,eligible,&shift,&peers,&group,&phase);
    CHECK("one satellite four signals still has one vote",ok && peers==3 && shift==10);
    for(i=0;i<3;i++) {
        meta[i].sat=i+1;meta[i].frequency_slot=0;meta[i].measurement_class=INNOV_GNSS_PHASE;
        v[i]=10;eligible[i][0]=1;
    }
    rtk.ssat[0].ppp_arc_reset[0]=1;
    ok=ppp_common_clock_seed(&rtk,v,meta,3,eligible,&shift,&peers,&group,&phase);
    CHECK("slipped or gap-reset phase cannot vote",!ok);
    rtk.ssat[0].ppp_arc_reset[0]=0;eligible[0][0]=0;
    CHECK("newly initialized ambiguity cannot vote",!ppp_common_clock_seed(&rtk,v,meta,3,eligible,&shift,&peers,&group,&phase));
    for(i=0;i<3;i++) {
        meta[3+i]=meta[i];meta[3+i].measurement_class=INNOV_GNSS_CODE;v[3+i]=20;
    }
    v[3]=1000;
    ok=ppp_common_clock_seed(&rtk,v,meta,6,eligible,&shift,&peers,&group,&phase);
    CHECK("insufficient continuous phase falls back to code median",ok && !phase && shift==20 && peers==3);
    v[3]=30;v[4]=20;v[5]=10;
    ok=ppp_common_clock_seed(&rtk,v+3,meta+3,3,eligible,&shift,&peers,&group,&phase);
    CHECK("clock seed recalculates from edited row set",ok && shift==20);
    CHECK("two remaining satellites do not fabricate consensus",!ppp_common_clock_seed(&rtk,v+4,meta+4,2,eligible,&shift,&peers,&group,&phase));
    for(i=0;i<3;i++) {meta[i].sys=SYS_CMP;meta[i].measurement_class=INNOV_GNSS_CODE;v[i]=15;}
    ok=ppp_common_clock_seed(&rtk,v,meta,3,eligible,&shift,&peers,&group,&phase);
    CHECK("no GPS uses available constellation datum with predicted ISB",ok && group==3 && shift==15);
    meta[0].measurement_class=INNOV_IONO_PRIOR;meta[1].measurement_class=INNOV_TROP_PRIOR;
    CHECK("virtual priors cannot seed receiver clock",!ppp_common_clock_seed(&rtk,v,meta,3,eligible,&shift,&peers,&group,&phase));
    {
        static nav_t nav;obsd_t obs;
        rtkfree(&rtk);
        fixture(&rtk,&obs,1,1);rtk.ppp_clock_valid=1;rtk.ppp_clock_m=12345;
        obs.P[0]=NAN;pppos(&rtk,&obs,1,&nav);
        CHECK("PPP failure cannot promote or replace trusted clock",rtk.ppp_failure==FILTER_NAN_INPUT && rtk.ppp_clock_valid && rtk.ppp_clock_m==12345);
    }
    rtkfree(&rtk);
    i=clock_handoff_spp_tests();
    printf("CLOCK_RESULT passed=%d failed=%d handoff_failed=%d\n",passed,failed,i);
    return failed||i?1:0;
}
