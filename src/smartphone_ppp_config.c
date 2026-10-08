#include "smartphone_ppp_config.h"
#include <stdio.h>
#include <string.h>
#if NFREQ != 4
#error Smartphone PPP profile requires NFREQ=4 in every translation unit
#endif
#ifdef ENAQZS
#error Smartphone PPP profile uses the PC satellite layout without ENAQZS
#endif

#define PROFILE_OPTIONS \
    "-GAP_RESION=120 -IONCONS=1.5 -IONCONSINT=1 -VMF3SIG=0.15 " \
    "-VMF3ZWDSIG=0.30 -VMF3ZWDINT=300 -DOPPSM=0.90 -DOPPWARM=0 " \
    "-PREPROC=1 -DOPPSLIP=0.50 -CODEJUMP=30 -MWTHRES=5 " \
    "-BDSCODEVAR=1 -BDSCODEWARM=120 -WGTELCN=0 -PPPDIAG=1 " \
    "-PPPQUAR=3,120 -GALE5BPHASE=0"
typedef char profile_options_fit[
    sizeof(PROFILE_OPTIONS) <= sizeof(((prcopt_t *)0)->pppopt) ? 1 : -1];

ppp_policy_t smartphone_ppp_policy(const prcopt_t *opt)
{
    int legacy = opt && opt->ppp_baseline == PPP_BASELINE_B_LEGACY;
    ppp_policy_t policy = {0};
    const char *gap;
    double seconds;
    policy.legacy_weighting = policy.quality_learning = legacy;
    policy.smoothing = policy.atmosphere_constraints = legacy;
    policy.empirical_guards = policy.startup_qc = legacy;
    policy.corrected_lifecycle = !legacy ||
        opt->ppp_lifecycle == PPP_LIFECYCLE_CORRECTED;
    policy.arc_gap_seconds=PPP_ARC_GAP_SECONDS_DEFAULT;
    if(opt && (gap=strstr(opt->pppopt,"-ARCGAP=")) &&
        sscanf(gap+8,"%lf",&seconds)==1 && isfinite(seconds) && seconds>0.0)
        policy.arc_gap_seconds=seconds;
    return policy;
}

int smartphone_ppp_select(prcopt_t *opt, const char *baseline,
    const char *lifecycle, char *error, size_t capacity)
{
    const char *problem = NULL;
    if (baseline && *baseline) {
        if (!strcmp(baseline,"A") || !strcmp(baseline,"CLEAN_BASELINE"))
            opt->ppp_baseline = PPP_BASELINE_A_CLEAN;
        else if (!strcmp(baseline,"B") || !strcmp(baseline,"LEGACY_BASELINE"))
            opt->ppp_baseline = PPP_BASELINE_B_LEGACY;
        else if (!strcmp(baseline,"C") || !strcmp(baseline,"HUBER_ROBUST"))
            opt->ppp_baseline = MODE_C_NEW_ROBUST;
        else problem = "baseline must be A, B or C; D is reserved and unavailable";
    }
    if (!problem && lifecycle && *lifecycle) {
        if (!strcmp(lifecycle,"LEGACY")) opt->ppp_lifecycle=PPP_LIFECYCLE_LEGACY;
        else if (!strcmp(lifecycle,"CORRECTED")) opt->ppp_lifecycle=PPP_LIFECYCLE_CORRECTED;
        else problem = "lifecycle must be LEGACY or CORRECTED";
        if (!problem && opt->ppp_baseline!=PPP_BASELINE_B_LEGACY &&
            opt->ppp_lifecycle==PPP_LIFECYCLE_LEGACY)
            problem = "A/C require CORRECTED lifecycle";
    }
    if (error && capacity) snprintf(error,capacity,"%s",problem?problem:"");
    return !problem;
}

void smartphone_ppp_configure(prcopt_t *opt, solopt_t *sol)
{
    *opt = prcopt_default;
    opt->mode = PMODE_PPP_STATIC;
    opt->dynamics = 0;
    opt->navsys = SYS_GPS | SYS_GAL | SYS_CMP;
    opt->nf = 4;
    opt->sateph = EPHOPT_PREC;
    opt->ionoopt = IONOOPT_EST;
    opt->tropopt = TROPOPT_EST;
    opt->err[1] = 0.008; opt->err[2] = 0.012;
    opt->eratio[0] = 100.0; opt->eratio[1] = 70.0;
    opt->eratio[2] = 60.0; opt->eratio[3] = 100.0;
    opt->modear = ARMODE_OFF;
    opt->thresslip = 0.20;
    opt->elmin = 15.0 * D2R;
    opt->prn[0] = 1e-4; opt->prn[1] = 1e-3; opt->prn[2] = 1e-4;
    opt->maxout = 30;
    opt->tidecorr = 1;
    opt->posopt[0] = 1; opt->posopt[1] = 0;
    opt->posopt[2] = 1; opt->posopt[3] = 1;
    opt->snrmask.ena[0] = 0;
    memcpy(opt->pppopt, PROFILE_OPTIONS, sizeof(PROFILE_OPTIONS));
    if (sol) {
        *sol = solopt_default;
        sol->sstat = 2;
        sol->maxsolstd = 0.0;
    }
}

int smartphone_ppp_validate(const prcopt_t *opt, char *error, size_t capacity)
{
    const char *problem = NULL;
    int supported = SYS_GPS;
    if (NSATGLO) supported |= SYS_GLO;
    if (NSATGAL) supported |= SYS_GAL;
    if (NSATCMP) supported |= SYS_CMP;
    if (NSATQZS) supported |= SYS_QZS;
    if (!opt) problem = "null processing options";
    else if (opt->ppp_baseline < 0 || opt->ppp_baseline > MODE_C_NEW_ROBUST)
        problem = "D algorithm is not implemented";
    else if (opt->ppp_lifecycle < 0 || opt->ppp_lifecycle > PPP_LIFECYCLE_CORRECTED)
        problem = "invalid PPP lifecycle";
    else if (opt->nf < 1 || opt->nf > NFREQ)
        problem = "processing frequency count exceeds compiled observation layout";
    else if (!opt->navsys || (opt->navsys & ~supported))
        problem = "requested satellite system is not compiled";
    else if (!memchr(opt->pppopt, 0, sizeof(opt->pppopt)))
        problem = "PPP option string is not terminated";
    else if (!numeric_finite(opt->err,8) || !numeric_finite(opt->eratio,NFREQ) ||
        !numeric_finite(opt->prn,6) || !isfinite(opt->thresslip) || !isfinite(opt->elmin))
        problem = "nonfinite PPP stochastic model parameter";
    if (!problem) {
        const char *gap=strstr(opt->pppopt,"-ARCGAP=");double seconds;
        if(gap && (sscanf(gap+8,"%lf",&seconds)!=1 || !isfinite(seconds) || seconds<=0))
            problem="ARCGAP must be a positive finite interval in seconds";
    }
    if (error && capacity) snprintf(error, capacity, "%s", problem ? problem : "");
    return problem == NULL;
}

unsigned int smartphone_ppp_describe(const prcopt_t *opt, char *out, size_t capacity)
{
    /* Canonical text avoids platform-dependent struct padding in signatures. */
    char text[2048];
    unsigned int hash = 2166136261u;
    const unsigned char *p;
    snprintf(text, sizeof(text),
        "baseline=%s lifecycle=%s arc_gap_sec=%.9g eta=1 profile=%s NFREQ=%d MAXSAT=%d NSATGLO=%d NSATQZS=%d "
        "mode=%d soltype=%d nf=%d navsys=%d dynamics=%d sateph=%d "
        "iono=%d trop=%d ar=%d elmin=%.9g maxout=%d tide=%d "
        "err=%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g "
        "eratio=%.9g,%.9g,%.9g,%.9g,%.9g,%.9g "
        "prn=%.9g,%.9g,%.9g,%.9g,%.9g,%.9g "
        "std=%.9g,%.9g,%.9g slip=%.9g dop=%.9g "
        "maxinno=%.9g,%.9g niter=%d codesmooth=%d "
        "posopt=%d,%d,%d,%d,%d,%d snrmask=%d,%d pppopt=%s",
        opt->ppp_baseline==PPP_BASELINE_A_CLEAN?"A_CLEAN":
        opt->ppp_baseline==MODE_C_NEW_ROBUST?"C_HUBER":"B_LEGACY",
        smartphone_ppp_policy(opt).corrected_lifecycle?"CORRECTED":"LEGACY",
        smartphone_ppp_policy(opt).arc_gap_seconds,
        SMARTPHONE_PPP_PROFILE, NFREQ, MAXSAT, NSATGLO, NSATQZS,
        opt->mode, opt->soltype, opt->nf, opt->navsys, opt->dynamics,
        opt->sateph, opt->ionoopt, opt->tropopt, opt->modear,
        opt->elmin, opt->maxout, opt->tidecorr,
        opt->err[0], opt->err[1], opt->err[2], opt->err[3],
        opt->err[4], opt->err[5], opt->err[6], opt->err[7],
        opt->eratio[0], opt->eratio[1], opt->eratio[2],
        opt->eratio[3], opt->eratio[4], opt->eratio[5],
        opt->prn[0], opt->prn[1], opt->prn[2],
        opt->prn[3], opt->prn[4], opt->prn[5],
        opt->std[0], opt->std[1], opt->std[2], opt->thresslip, opt->thresdop,
        opt->maxinno[0], opt->maxinno[1], opt->niter, opt->codesmooth,
        opt->posopt[0], opt->posopt[1], opt->posopt[2],
        opt->posopt[3], opt->posopt[4], opt->posopt[5],
        opt->snrmask.ena[0], opt->snrmask.ena[1], opt->pppopt);
    if(opt->ppp_baseline==MODE_C_NEW_ROBUST) {
        size_t len=strlen(text);
        snprintf(text+len,sizeof(text)-len," huber_k=%.9g",PPP_HUBER_K_DEFAULT);
    }
    for (p = (const unsigned char *)text; *p; ++p) hash = (hash ^ *p) * 16777619u;
    if (out && capacity) snprintf(out, capacity, "PPP_CONFIG,signature=%08x,%s", hash, text);
    return hash;
}

void smartphone_ppp_log(const char *entry, const prcopt_t *opt)
{
    char description[2048];
    ppp_policy_t p=smartphone_ppp_policy(opt);
    smartphone_ppp_describe(opt, description, sizeof(description));
    fprintf(stderr, "%s,entry=%s\n", description, entry);
    trace(2, "%s,entry=%s\n", description, entry);
    fprintf(stderr,"PPP_POLICY,legacy_weighting=%d,quality_learning=%d,smoothing=%d,atmosphere_constraints=%d,empirical_guards=%d,startup_qc=%d,corrected_lifecycle=%d,eta=1\n",
        p.legacy_weighting,p.quality_learning,p.smoothing,p.atmosphere_constraints,
        p.empirical_guards,p.startup_qc,p.corrected_lifecycle);
}
