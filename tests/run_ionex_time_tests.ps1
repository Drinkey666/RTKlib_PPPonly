param([string]$DevCmd = 'E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Force validation/ionex_time_fix | Out-Null
$objects=Get-ChildItem build/PPP_only/x64/Release -Filter '*.obj' | Where-Object { $_.BaseName -notin @('rnx2rtkp','postpos') }
$taskArgs='/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /Fevalidation/ionex_time_fix/unit_tests.exe /Fovalidation/ionex_time_fix/ tests/ionex_time_regression.c ' + (($objects | ForEach-Object { '"'+$_.FullName+'"' }) -join ' ')
Set-Content validation/ionex_time_fix/unit.rsp -Encoding ascii -Value $taskArgs
$taskBuild='@echo off'+"`r`n"+'call "'+$DevCmd+'" -arch=x64 -host_arch=x64 >nul'+"`r`n"+'cl @validation\ionex_time_fix\unit.rsp /link /OPT:REF winmm.lib ws2_32.lib comdlg32.lib user32.lib gdi32.lib'
Set-Content validation/ionex_time_fix/unit.cmd -Encoding ascii -Value $taskBuild
& cmd.exe /c 'validation\ionex_time_fix\unit.cmd'
if($LASTEXITCODE -ne 0){throw 'IONEX unit test build failed'}
& ./validation/ionex_time_fix/unit_tests.exe | Tee-Object validation/ionex_time_fix/unit_results.txt
if($LASTEXITCODE -ne 0){throw 'IONEX unit tests failed'}
