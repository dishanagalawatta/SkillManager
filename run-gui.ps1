#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch SkillManager without any terminal window.

.DESCRIPTION
    Bypasses the console-subsystem entry-point wrapper (skill-manager.exe)
    and launches the Python GUI backend directly via pythonw.exe with
    WindowStyle Hidden — zero terminal windows visible.

    USAGE:
      .\run-gui.ps1          # Launch and detach (returns immediately)
      .\run-gui.ps1 -Wait    # Launch and wait for exit

.NOTES
    For the regular dev workflow, `uv run skill-manager` still works but
    will show a terminal (the uv/skill-manager.exe wrapper creates one).
    Use this script when you want no terminal at all.
#>
param([switch]$Wait)

$ErrorActionPreference = "Stop"

# Resolve project root (where this script lives)
$ProjectRoot = Split-Path -Parent $PSCommandPath

# Find pythonw.exe in the virtual environment
$PythonW = Join-Path $ProjectRoot ".venv" "Scripts" "pythonw.exe"
if (-not (Test-Path -LiteralPath $PythonW)) {
    Write-Error "pythonw.exe not found at: $PythonW"
    Write-Error "Run 'uv venv' first."
    exit 1
}

# Build the argument list
$ArgsList = @("-m", "skill_manager.__main__")

if ($Wait) {
    # Launch in same window (no new window), but wait for exit
    Write-Host "Starting SkillManager (waiting for exit)..."
    & $PythonW $ArgsList
} else {
    # Launch detached with hidden window — no terminal appears
    Start-Process `
        -FilePath $PythonW `
        -ArgumentList $ArgsList `
        -WindowStyle Hidden `
        -WorkingDirectory $ProjectRoot
}
