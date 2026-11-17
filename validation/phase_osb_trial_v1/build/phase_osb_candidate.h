#ifndef PHASE_OSB_CANDIDATE_H
#define PHASE_OSB_CANDIDATE_H
/* Private, single-process floating-PPP trial. No nav_t/rtk_t ABI changes.
 * Units: product ns -> m; L and ambiguity are both m inside ppp.c.
 * OFF does not load products or change arithmetic. Missing/expired corrections
 * are explicitly unavailable, never extrapolated; the original float carrier
 * remains usable. Only a corrected/raw datum transition translates active N.
 * Ordinary contiguous OSB updates are applied without resetting/translating N.
 */
#include <errno.h>
typedef struct {
    gtime_t start,end;
    double bias;
    int sat,code,next;
} posb_record_t;
typedef struct {
    int seen,status;
    double applied;
    gtime_t start,end;
} posb_history_t;
static struct {
    int configured,enabled,failed,n,capacity,invalid;
    int head[MAXSAT][MAXCODE+1];
    posb_record_t *record;
    posb_history_t history[MAXSAT][MAXCODE+1];
    FILE *epochs,*events;
} posb_trial;

static int posb_time(const char *s,gtime_t *out)
{
    int year,doy;double seconds,ep[6]={0};char tail;
    if(sscanf(s,"%d:%d:%lf%c",&year,&doy,&seconds,&tail)!=3 ||
       year<1980 || year>2199 || doy<1 || doy>366 ||
       !isfinite(seconds) || seconds<0. || seconds>86400.)return 0;
    ep[0]=year;ep[1]=ep[2]=1;
    *out=timeadd(epoch2time(ep),(doy-1)*86400.+seconds);return 1;
}

static int posb_add(int sat,int code,gtime_t start,gtime_t end,double bias)
{
    posb_record_t *p;
    if(sat<1 || sat>MAXSAT || code<1 || code>MAXCODE ||
       !isfinite(bias) || timediff(end,start)<=0.)return 0;
    if(posb_trial.n==posb_trial.capacity) {
        int cap=posb_trial.capacity?posb_trial.capacity*2:1024;
        p=(posb_record_t *)realloc(posb_trial.record,(size_t)cap*sizeof(*p));
        if(!p)return 0;posb_trial.record=p;posb_trial.capacity=cap;
    }
    p=posb_trial.record+posb_trial.n;
    p->sat=sat;p->code=code;p->start=start;p->end=end;p->bias=bias;
    p->next=posb_trial.head[sat-1][code];
    posb_trial.head[sat-1][code]=++posb_trial.n;return 1;
}

static int posb_read(const char *path)
{
    FILE *fp=fopen(path,"r");char line[2048],*tokens[40],*p,*end;
    if(!fp)return 0;
    while(fgets(line,sizeof(line),fp)) {
        int count=0,i,sat,code=0,have=0;double value=0.,scale=0.;gtime_t a={0},b={0};
        if(strstr(line,"TIME_SYSTEM")) {
            char *q=strstr(line,"TIME_SYSTEM")+11;
            while(*q==' ' || *q=='\t')q++;
            if(*q && *q!='G'){fclose(fp);return 0;}
        }
        for(p=strtok(line," \t\r\n");p && count<40;p=strtok(NULL," \t\r\n"))tokens[count++]=p;
        if(count<3 || strcmp(tokens[0],"OSB"))continue;
        sat=satid2no(tokens[2]);if(!sat)continue; /* exact PRN, not SVN */
        for(i=3;i<count;i++)if(strlen(tokens[i])==3 && tokens[i][0]=='L' &&
            tokens[i][1]>='0' && tokens[i][1]<='9') {code=obs2code(tokens[i]+1);break;}
        if(!code)continue;
        for(i=3;i<count;i++) {
            gtime_t t;
            if(posb_time(tokens[i],&t)) {if(!have)a=t;else if(have==1)b=t;have++;}
            if(i+1<count && (!strcmp(tokens[i],"ns") || !strcmp(tokens[i],"NS") || !strcmp(tokens[i],"m"))) {
                scale=!strcmp(tokens[i],"m")?1.:1E-9*CLIGHT;
                errno=0;value=strtod(tokens[i+1],&end);
                if(errno || *end || !isfinite(value)){scale=0.;break;}
            }
        }
        if(have<2 || scale==0. || !posb_add(sat,code,a,b,value*scale))posb_trial.invalid++;
    }
    fclose(fp);return posb_trial.n>0;
}

/* 1: current correction, 0: signal absent, -1: known signal but outside validity.
 * Latest start wins for overlap; intervals are strictly [start,end). */
static int posb_at(gtime_t time,int sat,int code,double *bias,gtime_t *start,gtime_t *end)
{
    int index,best=0,head;
    if(bias)*bias=0.;
    if(sat<1 || sat>MAXSAT || code<1 || code>MAXCODE)return 0;
    head=posb_trial.head[sat-1][code];if(!head)return 0;
    for(index=head;index;index=posb_trial.record[index-1].next) {
        const posb_record_t *r=posb_trial.record+index-1;
        if(timediff(time,r->start)<0. || timediff(time,r->end)>=0.)continue;
        if(!best || timediff(r->start,posb_trial.record[best-1].start)>0.)best=index;
    }
    if(!best)return -1;
    if(bias)*bias=posb_trial.record[best-1].bias;
    if(start)*start=posb_trial.record[best-1].start;
    if(end)*end=posb_trial.record[best-1].end;
    return 1;
}

static int posb_configure(void)
{
    const char *mode,*path,*diag;char file[2048];
    if(posb_trial.configured)return !posb_trial.failed;
    posb_trial.configured=1;mode=getenv("RTK_PPP_PHASE_OSB");
    if(!mode || !*mode || !strcmp(mode,"OFF"))return 1;
    if(strcmp(mode,"ON")){posb_trial.failed=1;return 0;}
    posb_trial.enabled=1;path=getenv("RTK_PPP_PHASE_OSB_FILE");
    if(!path || !*path)path=getenv("RTK_PPP_BIA");
    if(!path || !*path || !posb_read(path)){posb_trial.failed=1;return 0;}
    diag=getenv("RTK_PPP_PHASE_OSB_DIAG");
    if(diag && *diag) {
        snprintf(file,sizeof(file),"%s.epochs.csv",diag);posb_trial.epochs=fopen(file,"w");
        snprintf(file,sizeof(file),"%s.events.csv",diag);posb_trial.events=fopen(file,"w");
        if(!posb_trial.epochs || !posb_trial.events){posb_trial.failed=1;return 0;}
        fputs("week,tow,phase_rows,valid,absent,outside_validity,datum_translations,record_updates\n",posb_trial.epochs);
        fputs("week,tow,sat,signal,status,applied_m,previous_applied_m,N_translation_m,start_gps,end_gps\n",posb_trial.events);
    }
    trace(2,"$PHASE_OSB_CONFIG,mode=ON,records=%d,invalid=%d,units=m,missing=RAW_FLOAT_DATUM,expired=NO_EXTRAPOLATION,ordinary_updates=NO_RESET\n",posb_trial.n,posb_trial.invalid);
    return 1;
}

static double posb_phase_correction(gtime_t time,int sat,int code)
{
    double b=0.;
    if(posb_trial.enabled)posb_at(time,sat,code,&b,NULL,NULL);
    return b;
}

static void posb_epoch(rtk_t *rtk,const obsd_t *obs,int n)
{
    int i,f,week,rows=0,valid=0,absent=0,outside=0,translated=0,updates=0;
    double tow;
    if(!posb_trial.enabled)return;
    tow=time2gpst(obs[0].time,&week);
    for(i=0;i<n;i++)for(f=0;f<rtk->opt.nf && f<NFREQ;f++) {
        int sat=obs[i].sat,code=obs[i].code[f],status,j,change;
        double applied=0.,shift=0.,before=0.;gtime_t start={0},end={0};char id[8];
        posb_history_t *h;
        if(obs[i].L[f]==0. || sat<1 || sat>MAXSAT || code<1 || code>MAXCODE)continue;
        rows++;status=posb_at(obs[i].time,sat,code,&applied,&start,&end);
        if(status>0)valid++;else if(!status)absent++;else outside++;
        h=&posb_trial.history[sat-1][code];before=h->applied;
        change=!h->seen || h->status!=status || timediff(start,h->start)!=0. || timediff(end,h->end)!=0.;
        /* N_raw = N_corrected + b. Translate only when correction availability
         * changes datum. No translation at ordinary 300-s bias value updates. */
        if(h->seen && (h->status==1)!=(status==1)) {
            j=IB(sat,f,&rtk->opt);
            if(j>=0 && j<rtk->nx && rtk->x[j]!=0. && rtk->P[j+j*rtk->nx]>0. &&
               !(rtk->ssat[sat-1].slip[f]&LLI_SLIP)) {
                shift=h->applied-applied;rtk->x[j]+=shift;
                /* Same nonzero-N sentinel convention as the existing seed. */
                if(rtk->x[j]==0.)rtk->x[j]=1E-4;
                ppp_innovation_note_current_adjustment(j);translated++;
            }
        }
        if(change) {
            updates++;satno2id(sat,id);
            trace(2,"$PHASE_OSB_RECORD,%d,%.9f,%s,L%s,status=%d,bias=%.12g,delta=%.12g,N_translation=%.12g\n",week,tow,id,code2obs(code),status,applied,applied-before,shift);
            if(posb_trial.events)fprintf(posb_trial.events,"%d,%.9f,%s,L%s,%d,%.12g,%.12g,%.12g,%.3f,%.3f\n",week,tow,id,code2obs(code),status,applied,before,shift,(double)start.time+start.sec,(double)end.time+end.sec);
        }
        h->seen=1;h->status=status;h->applied=applied;h->start=start;h->end=end;
    }
    if(posb_trial.epochs)fprintf(posb_trial.epochs,"%d,%.9f,%d,%d,%d,%d,%d,%d\n",week,tow,rows,valid,absent,outside,translated,updates);
}
#endif
