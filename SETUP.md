# Setup Guide

## Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/driver-vuln-pipeline.git
cd driver-vuln-pipeline
```

## Step 2: Install 7-Zip

7-Zip is required for extracting driver packages.

```powershell
winget install 7zip.7zip
```

Or download manually from [7-zip.org](https://www.7-zip.org/).

## Step 3: Install Python 3.10+

Download from [python.org](https://www.python.org/downloads/) or use winget:

```powershell
winget install Python.Python.3.12
```

Or use the embedded Python (no install needed):

```powershell
# Download python-embed and extract to project folder
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip" -OutFile "python-embed.zip"
Expand-Archive -Path "python-embed.zip" -DestinationPath "python-embed"
```

## Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or with embedded Python:

```bash
python-embed\python.exe -m pip install -r requirements.txt
```

## Step 5: Configure Kimi API Key

Edit `kimi_config.json` and replace `YOUR_API_KEY_HERE` with your actual key:

```json
{
  "api_key": "sk-kimi-your-actual-key-here",
  "base_url": "https://api.kimi.com/coding/v1/messages",
  "model": "kimi-for-coding",
  "max_tokens": 8192,
  "request_timeout": 0
}
```

Get your API key from [kimi.com](https://kimi.com).

## Step 6: Install Ghidra & Java (Auto-Download)

The pipeline can auto-download Ghidra and Java on first run. Just run:

```bash
python decompiler.py --auto-install --timeout 0 "C:\Windows\System32\drivers\AcpiVpc.sys"
```

Or manually download:

1. **Ghidra 11.0.3**: [GitHub Releases](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_11.0.3_build)
2. **Eclipse Temurin JRE 21**: [Adoptium](https://adoptium.net/temurin/releases/?version=21)

Extract both to a `ghidra_tools/` folder:

```
ghidra_tools/
├── ghidra_11.0.3_PUBLIC/
└── jdk-21.0.11+10-jre/
```

## Step 7: Verify Installation

Run a quick test on a small driver:

```bash
python vuln_pipeline.py --driver-file "C:\Windows\System32\drivers\AcpiVpc.sys" --output-dir test_reports --max-chars 30000
```

If you see:
```
[INFO] Pseudo-C saved: ...
[INFO] Kimi response received. Tokens: prompt=..., completion=...
[INFO] Report saved: ...
```

Then everything is working.

## Troubleshooting

### "7z not found"
Install 7-Zip and ensure it's in PATH, or install to `C:\Program Files\7-Zip\7z.exe`.

### "Ghidra not found"
Run `decompiler.py --auto-install` or place Ghidra in `ghidra_tools/ghidra_11.0.3_PUBLIC/`.

### "Java not found"
Place JRE in `ghidra_tools/jdk-21.0.11+10-jre/` or set `JAVA_HOME`.

### API errors (429, 500, etc.)
The pipeline auto-retries with exponential backoff. If it keeps failing, check your API key in `kimi_config.json`.

### "No .sys files found" (AMD downloads)
AMD web installers are stubs without kernel files. Use `--scan-local-drivers` instead for real AMD `.sys` files.
