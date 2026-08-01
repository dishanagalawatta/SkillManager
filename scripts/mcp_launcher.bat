@echo off
rem mcp_launcher.bat - Launch the SkillManager MCP server for MCP clients.
rem
rem Why this exists: GUI-launched MCP clients spawn the configured command
rem with a minimal PATH. `uv` from the standalone installer lives in
rem %USERPROFILE%\.local\bin which those processes cannot see, so
rem `"command": "uv"` configs fail with `Executable not found in $PATH: "uv"`.
rem
rem This launcher prefers the project venv Python directly and falls back to
rem uv found on PATH or in %USERPROFILE%\.local\bin.
rem
rem Client config:
rem   "command": "C:\\path\\to\\skill-manager\\scripts\\mcp_launcher.bat",
rem   "args": ["--mcp"]        (or --mcp-light / --mcp-allow-write)

setlocal
set "PROJECT_ROOT=%~dp0.."

rem 1) Preferred: the project venv Python (no uv needed at runtime).
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m skill_manager.__main__ %*
    exit /b %ERRORLEVEL%
)

rem 2) Fallback: uv on PATH, then the standalone installer location.
where uv >nul 2>nul
if %ERRORLEVEL%==0 (
    uv --directory "%PROJECT_ROOT%" run skill-manager %*
    exit /b %ERRORLEVEL%
)
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    "%USERPROFILE%\.local\bin\uv.exe" --directory "%PROJECT_ROOT%" run skill-manager %*
    exit /b %ERRORLEVEL%
)

rem 3) Nothing usable - explain how to fix it.
echo SkillManager MCP launcher: no "%VENV_PYTHON%" and no uv found. 1>&2
echo Run "uv sync" in "%PROJECT_ROOT%" first, or install uv. 1>&2
exit /b 1
