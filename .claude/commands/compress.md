Compress files using compress.py. Arguments: $ARGUMENTS

Follow these steps:

1. Ensure the virtual environment exists and dependencies are installed:
   ```
   cd .
   if [ ! -d .venv ]; then python3 -m venv .venv; fi
   source .venv/bin/activate
   pip install -q -r requirements.txt
   ```

2. Run the compression script with the provided arguments:
   ```
   source .venv/bin/activate
   python compress.py $ARGUMENTS
   ```

3. Report the results to the user, including file sizes and reduction percentages.

4. Suggest adjustments if needed:
   - For more compression: try `-q 40` or `-g` (grayscale)
   - For better quality: try `-q 75 -d 200`
   - To force lossy rendering on PDFs: use `--force-render`
   - To change resolution: use `-d 100` (lower) or `-d 200` (higher)
   - To auto-fit to a size limit: use `-m 2` (2 MB target)
   - For text-heavy docs (preserves vector text): use `-E gs`
   - For batch AIMA portal submissions: use `/compress-AIMA` instead
