/* Exercise the real SPP solver/validation with deterministic satellite geometry. */
#define satposs reliability_satposs
#include "../src/pntpos.c"
#undef satposs
#include <stdio.h>
static double test_rs[8*6];
static int passed,failed;
#define CHECK(name,c) do {if(c){passed++;printf("PASS %s\n",name);}else{failed++;printf("FAIL %s line=%d\n",name,__LINE__);}}while(0)
void reliability_satposs(gtime_t teph,const obsd_t *obs,int n,const nav_t *nav,
    int ephopt,double *rs,double *dts,double *var,int *svh)
{
    int i;for(i=0;i<n;i++) {
        memcpy(rs+6*i,test_rs+6*(obs[i].sat-1),6*sizeof(double));
        dts[2*i]=dts[2*i+1]=0;var[i]=1;svh[i]=0;
    }
}
static void setup(obsd_t *obs,sol_t *sol,int poor_geometry)
{
    const double rr[3]={6378137,0,0};double e[3],az,el;
    int i,j;memset(obs,0,8*sizeof(*obs));memset(sol,0,sizeof(*sol));
    memset(test_rs,0,sizeof(test_rs));
    sol->rr[0]=rr[0]+20;sol->rr[1]=10;sol->rr[2]=-10;
    sol->time=gpst2time(2400,99);sol->eventime=sol->time;
    sol->stat=SOLQ_PPP;sol->ns=7;
    for(i=0;i<6;i++)sol->dtr[i]=.001*(i+1),sol->qr[i]=(float)(i+1);
    for(i=0;i<8;i++) {
        az=(i*45.0)*D2R;
        el=(poor_geometry?30.0+.1*(i%3):20.0+20.0*(i%3))*D2R;
        e[0]=sin(el);e[1]=cos(el)*sin(az);e[2]=cos(el)*cos(az);
        for(j=0;j<3;j++)test_rs[6*i+j]=rr[j]+2.2E7*e[j];
        obs[i].time=gpst2time(2400,100);obs[i].sat=(uint8_t)(i+1);obs[i].rcv=1;
        obs[i].code[0]=CODE_L1C;obs[i].SNR[0]=45000;
        obs[i].P[0]=geodist(test_rs+6*i,rr,e)+60000;
    }
}
int reliability_spp_tests(void)
{
    static nav_t nav;obsd_t obs[8];sol_t sol,before,direct;
    prcopt_t opt=prcopt_default;double rs[48],dts[16],var[8],azel[16],resp[8];
    int svh[8],vsat[8],ok;char msg[128];
    opt.mode=PMODE_SINGLE;opt.navsys=SYS_GPS;opt.ionoopt=IONOOPT_OFF;
    opt.tropopt=TROPOPT_OFF;opt.posopt[4]=0;
    setup(obs,&sol,0);direct=sol;
    reliability_satposs(obs[0].time,obs,8,&nav,0,rs,dts,var,svh);
    ok=estpos(obs,8,rs,dts,var,svh,&nav,&opt,NULL,&direct,azel,vsat,resp,msg);
    CHECK("accepted control geometry",ok && fabs(direct.dtr[0]-60000/CLIGHT)<1E-10);
    ok=pntpos(obs,8,&nav,&opt,&sol,NULL,NULL,msg);
    CHECK("accepted SPP retains position/clock arithmetic",ok &&
        !memcmp(sol.rr,direct.rr,3*sizeof(double)) && !memcmp(sol.dtr,direct.dtr,sizeof(sol.dtr)) &&
        !memcmp(sol.qr,direct.qr,sizeof(sol.qr)));
    setup(obs,&sol,1);before=direct=sol;
    reliability_satposs(obs[0].time,obs,8,&nav,0,rs,dts,var,svh);
    ok=estpos(obs,8,rs,dts,var,svh,&nav,&opt,NULL,&direct,azel,vsat,resp,msg);
    CHECK("failure fixture converges but fails GDOP with changed clock",!ok &&
        strstr(msg,"gdop error") && direct.dtr[0]!=before.dtr[0]);
    ok=pntpos(obs,8,&nav,&opt,&sol,NULL,NULL,msg);before.stat=SOLQ_NONE;
    CHECK("quality failure preserves every trusted numeric solution field",!ok && !memcmp(&sol,&before,sizeof(sol)));
    opt.posopt[4]=1;sol=before;
    ok=pntpos(obs,8,&nav,&opt,&sol,NULL,NULL,msg);
    CHECK("failed RAIM retries cannot commit candidates",!ok && !memcmp(&sol,&before,sizeof(sol)));
    opt.posopt[4]=0;sol=before;
    ok=pntpos_startup(obs,8,&nav,&opt,&sol,NULL,NULL,msg);
    CHECK("failed startup FDE cannot commit candidates",!ok && !memcmp(&sol,&before,sizeof(sol)));
    ok=pntpos(obs,2,&nav,&opt,&sol,NULL,NULL,msg);
    CHECK("insufficient observations preserve trusted numeric state",!ok && !memcmp(&sol,&before,sizeof(sol)));
    ok=pntpos(obs,0,&nav,&opt,&sol,NULL,NULL,msg);
    CHECK("invalid count preserves trusted numeric state",!ok && !memcmp(&sol,&before,sizeof(sol)));
    printf("SPP_RESULT passed=%d failed=%d\n",passed,failed);return failed;
}
