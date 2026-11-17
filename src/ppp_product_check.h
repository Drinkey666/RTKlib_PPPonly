#ifndef PPP_PRODUCT_CHECK_H
#define PPP_PRODUCT_CHECK_H
#include "rtklib.h"
#include "pc_file_picker.h"

/* File-product contract: receiver epochs must be inside both loaded spans.
 * Does not promise per-satellite availability or positioning accuracy. */
int ppp_product_window(const nav_t *nav,gtime_t begin,gtime_t end,
                       char *reason,size_t capacity);
/* Independent preflight. Writes only report; never invokes rtkpos/filter or
 * edits observations, processing options, or live atmospheric caches.
 * Returns 0=fail, 1=pass, 2=pass with warnings. */
int ppp_product_check_files(const pc_ppp_files_t *files,const prcopt_t *opt,
                            int max_epochs,FILE *report);
#endif
