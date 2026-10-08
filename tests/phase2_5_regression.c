/* Observer-only lifecycle regressions; no estimator decisions. */
#define main phase1_main
#include "phase1_regression.c"
#undef main
static void meta(ppp_innovation_meta_t *m,int row)
{
    memset(m,0,sizeof(*m));m->time=gpst2time(2400,140);
    m->row_index=row;m->source_obs_index=0;m->sat=1;m->frequency_slot=0;m->signal=CODE_L1C;
    m->measurement_class=row?INNOV_GNSS_PHASE:INNOV_GNSS_CODE;
}
int main(void)
{
    rtk_t *rtk=(rtk_t *)calloc(1,sizeof(rtk_t)),*before=(rtk_t *)malloc(sizeof(rtk_t));
    obsd_t obs,oc;ppp_innovation_meta_t m;double H[4]={1,0,0,1},Hc[4];
    unsigned char slips[NFREQ]={0};unsigned long id;double *xb,*Pb;
    fixture(rtk,&obs,1,1);memcpy(before,rtk,sizeof(*rtk));oc=obs;memcpy(Hc,H,sizeof H);
    xb=mat(rtk->nx,1);Pb=mat(rtk->nx,rtk->nx);matcpy(xb,rtk->x,rtk->nx,1);matcpy(Pb,rtk->P,rtk->nx,rtk->nx);
    CHECK("observer open",ppp_innovation_log_open("validation/phase2_5/observer_unit.csv"));
    ppp_innovation_log_epoch(obs.time);ppp_innovation_note_spp(1);
    ppp_innovation_core_begin(2,&obs,1,1,rtk);ppp_innovation_note_current_init(0,0,0,0);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);id=m.arc_id;
    CHECK("first observation ARC_INIT",m.lifecycle_bits&INNOV_LIFE_INIT && m.continuous_epochs==1 && m.arc_age==0);
    CHECK("current SPP initialization explicit",m.state_init_from_current_obs && m.state_init_affects_row && m.spp_from_current_obs && m.spp_attempted && m.provenance_valid);
    obs.time=timeadd(obs.time,1);ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("continuous observation independent of ambiguity sentinel",m.arc_id==id && m.arc_age==1 && m.continuous_epochs==2 && m.lifecycle_bits==INNOV_LIFE_CONTINUOUS);
    CHECK("no invented observation initialization",!m.state_init_from_current_obs&&!m.spp_from_current_obs);
    ppp_innovation_meta_provenance(&m,H,2,1);
    CHECK("editing retry flag without age increment",m.same_epoch_reentry && m.continuous_epochs==2 && m.arc_age==1);
    ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("same GNSS epoch reentry retains arc/count",m.same_epoch_reentry && m.arc_id==id && m.continuous_epochs==2);
    obs.time=timeadd(obs.time,2);ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("post-gap recovery starts fresh arc",m.gap_flag && (m.lifecycle_bits&INNOV_LIFE_RECOVERY) && (m.lifecycle_bits&INNOV_LIFE_POST_GAP) && m.arc_id>id && m.continuous_epochs==1 && m.arc_age==0);id=m.arc_id;
    obs.time=timeadd(obs.time,1);ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    slips[0]=1;ppp_innovation_core_events(&obs,1,rtk,slips);ppp_innovation_core_events(&obs,1,rtk,slips);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("confirmed slip breaks arc exactly once",m.arc_id==id+1 && (m.lifecycle_bits&INNOV_LIFE_RESTART) && m.continuous_epochs==1);id=m.arc_id;
    obs.LLI[0]=LLI_SLIP;ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    ppp_innovation_core_events(&obs,1,rtk,slips);ppp_innovation_note_current_init(1,1,0,1);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("same-time slip/init reentry does not reset arc again",m.same_epoch_reentry&&m.arc_id==id&&m.continuous_epochs==1);
    slips[0]=0;obs.LLI[0]=0;
    obs.time=timeadd(obs.time,1);obs.code[0]=CODE_L1X;ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("actual signal switch breaks arc",m.signal_switch_flag && m.arc_id==id+1 && m.continuous_epochs==1);id=m.arc_id;
    obs.time=timeadd(obs.time,1);ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,0,1,rtk);
    obs.time=timeadd(obs.time,1);ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("missing input epoch breaks arc",m.gap_flag && m.arc_id==id+1 && m.continuous_epochs==1);
    ppp_innovation_note_current_init(1,1,0,1);meta(&m,0);m.time=obs.time;m.signal=obs.code[0];
    ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("ambiguity seed global provenance with P row unaffected",m.state_init_from_current_obs && m.ambiguity_init_from_current_obs && !m.state_init_affects_row);
    meta(&m,1);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("phase row sees initialized ambiguity state",m.state_init_affects_row);
    obs.time=timeadd(obs.time,1);ppp_innovation_log_epoch(obs.time);ppp_innovation_note_spp(0);
    ppp_innovation_core_begin(2,&obs,1,1,rtk);meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("failed SPP clock source unknown, not falsely clean",m.spp_attempted && !m.spp_from_current_obs && !m.provenance_valid);
    obs.time=timeadd(obs.time,1);ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    ppp_innovation_note_current_adjustment(0);meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("legacy current-observation adjustment separate from init",m.legacy_current_obs_adjustment && !m.state_init_from_current_obs);
    CHECK("observer APIs preserve estimator and H bitwise",!memcmp(rtk,before,sizeof(*rtk))&&!memcmp(H,Hc,sizeof H)&&
        !memcmp(rtk->x,xb,rtk->nx*sizeof(double))&&!memcmp(rtk->P,Pb,(size_t)rtk->nx*rtk->nx*sizeof(double)));
    /* Only P disappears; the raw signal and L remain continuous. */
    obs.time=timeadd(obs.time,1);obs.P[0]=0;ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,1);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    obs.time=timeadd(obs.time,1);obs.P[0]=oc.P[0];ppp_innovation_log_epoch(obs.time);ppp_innovation_core_begin(2,&obs,1,1,rtk);
    meta(&m,0);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("missing P splits P innovation while raw/L continue",m.gap_flag&&(m.lifecycle_bits&INNOV_LIFE_POST_GAP)&&m.continuous_epochs==1&&m.arc_age==0&&m.raw_continuous_epochs>1);
    meta(&m,1);m.time=obs.time;m.signal=obs.code[0];ppp_innovation_meta_provenance(&m,H,2,0);
    CHECK("P loss does not split valid L sequence",!m.gap_flag&&m.continuous_epochs==2&&m.lifecycle_bits==INNOV_LIFE_CONTINUOUS);
    CHECK("observer did not mutate original observation fields",obs.P[0]==oc.P[0]&&obs.L[0]==oc.L[0]&&obs.SNR[0]==oc.SNR[0]);
    ppp_innovation_log_close();rtkfree(rtk);free(rtk);free(before);free(xb);free(Pb);
    printf("RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
