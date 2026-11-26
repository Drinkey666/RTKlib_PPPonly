param([string]$DevCmd='E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskOut='validation/physical_atmosphere/unit'
New-Item -ItemType Directory -Force $taskOut | Out-Null
Copy-Item -LiteralPath src/ppp.c -Destination "$taskOut/ppp_estimator_under_test.c"
$objects='rtkcmn','trace','preceph','ephemeris','ionex','sofa','tides','pntpos','ppp_position','smartphone_ppp_config','ppp_innovation_diag'
$taskArgs='/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /I'+$taskOut+' /Fe'+$taskOut+'/tests.exe /Fo'+$taskOut+'/tests.obj tests/physical_atmosphere_regression.c '+(($objects | ForEach-Object {'build/PPP_only/x64/Release/'+$_+'.obj'}) -join ' ')
Set-Content -LiteralPath "$taskOut/tests.rsp" -Encoding ascii -Value $taskArgs
$taskBuild='@echo off'+"`r`n"+'call "'+$DevCmd+'" -arch=x64 -host_arch=x64 >nul'+"`r`n"+'cl @'+$taskOut+'/tests.rsp /link /OPT:REF winmm.lib ws2_32.lib'
Set-Content -LiteralPath "$taskOut/build.cmd" -Encoding ascii -Value $taskBuild
& cmd.exe /c (Resolve-Path -LiteralPath "$taskOut/build.cmd").Path
if($LASTEXITCODE -ne 0){throw 'Physical atmosphere tests failed to build'}
& "$taskOut/tests.exe" | Tee-Object -FilePath "$taskOut/results.txt"
if($LASTEXITCODE -ne 0){throw 'Physical atmosphere regression failed'}
