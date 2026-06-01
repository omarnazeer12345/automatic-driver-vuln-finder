#!/usr/bin/env python3
r"""
Windows Driver -> Ghidra -> Kimi AI  |  Automated Vulnerability Analysis Pipeline

Flow:
  1. Obtain driver binary (local .sys file, system DriverStore scan, or download)
  2. Extract ALL kernel .sys files from the package
  3. Decompile each .sys with Ghidra headless -> pseudo-C (.c)
  4. Send pseudo-C + prompt to Kimi AI API for vulnerability analysis
  5. Save vulnerability report as report.txt for each kernel file

IMPORTANT NOTE ABOUT AMD DOWNLOADS:
  AMD's support website only provides web installers (~47 MB downloader stubs).
  These do NOT contain the actual .sys kernel driver files inside.
  For real AMD kernel drivers, use:
    --scan-local-drivers   -> scans C:\Windows\System32\drivers + DriverStore
    --scan-driverstore     -> scans C:\Windows\System32\DriverStore\FileRepository
    --driver-file <path>   -> point to an existing .sys file

Usage:
    python vuln_pipeline.py --driver-file C:\Windows\System32\drivers\amdgpio2.sys
    python vuln_pipeline.py --scan-local-drivers --output-dir reports
    python vuln_pipeline.py --scan-driverstore --output-dir reports
    python vuln_pipeline.py --amd-preset rx7800xt
    python vuln_pipeline.py --download-all --output-dir reports

Editable files:
    kimi_prompt.txt      -> vulnerability analysis prompt
    kimi_config.json     -> API key, model, base_url, etc.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

__version__ = "1.2.0"

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "kimi_config.json"
PROMPT_PATH = SCRIPT_DIR / "kimi_prompt.txt"

SYSTEM_MSG = (
    "You are an expert Windows kernel driver security researcher. "
    "Analyze the provided decompiled pseudo-C code for memory safety bugs, "
    "logic errors, IOCTL handler vulnerabilities, race conditions, buffer overflows, "
    "integer overflows, use-after-free, and any exploitable weaknesses. "
    "Provide a structured report with severity ratings and line references where possible."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        error(f"Failed to load {path}: {exc}")


def load_text(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        error(f"Failed to load {path}: {exc}")


def python_exe() -> str:
    """Return path to embedded Python or system python."""
    embed = SCRIPT_DIR / "python-embed" / "python.exe"
    if embed.exists():
        return str(embed)
    return sys.executable


def get_amd_presets() -> list[str]:
    """Import AMD_PRODUCTS from the downloader script."""
    downloader = SCRIPT_DIR / "amd_driver_downloader.py"
    if not downloader.exists():
        error(f"AMD downloader not found: {downloader}")

    spec = importlib.util.spec_from_file_location("amd_downloader", str(downloader))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.AMD_PRODUCTS.keys())


def get_nvidia_presets() -> list[str]:
    """Import NVIDIA_PRODUCTS from the downloader script."""
    downloader = SCRIPT_DIR / "nvidia_driver_downloader.py"
    if not downloader.exists():
        error(f"NVIDIA downloader not found: {downloader}")

    spec = importlib.util.spec_from_file_location("nvidia_downloader", str(downloader))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.NVIDIA_PRODUCTS.keys())


def get_intel_presets() -> list[str]:
    """Import INTEL_PRODUCTS from the downloader script."""
    downloader = SCRIPT_DIR / "intel_driver_downloader.py"
    if not downloader.exists():
        error(f"Intel downloader not found: {downloader}")

    spec = importlib.util.spec_from_file_location("intel_downloader", str(downloader))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.INTEL_PRODUCTS.keys())


# ---------------------------------------------------------------------------
# Phase 1: Obtain driver
# ---------------------------------------------------------------------------

def download_amd_preset(preset: str, dest_dir: Path) -> Path | None:
    """Download AMD driver using the existing downloader script. Returns path or None on failure."""
    downloader = SCRIPT_DIR / "amd_driver_downloader.py"
    if not downloader.exists():
        warn(f"AMD downloader not found: {downloader}")
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    info(f"Downloading AMD preset '{preset}' ...")

    cmd = [
        python_exe(),
        str(downloader),
        "--product", preset,
        "--output-dir", str(dest_dir),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=None,
    )

    if proc.returncode != 0:
        warn(f"AMD downloader failed for preset '{preset}':\n{proc.stdout}\n{proc.stderr}")
        return None

    # Find the downloaded file (newest file in dest_dir)
    files = [f for f in dest_dir.iterdir() if f.is_file()]
    if not files:
        warn(f"Download completed for '{preset}' but no file was found.")
        return None

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    downloaded = files[0]
    info(f"Downloaded: {downloaded.name} ({downloaded.stat().st_size} bytes)")
    return downloaded


def download_nvidia_preset(preset: str, dest_dir: Path) -> Path | None:
    """Download NVIDIA driver using the existing downloader script. Returns path or None on failure."""
    downloader = SCRIPT_DIR / "nvidia_driver_downloader.py"
    if not downloader.exists():
        warn(f"NVIDIA downloader not found: {downloader}")
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    info(f"Downloading NVIDIA preset '{preset}' ...")

    cmd = [
        python_exe(),
        str(downloader),
        "--product", preset,
        "--output-dir", str(dest_dir),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=None,
    )

    if proc.returncode != 0:
        warn(f"NVIDIA downloader failed for preset '{preset}':\n{proc.stdout}\n{proc.stderr}")
        return None

    files = [f for f in dest_dir.iterdir() if f.is_file()]
    if not files:
        warn(f"Download completed for '{preset}' but no file was found.")
        return None

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    downloaded = files[0]
    info(f"Downloaded: {downloaded.name} ({downloaded.stat().st_size} bytes)")
    return downloaded


def download_intel_preset(preset: str, dest_dir: Path) -> Path | None:
    """Download Intel driver using the existing downloader script. Returns path or None on failure."""
    downloader = SCRIPT_DIR / "intel_driver_downloader.py"
    if not downloader.exists():
        warn(f"Intel downloader not found: {downloader}")
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    info(f"Downloading Intel preset '{preset}' ...")

    cmd = [
        python_exe(),
        str(downloader),
        "--product", preset,
        "--output-dir", str(dest_dir),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=None,
    )

    if proc.returncode != 0:
        warn(f"Intel downloader failed for preset '{preset}':\n{proc.stdout}\n{proc.stderr}")
        return None

    files = [f for f in dest_dir.iterdir() if f.is_file()]
    if not files:
        warn(f"Download completed for '{preset}' but no file was found.")
        return None

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    downloaded = files[0]
    info(f"Downloaded: {downloaded.name} ({downloaded.stat().st_size} bytes)")
    return downloaded


def find_seven_zip() -> str | None:
    """Find 7-Zip executable on Windows."""
    # Check common locations
    candidates = [
        shutil.which("7z"),
        shutil.which("7za"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def find_innounp() -> str | None:
    """Find innounp (Inno Setup unpacker) executable."""
    candidates = [
        shutil.which("innounp"),
        r"C:\Program Files\innounp\innounp.exe",
    ]
    # Also check WinGet install location
    winget_base = Path(r"C:\Users") / os.getlogin() / r"AppData\Local\Microsoft\WinGet\Packages"
    if winget_base.exists():
        for sub in winget_base.glob("JurgenRathlev.innounp*"):
            exe = sub / "innounp.exe"
            if exe.exists():
                return str(exe)
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def extract_kernel_files(installer_path: Path, extract_dir: Path) -> list[Path]:
    """
    Extract all .sys kernel driver files from the installer package.
    Supports ZIP-based SFX, 7-Zip (NSIS, CAB, etc.), and Inno Setup (innounp).
    Returns a sorted list of .sys file paths (largest first).
    """
    extract_dir.mkdir(parents=True, exist_ok=True)
    sys_files: list[Path] = []

    # --- Try ZIP / SFX first ---
    if zipfile.is_zipfile(str(installer_path)):
        info(f"Extracting ZIP/SFX: {installer_path.name} ...")
        try:
            with zipfile.ZipFile(installer_path, "r") as zf:
                for member in zf.namelist():
                    if member.lower().endswith(".sys"):
                        zf.extract(member, path=extract_dir)
        except Exception as exc:
            warn(f"ZIP extraction failed: {exc}")

    # --- Try Inno Setup (innounp) ---
    innounp = find_innounp()
    if not sys_files and innounp:
        info(f"Attempting Inno Setup extraction with innounp: {installer_path.name} ...")
        try:
            subprocess.run(
                [innounp, "-x", f"-d{extract_dir}", str(installer_path)],
                capture_output=True,
                timeout=None,
            )
        except Exception as exc:
            warn(f"innounp extraction failed: {exc}")

    # --- Try 7-Zip (handles NSIS, CAB, etc.) ---
    seven_zip = find_seven_zip()
    if not sys_files and seven_zip:
        info(f"Attempting 7-Zip extraction: {installer_path.name} ...")
        try:
            subprocess.run(
                [seven_zip, "x", "-y", f"-o{extract_dir}", str(installer_path)],
                capture_output=True,
                timeout=None,
            )
        except Exception as exc:
            warn(f"7-Zip extraction failed: {exc}")

    # --- Collect all .sys files ---
    for f in extract_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() == ".sys":
            sys_files.append(f)

    if not sys_files:
        warn("No .sys kernel files found inside the package.")
        return []

    # Sort by size descending (main kernel drivers are usually the largest)
    sys_files.sort(key=lambda p: p.stat().st_size, reverse=True)

    info(f"Found {len(sys_files)} kernel .sys file(s):")
    for f in sys_files:
        info(f"  - {f.name} ({f.stat().st_size} bytes)")

    return sys_files


# ---------------------------------------------------------------------------
# Phase 2: Decompile with Ghidra
# ---------------------------------------------------------------------------

def decompile_driver(driver_path: Path, output_c: Path, timeout: int = 0) -> bool:
    """Run Ghidra decompiler on a single driver binary. Returns True on success."""
    decompiler = SCRIPT_DIR / "decompiler.py"
    if not decompiler.exists():
        warn(f"Decompiler script not found: {decompiler}")
        return False

    # Detect bundled Ghidra + JRE
    bundled_ghidra = SCRIPT_DIR / "ghidra_tools" / "ghidra_11.0.3_PUBLIC"
    bundled_jre = SCRIPT_DIR / "ghidra_tools" / "jdk-21.0.11+10-jre"

    info(f"Decompiling {driver_path.name} with Ghidra ...")
    cmd = [
        python_exe(),
        str(decompiler),
        str(driver_path),
        "--output", str(output_c),
    ]
    if timeout > 0:
        cmd += ["--timeout", str(timeout)]
    if bundled_ghidra.exists():
        cmd += ["--ghidra", str(bundled_ghidra)]

    env = os.environ.copy()
    if bundled_jre.exists():
        env["JAVA_HOME"] = str(bundled_jre)
        env["PATH"] = str(bundled_jre / "bin") + os.pathsep + env.get("PATH", "")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=(timeout + 60) if timeout > 0 else None,
            env=env,
        )
    except Exception as exc:
        warn(f"Decompiler subprocess failed: {exc}")
        return False

    if proc.returncode != 0:
        warn(f"Decompiler exited with code {proc.returncode}.\n{proc.stdout}\n{proc.stderr}")
        return False

    if not output_c.exists():
        warn("Decompilation output file was not created.")
        return False

    info(f"Pseudo-C saved: {output_c} ({output_c.stat().st_size} bytes)")
    return True


# ---------------------------------------------------------------------------
# Phase 3: Kimi AI Analysis
# ---------------------------------------------------------------------------

def analyze_with_kimi(pseudo_c: str, config: dict, prompt: str, timeout: int = 0) -> str | None:
    """Send decompiled code to Kimi Code API (Anthropic protocol) and return report text."""
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.kimi.com/coding/v1/messages")
    model = config.get("model", "kimi-for-coding")
    max_tokens = config.get("max_tokens", 8192)
    req_timeout = timeout if timeout > 0 else config.get("request_timeout", 0)

    if not api_key:
        warn("Kimi API key is missing. Check kimi_config.json.")
        return None

    user_content = f"{prompt}\n\n--- DECOMPILED PSEUDO-C START ---\n\n{pseudo_c}\n\n--- DECOMPILED PSEUDO-C END ---"

    # Guard against oversized payloads (~2 MB limit)
    MAX_PAYLOAD_BYTES = 1_800_000
    while len(user_content.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        warn(f"Content too long ({len(user_content)} chars). Truncating...")
        user_content = user_content[:len(user_content)//2]
        user_content += "\n\n/* [TRUNCATED for API size limits] */\n"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_MSG,
        "messages": [
            {"role": "user", "content": user_content},
        ],
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
    }

    info(f"Sending to Kimi Code API ({model}) ...")
    info(f"Payload size: {len(body)} bytes")

    req = urllib.request.Request(base_url, data=body, headers=headers, method="POST")

    # Retry with exponential backoff on 429 or 5xx errors
    max_retries = 5
    base_delay = 20
    resp_bytes = b""

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=req_timeout if req_timeout > 0 else None) as resp:
                resp_bytes = resp.read()
            break  # success
        except urllib.error.HTTPError as exc:
            resp_text = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 or (500 <= exc.code < 600):
                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    warn(f"Kimi API HTTP {exc.code} (attempt {attempt}/{max_retries}). Retrying in {delay}s ...")
                    time.sleep(delay)
                    continue
            warn(f"Kimi API HTTP error {exc.code}: {resp_text}")
            return None
        except Exception as exc:
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                warn(f"Kimi API request failed (attempt {attempt}/{max_retries}): {exc}. Retrying in {delay}s ...")
                time.sleep(delay)
                continue
            warn(f"Kimi API request failed: {exc}")
            return None

    try:
        resp_json = json.loads(resp_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:
        warn(f"Failed to parse Kimi API response: {exc}")
        return None

    content_blocks = resp_json.get("content", [])
    if not content_blocks:
        warn(f"No content in Kimi response: {resp_json}")
        return None

    report = ""
    for block in content_blocks:
        if block.get("type") == "text":
            report += block.get("text", "")

    if not report:
        warn("Kimi returned empty report content.")
        return None

    usage = resp_json.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", "?")
    completion_tokens = usage.get("completion_tokens", "?")
    info(f"Kimi response received. Tokens: prompt={prompt_tokens}, completion={completion_tokens}")

    return report


def save_report(report: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    info(f"Report saved: {path}")


# ---------------------------------------------------------------------------
# Single-driver processing
# ---------------------------------------------------------------------------

def process_single_driver(
    driver_path: Path,
    config: dict,
    prompt: str,
    args,
    work_dir: Path | None = None,
) -> Path | None:
    """Process one .sys driver through decompilation + AI. Returns report path or None."""
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="vuln_pipeline_"))

    # --- Decompile ---
    decomp_c = work_dir / f"{driver_path.stem}.c"
    if not decompile_driver(driver_path, decomp_c, timeout=args.ghidra_timeout):
        return None

    # Read decompiled C (with size safety)
    pseudo_c = decomp_c.read_text(encoding="utf-8", errors="replace")
    max_chars = args.max_chars
    if len(pseudo_c) > max_chars:
        warn(f"Decompiled C is {len(pseudo_c)} chars; truncating to {max_chars} for API safety.")
        pseudo_c = pseudo_c[:max_chars]
        pseudo_c += "\n\n/* [TRUNCATED for API token limits] */\n"

    # --- AI Analysis ---
    report = analyze_with_kimi(pseudo_c, config, prompt, timeout=getattr(args, "api_timeout", 0))
    if report is None:
        return None

    # --- Save Report & Pseudo-C ---
    if args.output_dir:
        out_dir = Path(args.output_dir).expanduser().resolve()
    else:
        out_dir = Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    report_path = out_dir / f"{driver_path.stem}_vuln_report.txt"
    c_path = out_dir / f"{driver_path.stem}_decompiled.c"

    save_report(report, report_path)
    shutil.copy2(decomp_c, c_path)
    info(f"Pseudo-C saved: {c_path}")

    return report_path


# ---------------------------------------------------------------------------
# Batch mode (AMD preset downloads)
# ---------------------------------------------------------------------------

def run_batch(args) -> None:
    """Download and analyze ALL AMD presets one by one."""
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    presets = get_amd_presets()
    info(f"Found {len(presets)} AMD presets to process.")
    info("NOTE: AMD's website only provides web installers (~47 MB stubs).")
    info("      These typically do NOT contain .sys kernel files.")
    info("      For real kernel drivers, use --scan-local-drivers or --scan-driverstore.")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    download_dir = output_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    max_size_bytes = args.max_file_size_mb * 1024 * 1024

    success = 0
    failed = 0
    skipped = 0

    for idx, preset in enumerate(presets, start=1):
        print(f"\n{'='*60}")
        info(f"[{idx}/{len(presets)}] Processing preset: {preset}")
        print(f"{'='*60}")

        # --- Download ---
        downloaded = download_amd_preset(preset, download_dir)
        if downloaded is None:
            failed += 1
            continue

        # --- Size check ---
        if downloaded.stat().st_size > max_size_bytes:
            warn(f"File {downloaded.name} ({downloaded.stat().st_size} bytes) exceeds max size ({max_size_bytes} bytes). Skipping.")
            skipped += 1
            continue

        # --- Extract kernel .sys files ---
        extract_dir = download_dir / f"{preset}_extracted"
        kernel_files = extract_kernel_files(downloaded, extract_dir)

        if not kernel_files:
            warn(f"No kernel files extracted for preset '{preset}'.")
            warn(f"AMD web installers do not contain .sys files. Skipping.")
            skipped += 1
            continue

        # --- Process each .sys ---
        for sys_path in kernel_files:
            report_path = output_dir / f"{sys_path.stem}_vuln_report.txt"
            if args.skip_existing and report_path.exists():
                info(f"Report already exists, skipping: {report_path}")
                skipped += 1
                continue

            work_dir = Path(tempfile.mkdtemp(prefix=f"vuln_pipeline_{preset}_{sys_path.stem}_"))
            try:
                result_path = process_single_driver(
                    sys_path, config, prompt, args, work_dir=work_dir
                )
                if result_path:
                    success += 1
                else:
                    failed += 1
            except Exception as exc:
                warn(f"Unhandled exception during processing of {sys_path}: {exc}")
                failed += 1
            finally:
                if not args.keep_work:
                    shutil.rmtree(work_dir, ignore_errors=True)

        # Be polite to servers and respect API rate limits
        time.sleep(1)
        if args.api_delay > 0:
            time.sleep(args.api_delay)

    print(f"\n{'='*60}")
    info("BATCH COMPLETE")
    info(f"Success : {success}")
    info(f"Failed  : {failed}")
    info(f"Skipped : {skipped}")
    info(f"Reports saved to: {output_dir}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# NVIDIA batch mode
# ---------------------------------------------------------------------------

def run_nvidia_batch(args) -> None:
    """Download and analyze ALL NVIDIA presets one by one."""
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    presets = get_nvidia_presets()
    info(f"Found {len(presets)} NVIDIA presets to process.")
    info("NOTE: NVIDIA provides full installers with real .sys kernel files inside.")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    download_dir = output_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    max_size_bytes = args.max_file_size_mb * 1024 * 1024

    success = 0
    failed = 0
    skipped = 0

    for idx, preset in enumerate(presets, start=1):
        print(f"\n{'='*60}")
        info(f"[{idx}/{len(presets)}] Processing NVIDIA preset: {preset}")
        print(f"{'='*60}")

        downloaded = download_nvidia_preset(preset, download_dir)
        if downloaded is None:
            failed += 1
            continue

        if downloaded.stat().st_size > max_size_bytes:
            warn(f"File {downloaded.name} ({downloaded.stat().st_size} bytes) exceeds max size ({max_size_bytes} bytes). Skipping.")
            skipped += 1
            continue

        extract_dir = download_dir / f"{preset}_extracted"
        kernel_files = extract_kernel_files(downloaded, extract_dir)

        if not kernel_files:
            warn(f"No kernel files extracted for preset '{preset}'.")
            skipped += 1
            continue

        for sys_path in kernel_files:
            report_path = output_dir / f"{sys_path.stem}_vuln_report.txt"
            if args.skip_existing and report_path.exists():
                info(f"Report already exists, skipping: {report_path}")
                skipped += 1
                continue

            work_dir = Path(tempfile.mkdtemp(prefix=f"vuln_pipeline_nvidia_{preset}_{sys_path.stem}_"))
            try:
                result_path = process_single_driver(
                    sys_path, config, prompt, args, work_dir=work_dir
                )
                if result_path:
                    success += 1
                else:
                    failed += 1
            except Exception as exc:
                warn(f"Unhandled exception during processing of {sys_path}: {exc}")
                failed += 1
            finally:
                if not args.keep_work:
                    shutil.rmtree(work_dir, ignore_errors=True)

        time.sleep(1)
        if args.api_delay > 0:
            time.sleep(args.api_delay)

    print(f"\n{'='*60}")
    info("NVIDIA BATCH COMPLETE")
    info(f"Success : {success}")
    info(f"Failed  : {failed}")
    info(f"Skipped : {skipped}")
    info(f"Reports saved to: {output_dir}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Intel batch mode
# ---------------------------------------------------------------------------

def run_intel_batch(args) -> None:
    """Download and analyze ALL Intel presets one by one."""
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    presets = get_intel_presets()
    info(f"Found {len(presets)} Intel presets to process.")
    info("NOTE: Intel's website may block automated downloads (403).")
    info("      If downloads fail, use --driver-folder with manually downloaded packages.")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    download_dir = output_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    max_size_bytes = args.max_file_size_mb * 1024 * 1024

    success = 0
    failed = 0
    skipped = 0

    for idx, preset in enumerate(presets, start=1):
        print(f"\n{'='*60}")
        info(f"[{idx}/{len(presets)}] Processing Intel preset: {preset}")
        print(f"{'='*60}")

        downloaded = download_intel_preset(preset, download_dir)
        if downloaded is None:
            failed += 1
            continue

        if downloaded.stat().st_size > max_size_bytes:
            warn(f"File {downloaded.name} ({downloaded.stat().st_size} bytes) exceeds max size ({max_size_bytes} bytes). Skipping.")
            skipped += 1
            continue

        extract_dir = download_dir / f"{preset}_extracted"
        kernel_files = extract_kernel_files(downloaded, extract_dir)

        if not kernel_files:
            warn(f"No kernel files extracted for preset '{preset}'.")
            skipped += 1
            continue

        for sys_path in kernel_files:
            report_path = output_dir / f"{sys_path.stem}_vuln_report.txt"
            if args.skip_existing and report_path.exists():
                info(f"Report already exists, skipping: {report_path}")
                skipped += 1
                continue

            work_dir = Path(tempfile.mkdtemp(prefix=f"vuln_pipeline_intel_{preset}_{sys_path.stem}_"))
            try:
                result_path = process_single_driver(
                    sys_path, config, prompt, args, work_dir=work_dir
                )
                if result_path:
                    success += 1
                else:
                    failed += 1
            except Exception as exc:
                warn(f"Unhandled exception during processing of {sys_path}: {exc}")
                failed += 1
            finally:
                if not args.keep_work:
                    shutil.rmtree(work_dir, ignore_errors=True)

        time.sleep(1)
        if args.api_delay > 0:
            time.sleep(args.api_delay)

    print(f"\n{'='*60}")
    info("INTEL BATCH COMPLETE")
    info(f"Success : {success}")
    info(f"Failed  : {failed}")
    info(f"Skipped : {skipped}")
    info(f"Reports saved to: {output_dir}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Single mode
# ---------------------------------------------------------------------------

def run_single(args) -> None:
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    work_dir = Path(tempfile.mkdtemp(prefix="vuln_pipeline_"))
    info(f"Working directory: {work_dir}")

    # --- Phase 1: Obtain driver ---
    if args.driver_file:
        driver_path = Path(args.driver_file).expanduser().resolve()
        if not driver_path.exists():
            error(f"Driver file not found: {driver_path}")
        if driver_path.suffix.lower() == ".sys":
            kernel_files = [driver_path]
            info(f"Using local kernel file: {driver_path}")
        else:
            info(f"Local file is not .sys; treating as installer: {driver_path}")
            extract_dir = work_dir / "extracted"
            kernel_files = extract_kernel_files(driver_path, extract_dir)
            if not kernel_files:
                error("No kernel .sys files found in the provided file.")
    elif args.amd_preset:
        download_dir = work_dir / "downloads"
        downloaded = download_amd_preset(args.amd_preset, download_dir)
        if downloaded is None:
            error(f"Failed to download preset: {args.amd_preset}")

        extract_dir = work_dir / "extracted"
        kernel_files = extract_kernel_files(downloaded, extract_dir)
        if not kernel_files:
            warn("No kernel .sys files found in the downloaded package.")
            warn("AMD web installers do not contain kernel driver files.")
            warn("Use --scan-local-drivers or --scan-driverstore for real kernel drivers.")
            error("Exiting.")
    elif args.nvidia_preset:
        download_dir = work_dir / "downloads"
        downloaded = download_nvidia_preset(args.nvidia_preset, download_dir)
        if downloaded is None:
            error(f"Failed to download preset: {args.nvidia_preset}")

        extract_dir = work_dir / "extracted"
        kernel_files = extract_kernel_files(downloaded, extract_dir)
        if not kernel_files:
            warn("No kernel .sys files found in the downloaded package.")
            error("Exiting.")
    elif args.intel_preset:
        download_dir = work_dir / "downloads"
        downloaded = download_intel_preset(args.intel_preset, download_dir)
        if downloaded is None:
            error(f"Failed to download preset: {args.intel_preset}")

        extract_dir = work_dir / "extracted"
        kernel_files = extract_kernel_files(downloaded, extract_dir)
        if not kernel_files:
            warn("No kernel .sys files found in the downloaded package.")
            error("Exiting.")
    else:
        error("Specify one of: --driver-file, --amd-preset, --nvidia-preset, or --intel-preset.")

    # --- Process each kernel file ---
    reports: list[tuple[Path, Path]] = []
    for sys_path in kernel_files:
        info(f"\n>>> Processing kernel file: {sys_path.name}")
        result_path = process_single_driver(sys_path, config, prompt, args, work_dir=work_dir)
        if result_path:
            reports.append((sys_path, result_path))

    # --- Cleanup ---
    if not args.keep_work:
        shutil.rmtree(work_dir, ignore_errors=True)
        info("Cleaned up working directory.")
    else:
        info(f"Kept working directory: {work_dir}")

    # --- Summary ---
    if reports:
        print(f"\n{'='*60}")
        print("PIPELINE COMPLETE")
        for sys_path, report_path in reports:
            print(f"  Driver : {sys_path}")
            print(f"  Report : {report_path}")
        print(f"{'='*60}")
    else:
        error("Pipeline failed. Check warnings above.")


# ---------------------------------------------------------------------------
# Folder scan mode (manual driver packages)
# ---------------------------------------------------------------------------

def run_folder_scan(args) -> None:
    """Scan a folder of manually downloaded driver packages, extract .sys files, analyze all."""
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    folder = Path(args.driver_folder).expanduser().resolve()
    if not folder.exists() or not folder.is_dir():
        error(f"Folder not found: {folder}")

    # Find all potential driver packages
    extensions = {".exe", ".zip", ".7z", ".cab", ".msi", ".rar"}
    packages = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in extensions]
    info(f"Found {len(packages)} driver package(s) in {folder}")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0

    for pkg_idx, package in enumerate(packages, start=1):
        print(f"\n{'='*60}")
        info(f"[{pkg_idx}/{len(packages)}] Extracting package: {package.name}")
        print(f"{'='*60}")

        extract_dir = output_dir / "extracted" / package.stem
        kernel_files = extract_kernel_files(package, extract_dir)

        if not kernel_files:
            warn(f"No .sys files found in {package.name}. Skipping.")
            skipped += 1
            continue

        for sys_path in kernel_files:
            report_path = output_dir / f"{sys_path.stem}_vuln_report.txt"
            if args.skip_existing and report_path.exists():
                info(f"Report already exists, skipping: {report_path}")
                skipped += 1
                continue

            info(f"\n>>> Processing kernel file: {sys_path.name} (from {package.name})")
            work_dir = Path(tempfile.mkdtemp(prefix=f"vuln_pipeline_{package.stem}_{sys_path.stem}_"))
            try:
                result_path = process_single_driver(
                    sys_path, config, prompt, args, work_dir=work_dir
                )
                if result_path:
                    success += 1
                else:
                    failed += 1
            except Exception as exc:
                warn(f"Unhandled exception during processing of {sys_path}: {exc}")
                failed += 1
            finally:
                if not args.keep_work:
                    shutil.rmtree(work_dir, ignore_errors=True)

        time.sleep(1)
        if args.api_delay > 0:
            time.sleep(args.api_delay)

    print(f"\n{'='*60}")
    info("FOLDER SCAN COMPLETE")
    info(f"Packages : {len(packages)}")
    info(f"Success  : {success}")
    info(f"Failed   : {failed}")
    info(f"Skipped  : {skipped}")
    info(f"Reports saved to: {output_dir}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Local driver scan mode
# ---------------------------------------------------------------------------

def scan_driverstore() -> list[Path]:
    """Find all .sys files in Windows DriverStore."""
    sys_files: list[Path] = []
    base = Path("C:/Windows/System32/DriverStore/FileRepository")
    if base.exists():
        for f in base.rglob("*"):
            if f.is_file() and f.suffix.lower() == ".sys":
                sys_files.append(f)
    # Deduplicate by inode
    seen: set[int] = set()
    unique: list[Path] = []
    for p in sys_files:
        try:
            inode = p.stat().st_ino
            if inode not in seen:
                seen.add(inode)
                unique.append(p)
        except Exception:
            unique.append(p)
    unique.sort(key=lambda p: p.stat().st_size, reverse=True)
    return unique


def scan_active_drivers() -> list[Path]:
    """Find all .sys files in C:/Windows/System32/drivers."""
    sys_files: list[Path] = []
    base = Path("C:/Windows/System32/drivers")
    if base.exists():
        for f in base.iterdir():
            if f.is_file() and f.suffix.lower() == ".sys":
                sys_files.append(f)
    sys_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    return sys_files


def scan_local_kernel_files() -> list[Path]:
    """Find all .sys kernel driver files in standard Windows driver directories."""
    driverstore = scan_driverstore()
    active = scan_active_drivers()
    # Merge, preferring active drivers (they're at the top)
    seen_names = {p.name.lower() for p in active}
    combined = list(active)
    for p in driverstore:
        if p.name.lower() not in seen_names:
            combined.append(p)
    return combined


def run_local_scan(args) -> None:
    """Scan local system for kernel drivers and analyze them all."""
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    kernel_files = scan_local_kernel_files()
    info(f"Found {len(kernel_files)} unique kernel .sys file(s) on this system.")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0

    for idx, sys_path in enumerate(kernel_files, start=1):
        print(f"\n{'='*60}")
        info(f"[{idx}/{len(kernel_files)}] Processing: {sys_path.name}")
        print(f"{'='*60}")

        report_path = output_dir / f"{sys_path.stem}_vuln_report.txt"
        if args.skip_existing and report_path.exists():
            info(f"Report already exists, skipping: {report_path}")
            skipped += 1
            continue

        work_dir = Path(tempfile.mkdtemp(prefix=f"vuln_pipeline_{sys_path.stem}_"))
        try:
            result_path = process_single_driver(
                sys_path, config, prompt, args, work_dir=work_dir
            )
            if result_path:
                success += 1
            else:
                failed += 1
        except Exception as exc:
            warn(f"Unhandled exception during processing of {sys_path}: {exc}")
            failed += 1
        finally:
            if not args.keep_work:
                shutil.rmtree(work_dir, ignore_errors=True)

        # Rate limit between drivers
        time.sleep(1)
        if args.api_delay > 0:
            time.sleep(args.api_delay)

    print(f"\n{'='*60}")
    info("LOCAL SCAN COMPLETE")
    info(f"Success : {success}")
    info(f"Failed  : {failed}")
    info(f"Skipped : {skipped}")
    info(f"Reports saved to: {output_dir}")
    print(f"{'='*60}")


def run_driverstore_scan(args) -> None:
    """Scan Windows DriverStore for all kernel drivers and analyze them."""
    config = load_json(CONFIG_PATH)
    prompt = load_text(PROMPT_PATH)

    kernel_files = scan_driverstore()
    info(f"Found {len(kernel_files)} kernel .sys file(s) in DriverStore.")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0

    for idx, sys_path in enumerate(kernel_files, start=1):
        print(f"\n{'='*60}")
        info(f"[{idx}/{len(kernel_files)}] Processing: {sys_path.name}")
        print(f"{'='*60}")

        report_path = output_dir / f"{sys_path.stem}_vuln_report.txt"
        if args.skip_existing and report_path.exists():
            info(f"Report already exists, skipping: {report_path}")
            skipped += 1
            continue

        work_dir = Path(tempfile.mkdtemp(prefix=f"vuln_pipeline_{sys_path.stem}_"))
        try:
            result_path = process_single_driver(
                sys_path, config, prompt, args, work_dir=work_dir
            )
            if result_path:
                success += 1
            else:
                failed += 1
        except Exception as exc:
            warn(f"Unhandled exception during processing of {sys_path}: {exc}")
            failed += 1
        finally:
            if not args.keep_work:
                shutil.rmtree(work_dir, ignore_errors=True)

        time.sleep(1)
        if args.api_delay > 0:
            time.sleep(args.api_delay)

    print(f"\n{'='*60}")
    info("DRIVERSTORE SCAN COMPLETE")
    info(f"Success : {success}")
    info(f"Failed  : {failed}")
    info(f"Skipped : {skipped}")
    info(f"Reports saved to: {output_dir}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vuln_pipeline.py",
        description="Windows Driver -> Ghidra -> Kimi AI Vulnerability Pipeline",
    )

    # Mode selection
    p.add_argument(
        "--driver-file",
        help="Path to an existing driver binary (.sys) or installer package",
    )
    p.add_argument(
        "--amd-preset",
        help="AMD product preset to download (e.g. rx7800xt, ryzen97950x). NOTE: AMD provides web installers only.",
    )
    p.add_argument(
        "--download-all",
        action="store_true",
        help="Download and analyze ALL AMD presets one-by-one (web installers, may not contain .sys files)",
    )
    p.add_argument(
        "--scan-local-drivers",
        action="store_true",
        help="Scan C:\\Windows\\System32\\drivers + DriverStore for all .sys files and analyze them (RECOMMENDED)",
    )
    p.add_argument(
        "--scan-driverstore",
        action="store_true",
        help="Scan C:\\Windows\\System32\\DriverStore\\FileRepository for all .sys files and analyze them",
    )
    p.add_argument(
        "--driver-folder",
        help="Path to a folder containing manually downloaded driver packages (.exe, .zip, .7z, .cab). Extracts .sys from all packages and analyzes them.",
    )
    p.add_argument(
        "--nvidia-preset",
        help="NVIDIA product preset to download (e.g. rtx4090, rtx3080, gtx1060). Downloads FULL installer with real .sys files.",
    )
    p.add_argument(
        "--intel-preset",
        help="Intel product preset to download (e.g. graphics, wifi, chipset). NOTE: Intel may block automated downloads.",
    )
    p.add_argument(
        "--download-nvidia-all",
        action="store_true",
        help="Download and analyze ALL NVIDIA presets one-by-one (full installers with .sys files)",
    )
    p.add_argument(
        "--download-intel-all",
        action="store_true",
        help="Download and analyze ALL Intel presets one-by-one (may be blocked by Intel anti-bot)",
    )

    # Output options
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output report .txt path (single mode only)",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save reports (default: current directory)",
    )

    # Limits & safety
    p.add_argument(
        "--ghidra-timeout",
        type=int,
        default=0,
        help="Timeout for Ghidra decompilation in seconds. 0 = no limit (default: 0)",
    )
    p.add_argument(
        "--api-timeout",
        type=int,
        default=0,
        help="Timeout for Kimi API requests in seconds. 0 = no limit (default: 0)",
    )
    p.add_argument(
        "--max-chars",
        type=int,
        default=100_000,
        help="Max characters of pseudo-C to send to Kimi (default: 100000)",
    )
    p.add_argument(
        "--max-file-size-mb",
        type=int,
        default=100,
        help="Skip downloaded files larger than this many MB (default: 100)",
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip drivers that already have a report file",
    )
    p.add_argument(
        "--api-delay",
        type=int,
        default=5,
        help="Seconds to wait between API calls in batch mode (default: 5)",
    )

    # Misc
    p.add_argument(
        "--keep-work",
        action="store_true",
        help="Keep temporary working directories for inspection",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate mutually-exclusive-ish modes
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
    if mode_count == 0:
        parser.error("Specify one mode. Use --help for available options.")
    if mode_count > 1:
        parser.error("All mode flags are mutually exclusive.")

    if args.download_all:
        run_batch(args)
    elif args.download_nvidia_all:
        run_nvidia_batch(args)
    elif args.download_intel_all:
        run_intel_batch(args)
    elif args.scan_local_drivers:
        run_local_scan(args)
    elif args.scan_driverstore:
        run_driverstore_scan(args)
    elif args.driver_folder:
        run_folder_scan(args)
    else:
        run_single(args)


if __name__ == "__main__":
    main()
