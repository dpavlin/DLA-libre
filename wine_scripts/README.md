# wine_scripts/

This directory contains auxiliary scripts used during the reverse engineering and verification of the 3M(TM) Digital Data Manager. The scripts fall into three categories:

1. **Wine automation** (`*.sh`) — Headless scripts that drive the legacy `DataManager.exe` under Wine/Xvfb to compile catalogs, process imports, and verify pull lists.
2. **Python verification** (`*.py`) — Tools for comparing native vs. Wine outputs, verifying sort order correctness, and rebuilding git history.
3. **JavaScript utilities** (`*.js`) — ActiveXObject/ADODB scripts for inspecting and manipulating the Access database schema.

---

## Shell Scripts (Wine Automation)

All `.sh` scripts use `Xvfb :99` for headless display, `xdotool` for GUI automation, and `wine` to run `DataManager.exe`. They assume the Wine prefix is at `/home/dpavlin/.wine`.

### [`check_large_pull_wine.sh`](check_large_pull_wine.sh)

Automated holds compiler that queries, selects, and compiles large-scale Koha pull lists under Wine.

**Workflow:**
1. Kills any existing Wine/Xvfb processes and clears the pull directory.
2. Launches `DataManager.exe` under Xvfb to detect `pull_koha_large.tab`.
3. Runs a WSH/ADODB script (`select_large_pull.js`) to select only the large pull list in the database.
4. Relaunches the app, triggers **Export** via GUI (Alt+F, E), and waits for compilation.
5. Exits cleanly and reports generated files in the pull folder.

**Use case:** Compiling large holds/pull lists on the DLA handheld reader.

---

### [`check_pull_wine.sh`](check_pull_wine.sh)

Verification helper that launches the legacy client, takes a screenshot of the Pull Lists screen, and confirms which pull lists are loaded and marked as "Selected".

**Workflow:**
1. Cleans up previous Wine/Xvfb sessions.
2. Launches `DataManager.exe` under Xvfb.
3. Takes a screenshot (`screenshot_pull_lists.png`) to visually verify the Pull Lists screen (should show pull lists in green with the selected list highlighted).
4. Exits cleanly.

**Use case:** Quick sanity check before running a full export — confirms the database state before compilation.

---

### [`execute_export_a.sh`](execute_export_a.sh)

Isolated automation script to clear, load, and compile **Floor A** databases under Wine for comparative analysis with the native compiler.

**Workflow:**
1. Temporarily moves other floor tab files (B–F) out of the monitored folder so only Floor A is processed.
2. Runs `clear_db.js` to wipe the LibItem and List tables.
3. Runs `setup_list.js` to select only Floor A and set its path.
4. Launches `DataManager.exe`, triggers **Refresh (F5)**, then **Export** via GUI.
5. Waits for compilation (Floor A typically has ~2760 items, ~25 seconds).
6. Restores other floor files and reports generated files under `Card/Database/`.

**Use case:** Controlled, isolated export of a single floor for byte-for-byte parity testing.

---

### [`execute_export_pull.sh`](execute_export_pull.sh)

Verification helper to execute the compilation of pull lists under Wine.

**Workflow:**
1. Clears the Card Database folder and sets it up fresh.
2. Launches `DataManager.exe` under Xvfb.
3. Triggers **Export** (Alt+F, E) and accepts validation warnings.
4. Takes a screenshot (`screenshot_export_pull_done.png`) to verify success.
5. Exits cleanly and reports files in the Database folder.

**Use case:** Triggering export after a pull list has been prepared in the database.

---

### [`execute_import_wine.sh`](execute_import_wine.sh)

Executes the import/scan processing flow under Wine to verify legacy parsing output.

**Workflow:**
1. Sets up Card Upload folders (`Card/upload/inv/`) and cleans the Import directory.
2. Copies a sample upload file (`test/upload/inv/001.pdX`) into the upload folder.
3. Launches `DataManager.exe`, triggers **Import** (Alt+F, I) via GUI.
4. Takes two screenshots (`screenshot_import_dialog.png`, `screenshot_import_done.png`) to verify the import dialog and completion.
5. Exits cleanly and reports files in the Import directory.

**Use case:** Verifying that the legacy client correctly parses uploaded handheld scan files before the native import is trusted.

---

## Python Scripts

### [`compare_a.py`](compare_a.py)

Binary comparison utility for **Floor A** PalmDB output segments. Compares Wine-generated databases against native compiler output for every file segment.

**What it checks:**
* **`000-3MLH.pdb`** — Full binary comparison excluding header timestamps and CAFN dynamic timestamps.
* **`id01/001-3MLH.pdX`** — Parses index entries (barcode, zone, slot) and compares counts + individual entries.
* **`md01/001d-3MLH.pdb`** — Parses data records and compares content.
* **`ndex/3F3F4431/` and `ndex/3F3F4432/`** — Parses title/callnumber mapping tables (both PDB records and PDX index entries).

**Paths compared:**
* Wine: `/home/dpavlin/DLA/Card/Database/`
* Native: `/home/dpavlin/DLA_floors/A/Database/`

**Use case:** Verifying that the native compiler produces byte-identical output to the legacy Wine compiler for Floor A.

---

### [`compare_databases.py`](compare_databases.py)

PDX/PDB file comparison utility for **Floor F**. Parses and compares index (.pdX) and data (.pdb) files between the original Wine database and the native compiled output.

**What it checks:**
* **Index segments** (`id01/001-3MLH.pdX` through `id01/006-3MLH.pdX`): Parses barcode → segment → shelf_idx tuples, compares first/last 3 entries.
* **Data segments** (`md01/001d-3MLH.pdb` through `md01/006d-3MLH.pdb`): Parses UTF-8 text records, compares content.

**Paths compared:**
* Original (Wine): `/home/dpavlin/DLA/F/Database/`
* Compiled (Native): `/home/dpavlin/DLA_floors/F/Database/`

**Use case:** Extended parity verification across multiple floor segments, particularly for larger floors that generate multiple index/data files.

---

### [`test_sort.py`](test_sort.py)

Sort order verification test that compares the native Python sorting logic against the Wine/ADODB title sort mapping stored in the PalmOS index file.

**What it does:**
1. Reads the Wine index mapping (`ndex/3F3F4431/id01/001-3MLH.pdX`) which contains 1-based record indices in title-sort order.
2. Loads the original `A.tab` file and sorts by barcode (to align 1-based indexing).
3. Applies the same title truncation rule used in the native compiler: `f"title: {title}"[:40][7:]`.
4. Performs case-insensitive sorting and compares the resulting index map against the Wine map.
5. Reports total mismatches out of 2760 records.

**Use case:** Debugging and verifying that the native sort order matches the legacy Wine compiler's title-based sort exactly.

---

### [`build_timeline.py`](build_timeline.py)

Builds a re-ordered git commit history that places all `wine_scripts` files chronologically first (based on their creation timestamps extracted from the AI session transcript), followed by the rest of the repository history.

**What it does:**
1. Parses `transcript.jsonl` from the AI session to extract file creation timestamps and context descriptions.
2. Creates an orphan branch with an empty initial commit.
3. Adds all 32 files in chronological order with descriptive commit messages.
4. Cherry-picks the remaining 19 commits from the original history.

**Use case:** Repository housekeeping — creating a clean, chronological commit history where the Wine reverse engineering scripts appear first.

---

### [`organize_files.py`](organize_files.py)

Repository file organization tool. Moves misplaced `.js`, `.py`, and `.sh` files from the repository root into `wine_scripts/`, with configurable exceptions for core files.

**Key features:**
* Supports `--dry-run` mode for preview.
* Configurable `ROOT_EXCEPTIONS` set to keep core files in root (`dla_tool.py`, `build_all_floors.sh`, `execute_export_final.sh`).
* Detects name collisions and refuses to overwrite.

**Use case:** Maintaining clean file organization as the repository grows.
