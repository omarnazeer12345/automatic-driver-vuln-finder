# Windows Kernel Driver Vulnerability Analysis Pipeline
# Setup Script
# Run this in PowerShell as Administrator (optional, but recommended)

param(
    [switch]$Skip7Zip,
    [switch]$SkipPython,
    [switch]$SkipGhidra
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-Warn($msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

function Write-Error($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

Write-Info "Setting up Driver Vuln Pipeline in: $ProjectDir"

# --- 1. Check 7-Zip ---
if (-not $Skip7Zip) {
    $sevenZip = Get-Command "7z" -ErrorAction SilentlyContinue
    if (-not $sevenZip) {
        $sevenZipPath = "C:\Program Files\7-Zip\7z.exe"
        if (Test-Path $sevenZipPath) {
            Write-Info "7-Zip found at: $sevenZipPath"
        } else {
            Write-Warn "7-Zip not found. Installing via winget..."
            winget install 7zip.7zip --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to install 7-Zip. Please install manually from https://www.7-zip.org/"
                exit 1
            }
        }
    } else {
        Write-Info "7-Zip found in PATH."
    }
}

# --- 2. Check Python ---
if (-not $SkipPython) {
    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command "python3" -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        $embedPython = Join-Path $ProjectDir "python-embed\python.exe"
        if (Test-Path $embedPython) {
            Write-Info "Embedded Python found."
            $python = $embedPython
        } else {
            Write-Warn "Python not found. Downloading embedded Python 3.12..."
            $pyUrl = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip"
            $pyZip = Join-Path $ProjectDir "python-embed.zip"
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyZip
            Expand-Archive -Path $pyZip -DestinationPath (Join-Path $ProjectDir "python-embed")
            Remove-Item $pyZip
            # Enable pip
            $pthFile = Join-Path $ProjectDir "python-embed\python312._pth"
            if (Test-Path $pthFile) {
                (Get-Content $pthFile) -replace "^#import site", "import site" | Set-Content $pthFile
            }
            # Download get-pip.py
            $getPip = Join-Path $ProjectDir "python-embed\get-pip.py"
            Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
            & (Join-Path $ProjectDir "python-embed\python.exe") $getPip
            $python = Join-Path $ProjectDir "python-embed\python.exe"
        }
    } else {
        Write-Info "Python found: $($python.Source)"
    }

    # Install requirements
    Write-Info "Installing Python dependencies..."
    & $python -m pip install -r (Join-Path $ProjectDir "requirements.txt")
}

# --- 3. Check Ghidra ---
if (-not $SkipGhidra) {
    $ghidraDir = Join-Path $ProjectDir "ghidra_tools\ghidra_11.0.3_PUBLIC"
    $jreDir = Join-Path $ProjectDir "ghidra_tools\jdk-21.0.11+10-jre"

    if ((Test-Path $ghidraDir) -and (Test-Path $jreDir)) {
        Write-Info "Ghidra + JRE found."
    } else {
        Write-Warn "Ghidra or JRE not found."
        Write-Info "Run the following to auto-download:"
        Write-Host "   python decompiler.py --auto-install --timeout 0 C:\Windows\System32\drivers\AcpiVpc.sys" -ForegroundColor Green
    }
}

# --- 4. Check API Key ---
$configFile = Join-Path $ProjectDir "kimi_config.json"
$config = Get-Content $configFile | ConvertFrom-Json
if ($config.api_key -eq "YOUR_API_KEY_HERE" -or $config.api_key -eq "") {
    Write-Warn "API key not configured in kimi_config.json"
    Write-Info "Please edit $configFile and add your Kimi API key."
} else {
    Write-Info "API key is configured."
}

Write-Info "Setup complete!"
Write-Info "Test with: python vuln_pipeline.py --driver-file C:\Windows\System32\drivers\AcpiVpc.sys --output-dir test_reports --max-chars 30000"
