param([string]$DevCmd = 'E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
New-Item -ItemType Directory -Force validation/phase1 | Out-Null
$objects = 'rtkcmn','trace','preceph','ephemeris','ionex','sbas','sofa','tides','pntpos','ppp_ar','ppp_position','smartphone_ppp_config'
$taskArgs = '/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /Fevalidation/phase1/phase1_tests.exe /Fovalidation/phase1/ tests/phase1_regression.c tests/filter_reference_97a57a9.c ' + (($objects | ForEach-Object { 'build/PPP_only/x64/Release/' + $_ + '.obj' }) -join ' ')
Set-Content -LiteralPath validation/phase1/tests.rsp -Encoding ascii -Value $taskArgs
$taskBuild = '@echo off' + "`r`n" + 'call "' + $DevCmd + '" -arch=x64 -host_arch=x64 >nul' + "`r`n" + 'cl @validation\phase1\tests.rsp /link /OPT:REF winmm.lib ws2_32.lib'
Set-Content -LiteralPath validation/phase1/build_tests.cmd -Encoding ascii -Value $taskBuild
& cmd.exe /c 'validation\phase1\build_tests.cmd'
if ($LASTEXITCODE -ne 0) { throw 'Regression build failed (build Release x64 first).' }
& ./validation/phase1/phase1_tests.exe | Tee-Object -FilePath validation/phase1/test_results.txt
if ($LASTEXITCODE -ne 0) { throw 'Regression failed.' }
