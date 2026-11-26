#include "../src/rtklib.h"
#include <stdio.h>
#include <math.h>
#include <string.h>

static int passed,failed;
#define CHECK(name,condition) do { if(condition) {passed++;printf("PASS %s\n",name);} \
    else {failed++;printf("FAIL %s line=%d\n",name,__LINE__);} } while(0)

static void line(FILE *fp,const char *data,const char *label)
{fprintf(fp,"%-60s%-20s\n",data,label);}

/* Two hourly maps on a 2x2 grid. Analytic VTEC:
 * map0 = 10 + 0.1*lon_deg; map1 = 20 + 0.2*lon_deg.
 * Zenith at lat/lon=0 gives mapping=1 and no pierce-point displacement. */
static int fixture(const char *path,int year)
{
    FILE *fp=fopen(path,"w");char text[128];int kind,map,lat;
    if(!fp)return 0;
    snprintf(text,sizeof(text),"%8.1f%12sI",1.0,"");line(fp,text,"IONEX VERSION / TYPE");
    line(fp," 6371.0","BASE RADIUS");
    line(fp,"   450.0 450.0   0.0","HGT1 / HGT2 / DHGT");
    line(fp,"   -10.0  10.0  20.0","LAT1 / LAT2 / DLAT");
    line(fp,"   -30.0  30.0  60.0","LON1 / LON2 / DLON");
    line(fp,"     0","EXPONENT");line(fp,"","END OF HEADER");
    for(kind=0;kind<2;kind++)for(map=0;map<2;map++) {
        line(fp,"     1",kind?"START OF RMS MAP":"START OF TEC MAP");
        snprintf(text,sizeof(text),"%6d%6d%6d%6d%6d%6d",year,3,21,map,0,0);
        line(fp,text,"EPOCH OF CURRENT MAP");
        for(lat=-10;lat<=10;lat+=20) {
            snprintf(text,sizeof(text),"%2s%6.1f%6.1f%6.1f%6.1f%6.1f","",
                (double)lat,-30.0,30.0,60.0,450.0);
            line(fp,text,"LAT/LON1/LON2/DLON/H");
            fprintf(fp,"%5d%5d\n",kind?(map?4:2):(map?14:7),
                kind?(map?4:2):(map?26:13));
        }
        line(fp,"     1",kind?"END OF RMS MAP":"END OF TEC MAP");
    }
    fclose(fp);return 1;
}

static void release(nav_t *nav)
{
    int i;
    for(i=0;i<nav->nt;i++){free(nav->tec[i].data);free(nav->tec[i].rms);}
    free(nav->tec);nav->tec=NULL;nav->nt=nav->ntmax=0;
}

int main(void)
{
    nav_t *nav=(nav_t *)calloc(1,sizeof(*nav)),*other=(nav_t *)calloc(1,sizeof(*other));
    const double ep[]={2026,3,21,0,0,0},pos[]={0,0,100},azel[]={0,PI/2};
    const double factor=40.30E16/FREQL1/FREQL1;
    gtime_t utc=epoch2time(ep),gpst=utc2gpst(utc),query,before[2];
    double delay,var,a,expected,old_data[8];int i;
    if(!nav || !other)return 2;
    CHECK("default per-session mode is corrected",nav->ionex_time_mode==IONEX_TIME_CORRECTED);
    CHECK("explicit legacy selected",ionex_time_select(nav,"LEGACY") && nav->ionex_time_mode==IONEX_TIME_LEGACY);
    CHECK("invalid mode leaves selected mode unchanged",!ionex_time_select(nav,"bad") && nav->ionex_time_mode==IONEX_TIME_LEGACY);
    CHECK("mode belongs to nav session, not a global",other->ionex_time_mode==IONEX_TIME_CORRECTED);
    CHECK("unset selector resets previous legacy session",ionex_time_select(nav,NULL) && nav->ionex_time_mode==IONEX_TIME_CORRECTED);
    CHECK("fixture created",fixture("validation/ionex_time_fix/synthetic.INX",2026));
    readtec("validation\\ionex_time_fix\\synthetic.INX",nav,0);
    CHECK("real reader loads two TEC maps",nav->nt==2);
    if(nav->nt!=2){release(nav);free(nav);free(other);return 1;}
    CHECK("reader retains original UTC epochs",timediff(nav->tec[0].time,utc)==0.0 &&
        timediff(nav->tec[1].time,timeadd(utc,3600))==0.0);
    CHECK("RMS maps attach to matching UTC TEC epochs",nav->tec[0].rms[0]==2.0f && nav->tec[1].rms[0]==4.0f);
    for(i=0;i<2;i++){before[i]=nav->tec[i].time;memcpy(old_data+4*i,nav->tec[i].data,4*sizeof(double));}
    CHECK("2026 GPST UTC offset uses leap table",timediff(gpst,utc)==18.0);
    query=ionex_query_time(gpst,nav);
    CHECK("GPST query becomes the same UTC instant",timediff(query,utc)==0.0);
    CHECK("first exact epoch coverage agrees with solver",ionex_in_range(gpst,nav) &&
        iontec(gpst,nav,pos,azel,0,&delay,&var) && fabs(delay-10*factor)<1E-12);
    CHECK("half-hour interpolation matches hand calculation",iontec(timeadd(gpst,1800),nav,pos,azel,0,&delay,&var) &&
        fabs(delay-15*factor)<1E-12);
    CHECK("variance interpolation unchanged",fabs(var-10*factor*factor)<1E-12);
    CHECK("fractional epoch interpolation matches hand calculation",iontec(timeadd(gpst,900.25),nav,pos,azel,0,&delay,&var) &&
        fabs(delay-(10+10*900.25/3600)*factor)<1E-12);
    CHECK("sun-fixed rotation also uses UTC query",iontec(timeadd(gpst,1800),nav,pos,azel,1,&delay,&var) &&
        fabs(delay-14.625*factor)<1E-12);
    CHECK("last exact map epoch is accepted",ionex_in_range(timeadd(gpst,3600),nav) &&
        iontec(timeadd(gpst,3600),nav,pos,azel,0,&delay,&var) && fabs(delay-20*factor)<1E-12);
    CHECK("last sun-fixed epoch has zero final-map rotation",iontec(timeadd(gpst,3600),nav,pos,azel,1,&delay,&var) &&
        fabs(delay-20*factor)<1E-12);
    CHECK("before first map is rejected without extrapolation",!ionex_in_range(timeadd(gpst,-0.001),nav) &&
        !iontec(timeadd(gpst,-0.001),nav,pos,azel,0,&delay,&var));
    CHECK("after last map is rejected without extrapolation",!ionex_in_range(timeadd(gpst,3600.001),nav) &&
        !iontec(timeadd(gpst,3600.001),nav,pos,azel,0,&delay,&var));
    CHECK("UTC label misused as GPST is correctly outside coverage",!ionex_in_range(utc,nav));
    query=gpst;query.sec=NAN;delay=91;var=92;
    CHECK("NaN epoch fails without inventing a result",!ionex_in_range(query,nav) &&
        !iontec(query,nav,pos,azel,0,&delay,&var) && delay==91 && var==92);
    query.sec=INFINITY;
    CHECK("Inf epoch fails without inventing a result",!iontec(query,nav,pos,azel,0,&delay,&var) && delay==91 && var==92);
    nav->ionex_time_mode=255;
    CHECK("invalid session mode cannot silently proceed",!ionex_in_range(gpst,nav) && !iontec(gpst,nav,pos,azel,0,&delay,&var));
    CHECK("explicit legacy restores old query clock",ionex_time_select(nav,"LEGACY") &&
        timediff(ionex_query_time(gpst,nav),gpst)==0.0);
    a=1818.0/3600.0;
    CHECK("legacy earth-fixed result matches old mixed-time arithmetic",iontec(timeadd(gpst,1800),nav,pos,azel,0,&delay,&var) &&
        fabs(delay-(10+10*a)*factor)<1E-12);
    expected=(10+0.1*(360*1818.0/86400))*(1-a)+(20+0.2*(360*(-1782.0)/86400))*a;
    CHECK("legacy sun-fixed result matches old mixed-time arithmetic",iontec(timeadd(gpst,1800),nav,pos,azel,1,&delay,&var) &&
        fabs(delay-expected*factor)<1E-12);
    CHECK("legacy last endpoint rejection is reproducible",!ionex_in_range(timeadd(utc,3600),nav) &&
        !iontec(timeadd(utc,3600),nav,pos,azel,0,&delay,&var));
    ionex_time_select(nav,"CORRECTED");
    CHECK("repeated corrected queries never convert map epochs twice",iontec(timeadd(gpst,1800),nav,pos,azel,0,&delay,&var) &&
        fabs(delay-15*factor)<1E-12 && timediff(nav->tec[0].time,before[0])==0.0 &&
        timediff(nav->tec[1].time,before[1])==0.0 &&
        !memcmp(nav->tec[0].data,old_data,4*sizeof(double)) &&
        !memcmp(nav->tec[1].data,old_data+4,4*sizeof(double)));
    release(nav);
    CHECK("historical fixture created",fixture("validation/ionex_time_fix/historical.INX",2016));
    readtec("validation\\ionex_time_fix\\historical.INX",nav,0);
    if(nav->nt==2) {
        utc=nav->tec[0].time;gpst=utc2gpst(utc);
        CHECK("2016 offset is 17 seconds, not hardcoded 18",timediff(gpst,utc)==17.0);
        CHECK("historical interpolation uses leap table",iontec(timeadd(gpst,1800),nav,pos,azel,0,&delay,&var) &&
            fabs(delay-15*factor)<1E-12);
    }
    else CHECK("historical fixture loads two maps",0);
    release(nav);free(nav);free(other);
    printf("RESULT passed=%d failed=%d\n",passed,failed);return failed?1:0;
}
