/* G1-only integration: frequency, actual-code admission and metre conversion. */
#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s\n",n);}}while(0)
int main(void)
{
    prcopt_t opt,legacy;char error[256];int sat=satno(SYS_GLO,12),k;
    nav_t *nav=calloc(1,sizeof(*nav));obsd_t ob={0};
    double L[NFREQ],P[NFREQ],Lc,Pc,zero[NFREQ]={0},azel[]={0,.8};
    smartphone_ppp_configure(&opt,NULL);opt.ppp_baseline=PPP_BASELINE_A_CLEAN;
    legacy=opt;
    CHECK("default remains GEC",!(opt.navsys&SYS_GLO));
    CHECK("integrated selector",smartphone_ppp_select_estimator(&opt,"INTEGRATED",NULL,NULL,NULL,error,sizeof(error)));
    k=pppnx(&opt);opt.navsys|=SYS_GLO;
    CHECK("integrated GLO config valid",smartphone_ppp_validate(&opt,error,sizeof(error)));
    CHECK("no redundant GLO bias state",pppnx(&opt)==k && ppp_ifb_index(SYS_GLO,0,CODE_L1C,&opt)==-1);
    CHECK("G1 code admitted",ppp_code_modelled(SYS_GLO,0,CODE_L1C,&opt));
    CHECK("G1 phase admitted",ppp_signal_supported(SYS_GLO,0,CODE_L1C,&opt));
    CHECK("wrong code cannot impersonate datum",!ppp_code_modelled(SYS_GLO,0,CODE_L1P,&opt));
    CHECK("wrong slot cannot impersonate G1",!ppp_signal_supported(SYS_GLO,1,CODE_L1C,&opt));
    CHECK("G2 code and phase not silently enabled",!ppp_code_modelled(SYS_GLO,1,CODE_L2C,&opt)&&!ppp_signal_supported(SYS_GLO,1,CODE_L2C,&opt));
    CHECK("G3 and CDMA not silently enabled",!ppp_signal_supported(SYS_GLO,2,CODE_L3Q,&opt)&&!ppp_signal_supported(SYS_GLO,0,CODE_L4A,&opt));
    CHECK("legacy signal admission unchanged",ppp_signal_supported(SYS_GLO,1,CODE_L2C,&legacy));
    opt.ppp_baseline=PPP_BASELINE_B_LEGACY;
    CHECK("B integrated mixing remains refused",!smartphone_ppp_validate(&opt,error,sizeof(error)));
    CHECK("missing channel returns no frequency",sat2freq(sat,CODE_L1C,nav)==0);
    nav->glo_fcn[11]=1;
    CHECK("channel -7 G1 matches raPPPid formula",sat2freq(sat,CODE_L1C,nav)==1602E6-.5625E6*7);
    CHECK("channel -7 G2 frequency matches formula",sat2freq(sat,CODE_L2C,nav)==1246E6-.4375E6*7);
    nav->glo_fcn[11]=14;
    CHECK("channel +6 frequency",sat2freq(sat,CODE_L1C,nav)==1602E6+.5625E6*6);
    nav->glo_fcn[11]=15;
    CHECK("invalid channel not treated as GPS L1",sat2freq(sat,CODE_L1C,nav)==0);
    nav->glo_fcn[11]=8;
    CHECK("channel zero is valid",sat2freq(sat,CODE_L1C,nav)==1602E6);
    ob.sat=sat;ob.code[0]=CODE_L1C;ob.P[0]=2E7;ob.L[0]=12345;ob.SNR[0]=35000;
    corr_meas(&ob,nav,azel,&legacy,zero,zero,NULL,0,L,P,&Lc,&Pc);
    CHECK("phase cycles converted using GLO frequency",fabs(L[0]-12345*CLIGHT/1602E6)<1E-12);
    CHECK("raw G1 code not made into IF",P[0]==2E7 && Pc==0 && Lc==0);
    nav->glo_fcn[11]=0;
    corr_meas(&ob,nav,azel,&legacy,zero,zero,NULL,0,L,P,&Lc,&Pc);
    CHECK("missing channel excludes code and phase",P[0]==0 && L[0]==0);
    nav->glo_fcn[11]=8;nav->nosb=1;nav->osbs=calloc(1,sizeof(codeosb_t));
    nav->osb_head[sat-1][CODE_L1C]=1;
    ob.time=gpst2time(2410,100);nav->osbs[0].start=gpst2time(2410,90);
    nav->osbs[0].end=gpst2time(2410,110);nav->osbs[0].bias=2.5;
    opt.ppp_baseline=PPP_BASELINE_A_CLEAN;
    corr_meas(&ob,nav,azel,&opt,zero,zero,NULL,0,L,P,&Lc,&Pc);
    CHECK("GLO actual-code OSB subtracted in metres",P[0]==2E7-2.5);
    nav->osbs[0].bias=0;
    corr_meas(&ob,nav,azel,&opt,zero,zero,NULL,0,L,P,&Lc,&Pc);
    CHECK("valid zero OSB is not missing",P[0]==2E7);
    ob.time=gpst2time(2410,110);
    corr_meas(&ob,nav,azel,&opt,zero,zero,NULL,0,L,P,&Lc,&Pc);
    CHECK("expired GLO code OSB cannot silently survive",P[0]==0 && L[0]!=0);
    free(nav->osbs);free(nav);printf("GLO_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
