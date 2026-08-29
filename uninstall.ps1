param(
    [switch]$PurgeBackups,
    [switch]$KeepAuthorization
)

$ErrorActionPreference = "Stop"
$InstallRoot = if ($env:DATACORE_INSTALL_ROOT) { $env:DATACORE_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA "DataCore\CLI" }
$VenvRoot = Join-Path $InstallRoot "venv"
$ScriptsDir = Join-Path $VenvRoot "Scripts"
$PythonExe = Join-Path $ScriptsDir "python.exe"
$DataCoreExe = Join-Path $ScriptsDir "datacore.exe"
$InstallMarker = Join-Path $InstallRoot ".datacore-cli-install"
$SkillsRoot = if ($env:DATACORE_SKILLS_DIR) { $env:DATACORE_SKILLS_DIR } else { Join-Path $HOME ".agents\skills" }
$env:PYTHONUTF8 = "1"

$ResolvedRoot = $null
if (Test-Path -LiteralPath $InstallRoot) {
    $TrimChars = [char[]]"\/"
    $ResolvedRoot = (Resolve-Path -LiteralPath $InstallRoot).Path.TrimEnd($TrimChars)
    $ResolvedHome = [System.IO.Path]::GetFullPath($HOME).TrimEnd($TrimChars)
    $VolumeRoot = [System.IO.Path]::GetPathRoot($ResolvedRoot).TrimEnd($TrimChars)
    if ($ResolvedRoot -eq $ResolvedHome -or $ResolvedRoot -eq $VolumeRoot) {
        throw "Refusing uninstall from unsafe path: $ResolvedRoot"
    }
    if (-not (Test-Path -LiteralPath $InstallMarker) -and -not (Test-Path -LiteralPath $DataCoreExe)) {
        throw "Refusing uninstall: $ResolvedRoot is not a DataCore CLI installation."
    }
}

$Cli = if (Test-Path -LiteralPath $DataCoreExe) { $DataCoreExe } else { $null }
$RemoteRevocationWarning = $false

if ($Cli) {
    if (-not $KeepAuthorization) {
        $HasAuthorization = $false
        if (Test-Path -LiteralPath $PythonExe) {
            & $PythonExe -c "from datacore_cli.credentials import load_token; from datacore_cli.main import DEFAULT_BASE_URL; raise SystemExit(0 if load_token(DEFAULT_BASE_URL) else 1)" 2>$null
            $HasAuthorization = $LASTEXITCODE -eq 0
        }
        if ($HasAuthorization) {
            try {
                & $Cli auth logout | Out-Null
                if ($LASTEXITCODE -ne 0) { $RemoteRevocationWarning = $true }
            } catch { $RemoteRevocationWarning = $true }
        }
        try {
            & $Cli uninstall --yes | Out-Null
            if ($LASTEXITCODE -ne 0) { Write-Warning "Local credential or DataCore Skills could not be removed automatically." }
        } catch { Write-Warning "Local credential or DataCore Skills could not be removed automatically." }
    } else {
        try {
            & $Cli skills uninstall --yes | Out-Null
            if ($LASTEXITCODE -ne 0) { Write-Warning "DataCore Skills could not be removed automatically." }
        } catch { Write-Warning "DataCore Skills could not be removed automatically." }
    }
} else {
    Write-Warning "No DataCore CLI was available to clean authorization and Skills."
}

if (-not $KeepAuthorization) {
    $ConfigRoot = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { Join-Path $HOME ".config" }
    $CredentialFile = Join-Path $ConfigRoot "datacore\credentials.json"
    if (Test-Path -LiteralPath $CredentialFile) {
        try {
            $CredentialValue = Get-Content -Raw -LiteralPath $CredentialFile | ConvertFrom-Json
            if (@($CredentialValue.PSObject.Properties).Count -eq 0) {
                Remove-Item -Force -LiteralPath $CredentialFile
                $CredentialParent = Split-Path -Parent $CredentialFile
                if (@(Get-ChildItem -Force -LiteralPath $CredentialParent -ErrorAction SilentlyContinue).Count -eq 0) {
                    Remove-Item -Force -LiteralPath $CredentialParent
                }
            }
        } catch { }
    }
}

if ($ResolvedRoot) {
    Remove-Item -Recurse -Force $ResolvedRoot
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath) {
    $PathParts = @($UserPath -split ";" | Where-Object { $_ -and $_ -ne $ScriptsDir })
    [Environment]::SetEnvironmentVariable("Path", ($PathParts -join ";"), "User")
}

if ($PurgeBackups) {
    $SkillsParent = Split-Path -Parent $SkillsRoot
    $BackupRoot = Join-Path $SkillsParent "datacore-skill-backups"
    $ResolvedHome = [System.IO.Path]::GetFullPath($HOME).TrimEnd([char[]]"\/")
    $BackupFull = [System.IO.Path]::GetFullPath($BackupRoot)
    if (-not $BackupFull.StartsWith("$ResolvedHome$([System.IO.Path]::DirectorySeparatorChar)", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to purge backups outside the home directory: $BackupFull"
    }
    Remove-Item -Recurse -Force $BackupFull -ErrorAction SilentlyContinue
}

if (Test-Path -LiteralPath $SkillsRoot) {
    $Remaining = @(Get-ChildItem -Force -LiteralPath $SkillsRoot -ErrorAction SilentlyContinue)
    if ($Remaining.Count -eq 0) { Remove-Item -Force $SkillsRoot }
}
$SkillsParent = Split-Path -Parent $SkillsRoot
if (Test-Path -LiteralPath $SkillsParent) {
    $Remaining = @(Get-ChildItem -Force -LiteralPath $SkillsParent -ErrorAction SilentlyContinue)
    if ($Remaining.Count -eq 0) { Remove-Item -Force $SkillsParent }
}

if ($KeepAuthorization) {
    Write-Host "DataCore CLI and managed Skills were removed; device authorization was kept."
} elseif ($PurgeBackups) {
    Write-Host "DataCore CLI, managed Skills, backups, and the local device credential were removed."
} else {
    Write-Host "DataCore CLI, managed Skills, and the local device credential were removed."
    Write-Host "Safety backups of user-modified Skills, if any, were kept."
}
if ($RemoteRevocationWarning) {
    Write-Warning "Remote session revocation could not be confirmed; revoke this device in DataCore Personal Center if needed."
}
if (-not $KeepAuthorization -and $env:DATACORE_TOKEN) {
    Write-Warning "DATACORE_TOKEN is still set in the environment; remove it from the environment or secret manager separately."
}
