param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath,

    [Parameter(Mandatory=$false)]
    [string]$CertPath = "$PSScriptRoot\certs\code-signing.pfx",

    [Parameter(Mandatory=$false)]
    [string]$CertPassword = $env:WIN_PFX_PASS
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $CertPath)) {
    Write-Host "SKIP_SIGN: cert not found at $CertPath"
    exit 0
}

if (-not $CertPassword) {
    Write-Host "SKIP_SIGN: WIN_PFX_PASS not set"
    exit 0
}

$signtool = Get-Command 'signtool.exe' -ErrorAction SilentlyContinue
if (-not $signtool) {
    Write-Host "SKIP_SIGN: signtool.exe not found in PATH"
    exit 0
}

$password = ConvertTo-SecureString -String $CertPassword -Force -AsPlainText

if ($FilePath -like '*.exe' -or $FilePath -like '*.msi') {
    & signtool.exe sign /fd SHA256 /tr http://ts.ssl.com /td sha256 /f $CertPath /p $CertPassword $FilePath
    if ($LASTEXITCODE -ne 0) { throw "signtool failed with exit code $LASTEXITCODE" }
    Write-Host "SIGNED: $FilePath"
} else {
    Write-Host "SKIP_SIGN: unsupported file type: $FilePath"
}
