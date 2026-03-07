#!/usr/bin/env python3
"""Compress JPEG and PDF files into optimized PDFs for government portal uploads."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def check_dependencies():
    """Check that required external tools are available."""
    missing = []
    if not shutil.which("magick"):
        missing.append("magick (ImageMagick)")
    if not shutil.which("pdftocairo"):
        missing.append("pdftocairo (poppler)")
    if missing:
        print(f"Error: missing required tools: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def compress_jpeg(input_path: Path, output_path: Path, quality: int, dpi: int):
    """Convert a JPEG to a compressed PDF using ImageMagick."""
    cmd = [
        "magick",
        str(input_path),
        "-quality", str(quality),
        "-density", str(dpi),
        "-resize", f"{dpi * 8}x{dpi * 8}>",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def compress_pdf_lossless(input_path: Path, output_path: Path) -> bool:
    """Try lossless PDF compression with pypdf.

    Returns True if compression achieved <85% of original size.
    """
    original_size = input_path.stat().st_size

    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    for page in writer.pages:
        page.compress_content_streams()

    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

    with open(output_path, "wb") as f:
        writer.write(f)

    compressed_size = output_path.stat().st_size
    ratio = compressed_size / original_size

    if ratio < 0.85:
        return True

    # Not enough compression — remove the file
    output_path.unlink(missing_ok=True)
    return False


def compress_pdf_render(input_path: Path, output_path: Path, quality: int, dpi: int, grayscale: bool = False):
    """Render PDF pages to JPEG with pdftocairo, then reassemble with ImageMagick."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Render each page to JPEG
        cmd = [
            "pdftocairo",
            "-jpeg",
            "-jpegopt", f"quality={quality}",
            "-r", str(dpi),
        ]
        if grayscale:
            cmd.append("-gray")
        cmd += [str(input_path), os.path.join(tmpdir, "page")]
        subprocess.run(cmd, check=True, capture_output=True)

        # Collect rendered pages in sorted order
        pages = sorted(Path(tmpdir).glob("page-*.jpg"))
        if not pages:
            raise RuntimeError(f"pdftocairo produced no output for {input_path}")

        # Assemble into multi-page PDF with ImageMagick
        cmd = ["magick"] + [str(p) for p in pages] + ["-quality", str(quality), str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)


def compress_pdf(
    input_path: Path,
    output_path: Path,
    quality: int,
    dpi: int,
    force_render: bool,
    grayscale: bool = False,
):
    """Compress a PDF: try lossless first, fall back to lossy render."""
    if not force_render:
        if compress_pdf_lossless(input_path, output_path):
            return "lossless"

    compress_pdf_render(input_path, output_path, quality, dpi, grayscale)
    return "rendered"


def compress_pdf_to_target(
    input_path: Path,
    output_path: Path,
    max_bytes: int,
    dpi: int,
    grayscale: bool = False,
):
    """Binary search for highest quality that fits under max_bytes.

    Returns the quality value used.
    """
    lo, hi = 10, 70
    best_quality = lo

    while lo <= hi:
        mid = (lo + hi) // 2
        compress_pdf_render(input_path, output_path, mid, dpi, grayscale)
        size = output_path.stat().st_size
        if size <= max_bytes:
            best_quality = mid
            lo = mid + 1
        else:
            hi = mid - 1

    # Final render at best quality if needed
    if best_quality != mid:
        compress_pdf_render(input_path, output_path, best_quality, dpi, grayscale)

    return best_quality


def format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    parser = argparse.ArgumentParser(
        description="Compress JPEG and PDF files into optimized PDFs."
    )
    parser.add_argument("files", nargs="+", help="Input JPEG or PDF files")
    parser.add_argument(
        "-q", "--quality", type=int, default=60,
        help="JPEG quality 1-95 (default: 60)",
    )
    parser.add_argument(
        "-d", "--dpi", type=int, default=150,
        help="Render DPI for PDF pages (default: 150)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (default: same as input file)",
    )
    parser.add_argument(
        "--force-render", action="store_true",
        help="Skip lossless compression, force lossy render for PDFs",
    )
    parser.add_argument(
        "-g", "--grayscale", action="store_true",
        help="Convert to grayscale (reduces size, ideal for document scans)",
    )
    parser.add_argument(
        "-m", "--max-size", type=float, default=None,
        help="Target maximum file size in MB (auto-selects best quality)",
    )
    args = parser.parse_args()

    check_dependencies()

    results = []

    for filepath in args.files:
        input_path = Path(filepath).resolve()

        if not input_path.exists():
            print(f"Warning: {filepath} not found, skipping", file=sys.stderr)
            continue

        ext = input_path.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".pdf"):
            print(f"Warning: unsupported file type {ext}, skipping {filepath}", file=sys.stderr)
            continue

        # Determine output path
        out_dir = Path(args.output_dir) if args.output_dir else input_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{input_path.stem}_compressed.pdf"

        original_size = input_path.stat().st_size

        try:
            auto_quality = None
            if ext in (".jpg", ".jpeg"):
                compress_jpeg(input_path, output_path, args.quality, args.dpi)
                method = "jpeg→pdf"
            elif args.max_size is not None:
                max_bytes = int(args.max_size * 1024 * 1024)
                auto_quality = compress_pdf_to_target(
                    input_path, output_path, max_bytes, args.dpi, args.grayscale
                )
                method = "auto-fit"
            else:
                method = compress_pdf(
                    input_path, output_path, args.quality, args.dpi,
                    args.force_render, args.grayscale,
                )

            compressed_size = output_path.stat().st_size
            reduction = (1 - compressed_size / original_size) * 100

            result = {
                "input": input_path.name,
                "output": output_path.name,
                "original": original_size,
                "compressed": compressed_size,
                "reduction": reduction,
                "method": method,
            }
            if auto_quality is not None:
                result["auto_quality"] = auto_quality
            results.append(result)

        except Exception as e:
            print(f"Error compressing {filepath}: {e}", file=sys.stderr)

    # Print summary
    if results:
        has_auto = any("auto_quality" in r for r in results)
        header = f"{'Input':<30} {'Method':<10} {'Original':>10} {'Compressed':>10} {'Reduction':>10}"
        if has_auto:
            header += f" {'Quality':>8}"
        print(f"\n{header}")
        print("-" * (75 + (9 if has_auto else 0)))
        for r in results:
            line = (
                f"{r['input']:<30} {r['method']:<10} "
                f"{format_size(r['original']):>10} {format_size(r['compressed']):>10} "
                f"{r['reduction']:>9.1f}%"
            )
            if has_auto and "auto_quality" in r:
                line += f" {r['auto_quality']:>8}"
            print(line)
    else:
        print("No files were compressed.")


if __name__ == "__main__":
    main()
