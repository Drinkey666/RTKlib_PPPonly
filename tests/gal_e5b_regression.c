/* Raw Galileo E5b extension: datum, residual Jacobian, reset, disabled baseline. */
#include <stdio.h>
#include "ppp_estimator_under_test.c"
static int passed,failed;
#define CHECK(n,c) do{if(c){passed++;printf("PASS %s\n",n);}else{failed++;printf("FAIL %s\n",n);}}while(0)

int main(void)
{
    prcopt_t base,opt;char error[256];int profile,sat=satno(SYS_GAL,12),idx,nv;
    rtk_t *rtk=calloc(1,sizeof(*rtk));nav_t *nav=calloc(1,sizeof(*nav));obsd_t ob={0};
    double rs[6]={20200000,14000000,18000000},dts[2]={0},sv[1]={1},dr[3]={0},az[2],v[2],R[4],*H;
    int health[1]={0},exc[1]={0};unsigned char mexc[MAXOBS*2*NFREQ]={0};ppp_innovation_meta_t rows[2];
    smartphone_ppp_configure(&base,NULL);base.ppp_baseline=PPP_BASELINE_A_CLEAN;
    CHECK("default E5b opt-in disabled",!base.ppp_gal_e5b && !ppp_signal_supported(SYS_GAL,1,CODE_L7Q,&base));
    CHECK("legacy base state count retained",ND(&base)==5);
    for(profile=0;profile<2;profile++) {
        opt=base;opt.ppp_rcb_datum=profile;opt.ppp_gal_e5b=1;
        CHECK("valid raw E5b configuration",smartphone_ppp_validate(&opt,error,sizeof(error)));
        CHECK("exactly one independent extra RCB",ND(&opt)==ND_BASE(&opt)+1);
        CHECK("actual E5b code admitted",ppp_code_modelled(SYS_GAL,1,CODE_L7Q,&opt));
        CHECK("actual E5b phase admitted",ppp_signal_supported(SYS_GAL,1,CODE_L7Q,&opt));
        CHECK("wrong slot and code do not alias E5b bias",ppp_ifb_index(SYS_GAL,2,CODE_L7Q,&opt)==-1 && ppp_ifb_index(SYS_GAL,1,CODE_L7X,&opt)==-1);
        CHECK("Galileo E5a datum retained",ppp_ifb_index(SYS_GAL,2,CODE_L5Q,&opt)==(profile?-1:RCB_GAL_C5Q));
        CHECK("BDS existing state indices retained",ppp_ifb_index(SYS_CMP,2,CODE_L5P,&opt)==(profile?0:RCB_BDS_C5P));
        CHECK("E5b physical frequency",sat2freq(sat,CODE_L7Q,nav)==FREQE5b);
        opt.posopt[0]=opt.posopt[2]=0;
        rtkinit(rtk,&opt);idx=ID(ND_BASE(&opt),&opt);
        CHECK("state layout does not overlap ionosphere or ambiguity",idx>II(MAXSAT,&opt) && idx<IB(1,0,&opt) && IB(MAXSAT,opt.nf-1,&opt)==rtk->nx-1);
        CHECK("new session locks E5b layout",ppp_estimator_guard(rtk));
        rtk->opt.ppp_gal_e5b=0;
        CHECK("live E5b layout change refused",!ppp_estimator_guard(rtk));rtk->opt=opt;
        ob.sat=sat;ob.rcv=1;ob.time=gpst2time(2410,192814);ob.code[1]=CODE_L7Q;
        ob.P[1]=ob.L[1]=0;uddcb_ppp(rtk,&ob,1);
        CHECK("unobserved E5b RCB remains inactive",rtk->P[idx+idx*rtk->nx]==0);
        ob.P[1]=20000110;ob.L[1]=2E7*FREQE5b/CLIGHT;ob.SNR[1]=35000;
        uddcb_ppp(rtk,&ob,1);
        CHECK("E5b RCB uses existing initialization variance",rtk->P[idx+idx*rtk->nx]==VAR_IFB);
        rtk->sol.time=ob.time;rtk->sol.rr[0]=6378137;rtk->ssat[sat-1].azel[1]=PI/2;
        initx(rtk,6378137,1,0);initx(rtk,1,1,1);initx(rtk,1,1,2);
        initx(rtk,2,1,IT(&opt));initx(rtk,5,1,II(sat,&opt));
        initx(rtk,100,1,IB(sat,1,&opt));initx(rtk,3,VAR_IFB,idx);
        H=mat(rtk->nx,2);exc[0]=0;
        nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,NULL,rows,NULL);
        CHECK("both raw E5b rows exist with exact metadata",nv==2 && rows[0].signal==CODE_L7Q && rows[1].signal==CODE_L7Q && rows[0].frequency_slot==1 && rows[1].frequency_hz==FREQE5b && !rows[1].combined);
        CHECK("RCB affects only code Jacobian",nv==2 && H[idx]==0 && H[idx+rtk->nx]==1);
        CHECK("ambiguity affects only phase Jacobian",nv==2 && H[IB(sat,1,&opt)]==1 && H[IB(sat,1,&opt)+rtk->nx]==0);
        {
            double phase=v[0],code=v[1];rtk->x[idx]+=2;
            nv=ppp_res(0,&ob,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,v,H,R,az,NULL,NULL,rows,NULL);
            CHECK("code RCB sign and phase independence",nv==2 && v[0]==phase && fabs(v[1]-(code-2))<1E-7);
        }
        rtk->ssat[sat-1].slip[1]=LLI_SLIP;ob.P[1]=0;
        udbias_ppp(rtk,&ob,1,nav);
        CHECK("E5b confirmed slip without code invalidates old arc",rtk->x[IB(sat,1,&opt)]==0 && rtk->ssat[sat-1].ppp_arc_pending[1]);
        ob.P[1]=20000110;rtk->ssat[sat-1].slip[1]=0;ob.time=timeadd(ob.time,1);
        udbias_ppp(rtk,&ob,1,nav);
        CHECK("E5b arc reinitializes when code returns",rtk->x[IB(sat,1,&opt)]!=0 && !rtk->ssat[sat-1].ppp_arc_pending[1]);
        free(H);rtkfree(rtk);
    }
    opt=base;opt.ppp_gal_e5b=1;opt.ionoopt=IONOOPT_IFLC;
    CHECK("E5b extension cannot silently enable IF",!smartphone_ppp_validate(&opt,error,sizeof(error)));
    opt=base;opt.ppp_gal_e5b=1;opt.nf=2;
    CHECK("insufficient frequency layout rejected",!smartphone_ppp_validate(&opt,error,sizeof(error)));
    opt=base;opt.ppp_gal_e5b=1;opt.navsys=SYS_GPS;
    CHECK("Galileo required for E5b state",!smartphone_ppp_validate(&opt,error,sizeof(error)));
    free(rtk);free(nav);printf("E5B_RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
