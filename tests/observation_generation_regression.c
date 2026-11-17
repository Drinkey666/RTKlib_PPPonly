#include "../src/gnss_adapter.h"
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#define CSV_COLS 80
#include "../validation/observation_generation_2023_v1/production_parser.h"
static int passed,failed;
#define TEST(name,x) do{if(x){passed++;printf("PASS %s\n",name);}else{failed++;printf("FAIL %s:%d\n",name,__LINE__);}}while(0)
static void base(gnss_adapter_t *ctx,android_clock_t *c,android_meas_t *m) {
    gnss_adapter_init(ctx);memset(c,0,sizeof(*c));memset(m,0,sizeof(*m));
    c->has_full_bias=1;c->time_nanos=100000000000LL;c->full_bias_nanos=-2400LL*604800000000000LL;
    c->has_leap_seconds=1;c->leap_seconds=18;
    m->constellation_type=1;m->svid=1;m->state=9;m->sv_time_status=1;
    m->received_sv_time_nanos=99930000000LL;m->received_sv_time_uncertainty_nanos=1;
    m->cn0_dbhz=35;m->adr_state=25;m->adr_meters=-1234.5;m->adr_uncertainty_meters=.01;
    m->carrier_frequency_hz=1575420000.;strcpy(m->code_type,"C");
    m->pseudorange_rate_mps=-10;m->pseudorange_rate_uncertainty_mps=.1;
}
static void advance(android_clock_t *c,android_meas_t *m) {c->time_nanos+=1000000000LL;m->received_sv_time_nanos+=1000000000LL;}
int main(void) {
    static gnss_adapter_t ctx;android_clock_t c,view;android_meas_t m,pair[2];obsd_t obs[5];gnss_adapter_stats_t st;
    int n;double p,l,lam;int64_t f;gnss_clock_reference_t ref={0};gnss_nanotime_t t;
    base(&ctx,&c,&m);n=gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);p=obs[0].P[0];l=obs[0].L[0];lam=CLIGHT/m.carrier_frequency_hz;
    TEST("normal P",n==1 && fabs(p-.07*CLIGHT)<1e-8);
    TEST("negative ADR preserved",l==m.adr_meters/lam && l<0);
    TEST("Doppler sign",obs[0].D[0]==(float)(10/lam));
    TEST("SNR unit",obs[0].SNR[0]==35000);
    f=ctx.clock_reference.full_bias_ref;advance(&c,&m);c.full_bias_nanos+=256;c.bias_nanos=.75;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("FullBias anchor held",ctx.clock_reference.full_bias_ref==f);
    TEST("Bias anchor held",ctx.clock_reference.bias_ref==0.);
    TEST("no extra 76m code step",obs[0].P[0]==p);
    TEST("phase not retuned",obs[0].L[0]==l);
    TEST("FBN update is not a hardware slip",!(obs[0].LLI[0]&1));
    advance(&c,&m);c.full_bias_nanos+=999936;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("coarse estimate update does not reanchor",ctx.clock_reference.full_bias_ref==f && obs[0].P[0]==p);
    TEST("coarse estimate update does not reset arcs",!(obs[0].LLI[0]&1));
    advance(&c,&m);c.has_full_bias=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("known anchor survives missing current estimate",obs[0].P[0]==p);
    c.hardware_clock_discontinuity_count++;advance(&c,&m);
    n=gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("new segment waits for valid reference",n==0 && st.invalid_clock==1);
    TEST("reset evidence retained",ctx.pending_reset[0][0]&GNSS_RESET_CLOCK);
    c.has_full_bias=1;c.bias_nanos=0.;advance(&c,&m);m.received_sv_time_nanos-=1000192;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("HCDC establishes new FullBias",ctx.clock_reference.full_bias_ref==c.full_bias_nanos);
    TEST("new segment has new identity",ctx.clock_reference.segment==2);
    TEST("phase arc reset survives invalid clock",obs[0].LLI[0]&1);
    base(&ctx,&c,&m);pair[0]=m;pair[1]=m;pair[1].svid=2;
    gnss_adapter_convert(&ctx,&c,pair,2,obs,5,&st);f=ctx.clock_reference.full_bias_ref;
    c.time_nanos+=1000000000LL;for(int i=0;i<2;i++)pair[i].received_sv_time_nanos+=1000000000LL;
    pair[0].adr_state=27;gnss_adapter_convert(&ctx,&c,pair,2,obs,5,&st);
    TEST("VALID RESET is not a phase sample",obs[0].L[0]==0 && (obs[0].LLI[0]&1));
    TEST("one ADR reset does not reset shared clock",ctx.clock_reference.full_bias_ref==f && ctx.clock_reference.segment==1);
    TEST("other satellite remains continuous",obs[1].L[0]!=0 && !(obs[1].LLI[0]&1));
    advance(&c,&pair[0]);pair[0].adr_state=25;pair[0].state=0;
    gnss_adapter_convert(&ctx,&c,pair,1,obs,5,&st);
    TEST("phase-only recovery retains pending",obs[0].L[0]!=0 && (obs[0].LLI[0]&1) && ctx.pending_reset[0][0]);
    advance(&c,&pair[0]);pair[0].state=9;gnss_adapter_convert(&ctx,&c,pair,1,obs,5,&st);
    TEST("complete recovery transfers reset",(obs[0].LLI[0]&1) && !ctx.pending_reset[0][0]);
    advance(&c,&pair[0]);gnss_adapter_convert(&ctx,&c,pair,1,obs,5,&st);
    TEST("recovered arc continuous",!(obs[0].LLI[0]&1));
    base(&ctx,&c,&m);m.adr_state=17;gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("half-cycle explicitly flagged",obs[0].L[0]!=0 && (obs[0].LLI[0]&2));
    advance(&c,&m);m.adr_state=25;gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("half-cycle transition splits phase arc",obs[0].LLI[0]&1);
    base(&ctx,&c,&m);c.bias_nanos=.25;m.time_offset_nanos=.75;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("fractional ns preserved",fabs(obs[0].P[0]-(.07*CLIGHT+.5e-9*CLIGHT))<1e-8);
    TEST("actual offset timestamps",fabs(obs[0].time.sec-.0000000005)<1e-16);
    base(&ctx,&c,&m);c.time_nanos=30000000LL;m.received_sv_time_nanos=604799960000000LL;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("GPS week wrap",fabs(obs[0].P[0]-.07*CLIGHT)<1e-8);
    base(&ctx,&c,&m);c.time_nanos=70000000LL;m.received_sv_time_nanos=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("valid zero transmit time at boundary",fabs(obs[0].P[0]-.07*CLIGHT)<1e-8);
    base(&ctx,&c,&m);m.constellation_type=5;m.carrier_frequency_hz=1561098000.;strcpy(m.code_type,"I");
    c.time_nanos=14070000000LL;m.received_sv_time_nanos=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("BDT fourteen seconds and wrap",fabs(obs[0].P[0]-.07*CLIGHT)<1e-8);
    for(int k=-7;k<=6;k+=13) {
        base(&ctx,&c,&m);m.constellation_type=3;m.state=64|128;m.carrier_frequency_hz=1602e6+k*.5625e6;
        c.time_nanos=75618070000000LL;m.received_sv_time_nanos=0;
        gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
        TEST("GLONASS channel wavelength",fabs(obs[0].L[0]-m.adr_meters/(CLIGHT/m.carrier_frequency_hz))<1e-10);
        TEST("GLONASS day wrap and UTC leap",fabs(obs[0].P[0]-.07*CLIGHT)<1e-8);
    }
    base(&ctx,&c,&m);m.constellation_type=3;m.state=64|128;m.carrier_frequency_hz=1602e6;
    c.time_nanos=75618070000000LL;c.has_leap_seconds=0;m.received_sv_time_nanos=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("date-dependent leap fallback",fabs(obs[0].P[0]-.07*CLIGHT)<1e-8);
    base(&ctx,&c,&m);c.full_bias_nanos=0;c.has_leap_seconds=0;c.time_nanos=75600070000000LL;
    m.constellation_type=3;m.state=64|128;m.carrier_frequency_hz=1602e6;m.received_sv_time_nanos=0;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("historical leap zero",fabs(obs[0].P[0]-.07*CLIGHT)<1e-8);
    base(&ctx,&c,&m);pair[0]=m;pair[1]=m;pair[1].carrier_frequency_hz=1176450000.;strcpy(pair[1].code_type,"Q");pair[1].time_offset_nanos=1000000;
    n=gnss_adapter_convert(&ctx,&c,pair,2,obs,5,&st);
    TEST("mixed signal times explicitly unsupported",n==0 && st.time_conflicts==1);
    base(&ctx,&c,&m);c.time_nanos=INT64_MAX;c.full_bias_nanos=-INT64_MAX;
    n=gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("overflow is failure, not zero filling",n==0 && st.invalid_clock==1);
    base(&ctx,&c,&m);c.bias_nanos=NAN;
    TEST("NaN anchor rejected",gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st)==0);
    base(&ctx,&c,&m);gnss_clock_reference_apply(&ref,&c,&view);
    android_clock_t twice;gnss_clock_reference_t next={0};gnss_clock_reference_apply(&next,&view,&twice);
    TEST("already normalized reference is not applied twice",twice.full_bias_nanos==view.full_bias_nanos && twice.bias_nanos==view.bias_nanos && twice.reference_segment==view.reference_segment);
    TEST("normalization does not modify Raw",c.reference_segment==0 && c.clock_correction_nanos==0);
    TEST("integer precision",gnss_receiver_nanotime(&view,.5,&t) && t.fraction_ns==.5);
    base(&ctx,&c,&m);m.adr_meters=1e-6;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("small nonzero phase is not a missing-value threshold",obs[0].L[0]!=0.0);
    base(&ctx,&c,&m);m.adr_meters=0.;
    gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st);
    TEST("RTKLIB exact-zero sentinel is diagnosed",st.phase_zero_sentinel==1);
    base(&ctx,&c,&m);m.constellation_type=3;m.carrier_frequency_hz=NAN;
    TEST("NaN GLONASS frequency rejected before integer conversion",gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st)==0 && st.unsupported==1);
    m.carrier_frequency_hz=1e300;
    TEST("oversized GLONASS frequency rejected before integer conversion",gnss_adapter_convert(&ctx,&c,&m,1,obs,5,&st)==0 && st.unsupported==1);
    base(&ctx,&c,&m);pair[0]=m;pair[0].adr_meters=NAN;pair[1]=m;
    gnss_adapter_convert(&ctx,&c,pair,2,obs,5,&st);
    TEST("invalid duplicate does not outrank a valid phase",obs[0].L[0]!=0.0 && isfinite(obs[0].L[0]));
    {char line[4096];const char *fields[54];int q;
        android_clock_t previous={0};
        for(q=0;q<54;q++)fields[q]="";
        fields[0]="Raw";fields[2]="100000000000";fields[5]="-1451520000000000000";
        fields[11]="1";fields[13]="9";fields[14]="99930000000";fields[15]="1";
        fields[19]="25";fields[20]="123";fields[21]="0.1";fields[22]="1575420000";fields[28]="1";fields[35]="C";
        line[0]=0;for(q=0;q<54;q++){strcat(line,fields[q]);if(q<53)strcat(line,",");}
        TEST("production parser accepts complete integer clock",parse_raw(line,&c,&m,&previous)==1 && c.has_full_bias);
        TEST("missing PRR is not valid zero",isnan(m.pseudorange_rate_mps) && isnan(m.pseudorange_rate_uncertainty_mps));
        fields[2]="bad";line[0]=0;for(q=0;q<54;q++){strcat(line,fields[q]);if(q<53)strcat(line,",");}
        TEST("malformed TimeNanos rejected",!parse_raw(line,&c,&m,&previous));
        fields[2]="100000000000";fields[5]="bad";fields[14]="";line[0]=0;for(q=0;q<54;q++){strcat(line,fields[q]);if(q<53)strcat(line,",");}
        parse_raw(line,&c,&m,&previous);
        TEST("missing clock and transmitter not zero-filled",!c.has_full_bias && m.sv_time_status==-1);
    }
    printf("OBS_GENERATION_2023: passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
