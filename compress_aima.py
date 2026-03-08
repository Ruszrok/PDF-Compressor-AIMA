#!/usr/bin/env python3
"""Compress multiple PDF files for AIMA portal uploads.

Compresses each PDF individually with per-document strategies (Ghostscript for
digital docs, pdftocairo render for scanned docs), then merges all into a single
PDF under a byte budget.

Usage:
    python compress_aima.py SOURCE_DIR [options]

Examples:
    python compress_aima.py ~/Documents/aima-docs
    python compress_aima.py ~/Documents/aima-docs --prefix z5 --budget-bytes 2000000
    python compress_aima.py ~/Documents/aima-docs --scanned "scan1,scan2" --open
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from compress import compress_ghostscript, compress_pdf_render, format_size


def detect_scanned(pdf_path: Path) -> bool:
    """Detect if a PDF is scanned (no extractable text)."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            if len(text.strip()) > 20:
                return False
        return len(text.strip()) < 20
    except Exception:
        return False


def collect_sources(src_dir: Path, prefix: str, exclude_prefixes: list[str]) -> list[Path]:
    """Collect PDF files matching prefix, excluding compressed/merged outputs."""
    files = sorted(
        f for f in src_dir.glob(f"{prefix}*.pdf")
        if not any(f.name.startswith(ep) for ep in exclude_prefixes)
    )
    if not files:
        print(f"No {prefix}*.pdf files found in {src_dir}", file=sys.stderr)
        sys.exit(1)
    return files


def compress_one(src: Path, out_path: Path, dpi: int, quality: int, is_scanned: bool) -> str:
    """Compress a single file, returning the method used."""
    if is_scanned:
        compress_pdf_render(src, out_path, quality, dpi, grayscale=True)
        return "render"

    compress_ghostscript(src, out_path, quality, dpi, grayscale=True, preset="/screen")
    if out_path.stat().st_size <= src.stat().st_size:
        return "gs/screen"

    # GS inflated — use original
    shutil.copy2(src, out_path)
    return "original"


def print_table(results: list[tuple[Path, Path, str]]) -> int:
    """Print a size comparison table. Returns total compressed size."""
    print(f"\n{'File':<55} {'Method':<10} {'Original':>10} {'Compressed':>10} {'Ratio':>7}")
    print("-" * 95)
    total_orig = total_comp = 0
    for src, out, method in results:
        orig_sz = src.stat().st_size
        comp_sz = out.stat().st_size
        total_orig += orig_sz
        total_comp += comp_sz
        ratio = comp_sz / orig_sz * 100
        print(
            f"{src.name:<55} {method:<10} "
            f"{format_size(orig_sz):>10} {format_size(comp_sz):>10} {ratio:>6.1f}%"
        )
    print("-" * 95)
    ratio = total_comp / total_orig * 100 if total_orig else 0
    print(
        f"{'TOTAL':<55} {'':<10} "
        f"{format_size(total_orig):>10} {format_size(total_comp):>10} {ratio:>6.1f}%"
    )
    return total_comp


def recompress_largest(results: list[tuple[Path, Path, str]], budget: int, scanned_set: set[str]):
    """Re-compress largest files with progressively lower DPI/quality until total fits budget."""
    fallback_settings = [
        (100, 50),
        (80, 40),
        (60, 30),
        (50, 25),
    ]
    for dpi, quality in fallback_settings:
        total = sum(out.stat().st_size for _, out, _ in results)
        if total <= budget:
            return
        ranked = sorted(range(len(results)), key=lambda i: results[i][1].stat().st_size, reverse=True)
        for i in ranked:
            total = sum(o.stat().st_size for _, o, _ in results)
            if total <= budget:
                return
            src, out, method = results[i]
            old_size = out.stat().st_size
            compress_pdf_render(src, out, quality, dpi, grayscale=True)
            new_size = out.stat().st_size
            if new_size < old_size:
                results[i] = (src, out, "render")
                print(f"  Re-compressed {src.name}: {format_size(old_size)} -> {format_size(new_size)} (dpi={dpi}, q={quality})")
            else:
                if method == "original":
                    shutil.copy2(src, out)
                elif method == "gs/screen":
                    compress_ghostscript(src, out, 60, 100, grayscale=True, preset="/screen")

    total = sum(out.stat().st_size for _, out, _ in results)
    if total > budget:
        print(f"Warning: total {format_size(total)} still exceeds budget {format_size(budget)}", file=sys.stderr)


def merge(results: list[tuple[Path, Path, str]], output_path: Path):
    """Merge all compressed PDFs into one, sorted by filename."""
    writer = PdfWriter()
    for _, out, _ in sorted(results, key=lambda r: r[1].name):
        writer.append(str(out))
    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    with open(output_path, "wb") as f:
        writer.write(f)


def main():
    parser = argparse.ArgumentParser(
        description="Compress multiple PDFs for AIMA portal uploads, merge into one file."
    )
    parser.add_argument("source_dir", help="Directory containing source PDF files")
    parser.add_argument("--prefix", default="", help="Filename prefix to match (default: all PDFs)")
    parser.add_argument("--output-prefix", default=None, help="Prefix for compressed files (default: {prefix}c)")
    parser.add_argument("--merged-name", default=None, help="Merged output filename (default: {prefix}f.pdf)")
    parser.add_argument("--budget-bytes", type=int, default=2_000_000, help="Max merged file size in bytes (default: 2000000)")
    parser.add_argument("--dpi", type=int, default=100, help="Initial DPI (default: 100)")
    parser.add_argument("--quality", type=int, default=60, help="Initial JPEG quality (default: 60)")
    parser.add_argument("--scanned", default=None, help="Comma-separated prefixes of scanned (non-digital) docs to force render")
    parser.add_argument("--open", action="store_true", help="Open merged PDF in Preview after completion")
    args = parser.parse_args()

    src_dir = Path(args.source_dir).resolve()
    if not src_dir.is_dir():
        print(f"Error: {src_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    prefix = args.prefix
    out_prefix = args.output_prefix or (prefix.rstrip(".") + "c" if prefix else "c_")
    merged_name = args.merged_name or (prefix.rstrip(".") + "f.pdf" if prefix else "merged.pdf")

    # Exclude our own output files
    exclude_prefixes = [out_prefix]
    if merged_name:
        exclude_prefixes.append(merged_name.replace(".pdf", ""))

    # Explicit scanned prefixes
    scanned_prefixes = set()
    if args.scanned:
        scanned_prefixes = {s.strip() for s in args.scanned.split(",")}

    print(f"Source: {src_dir}")
    print(f"Prefix: '{prefix}' -> compressed: '{out_prefix}', merged: '{merged_name}'")

    # Collect source files
    sources = collect_sources(src_dir, prefix, exclude_prefixes)
    print(f"Found {len(sources)} PDF files\n")

    # Auto-detect scanned docs
    print("Analyzing documents...")
    scanned_set = set()
    for src in sources:
        is_scan = any(src.name.startswith(sp) for sp in scanned_prefixes) or detect_scanned(src)
        if is_scan:
            scanned_set.add(src.name)
            print(f"  {src.name}: scanned (will use render)")

    # Step 1: Compress each file
    print("\nCompressing...")
    results = []
    for src in sources:
        out_name = src.name.replace(prefix, out_prefix, 1) if prefix else f"{out_prefix}{src.name}"
        out_path = src_dir / out_name
        method = compress_one(src, out_path, args.dpi, args.quality, src.name in scanned_set)
        results.append((src, out_path, method))

    # Step 2: Print size table
    total = print_table(results)

    # Step 3: Budget fitting
    if total > args.budget_bytes:
        print(f"\nTotal {format_size(total)} exceeds budget {format_size(args.budget_bytes)}, re-compressing...")
        recompress_largest(results, args.budget_bytes, scanned_set)
        total = print_table(results)

    # Step 4: Merge
    merged_path = src_dir / merged_name
    print(f"\nMerging into {merged_name}...")
    merge(results, merged_path)
    merged_size = merged_path.stat().st_size
    print(f"{merged_name}: {format_size(merged_size)} ({merged_size:,} bytes)")

    # Step 5: Verification
    if merged_size <= args.budget_bytes:
        print(f"OK — {format_size(args.budget_bytes - merged_size)} under budget")
    else:
        print(f"WARNING — over budget by {format_size(merged_size - args.budget_bytes)}", file=sys.stderr)

    if args.open:
        subprocess.run(["open", str(merged_path)])


if __name__ == "__main__":
    main()
