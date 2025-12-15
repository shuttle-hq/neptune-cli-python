# Neptune CLI Installer for Windows
$ErrorActionPreference = "Stop"

$Repo = "shuttle-hq/neptune-mcp"
$InstallDir = "$env:LOCALAPPDATA\Programs\neptune"
$BinaryName = "neptune.exe"
$MaxRetries = 5

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

# Download binary with retry mechanism
$RetryCount = 0
$Downloaded = $false

while ($RetryCount -lt $MaxRetries -and -not $Downloaded) {
    try {
        Invoke-WebRequest -Uri $LatestUrl -OutFile $TempFile -UseBasicParsing
        $Downloaded = $true
    }
    catch {
        $RetryCount++
        if ($RetryCount -lt $MaxRetries) {
            Write-Host "Download failed. Retrying... (Attempt $($RetryCount + 1)/$MaxRetries)"
            Start-Sleep -Seconds 2
        }
        else {
            Write-Error "Download failed after $MaxRetries attempts"
            throw
        }
    }
}

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

Write-Host ""
Write-Host "Installation successful! You can now use Neptune in your MCP client."
