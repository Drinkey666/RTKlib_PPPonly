@echo off
setlocal
rem Unified recorded PC entry. Existing A/B/research launchers are preserved.
python "%~dp0tools\run_ppp_session.py" %*
exit /b %errorlevel%
