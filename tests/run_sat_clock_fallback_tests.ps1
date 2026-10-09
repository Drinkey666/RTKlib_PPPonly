param([string]$DevCmd = 'E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
New-Item -ItemType Directory -Force validation/sat_clock_fallback | Out-Null
$others = 'rtkcmn','trace','preceph','sofa','sbas'
$taskArgs = '/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /Fevalidation/sat_clock_fallback/sat_clock_fallback_tests.exe /Fovalidation/sat_clock_fallback/ tests/sat_clock_fallback_regression.c src/ephemeris.c ' + (($others | ForEach-Object { 'build/PPP_only/x64/Release/' + $_ + '.obj' }) -join ' ')
Set-Content -LiteralPath validation/sat_clock_fallback/tests.rsp -Encoding ascii -Value $taskArgs
$taskBuild = '@echo off' + "`r`n" + 'call "' + $DevCmd + '" -arch=x64 -host_arch=x64 >nul' + "`r`n" + 'cl @validation\sat_clock_fallback\tests.rsp /link /OPT:REF winmm.lib ws2_32.lib'
Set-Content -LiteralPath validation/sat_clock_fallback/build_tests.cmd -Encoding ascii -Value $taskBuild
& cmd.exe /c 'validation\sat_clock_fallback\build_tests.cmd'
if ($LASTEXITCODE -ne 0) { throw 'Satellite-clock regression build failed (build Release x64 first).' }
& ./validation/sat_clock_fallback/sat_clock_fallback_tests.exe | Tee-Object -FilePath validation/sat_clock_fallback/test_results.txt
if ($LASTEXITCODE -ne 0) { throw 'Satellite-clock regression failed.' }
