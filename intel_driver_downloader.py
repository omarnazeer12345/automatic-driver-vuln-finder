#!/usr/bin/env python3
"""
Intel Driver Downloader
Scrapes Intel's download center and downloads latest official drivers.

Usage:
    python intel_driver_downloader.py --product graphics
    python intel_driver_downloader.py --all
    python intel_driver_downloader.py --list

Dependency-free (uses only the Python standard library).
"""

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# ── Intel ────────────────────────────────────────────────────────────────────
# Download page URLs for key Intel driver categories
INTEL_PRODUCTS = {
    # Graphics / Display
    "graphics":        "https://www.intel.com/content/www/us/en/download/19792/intel-graphics-windows-dch-drivers.html",
    "graphics-beta":   "https://www.intel.com/content/www/us/en/download/19344/intel-graphics-beta-windows-dch-drivers.html",

    # Network / Ethernet
    "ethernet-i225":   "https://www.intel.com/content/www/us/en/download/18293/intel-network-adapter-driver-for-windows-10.html",
    "ethernet-e810":   "https://www.intel.com/content/www/us/en/download/19694/intel-network-adapter-driver-for-e810-series-devices.html",

    # WiFi / Bluetooth
    "wifi":            "https://www.intel.com/content/www/us/en/download/19351/intel-wireless-bluetooth-for-windows-10-and-windows-11.html",
    "wifi-ax":         "https://www.intel.com/content/www/us/en/download/18651/intel-wireless-wi-fi-drivers-for-windows-10-and-windows-11.html",

    # Chipset / SATA / RST
    "chipset":         "https://www.intel.com/content/www/us/en/download/19347/intel-chipset-device-software-for-windows-10.html",
    "rst":             "https://www.intel.com/content/www/us/en/download/19727/intel-rapid-storage-technology-driver-installation-software.html",
    "sata":            "https://www.intel.com/content/www/us/en/download/19727/intel-rapid-storage-technology-driver-installation-software.html",

    # Management Engine
    "me":              "https://www.intel.com/content/www/us/en/download/6826/intel-management-engine-drivers.html",

    # Audio
    "audio":           "https://www.intel.com/content/www/us/en/download/19752/intel-smart-sound-technology-intel-sst-driver.html",
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
            ),
            "Accept": "*/*",
        },
    )

    with urllib.request.urlopen(req, timeout=300) as response:
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


def fetch_intel_driver(page_url: str) -> dict:
    """Scrape an Intel download page and return driver metadata."""
    req = urllib.request.Request(
        page_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # Intel download pages typically have a direct download link in a button or link
    # Look for .exe download URLs
    matches = re.findall(r'href="(https?://[^"]+\.exe)"', html)
    if not matches:
        # Try data-href or other attributes
        matches = re.findall(r'data-href="(https?://[^"]+\.exe)"', html)
    if not matches:
        # Look for download manager links
        matches = re.findall(r'(https?://downloadmirror\.intel\.com/[^"\'\s]+\.exe)', html)
    if not matches:
        # Look for any intel download URL ending in .exe
        matches = re.findall(r'(https?://[^"\'\s]*intel\.com/[^"\'\s]*\.exe)', html)

    if not matches:
        raise RuntimeError("No .exe driver link found on the Intel download page.")

    driver_url = matches[0]
    filename = os.path.basename(urllib.parse.urlparse(driver_url).path)

    # Try to extract version from filename or page
    version_match = re.search(r"(\d+(?:\.\d+){1,3})", filename)
    version = version_match.group(1) if version_match else "Unknown"

    return {
        "name": filename,
        "version": version,
        "date": "Unknown",
        "url": driver_url,
        "size": "Unknown",
    }


def list_products() -> None:
    """Print available preset products."""
    print("Available Intel presets:")
    for key, val in sorted(INTEL_PRODUCTS.items()):
        print(f"  {key:<15} -> {val}")


def download_one(product_key: str, out_dir: Path) -> bool:
    """Download a single driver. Returns True on success."""
    try:
        page_url = INTEL_PRODUCTS[product_key]
        print_info(f"[{product_key}] Scraping Intel download page ...")
        driver = fetch_intel_driver(page_url)

        print(f"  Driver:  {driver['name']}")
        print(f"  Version: {driver['version']}")
        print(f"  Date:    {driver['date']}")
        print(f"  URL:     {driver['url']}")

        filename = os.path.basename(urllib.parse.urlparse(driver["url"]).path)
        if not filename:
            filename = f"intel_{product_key}_{driver['version']}.exe"
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="intel_driver_downloader.py",
        description="Download latest Intel drivers.",
    )
    parser.add_argument("--product", help="Intel product preset (e.g. graphics, wifi, chipset)")
    parser.add_argument("--output-dir", default=".", help="Directory to save downloaded files")
    parser.add_argument("--all", action="store_true", help="Download ALL Intel presets one-by-one")
    parser.add_argument("--list", action="store_true", help="List available presets and exit")
    args = parser.parse_args()

    if args.list:
        list_products()
        return

    out_dir = Path(args.output_dir).expanduser().resolve()

    if args.all:
        print_info("Starting batch download for ALL Intel presets")
        for key in sorted(INTEL_PRODUCTS.keys()):
            download_one(key, out_dir)
            time.sleep(1)
        print_info("Batch download complete.")
        return

    if args.product:
        product = args.product.lower()
        if product not in INTEL_PRODUCTS:
            print_error(f"Unknown preset: {product}")
            list_products()
            sys.exit(1)
        if not download_one(product, out_dir):
            sys.exit(1)
        return

    parser.error("Specify --product, --all, or --list.")


if __name__ == "__main__":
    main()
