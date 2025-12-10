# Neptune CLI Installer for Windows
$ErrorActionPreference = "Stop"

$Repo = "dcodesdev/neptune-cli-python"
$InstallDir = "$env:LOCALAPPDATA\Programs\neptune"
$BinaryName = "neptune.exe"

# Detect architecture
$Arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "x86" }

if ($Arch -ne "amd64") {
    Write-Error "Only 64-bit Windows is supported"
    exit 1
}

$AssetName = "neptune-windows-${Arch}.exe"

Write-Host "Detected: Windows $Arch"
Write-Host "Downloading: $AssetName"

$LatestUrl = "https://github.com/${Repo}/releases/latest/download/${AssetName}"

# Create install directory
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$TempFile = Join-Path $env:TEMP $BinaryName

# Download binary
Invoke-WebRequest -Uri $LatestUrl -OutFile $TempFile -UseBasicParsing

# Install
Move-Item -Path $TempFile -Destination (Join-Path $InstallDir $BinaryName) -Force

Write-Host "Neptune CLI installed to $InstallDir\$BinaryName"

# Add to PATH if not already there
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
    Write-Host ""
    Write-Host "Added $InstallDir to your PATH."
    Write-Host "Restart your terminal for changes to take effect."
}

Write-Host "Run 'neptune --help' to get started"
