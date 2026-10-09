/* Regression for satellite-indexed variance in satposs() clock fallback. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/rtklib.h"

static int passed, failed;
#define CHECK(name, condition) do { \
    if (condition) { passed++; printf("PASS %s\n", name); } \
    else { failed++; printf("FAIL %s (line %d)\n", name, __LINE__); } \
} while (0)

static void setup_nav(nav_t *nav, int missing_second_clock)
{
    const int sat1 = satno(SYS_GPS, 1), sat2 = satno(SYS_GPS, 2);
    const gtime_t epoch = gpst2time(2400, 1000.0);
    int j;

    memset(nav, 0, sizeof(*nav));
    nav->n = nav->nmax = 2;
    nav->ne = nav->nemax = 11; /* pephpos() needs NMAX + 1 samples. */
    nav->eph = (eph_t *)calloc(2, sizeof(eph_t));
    nav->peph = (peph_t *)calloc(11, sizeof(peph_t));
    if (!nav->eph || !nav->peph) {
        fprintf(stderr, "fixture allocation failed\n");
        exit(2);
    }
    nav->eph[0].sat = sat1;
    nav->eph[1].sat = sat2;
    for (j = 0; j < 2; ++j) {
        nav->eph[j].toe = epoch;
        nav->eph[j].toc = epoch;
        nav->eph[j].f0 = (j + 1) * 1E-4;
    }
    for (j = 0; j < nav->ne; ++j) {
        peph_t *peph = nav->peph + j;
        peph->time = timeadd(epoch, (j - 5) * 300.0);
        peph->pos[sat1 - 1][0] = 20200000.0;
        peph->pos[sat1 - 1][1] = 14000000.0;
        peph->pos[sat1 - 1][2] = 18000000.0;
        peph->pos[sat1 - 1][3] = 1E-4;
        peph->pos[sat2 - 1][0] = 23000000.0;
        peph->pos[sat2 - 1][1] = -13000000.0;
        peph->pos[sat2 - 1][2] = 9000000.0;
        peph->pos[sat2 - 1][3] = missing_second_clock ? 0.0 : 2E-4;
        peph->std[sat1 - 1][0] = peph->std[sat2 - 1][0] = 0.1f;
    }
}

static void run_case(int missing_second_clock, int reverse, double variance_by_sat[2])
{
    nav_t *nav = (nav_t *)calloc(1, sizeof(nav_t));
    obsd_t obs[2] = {{0}};
    double rs[12], dts[4], var[2];
    int svh[2], j;

    if (!nav) exit(2);
    setup_nav(nav, missing_second_clock);
    for (j = 0; j < 2; ++j) {
        obs[j].sat = (unsigned char)satno(SYS_GPS, reverse ? 2 - j : 1 + j);
        obs[j].time = timeadd(gpst2time(2400, 1000.0), 30.0);
        obs[j].P[0] = 24000000.0;
    }
    satposs(obs[0].time, obs, 2, nav, EPHOPT_PREC, rs, dts, var, svh);
    for (j = 0; j < 2; ++j) {
        CHECK("synthetic precise position and clock available",
            isfinite(rs[j * 6]) && rs[j * 6] != 0.0 && isfinite(dts[j * 2]) &&
            dts[j * 2] != 0.0 && svh[j] == 0);
        variance_by_sat[obs[j].sat == satno(SYS_GPS, 1) ? 0 : 1] = var[j];
    }
    free(nav->eph);
    free(nav->peph);
    free(nav);
}

int main(void)
{
    double missing[2], complete[2], reversed[2];
    FILE *fp;
    char line[512];
    int fallback_index_one = 0, fallback_index_zero = 0, fallback_total = 0;

    traceopen("validation/sat_clock_fallback/regression.trace");
    tracelevel(2);
    run_case(1, 0, missing);  /* G02 lacks SP3/PCLK clock at input index 1. */
    run_case(0, 0, complete); /* Both precise clocks are present. */
    run_case(1, 1, reversed); /* G02 fallback moves to input index 0. */
    traceclose();

    CHECK("non-fallback first satellite variance untouched",
        missing[0] > 0.0 && missing[0] == complete[0]);
    CHECK("missing-clock second satellite gets 900 m2", missing[1] == 900.0);
    CHECK("present precise clock keeps original variance",
        complete[1] > 0.0 && complete[1] < 900.0);
    CHECK("satellite order does not change per-satellite variances",
        reversed[0] == missing[0] && reversed[1] == missing[1]);

    fp = fopen("validation/sat_clock_fallback/regression.trace", "r");
    if (fp) {
        while (fgets(line, sizeof(line), fp)) {
            if (!strstr(line, "$SAT_CLOCK_FALLBACK")) continue;
            fallback_total++;
            if (strstr(line, "input_index=1") && strstr(line, "var=900.000"))
                fallback_index_one++;
            if (strstr(line, "input_index=0") && strstr(line, "var=900.000"))
                fallback_index_zero++;
        }
        fclose(fp);
    }
    CHECK("fallback trace identifies both satellite input indices",
        fallback_total == 2 && fallback_index_one == 1 && fallback_index_zero == 1);
    printf("RESULT passed=%d failed=%d\n", passed, failed);
    return failed ? 1 : 0;
}
