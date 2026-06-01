# Windows Kernel Driver Vulnerability Analysis Pipeline

An automated pipeline that downloads GPU drivers (AMD / NVIDIA / Intel), extracts kernel `.sys` files, decompiles them with Ghidra into pseudo-C, and analyzes them with AI for security vulnerabilities.

## Features

- **Multi-vendor driver downloads**: AMD, NVIDIA, Intel presets
- **Kernel file extraction**: Extracts `.sys` from `.exe`, `.zip`, `.7z`, `.cab` installers
- **Headless Ghidra decompilation**: Auto-detects bundled Ghidra + JRE
- **AI vulnerability analysis**: Kimi Code API (Anthropic protocol)
- **Local system scanning**: Batch-scan `C:\Windows\System32\drivers` + DriverStore
- **No timeouts**: All timeouts removed for large driver processing

## Requirements

- Python 3.10+
- Ghidra 11.0+ (bundled in `ghidra_tools/`)
- Java 21 JRE (bundled in `ghidra_tools/jdk-21.0.11+10-jre/`)
- 7-Zip (install via `winget install 7zip.7zip`)
- Kimi Code API key (in `kimi_config.json`)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Single driver file
```bash
python vuln_pipeline.py --driver-file path\to\driver.sys --output-dir reports
```

### Scan all local drivers
```bash
python vuln_pipeline.py --scan-local-drivers --output-dir reports
```

### Download & analyze NVIDIA driver
```bash
python vuln_pipeline.py --nvidia-preset "RTX 4090" --output-dir reports
```

### Download & analyze AMD driver
```bash
python vuln_pipeline.py --amd-preset "RX 7900 XTX" --output-dir reports
```

### Analyze a folder of driver packages
```bash
python vuln_pipeline.py --driver-folder "C:\Downloads\drivers" --output-dir reports
```

### Batch download all NVIDIA presets
```bash
python vuln_pipeline.py --download-nvidia-all --output-dir reports
```

## Files

| File | Purpose |
|------|---------|
| `vuln_pipeline.py` | Main orchestrator — all 10 modes |
| `decompiler.py` | Ghidra headless wrapper |
| `ghidra_decompile.py` | Jython script for Ghidra |
| `amd_driver_downloader.py` | AMD driver scraper (274 presets) |
| `nvidia_driver_downloader.py` | NVIDIA driver API downloader |
| `intel_driver_downloader.py` | Intel driver scraper |
| `kimi_config.json` | API key & model settings |
| `kimi_prompt.txt` | Editable AI analysis prompt |

## License

For security research and educational purposes only.
