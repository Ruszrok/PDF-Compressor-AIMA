Compress multiple PDF documents for AIMA government portal upload. Arguments: $ARGUMENTS

This skill compresses a folder of PDF documents into a single merged PDF file under a byte budget, suitable for uploading to the AIMA (Portuguese immigration) portal.

Follow these steps:

1. Parse the arguments. The user should provide at minimum a source directory path. Optional arguments include `--prefix`, `--budget-bytes`, `--scanned`, `--open`, etc. If no arguments are provided, ask the user for the source directory.

2. Ensure the virtual environment exists and dependencies are installed:
   ```
   if [ ! -d .venv ]; then python3 -m venv .venv; fi
   source .venv/bin/activate
   pip install -q -r requirements.txt
   ```

3. List the PDF files in the source directory to give the user an overview:
   ```
   ls -lhS "$SOURCE_DIR"/$PREFIX*.pdf
   ```

4. Run the compression script:
   ```
   source .venv/bin/activate
   python compress_aima.py $ARGUMENTS
   ```

5. Report the results including:
   - Per-file original vs compressed sizes
   - Compression method used for each file (gs/screen, render, original)
   - Total parts size and merged file size
   - Whether the result is under the byte budget

6. Open the merged PDF for the user to visually verify quality:
   ```
   open "$MERGED_PDF_PATH"
   ```

7. Ask the user if they want to adjust quality on any specific files. If yes:
   - Re-compress the requested files at higher quality (higher DPI/quality values)
   - Re-merge and verify the total is still under budget
   - Show the updated size table

8. Suggest adjustments if needed:
   - For smaller output: try `--dpi 80 --quality 40`
   - For better quality: try `--dpi 150 --quality 70`
   - To identify scanned docs: use `--scanned "prefix1,prefix2"`
   - To change budget: use `--budget-bytes 3000000`

### Usage examples:
```
/compress-AIMA ~/Documents/aima-docs --prefix doc --budget-bytes 2000000
/compress-AIMA ~/Documents/aima-docs --prefix inv --budget-bytes 2000000 --scanned "inv.3 " --open
/compress-AIMA ~/Documents/aima-docs
```

### CLI flags for compress_aima.py:
| Flag | Default | Description |
|------|---------|-------------|
| `source_dir` | required | Directory containing source PDF files |
| `--prefix` | "" | Filename prefix to match (e.g., "z5") |
| `--output-prefix` | {prefix}c | Prefix for compressed files |
| `--merged-name` | {prefix}f.pdf | Merged output filename |
| `--budget-bytes` | 2000000 | Max merged file size in bytes |
| `--dpi` | 100 | Initial render DPI |
| `--quality` | 60 | Initial JPEG quality |
| `--scanned` | auto-detect | Comma-separated prefixes of scanned docs |
| `--open` | off | Open merged PDF in Preview after completion |
