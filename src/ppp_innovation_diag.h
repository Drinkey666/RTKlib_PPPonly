/* Phase 2: observational diagnostics only. No estimator decisions or writes. */
#ifndef PPP_INNOVATION_DIAG_H
#define PPP_INNOVATION_DIAG_H
#include "rtklib.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
    INNOV_OTHER_CONSTRAINT=0, INNOV_GNSS_CODE, INNOV_GNSS_PHASE,
    INNOV_IONO_PRIOR, INNOV_TROP_PRIOR
} ppp_measurement_class_t;
typedef struct {
    gtime_t time;
    int row_index,source_obs_index,sat,sys,frequency_slot,mexc_index;
    uint8_t signal,signal2;
    double frequency_hz,frequency2_hz,elevation_deg,cn0_dbhz,r0;
    ppp_measurement_class_t measurement_class;
    int slip_flag,arc_status,combined;
} ppp_innovation_meta_t;
enum { INNOV_ARC_NA=0,INNOV_ARC_ACTIVE,INNOV_ARC_PENDING,
    INNOV_ARC_REINITIALIZED,INNOV_ARC_UNINITIALIZED,INNOV_ARC_LEGACY_ACTIVE };
enum { INNOV_BAD_V=1,INNOV_BAD_P=2,INNOV_BAD_H=4,INNOV_BAD_R=8,
    INNOV_BAD_S=16,INNOV_NONPOSITIVE_S=32,INNOV_BAD_U=64,INNOV_NO_MEMORY=128 };
typedef struct {
    double v,obs_var,pred_var,Sii,sqrt_Sii,u;
    int u_valid,invalid_reason,inactive_state_support;
} ppp_innovation_value_t;
/* Read-only. H is nx*nv, column-major (column i = textbook row h_i).
 * P is nx*nx, R/S are nv*nv, column-major. Optional full_S is independently
 * owned output, never aliased with any input. S=H_rtklib' P H_rtklib+R.
 * Returns 0 when outputs are formed (invalid rows explicitly flagged), -1
 * for bad dimensions/pointers. No active-state compression is applied. */
int ppp_innovation_diag(const double *x,const double *P,const double *v,
    const double *H,const double *R,int nx,int nv,
    ppp_innovation_value_t *out,double *full_S);

/* CSV observer is optional and process-local: one active PC run per writer.
 * Failure to open/write diagnostics never changes estimator return/status. */
int ppp_innovation_log_open(const char *path);
int ppp_innovation_log_close(void);
int ppp_innovation_log_enabled(void);
void ppp_innovation_log_epoch(gtime_t time);
void ppp_innovation_log_trial(int trial,int baseline,int corrected,
    const ppp_innovation_meta_t *meta,const ppp_innovation_value_t *value,
    int count,const unsigned char *final_mexc,int mexc_count,
    int epoch_failure,int solution_status,int posterior_committed);
const char *ppp_innovation_class_name(ppp_measurement_class_t c);
#ifdef __cplusplus
}
#endif
#endif
