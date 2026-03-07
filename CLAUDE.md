# PDF Compressor

Compresses JPEG and PDF files into optimized PDFs suitable for uploading to government portals.

## System Dependencies

- **Python 3.13** — runtime
- **ImageMagick** (`magick`) — image processing and PDF assembly
- **poppler** (`pdftocairo`) — PDF-to-image rendering (at `/opt/homebrew/bin/pdftocairo`)
- Ghostscript is NOT installed — ImageMagick cannot read PDFs directly

## Setup

```bash
cd .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
source .venv/bin/activate
python compress.py [-q QUALITY] [-d DPI] [-o OUTPUT_DIR] [-g] [-m MAX_MB] [--force-render] file1 file2 ...
```

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-q` / `--quality` | 60 | JPEG quality (1-95) |
| `-d` / `--dpi` | 150 | Render DPI for PDF pages |
| `-o` / `--output-dir` | same as input | Output directory |
| `--force-render` | off | Skip lossless, force lossy render for PDFs |
| `-g` / `--grayscale` | off | Convert to grayscale (reduces size, ideal for document scans) |
| `-m` / `--max-size` | none | Target max file size in MB (auto-selects best quality) |

### Examples

```bash
python compress.py scan.jpg                          # JPEG → compressed PDF
python compress.py document.pdf                      # PDF → compressed PDF
python compress.py -q 40 large.pdf                   # More aggressive compression
python compress.py -q 75 -d 200 important.pdf        # Higher quality
python compress.py --force-render bloated.pdf         # Force lossy rendering
python compress.py -o ./output file1.jpg file2.pdf    # Batch, custom output dir
python compress.py -g --force-render document.pdf     # Grayscale lossy compression
python compress.py -g -m 2 large.pdf                  # Auto-fit to 2 MB, grayscale
```

## Output

Files are saved as `{original_name}_compressed.pdf` in the output directory (defaults to same directory as input).

## Compression Strategy

- **JPEG → PDF**: ImageMagick converts directly with quality/DPI settings
- **PDF → PDF (two-stage)**:
  1. **Lossless** (pypdf): compress streams, remove duplicates — accepted if <85% of original
  2. **Lossy fallback**: `pdftocairo` renders pages to JPEG, then `magick` reassembles into PDF
- **Auto-fit** (`--max-size`): binary search for highest JPEG quality that fits under target size

## Slash Command

Use `/compress` in Claude Code to run compression. Example: `/compress scan.jpg -q 40`
