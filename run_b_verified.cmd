@echo off
setlocal
rem One verified preset in the actual VS project; old defaults remain available.
set RTK_PPP_PROFILE=B_VERIFIED
set RTK_PPP_BASELINE=B
set RTK_PPP_LIFECYCLE=CORRECTED
set RTK_PPP_CLOCK=PPP_COMMON
set RTK_PPP_ESTIMATOR=LEGACY
set RTK_PPP_RCB=
set RTK_PPP_TROP=
set RTK_PPP_UPDATE=
set RTK_PPP_NF=4
set RTK_PPP_SYSTEMS=GEC
set RTK_PPP_GLO=0
set RTK_PPP_GAL_E5B=0
set RTK_PPP_EXSATS=
set RTK_PPP_OPTS=
set RTK_PPP_AUDIT_POLICY=
set RTK_PPP_B_ION_CONTINUITY=
set RTK_PPP_PHASE_REFERENCE_SEED=
set RTK_PPP_BOOTSTRAP_IONO=
set RTK_PPP_VERIFIED_ROBUST=
if not exist "%~dp0x64\Release\PPP_only.exe" (
  echo Build PPP_only.sln as Release x64 first.
  exit /b 2
)
echo B_VERIFIED - formal VS executable, continuity repairs and Joseph covariance. Choose a NEW output.
"%~dp0x64\Release\PPP_only.exe" %*
