#!/bin/bash
# Script to export all floors from Koha and compile them into DLA card databases

set -e

FLOORS=("A" "B" "C" "D" "E" "F")
OUTPUT_BASE="/home/dpavlin/DLA_floors"
DLA_TOOL="/home/dpavlin/dla_tool.py"

echo "=========================================================="
echo "Starting Koha Export & DLA Database Compilation"
echo "=========================================================="
echo "Timestamp: $(date -R)"
echo ""

mkdir -p "$OUTPUT_BASE"

for FLOOR in "${FLOORS[@]}"; do
    echo "----------------------------------------------------------"
    echo "[*] Floor $FLOOR: Querying Koha Dev database..."
    TAB_FILE="/home/dpavlin/DLA/ShelfOrderList/${FLOOR}.tab"
    
    # Query Koha
    ssh ffzg.koha-dev.rot13.org "sudo koha-mysql ffzg -B -e \"
        SELECT barcode, itemcallnumber, title 
        FROM items 
        JOIN biblio ON biblio.biblionumber=items.biblionumber 
        WHERE itemcallnumber LIKE '${FLOOR}%' 
          AND location LIKE 'OP%' 
        ORDER BY itemcallnumber COLLATE 'utf8mb4_croatian_ci'
    \"" > "$TAB_FILE"
    
    LINE_COUNT=$(wc -l < "$TAB_FILE")
    echo "[+] Floor $FLOOR: Exported $LINE_COUNT items to $TAB_FILE"
    
    # Compile with dla_tool
    OUT_DIR="$OUTPUT_BASE/$FLOOR"
    echo "[*] Floor $FLOOR: Compiling to DLA card database format at $OUT_DIR..."
    rm -rf "$OUT_DIR"
    mkdir -p "$OUT_DIR"
    
    python3 "$DLA_TOOL" export "$TAB_FILE" "$OUT_DIR"
    
    # Verification
    PDB_COUNT=$(find "$OUT_DIR" -name "*.pdb" -o -name "*.pdX" | wc -l)
    echo "[SUCCESS] Floor $FLOOR: Compiled database. Generated $PDB_COUNT files."
    echo ""
done

echo "=========================================================="
echo "All floors processed successfully!"
echo "Outputs are located under: $OUTPUT_BASE/"
echo "=========================================================="
