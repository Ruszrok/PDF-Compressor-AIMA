#!/usr/bin/env python3
"""Compare PDF compression approaches side by side.

Produces 4 compressed versions of a PDF:
  v1: Python render (pdftocairo + magick) — current approach
  v2: Python render + grayscale + enhance
  v3: Ghostscript (preserves vector text)
  v4: pdfcpu lossless optimize (structural only)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from compress import (
    compress_ghostscript_to_target,
    compress_pdf_render,
    compress_pdf_to_target,
    format_size,
)


def check_compare_dependencies():
    """Check that all comparison tools are available."""
    tools = {
        "magick": "ImageMagick (brew install imagemagick)",
        "pdftocairo": "poppler (brew install poppler)",
        "gs": "Ghostscript (brew install ghostscript)",
        "pdfcpu": "pdfcpu (brew install pdfcpu)",
    }
    missing = [desc for cmd, desc in tools.items() if not shutil.which(cmd)]
    if missing:
        print(f"Error: missing required tools:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)


def compress_pdfcpu(input_path: Path, output_path: Path):
    """Lossless structural optimization using pdfcpu (Go)."""
    subprocess.run(
        ["pdfcpu", "optimize", str(input_path), str(output_path)],
        check=True, capture_output=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Compare PDF compression approaches side by side."
    )
    parser.add_argument("file", help="Input PDF file")
    parser.add_argument(
        "-m", "--max-size", type=float, default=2.0,
        help="Target max file size in MB (default: 2.0)",
    )
    parser.add_argument(
        "-d", "--dpi", type=int, default=150,
        help="Render DPI (default: 150)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (default: same as input file)",
    )
    args = parser.parse_args()

    check_compare_dependencies()

    input_path = Path(args.file).resolve()
    if not input_path.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix.lower() != ".pdf":
        print(f"Error: {args.file} is not a PDF", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    original_size = input_path.stat().st_size
    max_bytes = int(args.max_size * 1024 * 1024)
    stem = input_path.stem

    versions = [
        ("v1_python", "Render (default)"),
        ("v2_python_ge", "Render+gray+enh"),
        ("v3_ghostscript", "Ghostscript"),
        ("v4_pdfcpu", "pdfcpu lossless"),
    ]

    results = []
    output_paths = []

    for tag, label in versions:
        out_path = out_dir / f"{stem}_{tag}.pdf"
        output_paths.append(out_path)

        print(f"Compressing {tag}...", end=" ", flush=True)
        try:
            quality = None
            if tag == "v1_python":
                quality = compress_pdf_to_target(
                    input_path, out_path, max_bytes, args.dpi,
                    grayscale=False, enhance=False,
                )
            elif tag == "v2_python_ge":
                quality = compress_pdf_to_target(
                    input_path, out_path, max_bytes, args.dpi,
                    grayscale=True, enhance=True,
                )
            elif tag == "v3_ghostscript":
                quality = compress_ghostscript_to_target(
                    input_path, out_path, max_bytes, args.dpi,
                    grayscale=True,
                )
            elif tag == "v4_pdfcpu":
                compress_pdfcpu(input_path, out_path)

            size = out_path.stat().st_size
            reduction = (1 - size / original_size) * 100
            results.append({
                "tag": tag,
                "label": label,
                "size": size,
                "reduction": reduction,
                "quality": quality,
                "path": out_path,
            })
            print(f"{format_size(size)} ({reduction:.1f}% reduction)")

        except Exception as e:
            print(f"FAILED: {e}")
            results.append({
                "tag": tag,
                "label": label,
                "size": None,
                "reduction": None,
                "quality": None,
                "path": out_path,
                "error": str(e),
            })

    # Print comparison table
    print(f"\n{'='*80}")
    print(f"Comparison: {input_path.name} ({format_size(original_size)})")
    print(f"Target: {args.max_size} MB | DPI: {args.dpi}")
    print(f"{'='*80}")
    print(f"{'Version':<20} {'Method':<20} {'Size':>10} {'Reduction':>10} {'Quality':>8}")
    print("-" * 70)

    for r in results:
        if r["size"] is not None:
            q_str = str(r["quality"]) if r["quality"] is not None else "n/a"
            print(
                f"{r['tag']:<20} {r['label']:<20} "
                f"{format_size(r['size']):>10} {r['reduction']:>9.1f}% {q_str:>8}"
            )
        else:
            print(f"{r['tag']:<20} {r['label']:<20} {'FAILED':>10}")

    # Open all successful outputs in Preview for visual comparison
    successful = [r["path"] for r in results if r["size"] is not None]
    if successful:
        print(f"\nOpening {len(successful)} files in Preview for comparison...")
        subprocess.run(["open", "-a", "Preview"] + [str(p) for p in successful])


if __name__ == "__main__":
    main()
