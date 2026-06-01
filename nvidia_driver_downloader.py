#!/usr/bin/env python3
"""
NVIDIA Driver Downloader
Queries NVIDIA's API and downloads the latest official NVIDIA drivers.

Usage:
    python nvidia_driver_downloader.py --product rtx4090
    python nvidia_driver_downloader.py --all
    python nvidia_driver_downloader.py --list
    python nvidia_driver_downloader.py --psid 129 --pfid 967

The script is dependency-free (uses only the Python standard library).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# ── NVIDIA ────────────────────────────────────────────────────────────────────
NVIDIA_API = (
    "https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/services/"
    "AjaxDriverService.php"
)

NVIDIA_PRODUCTS = {
    # RTX 40-series
    "rtx4090":   {"psid": 129, "pfid": 967, "name": "GeForce RTX 4090"},
    "rtx4080":   {"psid": 129, "pfid": 966, "name": "GeForce RTX 4080"},
    "rtx4070ti": {"psid": 129, "pfid": 995, "name": "GeForce RTX 4070 Ti"},
    "rtx4070":   {"psid": 129, "pfid": 993, "name": "GeForce RTX 4070"},
    "rtx4060ti": {"psid": 129, "pfid": 1038,"name": "GeForce RTX 4060 Ti"},
    "rtx4060":   {"psid": 129, "pfid": 1037,"name": "GeForce RTX 4060"},
    # RTX 30-series
    "rtx3090ti": {"psid": 127, "pfid": 921, "name": "GeForce RTX 3090 Ti"},
    "rtx3090":   {"psid": 127, "pfid": 890, "name": "GeForce RTX 3090"},
    "rtx3080ti": {"psid": 127, "pfid": 922, "name": "GeForce RTX 3080 Ti"},
    "rtx3080":   {"psid": 127, "pfid": 889, "name": "GeForce RTX 3080"},
    "rtx3070ti": {"psid": 127, "pfid": 923, "name": "GeForce RTX 3070 Ti"},
    "rtx3070":   {"psid": 127, "pfid": 888, "name": "GeForce RTX 3070"},
    "rtx3060ti": {"psid": 127, "pfid": 924, "name": "GeForce RTX 3060 Ti"},
    "rtx3060":   {"psid": 127, "pfid": 912, "name": "GeForce RTX 3060"},
    "rtx3050":   {"psid": 127, "pfid": 976, "name": "GeForce RTX 3050"},
    # RTX 20-series
    "rtx2080ti": {"psid": 120, "pfid": 858, "name": "GeForce RTX 2080 Ti"},
    "rtx2080":   {"psid": 120, "pfid": 859, "name": "GeForce RTX 2080"},
    "rtx2060":   {"psid": 120, "pfid": 861, "name": "GeForce RTX 2060"},
    # GTX 16-series
    "gtx1660ti": {"psid": 134, "pfid": 847, "name": "GeForce GTX 1660 Ti"},
    # GTX 10-series
    "gtx1080ti": {"psid": 101, "pfid": 816, "name": "GeForce GTX 1080 Ti"},
    "gtx1060":   {"psid": 101, "pfid": 845, "name": "GeForce GTX 1060"},
}


def print_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def print_info(msg: str) -> None:
    print(f"[INFO]  {msg}")


def print_success(msg: str) -> None:
    print(f"[OK]    {msg}")


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """Download *url* to *dest* with a simple text progress bar."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(req) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        dest.parent.mkdir(parents=True, exist_ok=True)

        with dest.open("wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total:
                    pct = downloaded / total * 100
                    bar_len = 30
                    filled = int(bar_len * downloaded // total)
                    bar = "#" * filled + "-" * (bar_len - filled)
                    print(
                        f"\r  {bar} {pct:5.1f}%  {downloaded:,}/{total:,} bytes",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"\r  {downloaded:,} bytes downloaded", end="", flush=True)

    print()  # newline after progress bar


def fetch_nvidia_driver(psid: int, pfid: int, osid: int) -> dict:
    """Query NVIDIA's API and return driver metadata."""
    params = urllib.parse.urlencode(
        {
            "func": "DriverManualLookup",
            "psid": psid,
            "pfid": pfid,
            "osID": osid,
            "languageCode": 1033,
            "isWHQL": 1,
            "dch": 1,
            "sort1": 0,
            "numberOfResults": 1,
        }
    )
    url = f"{NVIDIA_API}?{params}"

    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("Success") != "1" or not data.get("IDS"):
        raise RuntimeError("NVIDIA API returned no driver results.")

    info = data["IDS"][0]["downloadInfo"]
    return {
        "name": urllib.parse.unquote(info.get("Name", "NVIDIA Driver")),
        "version": info.get("Version", "Unknown"),
        "date": info.get("ReleaseDateTime", "Unknown"),
        "url": info["DownloadURL"],
        "size": info.get("DownloadURLFileSize", "Unknown"),
    }


def list_products() -> None:
    """Print available preset products."""
    print("Available NVIDIA presets:")
    for key, val in sorted(NVIDIA_PRODUCTS.items()):
        print(f"  {key:<13} -> {val['name']} (psid={val['psid']}, pfid={val['pfid']})")


def download_one(product_key: str, out_dir: Path, osid: int) -> bool:
    """Download a single driver. Returns True on success."""
    try:
        preset = NVIDIA_PRODUCTS[product_key]
        print_info(f"[{product_key}] Querying NVIDIA driver for {preset['name']} ...")
        driver = fetch_nvidia_driver(preset["psid"], preset["pfid"], osid)

        print(f"  Driver:  {driver['name']}")
        print(f"  Version: {driver['version']}")
        print(f"  Date:    {driver['date']}")
        print(f"  Size:    {driver['size']}")

        filename = os.path.basename(urllib.parse.urlparse(driver["url"]).path)
        if not filename:
            filename = f"nvidia_{product_key}_{driver['version']}.exe"
        dest = out_dir / filename

        if dest.exists():
            print_info(f"[{product_key}] Already exists, skipping: {dest}")
            return True

        print_info(f"[{product_key}] Downloading to {dest} ...")
        download_file(driver["url"], dest)
        print_success(f"[{product_key}] Saved: {dest}")
        return True

    except urllib.error.HTTPError as exc:
        print_error(f"[{product_key}] HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        print_error(f"[{product_key}] Network error: {exc.reason}")
    except RuntimeError as exc:
        print_error(f"[{product_key}] {exc}")
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print_error(f"[{product_key}] Unexpected error: {exc}")

    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the latest NVIDIA GPU drivers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --product rtx4090
  %(prog)s --all
  %(prog)s --list
  %(prog)s --psid 129 --pfid 967
""",
    )
    parser.add_argument("--product", help="Preset product key (e.g. rtx4090)")
    parser.add_argument("--psid", type=int, help="NVIDIA Product Series ID (overrides preset)")
    parser.add_argument("--pfid", type=int, help="NVIDIA Product ID (overrides preset)")
    parser.add_argument("--osid", type=int, default=57,
                        help="NVIDIA OS ID (default: 57 for Windows 10/11 64-bit)")
    parser.add_argument("--output-dir", default="nvidia_drivers",
                        help="Directory to save the driver(s) (default: ./nvidia_drivers)")
    parser.add_argument("--list", action="store_true",
                        help="List available preset products and exit")
    parser.add_argument("--all", action="store_true",
                        help="Download drivers for ALL presets")

    args = parser.parse_args()

    if args.list:
        list_products()
        return 0

    out_dir = Path(args.output_dir)

    # ── Batch mode (--all) ──────────────────────────────────────────────────────
    if args.all:
        if args.product or args.psid is not None or args.pfid is not None:
            print_error("--all cannot be combined with --product, --psid, or --pfid.")
            return 1

        success = 0
        failed = 0

        print(f"\n{'='*60}")
        print_info("Starting batch download for ALL NVIDIA presets")
        print(f"{'='*60}\n")

        for key in NVIDIA_PRODUCTS:
            if download_one(key, out_dir, args.osid):
                success += 1
            else:
                failed += 1
            time.sleep(1)  # be polite to the servers

        print(f"\n{'='*60}")
        print_info(f"Batch complete — {success} succeeded, {failed} failed.")
        return 0 if failed == 0 else 1

    # ── Single-driver mode ──────────────────────────────────────────────────────
    if args.psid is not None and args.pfid is not None:
        # Custom single NVIDIA driver
        try:
            print_info(f"Querying NVIDIA driver (psid={args.psid}, pfid={args.pfid}) ...")
            driver = fetch_nvidia_driver(args.psid, args.pfid, args.osid)
        except Exception as exc:
            print_error(str(exc))
            return 1
    elif args.product:
        if args.product.lower() not in NVIDIA_PRODUCTS:
            print_error(f"Unknown NVIDIA product '{args.product}'.")
            print("Run with --list to see available presets.")
            return 1
        if not download_one(args.product.lower(), out_dir, args.osid):
            return 1
        return 0
    else:
        print_error("NVIDIA requires --product or both --psid and --pfid (or use --all).")
        return 1

    # If we reach here it means we have a 'driver' dict from custom psid/pfid
    print(f"\n  Driver:  {driver['name']}")
    print(f"  Version: {driver['version']}")
    print(f"  Date:    {driver['date']}")
    print(f"  Size:    {driver['size']}")
    print(f"  URL:     {driver['url']}\n")

    filename = os.path.basename(urllib.parse.urlparse(driver["url"]).path)
    if not filename:
        filename = f"nvidia_driver_{driver['version']}.exe"
    dest = out_dir / filename

    if dest.exists():
        print_info(f"File already exists: {dest}")
        return 0

    try:
        print_info(f"Downloading to {dest} ...")
        download_file(driver["url"], dest)
        print_success(f"Saved: {dest}")
        return 0
    except urllib.error.HTTPError as exc:
        print_error(f"HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        print_error(f"Network error: {exc.reason}")
    except KeyboardInterrupt:
        print_error("Download cancelled by user.")
        return 130
    except Exception as exc:
        print_error(f"Unexpected error: {exc}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
