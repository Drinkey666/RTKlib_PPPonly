#include "../src/ppp.c"
#include "../src/ppp_product_check.h"
#include <stdio.h>
static int pass,fail;
#define CHECK(name,c) do {if(c){pass++;printf("PASS %s\n",name);}else{fail++;printf("FAIL %s line=%d\n",name,__LINE__);}}while(0)
static void atx_line(FILE *fp,const char *data,const char *label)
{fprintf(fp,"%-60.60s%-20s\n",data,label);}
int main(void)
{
    static nav_t nav;char why[128];gtime_t t=gpst2time(2400,10000),a,b;
    int i;FILE *f;vmf3_grid_t *before;double *heights;int valid;
    nav.ne=11;nav.nc=2;nav.peph=calloc(11,sizeof(peph_t));nav.pclk=calloc(2,sizeof(pclk_t));
    for(i=0;i<11;i++)nav.peph[i].time=timeadd(t,i*300);
    nav.pclk[0].time=t;nav.pclk[1].time=timeadd(t,3000);
    CHECK("exact endpoint coverage accepted",ppp_product_window(&nav,t,timeadd(t,3000),why,sizeof(why)));
    CHECK("orbit starts too late",!ppp_product_window(&nav,timeadd(t,-1),t,why,sizeof(why)) && !strcmp(why,"SP3_STARTS_AFTER_OBS"));
    CHECK("orbit ends too early",!ppp_product_window(&nav,t,timeadd(t,3001),why,sizeof(why)) && !strcmp(why,"SP3_ENDS_BEFORE_OBS"));
    nav.pclk[0].time=timeadd(t,1);
    CHECK("clock starts too late",!ppp_product_window(&nav,t,timeadd(t,100),why,sizeof(why)) && !strcmp(why,"CLK_STARTS_AFTER_OBS"));
    nav.pclk[0].time=t;nav.pclk[1].time=timeadd(t,2999);
    CHECK("clock ends too early",!ppp_product_window(&nav,t,timeadd(t,3000),why,sizeof(why)) && !strcmp(why,"CLK_ENDS_BEFORE_OBS"));
    nav.pclk[1].time=timeadd(t,3000);nav.ne=10;
    CHECK("ten orbit samples insufficient for current interpolator",!ppp_product_window(&nav,t,t,why,sizeof(why)) && !strcmp(why,"SP3_INSUFFICIENT_EPOCHS"));
    nav.ne=11;nav.nc=1;
    CHECK("one clock sample rejected",!ppp_product_window(&nav,t,t,why,sizeof(why)) && !strcmp(why,"CLK_INSUFFICIENT_EPOCHS"));
    nav.nc=2;a=t;a.sec=NAN;
    CHECK("NaN observation time rejected",!ppp_product_window(&nav,a,t,why,sizeof(why)));
    CHECK("reversed observation span rejected",!ppp_product_window(&nav,timeadd(t,1),t,why,sizeof(why)));
    nav.peph[5].time=nav.peph[4].time;
    CHECK("duplicate orbit epochs rejected",!ppp_product_window(&nav,t,t,why,sizeof(why)) && !strcmp(why,"SP3_INVALID_TIME_GRID"));
    nav.peph[5].time=timeadd(t,1500);nav.pclk[1].time.sec=INFINITY;
    CHECK("nonfinite clock epoch rejected",!ppp_product_window(&nav,t,t,why,sizeof(why)) && !strcmp(why,"CLK_INVALID_TIME_GRID"));
    CHECK("missing nav rejected",!ppp_product_window(NULL,t,t,why,sizeof(why)));
    free(nav.peph);free(nav.pclk);
    for(i=0;i<2;i++) {
        int j;char name[128];sprintf(name,"validation/product_check/vmf%d",i);f=fopen(name,"w");
        fprintf(f,"! Epoch: 2026 03 17 %02d 00 0.0\n",i*6);
        for(j=0;j<VMF3_NGRID;j++)fprintf(f,"0 0 .001 .0005 2.3 .15\n");fclose(f);
    }
    f=fopen("validation/product_check/orog","w");for(i=0;i<VMF3_NGRID;i++)fprintf(f,"0\n");fclose(f);
    CHECK("load control VMF cache",pppvmf3load("validation/product_check/vmf0","validation/product_check/vmf1","validation/product_check/orog"));
    before=malloc(sizeof(vmf3_grid));heights=malloc(sizeof(vmf3_orog));
    memcpy(before,vmf3_grid,sizeof(vmf3_grid));memcpy(heights,vmf3_orog,sizeof(vmf3_orog));valid=vmf3_orog_valid;
    CHECK("inspect valid VMF files",pppvmf3inspect("validation/product_check/vmf0","validation/product_check/vmf1","validation/product_check/orog",&a,&b));
    {double ep[]={2026,3,17,0,0,0};CHECK("VMF UTC to GPST uses leap second conversion",timediff(a,epoch2time(ep))==18 && timediff(b,a)==21600);}
    CHECK("reversed VMF grids rejected",!pppvmf3inspect("validation/product_check/vmf1","validation/product_check/vmf0","validation/product_check/orog",&a,&b));
    CHECK("missing VMF file rejected",!pppvmf3inspect("validation/product_check/missing","validation/product_check/vmf1","validation/product_check/orog",&a,&b));
    CHECK("inspect success and failures do not mutate atmospheric cache",!memcmp(before,vmf3_grid,sizeof(vmf3_grid)) && !memcmp(heights,vmf3_orog,sizeof(vmf3_orog)) && valid==vmf3_orog_valid);
    free(before);free(heights);
    {   /* Physical C06 PCO must survive even though legacy observation slots
         * have no B3I slot.  The IF helper does not alter legacy off[]/var[]. */
        pcvs_t pcvs={0};pcv_t *satpcv;double pco[3]={91,92,93},pcv_value=91.0;
        double c1=SQR(FREQ1_CMP)/(SQR(FREQ1_CMP)-SQR(FREQ3_CMP));
        double c2=1.0-c1;char type[60];
        f=fopen("validation/product_check/physical_frequency.atx","w");
        atx_line(f,"","START OF ANTENNA");
        snprintf(type,sizeof(type),"%-20s%-20s","BEIDOU-2G","C01");
        atx_line(f,type,"TYPE / SERIAL NO");
        atx_line(f,"   C02","START OF FREQUENCY");
        atx_line(f,"    100.00    200.00    300.00","NORTH / EAST / UP");
        atx_line(f,"   NOAZI    2.00    4.00","");
        atx_line(f,"   C02","END OF FREQUENCY");
        atx_line(f,"   C06","START OF FREQUENCY");
        atx_line(f,"    400.00    500.00    600.00","NORTH / EAST / UP");
        atx_line(f,"   NOAZI    6.00    8.00","");
        atx_line(f,"   C06","END OF FREQUENCY");
        atx_line(f,"   C07","START OF FREQUENCY");
        atx_line(f,"    700.00    800.00    900.00","NORTH / EAST / UP");
        atx_line(f,"   NOAZI    7.00    9.00","");
        atx_line(f,"   C07","END OF FREQUENCY");
        atx_line(f,"","END OF ANTENNA");fclose(f);
        CHECK("read physical-frequency fixture",readpcv("validation/product_check/physical_frequency.atx",&pcvs));
        satpcv=searchpcv(satno(SYS_CMP,1),"",t,&pcvs);
        CHECK("find BDS calibration",satpcv!=NULL);
        if(satpcv) {
            CHECK("legacy B1I/B2 slots unchanged",fabs(satpcv->off[0][0]-0.1)<1E-12 && fabs(satpcv->off[1][0]-0.7)<1E-12);
            CHECK("physical PCV parse preserves legacy slot values",
                fabs(satpcv->var[0][0]-0.002)<1E-12 &&
                fabs(satpcv->var[1][0]-0.007)<1E-12);
            CHECK("physical C06 read independently",pcv_antex_pco(satpcv,6,pco) && fabs(pco[0]-0.4)<1E-12 && fabs(pco[2]-0.6)<1E-12);
            CHECK("physical C06 PCV read independently",pcv_antex_nadir(satpcv,6,0.0,&pcv_value) && fabs(pcv_value-0.006)<1E-12);
            CHECK("missing physical PCV is invalid",!pcv_antex_nadir(satpcv,8,0.0,&pcv_value));
            {   double rs[3]={20200000.0,0.0,0.0},rr[3]={6378137.0,0.0,0.0},dant[NFREQ]={0};
                uint8_t codes[2]={CODE_L2I,CODE_L6I},available[2]={1,1};
                satantpcv(rs,rr,satpcv,codes,2,1,dant,available);
                CHECK("product PCV follows actual C02/C06 signals",available[0] && available[1] &&
                    fabs(dant[0]-0.002)<1E-12 && fabs(dant[1]-0.006)<1E-12);
            }
            CHECK("physical IF PCO coefficients",pcv_antex_if_pco(satpcv,2,6,FREQ1_CMP,FREQ3_CMP,pco) && fabs(pco[0]-(c1*0.1+c2*0.4))<1E-12);
            pco[0]=91.0;
            CHECK("missing physical frequency fails without output",!pcv_antex_if_pco(satpcv,2,8,FREQ1_CMP,FREQ3_CMP,pco) && pco[0]==91.0);
            CHECK("equal IF frequencies fail without output",!pcv_antex_if_pco(satpcv,2,6,FREQ1_CMP,FREQ1_CMP,pco) && pco[0]==91.0);
        }
        free(pcvs.pcv);
        {   pcv_t synthetic={0};double v[3]={8,9,10};int k;
            synthetic.sat=satno(SYS_CMP,1);
            synthetic.antex_pco_mask=(uint16_t)((1u<<2)|(1u<<6));
            CHECK("zero PCO gives zero IF PCO",pcv_antex_if_pco(&synthetic,2,6,FREQ1_CMP,FREQ3_CMP,v) && v[0]==0.0 && v[1]==0.0 && v[2]==0.0);
            for(k=0;k<3;k++)synthetic.antex_pco[2][k]=synthetic.antex_pco[6][k]=0.25*(k+1);
            CHECK("identical PCO survives IF combination",pcv_antex_if_pco(&synthetic,2,6,FREQ1_CMP,FREQ3_CMP,v) &&
                fabs(v[0]-0.25)<1E-12 && fabs(v[1]-0.5)<1E-12 && fabs(v[2]-0.75)<1E-12);
        }
    }
    {   /* The actual model must use the BIA clock datum, not a fixed RTKLIB
         * Galileo E1/E5b or BeiDou B1I/B2b pair. */
        int sat=satno(SYS_CMP,1),gal=2,cmp=3;
        char cwd[MAXSTRPATH],bia[MAXSTRPATH];
        double rs[3]={20200000.0,0.0,0.0},rr[3]={6378137.0,0.0,0.0};
        double off[3],delta[2],c1,pref,raw,reference;
        uint8_t code[2],valid[2];pcv_t *p=&nav.pcvs[sat-1];
        f=fopen("validation/product_check/clock_reference.BIA","w");
        fprintf(f," SATELLITE_CLOCK_REFERENCE_OBSERVABLES   E  C1X  C5X  C1C  C5Q\n");
        fprintf(f," SATELLITE_CLOCK_REFERENCE_OBSERVABLES   C  C2I  C6I\n");
        fclose(f);
        GetCurrentDirectoryA(sizeof(cwd),cwd);
        snprintf(bia,sizeof(bia),"%s\\validation\\product_check\\clock_reference.BIA",cwd);
        readdcb(bia,&nav,NULL);
        CHECK("Galileo reference parses two physical frequencies despite four codes",
            nav.clock_ref_status[gal]==1 && nav.clock_ref_antex[gal][0]==1 &&
            nav.clock_ref_antex[gal][1]==5);
        CHECK("BeiDou reference is B1I/B3I",
            nav.clock_ref_status[cmp]==1 && nav.clock_ref_antex[cmp][0]==2 &&
            nav.clock_ref_antex[cmp][1]==6);
        memset(p,0,sizeof(*p));p->sat=sat;
        p->antex_pco_mask=(uint16_t)((1u<<2)|(1u<<6)|(1u<<7));
        p->antex_pco[2][2]=1.0;p->antex_pco[6][2]=2.0;
        p->antex_pco[7][2]=3.0;
        c1=SQR(FREQ1_CMP)/(SQR(FREQ1_CMP)-SQR(FREQ3_CMP));
        pref=c1*1.0+(1.0-c1)*2.0;
        satantoff(t,rs,sat,&nav,off);
        CHECK("product-declared IF PCO moves CoM toward receiver",
            fabs(off[0]+pref)<1E-9 && fabs(off[1])<1E-9 && fabs(off[2])<1E-9);
        code[0]=obs2code("2I");code[1]=obs2code("7I");
        satantpco_delta(t,rs,rr,sat,&nav,code,2,delta,valid);
        CHECK("per-signal PCO signs and datum are correct",
            valid[0] && valid[1] && fabs(delta[0]-(pref-1.0))<1E-9 &&
            fabs(delta[1]-(pref-3.0))<1E-9);
        raw=rs[0]-rr[0]-3.0;reference=rs[0]+off[0]-rr[0];
        CHECK("corrected signal range equals reference APC geometry",
            fabs((raw-delta[1])-reference)<1E-6);
        p->antex_pco_mask&=(uint16_t)~(1u<<7);
        satantpco_delta(t,rs,rr,sat,&nav,code,2,delta,valid);
        CHECK("uncalibrated signal cannot silently use another PCO",
            valid[0] && !valid[1]);
        f=fopen("validation/product_check/clock_reference_conflict.BIA","w");
        fprintf(f," SATELLITE_CLOCK_REFERENCE_OBSERVABLES   C  C2I  C6I\n");
        fprintf(f," SATELLITE_CLOCK_REFERENCE_OBSERVABLES   C  C2I  C7I\n");
        fclose(f);
        snprintf(bia,sizeof(bia),"%s\\validation\\product_check\\clock_reference_conflict.BIA",cwd);
        readdcb(bia,&nav,NULL);
        CHECK("conflicting clock reference is explicit",nav.clock_ref_status[cmp]==2);
    }
    {   /* OSB sign is observation minus bias. A declared product with one
         * absent signal must not substitute an unrelated DCB or zero bias. */
        obsd_t ob={0};prcopt_t opt={0};double azel[2]={0,PI/4},zero[NFREQ]={0};
        double L[NFREQ]={0},P[NFREQ]={0},Lc,Pc;int sat=satno(SYS_GPS,1);
        ob.sat=(uint8_t)sat;ob.time=t;ob.code[0]=CODE_L1C;
        ob.P[0]=20200000.0;ob.L[0]=106000000.0;opt.nf=1;
        opt.sateph=EPHOPT_PREC;nav.nosb=1;nav.clock_ref_status[0]=1;
        strcpy(nav.bia_apc_model,"IGS20_2408.ATX");
        corr_meas(&ob,&nav,azel,&opt,zero,zero,NULL,0.0,L,P,&Lc,&Pc);
        CHECK("declared BIA absent OSB skips code but preserves phase",P[0]==0.0 && L[0]!=0.0);
        nav.legacy_product_reference=1;
        corr_meas(&ob,&nav,azel,&opt,zero,zero,NULL,0.0,L,P,&Lc,&Pc);
        CHECK("explicit legacy setting retains historical missing-OSB fallback",P[0]==ob.P[0]);
        nav.legacy_product_reference=0;
        nav.osbs=calloc(1,sizeof(codeosb_t));
        nav.osbs[0].start=timeadd(t,-1.0);nav.osbs[0].end=timeadd(t,1.0);
        nav.osbs[0].bias=5.0;nav.osb_head[sat-1][CODE_L1C]=1;
        corr_meas(&ob,&nav,azel,&opt,zero,zero,NULL,0.0,L,P,&Lc,&Pc);
        CHECK("OSB is subtracted with declared sign and metre units",fabs(P[0]-(ob.P[0]-5.0))<1E-9);
        free(nav.osbs);nav.osbs=NULL;nav.nosb=0;nav.osb_head[sat-1][CODE_L1C]=0;
        nav.clock_ref_status[0]=0;
    }
    printf("RESULT passed=%d failed=%d\n",pass,fail);return fail?1:0;
}
