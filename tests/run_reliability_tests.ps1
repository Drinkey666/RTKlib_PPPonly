param([string]$DevCmd = 'E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
New-Item -ItemType Directory -Force validation/reliability | Out-Null
$objects = 'rtkcmn','trace','preceph','ephemeris','ionex','sofa','tides','ppp_position','smartphone_ppp_config','ppp_innovation_diag','gnss_adapter','gnss_signal_policy'
$taskArgs = '/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /Fevalidation/reliability/reliability_tests.exe /Fovalidation/reliability/ tests/reliability_regression.c tests/reliability_spp.c ' + (($objects | ForEach-Object { 'build/PPP_only/x64/Release/' + $_ + '.obj' }) -join ' ')
Set-Content -LiteralPath validation/reliability/tests.rsp -Encoding ascii -Value $taskArgs
$taskBuild = '@echo off' + "`r`n" + 'call "' + $DevCmd + '" -arch=x64 -host_arch=x64 >nul' + "`r`n" + 'cl @validation\reliability\tests.rsp /link /OPT:REF winmm.lib ws2_32.lib'
Set-Content -LiteralPath validation/reliability/build_tests.cmd -Encoding ascii -Value $taskBuild
& cmd.exe /c 'validation\reliability\build_tests.cmd'
if ($LASTEXITCODE -ne 0) { throw 'Regression build failed (build Release x64 first).' }
& ./validation/reliability/reliability_tests.exe | Tee-Object -FilePath validation/reliability/test_results.txt
if ($LASTEXITCODE -ne 0) { throw 'Reliability regression failed.' }
