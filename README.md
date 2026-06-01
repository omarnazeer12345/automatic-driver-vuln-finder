# Windows Kernel Driver Vulnerability Analysis Pipeline

An automated pipeline that downloads GPU drivers (AMD / NVIDIA / Intel), extracts kernel `.sys` files, decompiles them with Ghidra into pseudo-C, and analyzes them with AI for security vulnerabilities.

## Features

- **Multi-vendor driver downloads**: AMD (274 presets), NVIDIA (15+ GPUs), Intel (11 products)
- **Kernel file extraction**: Extracts `.sys` from `.exe`, `.zip`, `.7z`, `.cab`, `.msi` installers
- **Headless Ghidra decompilation**: Auto-detects bundled Ghidra + JRE, or downloads them automatically
- **AI vulnerability analysis**: Kimi Code API (Anthropic Messages protocol)
- **Local system scanning**: Batch-scan `C:\Windows\System32\drivers` + DriverStore (300+ drivers)
- **No timeouts**: All subprocess and API timeouts removed for large driver processing
- **Editable AI prompt**: Customize the vulnerability analysis prompt via `kimi_prompt.txt`
- **10 operation modes**: Single file, batch download, local scan, driver store scan, folder scan

## Quick Start

```bash
# 1. Install 7-Zip
winget install 7zip.7zip

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Add your Kimi API key to kimi_config.json

# 4. Analyze a local driver
python vuln_pipeline.py --driver-file "C:\Windows\System32\drivers\AcpiVpc.sys" --output-dir reports
```

## Requirements

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.10+ | Pipeline runtime | [python.org](https://python.org) |
| Ghidra 11.0+ | Binary decompilation | Auto-downloaded by `decompiler.py` |
| Java 21 JRE | Ghidra runtime | Auto-downloaded by `decompiler.py` |
| 7-Zip | Archive extraction | `winget install 7zip.7zip` |
| Kimi API key | AI analysis | [kimi.com](https://kimi.com) |

## Pipeline Architecture

```
Driver Source (.exe/.zip/.7z/.cab)
        |
        v
[extract_kernel_files()]  -->  .sys kernel files
        |
        v
[decompile_driver()]  -->  Ghidra headless  -->  pseudo-C (.c)
        |
        v
[analyze_with_kimi()]  -->  Kimi Code API  -->  vulnerability report (.txt)
```

## All 10 Operation Modes

| Mode | Flag | Description |
|------|------|-------------|
| Single file | `--driver-file PATH` | Analyze one `.sys` file |
| AMD preset | `--amd-preset NAME` | Download & analyze one AMD driver |
| NVIDIA preset | `--nvidia-preset NAME` | Download & analyze one NVIDIA driver |
| Intel preset | `--intel-preset NAME` | Download & analyze one Intel driver |
| AMD batch | `--download-all` | Download & analyze ALL AMD presets |
| NVIDIA batch | `--download-nvidia-all` | Download & analyze ALL NVIDIA presets |
| Intel batch | `--download-intel-all` | Download & analyze ALL Intel presets |
| Local scan | `--scan-local-drivers` | Scan system drivers + DriverStore |
| DriverStore only | `--scan-driverstore` | Scan Windows DriverStore only |
| Folder scan | `--driver-folder PATH` | Extract & analyze packages in folder |

## Usage Examples

### Single driver file
```bash
python vuln_pipeline.py --driver-file "C:\Windows\System32\drivers\AcpiVpc.sys" --output-dir reports --max-chars 30000
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

## File Reference

| File | Purpose |
|------|---------|
| `vuln_pipeline.py` | Main orchestrator — all 10 modes, extraction, decompilation, AI analysis |
| `decompiler.py` | Ghidra headless wrapper — auto-detects/downloads Ghidra + JRE |
| `ghidra_decompile.py` | Jython script run inside Ghidra for actual decompilation |
| `amd_driver_downloader.py` | AMD driver scraper (274 product presets from support pages) |
| `nvidia_driver_downloader.py` | NVIDIA driver downloader (Ajax API — full ~800MB installers) |
| `intel_driver_downloader.py` | Intel driver scraper (download center pages) |
| `fix_syntax.py` | Helper script for f-string formatting fixes |
| `kimi_config.json` | API key, base URL, model, max_tokens, request_timeout |
| `kimi_prompt.txt` | Editable AI analysis prompt sent with each decompiled driver |
| `requirements.txt` | Python dependencies |

## Configuration

### `kimi_config.json`
```json
{
  "api_key": "sk-kimi-...",
  "base_url": "https://api.kimi.com/coding/v1/messages",
  "model": "kimi-for-coding",
  "max_tokens": 8192,
  "request_timeout": 0
}
```

### `kimi_prompt.txt`
Edit this file to change what the AI looks for. Default prompt asks for critical vulnerabilities, memory safety issues, IOCTL handlers, and exploitability assessment.

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--driver-file` | — | Path to a single `.sys` or installer file |
| `--amd-preset` | — | AMD product name from preset list |
| `--nvidia-preset` | — | NVIDIA product name from preset list |
| `--intel-preset` | — | Intel product name from preset list |
| `--download-all` | — | Batch all AMD presets |
| `--download-nvidia-all` | — | Batch all NVIDIA presets |
| `--download-intel-all` | — | Batch all Intel presets |
| `--scan-local-drivers` | — | Scan system drivers + DriverStore |
| `--scan-driverstore` | — | Scan DriverStore only |
| `--driver-folder` | — | Folder containing driver packages |
| `--output-dir` | `.` | Directory for reports and decompiled C |
| `--ghidra-timeout` | `0` | Ghidra timeout in seconds. `0` = no limit |
| `--api-timeout` | `0` | API request timeout in seconds. `0` = no limit |
| `--max-chars` | `100000` | Max pseudo-C chars sent to Kimi |
| `--max-file-size-mb` | `100` | Skip downloaded files larger than this |
| `--skip-existing` | — | Skip drivers that already have reports |
| `--api-delay` | `5` | Seconds between API calls in batch mode |

## Output

For each driver analyzed, two files are created in `--output-dir`:

```
reports/
├── {driver_name}_vuln_report.txt     # AI vulnerability findings
└── {driver_name}_decompiled.c        # Ghidra pseudo-C output
```

## Known Limitations

| Issue | Workaround |
|-------|------------|
| AMD web installers contain no `.sys` files | Use `--scan-local-drivers` or `--driver-folder` with full packages |
| Intel download blocked by Akamai (403) | Use `--driver-folder` with manually downloaded Intel drivers |
| Large drivers (>20MB) take very long in Ghidra | Use `--ghidra-timeout 3600` or let it run with `0` (no limit) |
| API has ~2MB payload limit | Large pseudo-C is auto-truncated to `--max-chars` |

## Security Notice

This tool is for **security research and educational purposes only**. Do not use on systems you do not own or have explicit permission to test.

## License

MIT License — see LICENSE file.
