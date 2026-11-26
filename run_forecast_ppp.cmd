@echo off
setlocal
if "%~1"=="" (
  echo Usage: run_forecast_ppp.cmd product_manifest.json [--run]
  echo Default: check only. --run starts PPP only after forecast checks pass.
  exit /b 2
)
if not defined PPP_FORECAST_PYTHON set "PPP_FORECAST_PYTHON=E:\Program Files (x86)\python3\python.exe"
"%PPP_FORECAST_PYTHON%" "%~dp0tools\forecast_ppp.py" %*
exit /b %errorlevel%
