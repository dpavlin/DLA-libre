# DLA-libre

`DLA-libre` is a native, open-source Linux implementation of the proprietary **3M(TM) Digital Data Manager** database compiler. It replaces the legacy Windows-based compiler (`DataManager.exe`) by compiling tab-delimited shelf list catalogs into PalmOS database formats (.pdb/.pdX) used by the **3M(TM) Digital Library Assistant (DLA)** handheld inventory reader.

### Why is it called a "Database Compiler"?
The tool is designated as a compiler because it does not simply convert file types; it processes raw flat-file catalog listings (`.tab`/`.csv`) and builds ("compiles") them into highly structured, device-native PalmOS binary database formats. This compilation process involves:
* **Structured Binary Index Trees:** Generating `.pdX` index segments with dynamic record layout sizes (14-byte vs 16-byte records) depending on database size.
* **Sorted Catalogs:** Constructing sorted book data catalogs (`.pdb` data segments) with field-level null padding, custom labels, and spacing configurations.
* **Metadata Mapping:** Packaging app info, validation parameters, and sort metadata blocks.
* **Self-Synchronizing Import Parser:** Resolving internal alignment shifts and epoch offsets when converting scanned device logs back to CSV.

The native tool matches the original compiler outputs **100% byte-for-byte identically** (excluding compile-time timestamps).

---

## 1. Repository Directory Structure

*   **[`dla_tool.py`](dla_tool.py)**: The core native compiler. Supports converting text lists to PalmDB catalogs, and parsing scanned uploads back to CSV.
*   **[`build_all_floors.sh`](build_all_floors.sh)**: Master automation script that queries a Koha ILS database via SSH, downloads shelf lists for all floors (A-F), and natively compiles them.
*   **[`execute_export_final.sh`](execute_export_final.sh)**: Main automation script executing the full GUI export flow under Wine to generate final catalog databases.
*   **[`parity_verification_report.md`](parity_verification_report.md)**: Detailed byte-level parity results, MD5 checksum comparisons, and automated Wine-based regression testing.
*   **[`docs/`](docs/)**: Operational documentation for deploying and configuring the original legacy 3M client on a clean Windows/Wine machine.
    *   **[`docs/README.md`](docs/README.md)**: Operations & Setup Guide.
    *   **[`docs/images/`](docs/images/)**: Capture logs of the original user interface.
*   **[`wine_scripts/`](wine_scripts/)**: Auxiliary scripts for reverse engineering, verification, and Wine-based automation.
    *   **[`wine_scripts/README.md`](wine_scripts/README.md)**: Detailed documentation of all Wine and verification scripts.

---

## 2. Using `dla_tool.py` (Native Compiler)

The native tool requires only Python 3 and has no external dependencies.

### Export (Compile catalog database from `.tab` text file)
```bash
python3 dla_tool.py export <input_file.tab> <output_directory>
```
*   **Input format:** Tab-separated file with fields: `Barcode \t Callnumber \t Title`
*   **Output structure:** Generates a folder structured with:
    *   `000-3MLH.pdb`: Segment master catalog with spacing metadata.
    *   `id01/001-3MLH.pdX` (and subsequent segments): Barcode indexes (dynamic 14 or 16-byte record layout).
    *   `md01/001d-3MLH.pdb` (and subsequent segments): Book detail strings (Title & Callnumber) with individual field-level null padding.
    *   `ndex/3F3F4431/` and `ndex/3F3F4432/`: Title and Callnumber search mapping tables.

---

### Export Pull List (Compile hold/pull lists to DLA card database)
```bash
python3 dla_tool.py export-pull <input_file.tab> <output_file.pdb> [--description <name>]
```
*   **Input format:** Tab-separated file with fields: `Barcode \t Callnumber \t Title`
*   **Output structure:** Generates a single PalmOS database file `PL*.pdb` and automatically creates/updates the `PL000.tmp` index file inside the same directory (both must be loaded into the `pull/` directory on the CompactFlash memory card for the handheld reader to display and read them).

---

### Import (Extract scanned barcodes from uploaded handheld `.pdX` files)
```bash
python3 dla_tool.py import <uploaded_001.pdX> <output_scans.csv>
```
Converts the scanned files uploaded from the handheld reader back into a standard CSV showing sequence numbers, raw timestamps, and scanned barcodes.

---

### Import Pull Results (Deduce Pulled/Not Pulled items from returned card pull database)
```bash
python3 dla_tool.py import-pull <original_file> <card_file.pdb> <output_prefix>
```
*   **Original File:** The original pull list (can be the original tab-delimited text list `.tab` or the originally compiled database `.pdb`).
*   **Card File:** The modified/returned PalmOS database `PL*.pdb` retrieved from the `pull/` folder on the card after shelf reading.
*   **Output Files:** Automatically compares the two states and outputs:
    *   `<output_prefix>_pulled.txt`: Barcodes of items that were successfully found and pulled from the shelf.
    *   `<output_prefix>_not_pulled.txt`: Barcodes of items that were not found and remain on the pull list.

---

## 3. Parity Verification
For detailed byte-level parity results, MD5 checksum comparisons, and automated Wine-based regression testing, please refer to the dedicated **[Parity Verification Report](parity_verification_report.md)**.
