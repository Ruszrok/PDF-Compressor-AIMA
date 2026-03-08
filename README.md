# PDF Compressor

A toolkit for compressing JPEG and PDF files into optimized PDFs suitable for uploading to government portals (AIMA, etc.). Includes Claude Code integration with slash commands for interactive compression workflows.

## Features

- **Single-file compression** (`compress.py`) — compress individual PDFs/JPEGs with configurable quality, DPI, grayscale, and auto-fit to size targets
- **Batch AIMA compression** (`compress_aima.py`) — compress a folder of PDFs with per-document strategies and merge into a single file under a byte budget
- **Visual comparison** (`compare.py`) — compare 4 compression methods side by side
- **Claude Code slash commands** — `/compress` and `/compress-AIMA` for interactive use

## Requirements

### System Dependencies

Install on macOS with Homebrew:

```bash
brew install python@3.13 imagemagick poppler ghostscript pdfcpu
```

| Tool | Purpose |
|------|---------|
| Python 3.13 | Runtime |
| ImageMagick (`magick`) | Image processing and PDF assembly |
| poppler (`pdftocairo`) | PDF-to-image rendering |
| Ghostscript (`gs`) | PDF optimization preserving vector text |
| pdfcpu | Lossless structural PDF optimization (used by `compare.py`) |

### Python Dependencies

```bash
pip install pypdf>=6.0
```

## Setup

```bash
git clone <this-repo>
cd compressor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Compress a single file

```bash
source .venv/bin/activate
python compress.py document.pdf                      # Default compression
python compress.py -q 40 large.pdf                   # More aggressive
python compress.py -g -m 2 large.pdf                  # Grayscale, auto-fit to 2 MB
python compress.py -E gs -g document.pdf              # Ghostscript (preserves vector text)
```

### Batch compress for AIMA portal

```bash
source .venv/bin/activate
python compress_aima.py ~/Documents/aima-docs --prefix z5 --budget-bytes 2000000 --open
```

This will:
1. Find all `z5*.pdf` files in the source directory
2. Compress each individually (Ghostscript for digital, render for scanned)
3. Auto-fit to budget by re-compressing largest files if needed
4. Merge all into `z5f.pdf` and open in Preview

### Compare compression methods

```bash
source .venv/bin/activate
python compare.py -m 2 document.pdf
```

## Using with Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) is Anthropic's CLI tool that lets you use Claude directly in your terminal. This project includes slash commands that make compression interactive — Claude analyzes your files, runs compression, shows results, and helps you adjust quality.

### Installing Claude Code

1. **Install Node.js** (v18+):
   ```bash
   brew install node
   ```

2. **Install Claude Code**:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

3. **Authenticate** — run `claude` and follow the prompts to log in with your Anthropic account. You need an active Anthropic API key or a Claude Pro/Max subscription.

4. **Navigate to this project**:
   ```bash
   cd /path/to/compressor
   claude
   ```

### Slash Commands

Once inside Claude Code in this project directory:

| Command | Description |
|---------|-------------|
| `/compress <files> [flags]` | Compress individual files interactively |
| `/compress-AIMA <source_dir> [flags]` | Batch-compress PDFs for AIMA portal upload |

#### Examples

```
/compress scan.jpg -q 40
/compress document.pdf -E gs -g -m 2
/compress-AIMA ~/Documents/aima-docs --prefix z5 --budget-bytes 2000000
/compress-AIMA ~/Documents/aima-docs --prefix z5 --scanned "z5.9 " --open
```

### Interactive workflow with `/compress-AIMA`

1. Run `/compress-AIMA /path/to/docs --prefix z5 --budget-bytes 2000000`
2. Claude compresses each document, shows a size table
3. If over budget, automatically re-compresses largest files
4. Opens the merged PDF for visual verification
5. You can ask Claude to increase quality on specific files — it will re-compress and re-merge while staying under budget

### Claude Code Requirements

- **Node.js** v18+ (`brew install node`)
- **Claude Code** (`npm install -g @anthropic-ai/claude-code`)
- **Anthropic account** — one of:
  - Claude Pro subscription ($20/month) or Claude Max ($100/month)
  - Anthropic API key with credits
- All system dependencies listed above must be installed
