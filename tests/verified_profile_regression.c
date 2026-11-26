/* Canonical profile validation; no observation or model parameters tuned. */
#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s\n",n);}}while(0)
int main(void){
 prcopt_t opt,before;char err[256],desc[2048];
 smartphone_ppp_configure(&opt,NULL);before=opt;
 CHECK("empty profile is byte-preserving",smartphone_ppp_select_profile(&opt,NULL,err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 CHECK("DEFAULT profile is byte-preserving",smartphone_ppp_select_profile(&opt,"DEFAULT",err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 CHECK("unknown profile rejected without partial changes",!smartphone_ppp_select_profile(&opt,"BAD",err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 CHECK("B_VERIFIED accepted",smartphone_ppp_select_profile(&opt,"B_VERIFIED",err,sizeof(err)));
 CHECK("preset validates",smartphone_ppp_validate(&opt,err,sizeof(err)));
 CHECK("preset selects B",opt.ppp_baseline==PPP_BASELINE_B_LEGACY);
 CHECK("preset selects COMMON",opt.ppp_clock_mode==PPP_CLOCK_COMMON);
 CHECK("preset enables coherent repairs",smartphone_ppp_policy(&opt).verified_repairs&&smartphone_ppp_policy(&opt).corrected_lifecycle);
 CHECK("B atmosphere smoothing legacy weighting retained",smartphone_ppp_policy(&opt).atmosphere_constraints&&smartphone_ppp_policy(&opt).smoothing&&smartphone_ppp_policy(&opt).legacy_weighting);
 CHECK("R Q P0 options unchanged",!memcmp(opt.err,before.err,sizeof(opt.err))&&!memcmp(opt.prn,before.prn,sizeof(opt.prn))&&!strcmp(opt.pppopt,before.pppopt));
 before=opt;CHECK("profile selection idempotent",smartphone_ppp_select_profile(&opt,"B_VERIFIED",err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 smartphone_ppp_describe(&opt,desc,sizeof(desc));CHECK("trace identifies repairs",strstr(desc,"B_VERIFIED_v2")!=NULL&&strstr(desc,"covariance=JOSEPH_B_MASK")!=NULL);
 CHECK("verified B selects safe legacy-mask update",ppp_verified_joseph(&opt)&&ppp_safe_covariance(&opt));
 opt.ppp_physical_atmosphere=1;before=opt;CHECK("PHYSICAL mixing fails atomically",!smartphone_ppp_select_profile(&opt,"B_VERIFIED",err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 smartphone_ppp_configure(&opt,NULL);opt.ppp_iekf=1;before=opt;CHECK("IEKF mixing fails atomically",!smartphone_ppp_select_profile(&opt,"B_VERIFIED",err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 smartphone_ppp_configure(&opt,NULL);memset(opt.rnxopt[0],'x',sizeof(opt.rnxopt[0])-1);opt.rnxopt[0][sizeof(opt.rnxopt[0])-1]=0;before=opt;
 CHECK("RINEX option capacity checked before mutation",!smartphone_ppp_select_profile(&opt,"B_VERIFIED",err,sizeof(err))&&!memcmp(&opt,&before,sizeof(opt)));
 smartphone_ppp_configure(&opt,NULL);strcpy(opt.rnxopt[0],"-PPP_PHASE_ID_EXTRA");CHECK("prefix token does not disable real flag",smartphone_ppp_select_profile(&opt,"B_VERIFIED",err,sizeof(err))&&strstr(opt.rnxopt[0]," -PPP_PHASE_ID"));
 opt.rnxopt[0][0]=0;CHECK("incomplete preset rejected",!smartphone_ppp_validate(&opt,err,sizeof(err)));
 smartphone_ppp_configure(&opt,NULL);opt.ppp_baseline=PPP_BASELINE_B_LEGACY;opt.ppp_lifecycle=PPP_LIFECYCLE_CORRECTED;
 CHECK("old corrected B does not silently opt in",!smartphone_ppp_policy(&opt).verified_repairs);
 CHECK("old B covariance entry preserved",!ppp_verified_joseph(&opt)&&!ppp_safe_covariance(&opt));
 CHECK("null profile target rejected",!smartphone_ppp_select_profile(NULL,"B_VERIFIED",err,sizeof(err)));
 printf("RESULT passed=%d failed=%d\n",passed,failed);return failed!=0;
}
