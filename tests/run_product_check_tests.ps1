param([string]$DevCmd = 'E:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Force validation/product_check | Out-Null
$objects=Get-ChildItem build/PPP_only/x64/Release -Filter '*.obj' | Where-Object { $_.BaseName -notin @('ppp','rnx2rtkp','postpos') }
$taskArgs='/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /Isrc /Fevalidation/product_check/unit_tests.exe /Fovalidation/product_check/ tests/product_check_regression.c ' + (($objects | ForEach-Object { '"'+$_.FullName+'"' }) -join ' ')
Set-Content validation/product_check/unit.rsp -Encoding ascii -Value $taskArgs
$taskBuild='@echo off'+"`r`n"+'call "'+$DevCmd+'" -arch=x64 -host_arch=x64 >nul'+"`r`n"+'cl @validation\product_check\unit.rsp /link /OPT:REF winmm.lib ws2_32.lib comdlg32.lib user32.lib gdi32.lib'
Set-Content validation/product_check/unit.cmd -Encoding ascii -Value $taskBuild
& cmd.exe /c 'validation\product_check\unit.cmd'
if($LASTEXITCODE -ne 0){throw 'Unit test build failed'}
& ./validation/product_check/unit_tests.exe | Tee-Object validation/product_check/unit_results.txt
if($LASTEXITCODE -ne 0){throw 'Unit tests failed'}
