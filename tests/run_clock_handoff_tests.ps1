param([string]$DevCmd='E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Force validation/clock_handoff | Out-Null
$objects='rtkcmn','trace','preceph','ephemeris','ionex','sofa','tides','pntpos','ppp_position','smartphone_ppp_config','ppp_innovation_diag'
$taskArgs='/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /Fevalidation/clock_handoff/unit_tests.exe /Fovalidation/clock_handoff/ tests/clock_handoff_regression.c tests/clock_handoff_spp.c tests/filter_reference_97a57a9.c ' + (($objects | ForEach-Object {'build/PPP_only/x64/Release/'+$_+'.obj'}) -join ' ')
Set-Content validation/clock_handoff/unit.rsp -Encoding ascii -Value $taskArgs
$taskBuild='@echo off'+"`r`n"+'call "'+$DevCmd+'" -arch=x64 -host_arch=x64 >nul'+"`r`n"+'cl @validation\clock_handoff\unit.rsp /link /OPT:REF winmm.lib ws2_32.lib'
Set-Content validation/clock_handoff/unit.cmd -Encoding ascii -Value $taskBuild
& cmd.exe /c 'validation\clock_handoff\unit.cmd'
if($LASTEXITCODE -ne 0){throw 'Clock tests build failed'}
& ./validation/clock_handoff/unit_tests.exe | Tee-Object validation/clock_handoff/unit_results.txt
if($LASTEXITCODE -ne 0){throw 'Clock tests failed'}
