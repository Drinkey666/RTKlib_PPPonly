/* Parser is extracted verbatim from current gnss_replay.c by the test runner. */
#ifdef GENERATE_LEGACY
#include "../validation/observation_generation_2023_v1/before/pc/src/gnss_adapter.h"
#else
#include "../src/gnss_adapter.h"
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#define CSV_COLS 80
#define RAW_PER_EPOCH 256
#define LINE_SIZE 8192
#ifdef GENERATE_LEGACY
#include "../validation/observation_generation_2023_v1/before_parser.h"
#include "../validation/fullbias_reference_v1/production_normalizer.h"
static clock_history_t history;
#else
#include "../validation/observation_generation_2023_v1/production_parser.h"
#endif
static gnss_adapter_t ctx;
static android_meas_t rows[RAW_PER_EPOCH];
static long source_rows[RAW_PER_EPOCH];
static void emit(android_clock_t *c,int count) {
    obsd_t obs[MAXOBS];gnss_adapter_stats_t stats;int n,i,k,j,sat,slot;uint8_t code;
#ifdef GENERATE_LEGACY
    normalize_clock(&history,c);
#endif
    n=gnss_adapter_convert(&ctx,c,rows,count,obs,MAXOBS,&stats);
    for(i=0;i<n;i++)for(k=0;k<NFREQ;k++)if(obs[i].code[k]) {
        long source=0;
        for(j=0;j<count;j++)if(gnss_adapter_map_signal(rows+j,&sat,&code,&slot) &&
           sat==obs[i].sat && code==obs[i].code[k] && slot==k){source=source_rows[j];break;}
        printf("%ld,%lld,%d,%d,%s,%d,%.12f,%.12f,%.9f,%.3f,%d\n",source,
            (long long)c->time_nanos,
#ifdef GENERATE_LEGACY
            1,
#else
            ctx.clock_reference.segment,
#endif
            obs[i].sat,code2obs(obs[i].code[k]),k,
            obs[i].P[k],obs[i].L[k],(double)obs[i].D[k],obs[i].SNR[k]*SNR_UNIT,obs[i].LLI[k]);
    }
}
int main(int argc,char **argv) {
    FILE *fp;char line[LINE_SIZE];android_clock_t c,last={0},current={0};android_meas_t m;
    int n=0;long row=0;
    if(argc!=2 || !(fp=fopen(argv[1],"rb")))return 2;
    gnss_adapter_init(&ctx);
    printf("source_row,time_nanos,segment,sat,signal,slot,P,L,D,CN0,lli\n");
    while(fgets(line,sizeof(line),fp)) {
        row++;if(strncmp(line,"Raw,",4) || !parse_raw(line,&c,&m,&last))continue;
        if(n && (c.time_nanos!=current.time_nanos || c.hardware_clock_discontinuity_count!=current.hardware_clock_discontinuity_count)) {
            emit(&current,n);n=0;
        }
        if(!n || (!current.has_full_bias && c.has_full_bias))current=c;
        if(n>=RAW_PER_EPOCH){fclose(fp);return 3;}
        rows[n]=m;source_rows[n++]=row;last=c;
    }
    if(n)emit(&current,n);fclose(fp);return 0;
}
