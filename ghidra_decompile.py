# Jython post-script for Ghidra headless mode
# Decompiles all functions (or a selected list) and writes pseudo-C to a file.
#
# Environment variables consumed:
#   _GHIDRA_DECOMP_OUT   -> path to write the final .c file
#   _GHIDRA_DECOMP_FUNCS -> comma-separated function names (optional)
#
# Usage (inside Ghidra headless):
#   analyzeHeadless <proj> <name> -import <file> -postScript ghidra_decompile.py

import os
import sys
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------
OUT_PATH = os.environ.get("_GHIDRA_DECOMP_OUT")
FUNC_FILTER = os.environ.get("_GHIDRA_DECOMP_FUNCS", "").strip()

if not OUT_PATH:
    print("[ghidra_decompile.py] ERROR: _GHIDRA_DECOMP_OUT not set")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_functions():
    """Yield every Function in the current program."""
    func_mgr = currentProgram.getFunctionManager()
    func = func_mgr.getFunctions(True)
    while func.hasNext():
        yield func.next()


def decompile_function(decomp, func, timeout=60):
    """Decompile a single function and return its C text, or None."""
    results = decomp.decompileFunction(func, timeout, ConsoleTaskMonitor())
    if not results.decompileCompleted():
        return None
    return results.getDecompiledFunction().getC()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("[ghidra_decompile.py] Starting decompilation ...")
    print("[ghidra_decompile.py] Program: {}".format(currentProgram.getName()))

    decomp = DecompInterface()
    decomp.openProgram(currentProgram)

    # Optional: tune simplification/style
    # options = decomp.getOptions()
    # options.setUnicodeEscape(False)

    # Build filter set
    wanted_names = set()
    if FUNC_FILTER:
        wanted_names = set(f.strip() for f in FUNC_FILTER.split(",") if f.strip())
        print("[ghidra_decompile.py] Filtering to functions: {}".format(wanted_names))

    lines = []
    lines.append("/*")
    lines.append(" * Ghidra Pseudo-C Decompilation")
    lines.append(" * Program: {}".format(currentProgram.getName()))
    lines.append(" * Language: {}".format(currentProgram.getLanguageID()))
    lines.append(" * Compiler: {}".format(currentProgram.getCompilerSpec().getCompilerSpecID()))
    lines.append(" */")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("#include <stddef.h>")
    lines.append("")

    count = 0
    skipped = 0

    for func in get_all_functions():
        name = func.getName()
        if wanted_names and name not in wanted_names:
            skipped += 1
            continue

        print("[ghidra_decompile.py] Decompiling: {} @ {}".format(
            name, func.getEntryPoint()))
        c_text = decompile_function(decomp, func, timeout=60)
        if c_text is None:
            lines.append("/* WARNING: failed to decompile '{}' */".format(name))
            lines.append("")
            skipped += 1
            continue

        lines.append("/* Function: {} */".format(name))
        lines.append(c_text)
        lines.append("")
        count += 1

    decomp.dispose()

    # Write output
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))

    print("[ghidra_decompile.py] Done. {} functions decompiled. {} skipped.".format(
        count, skipped))
    print("[ghidra_decompile.py] Output written to: {}".format(OUT_PATH))


main()
