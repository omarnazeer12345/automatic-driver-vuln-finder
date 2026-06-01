# Architecture

## Overview

The pipeline is a 3-phase system:

1. **Acquisition** — Download or locate driver packages, extract `.sys` kernel files
2. **Decompilation** — Feed `.sys` binaries into Ghidra headless, get pseudo-C
3. **Analysis** — Send pseudo-C to Kimi Code API, receive vulnerability report

## Phase 1: Acquisition

### `vuln_pipeline.py` — `extract_kernel_files()`

Takes an installer path and tries 3 extraction methods in order:

1. **ZIP/SFX** (`zipfile` module) — Handles self-extracting archives
2. **Inno Setup** (`innounp`) — Handles Inno Setup installers
3. **7-Zip** (`7z`) — Handles NSIS, CAB, and other formats

After extraction, collects all `.sys` files and sorts by size descending.

### Downloaders

| Downloader | Source | Output | Notes |
|------------|--------|--------|-------|
| `amd_driver_downloader.py` | AMD support pages | ~47MB web stub | Contains NO `.sys` files |
| `nvidia_driver_downloader.py` | NVIDIA Ajax API | ~800MB full installer | Contains real `.sys` files |
| `intel_driver_downloader.py` | Intel download center | Varies | Often blocked by Akamai 403 |

### Local Scanning

`scan_local_kernel_files()` searches:
- `C:\Windows\System32\drivers\*.sys`
- `C:\Windows\System32\DriverStore\FileRepository\*\*.sys`

Returns deduplicated list sorted by file size.

## Phase 2: Decompilation

### `decompiler.py`

A Python wrapper around Ghidra's `analyzeHeadless`.

**Auto-detection order:**
1. Check `--ghidra` CLI argument
2. Check `GHIDRA_HOME` environment variable
3. Check bundled path: `./ghidra_tools/ghidra_11.0.3_PUBLIC/`
4. Auto-download from GitHub if `--auto-install`

**Java detection:**
1. Check `JAVA_HOME` environment variable
2. Check bundled JRE: `./ghidra_tools/jdk-21.0.11+10-jre/`

**Process:**
1. Creates a temporary Ghidra project
2. Imports the binary
3. Runs auto-analysis
4. Calls `ghidra_decompile.py` (Jython script) to extract pseudo-C
5. Saves output to `.c` file

### `ghidra_decompile.py`

A Jython script executed inside Ghidra's scripting engine. It:
1. Gets the current program
2. Iterates through functions (entry point + exported)
3. Uses Ghidra's `DecompInterface` to decompile each function
4. Writes pseudo-C to the output file

## Phase 3: AI Analysis

### `vuln_pipeline.py` — `analyze_with_kimi()`

**Protocol:** Anthropic Messages API

**Request structure:**
```json
{
  "model": "kimi-for-coding",
  "max_tokens": 8192,
  "system": "You are a kernel security expert...",
  "messages": [
    {"role": "user", "content": "{prompt}\n\n--- DECOMPILED PSEUDO-C START ---\n\n{pseudo_c}\n\n--- DECOMPILED PSEUDO-C END ---"}
  ]
}
```

**Payload safety:**
- Auto-truncates if payload exceeds ~1.8MB
- Respects `--max-chars` limit

**Retry logic:**
- 5 retries with exponential backoff
- Retries on HTTP 429 (rate limit) and 5xx errors
- Base delay: 20 seconds, doubles each attempt

### Response Parsing

Expects Anthropic response format:
```json
{
  "content": [
    {"type": "text", "text": "...report text..."}
  ],
  "usage": {
    "input_tokens": N,
    "output_tokens": M
  }
}
```

## Data Flow

```
User Input (driver path / preset / scan flag)
    |
    v
[Acquisition Layer]
    |-- downloaders (AMD/NVIDIA/Intel)
    |-- local filesystem scan
    |-- extraction (ZIP / innounp / 7-Zip)
    |
    v
[Decompilation Layer]
    |-- Ghidra headless project creation
    |-- auto-analysis
    |-- function decompilation (Jython)
    |
    v
[Analysis Layer]
    |-- pseudo-C truncation (size limits)
    |-- Anthropic API request
    |-- retry with backoff
    |
    v
[Output Layer]
    |-- {driver}_vuln_report.txt
    |-- {driver}_decompiled.c
```

## Configuration Files

| File | Format | Purpose |
|------|--------|---------|
| `kimi_config.json` | JSON | API credentials, model, timeouts |
| `kimi_prompt.txt` | Plain text | AI system/user prompt template |

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `GHIDRA_HOME` | `decompiler.py` | Path to Ghidra installation |
| `JAVA_HOME` | `decompiler.py` | Path to Java JRE |
| `PATH` | `decompiler.py` | Java binary location |

## Modes Architecture

The pipeline supports 10 mutually exclusive modes, dispatched in `main()`:

```python
mode_count = sum([
    bool(args.driver_file),
    bool(args.amd_preset),
    args.download_all,
    args.scan_local_drivers,
    args.scan_driverstore,
    bool(args.driver_folder),
    bool(args.nvidia_preset),
    bool(args.intel_preset),
    args.download_nvidia_all,
    args.download_intel_all,
])
```

Each mode calls its own runner function (`run_single`, `run_batch`, `run_nvidia_batch`, etc.) which in turn calls `process_single_driver()` for each `.sys` file.

## Error Handling

- **Download failures**: Logged as warnings, pipeline continues to next driver
- **Extraction failures**: Falls back through ZIP → innounp → 7-Zip
- **Decompilation failures**: Logged, skips to next driver
- **API failures**: Retries 5 times with exponential backoff
- **Individual driver errors**: Never crash the entire batch
