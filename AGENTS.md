# Working on Ultra Fast Blink

## Purpose and voice

This is a SASpro user script for quickly screening long astrophotography sessions, especially nights that became cloudy or misty. The author built and used it for this purpose. Preserve that practical, personal explanation in the README; keep the language clear, friendly and direct.

This tool is not a replacement for SASpro's Blink. Its score uses assumptions and sampled star evidence; previews and assessments have lower fidelity than a full inspection. Do not describe the score as a stacking weight or promise that every rejected frame is bad.

## Architecture

- `ultra_fast_blink.py`: SASpro metadata, package loading and `run(ctx)` entry point.
- `ultra_fast_blink/_models.py`: Measurement, Frame and shared constants.
- `_readers.py`: FITS/XISF planes and format dispatch.
- `_analysis.py`: Sample windows, SEP measurements and bounded previews.
- `_workers.py`: Qt workers and the bounded thread pool.
- `_file_ops.py`: Moving files without overwriting destinations.
- `_window.py`: Comparator widget, interactions and file actions.
- `_integration.py`: Window ownership and SASpro stacking integration.

Keep dependencies flowing from UI/workers toward analysis/readers/models. Keep shared models independent of Qt.

## SASpro loader details

These were verified in `src/setiastro/saspro/ops/scripts.py` in the SASpro source checkout during the original split:

- The loader recursively scans for `.py` files. It skips `__init__.py`, underscore/hidden filenames and `__pycache__`. An underscore-prefixed directory alone does not hide its contents. Keep helper filenames underscore-prefixed.
- Scripts are loaded with `spec_from_file_location`; their directory is not automatically added to `sys.path`, and the entry point has no normal package context.
- Preserve `SCRIPT_NAME`, `SCRIPT_GROUP`, `SCRIPT_ID` and callable `run(ctx)` in the entry file. The current ID is `setiastro.ultra-fast-blink`.
- The entry point explicitly loads the sibling package under a fresh UUID-based module name each time. This refreshes helpers on Reload Scripts while existing windows retain their original classes. Successful loads currently remain in `sys.modules`; do not assume they are cleaned up.
- The built-in script editor lists top-level files only. Helpers are edited externally.
- Install the entry file and package folder together. Do not turn this into a standalone application accidentally.

## Data and UI constraints

Uncompressed FITS and attached uncompressed XISF use mapped data. Only owned small arrays should escape reader contexts; release mapping references before closing them. Compressed/inline XISF requires full decoding, but subsequent analysis still processes sampled patches. Keep decompression and analysis distinct in documentation. Compressed FITS is rejected. FITS supports 2D planes; XISF supports mono/RGB and uses its first image.

Preserve Bayer sampling behavior, FITS scaling/blank handling and XISF storage layout handling. Scoring is based on patches, not every pixel. Keep previews bounded and generated on demand; the UI caches at most three.

Scanning uses at most two jobs in flight. Keep cancellation and worker shutdown intact: threads must finish before Qt destroys their windows. Keep window ownership under SASpro and do not start another application event loop.

Preserve no-overwrite file operations, error reporting and explicit deletion confirmation. Stacking sends selected rows, otherwise all listed files; Select Unflagged selects keepers explicitly.

## Verification

For code changes, check syntax in memory or use Python's `-B` flag to avoid littering the script folder with bytecode. Exercise imports with `spec_from_file_location` and `exec_module`, matching SASpro rather than relying on the working directory. Load twice to check helper refresh behavior.

A Qt smoke check can use `QT_QPA_PLATFORM=offscreen`, create a QApplication and a QWidget-backed context exposing `main_window()` and `log()`, call `run(ctx)`, then close the child comparator. This verifies construction, not FITS/XISF processing or actual stacking integration. Use representative images for changes to readers or analysis.

The initial split passed repeated imports and an offscreen window open/close check in the SASpro checkout's virtual environment. That environment is external to this repository; do not assume a local `.venv` exists here.

## Documentation assets

`docs/screenshot.png` is the author-provided screenshot from November 2, 2026. Keep the README image link relative so it renders on GitHub. The LICENSE file was empty when these notes were written; do not claim a specific license without the author's decision.
