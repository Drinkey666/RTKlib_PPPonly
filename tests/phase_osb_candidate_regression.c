/* Phase product semantics and ambiguity-datum tests, not tuned to coordinates. */
#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s line=%d\n",n,__LINE__);}}while(0)
static void clear_posb(void)
{
    free(posb_trial.record);
    if(posb_trial.epochs)fclose(posb_trial.epochs);
    if(posb_trial.events)fclose(posb_trial.events);
    memset(&posb_trial,0,sizeof(posb_trial));
}
int main(void)
{
    gtime_t t,a,b;double value=0.,L[NFREQ],P[NFREQ],Lc,Pc,z[NFREQ]={0};
    int sat=satid2no("G01"),c=obs2code("1C"),f=0,j,info;
    nav_t *nav=(nav_t *)calloc(1,sizeof(nav_t));rtk_t *rtk=(rtk_t *)calloc(1,sizeof(rtk_t));
    prcopt_t opt=prcopt_default;solopt_t sol=solopt_default;obsd_t obs={0};
    FILE *fp;char error[256];double oldP,oldN,unbiased,original;
    CHECK("parse GPST day seconds",posb_time("2026:304:08000",&t));
    CHECK("reject malformed epoch",!posb_time("2026:304:08000oops",&a));
    CHECK("reject nonfinite epoch",!posb_time("2026:304:nan",&a));
    a=t;b=timeadd(t,300.);
    CHECK("zero OSB is a valid record",posb_add(sat,c,a,b,0.));
    CHECK("zero OSB lookup succeeds",posb_at(t,sat,c,&value,NULL,NULL)==1 && value==0.);
    CHECK("end is exclusive",posb_at(b,sat,c,&value,NULL,NULL)==-1);
    CHECK("no extrapolation before start",posb_at(timeadd(a,-.001),sat,c,&value,NULL,NULL)==-1 && value==0.);
    CHECK("absent signal is distinct",posb_at(t,sat,obs2code("5Q"),&value,NULL,NULL)==0);
    CHECK("reject reversed interval",!posb_add(sat,c,b,a,1.));
    CHECK("reject NaN correction",!posb_add(sat,c,a,b,NAN));
    CHECK("adjacent record accepted",posb_add(sat,c,b,timeadd(b,300.),.25));
    CHECK("exact boundary selects new record",posb_at(b,sat,c,&value,NULL,NULL)==1 && value==.25);
    CHECK("overlap lookup chooses latest start",posb_add(sat,c,timeadd(t,100.),timeadd(t,200.),.125) && posb_at(timeadd(t,150.),sat,c,&value,NULL,NULL)==1 && value==.125);
    clear_posb();
    fp=fopen("phase_osb_fixture.BIA","w");
    fputs(" OSB G001 G01 C1C 2026:304:08000 2026:304:08300 ns 999.0 0.0\n"
          " OSB G001 G01 L1C 2026:304:08000 2026:304:08300 ns 1.0 0.0\n"
          " OSB C061 C02 L2I 2026:304:08000 2026:304:08300 m -0.2 0.0\n"
          " OSB G001 G01 L5Q 2026:304:08000 2026:304:08300 ns nan 0.0\n",fp);fclose(fp);
    CHECK("parse only phase records",posb_read("phase_osb_fixture.BIA") && posb_trial.n==2);
    CHECK("ns converted to metres",posb_at(t,sat,c,&value,NULL,NULL)==1 && fabs(value-CLIGHT*1E-9)<1E-14);
    CHECK("exact BeiDou PRN not SVN",posb_at(t,satid2no("C02"),obs2code("2I"),&value,NULL,NULL)==1 && value==-.2);
    CHECK("nonfinite phase record unavailable",posb_at(t,sat,obs2code("5Q"),&value,NULL,NULL)==0 && posb_trial.invalid==1);
    clear_posb();
    smartphone_ppp_configure(&opt,&sol);
    info=smartphone_ppp_select_profile(&opt,"B_VERIFIED",error,sizeof(error));
    CHECK("verified profile configured",info);
    obs.time=t;obs.sat=sat;obs.code[0]=(uint8_t)c;obs.P[0]=22000000.;obs.L[0]=100000.;obs.SNR[0]=45000;
    corr_meas(&obs,nav,z,&opt,z,z,NULL,0.,L,P,&Lc,&Pc);original=L[0];
    CHECK("OFF preserves original phase",original==obs.L[0]*CLIGHT/FREQL1);
    posb_add(sat,c,t,timeadd(t,300.),.25);posb_trial.enabled=1;
    corr_meas(&obs,nav,z,&opt,z,z,NULL,0.,L,P,&Lc,&Pc);
    CHECK("phase sign and metre units",fabs((original-L[0])-.25)<1E-10);
    CHECK("phase OSB does not alter code",P[0]==obs.P[0]);
    oldN=original-P[0];unbiased=L[0]-P[0];
    CHECK("ambiguity seed uses same corrected phase",fabs(unbiased-(oldN-.25))<1E-8);
    CHECK("constant bias/N change preserves residual",fabs((original-oldN)-(L[0]-unbiased))<1E-8);
    obs.P[0]=0.;corr_meas(&obs,nav,z,&opt,z,z,NULL,0.,L,P,&Lc,&Pc);
    CHECK("phase-only input still corrected",P[0]==0. && fabs((original-L[0])-.25)<1E-10);
    obs.time=timeadd(t,301.);corr_meas(&obs,nav,z,&opt,z,z,NULL,0.,L,P,&Lc,&Pc);
    CHECK("expired correction retains raw float phase",L[0]==original);
    obs.time=t;obs.P[0]=22000000.;
    rtkinit(rtk,&opt);j=IB(sat,f,&opt);rtk->x[j]=123.;rtk->P[j+j*rtk->nx]=4.;oldP=rtk->P[j+j*rtk->nx];
    posb_epoch(rtk,&obs,1);
    CHECK("first product use does not shift preexisting fixture N",rtk->x[j]==123.);
    posb_add(sat,c,timeadd(t,300.),timeadd(t,600.),.5);obs.time=timeadd(t,300.);
    posb_epoch(rtk,&obs,1);
    CHECK("normal OSB update does not reset/translate N",rtk->x[j]==123. && rtk->P[j+j*rtk->nx]==oldP);
    obs.time=timeadd(t,601.);posb_epoch(rtk,&obs,1);
    CHECK("valid-to-raw transition translates N once",rtk->x[j]==123.5 && rtk->P[j+j*rtk->nx]==oldP);
    posb_epoch(rtk,&obs,1);
    CHECK("same epoch does not apply datum shift twice",rtk->x[j]==123.5);
    posb_add(sat,c,timeadd(t,700.),timeadd(t,1000.),.2);obs.time=timeadd(t,701.);posb_epoch(rtk,&obs,1);
    CHECK("raw-to-corrected transition sign",fabs(rtk->x[j]-123.3)<1E-12 && rtk->P[j+j*rtk->nx]==oldP);
    obs.time=timeadd(t,1001.);rtk->ssat[sat-1].slip[0]|=LLI_SLIP;oldN=rtk->x[j];posb_epoch(rtk,&obs,1);
    CHECK("confirmed slip leaves reinitialization to core",rtk->x[j]==oldN);
    rtk->ssat[sat-1].slip[0]=0;rtk->x[j]=0.;rtk->P[j+j*rtk->nx]=0.;
    posb_add(sat,c,timeadd(t,1100.),timeadd(t,1400.),.1);obs.time=timeadd(t,1101.);posb_epoch(rtk,&obs,1);
    CHECK("uninitialized N is not given artificial history",rtk->x[j]==0. && rtk->P[j+j*rtk->nx]==0.);
    rtkfree(rtk);free(rtk);free(nav);clear_posb();
    printf("PHASE_OSB_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
