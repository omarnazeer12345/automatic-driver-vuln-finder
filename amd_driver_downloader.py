#!/usr/bin/env python3
"""
AMD Driver Downloader
Scrapes and downloads the latest official AMD drivers.

Usage:
    python amd_driver_downloader.py --product rx7900xtx
    python amd_driver_downloader.py --all
    python amd_driver_downloader.py --list

The script is dependency-free (uses only the Python standard library).
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


# ── AMD ───────────────────────────────────────────────────────────────────────
AMD_PRODUCTS = {
    # ═══════════════════════════════════════════════════════════════════════════
    # RX 7000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx7900xtx":       "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7900-xtx",
    "rx7900xt":        "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7900-xt",
    "rx7900gre":       "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7900-gre",
    "rx7800xt":        "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7800-xt",
    "rx7700xt":        "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7700-xt",
    "rx7600xt":        "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7600-xt",
    "rx7600":          "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7600",
    "rx7500xt":        "https://www.amd.com/en/support/graphics/amd-radeon-7000-series/amd-radeon-rx-7000-series/amd-radeon-rx-7500-xt",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 7000M Series (Mobile)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx7900m":         "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7900m",
    "rx7700s":         "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7700s",
    "rx7600mxt":       "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7600m-xt",
    "rx7600m":         "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7600m",
    "rx7600s":         "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7600s",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 6000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx6950xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6950-xt",
    "rx6900xtlc":      "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6900-xt-liquid-cooled-edition",
    "rx6900xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6900-xt",
    "rx6800xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6800-xt",
    "rx6800":          "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6800",
    "rx6750xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6750-xt",
    "rx6700xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6700-xt",
    "rx6650xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6650-xt",
    "rx6600xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6600-xt",
    "rx6600":          "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6600",
    "rx6500xt":        "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6500-xt",
    "rx6400":          "https://www.amd.com/en/support/graphics/amd-radeon-6000-series/amd-radeon-rx-6000-series/amd-radeon-rx-6400",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 6000M Series (Mobile)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx6800m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6800m",
    "rx6700m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6700m",
    "rx6600m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6600m",
    "rx6500m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6500m",
    "rx6300m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6300m",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 6000S Series (Thin & Light Laptop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx6800s":         "https://www.amd.com/en/support/graphics/amd-radeon-6000s-series/amd-radeon-rx-6000s-series/amd-radeon-rx-6800s",
    "rx6600s":         "https://www.amd.com/en/support/graphics/amd-radeon-6000s-series/amd-radeon-rx-6000s-series/amd-radeon-rx-6600s",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 5000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx5700xt":        "https://www.amd.com/en/support/graphics/amd-radeon-5000-series/amd-radeon-rx-5000-series/amd-radeon-rx-5700-xt",
    "rx5700":          "https://www.amd.com/en/support/graphics/amd-radeon-5000-series/amd-radeon-rx-5000-series/amd-radeon-rx-5700",
    "rx5600xt":        "https://www.amd.com/en/support/graphics/amd-radeon-5000-series/amd-radeon-rx-5000-series/amd-radeon-rx-5600-xt",
    "rx5500xt":        "https://www.amd.com/en/support/graphics/amd-radeon-5000-series/amd-radeon-rx-5000-series/amd-radeon-rx-5500-xt",
    "rx5500":          "https://www.amd.com/en/support/graphics/amd-radeon-5000-series/amd-radeon-rx-5000-series/amd-radeon-rx-5500",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 5000M Series (Mobile)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx5600m":         "https://www.amd.com/en/support/graphics/amd-radeon-5000m-series/amd-radeon-rx-5000m-series/amd-radeon-rx-5600m",
    "rx5500m":         "https://www.amd.com/en/support/graphics/amd-radeon-5000m-series/amd-radeon-rx-5000m-series/amd-radeon-rx-5500m",
    "rx5300m":         "https://www.amd.com/en/support/graphics/amd-radeon-5000m-series/amd-radeon-rx-5000m-series/amd-radeon-rx-5300m",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 500 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx590":           "https://www.amd.com/en/support/graphics/amd-radeon-500-series/amd-radeon-rx-500-series/amd-radeon-rx-590",
    "rx580":           "https://www.amd.com/en/support/graphics/amd-radeon-500-series/amd-radeon-rx-500-series/amd-radeon-rx-580",
    "rx570":           "https://www.amd.com/en/support/graphics/amd-radeon-500-series/amd-radeon-rx-500-series/amd-radeon-rx-570",
    "rx560":           "https://www.amd.com/en/support/graphics/amd-radeon-500-series/amd-radeon-rx-500-series/amd-radeon-rx-560",
    "rx550":           "https://www.amd.com/en/support/graphics/amd-radeon-500-series/amd-radeon-rx-500-series/amd-radeon-rx-550",
    "rx540":           "https://www.amd.com/en/support/graphics/amd-radeon-500-series/amd-radeon-rx-500-series/amd-radeon-rx-540",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 400 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx480":           "https://www.amd.com/en/support/graphics/amd-radeon-400-series/amd-radeon-rx-400-series/amd-radeon-rx-480",
    "rx470":           "https://www.amd.com/en/support/graphics/amd-radeon-400-series/amd-radeon-rx-400-series/amd-radeon-rx-470",
    "rx460":           "https://www.amd.com/en/support/graphics/amd-radeon-400-series/amd-radeon-rx-400-series/amd-radeon-rx-460",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 600 Series (Entry Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx640":           "https://www.amd.com/en/support/graphics/amd-radeon-600-series/amd-radeon-600-series/amd-radeon-rx-640",
    "rx630":           "https://www.amd.com/en/support/graphics/amd-radeon-600-series/amd-radeon-600-series/amd-radeon-rx-630",
    "rx620":           "https://www.amd.com/en/support/graphics/amd-radeon-600-series/amd-radeon-600-series/amd-radeon-rx-620",
    "rx610":           "https://www.amd.com/en/support/graphics/amd-radeon-600-series/amd-radeon-600-series/amd-radeon-rx-610",
    "r610":            "https://www.amd.com/en/support/graphics/amd-radeon-600-series/amd-radeon-600-series/amd-radeon-610",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX Vega & Radeon VII
    # ═══════════════════════════════════════════════════════════════════════════
    "rxvega64":        "https://www.amd.com/en/support/graphics/amd-radeon-rx-vega-series/amd-radeon-rx-vega-series/amd-radeon-rx-vega-64",
    "rxvega56":        "https://www.amd.com/en/support/graphics/amd-radeon-rx-vega-series/amd-radeon-rx-vega-series/amd-radeon-rx-vega-56",
    "radeonvii":       "https://www.amd.com/en/support/graphics/amd-radeon-vii/amd-radeon-vii/amd-radeon-vii",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon 600M Series (Integrated Laptop)
    # ═══════════════════════════════════════════════════════════════════════════
    "r680m":           "https://www.amd.com/en/support/graphics/amd-radeon-600m-series/amd-radeon-600m-series/amd-radeon-680m",
    "r660m":           "https://www.amd.com/en/support/graphics/amd-radeon-600m-series/amd-radeon-600m-series/amd-radeon-660m",
    "r610m":           "https://www.amd.com/en/support/graphics/amd-radeon-600m-series/amd-radeon-600m-series/amd-radeon-610m",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro W7000 Series (Workstation)
    # ═══════════════════════════════════════════════════════════════════════════
    "w7900":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7900",
    "w7800":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7800",
    "w7600":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7600",
    "w7500":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7500",
    "w7400":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7400",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro W6000 Series (Workstation)
    # ═══════════════════════════════════════════════════════════════════════════
    "w6800":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000-series/amd-radeon-pro-w6800",
    "w6600":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000-series/amd-radeon-pro-w6600",
    "w6400":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000-series/amd-radeon-pro-w6400",
    "w6300":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000-series/amd-radeon-pro-w6300",
    "w6000":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000-series/amd-radeon-pro-w6000",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro W5000 Series (Workstation)
    # ═══════════════════════════════════════════════════════════════════════════
    "w5700":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5700",
    "w5600":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5600",
    "w5500":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5500",
    "w5500x":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5500x",
    "w5500m":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5500m",
    "w5300":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5300",
    "w5100":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000-series/amd-radeon-pro-w5100",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro W4000 Series (Workstation)
    # ═══════════════════════════════════════════════════════════════════════════
    "w4300":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w4000-series/amd-radeon-pro-w4300",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro WX Series (Workstation)
    # ═══════════════════════════════════════════════════════════════════════════
    "wx9100":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-6000-series/amd-radeon-pro-wx-9100",
    "wx8200":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-6000-series/amd-radeon-pro-wx-8200",
    "wx7100":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-5000-series/amd-radeon-pro-wx-7100",
    "wx5100":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-5000-series/amd-radeon-pro-wx-5100",
    "wx4100":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-4000-series/amd-radeon-pro-wx-4100",
    "wx3200":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-3000-series/amd-radeon-pro-wx-3200",
    "wx3100":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-3000-series/amd-radeon-pro-wx-3100",
    "wx2500":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-2000-series/amd-radeon-pro-wx-2500",
    "wx2100":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-wx-2000-series/amd-radeon-pro-wx-2100",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro Vega Series
    # ═══════════════════════════════════════════════════════════════════════════
    "provega20":       "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-vega-series/amd-radeon-pro-vega-20",
    "provega16":       "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-vega-series/amd-radeon-pro-vega-16",
    "provegaii":       "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-vega-series/amd-radeon-pro-vega-ii",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro VII / V-Series (Datacenter)
    # ═══════════════════════════════════════════════════════════════════════════
    "provii":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-vii/amd-radeon-pro-vii",
    "prov620":         "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-v-series/amd-radeon-pro-v620",
    "prov420":         "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-v-series/amd-radeon-pro-v420",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Instinct (Datacenter / AI)
    # ═══════════════════════════════════════════════════════════════════════════
    "mi200":           "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi200",
    "mi210":           "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi210",
    "mi100":           "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi100",
    "mi60":            "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi60",
    "mi50":            "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi50",
    "mi25":            "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi25",
    "mi8":             "https://www.amd.com/en/support/graphics/amd-radeon-instinct/amd-radeon-instinct/amd-radeon-instinct-mi8",

    # ═══════════════════════════════════════════════════════════════════════════
    # FirePro Series (Legacy Workstation)
    # ═══════════════════════════════════════════════════════════════════════════
    "fpw9100":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-w-series/amd-firepro-w9100",
    "fpw8100":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-w-series/amd-firepro-w8100",
    "fpw7100":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-w-series/amd-firepro-w7100",
    "fpw5100":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-w-series/amd-firepro-w5100",
    "fpw4100":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-w-series/amd-firepro-w4100",
    "fpw2100":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-w-series/amd-firepro-w2100",
    "fps9170":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-s-series/amd-firepro-s9170",
    "fps9150":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-s-series/amd-firepro-s9150",
    "fps9050":         "https://www.amd.com/en/support/graphics/amd-firepro/amd-firepro-s-series/amd-firepro-s9050",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon R5 / R3 Series (Entry Level)
    # ═══════════════════════════════════════════════════════════════════════════
    "r5430":           "https://www.amd.com/en/support/graphics/amd-radeon-r5-series/amd-radeon-r5-series/amd-radeon-r5-430",
    "r5340":           "https://www.amd.com/en/support/graphics/amd-radeon-r5-series/amd-radeon-r5-series/amd-radeon-r5-340",
    "r3430":           "https://www.amd.com/en/support/graphics/amd-radeon-r3-series/amd-radeon-r3-series/amd-radeon-r3-430",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon 500M Series (Mobile Integrated)
    # ═══════════════════════════════════════════════════════════════════════════
    "r530m":           "https://www.amd.com/en/support/graphics/amd-radeon-500m-series/amd-radeon-500m-series/amd-radeon-530m",
    "r520m":           "https://www.amd.com/en/support/graphics/amd-radeon-500m-series/amd-radeon-500m-series/amd-radeon-520m",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 8000 Series (OEM)
    # ═══════════════════════════════════════════════════════════════════════════
    "hd8670":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-8000-series/amd-radeon-hd-8000-series/amd-radeon-hd-8670",
    "hd8570":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-8000-series/amd-radeon-hd-8000-series/amd-radeon-hd-8570",
    "hd8470":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-8000-series/amd-radeon-hd-8000-series/amd-radeon-hd-8470",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 7000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "hd7970":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-7000-series/amd-radeon-hd-7000-series/amd-radeon-hd-7970",
    "hd7850":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-7000-series/amd-radeon-hd-7000-series/amd-radeon-hd-7850",
    "hd7750":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-7000-series/amd-radeon-hd-7000-series/amd-radeon-hd-7750",
    "hd7730":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-7000-series/amd-radeon-hd-7000-series/amd-radeon-hd-7730",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 6000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "hd6970":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-6000-series/amd-radeon-hd-6000-series/amd-radeon-hd-6970",
    "hd6850":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-6000-series/amd-radeon-hd-6000-series/amd-radeon-hd-6850",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 5000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "hd5870":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-5000-series/amd-radeon-hd-5000-series/amd-radeon-hd-5870",
    "hd5770":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-5000-series/amd-radeon-hd-5000-series/amd-radeon-hd-5770",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 4000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "hd4870":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-4000-series/amd-radeon-hd-4000-series/amd-radeon-hd-4870",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 3000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "hd3870":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-3000-series/amd-radeon-hd-3000-series/amd-radeon-hd-3870",
    "hd3850":          "https://www.amd.com/en/support/graphics/amd-radeon-hd-3000-series/amd-radeon-hd-3000-series/amd-radeon-hd-3850",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon HD 2000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "hd2900xt":        "https://www.amd.com/en/support/graphics/amd-radeon-hd-2000-series/amd-radeon-hd-2000-series/amd-radeon-hd-2900-xt",

    # ═══════════════════════════════════════════════════════════════════════════
    # R9 300 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r9390x":          "https://www.amd.com/en/support/graphics/amd-radeon-r9-300-series/amd-radeon-r9-300-series/amd-radeon-r9-390x",
    "r9380":           "https://www.amd.com/en/support/graphics/amd-radeon-r9-300-series/amd-radeon-r9-300-series/amd-radeon-r9-380",
    "r9370":           "https://www.amd.com/en/support/graphics/amd-radeon-r9-300-series/amd-radeon-r9-300-series/amd-radeon-r9-370",

    # ═══════════════════════════════════════════════════════════════════════════
    # R9 200 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r9290x":          "https://www.amd.com/en/support/graphics/amd-radeon-r9-200-series/amd-radeon-r9-200-series/amd-radeon-r9-290x",
    "r9280x":          "https://www.amd.com/en/support/graphics/amd-radeon-r9-200-series/amd-radeon-r9-200-series/amd-radeon-r9-280x",
    "r9270x":          "https://www.amd.com/en/support/graphics/amd-radeon-r9-200-series/amd-radeon-r9-200-series/amd-radeon-r9-270x",

    # ═══════════════════════════════════════════════════════════════════════════
    # R7 300 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r7360":           "https://www.amd.com/en/support/graphics/amd-radeon-r7-300-series/amd-radeon-r7-300-series/amd-radeon-r7-360",
    "r7370":           "https://www.amd.com/en/support/graphics/amd-radeon-r7-300-series/amd-radeon-r7-300-series/amd-radeon-r7-370",

    # ═══════════════════════════════════════════════════════════════════════════
    # R7 200 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r7260x":          "https://www.amd.com/en/support/graphics/amd-radeon-r7-200-series/amd-radeon-r7-200-series/amd-radeon-r7-260x",
    "r7250":           "https://www.amd.com/en/support/graphics/amd-radeon-r7-200-series/amd-radeon-r7-200-series/amd-radeon-r7-250",
    "r7240":           "https://www.amd.com/en/support/graphics/amd-radeon-r7-200-series/amd-radeon-r7-200-series/amd-radeon-r7-240",

    # ═══════════════════════════════════════════════════════════════════════════
    # Embedded Radeon
    # ═══════════════════════════════════════════════════════════════════════════
    "re8860":          "https://www.amd.com/en/support/graphics/amd-embedded-radeon/amd-embedded-radeon-e-series/amd-radeon-e8860",
    "re6760":          "https://www.amd.com/en/support/graphics/amd-embedded-radeon/amd-embedded-radeon-e-series/amd-radeon-e6760",
    "re6465":          "https://www.amd.com/en/support/graphics/amd-embedded-radeon/amd-embedded-radeon-e-series/amd-radeon-e6465",
    "re6460":          "https://www.amd.com/en/support/graphics/amd-embedded-radeon/amd-embedded-radeon-e-series/amd-radeon-e6460",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Sky (Cloud Gaming)
    # ═══════════════════════════════════════════════════════════════════════════
    "rsky900":         "https://www.amd.com/en/support/graphics/amd-radeon-sky-series/amd-radeon-sky-series/amd-radeon-sky-900",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen AI 300 Series (Latest APUs with AI)
    # ═══════════════════════════════════════════════════════════════════════════
    "ai9hx375":        "https://www.amd.com/en/support/processors/ryzen/ryzen-ai-300-series/amd-ryzen-ai-9-hx-375",
    "ai9hx370":        "https://www.amd.com/en/support/processors/ryzen/ryzen-ai-300-series/amd-ryzen-ai-9-hx-370",
    "ai9350":          "https://www.amd.com/en/support/processors/ryzen/ryzen-ai-300-series/amd-ryzen-ai-7-350",
    "ai5340":          "https://www.amd.com/en/support/processors/ryzen/ryzen-ai-300-series/amd-ryzen-ai-5-340",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 9000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "r99950x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-9000-series/amd-ryzen-9-9950x",
    "r99900x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-9000-series/amd-ryzen-9-9900x",
    "r79800x3d":       "https://www.amd.com/en/support/processors/ryzen/ryzen-9000-series/amd-ryzen-7-9800x3d",
    "r79700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-9000-series/amd-ryzen-7-9700x",
    "r59600x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-9000-series/amd-ryzen-5-9600x",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen PRO 9000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r9pro9950":       "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-9000-series/amd-ryzen-9-pro-9950",
    "r7pro9700":       "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-9000-series/amd-ryzen-7-pro-9700",
    "r5pro9600":       "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-9000-series/amd-ryzen-5-pro-9600",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 8000 Series (Desktop APUs)
    # ═══════════════════════════════════════════════════════════════════════════
    "r78700g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-8000-series/amd-ryzen-7-8700g",
    "r58600g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-8000-series/amd-ryzen-5-8600g",
    "r58500g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-8000-series/amd-ryzen-5-8500g",
    "r38300g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-8000-series/amd-ryzen-3-8300g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 7000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "r97950x3d":       "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-9-7950x3d",
    "r97950x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-9-7950x",
    "r97900x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-9-7900x",
    "r77800x3d":       "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-7-7800x3d",
    "r77700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-7-7700x",
    "r57600x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-5-7600x",
    "r57500f":         "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-5-7500f",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 5000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "r95950x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-9-5950x",
    "r75800x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-7-5800x",
    "r75600x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600x",
    "r55500":          "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5500",
    "r75700g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-7-5700g",
    "r55600g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 4000 Series (Desktop APUs)
    # ═══════════════════════════════════════════════════════════════════════════
    "r74700g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-4000-series/amd-ryzen-7-4700g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen PRO 4000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r7pro4750g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-4000-series/amd-ryzen-7-pro-4750g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 3000 Series (Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "r93950x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-9-3950x",
    "r73700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-7-3700x",
    "r53400g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-5-3400g",
    "r33200g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-3-3200g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen PRO 3000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r5pro3400g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-3000-series/amd-ryzen-5-pro-3400g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 2000 Series (Desktop APUs)
    # ═══════════════════════════════════════════════════════════════════════════
    "r52400g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-2000-series/amd-ryzen-5-2400g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen PRO 8000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r7pro8700g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-8000-series/amd-ryzen-7-pro-8700g",
    "r5pro8600g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-8000-series/amd-ryzen-5-pro-8600g",
    "r5pro8500g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-8000-series/amd-ryzen-5-pro-8500g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen PRO 7000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r9pro7945":       "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-7000-series/amd-ryzen-9-pro-7945",
    "r7pro7745":       "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-7000-series/amd-ryzen-7-pro-7745",
    "r5pro7645":       "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-7000-series/amd-ryzen-5-pro-7645",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen PRO 5000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r7pro5750g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-5000-series/amd-ryzen-7-pro-5750g",
    "r5pro5650g":      "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-5000-series/amd-ryzen-5-pro-5650g",
    "r5pro5650ge":     "https://www.amd.com/en/support/processors/ryzen/ryzen-pro-5000-series/amd-ryzen-5-pro-5650ge",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen Threadripper PRO WX Series
    # ═══════════════════════════════════════════════════════════════════════════
    "trpro7995wx":     "https://www.amd.com/en/support/processors/ryzen/ryzen-threadripper-pro-7000-wx-series/amd-ryzen-threadripper-pro-7995wx",
    "trpro5995wx":     "https://www.amd.com/en/support/processors/ryzen/ryzen-threadripper-pro-5000-wx-series/amd-ryzen-threadripper-pro-5995wx",
    "trpro3995wx":     "https://www.amd.com/en/support/processors/ryzen/ryzen-threadripper-pro-3000-wx-series/amd-ryzen-threadripper-pro-3995wx",

    # ═══════════════════════════════════════════════════════════════════════════
    # AMD A-Series APUs
    # ═══════════════════════════════════════════════════════════════════════════
    "a109700":         "https://www.amd.com/en/support/processors/a-series/amd-a10-series-apus/a10-9700",
    "a107890k":        "https://www.amd.com/en/support/processors/a-series/amd-a10-series-apus/a10-7890k",
    "a129800":         "https://www.amd.com/en/support/processors/a-series/amd-a12-series-apus/a12-9800",
    "a89600":          "https://www.amd.com/en/support/processors/a-series/amd-a8-series-apus/a8-9600",
    "a69500":          "https://www.amd.com/en/support/processors/a-series/amd-a6-series-apus/a6-9500",
    "a46300":          "https://www.amd.com/en/support/processors/a-series/amd-a4-series-apus/a4-6300",

    # ═══════════════════════════════════════════════════════════════════════════
    # Athlon & Sempron Series
    # ═══════════════════════════════════════════════════════════════════════════
    "athlon3000g":     "https://www.amd.com/en/support/processors/athlon/athlon-3000-series/amd-athlon-3000g",
    "athlon3150u":     "https://www.amd.com/en/support/processors/athlon/athlon-3000-series/amd-athlon-gold-3150u",
    "athlon3050u":     "https://www.amd.com/en/support/processors/athlon/athlon-3000-series/amd-athlon-silver-3050u",
    "athlon3050e":     "https://www.amd.com/en/support/processors/athlon/athlon-3000-series/amd-athlon-silver-3050e",
    "sempron3850":     "https://www.amd.com/en/support/processors/sempron/sempron-3000-series/amd-sempron-3850",
    "sempron2650":     "https://www.amd.com/en/support/processors/sempron/sempron-3000-series/amd-sempron-2650",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen Z1 Series (Handheld Gaming)
    # ═══════════════════════════════════════════════════════════════════════════
    "ryzenz1":         "https://www.amd.com/en/support/processors/ryzen/ryzen-z1-series/amd-ryzen-z1",
    "ryzenz1extreme":  "https://www.amd.com/en/support/processors/ryzen/ryzen-z1-series/amd-ryzen-z1-extreme",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen AI Max 300 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "aimax395":        "https://www.amd.com/en/support/processors/ryzen/ryzen-ai-max-300-series/amd-ryzen-ai-max-plus-395",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 7000S Series (Thin & Light Laptop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx7900s":         "https://www.amd.com/en/support/graphics/amd-radeon-7000s-series/amd-radeon-rx-7000s-series/amd-radeon-rx-7900s",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon 700M Series (Ryzen 7000/8000 Integrated)
    # ═══════════════════════════════════════════════════════════════════════════
    "r780m":           "https://www.amd.com/en/support/graphics/amd-radeon-700m-series/amd-radeon-700m-series/amd-radeon-780m",
    "r760m":           "https://www.amd.com/en/support/graphics/amd-radeon-700m-series/amd-radeon-700m-series/amd-radeon-760m",
    "r740m":           "https://www.amd.com/en/support/graphics/amd-radeon-700m-series/amd-radeon-700m-series/amd-radeon-740m",
    "r710m":           "https://www.amd.com/en/support/graphics/amd-radeon-700m-series/amd-radeon-700m-series/amd-radeon-710m",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 7000M More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "rx7800m":         "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7800m",
    "rx7650mxt":       "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7650m-xt",
    "rx7600mxt":       "https://www.amd.com/en/support/graphics/amd-radeon-7000m-series/amd-radeon-rx-7000m-series/amd-radeon-rx-7600m-xt",

    # ═══════════════════════════════════════════════════════════════════════════
    # RX 6000M More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "rx6550m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6550m",
    "rx6450m":         "https://www.amd.com/en/support/graphics/amd-radeon-6000m-series/amd-radeon-rx-6000m-series/amd-radeon-rx-6450m",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro Mobile (Workstation Laptop)
    # ═══════════════════════════════════════════════════════════════════════════
    "w6600m":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000m-series/amd-radeon-pro-w6600m",
    "w6300m":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w6000m-series/amd-radeon-pro-w6300m",
    "w5500m":          "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w5000m-series/amd-radeon-pro-w5500m",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon Pro W7000 More
    # ═══════════════════════════════════════════════════════════════════════════
    "w7700":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7700",
    "w7500":           "https://www.amd.com/en/support/graphics/amd-radeon-pro-graphics/amd-radeon-pro-w7000-series/amd-radeon-pro-w7500",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon RX 500X Series (OEM Desktop)
    # ═══════════════════════════════════════════════════════════════════════════
    "rx580x":          "https://www.amd.com/en/support/graphics/amd-radeon-rx-500x-series/amd-radeon-rx-500x-series/amd-radeon-rx-580x",
    "rx560x":          "https://www.amd.com/en/support/graphics/amd-radeon-rx-500x-series/amd-radeon-rx-500x-series/amd-radeon-rx-560x",

    # ═══════════════════════════════════════════════════════════════════════════
    # Radeon RX Vega M (Intel-AMD Partnership)
    # ═══════════════════════════════════════════════════════════════════════════
    "rxtvegamgh":      "https://www.amd.com/en/support/graphics/amd-radeon-rx-vega-m/amd-radeon-rx-vega-m/amd-radeon-rx-vega-m-gh",
    "rxtvegamgl":      "https://www.amd.com/en/support/graphics/amd-radeon-rx-vega-m/amd-radeon-rx-vega-m/amd-radeon-rx-vega-m-gl",

    # ═══════════════════════════════════════════════════════════════════════════
    # AMD A-Series APUs (More Variants)
    # ═══════════════════════════════════════════════════════════════════════════
    "a99425":          "https://www.amd.com/en/support/processors/a-series/amd-a9-series-apus/a9-9425",
    "a99420":          "https://www.amd.com/en/support/processors/a-series/amd-a9-series-apus/a9-9420",
    "a109700e":        "https://www.amd.com/en/support/processors/a-series/amd-a10-series-apus/a10-9700e",
    "a109620p":        "https://www.amd.com/en/support/processors/a-series/amd-a10-series-apus/a10-9620p",
    "a87680":          "https://www.amd.com/en/support/processors/a-series/amd-a8-series-apus/a8-7680",
    "a87410":          "https://www.amd.com/en/support/processors/a-series/amd-a8-series-apus/a8-7410",
    "a69225":          "https://www.amd.com/en/support/processors/a-series/amd-a6-series-apus/a6-9225",
    "a49125":          "https://www.amd.com/en/support/processors/a-series/amd-a4-series-apus/a4-9125",

    # ═══════════════════════════════════════════════════════════════════════════
    # AMD FX-Series APUs
    # ═══════════════════════════════════════════════════════════════════════════
    "fx9830p":         "https://www.amd.com/en/support/processors/fx-series/amd-fx-series-apus/fx-9830p",
    "fx9800p":         "https://www.amd.com/en/support/processors/fx-series/amd-fx-series-apus/fx-9800p",
    "fx8800p":         "https://www.amd.com/en/support/processors/fx-series/amd-fx-series-apus/fx-8800p",
    "fx7600p":         "https://www.amd.com/en/support/processors/fx-series/amd-fx-series-apus/fx-7600p",
    "fx7500":          "https://www.amd.com/en/support/processors/fx-series/amd-fx-series-apus/fx-7500",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 9000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r99950x3d":       "https://www.amd.com/en/support/processors/ryzen/ryzen-9000-series/amd-ryzen-9-9950x3d",
    "r97900":          "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-9-7900",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 8000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r78700f":         "https://www.amd.com/en/support/processors/ryzen/ryzen-8000-series/amd-ryzen-7-8700f",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 7000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r97900":          "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-9-7900",
    "r37300x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-7000-series/amd-ryzen-3-7300x",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 5000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r95950x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-9-5950x",
    "r95900x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-9-5900x",
    "r75800x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-7-5800x",
    "r75700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-7-5700x",
    "r75600x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600x",
    "r55600":          "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600",
    "r55500":          "https://www.amd.com/en/support/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5500",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 4000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r74600g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-4000-series/amd-ryzen-5-4600g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 3000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r93950x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-9-3950x",
    "r93900x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-9-3900x",
    "r73800x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-7-3800x",
    "r73700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-7-3700x",
    "r53600":          "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-5-3600",
    "r53500x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-3000-series/amd-ryzen-5-3500x",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 2000 More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "r72700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-2000-series/amd-ryzen-7-2700x",
    "r52600":          "https://www.amd.com/en/support/processors/ryzen/ryzen-2000-series/amd-ryzen-5-2600",
    "r52400g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-2000-series/amd-ryzen-5-2400g",
    "r32200g":         "https://www.amd.com/en/support/processors/ryzen/ryzen-2000-series/amd-ryzen-3-2200g",

    # ═══════════════════════════════════════════════════════════════════════════
    # Ryzen 1000 Series
    # ═══════════════════════════════════════════════════════════════════════════
    "r71800x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-1000-series/amd-ryzen-7-1800x",
    "r71700x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-1000-series/amd-ryzen-7-1700x",
    "r51600":          "https://www.amd.com/en/support/processors/ryzen/ryzen-1000-series/amd-ryzen-5-1600",
    "r31300x":         "https://www.amd.com/en/support/processors/ryzen/ryzen-1000-series/amd-ryzen-3-1300x",

    # ═══════════════════════════════════════════════════════════════════════════
    # Threadripper PRO More Variants
    # ═══════════════════════════════════════════════════════════════════════════
    "trpro7975wx":     "https://www.amd.com/en/support/processors/ryzen/ryzen-threadripper-pro-7000-wx-series/amd-ryzen-threadripper-pro-7975wx",
    "trpro7955wx":     "https://www.amd.com/en/support/processors/ryzen/ryzen-threadripper-pro-7000-wx-series/amd-ryzen-threadripper-pro-7955wx",
    "trpro7945wx":     "https://www.amd.com/en/support/processors/ryzen/ryzen-threadripper-pro-7000-wx-series/amd-ryzen-threadripper-pro-7945wx",

    # ═══════════════════════════════════════════════════════════════════════════
    # EPYC Embedded
    # ═══════════════════════════════════════════════════════════════════════════
    "epyc9654":        "https://www.amd.com/en/support/processors/epyc/amd-epyc-embedded-9004-series/amd-epyc-embedded-9654",
    "epyc9534":        "https://www.amd.com/en/support/processors/epyc/amd-epyc-embedded-9004-series/amd-epyc-embedded-9534",
    "epyc9454":        "https://www.amd.com/en/support/processors/epyc/amd-epyc-embedded-9004-series/amd-epyc-embedded-9454",
}


def print_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def print_info(msg: str) -> None:
    print(f"[INFO]  {msg}")


def print_success(msg: str) -> None:
    print(f"[OK]    {msg}")


def download_file(url: str, dest: Path, referer: str = "", chunk_size: int = 8192) -> None:
    """Download *url* to *dest* with a simple text progress bar."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)

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


def fetch_amd_driver(page_url: str) -> dict:
    """Scrape an AMD support page and return driver metadata."""
    req = urllib.request.Request(
        page_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")

    # Find every .exe link on the page
    matches = re.findall(r'href="([^"]+\.exe)"', html)
    if not matches:
        raise RuntimeError("No .exe driver link found on the AMD support page.")

    # Prefer full offline installer over web/minimal installer
    # Full installer: no "minimalsetup" or "web" in name, usually larger
    # Web installer: contains "minimalsetup" and/or "web"
    def _score(url: str) -> int:
        name = url.lower()
        if "minimalsetup" in name or "_web" in name:
            return 0   # least preferred
        if "whql" in name or "win10" in name or "win11" in name:
            return 2   # most preferred (full offline)
        return 1       # fallback

    matches.sort(key=_score, reverse=True)
    driver_url = matches[0]
    filename = os.path.basename(driver_url)

    # Try to extract version from the filename, e.g. 26.5.2
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
    print("Available AMD presets:")
    for key, val in sorted(AMD_PRODUCTS.items()):
        print(f"  {key:<13} -> {val}")


def download_one(product_key: str, out_dir: Path) -> bool:
    """Download a single driver. Returns True on success."""
    try:
        page_url = AMD_PRODUCTS[product_key]
        print_info(f"[{product_key}] Scraping AMD driver page ...")
        driver = fetch_amd_driver(page_url)

        print(f"  Driver:  {driver['name']}")
        print(f"  Version: {driver['version']}")
        print(f"  Date:    {driver['date']}")
        print(f"  Size:    {driver['size']}")

        filename = os.path.basename(urllib.parse.urlparse(driver["url"]).path)
        if not filename:
            filename = f"amd_{product_key}_{driver['version']}.exe"
        dest = out_dir / filename

        if dest.exists():
            print_info(f"[{product_key}] Already exists, skipping: {dest}")
            return True

        print_info(f"[{product_key}] Downloading to {dest} ...")
        download_file(driver["url"], dest, referer=page_url)
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
        description="Download the latest AMD GPU drivers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --product rx7900xtx
  %(prog)s --all
  %(prog)s --list
  %(prog)s --amd-url "https://www.amd.com/en/support/graphics/..."
""",
    )
    parser.add_argument("--product", help="Preset product key (e.g. rx7900xtx)")
    parser.add_argument("--amd-url", help="Custom AMD support page URL (overrides preset)")
    parser.add_argument("--output-dir", default="amd_drivers",
                        help="Directory to save the driver(s) (default: ./amd_drivers)")
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
        if args.product or args.amd_url:
            print_error("--all cannot be combined with --product or --amd-url.")
            return 1

        success = 0
        failed = 0

        print(f"\n{'='*60}")
        print_info("Starting batch download for ALL AMD presets")
        print(f"{'='*60}\n")

        for key in AMD_PRODUCTS:
            if download_one(key, out_dir):
                success += 1
            else:
                failed += 1
            time.sleep(1)  # be polite to the servers

        print(f"\n{'='*60}")
        print_info(f"Batch complete — {success} succeeded, {failed} failed.")
        return 0 if failed == 0 else 1

    # ── Single-driver mode ──────────────────────────────────────────────────────
    if args.amd_url:
        try:
            print_info("Scraping custom AMD page ...")
            driver = fetch_amd_driver(args.amd_url)
        except Exception as exc:
            print_error(str(exc))
            return 1
    elif args.product:
        if args.product.lower() not in AMD_PRODUCTS:
            print_error(f"Unknown AMD product '{args.product}'.")
            print("Run with --list to see available presets.")
            return 1
        if not download_one(args.product.lower(), out_dir):
            return 1
        return 0
    else:
        print_error("AMD requires --product or --amd-url (or use --all).")
        return 1

    # If we reach here it means we have a 'driver' dict from custom amd-url
    print(f"\n  Driver:  {driver['name']}")
    print(f"  Version: {driver['version']}")
    print(f"  Date:    {driver['date']}")
    print(f"  Size:    {driver['size']}")
    print(f"  URL:     {driver['url']}\n")

    filename = os.path.basename(urllib.parse.urlparse(driver["url"]).path)
    if not filename:
        filename = f"amd_driver_{driver['version']}.exe"
    dest = out_dir / filename

    if dest.exists():
        print_info(f"File already exists: {dest}")
        return 0

    try:
        print_info(f"Downloading to {dest} ...")
        download_file(driver["url"], dest, referer=args.amd_url)
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
