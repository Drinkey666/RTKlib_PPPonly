/* Physical prior/datum integration tests; synthetic data, no surveyed truth. */
#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s line=%d\n",n,__LINE__);}}while(0)

static void maps(nav_t *nav,gtime_t utc)
{
    int i,j;
    nav->nt=nav->ntmax=2;nav->tec=calloc(2,sizeof(tec_t));
    for(i=0;i<2;i++) {
        tec_t *t=nav->tec+i;t->time=timeadd(utc,3600*i);t->rb=6371;
        t->ndata[0]=t->ndata[1]=2;t->ndata[2]=1;
        t->lats[0]=-90;t->lats[1]=90;t->lats[2]=180;
        t->lons[0]=-180;t->lons[1]=180;t->lons[2]=360;
        t->hgts[0]=t->hgts[1]=450;
        t->data=calloc(4,sizeof(double));t->rms=calloc(4,sizeof(float));
        for(j=0;j<4;j++){t->data[j]=10+10*i;t->rms[j]=2;}
    }
}
int main(void)
{
    prcopt_t base,opt,bad;char error[256],desc[2048];
    rtk_t *rtk=calloc(1,sizeof(*rtk));nav_t *nav=calloc(1,sizeof(*nav));obsd_t ob={0};
    const double ep[]={2026,3,17,0,30,0},pos[]={0,0,0};
    gtime_t time=utc2gpst(epoch2time(ep));
    double rs[]={20200000,14000000,18000000},dts[]={0,0},sv[]={1},dr[]={0,0,0};
    double az[2],v[5],R[25],*H,I,V,k=SQR(FREQL1/FREQL5);
    int health[]={0},exc[]={0},use[MAXSAT+3]={0},sat=satno(SYS_GPS,12),nv,ii,id,i;
    unsigned char mexc[MAXOBS*2*NFREQ]={0},gnss[5]={0};ppp_innovation_meta_t rows[5];
    smartphone_ppp_configure(&base,NULL);base.ppp_baseline=PPP_BASELINE_A_CLEAN;opt=base;
    CHECK("default unchanged",!base.ppp_physical_atmosphere);
    CHECK("physical selector",smartphone_ppp_select_estimator(&opt,"PHYSICAL",NULL,NULL,NULL,error,sizeof(error)));
    CHECK("physical configuration validated",smartphone_ppp_validate(&opt,error,sizeof(error)));
    CHECK("physical basis retains relative RCB",!opt.ppp_rcb_datum&&ND(&opt)==ND(&base)&&opt.ppp_wet_correction&&opt.ppp_iekf);
    CHECK("no legacy penalties or smoothing",!smartphone_ppp_policy(&opt).legacy_weighting&&!smartphone_ppp_policy(&opt).smoothing&&!smartphone_ppp_policy(&opt).atmosphere_constraints);
    CHECK("GNSS stochastic parameters unchanged",!memcmp(opt.err,base.err,sizeof(opt.err))&&!memcmp(opt.prn,base.prn,sizeof(opt.prn))&&!memcmp(opt.eratio,base.eratio,sizeof(opt.eratio)));
    smartphone_ppp_describe(&opt,desc,sizeof(desc));
    CHECK("physical policy covered in signature",strstr(desc,"atmosphere=PHYSICAL")!=NULL&&smartphone_ppp_describe(&opt,NULL,0)!=smartphone_ppp_describe(&base,NULL,0));
    bad=opt;bad.ppp_rcb_datum=1;CHECK("effective ionosphere cannot receive physical prior",!smartphone_ppp_validate(&bad,error,sizeof(error)));
    bad=opt;bad.ppp_baseline=PPP_BASELINE_B_LEGACY;CHECK("B history cannot be overwritten",!smartphone_ppp_validate(&bad,error,sizeof(error)));
    bad=opt;bad.ionoopt=IONOOPT_IFLC;CHECK("IFLC incompatible",!smartphone_ppp_validate(&bad,error,sizeof(error)));
    bad=opt;bad.nf=2;CHECK("unsupported slot layout rejected",!smartphone_ppp_validate(&bad,error,sizeof(error)));
    bad=opt;smartphone_ppp_select_estimator(&bad,"INTEGRATED",NULL,NULL,NULL,error,sizeof(error));CHECK("integrated selection restores old model",!bad.ppp_physical_atmosphere&&bad.ppp_rcb_datum);
    CHECK("reference code fixed only once",ppp_ifb_index(SYS_GPS,0,CODE_L1C,&opt)==-1&&ppp_ifb_index(SYS_GPS,2,CODE_L5Q,&opt)==RCB_GPS_C5Q);
    CHECK("actual code mismatch not a reference",!ppp_code_modelled(SYS_GPS,0,CODE_L1X,&opt));
    CHECK("GLO model explicitly single G1",ppp_signal_supported(SYS_GLO,0,CODE_L1C,&opt)&&!ppp_signal_supported(SYS_GLO,1,CODE_L2C,&opt));
    {
        double A[]={1,1,1,1,0, 1,k,-1,-k,1, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0};
        CHECK("physical GIM anchors clock ionosphere RCB gauge",matinv(A,5)==0);
        double B[]={1,1,1,1,0, 1,k,-1,-k,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0};
        CHECK("dropping physical datum leaves null direction",matinv(B,5)!=0);
    }
    maps(nav,timeadd(gpst2utc(time),-1800));
    CHECK("map cadence from product not legacy 1s",physical_iono_interval(nav)==3600);
    CHECK("same epoch consumes no extra information",atmosphere_information_ppp(time,time,3600)==0);
    CHECK("1Hz information fraction",fabs(atmosphere_information_ppp(timeadd(time,1),time,3600)-1.0/3600)<1E-15);
    CHECK("long gap capped to one product",atmosphere_information_ppp(timeadd(time,7200),time,3600)==1);
    {int nt=nav->nt;nav->nt=1;CHECK("no cadence no repeated prior",physical_iono_interval(nav)==0);nav->nt=nt;}
    opt.posopt[0]=opt.posopt[2]=0;rtkinit(rtk,&opt);rtk->sol.time=time;rtk->tt=1;
    pos2ecef(pos,rtk->sol.rr);matcpy(rtk->x,rtk->sol.rr,3,1);
    CHECK("session locks physical basis",ppp_estimator_guard(rtk));rtk->opt.ppp_physical_atmosphere=0;
    CHECK("live basis switch refused",!ppp_estimator_guard(rtk));rtk->opt=opt;
    initx(rtk,6378137,1,0);initx(rtk,1,1,1);initx(rtk,1,1,2);initx(rtk,2,1,IT(&opt));
    ob.sat=sat;ob.time=time;ob.code[0]=CODE_L1C;ob.code[2]=CODE_L5Q;
    ob.P[0]=ob.P[2]=2E7;ob.L[0]=2E7*FREQL1/CLIGHT;ob.L[2]=2E7*FREQL5/CLIGHT;
    ob.SNR[0]=ob.SNR[2]=35000;
    {double pp[3],e[3];ecef2pos(rtk->x,pp);geodist(rs,rtk->x,e);satazel(pp,e,rtk->ssat[sat-1].azel);}
    ii=II(sat,&opt);id=ID(RCB_GPS_C5Q,&opt);H=mat(rtk->nx,5);
    uddcb_ppp(rtk,&ob,1);
    CHECK("observed RCB is valid exact zero",rtk->x[id]==0&&rtk->P[id+id*rtk->nx]==VAR_IFB);
    CHECK("unobserved constellation RCB inactive",rtk->P[ID(RCB_GAL_C5Q,&opt)*(rtk->nx+1)]==0);
    udiono_ppp(rtk,&ob,1,nav);
    CHECK("physical ionosphere initializes from GIM",rtk->P[ii+ii*rtk->nx]>0&&timediff(rtk->ssat[sat-1].ppp_ion_prior_time,time)==0);
    initx(rtk,100,1,IB(sat,0,&opt));initx(rtk,100,1,IB(sat,2,&opt));
    nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,use,rows,gnss);
    CHECK("GIM initialization never doubled in same epoch",nv==4&&use[0]==0);
    ob.time=timeadd(time,1);initx(rtk,25,1,ii);exc[0]=0;
    nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,use,rows,gnss);
    CHECK("one physical GIM row per satellite",nv==5&&use[0]==1&&use[3+sat-1]==1&&rows[4].measurement_class==INNOV_IONO_PRIOR&&gnss[4]==0);
    CHECK("physical prior Jacobian touches only ionosphere",H[ii+4*rtk->nx]==1&&H[id+4*rtk->nx]==0&&H[IC(0,&opt)+4*rtk->nx]==0);
    {
        double pp[3];ecef2pos(rtk->x,pp);ionex_vertical_prior(ob.time,nav,pp,az,&opt,&I,&V);
        CHECK("GIM units and residual sign",fabs(v[4]-(I-25))<1E-12);
        CHECK("large prior residual does not receive legacy penalty",fabs(R[24]-V*3600)<1E-8);
        CHECK("GNSS ionosphere signs and actual frequency scale",fabs(H[ii]+H[ii+rtk->nx])<1E-12&&fabs(H[ii+2*rtk->nx]/H[ii]-k)<1E-12);
        CHECK("RCB belongs to secondary code only",H[id]==0&&H[id+rtk->nx]==0&&H[id+2*rtk->nx]==0&&H[id+3*rtk->nx]==1);
    }
    CHECK("trial does not consume GIM timestamp",timediff(rtk->ssat[sat-1].ppp_ion_prior_time,time)==0);
    /* Accepted carrier counters may be huge while valid code continues. */
    {
        ssat_t *ss=&rtk->ssat[sat-1];double prior=rtk->x[ii],cross=.0123;
        double expected=rtk->P[ii*(rtk->nx+1)];gtime_t consumed=ss->ppp_ion_prior_time;
        ob.L[0]=ob.L[2]=0;ss->azel[1]=PI/2;
        rtk->P[ii]=rtk->P[ii*rtk->nx]=cross;
        for(i=0;i<NFREQ;i++)ss->outc[i]=1000;
        udiono_ppp(rtk,&ob,1,nav);
        CHECK("continuous code cannot reset ionosphere due to phase outc",rtk->x[ii]==prior);
        CHECK("code-only continuity preserves cross covariance",rtk->P[ii]==cross&&rtk->P[ii*rtk->nx]==cross);
        CHECK("no repeated GIM seeding when phase absent",timediff(ss->ppp_ion_prior_time,consumed)==0);
        CHECK("same fixed Q rate for continuing code",fabs(rtk->P[ii*(rtk->nx+1)]-expected-SQR(opt.prn[1]))<1E-14);
        expected=rtk->P[ii*(rtk->nx+1)];udiono_ppp(rtk,&ob,1,nav);
        CHECK("same epoch adds no ionosphere process noise",rtk->P[ii*(rtk->nx+1)]==expected);
        ob.time=timeadd(time,22);udiono_ppp(rtk,&ob,1,nav);
        CHECK("short missing interval accumulates fixed Q over elapsed time",fabs(rtk->P[ii*(rtk->nx+1)]-expected-21*SQR(opt.prn[1]))<1E-14&&rtk->x[ii]==prior&&rtk->P[ii]==cross);
        ob.time=timeadd(time,200);udiono_ppp(rtk,&ob,1,nav);
        CHECK("true elapsed gap restarts physical ionosphere",rtk->x[ii]!=prior&&rtk->P[ii]==0&&timediff(ss->ppp_ion_prior_time,ob.time)==0);
        CHECK("gap uses seconds independent of 1000 carrier epochs",timediff(ss->ppp_ion_observation_time,ob.time)==0);
        ob.P[0]=ob.P[2]=0;initx(rtk,0,0,ii);udiono_ppp(rtk,&ob,1,nav);
        CHECK("no supported observation no prior initialization",rtk->P[ii*(rtk->nx+1)]==0);
        ob.P[0]=ob.P[2]=2E7;ss->azel[1]=opt.elmin/2;udiono_ppp(rtk,&ob,1,nav);
        CHECK("below cutoff cannot repeatedly seed GIM",rtk->P[ii*(rtk->nx+1)]==0);
        ss->azel[1]=PI/2;ob.code[0]=CODE_L1X;ob.code[2]=CODE_L5X;udiono_ppp(rtk,&ob,1,nav);
        CHECK("unsupported code cannot seed physical prior",rtk->P[ii*(rtk->nx+1)]==0);
        ob.code[0]=CODE_L1C;ob.code[2]=CODE_L5Q;ob.time=timeadd(time,1);
        ob.L[0]=2E7*FREQL1/CLIGHT;ob.L[2]=2E7*FREQL5/CLIGHT;
        initx(rtk,25,1,ii);ss->ppp_ion_prior_time=consumed;
    }
    rtk->ssat[sat-1].ppp_ion_prior_time=ob.time;exc[0]=0;
    nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,use,rows,gnss);
    CHECK("duplicate successful epoch no extra GIM row",nv==4);
    initx(rtk,0,1,ii);exc[0]=0;
    nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,use,rows,gnss);
    CHECK("exact zero physical ionosphere remains active",nv==4);
    nav->nt=0;ob.time=timeadd(time,2);exc[0]=0;
    nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,use,rows,gnss);
    CHECK("missing GIM preserves physical model without pseudo rows",nv==4&&use[0]==0&&rtk->x[id]==0&&rtk->P[id*(rtk->nx+1)]==VAR_IFB);nav->nt=2;
    memset(mexc,1,sizeof(mexc));exc[0]=0;
    nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,use,rows,gnss);
    CHECK("no isolated atmospheric update without GNSS support",nv==0);
    free(H);rtkfree(rtk);
    opt.ppp_iekf=0;rtkinit(rtk,&opt);ob.P[0]=NAN;pppos(rtk,&ob,1,nav);
    CHECK("physical path NaN protected",rtk->ppp_failure==FILTER_NAN_INPUT&&rtk->sol.stat==SOLQ_NONE);
    ob.P[0]=INFINITY;pppos(rtk,&ob,1,nav);CHECK("physical path Inf protected",rtk->ppp_failure==FILTER_NAN_INPUT&&rtk->sol.stat==SOLQ_NONE);
    rtkfree(rtk);
    /* Synthetic VMF forecast, so the new initialization path has an analytic oracle. */
    rtkinit(rtk,&opt);rtk->tt=1;rtk->sol.time=time;pos2ecef(pos,rtk->sol.rr);
    matcpy(rtk->x,rtk->sol.rr,3,1);vmf3_orog_valid=1;
    for(i=0;i<2;i++) {
        int j;vmf3_grid[i].valid=1;vmf3_grid[i].time=timeadd(time,3600*i);
        for(j=0;j<VMF3_NGRID;j++) {
            vmf3_grid[i].ah[j]=.001;vmf3_grid[i].aw[j]=.0005;
            vmf3_grid[i].zhd[j]=2.3;vmf3_grid[i].zwd[j]=.2+.1*i;vmf3_orog[j]=0;
        }
    }
    udtrop_ppp(rtk,time);
    CHECK("physical wet correction initializes at zero",rtk->x[IT(&opt)]==0&&fabs(rtk->ppp_trop_base-.2)<1E-14);
    CHECK("wet model uncertainty retained not deterministic",fabs(rtk->P[IT(&opt)*(rtk->nx+1)]-SQR(vmf3_init_sigma(&opt)))<1E-14);
    CHECK("wet init uses observation GPST",timediff(rtk->ppp_trop_time,time)==0);
    {
        int it=IT(&opt);double q=rtk->P[it*(rtk->nx+1)],total=ppp_total_trop(rtk,rtk->x);
        rtk->P[it]=rtk->P[it*rtk->nx]=.001;udtrop_ppp(rtk,timeadd(time,1));
        CHECK("forecast recenter retains physical total",fabs(ppp_total_trop(rtk,rtk->x)-total)<1E-12);
        CHECK("wet Q unchanged after zero initialization",fabs(rtk->P[it*(rtk->nx+1)]-q-SQR(opt.prn[2]))<1E-14);
        CHECK("wet cross covariance survives recenter",rtk->P[it]==.001&&rtk->P[it*rtk->nx]==.001);
    }
    rtkfree(rtk);vmf3_grid[0].valid=vmf3_grid[1].valid=vmf3_orog_valid=0;
    for(i=0;i<2;i++){free(nav->tec[i].data);free(nav->tec[i].rms);}free(nav->tec);free(nav);free(rtk);
    printf("PHYSICAL_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
