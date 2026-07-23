import struct
import os

original_dir = "/home/dpavlin/DLA/F/Database"
compiled_dir = "/home/dpavlin/DLA_floors/F/Database"

def parse_pdx(filepath):
    entries = []
    if not os.path.exists(filepath):
        return entries
    with open(filepath, "rb") as f:
        header = f.read(78)
        num_records, = struct.unpack(">H", header[76:78])
        for _ in range(num_records):
            entry = f.read(16)
            if len(entry) < 16:
                break
            barcode = entry[:11].split(b"\x00")[0].decode("ascii", errors="ignore")
            segment = entry[11]
            shelf_idx = struct.unpack(">I", entry[12:16])[0]
            entries.append((barcode, segment, shelf_idx))
    return entries

def parse_pdb(filepath):
    records = []
    if not os.path.exists(filepath):
        return records
    with open(filepath, "rb") as f:
        header = f.read(78)
        num_records, = struct.unpack(">H", header[76:78])
        offsets = []
        for _ in range(num_records):
            offsets.append(struct.unpack(">I", f.read(4))[0])
            f.read(4) # skip attrib/id
            
        for i in range(num_records):
            start = offsets[i]
            end = offsets[i+1] if i+1 < num_records else os.path.getsize(filepath)
            f.seek(start)
            data = f.read(end - start)
            text = data.decode("utf-8", errors="ignore").strip()
            records.append(text)
    return records

print("=== Comparing Index (.pdX) Files ===")
for i in range(1, 7):
    orig_pdx_path = os.path.join(original_dir, "id01", f"{i:03d}-3MLH.pdX")
    comp_pdx_path = os.path.join(compiled_dir, "id01", f"{i:03d}-3MLH.pdX")
    
    orig_pdx = parse_pdx(orig_pdx_path)
    comp_pdx = parse_pdx(comp_pdx_path)
    
    print(f"Segment {i:02d} Index (.pdX):")
    print(f"  Original entries count: {len(orig_pdx)}")
    print(f"  Compiled entries count: {len(comp_pdx)}")
    
    if len(orig_pdx) == len(comp_pdx):
        # Compare first and last 3 entries
        mismatches = 0
        for idx in range(len(orig_pdx)):
            if orig_pdx[idx] != comp_pdx[idx]:
                mismatches += 1
                if mismatches <= 3:
                    print(f"    Mismatch at index {idx}: Original={orig_pdx[idx]}, Compiled={comp_pdx[idx]}")
        if mismatches == 0:
            print("  [OK] Index entries are identical!")
        else:
            print(f"  [WARNING] Found {mismatches} mismatches out of {len(orig_pdx)} entries.")
    else:
        print("  [ERROR] Record count difference in index file!")

print("\n=== Comparing Data (.pdb) Files ===")
for i in range(1, 7):
    orig_pdb_path = os.path.join(original_dir, "md01", f"{i:03d}d-3MLH.pdb")
    comp_pdb_path = os.path.join(compiled_dir, "md01", f"{i:03d}d-3MLH.pdb")
    
    orig_pdb = parse_pdb(orig_pdb_path)
    comp_pdb = parse_pdb(comp_pdb_path)
    
    print(f"Segment {i:02d} Data (.pdb):")
    print(f"  Original records count: {len(orig_pdb)}")
    print(f"  Compiled records count: {len(comp_pdb)}")
    
    if len(orig_pdb) == len(comp_pdb):
        mismatches = 0
        for idx in range(len(orig_pdb)):
            if orig_pdb[idx] != comp_pdb[idx]:
                mismatches += 1
                if mismatches <= 3:
                    print(f"    Mismatch at index {idx}:\n      Original='{orig_pdb[idx]}'\n      Compiled='{comp_pdb[idx]}'")
        if mismatches == 0:
            print("  [OK] Data records are identical!")
        else:
            print(f"  [WARNING] Found {mismatches} mismatches out of {len(orig_pdb)} records.")
    else:
        print("  [ERROR] Record count difference in data file!")
