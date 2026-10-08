/* Reuse Phase 1's white-box fixture, without calling its main. */
#define main phase1_main
#include "phase1_regression.c"
#undef main
int main(void)
{
    double x[3]={1,2,3},P[9]={4,1,.5,1,9,2,.5,2,16};
    double H[6]={1,2,-1,0,1,3},R[4]={2,.25,.25,3},v[2]={10,-6};
    double expected[4]={53,-17.25,-17.25,168},S[4];
    double xc[3],Pc[9],Hc[6],Rc[4],vc[2],xf[3],Pf[9],xd[3],Pd[9];
    ppp_innovation_value_t d[2];int i;
    memcpy(xc,x,sizeof x);memcpy(Pc,P,sizeof P);memcpy(Hc,H,sizeof H);
    memcpy(Rc,R,sizeof R);memcpy(vc,v,sizeof v);
    CHECK("full S matrix with cross covariance and off-diagonal R",
        !ppp_innovation_diag(x,P,v,H,R,3,2,d,S) && !memcmp(S,expected,sizeof S));
    CHECK("S diagonal decomposition",d[0].pred_var==51 && d[1].pred_var==165 &&
        d[0].Sii==d[0].pred_var+d[0].obs_var && d[1].Sii==d[1].pred_var+d[1].obs_var);
    CHECK("standardization uses S not R",d[0].u==10/sqrt(53.0) && d[1].u==-6/sqrt(168.0) && d[0].u_valid && d[1].u_valid);
    CHECK("all inputs bitwise read-only",!memcmp(x,xc,sizeof x)&&!memcmp(P,Pc,sizeof P)&&
        !memcmp(H,Hc,sizeof H)&&!memcmp(R,Rc,sizeof R)&&!memcmp(v,vc,sizeof v));
    memcpy(xf,x,sizeof x);memcpy(Pf,P,sizeof P);memcpy(xd,x,sizeof x);memcpy(Pd,P,sizeof P);
    ppp_innovation_diag(xd,Pd,v,H,R,3,2,d,NULL);
    CHECK("filter bitwise same with diagnostics",!filter(xf,Pf,H,v,R,3,2)&&!filter(xd,Pd,H,v,R,3,2)&&
        !memcmp(xf,xd,sizeof xf)&&!memcmp(Pf,Pd,sizeof Pf));
    x[1]=0;ppp_innovation_diag(x,P,v,H,R,3,2,d,S);
    CHECK("zero-state sentinel flagged but full P retained",d[0].inactive_state_support && !memcmp(S,expected,sizeof S));x[1]=2;
    for(i=0;i<2;i++) {
        v[0]=i?INFINITY:NAN;ppp_innovation_diag(x,P,v,H,R,3,2,d,NULL);
        CHECK(i?"Inf innovation diagnostic invalid":"NaN innovation diagnostic invalid",!d[0].u_valid&&(d[0].invalid_reason&INNOV_BAD_V)&&d[1].u_valid);
        memcpy(vc,v,sizeof v);memcpy(xf,x,sizeof x);memcpy(Pf,P,sizeof P);
        CHECK("invalid diagnostic cannot bypass Phase 1 filter protection",filter(xf,Pf,H,v,R,3,2)==FILTER_NAN_INPUT && !memcmp(xf,x,sizeof x)&&!memcmp(Pf,P,sizeof P));
    }
    v[0]=10;P[0]=NAN;ppp_innovation_diag(x,P,v,H,R,3,2,d,NULL);
    CHECK("NaN P invalidates diagnostics",!d[0].u_valid&&!d[1].u_valid&&(d[0].invalid_reason&INNOV_BAD_P));P[0]=4;
    H[0]=INFINITY;ppp_innovation_diag(x,P,v,H,R,3,2,d,NULL);
    CHECK("Inf H invalid row isolated",!d[0].u_valid&&d[1].u_valid&&(d[0].invalid_reason&INNOV_BAD_H));H[0]=1;
    R[0]=NAN;ppp_innovation_diag(x,P,v,H,R,3,2,d,NULL);
    CHECK("NaN R invalid row",!d[0].u_valid&&(d[0].invalid_reason&INNOV_BAD_R));R[0]=2;
    {
        double xx=1,pp=1E6,hh=1,rr=1,vv=100;
        ppp_innovation_diag(&xx,&pp,&vv,&hh,&rr,1,1,d,NULL);
        CHECK("large raw startup innovation normal u",d[0].u_valid && fabs(d[0].u)<.1 && sqrt(d[0].obs_var)==1);
        pp=0;rr=0;ppp_innovation_diag(&xx,&pp,&vv,&hh,&rr,1,1,d,NULL);
        CHECK("zero S explicit invalid",!d[0].u_valid&&(d[0].invalid_reason&INNOV_NONPOSITIVE_S));
        rr=-1;ppp_innovation_diag(&xx,&pp,&vv,&hh,&rr,1,1,d,NULL);
        CHECK("negative S explicit invalid",!d[0].u_valid&&(d[0].invalid_reason&INNOV_NONPOSITIVE_S));
        rr=1E-300;vv=1E308;ppp_innovation_diag(&xx,&pp,&vv,&hh,&rr,1,1,d,NULL);
        CHECK("u overflow explicit invalid",!d[0].u_valid&&(d[0].invalid_reason&INNOV_BAD_U));
    }
    CHECK("invalid dimensions fail only diagnostic",ppp_innovation_diag(x,P,v,H,R,0,2,d,NULL)==-1);
    {
        rtk_t *rtk=(rtk_t*)calloc(1,sizeof(rtk_t));nav_t *nav=(nav_t*)calloc(1,sizeof(nav_t));obsd_t obs;
        double rs[6]={20200000,14000000,18000000},dts[2]={0},sv[1]={1},dr[3]={0},az[2],vv[2],rr[4],*hh;
        int health[1]={0},exc[1]={0},nv;unsigned char mexc[MAXOBS*2*NFREQ]={0};ppp_innovation_meta_t m[2];
        fixture(rtk,&obs,1,1);rtk->opt.posopt[0]=rtk->opt.posopt[2]=0;
        initx(rtk,6378137,1,0);initx(rtk,1,1,1);initx(rtk,1,1,2);initx(rtk,2,1,IT(&rtk->opt));hh=mat(rtk->nx,2);
        nv=ppp_res(0,&obs,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,vv,hh,rr,az,NULL,NULL,m,NULL);
        CHECK("phase/code exact source row mapping",nv==2&&m[0].row_index==0&&m[1].row_index==1&&
            m[0].measurement_class==INNOV_GNSS_PHASE&&m[1].measurement_class==INNOV_GNSS_CODE&&
            m[0].source_obs_index==0&&m[0].sat==obs.sat&&m[0].signal==CODE_L1C&&m[0].frequency_hz==FREQL1&&m[0].cn0_dbhz==35);
        mexc[0]=1;
        nv=ppp_res(0,&obs,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,vv,hh,rr,az,NULL,NULL,m,NULL);
        CHECK("editing row remaps without changing source identity",nv==1&&m[0].row_index==0&&m[0].mexc_index==1&&m[0].measurement_class==INNOV_GNSS_CODE);
        obs.L[0]=0;rtk->ssat[0].ppp_arc_pending[0]=1;initx(rtk,0,0,IB(1,0,&rtk->opt));
        nv=ppp_res(0,&obs,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,vv,hh,rr,az,NULL,NULL,m,NULL);
        CHECK("code row retains pending arc diagnostic",nv==1&&m[0].arc_status==INNOV_ARC_PENDING);
        {
            prcopt_t opt=rtk->opt;opt.nf=3;opt.ionoopt=IONOOPT_IFLC;
            rtkfree(rtk);rtkinit(rtk,&opt);obs.L[0]=2E7*FREQL1/CLIGHT;
            obs.code[1]=CODE_L2W; /* code identity exists, but no L2 data */
            obs.code[2]=CODE_L5Q;obs.L[2]=2E7*FREQL5/CLIGHT;obs.P[2]=20000120;obs.SNR[2]=35000;
            initx(rtk,6378137,1,0);initx(rtk,1,1,1);initx(rtk,1,1,2);
            initx(rtk,2,1,IT(&rtk->opt));initx(rtk,100,1,IB(1,0,&rtk->opt));
            free(hh);hh=mat(rtk->nx,2);mexc[0]=0;
            nv=ppp_res(0,&obs,1,rs,dts,sv,health,dr,exc,mexc,nav,rtk->x,rtk,vv,hh,rr,az,NULL,NULL,m,NULL);
            CHECK("IFLC maps actual L1/L5 pair despite empty L2 code slot",nv==2&&m[0].combined&&m[0].signal2==CODE_L5Q&&m[0].frequency2_hz==FREQL5);
        }
        CHECK("diagnostic open failure stays disabled",!ppp_innovation_log_open("validation/phase2/nonexistent_dir/diag.csv")&&!ppp_innovation_log_enabled());
        CHECK("diagnostic writer enable",ppp_innovation_log_open("validation/phase2/unit_diag.csv")&&ppp_innovation_log_enabled());
        rtkfree(rtk);fixture(rtk,&obs,1,1);initx(rtk,6378137,1,0);obs.P[0]=NAN;
        ppp_innovation_log_epoch(obs.time);pppos(rtk,&obs,1,nav);
        CHECK("PPP NaN still rejected with observer enabled",rtk->ppp_failure==FILTER_NAN_INPUT&&rtk->sol.stat==SOLQ_NONE&&rtk->x[0]==6378137);
        obs.P[0]=INFINITY;
        CHECK("rtkpos Inf still rejected with observer enabled",!rtkpos(rtk,&obs,1,nav)&&rtk->ppp_failure==FILTER_NAN_INPUT&&rtk->x[0]==6378137);
        ppp_innovation_log_close();
        free(hh);rtkfree(rtk);free(rtk);free(nav);
    }
    printf("RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
