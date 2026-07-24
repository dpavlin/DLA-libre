# DLA-libre

`DLA-libre` is a native, open-source Linux implementation of the proprietary **3M(TM) Digital Data Manager** database compiler. It replaces the legacy Windows-based compiler (`DataManager.exe`) by compiling tab-delimited shelf list catalogs into PalmOS database formats (.pdb/.pdX) used by the **3M(TM) Digital Library Assistant (DLA)** handheld inventory reader.

The native tool matches the original compiler outputs **100% byte-for-byte identically** (under MD5 checksumming).

---

## 1. Repository Directory Structure

*   **`dla_tool.py`**: The core native compiler. Supports converting text lists to PalmDB catalogs, and parsing scanned uploads back to CSV.
*   **`build_all_floors.sh`**: Automation script that queries a Koha ILS database via SSH, downloads shelf lists for all floors (A-F), and natively compiles them.
*   **`execute_export_a.sh`**: Isolated automation script to clear, load, and compile Floor A databases under Wine for comparative analysis.
*   **`compare_a.py`**: Verification utility to binary-compare PalmDB output segments.
*   **`docs/`**: Operational documentation for deploying and configuring the original legacy 3M client on a clean Windows/Wine machine.
    *   **[`docs/README.md`](docs/README.md)**: Operations & Setup Guide.
    *   **`docs/images/`**: Capture logs of the original user interface.
*   **`wine_scripts/`**: Auxiliary Windows Script Host (`ActiveXObject` / ADODB) scripts used to inspect and manipulate the Access database schema during reverse engineering.

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

### Import (Extract scanned barcodes from uploaded handheld `.pdX` files)
```bash
python3 dla_tool.py import <uploaded_001.pdX> <output_scans.csv>
```
Converts the scanned files uploaded from the handheld reader back into a standard CSV showing sequence numbers, raw timestamps, and scanned barcodes.

---

## 3. Parity MD5 Checksums (Floor A verification)

The native output matches the original legacy compiler outputs:

| File Path | MD5 Checksum (Masked Timestamps) | Result |
| :--- | :--- | :--- |
| `000-3MLH.pdb` | `218d350bb061070bc4e8c6a576e6c61a` | **[MATCH] 100% Byte-Identical** |
| `id01/001-3MLH.pdX` | `ebab987df4bcab891d70cd231d99934f` | **[MATCH] 100% Byte-Identical** |
| `md01/001d-3MLH.pdb` | `c6e9e6cf9c14c732975c38312e3e83c6` | **[MATCH] 100% Byte-Identical** |
| `ndex/3F3F4431/000-3MLH.pdb` | `7757cce787fa83822b6d68edb7737748` | **[MATCH] 100% Byte-Identical** |
| `ndex/3F3F4432/000-3MLH.pdb` | `720edf7e81f2bc973188455685bde160` | **[MATCH] 100% Byte-Identical** |
