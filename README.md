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

---

## 4. 3M DLA PDB Record Format Analysis

### Pull List Records (3MPL Type)

Pull list `.pdb` files use a 5-field tagged record format:

| Field | Attribute | Type | Description |
|-------|-----------|------|-------------|
| **ID** | `0x2a` | variable-length ASCII | Barcode (Item ID) |
| **SO** | `0x0c` | 4-byte big-endian uint32 | Shelf Order number |
| **RE** | `0x0c` | 4-byte big-endian uint32 | Relative/Hold type |
| **D1** | `0x2a` | variable-length ASCII | Primary Info (display text) |
| **D2** | `0x2a` | variable-length ASCII | Secondary Info (display text) |

### Device Scan Records (3MLL Type)

The RFID reader collects data during inventory scans. The upload files (`upload/inv/001.pdX`) contain:

| Field | Size | Description |
|-------|------|-------------|
| **SequenceNumber** | 2 bytes | Scan sequence counter |
| **Timestamp** | 4 bytes | PalmOS epoch timestamp |
| **Barcode** | 26 bytes | Item barcode (ASCII, null-padded) |
| **Total** | 32 bytes | Per record |

The library's `cmd_import` function successfully parses these files from historic inventura data (2018), extracting all scanned barcodes with timestamps.

### SO and RE Fields

**Current status:** All analyzed pull list PDB files show `SO=0x00000000` and `RE=0x00000000` for every record.

**Evidence:**
- Wine-generated `PL001.pdb` (150 records, 3M Data Manager v3.00): SO=0, RE=0
- E2 test export `PL001.pdb` (165 records): SO=0, RE=0
- Historic inventura data (2018): No pull list `.pdb` files found
- Device upload files: SO/RE not collected during scan

**Research performed:**
- Searched 3M Data Format Guide v3.00 (3788 lines): No SO/RE documentation
- Searched DLA User Guide (7308 lines): No SO/RE field definitions
- Searched Handheld User Guide (1234 lines): No SO/RE field definitions
- Examined Wine database tables (Format, ImpPullFormats, UploadFormat): No SO/RE parameters
- Parsed 100+ historic inventura upload files from 2018 using library's `cmd_import`

**Key finding:** The RFID reader does NOT collect SO/RE data during scans. SO/RE are populated during export, not during device scan.

**Possible explanations:**
1. SO/RE are populated by the 3M Conversion Station (not Data Manager export)
2. SO/RE are reserved for future 3M device features
3. SO/RE are used internally by the DLA during shelf-order checking (not exported)
4. SO/RE contain circulation status data (hold type, security status, etc.)

### 🔴 ACTION REQUIRED: Device Verification

**The SO and RE field values must be verified using an actual 3M DLA device:**

1. **Export a pull list from Data Manager** and load it onto a CompactFlash card
2. **Load the card into the DLA device** and run the "Pull Items" function
3. **Pull a few items** and save the results to the card
4. **Import the results back into Data Manager** and examine the saved `.pdb` file
5. **Check if SO/RE fields changed** after the device read/interacted with the list

**Alternative verification methods:**
- Use a 3M DLA device to scan a shelf-order list and check if SO values are populated in the device's internal records
- Check if the DLA's "Check Shelf Order" function uses SO values for ordering comparison
- Examine pull-list results `.pdb` files saved by the device after a pull session

**Impact on native compiler:**
- If SO/RE are simply placeholders: Current implementation (SO=0, RE=0) is correct ✅
- If SO contains shelf order positions: Need to populate from barcode index `.pdX` shelf_idx
- If RE contains circulation/hold status: Need to determine encoding from device data

For analysis scripts, see [`dla_pdb.py`](dla_pdb.py) and [`wine_scripts/examine_so_re.py`](wine_scripts/examine_so_re.py).
