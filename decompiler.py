#!/usr/bin/env python3
r"""
Ghidra Binary Decompiler — Python wrapper
Turns a compiled binary (ELF, PE, Mach-O, etc.) into pseudo-C via Ghidra headless mode.

Usage:
    python decompiler.py <binary_file> [options]
    python decompiler.py --help

Requirements:
    - Ghidra installed on your system (https://ghidra-sre.org)
    - Java 17+ (Ghidra bundles its own JDK on Windows, or use system Java)

Example:
    python decompiler.py hello.exe
    python decompiler.py /path/to/firmware.bin --ghidra "C:\Program Files\Ghidra"
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

__version__ = "1.0.0"

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


def find_ghidra() -> Path | None:
    """Try common Ghidra installation paths on Windows."""
    candidates = []

    # Local bundled install (preferred — known working version)
    local_tools = Path(__file__).resolve().parent / "ghidra_tools"
    if local_tools.exists():
        for entry in local_tools.iterdir():
            if entry.is_dir() and "ghidra_11" in entry.name.lower():
                candidates.append(entry)

    # Environment variable takes priority
    env = os.environ.get("GHIDRA_INSTALL_DIR")
    if env:
        candidates.append(Path(env))

    # Common Windows locations
    progfiles = os.environ.get("ProgramFiles", r"C:\Program Files")
    progfiles_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local")

    for base in (progfiles, progfiles_x86, local_appdata, r"C:\ghidra", r"C:\tools"):
        if not base or "%" in base:
            continue
        base_path = Path(base)
        if not base_path.exists():
            continue
        # Look for ghidra_* folders
        for entry in base_path.iterdir():
            if entry.is_dir() and "ghidra" in entry.name.lower():
                candidates.append(entry)

    # Pick the one with the newest mtime that has support/analyzeHeadless.bat
    valid = []
    for c in candidates:
        bat = c / "support" / "analyzeHeadless.bat"
        if bat.exists():
            valid.append((c, bat.stat().st_mtime))

    if valid:
        valid.sort(key=lambda x: x[1], reverse=True)
        return valid[0][0]
    return None


def locate_analyze_headless(ghidra_dir: Path) -> Path:
    bat = ghidra_dir / "support" / "analyzeHeadless.bat"
    sh = ghidra_dir / "support" / "analyzeHeadless"
    if sys.platform == "win32" and bat.exists():
        return bat
    if sh.exists():
        return sh
    error(
        f"Cannot find analyzeHeadless in {ghidra_dir / 'support'}. "
        "Is Ghidra fully installed?"
    )


def find_bundled_jre(ghidra_dir: Path) -> Path | None:
    """Look for a JRE/JDK sibling directory next to the Ghidra folder."""
    parent = ghidra_dir.parent
    for entry in parent.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name.lower()
        if "jdk" in name or "jre" in name:
            java_exe = entry / "bin" / "java.exe"
            if java_exe.exists():
                return entry
    return None


def download_ghidra(dest_zip: Path) -> None:
    """
    Download the latest public Ghidra release from GitHub.
    This is a fallback if no local install is found.
    """
    # NOTE: GitHub API or direct release URL. We use the NSA Ghidra releases page.
    # A stable direct link for 11.0.3 (adjust as needed):
    url = (
        "https://github.com/NationalSecurityAgency/ghidra/releases/download/"
        "Ghidra_11.0.3_build/ghidra_11.0.3_PUBLIC_20240410.zip"
    )
    info(f"Downloading Ghidra from GitHub ...")
    info(f"URL: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        ),
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=None) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 256 * 1024
            with open(dest_zip, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        bar_len = 40
                        filled = downloaded * bar_len // total
                        bar = "#" * filled + "-" * (bar_len - filled)
                        print(
                            f"\r[{bar}] {pct}% {downloaded}/{total} bytes",
                            end="",
                            flush=True,
                        )
            print()
    except Exception as exc:
        if dest_zip.exists():
            dest_zip.unlink()
        error(f"Download failed: {exc}")


def extract_ghidra(zip_path: Path, extract_to: Path) -> Path:
    info("Extracting Ghidra ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(path=extract_to)
    # Find the extracted folder
    for entry in extract_to.iterdir():
        if entry.is_dir() and "ghidra" in entry.name.lower():
            return entry
    error("Could not locate extracted Ghidra directory.")


def ensure_ghidra(args) -> Path:
    """Return path to Ghidra root, installing if necessary."""
    if args.ghidra:
        p = Path(args.ghidra).expanduser().resolve()
        if not p.exists():
            error(f"Provided Ghidra path does not exist: {p}")
        return p

    found = find_ghidra()
    if found:
        info(f"Found existing Ghidra installation: {found}")
        return found

    if args.auto_install:
        cache = Path(tempfile.gettempdir()) / "ghidra_cache"
        cache.mkdir(parents=True, exist_ok=True)
        zip_path = cache / "ghidra.zip"
        if not zip_path.exists():
            download_ghidra(zip_path)
        else:
            info(f"Using cached Ghidra zip: {zip_path}")
        extracted = extract_ghidra(zip_path, cache)
        info(f"Ghidra extracted to: {extracted}")
        return extracted

    error(
        "Ghidra not found. Please install Ghidra from https://ghidra-sre.org\n"
        "or pass --ghidra <path> or use --auto-install to download it automatically."
    )


# ---------------------------------------------------------------------------
# Core decompilation logic
# ---------------------------------------------------------------------------

def decompile_binary(binary_path: Path, ghidra_dir: Path, output_path: Path, args) -> None:
    """
    Run Ghidra headless to import the binary and decompile all functions.
    """
    analyze_headless = locate_analyze_headless(ghidra_dir)
    script_dir = Path(__file__).resolve().parent
    jython_script = script_dir / "ghidra_decompile.py"
    if not jython_script.exists():
        error(f"Missing Jython post-script: {jython_script}")

    # Create a temporary Ghidra project directory
    proj_dir = Path(tempfile.mkdtemp(prefix="ghidra_proj_"))
    proj_name = "decomp"

    # Output file path passed to the Jython script via a temp marker file
    marker = Path(tempfile.mktemp(prefix="ghidra_out_", suffix=".txt"))

    cmd = [
        str(analyze_headless),
        str(proj_dir),
        proj_name,
        "-import",
        str(binary_path),
        "-postScript",
        str(jython_script),
        "-scriptPath",
        str(script_dir),
        "-deleteProject",
    ]

    # Auto-analysis runs by default so functions are identified before post-script

    info("Running Ghidra headless decompiler ...")
    info(f"Command: {' '.join(cmd)}")

    env = os.environ.copy()
    # Use bundled JRE if available
    bundled_jre = find_bundled_jre(ghidra_dir)
    if bundled_jre:
        info(f"Using bundled JRE: {bundled_jre}")
        env["JAVA_HOME"] = str(bundled_jre)
        env["PATH"] = str(bundled_jre / "bin") + os.pathsep + env.get("PATH", "")

    # Tell the Jython script where to write results
    env["_GHIDRA_DECOMP_OUT"] = str(output_path)
    env["_GHIDRA_DECOMP_MARKER"] = str(marker)
    if args.functions:
        env["_GHIDRA_DECOMP_FUNCS"] = args.functions

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=not args.verbose,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout if args.timeout > 0 else None,
        )
    except subprocess.TimeoutExpired:
        error(f"Ghidra did not finish within {args.timeout} seconds.")
    elapsed = time.time() - start

    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, file=sys.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        error(f"Ghidra analyzeHeadless exited with code {proc.returncode}.")

    info(f"Ghidra finished in {elapsed:.1f}s.")

    if not output_path.exists():
        error("Decompilation output file was not created.")

    info(f"Pseudo-C saved to: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="decompiler.py",
        description="Decompile a binary to pseudo-C using Ghidra.",
    )
    p.add_argument("binary", help="Path to the binary to decompile")
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output C file path (default: <binary>.c)",
    )
    p.add_argument(
        "--ghidra",
        default=None,
        help="Path to Ghidra installation directory (e.g. C:\\Program Files\\Ghidra\\ghidra_11.0.3_PUBLIC)",
    )
    p.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically download and extract Ghidra if not found locally",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Maximum seconds to wait for Ghidra. 0 = no limit (default: 0)",
    )
    p.add_argument(
        "--functions",
        default="",
        help='Comma-separated list of function names to decompile (default: all exported + entry)',
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Show Ghidra headless stdout/stderr in real time",
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

    binary = Path(args.binary).expanduser().resolve()
    if not binary.exists():
        error(f"Binary not found: {binary}")

    output = Path(args.output) if args.output else binary.with_suffix(".c")
    output = output.expanduser().resolve()

    ghidra_dir = ensure_ghidra(args)
    decompile_binary(binary, ghidra_dir, output, args)

    # Quick stats
    lines = output.read_text(encoding="utf-8", errors="replace").count("\n")
    info(f"Output lines: {lines}")
    print(f"\nSuccess! Pseudo-C written to: {output}")


if __name__ == "__main__":
    main()
