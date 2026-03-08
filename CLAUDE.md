# PDF Compressor

Compresses JPEG and PDF files into optimized PDFs suitable for uploading to government portals.

## System Dependencies

- **Python 3.13** — runtime
- **ImageMagick** (`magick`) — image processing and PDF assembly
- **poppler** (`pdftocairo`) — PDF-to-image rendering (at `/opt/homebrew/bin/pdftocairo`)
- **Ghostscript** (`gs`) — PDF optimization preserving vector text (`brew install ghostscript`)
- **pdfcpu** — lossless structural PDF optimization (`brew install pdfcpu`), used by `compare.py`

## Setup

```bash
cd .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Single-file compression

```bash
source .venv/bin/activate
python compress.py [-q QUALITY] [-d DPI] [-o OUTPUT_DIR] [-g] [-m MAX_MB] [-E ENGINE] [--force-render] file1 file2 ...
```

#### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-q` / `--quality` | 60 | JPEG quality (1-95) |
| `-d` / `--dpi` | 150 | Render DPI for PDF pages |
| `-o` / `--output-dir` | same as input | Output directory |
| `--force-render` | off | Skip lossless, force lossy render for PDFs |
| `-g` / `--grayscale` | off | Convert to grayscale (reduces size, ideal for document scans) |
| `-m` / `--max-size` | none | Target max file size in MB (auto-selects best quality) |
| `-e` / `--enhance` | off | Enhance text readability (normalize contrast + sharpen) |
| `-E` / `--engine` | auto | Compression engine: `auto`, `render` (pdftocairo), `gs` (Ghostscript) |

#### Examples

```bash
python compress.py scan.jpg                          # JPEG -> compressed PDF
python compress.py document.pdf                      # PDF -> compressed PDF
python compress.py -q 40 large.pdf                   # More aggressive compression
python compress.py -q 75 -d 200 important.pdf        # Higher quality
python compress.py --force-render bloated.pdf         # Force lossy rendering
python compress.py -o ./output file1.jpg file2.pdf    # Batch, custom output dir
python compress.py -g --force-render document.pdf     # Grayscale lossy compression
python compress.py -g -m 2 large.pdf                  # Auto-fit to 2 MB, grayscale
python compress.py -g -e -m 2 large.pdf               # Auto-fit + enhanced text readability
python compress.py -E gs -g -m 2 large.pdf             # Ghostscript engine, auto-fit to 2 MB
```

### AIMA batch compression

`compress_aima.py` compresses a folder of PDFs with per-document strategies and merges into a single PDF under a byte budget. Designed for AIMA portal document submissions.

```bash
python compress_aima.py SOURCE_DIR [--prefix PREFIX] [--budget-bytes BYTES] [--dpi DPI] [--quality Q] [--scanned PREFIXES] [--open]
```

| Flag | Default | Description |
|------|---------|-------------|
| `source_dir` | required | Directory containing source PDF files |
| `--prefix` | "" | Filename prefix to match (e.g., "z5") |
| `--output-prefix` | {prefix}c | Prefix for compressed output files |
| `--merged-name` | {prefix}f.pdf | Merged output filename |
| `--budget-bytes` | 2000000 | Max merged file size in bytes |
| `--dpi` | 100 | Initial render DPI |
| `--quality` | 60 | Initial JPEG quality |
| `--scanned` | auto-detect | Comma-separated prefixes of scanned (non-digital) docs |
| `--open` | off | Open merged PDF in Preview after completion |

**Strategy**: Digital docs use Ghostscript `/screen` (preserves vector text). Scanned docs (auto-detected or specified) use pdftocairo render. If GS inflates a file, the original is kept. Budget fitting re-compresses largest files with progressively lower DPI/quality.

#### Examples

```bash
python compress_aima.py ~/docs --prefix z5 --budget-bytes 2000000
python compress_aima.py ~/docs --prefix z5 --scanned "z5.9 " --open
python compress_aima.py ~/docs                                      # All PDFs, 2 MB budget
```

## Output

- Single-file: `{original_name}_compressed.pdf` in the output directory
- AIMA batch: `{prefix}c*.pdf` per-file + `{prefix}f.pdf` merged, in the source directory

## Compression Strategy

- **JPEG -> PDF**: ImageMagick converts directly with quality/DPI settings
- **PDF -> PDF (two-stage)**:
  1. **Lossless** (pypdf): compress streams, remove duplicates — accepted if <85% of original
  2. **Lossy fallback**: `pdftocairo` renders pages to JPEG, then `magick` reassembles into PDF
- **Auto-fit** (`--max-size`): binary search for highest JPEG quality that fits under target size
- **Ghostscript** (`--engine gs` or AIMA default): recompresses embedded images while preserving vector text as vectors — superior for text-heavy documents

## Comparison Tool

`compare.py` produces 4 compressed versions of a PDF side by side for visual comparison:

```bash
python compare.py [-m MAX_SIZE_MB] [-d DPI] input.pdf
```

Versions produced: Python render (default), Python render+grayscale+enhance, Ghostscript, pdfcpu lossless.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/compress` | Compress individual files. Example: `/compress scan.jpg -q 40` |
| `/compress-AIMA` | Batch-compress a folder of PDFs for AIMA portal upload. Example: `/compress-AIMA ~/docs --prefix z5 --budget-bytes 2000000` |
