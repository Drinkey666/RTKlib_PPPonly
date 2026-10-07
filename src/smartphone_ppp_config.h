/* Canonical smartphone PPP defaults. Vendor this file unchanged for Android. */
#ifndef SMARTPHONE_PPP_CONFIG_H
#define SMARTPHONE_PPP_CONFIG_H
#include "rtklib.h"
#ifdef __cplusplus
extern "C" {
#endif
#define SMARTPHONE_PPP_PROFILE "pc-baseline-20260930-v1"
typedef enum { PPP_BASELINE_B_LEGACY=0, PPP_BASELINE_A_CLEAN=1,
    MODE_C_NEW_ROBUST=2, MODE_D_ADAPTIVE_R=3 } ppp_baseline_t;
typedef enum { PPP_LIFECYCLE_LEGACY=0, PPP_LIFECYCLE_CORRECTED=1 } ppp_lifecycle_t;
typedef struct {
    int legacy_weighting, quality_learning, smoothing, atmosphere_constraints;
    int empirical_guards, startup_qc, corrected_lifecycle;
    double arc_gap_seconds; /* elapsed-time continuity bound, not maxout epochs */
} ppp_policy_t;
#define PPP_ARC_GAP_SECONDS_DEFAULT 30.0
/* Sole mode policy. Reserved C/D modes are rejected, never silently run A/B. */
ppp_policy_t smartphone_ppp_policy(const prcopt_t *opt);
int smartphone_ppp_select(prcopt_t *opt, const char *baseline,
    const char *lifecycle, char *error, size_t capacity);
/* No products, state allocation or environment overrides are performed here. */
void smartphone_ppp_configure(prcopt_t *opt, solopt_t *sol);
/* Returns 0 with an explanation if compile-time layout/options conflict. */
int smartphone_ppp_validate(const prcopt_t *opt, char *error, size_t capacity);
/* Human-readable effective options for console, Android logcat and trace.
 * The signature covers the printed fields, not product identities or all of
 * prcopt_t. Never interpret equal signatures as proof of equal products. */
unsigned int smartphone_ppp_describe(const prcopt_t *opt, char *out, size_t capacity);
void smartphone_ppp_log(const char *entry, const prcopt_t *opt);
#ifdef __cplusplus
}
#endif
#endif
