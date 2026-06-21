# build.ps1 — PyInstaller + Inno Setup build pipeline
# Usage: .\packaging\windows\build.ps1 [-Version 1.7.0] [-SkipSign] [-SkipInno]
param(
    [string]$Version,
    [switch]$SkipSign,
    [switch]$SkipInno
)

$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\.."
$spec = "$root\packaging\skill_manager.spec"
$dist = "$root\dist"
$iss = "$PSScriptRoot\installer.iss"

# --- Resolve version from pyproject.toml if not passed ---
if (-not $Version) {
    $pyproject = Get-Content "$root\pyproject.toml" -Raw
    if ($pyproject -match 'version\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    } else {
        throw "Cannot determine version. Pass -Version or check pyproject.toml."
    }
}
Write-Host "BUILD: version=$Version"

# --- Step 1: PyInstaller ---
Write-Host "BUILD: running PyInstaller..."
$env:PYTHONDONTWRITEBYTECODE = '1'
& uv run pyinstaller $spec --clean --noconfirm 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

# --- Step 2: Sign the PyInstaller EXE ---
$exePath = "$dist\SkillManager\SkillManager.exe"
if (-not $SkipSign -and (Test-Path $exePath)) {
    Write-Host "BUILD: signing SkillManager.exe..."
    & "$PSScriptRoot\sign.ps1" -FilePath $exePath
}

# --- Step 3: Inno Setup ---
if (-not $SkipInno) {
    $iscc = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if (-not $iscc) {
        Write-Host "BUILD: ISCC.exe not found — skipping Inno Setup. Install Inno Setup or pass -SkipInno."
    } else {
        Write-Host "BUILD: running Inno Setup..."
        & ISCC.exe /D"AppVersion=$Version" $iss 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

        # --- Step 4: Sign the installer ---
        $installer = "$dist\SkillManager_Setup.exe"
        if (-not $SkipSign -and (Test-Path $installer)) {
            Write-Host "BUILD: signing installer..."
            & "$PSScriptRoot\sign.ps1" -FilePath $installer
        }
    }
}

Write-Host "BUILD: done. Output: $dist"
