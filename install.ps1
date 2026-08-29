param(
    [string]$Version = $env:DATACORE_VERSION,
    [switch]$NoSetup,
    [switch]$AllowFileCredential,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$Repo = "dptech-yb/datacore-cli"
$InstallRoot = if ($env:DATACORE_INSTALL_ROOT) { $env:DATACORE_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA "DataCore\CLI" }
$VenvRoot = Join-Path $InstallRoot "venv"
$ScriptsDir = Join-Path $VenvRoot "Scripts"
$DataCoreExe = Join-Path $ScriptsDir "datacore.exe"
$InstallMarker = Join-Path $InstallRoot ".datacore-cli-install"
$env:PYTHONUTF8 = "1"

if ($Uninstall) {
    if (-not (Test-Path -LiteralPath $InstallRoot)) {
        Write-Host "DataCore CLI is not installed."
        exit 0
    }
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
    if (Test-Path $DataCoreExe) {
        try { & $DataCoreExe auth logout | Out-Null } catch { }
        try { & $DataCoreExe skills uninstall --yes | Out-Null }
        catch { Write-Warning "DataCore Skills could not be removed automatically." }
    }
    Remove-Item -Recurse -Force $InstallRoot -ErrorAction SilentlyContinue
    $parts = ([Environment]::GetEnvironmentVariable("Path", "User") -split ";") | Where-Object { $_ -and $_ -ne $ScriptsDir }
    [Environment]::SetEnvironmentVariable("Path", ($parts -join ";"), "User")
    Write-Host "DataCore CLI and DataCore Skills were removed."
    exit 0
}

$PythonExe = $null
$PythonPrefix = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
    $PythonPrefix = @("-3")
}
if (-not $PythonExe) {
    throw "Python 3.10 or newer is required: https://www.python.org/downloads/windows/"
}
& $PythonExe @PythonPrefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.10 or newer is required." }

if (-not $Version -or $Version -eq "latest") {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
    $Version = $release.tag_name
}
if (-not $Version.StartsWith("v")) { $Version = "v$Version" }
$PackageVersion = $Version.Substring(1)
$Wheel = "datacore_cli-$PackageVersion-py3-none-any.whl"
$Base = if ($env:DATACORE_RELEASE_BASE) { $env:DATACORE_RELEASE_BASE } else { "https://github.com/$Repo/releases/download/$Version" }
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("datacore-cli-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TempRoot | Out-Null

try {
    Write-Host "Downloading DataCore CLI $Version..."
    Invoke-WebRequest -Uri "$Base/$Wheel" -OutFile (Join-Path $TempRoot $Wheel)
    Invoke-WebRequest -Uri "$Base/SHA256SUMS" -OutFile (Join-Path $TempRoot "SHA256SUMS")
    $checksumLine = Get-Content (Join-Path $TempRoot "SHA256SUMS") | Where-Object { $_ -match "\s\*?$([regex]::Escape($Wheel))$" } | Select-Object -First 1
    if (-not $checksumLine) { throw "Release checksum entry is missing." }
    $Expected = ($checksumLine -split "\s+")[0].ToLowerInvariant()
    $Actual = (Get-FileHash -Algorithm SHA256 (Join-Path $TempRoot $Wheel)).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) { throw "SHA256 verification failed; refusing installation." }

    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    if (-not (Test-Path (Join-Path $ScriptsDir "python.exe"))) {
        & $PythonExe @PythonPrefix -m venv $VenvRoot
    }
    & (Join-Path $ScriptsDir "python.exe") -m pip install --disable-pip-version-check --upgrade (Join-Path $TempRoot $Wheel)
    if ($LASTEXITCODE -ne 0) { throw "pip installation failed." }
    Set-Content -LiteralPath $InstallMarker -Value $PackageVersion -NoNewline

    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $PathParts = @($UserPath -split ";" | Where-Object { $_ })
    if ($PathParts -notcontains $ScriptsDir) {
        $PathParts += $ScriptsDir
        [Environment]::SetEnvironmentVariable("Path", ($PathParts -join ";"), "User")
        Write-Host "Added $ScriptsDir to the user PATH."
    }
    $env:Path = "$ScriptsDir;$env:Path"

    Write-Host "Installed DataCore CLI $PackageVersion."
    if (-not $NoSetup) {
        if ($AllowFileCredential) { & $DataCoreExe setup --allow-file-credential }
        else { & $DataCoreExe setup }
    } else {
        & $DataCoreExe skills install --force
        Write-Host "Run 'datacore setup' to authorize this device."
    }
}
finally {
    Remove-Item -Recurse -Force $TempRoot -ErrorAction SilentlyContinue
}
