/* Frozen RTKLIB filter implementation from commit 97a57a9.
 * Copyright (C) 2007-2020 T. Takasu; see src/rtkcmn.c and original project license.
 * Used only on finite, invertible inputs as an arithmetic regression oracle. */
#include "rtklib.h"
static int reference_filter_(const double *x, const double *P, const double *H,
                   const double *v, const double *R, int n, int m,
                   double *xp, double *Pp)
{
    double *F=mat(n,m),*Q=mat(m,m),*K=mat(n,m),*I=eye(n);
    int info;

    matcpy(Q,R,m,m);
    matcpy(xp,x,n,1);
    matmul("NN",n,m,n,P,H,F);       /* Q=H'*P*H+R */
    matmulp("TN",m,m,n,H,F,Q);
    if (!(info=matinv(Q,m))) {
        matmul("NN",n,m,m,F,Q,K);   /* K=P*H*Q^-1 */
        matmulp("NN",n,1,m,K,v,xp);  /* xp=x+K*v */
        matmulm("NT",n,n,m,K,H,I);  /* Pp=(I-K*H')*P */
        matmul("NN",n,n,n,I,P,Pp);
    }
    free(F); free(Q); free(K); free(I);
    return info;
}
extern int reference_filter(double *x, double *P, const double *H, const double *v,
                  const double *R, int n, int m)
{
    double *x_,*xp_,*P_,*Pp_,*H_;
    int i,j,k,info,*ix;

    /* create list of non-zero states */
    ix=imat(n,1); for (i=k=0;i<n;i++) if (x[i]!=0.0&&P[i+i*n]>0.0) ix[k++]=i;
    x_=mat(k,1); xp_=mat(k,1); P_=mat(k,k); Pp_=mat(k,k); H_=mat(k,m);
    /* compress array by removing zero elements to save computation time */
    for (i=0;i<k;i++) {
        x_[i]=x[ix[i]];
        for (j=0;j<k;j++) P_[i+j*k]=P[ix[i]+ix[j]*n];
        for (j=0;j<m;j++) H_[i+j*k]=H[ix[i]+j*n];
    }
    /* do kalman filter state update on compressed arrays */
    info=reference_filter_(x_,P_,H_,v,R,k,m,xp_,Pp_);
    /* copy values from compressed arrays back to full arrays */
    for (i=0;i<k;i++) {
        x[ix[i]]=xp_[i];
        for (j=0;j<k;j++) P[ix[i]+ix[j]*n]=Pp_[i+j*k];
    }
    free(ix); free(x_); free(xp_); free(P_); free(Pp_); free(H_);
    return info;
}
