@echo off
REM Inno Setup SignTool wrapper — calls sign.ps1
REM Configure in Inno Setup: SignTool=sign-wrapper
setlocal
set "CERT=%~dp0certs\code-signing.pfx"
if not exist "%CERT%" (
    echo SKIP_SIGN: cert not found at %CERT%
    exit /b 0
)
if "%WIN_PFX_PASS%"=="" (
    echo SKIP_SIGN: WIN_PFX_PASS not set
    exit /b 0
)
signtool.exe sign /fd SHA256 /tr http://ts.ssl.com /td sha256 /f "%CERT%" /p %WIN_PFX_PASS% %*
