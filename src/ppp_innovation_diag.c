#include "ppp_innovation_diag.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int ppp_innovation_diag(const double *x,const double *P,const double *v,
    const double *H,const double *R,int nx,int nv,
    ppp_innovation_value_t *out,double *full_S)
{
    int i,j,a,b,k,total=0,*index,*offset,goodP;
    if(nx<=0 || nv<=0 || !x || !P || !v || !H || !R || !out ||
        (size_t)nx>(size_t)-1/sizeof(int)/(size_t)nv)return -1;
    for(i=0;i<nv;i++) {
        out[i].v=v[i];out[i].obs_var=R[i+i*nv];
        out[i].pred_var=out[i].Sii=out[i].sqrt_Sii=out[i].u=NAN;
        out[i].u_valid=out[i].inactive_state_support=0;
        out[i].invalid_reason=(!isfinite(v[i])?INNOV_BAD_V:0)|
            (!isfinite(R[i+i*nv])?INNOV_BAD_R:0);
    }
    if(full_S)for(i=0;i<nv;i++)for(j=0;j<nv;j++)full_S[i+j*nv]=NAN;
    index=(int *)malloc((size_t)nx*nv*sizeof(int));
    offset=(int *)malloc(((size_t)nv+1)*sizeof(int));
    if(!index || !offset) {
        for(i=0;i<nv;i++)out[i].invalid_reason|=INNOV_NO_MEMORY;
        free(index);free(offset);return 0;
    }
    goodP=numeric_finite(P,(size_t)nx*nx);
    for(i=0;i<nv;i++) {
        offset[i]=total;
        if(!goodP)out[i].invalid_reason|=INNOV_BAD_P;
        for(a=0;a<nx;a++) {
            double h=H[a+i*nx];
            if(!isfinite(h))out[i].invalid_reason|=INNOV_BAD_H;
            if(h==0.0)continue;
            index[total++]=a;
            /* Expose the RTKLIB zero-state sentinel without changing S. */
            if(x[a]==0.0 || !(P[a+a*nx]>0.0)) {
                for(k=0;k<nx;k++)if(P[a+k*nx]!=0.0 || P[k+a*nx]!=0.0) {
                    out[i].inactive_state_support=1;break;
                }
            }
        }
    }
    offset[nv]=total;
    for(i=0;i<nv;i++) {
        double pred=0.0;
        if(!(out[i].invalid_reason&(INNOV_BAD_P|INNOV_BAD_H))) {
            /* Exact sparse form of h_i P h_i'; cross covariance retained. */
            for(a=offset[i];a<offset[i+1];a++)for(b=offset[i];b<offset[i+1];b++)
                pred+=H[index[a]+i*nx]*P[index[a]+index[b]*nx]*H[index[b]+i*nx];
            out[i].pred_var=pred;out[i].Sii=pred+out[i].obs_var;
        }
        if(!isfinite(out[i].Sii))out[i].invalid_reason|=INNOV_BAD_S;
        else if(out[i].Sii<=0.0)out[i].invalid_reason|=INNOV_NONPOSITIVE_S;
        else {
            out[i].sqrt_Sii=sqrt(out[i].Sii);
            if(isfinite(v[i]))out[i].u=v[i]/out[i].sqrt_Sii;
            if(!isfinite(out[i].u))out[i].invalid_reason|=INNOV_BAD_U;
        }
        out[i].u_valid=out[i].invalid_reason==0;
        if(full_S) {
            for(j=0;j<nv;j++) {
                double s=0.0;
                if(!goodP || (out[i].invalid_reason&INNOV_BAD_H) ||
                    (out[j].invalid_reason&INNOV_BAD_H))continue;
                for(a=offset[i];a<offset[i+1];a++)for(b=offset[j];b<offset[j+1];b++)
                    s+=H[index[a]+i*nx]*P[index[a]+index[b]*nx]*H[index[b]+j*nx];
                full_S[i+j*nv]=s+R[i+j*nv];
            }
        }
    }
    free(index);free(offset);return 0;
}

static FILE *innovation_csv;
static gtime_t first_input,current_input;
static unsigned long epoch_index;
static int io_error;
const char *ppp_innovation_class_name(ppp_measurement_class_t c)
{
    switch(c) {
        case INNOV_GNSS_CODE:return "GNSS_CODE";
        case INNOV_GNSS_PHASE:return "GNSS_PHASE";
        case INNOV_IONO_PRIOR:return "IONO_PRIOR";
        case INNOV_TROP_PRIOR:return "TROP_PRIOR";
        default:return "OTHER_CONSTRAINT";
    }
}
static const char *arc_name(int a)
{
    switch(a) {
        case INNOV_ARC_ACTIVE:return "ACTIVE";
        case INNOV_ARC_PENDING:return "ARC_PENDING_INIT";
        case INNOV_ARC_REINITIALIZED:return "ARC_REINITIALIZED";
        case INNOV_ARC_UNINITIALIZED:return "UNINITIALIZED";
        case INNOV_ARC_LEGACY_ACTIVE:return "LEGACY_ACTIVE";
        default:return "NA";
    }
}
static void reasons(int reason,char *s)
{
    s[0]=0;
#define REASON(bit,name) if(reason&(bit)){if(*s)strcat(s,"|");strcat(s,name);}
    REASON(INNOV_BAD_V,"NONFINITE_V");REASON(INNOV_BAD_P,"NONFINITE_P");
    REASON(INNOV_BAD_H,"NONFINITE_H");REASON(INNOV_BAD_R,"NONFINITE_R");
    REASON(INNOV_BAD_S,"NONFINITE_S");REASON(INNOV_NONPOSITIVE_S,"NONPOSITIVE_S");
    REASON(INNOV_BAD_U,"NONFINITE_U");REASON(INNOV_NO_MEMORY,"DIAG_NO_MEMORY");
#undef REASON
    if(!*s)strcpy(s,"OK");
}
int ppp_innovation_log_open(const char *path)
{
    ppp_innovation_log_close();io_error=0;epoch_index=0;
    first_input.time=current_input.time=0;first_input.sec=current_input.sec=0.0;
    if(!path || !*path)return 1;
    innovation_csv=fopen(path,"w");
    if(!innovation_csv)return 0;
    fprintf(innovation_csv,"time,week,tow,epoch,elapsed_s,stage,trial,sample_scope,baseline,lifecycle,row,sat,sys,signal,signal2,frequency_slot,frequency_hz,frequency2_hz,combined,obs_type,elevation_deg,cn0_dbhz,source_obs_index,v,R0_or_R,R0,pred_var,obs_var,Sii,sqrt_Sii,u,finite_flag,invalid_reason,measurement_class,slip_flag,arc_status,legacy_reject_flag,inactive_state_support,epoch_failure,solution_status,posterior_committed,abs_v,sqrt_Rii,sqrt_pred_var,abs_u\n");
    return !ferror(innovation_csv);
}
int ppp_innovation_log_close(void)
{
    if(innovation_csv){if(fclose(innovation_csv))io_error=1;innovation_csv=NULL;}
    return !io_error;
}
int ppp_innovation_log_enabled(void){return innovation_csv!=NULL && !io_error;}
void ppp_innovation_log_epoch(gtime_t time)
{
    if(!ppp_innovation_log_enabled())return;
    current_input=time;
    if(!epoch_index)first_input=time;
    epoch_index++;
}
void ppp_innovation_log_trial(int trial,int baseline,int corrected,
    const ppp_innovation_meta_t *meta,const ppp_innovation_value_t *value,
    int count,const unsigned char *final_mexc,int mexc_count,
    int epoch_failure,int solution_status,int posterior_committed)
{
    int i,week;char time[40],sid[8],reason[200];
    double elapsed;
    if(!ppp_innovation_log_enabled() || !meta || !value)return;
    elapsed=timediff(current_input,first_input);
    for(i=0;i<count;i++) {
        const ppp_innovation_meta_t *m=&meta[i];const ppp_innovation_value_t *d=&value[i];
        const char *sys=m->sys==SYS_GPS?"G":m->sys==SYS_GAL?"E":m->sys==SYS_CMP?"C":
            m->sys==SYS_GLO?"R":m->sys==SYS_QZS?"J":m->sys==SYS_SBS?"S":m->sys==SYS_IRN?"I":"";
        const char *type=m->measurement_class==INNOV_GNSS_CODE?"P":m->measurement_class==INNOV_GNSS_PHASE?"L":"PRIOR";
        int rejected=m->mexc_index>=0 && m->mexc_index<mexc_count && final_mexc && final_mexc[m->mexc_index];
        double tow=time2gpst(m->time,&week);
        sid[0]=0;if(m->sat)satno2id(m->sat,sid);time2str(m->time,time,3);reasons(d->invalid_reason,reason);
        fprintf(innovation_csv,"%s,%d,%.9f,%lu,%.9f,%s,%d,%s,%s,%s,%d,%s,%s,%s,%s,%d,%.17g,%.17g,%d,%s,%.9f,%.9f,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%s,%s,%d,%s,%d,%d,%d,%d,%d,%.17g,%.17g,%.17g,%.17g\n",
            time,week,tow,epoch_index,elapsed,elapsed>=0 && elapsed<30.0?"STARTUP":"STEADY",trial,
            trial==0?"FIRST_PREFIT":"EDIT_RETRY",baseline==1?"A":"B",corrected?"CORRECTED":"LEGACY",
            m->row_index,sid,sys,m->signal?code2obs(m->signal):"",m->signal2?code2obs(m->signal2):"",
            m->frequency_slot,m->frequency_hz,m->frequency2_hz,m->combined,type,m->elevation_deg,m->cn0_dbhz,
            m->source_obs_index,d->v,d->obs_var,m->r0,d->pred_var,d->obs_var,d->Sii,d->sqrt_Sii,d->u,
            d->u_valid,reason,ppp_innovation_class_name(m->measurement_class),m->slip_flag,arc_name(m->arc_status),
            rejected,d->inactive_state_support,epoch_failure,solution_status,posterior_committed,fabs(d->v),
            isfinite(d->obs_var)&&d->obs_var>=0?sqrt(d->obs_var):NAN,
            isfinite(d->pred_var)&&d->pred_var>=0?sqrt(d->pred_var):NAN,fabs(d->u));
    }
    if(ferror(innovation_csv)) {io_error=1;fprintf(stderr,"INNOV_DIAG_IO_ERROR,estimator_unchanged=1\n");}
}
