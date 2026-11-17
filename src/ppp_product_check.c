#include "ppp_product_check.h"
#include "gnss_replay.h"
#include <ctype.h>
#include <math.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const nav_t *nav;
    const prcopt_t *opt;
    pcvs_t pcvs;
    FILE *report;
    int errors,warnings,epochs,observed_epochs,no_precise_epochs,nonmonotonic;
    int pairs,precise_pairs,nav_pairs,osb_ok;
    int legacy_reference;
    gtime_t begin,end,previous;
    int seen[MAXSAT],missing_precise[MAXSAT],missing_nav[MAXSAT],missing_atx[MAXSAT];
    int missing_bds_c06_pco[MAXSAT];
    int missing_reference_pco[MAXSAT],missing_signal_pco[MAXSAT][MAXCODE+1];
    int missing_signal_pcv[MAXSAT][MAXCODE+1];
    int code_seen[MAXSAT][MAXCODE+1],code_absent[MAXSAT][MAXCODE+1],code_expired[MAXSAT][MAXCODE+1];
} check_t;

static void message(check_t *c,const char *level,const char *product,
                    const char *reason,const char *format,...)
{
    char detail[2048];va_list ap;
    if(!strcmp(level,"ERROR"))c->errors++;
    if(!strcmp(level,"WARN"))c->warnings++;
    va_start(ap,format);vsnprintf(detail,sizeof(detail),format,ap);va_end(ap);
    fprintf(c->report,"PPP_CHECK,%s,%s,reason=%s%s%s\n",level,product,reason,*detail?",":"",detail);
    if(!strcmp(level,"ERROR") && c->report!=stderr)
        fprintf(stderr,"PPP_CHECK,ERROR,%s,reason=%s%s%s\n",product,reason,*detail?",":"",detail);
}

int ppp_product_window(const nav_t *nav,gtime_t begin,gtime_t end,char *reason,size_t cap)
{
    const char *error=NULL;int i;
    if(!nav || !isfinite(begin.sec) || !isfinite(end.sec) || timediff(end,begin)<0)
        error="INVALID_OBS_TIME";
    else if(!nav->peph || nav->ne<11)error="SP3_INSUFFICIENT_EPOCHS"; /* production interpolation order 10 */
    else if(!nav->pclk || nav->nc<2)error="CLK_INSUFFICIENT_EPOCHS";
    else if(timediff(begin,nav->peph[0].time)<0)error="SP3_STARTS_AFTER_OBS";
    else if(timediff(end,nav->peph[nav->ne-1].time)>0)error="SP3_ENDS_BEFORE_OBS";
    else if(timediff(begin,nav->pclk[0].time)<0)error="CLK_STARTS_AFTER_OBS";
    else if(timediff(end,nav->pclk[nav->nc-1].time)>0)error="CLK_ENDS_BEFORE_OBS";
    if(!error)for(i=0;i<nav->ne;i++)if(!isfinite(nav->peph[i].time.sec) ||
        (i && timediff(nav->peph[i].time,nav->peph[i-1].time)<=0.0)) {
        error="SP3_INVALID_TIME_GRID";break;
    }
    if(!error)for(i=0;i<nav->nc;i++)if(!isfinite(nav->pclk[i].time.sec) ||
        (i && timediff(nav->pclk[i].time,nav->pclk[i-1].time)<=0.0)) {
        error="CLK_INVALID_TIME_GRID";break;
    }
    if(reason && cap)snprintf(reason,cap,"%s",error?error:"OK");
    return error==NULL;
}

static void span(check_t *c,const char *name,gtime_t first,gtime_t last,int records,const char *scale)
{
    char a[64],b[64];time2str(first,a,3);time2str(last,b,3);
    message(c,"INFO",name,"LOADED","records=%d,time_system=%s,start=%s,end=%s",records,scale,a,b);
}

/* The current CLK and BIA readers do not convert non-GPS time systems.
 * Reject explicit unsupported declarations instead of silently shifting time. */
static void check_time_system(check_t *c,const char *path,int kind)
{
    FILE *fp=fopen(path,"r");char line[1024],system[16]="";int i;
    if(!fp)return;
    for(i=0;i<512 && fgets(line,sizeof(line),fp);i++) {
        if(kind==PC_SP3 && !strncmp(line,"%c ",3) && strlen(line)>12) {
            sscanf(line+9,"%15s",system);break;
        }
        if(kind==PC_CLK && strstr(line,"TIME SYSTEM ID")){sscanf(line,"%15s",system);break;}
        if(kind==PC_BIA && strstr(line,"TIME_SYSTEM")){sscanf(strstr(line,"TIME_SYSTEM")+11,"%15s",system);break;}
        if(strstr(line,"END OF HEADER") || !strncmp(line,"+BIAS/SOLUTION",14))break;
    }
    fclose(fp);
    if(!*system)message(c,"WARN",pc_file_keys[kind],"TIME_SYSTEM_UNDECLARED","reader_assumption=GPST");
    else if(strcmp(system,"GPS") && !(kind==PC_BIA && !strcmp(system,"G")) &&
        !(kind==PC_SP3 && !strcmp(system,"UTC")))
        message(c,"ERROR",pc_file_keys[kind],"UNSUPPORTED_TIME_SYSTEM","declared=%s",system);
    else message(c,"INFO",pc_file_keys[kind],"TIME_SYSTEM","declared=%s,normalized=GPST",system);
}

/* Product headers name the antenna calibration used to generate clocks and
 * biases.  A generic igs20.atx can be a newer release.  A differently named
 * local file is accepted only if it is byte-identical to the declared model
 * found beside it; otherwise the product set has an unproven APC datum. */
static void apc_name(const char *source,char *name,size_t capacity)
{
    const char *base=source,*p;size_t i;
    if(!capacity)return;
    for(p=source;*p;p++)if(*p=='/' || *p=='\\')base=p+1;
    for(i=0;i+1<capacity && base[i] && base[i]!=' ' && base[i]!='\t';i++)
        name[i]=(char)toupper((unsigned char)base[i]);
    name[i]=0;
}

static int clk_apc_model(const char *path,char *model,size_t capacity)
{
    FILE *fp=fopen(path,"r");char line[1024],sys[32],program[128],file[128],next[128];
    int i,conflict=0;
    if(capacity)model[0]=0;
    if(!fp)return 0;
    for(i=0;i<512 && fgets(line,sizeof(line),fp);i++) {
        if(strstr(line,"SYS / PCVS APPLIED") &&
           sscanf(line,"%31s %127s %127s",sys,program,file)==3) {
            apc_name(file,next,sizeof(next));
            if(!*model)snprintf(model,capacity,"%s",next);
            else if(strcmp(model,next))conflict=1;
        }
        if(strstr(line,"END OF HEADER"))break;
    }
    fclose(fp);return conflict;
}

static void bia_apc_model(const char *path,char *model,size_t capacity)
{
    FILE *fp=fopen(path,"r");char line[1024],file[128],*key;int i;
    if(capacity)model[0]=0;
    if(!fp)return;
    for(i=0;i<512 && fgets(line,sizeof(line),fp);i++) {
        if((key=strstr(line,"APC_MODEL")) &&
           sscanf(key+strlen("APC_MODEL"),"%127s",file)==1) {
            apc_name(file,model,capacity);break;
        }
        if(!strncmp(line,"+BIAS/SOLUTION",14))break;
    }
    fclose(fp);
}

static int same_file_bytes(const char *a,const char *b)
{
    FILE *fa=fopen(a,"rb"),*fb=fopen(b,"rb");
    unsigned char x[16384],y[16384];size_t nx,ny;int equal=1;
    if(!fa || !fb) {if(fa)fclose(fa);if(fb)fclose(fb);return 0;}
    do {
        nx=fread(x,1,sizeof(x),fa);ny=fread(y,1,sizeof(y),fb);
        if(nx!=ny || memcmp(x,y,nx)) {equal=0;break;}
    } while(nx==sizeof(x));
    if(ferror(fa) || ferror(fb))equal=0;
    fclose(fa);fclose(fb);return equal;
}

static int same_declared_antex(const char *selected,const char *model)
{
    const char *slash=strrchr(selected,'\\'),*forward=strrchr(selected,'/');
    char declared[1024];size_t prefix=0;
    if(forward && (!slash || forward>slash))slash=forward;
    if(slash)prefix=(size_t)(slash-selected)+1;
    if(prefix+strlen(model)+1>sizeof(declared))return 0;
    memcpy(declared,selected,prefix);
    strcpy(declared+prefix,model);
    return same_file_bytes(selected,declared);
}

static void check_apc_model(check_t *c,const pc_ppp_files_t *files)
{
    char clk[128],bia[128],selected[128];
    int conflict=clk_apc_model(files->path[PC_CLK],clk,sizeof(clk));
    bia_apc_model(files->path[PC_BIA],bia,sizeof(bia));
    apc_name(files->path[PC_ATX],selected,sizeof(selected));
    if(*clk)message(c,"INFO","CLK","PCVS_APPLIED","model=%s",clk);
    if(*bia)message(c,"INFO","BIA","APC_MODEL","model=%s",bia);
    if(conflict)message(c,"ERROR","CLK","PCVS_DECLARATION_CONFLICT","models_differ_by_system=1");
    if(*clk && *bia && strcmp(clk,bia))
        message(c,"ERROR","CLK_BIA","APC_MODEL_MISMATCH","clock=%s,bias=%s",clk,bia);
    if(*bia && strcmp(bia,selected)) {
        const char *model=bia;
        if(same_declared_antex(files->path[PC_ATX],model))
            message(c,"INFO","ATX","APC_MODEL_ALIAS_VERIFIED",
                "selected=%s,declared=%s,byte_identical=1",selected,model);
        else message(c,c->legacy_reference?"WARN":"ERROR","ATX","APC_MODEL_CONTENT_MISMATCH",
            "selected=%s,clock=%s,bias=%s,choose_declared_ANTEX=1,historical_replay=%d",
            selected,*clk?clk:"UNDECLARED",*bia?bia:"UNDECLARED",c->legacy_reference);
    }
    else if(!*bia && *clk && strcmp(clk,selected))
        message(c,"WARN","ATX","CLK_APC_UNVERIFIED_WITHOUT_BIA_DATUM",
            "selected=%s,clock=%s,solver=LEGACY_REFERENCE",selected,clk);
}

/* The solver now reads these reference frequencies from Bias-SINEX.  Compare
 * against the legacy RTKLIB pair for provenance, not as a model warning.
 * Galileo can list two codes on each of its two reference frequencies. */
static void check_clock_reference(check_t *c,const char *path)
{
    FILE *fp=fopen(path,"r");
    char line[1024],key[80],sys[16],code[4][16];
    int expected[2],actual[2],i,j,n,seen[10],pair_count;
    if(!fp)return;
    while(fgets(line,sizeof(line),fp)) {
        if(!strncmp(line,"+BIAS/SOLUTION",14))break;
        if(!strstr(line,"SATELLITE_CLOCK_REFERENCE_OBSERVABLES"))continue;
        for(i=0;i<4;i++)code[i][0]=0;
        n=sscanf(line,"%79s %15s %15s %15s %15s %15s",
            key,sys,code[0],code[1],code[2],code[3]);
        if(n<4 || strlen(sys)!=1)continue;
        switch(sys[0]) {
            case 'G':case 'R':case 'J':expected[0]=1;expected[1]=2;break;
            case 'E':expected[0]=1;expected[1]=7;break;
            case 'C':expected[0]=2;expected[1]=7;break;
            default:continue;
        }
        memset(seen,0,sizeof(seen));pair_count=0;
        for(i=0;i<n-2;i++) {
            int f;
            if(strlen(code[i])!=3 || code[i][0]!='C' ||
               code[i][1]<'0' || code[i][1]>'9')break;
            f=code[i][1]-'0';
            if(!seen[f]) {
                if(pair_count<2)actual[pair_count]=f;
                pair_count++;seen[f]=1;
            }
        }
        if(i!=n-2 || pair_count!=2) {
            message(c,"WARN","BIA","CLOCK_REFERENCE_UNPARSED",
                "sys=%s,product_apc_unavailable=1",sys);
            continue;
        }
        /* The order in the BIA header is not part of the frequency identity. */
        j=(actual[0]==expected[0] && actual[1]==expected[1]) ||
          (actual[1]==expected[0] && actual[0]==expected[1]);
        if(!j)message(c,"INFO","BIA_ATX","CLOCK_REFERENCE_DIFFERS_FROM_LEGACY",
            "sys=%s,product_antex=%c%02d/%c%02d,legacy_antex=%c%02d/%c%02d,solver=%s",
            sys,sys[0],actual[0],sys[0],actual[1],sys[0],expected[0],sys[0],expected[1],
            c->legacy_reference?"LEGACY_REFERENCE":"PRODUCT_REFERENCE");
        else message(c,"INFO","BIA_ATX","CLOCK_REFERENCE_MATCHES_LEGACY",
            "sys=%s,antex=%c%02d/%c%02d,solver=%s",sys,sys[0],actual[0],sys[0],actual[1],
            c->legacy_reference?"LEGACY_REFERENCE":"PRODUCT_REFERENCE");
    }
    fclose(fp);
}

static int compare_double(const void *a,const void *b)
{double x=*(const double *)a,y=*(const double *)b;return x<y?-1:x>y;}

static void grid_spacing(check_t *c,int clock)
{
    const nav_t *nav=c->nav;int n=clock?nav->nc:nav->ne,i,irregular=0;
    double *dt,typical,maxgap=0;const char *name=clock?"CLK":"SP3";
    if(n<2)return;
    dt=(double *)malloc((n-1)*sizeof(double));
    if(!dt){message(c,"ERROR",name,"NO_MEMORY","");return;}
    for(i=1;i<n;i++)dt[i-1]=clock?timediff(nav->pclk[i].time,nav->pclk[i-1].time):timediff(nav->peph[i].time,nav->peph[i-1].time);
    qsort(dt,n-1,sizeof(double),compare_double);typical=dt[(n-2)/2];maxgap=dt[n-2];
    for(i=0;i<n-1;i++)if(fabs(dt[i]-typical)>1E-6)irregular++;
    message(c,irregular?"WARN":"INFO",name,"TIME_GRID_SPACING",
        "median_interval_s=%.6f,max_interval_s=%.6f,irregular_intervals=%d,diagnostic_only=1",typical,maxgap,irregular);
    free(dt);
}

static void visit_epoch(void *context,const obsd_t *obs,int n)
{
    check_t *c=(check_t *)context;const nav_t *nav=c->nav;
    int i,f,pairs=0,ready=0;gtime_t epoch=obs[0].time;
    if(!isfinite(epoch.sec)){message(c,"ERROR","OBS","NONFINITE_TIME","");return;}
    if(!c->epochs)c->begin=c->end=epoch;
    else {
        if(timediff(epoch,c->previous)<0)c->nonmonotonic++;
        if(timediff(epoch,c->begin)<0)c->begin=epoch;
        if(timediff(epoch,c->end)>0)c->end=epoch;
    }
    c->previous=epoch;c->epochs++;
    for(i=0;i<n;i++) {
        int sat=obs[i].sat,used=0,status,svh,ref_ok=1;
        double rs[6],dt[2],var,p=0,bias;
        pcv_t *pcv;
        gtime_t tx;
        if(sat<1 || sat>MAXSAT || obs[i].rcv!=1 ||
           !(satsys(sat,NULL)&c->opt->navsys) || c->opt->exsats[sat-1]==1)continue;
        pcv=searchpcv(sat,"",obs[i].time,&c->pcvs);
        for(f=0;f<c->opt->nf && f<NFREQ;f++) {
            int code=obs[i].code[f];
            if(code<1 || code>MAXCODE || (!obs[i].P[f] && !obs[i].L[f]))continue;
            if(!isfinite(obs[i].P[f]) || !isfinite(obs[i].L[f])) {
                message(c,"ERROR","OBS","NONFINITE_MEASUREMENT","sat=%d,slot=%d",sat,f+1);continue;
            }
            used=1;
            {
                const char *signal=code2obs(code);
                int id=signal && signal[0]>='1' && signal[0]<='9' ? signal[0]-'0' : 0;
                double signal_pco[3];
                if(!id || !pcv_antex_pco(pcv,id,signal_pco))
                    c->missing_signal_pco[sat-1][code]++;
                if(c->opt->posopt[0]) {
                    double signal_pcv;
                    if(!id || !pcv_antex_nadir(pcv,id,0.0,&signal_pcv))
                        c->missing_signal_pcv[sat-1][code]++;
                }
            }
            if(obs[i].P[f]) {
                if(!p)p=obs[i].P[f];
                c->code_seen[sat-1][code]++;
                status=codeosb_at(nav,obs[i].time,sat,code,&bias);
                if(status==1 && isfinite(bias))c->osb_ok++;
                else if(status<0)c->code_expired[sat-1][code]++;
                else c->code_absent[sat-1][code]++;
            }
        }
        if(!used)continue;
        c->seen[sat-1]++;c->pairs++;pairs++;
        tx=timeadd(obs[i].time,p>0?-p/CLIGHT:0.0);
        {
            double pco[3];
            int sys=satsys(sat,NULL),ix=sys==SYS_GPS?0:sys==SYS_GLO?1:
                sys==SYS_GAL?2:sys==SYS_CMP?3:sys==SYS_QZS?4:sys==SYS_IRN?5:-1;
            if(!c->legacy_reference && ix>=0 && nav->clock_ref_status[ix]==2)ref_ok=0;
            if(!c->legacy_reference && ix>=0 && nav->clock_ref_status[ix]==1 &&
               !pcv_antex_if_pco(pcv,nav->clock_ref_antex[ix][0],
                   nav->clock_ref_antex[ix][1],
                   sat2freq(sat,nav->clock_ref_code[ix][0],nav),
                   sat2freq(sat,nav->clock_ref_code[ix][1],nav),pco)) {
                c->missing_reference_pco[sat-1]++;ref_ok=0;
            }
        }
        if(ref_ok && peph2pos(tx,sat,nav,0,rs,dt,&var) && numeric_finite(rs,6) &&
            numeric_finite(dt,2) && isfinite(var) && var>=0.0 && dt[0]!=0.0) {
            c->precise_pairs++;ready++;
        }
        else c->missing_precise[sat-1]++;
        if(satpos(tx,obs[i].time,sat,EPHOPT_BRDC,nav,rs,dt,&var,&svh) &&
            numeric_finite(rs,6) && numeric_finite(dt,2))c->nav_pairs++;
        else c->missing_nav[sat-1]++;
        {
            double pco[3];
            if(!pcv)c->missing_atx[sat-1]++;
            if(satsys(sat,NULL)==SYS_CMP &&
               !pcv_antex_pco(pcv,6,pco))c->missing_bds_c06_pco[sat-1]++;
        }
    }
    if(pairs)c->observed_epochs++;
    if(pairs && !ready)c->no_precise_epochs++;
}

static void free_check_nav(nav_t *nav)
{
    int i;if(!nav)return;
    for(i=0;i<nav->nt;i++){free(nav->tec[i].data);free(nav->tec[i].rms);}
    freenav(nav,0xFF);free(nav->erp.data);free(nav);
}

int ppp_product_check_files(const pc_ppp_files_t *files,const prcopt_t *opt,
                            int max_epochs,FILE *report)
{
    nav_t *nav=(nav_t *)calloc(1,sizeof(*nav));
    check_t *c=(check_t *)calloc(1,sizeof(*c));obs_t obs={0},unused={0};sta_t sta={0};
    gtime_t vmf0={0},vmf1={0},osb0={0},osb1={0};char why[128];
    int ok=0,i,j,k,scan=0,vmf_ok=0;FILE *fp;
    if(!report)report=stderr;
    if(!nav || !c){fprintf(report,"PPP_CHECK,ERROR,ALL,reason=NO_MEMORY\n");goto done;}
    c->nav=nav;c->opt=opt;c->report=report;
    c->legacy_reference=getenv("RTK_PPP_REFERENCE_MODEL") &&
        !strcmp(getenv("RTK_PPP_REFERENCE_MODEL"),"LEGACY");
    if(!files || !opt || opt->nf<1 || opt->nf>NFREQ) {
        message(c,"ERROR","ALL","INVALID_ARGUMENT","");goto summary;
    }
    message(c,"INFO","ALL","FILE_PRODUCTS_ONLY","SSR=OFF,filter_started=0");
    if(!ionex_time_select(nav,getenv("RTK_PPP_IONEX_TIME"))) {
        message(c,"ERROR","IONEX","INVALID_TIME_MODE",
            "RTK_PPP_IONEX_TIME_must_be_CORRECTED_or_LEGACY=1");
        goto summary;
    }
    message(c,"INFO","IONEX","TIME_MODEL","mode=%s,input=GPST,maps=UTC,query=%s",
        nav->ionex_time_mode==IONEX_TIME_LEGACY?"LEGACY":"CORRECTED",
        nav->ionex_time_mode==IONEX_TIME_LEGACY?"GPST_MIXED_WITH_UTC":"UTC");
    /* Existing PC profile requires these selections even when some constraints
     * are disabled. No silent product omission or model switch is introduced. */
    for(i=0;i<PC_OUTPUT;i++) {
        if(!memchr(files->path[i],0,PC_PPP_PATH_CAP) || !(fp=fopen(files->path[i],"rb"))) {
            message(c,"ERROR",pc_file_keys[i],"FILE_UNREADABLE","");continue;
        }
        fclose(fp);message(c,"INFO",pc_file_keys[i],"PATH","file=%s",files->path[i]);
    }
    if(c->errors)goto summary;
    check_time_system(c,files->path[PC_SP3],PC_SP3);
    check_time_system(c,files->path[PC_CLK],PC_CLK);
    check_time_system(c,files->path[PC_BIA],PC_BIA);
    if(c->errors)goto summary;
    check_apc_model(c,files);
    check_clock_reference(c,files->path[PC_BIA]);
    if(!readrnx(files->path[PC_NAV],1,"",&unused,nav,&sta) || !(nav->n+nav->ng+nav->ns))
        message(c,"ERROR","NAV","NO_EPHEMERIS_RECORDS","");
    freeobs(&unused);uniqnav(nav);
    readsp3(files->path[PC_SP3],nav,0);
    if(nav->ne<11)message(c,"ERROR","SP3","INSUFFICIENT_EPOCHS","count=%d,required=11",nav->ne);
    else span(c,"SP3",nav->peph[0].time,nav->peph[nav->ne-1].time,nav->ne,"GPST");
    if(!readrnxc(files->path[PC_CLK],nav) || nav->nc<2)
        message(c,"ERROR","CLK","INSUFFICIENT_EPOCHS","count=%d,required=2",nav->nc);
    else span(c,"CLK",nav->pclk[0].time,nav->pclk[nav->nc-1].time,nav->nc,"GPST");
    if(!readdcb(files->path[PC_BIA],nav,&sta) || nav->nosb<=0)
        message(c,"ERROR","BIA","NO_TIME_BOUNDED_CODE_OSB","count=%d",nav->nosb);
    else {
        osb0=nav->osbs[0].start;osb1=nav->osbs[0].end;
        for(i=0;i<nav->nosb;i++) {
            if(!isfinite(nav->osbs[i].bias) || timediff(nav->osbs[i].end,nav->osbs[i].start)<=0) {
                message(c,"ERROR","BIA","INVALID_OSB_RECORD","index=%d",i);break;
            }
            if(timediff(nav->osbs[i].start,osb0)<0)osb0=nav->osbs[i].start;
            if(timediff(nav->osbs[i].end,osb1)>0)osb1=nav->osbs[i].end;
        }
        span(c,"BIA",osb0,osb1,nav->nosb,"GPST_END_EXCLUSIVE");
    }
    for(i=0;i<MAX_BIAS_SYS;i++)if(nav->clock_ref_status[i]==2)
        message(c,"ERROR","BIA","CLOCK_REFERENCE_CONFLICT","system_index=%d",i);
    readtec(files->path[PC_IONEX],nav,1);
    if(nav->nt<2)message(c,"ERROR","IONEX","INSUFFICIENT_MAPS","count=%d",nav->nt);
    else {
        span(c,"IONEX",nav->tec[0].time,nav->tec[nav->nt-1].time,nav->nt,"UTC_HEADER_READER_TIME");
        span(c,"IONEX_GPST",utc2gpst(nav->tec[0].time),utc2gpst(nav->tec[nav->nt-1].time),nav->nt,"GPST_FROM_UTC");
        message(c,"INFO","IONEX","READER_TIME_CONVENTION",
            "stored_map_epochs=UTC,query_converted_to_UTC=%d",
            nav->ionex_time_mode==IONEX_TIME_CORRECTED);
    }
    if(!readpcv(files->path[PC_ATX],&c->pcvs) || !c->pcvs.n)
        message(c,"ERROR","ATX","NO_CALIBRATION_RECORDS","");
    vmf_ok=pppvmf3inspect(files->path[PC_VMF_FIRST],files->path[PC_VMF_SECOND],files->path[PC_OROGRAPHY],&vmf0,&vmf1);
    if(!vmf_ok)message(c,"ERROR","VMF3_OR_OROGRAPHY","INVALID_GRID_OR_EPOCH_ORDER","");
    else span(c,"VMF3",vmf0,vmf1,2,"GPST_FROM_UTC");
    if(c->errors)goto summary;
    /* All buffers below belong to preflight; they are never used by PPP. */
    if(files->source==PC_SOURCE_TXT)scan=gnss_replay_scan_txt(files->path[PC_OBS],max_epochs,visit_epoch,c);
    else if(readrnx(files->path[PC_OBS],1,opt->rnxopt[0],&obs,nav,&sta) && obs.n) {
        sortobs(&obs);
        for(i=0;i<obs.n;i=j) {
            for(j=i+1;j<obs.n && fabs(timediff(obs.data[j].time,obs.data[i].time))<=DTTOL;j++);
            visit_epoch(c,obs.data+i,j-i);
        }
        scan=c->epochs;
    }
    if(scan<=0 || !c->epochs) {message(c,"ERROR","OBS","NO_VALID_EPOCHS","");goto summary;}
    span(c,"OBS",c->begin,c->end,c->epochs,"GPST");
    if(!ppp_product_window(nav,c->begin,c->end,why,sizeof(why)))
        message(c,"ERROR","SP3_CLK",why,"select_files_covering_OBS_GPST_not_local_time=1");
    else {grid_spacing(c,0);grid_spacing(c,1);}
    if(timediff(c->begin,osb0)<0 || timediff(c->end,osb1)>=0)
        message(c,"ERROR","BIA","OBS_OUTSIDE_OSB_SPAN","end_is_exclusive=1");
    if(vmf_ok && (timediff(c->begin,vmf0)<0 || timediff(c->end,vmf1)>0))
        message(c,"WARN","VMF3","PARTIAL_TIME_COVERAGE","existing_model_fallback_unchanged=1");
    if(nav->nt>=2 && (!ionex_in_range(c->begin,nav) || !ionex_in_range(c->end,nav)))
        message(c,"WARN","IONEX","PARTIAL_MODEL_TIME_COVERAGE",
            "mode=%s,native_time=UTC,model_and_preflight_use_same_domain=1",
            nav->ionex_time_mode==IONEX_TIME_LEGACY?"LEGACY":"CORRECTED");
    if(c->nonmonotonic)message(c,"ERROR","OBS","NONMONOTONIC_TIME","count=%d",c->nonmonotonic);
    if(!c->pairs)message(c,"ERROR","OBS","NO_ENABLED_OBSERVATIONS","");
    else if(!c->precise_pairs || !c->nav_pairs)
        message(c,"ERROR","PRODUCTS","NO_OBSERVED_SATELLITE_SUPPORT","precise_pairs=%d,nav_pairs=%d",c->precise_pairs,c->nav_pairs);
    if(c->no_precise_epochs)message(c,"WARN","SP3_CLK","EPOCHS_WITHOUT_PRECISE_SUPPORT","epochs=%d",c->no_precise_epochs);
    for(i=0;i<MAXSAT;i++)if(c->seen[i]) {
        char sid[8];satno2id(i+1,sid);
        message(c,(c->missing_precise[i]||c->missing_nav[i]||c->missing_atx[i])?"WARN":"INFO","SATELLITE","AVAILABILITY",
            "sat=%s,epochs=%d,orbit_clock_unavailable=%d,nav_unavailable=%d,atx_unavailable=%d",
            sid,c->seen[i],c->missing_precise[i],c->missing_nav[i],c->missing_atx[i]);
        if(satsys(i+1,NULL)==SYS_CMP)
            message(c,c->missing_bds_c06_pco[i]?"WARN":"INFO","ATX","BDS_C06_PCO_AVAILABILITY",
                "sat=%s,observed_epochs=%d,missing=%d,physical_id=C06",
                sid,c->seen[i],c->missing_bds_c06_pco[i]);
        if(c->missing_reference_pco[i])
            message(c,"WARN","ATX","CLOCK_REFERENCE_PCO_MISSING",
                "sat=%s,observed_epochs=%d,missing=%d,action=SKIP_SATELLITE",
                sid,c->seen[i],c->missing_reference_pco[i]);
        for(k=1;k<=MAXCODE;k++)if(c->code_seen[i][k])
            message(c,(c->code_absent[i][k]||c->code_expired[i][k])?"WARN":"INFO","SIGNAL","CODE_OSB_AVAILABILITY",
                "sat=%s,signal=C%s,samples=%d,missing=%d,expired=%d,missing_action=%s",
                sid,code2obs(k),c->code_seen[i][k],c->code_absent[i][k],c->code_expired[i][k],
                !c->legacy_reference && bias_clock_ref_status(nav,i+1)>0 ?
                    "SKIP_CODE":"LEGACY_FALLBACK_UNVERIFIED");
        for(k=1;k<=MAXCODE;k++)if(c->missing_signal_pco[i][k])
            message(c,"WARN","ATX","SIGNAL_PCO_MISSING",
                "sat=%s,signal=%s,observed_epochs=%d,missing=%d,action=%s",
                sid,code2obs(k),c->seen[i],c->missing_signal_pco[i][k],
                !c->legacy_reference && bias_clock_ref_status(nav,i+1)>0 ?
                    "SKIP_SIGNAL":"LEGACY_UNCALIBRATED");
        for(k=1;k<=MAXCODE;k++)if(c->missing_signal_pcv[i][k])
            message(c,"WARN","ATX","SIGNAL_PCV_MISSING",
                "sat=%s,signal=%s,observed_epochs=%d,missing=%d,action=%s",
                sid,code2obs(k),c->seen[i],c->missing_signal_pcv[i][k],
                !c->legacy_reference && bias_clock_ref_status(nav,i+1)>0 ?
                    "SKIP_SIGNAL":"LEGACY_SLOT_MODEL");
    }
    message(c,"INFO","LIMITS","COVERAGE_NOT_ACCURACY","antenna_reference_compatibility=NOT_PROVEN,forecast_error=NOT_ESTIMATED,publication_latency=NOT_VERIFIED");
summary:
    fprintf(report,"PPP_CHECK,SUMMARY,status=%s,errors=%d,warnings=%d,epochs=%d,filter_started=0\n",
        c->errors?"FAIL":c->warnings?"PASS_WITH_WARNINGS":"PASS",c->errors,c->warnings,c->epochs);
    ok=c->errors?0:c->warnings?2:1;
done:
    freeobs(&obs);freeobs(&unused);if(c)free(c->pcvs.pcv);free(c);free_check_nav(nav);return ok;
}
