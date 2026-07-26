#!/usr/bin/env python3
"""
Examine SO (Shelf Order) and RE (Relative/Hold) fields in DLA PalmOS databases.

Reads actual Wine-generated .pdb files and extracts SO/RE values from every record,
then compares them against native compiler output.

This script helps us understand:
- What SO values are actually stored (not just zero)
- What RE values mean (hold type, circulation status, etc.)
- How the native compiler should encode these fields
"""

import struct
import os
import sys
from collections import defaultdict, Counter

# Paths to Wine-generated databases
WINE_PULL_DB = "/home/dpavlin/DLA/Card/pull/PL001.pdb"
WINE_CARD_DB = "/home/dpavlin/DLA/Card/Database"

# Paths to native-generated databases (from previous runs)
NATIVE_PULL_DB = "/tmp/PL001_native.pdb"
NATIVE_FLOOR_A_DB = "/home/dpavlin/DLA_floors/A/Database"


def parse_pdb_header(data):
    """Parse the 78-byte PalmOS PDB header."""
    return {
        "name": data[0:32].split(b"\x00")[0].decode("ascii", errors="replace"),
        "attributes": struct.unpack(">H", data[32:34])[0],
        "version": struct.unpack(">H", data[34:36])[0],
        "create_time": struct.unpack(">I", data[36:40])[0],
        "modify_time": struct.unpack(">I", data[40:44])[0],
        "backup_time": struct.unpack(">I", data[44:48])[0],
        "modify_num": struct.unpack(">I", data[48:52])[0],
        "app_info_offset": struct.unpack(">I", data[52:56])[0],
        "sort_info_offset": struct.unpack(">I", data[56:60])[0],
        "type": data[60:64].decode("ascii", errors="replace"),
        "creator": data[64:68].decode("ascii", errors="replace"),
        "unique_id_seed": struct.unpack(">I", data[68:72])[0],
        "next_rec_list": struct.unpack(">I", data[72:76])[0],
        "num_records": struct.unpack(">H", data[76:78])[0],
    }


def parse_tagged_record(data, pos, max_fields=10):
    """Parse a tagged record starting at pos.
    
    PalmOS tagged record format:
    - 2 bytes header: flags (4 bits) + num_fields (4 bits)
    - For each field:
      - 2-byte tag (ASCII)
      - 1-byte attribute
      - 1-byte length
      - length-byte value
      - optional padding byte (to make field length even)
    
    Returns list of (tag, attr, length, value) tuples.
    """
    if pos + 2 > len(data):
        return None
    
    rec_header = struct.unpack(">BB", data[pos:pos+2])
    num_fields = rec_header[1] & 0x0f
    flags = rec_header[1] >> 4
    
    fields = []
    pos += 2
    
    for i in range(min(num_fields, max_fields)):
        if pos + 4 > len(data):
            break
        tag = data[pos:pos+2].decode("ascii", errors="replace")
        pos += 2
        attr = data[pos]; pos += 1
        length = data[pos]; pos += 1
        value = data[pos:pos+length]
        pos += length
        # Pad to even boundary
        if length % 2 != 0:
            pos += 1
        fields.append((tag, attr, length, value))
    
    return fields


def extract_records_from_pdb(pdb_path):
    """Extract all records from a PDB file."""
    if not os.path.exists(pdb_path):
        print(f"  [SKIP] {pdb_path} not found")
        return []
    
    with open(pdb_path, "rb") as f:
        data = f.read()
    
    header = parse_pdb_header(data)
    print(f"  File: {os.path.basename(pdb_path)}")
    print(f"  Records: {header['num_records']}, AppInfo offset: {header['app_info_offset']}")
    
    records = []
    for i in range(header["num_records"]):
        offset = 78 + i * 8
        rec_offset = struct.unpack(">I", data[offset:offset+4])[0]
        rec_attr = struct.unpack(">I", data[offset+4:offset+8])[0]
        
        fields = parse_tagged_record(data, rec_offset)
        if fields:
            records.append({
                "index": i,
                "offset": rec_offset,
                "attr": rec_attr,
                "fields": fields,
            })
    
    return records


def get_field(records, field_name):
    """Get a specific field from records, returning (index, attr, value) tuples."""
    results = []
    for rec in records:
        for tag, attr, length, value in rec["fields"]:
            if tag == field_name:
                results.append({
                    "index": rec["index"],
                    "offset": rec["offset"],
                    "attr": attr,
                    "length": length,
                    "value": value,
                })
                break
    return results


def analyze_so_re(records, source_label):
    """Analyze SO and RE fields in a set of records."""
    print(f"\n{'='*70}")
    print(f"  {source_label}")
    print(f"{'='*70}")
    
    so_records = get_field(records, "SO")
    re_records = get_field(records, "RE")
    id_records = get_field(records, "ID")
    d1_records = get_field(records, "D1")
    
    print(f"\n  Total records: {len(records)}")
    print(f"  Records with SO field: {len(so_records)}")
    print(f"  Records with RE field: {len(re_records)}")
    print(f"  Records with ID field: {len(id_records)}")
    
    if so_records:
        print(f"\n  --- SO Field Analysis ---")
        
        # Show first 10 SO values
        print(f"\n  First 10 SO values:")
        for so in so_records[:10]:
            value = so["value"]
            # Try to interpret as different integer types
            try:
                val_int = struct.unpack(">I", value)[0]
            except:
                val_int = -1
            
            barcode = ""
            id_field = get_field([records[so["index"]]], "ID")
            if id_field:
                barcode = id_field[0]["value"].decode("ascii", errors="replace")
            
            print(f"    [{so['index']:3d}] offset={so['offset']:6d}, attr=0x{so['attr']:02x}, "
                  f"len={so['length']:2d}, value={value.hex()}, as_int={val_int:6d}, "
                  f"raw={value!r}, barcode={barcode}")
        
        # Value distribution
        so_values = []
        for so in so_records:
            try:
                val = struct.unpack(">I", so["value"])[0]
                so_values.append(val)
            except:
                so_values.append(-1)
        
        print(f"\n  SO value distribution:")
        so_counter = Counter(so_values)
        for val, count in sorted(so_counter.items())[:20]:
            if val == -1:
                print(f"    Invalid: {count} records")
            else:
                print(f"    0x{val:08x} ({val:6d}): {count} records")
        
        print(f"\n  Unique SO values: {len(so_counter)}")
        print(f"  Min: {min(so_values) if so_values else 'N/A'}")
        print(f"  Max: {max(so_values) if so_values else 'N/A'}")
        
        # Check if SO values match shelf order
        if so_values and len(so_values) > 1:
            unique_sorted = sorted(set(so_values))
            print(f"\n  First 20 unique SO values (sorted): {unique_sorted[:20]}")
            
            # Check if they're sequential
            is_sequential = all(unique_sorted[i+1] - unique_sorted[i] == 1 
                                for i in range(min(5, len(unique_sorted)-1)))
            print(f"  Sequential (first 20): {is_sequential}")
    
    if re_records:
        print(f"\n  --- RE Field Analysis ---")
        
        print(f"\n  First 10 RE values:")
        for re_field in re_records[:10]:
            value = re_field["value"]
            try:
                val_int = struct.unpack(">I", value)[0]
            except:
                val_int = -1
            print(f"    [{re_field['index']:3d}] offset={re_field['offset']:6d}, "
                  f"attr=0x{re_field['attr']:02x}, len={re_field['length']:2d}, "
                  f"value={value.hex()}, as_int={val_int:6d}, raw={value!r}")
        
        # Value distribution
        re_values = []
        for re_field in re_records:
            try:
                val = struct.unpack(">I", re_field["value"])[0]
                re_values.append(val)
            except:
                re_values.append(-1)
        
        print(f"\n  RE value distribution:")
        re_counter = Counter(re_values)
        for val, count in sorted(re_counter.items())[:10]:
            if val == -1:
                print(f"    Invalid: {count} records")
            else:
                print(f"    0x{val:08x} ({val:6d}): {count} records")
        
        print(f"\n  Unique RE values: {len(re_counter)}")
        
        # Show all unique RE values
        unique_re = sorted(set(re_values))
        print(f"\n  All unique RE values:")
        for val in unique_re[:20]:
            if val == -1:
                print(f"    Invalid: appears in {re_counter[val]} records")
            else:
                print(f"    0x{val:08x} ({val:6d}): {re_counter[val]} records")
    
    # Show a complete record example
    if records:
        print(f"\n  --- Complete Record Example (first record) ---")
        rec = records[0]
        print(f"    Offset: {rec['offset']}")
        for tag, attr, length, value in rec["fields"]:
            print(f"    Field: {tag}, attr=0x{attr:02x}, len={length}, value={value!r}")


def compare_wine_vs_native(wine_pdb, native_pdb):
    """Compare SO and RE fields between Wine and native outputs."""
    print(f"\n\n{'#'*70}")
    print(f"  COMPARISON: Wine vs Native")
    print(f"{'#'*70}")
    
    wine_records = extract_records_from_pdb(wine_pdb)
    native_records = extract_records_from_pdb(native_pdb)
    
    if not wine_records or not native_records:
        print("  Cannot compare: one or both files missing")
        return
    
    print(f"\n  Wine: {len(wine_records)} records")
    print(f"  Native: {len(native_records)} records")
    
    # Compare SO fields
    wine_so = get_field(wine_records, "SO")
    native_so = get_field(native_records, "SO")
    
    print(f"\n  SO Field Comparison:")
    print(f"    Wine has {len(wine_so)} SO fields")
    print(f"    Native has {len(native_so)} SO fields")
    
    if wine_so and native_so:
        mismatches = 0
        for i, (w_so, n_so) in enumerate(zip(wine_so, native_so)):
            if w_so["value"] != n_so["value"]:
                mismatches += 1
                if mismatches <= 5:
                    print(f"    [{i}] Wine={w_so['value']!r} Native={n_so['value']!r}")
        
        if mismatches == 0:
            print(f"    ✅ SO fields are IDENTICAL for all {len(wine_so)} records")
        else:
            print(f"    ⚠️  SO fields differ in {mismatches}/{len(wine_so)} records")
    
    # Compare RE fields
    wine_re = get_field(wine_records, "RE")
    native_re = get_field(native_records, "RE")
    
    print(f"\n  RE Field Comparison:")
    print(f"    Wine has {len(wine_re)} RE fields")
    print(f"    Native has {len(native_re)} RE fields")
    
    if wine_re and native_re:
        mismatches = 0
        for i, (w_re, n_re) in enumerate(zip(wine_re, native_re)):
            if w_re["value"] != n_re["value"]:
                mismatches += 1
                if mismatches <= 5:
                    print(f"    [{i}] Wine={w_re['value']!r} Native={n_re['value']!r}")
        
        if mismatches == 0:
            print(f"    ✅ RE fields are IDENTICAL for all {len(wine_re)} records")
        else:
            print(f"    ⚠️  RE fields differ in {mismatches}/{len(wine_re)} records")


def analyze_floor_a_pdx():
    """Analyze SO values from the barcode index (.pdX) files."""
    print(f"\n{'='*70}")
    print(f"  FLOOR A: Barcode Index (.pdX) Analysis")
    print(f"{'='*70}")
    
    floor_a_id = os.path.join(NATIVE_FLOOR_A_DB, "id01")
    if not os.path.exists(floor_a_id):
        print(f"  [SKIP] {floor_a_id} not found")
        return
    
    for pdx_file in sorted(os.listdir(floor_a_id)):
        if not pdx_file.endswith(".pdX"):
            continue
        
        pdx_path = os.path.join(floor_a_id, pdx_file)
        with open(pdx_path, "rb") as f:
            data = f.read()
        
        header = parse_pdb_header(data)
        num_records = header["num_records"]
        
        print(f"\n  {pdx_file}: {num_records} records")
        
        # Parse index entries
        # Format depends on record size (14-byte or 16-byte)
        # 10-byte barcode + 2-byte flags + 2/4-byte shelf order
        if num_records > 0:
            # Determine record size from first entry
            entry = data[78:78+14]
            flags = struct.unpack(">BB", entry[10:12])[0]
            # Try 14-byte record first
            shelf_idx_14 = struct.unpack(">H", entry[12:14])[0]
            
            # Check if we should use 16-byte records
            # The idff block in AppInfo tells us, but let's just try both
            print(f"    Entry format: flags=0x{flags:02x}, 14-byte shelf_idx={shelf_idx_14}")
            
            # Extract first 5 entries
            for i in range(min(5, num_records)):
                entry_start = 78 + i * 14
                entry = data[entry_start:entry_start+14]
                barcode = entry[:10].decode("ascii", errors="replace")
                flags = struct.unpack(">BB", entry[10:12])[0]
                shelf_idx = struct.unpack(">H", entry[12:14])[0]
                print(f"    [{i:3d}] barcode={barcode}, flags=0x{flags:02x}, shelf_idx={shelf_idx}")
            
            # Extract all shelf indices
            shelf_indices = []
            record_size = 16 if header.get("type") == "3MLH" and num_records > 65535 else 14
            
            for i in range(num_records):
                entry_start = 78 + i * 14
                if entry_start + 14 > len(data):
                    break
                entry = data[entry_start:entry_start+14]
                shelf_idx = struct.unpack(">H", entry[12:14])[0]
                shelf_indices.append(shelf_idx)
            
            unique_indices = sorted(set(shelf_indices))
            print(f"    Unique shelf indices: {len(unique_indices)}")
            print(f"    First 20: {unique_indices[:20]}")
            
            # Check if they match record positions
            is_position_match = all(
                unique_indices[i] == i + 1 for i in range(min(20, len(unique_indices)))
            )
            print(f"    Shelf indices match record positions (1-based): {is_position_match}")


def main():
    print("=" * 70)
    print("  DLA SO/RE Field Examination Script")
    print("=" * 70)
    
    # 1. Analyze Wine pull list
    print("\n\n[1] WINE PULL LIST DATABASE")
    wine_records = extract_records_from_pdb(WINE_PULL_DB)
    if wine_records:
        analyze_so_re(wine_records, "Wine Pull List (150 items)")
    
    # 2. Analyze Wine card database (Floor A)
    print(f"\n\n[2] WINE CARD DATABASE (Floor A)")
    floor_a_pdb = os.path.join(WINE_CARD_DB, "000-3MLH.pdb")
    wine_floor_records = extract_records_from_pdb(floor_a_pdb)
    if wine_floor_records:
        analyze_so_re(wine_floor_records, "Wine Floor A Master Catalog")
    
    # 3. Analyze native pull list (if exists)
    print(f"\n\n[3] NATIVE PULL LIST DATABASE")
    native_records = extract_records_from_pdb(NATIVE_PULL_DB)
    if native_records:
        analyze_so_re(native_records, "Native Pull List (150 items)")
    
    # 4. Compare Wine vs Native pull list
    compare_wine_vs_native(WINE_PULL_DB, NATIVE_PULL_DB)
    
    # 5. Analyze Floor A .pdX index
    analyze_floor_a_pdx()
    
    # 6. Summary
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"""
  Key Questions Answered:
  1. What are SO values? → Check above (shelf order numbers)
  2. What are RE values? → Check above (hold type/circulation status)
  3. Does native match Wine? → Check comparison section
  4. Are SO/RE correctly encoded? → Check comparison section
  
  Next Steps:
  - If SO is just shelf order, native should use shelf_idx + 1
  - If RE is hold type, need to determine encoding from Wine data
  - Update dla_tool.py if fields don't match
""")


if __name__ == "__main__":
    main()
