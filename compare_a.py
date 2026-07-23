import os
import struct

wine_db_dir = "/home/dpavlin/DLA/Card/Database"
native_db_dir = "/home/dpavlin/DLA_floors/A/Database"

def parse_header(path):
    with open(path, "rb") as f:
        data = f.read(78)
        if len(data) < 78:
            return None
        name, attrib, version, create_time, mod_time, backup_time, mod_num, app_info, sort_info, type_str, creator_str, unique_id_seed, next_rec, num_records = struct.unpack(">32sHHIIIIII4s4sIIH", data)
        return {
            "name": name.split(b"\x00")[0].decode("ascii", errors="ignore"),
            "type": type_str.decode("ascii", errors="ignore"),
            "creator": creator_str.decode("ascii", errors="ignore"),
            "num_records": num_records
        }

def read_pdx(path):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "rb") as f:
        header = f.read(78)
        num_records, = struct.unpack(">H", header[76:78])
        for _ in range(num_records):
            entry = f.read(14)
            if len(entry) < 14:
                break
            barcode = entry[:10].decode("ascii", errors="ignore").strip()
            byte10 = entry[10]
            byte11 = entry[11]
            zone = entry[12]
            slot = entry[13]
            entries.append((barcode, byte10, byte11, zone, slot))
    return entries

def read_pdb_records(path):
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "rb") as f:
        header = f.read(78)
        num_records, = struct.unpack(">H", header[76:78])
        offsets = []
        for _ in range(num_records):
            offsets.append(struct.unpack(">I", f.read(4))[0])
            f.read(4) # skip attrib/unique id
        for i in range(num_records):
            start = offsets[i]
            end = offsets[i+1] if i+1 < num_records else os.path.getsize(path)
            f.seek(start)
            data = f.read(end - start)
            records.append(data)
    return records

def read_ndex_pdx(path):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "rb") as f:
        header = f.read(78)
        num_records, = struct.unpack(">H", header[76:78])
        for _ in range(num_records):
            entry = f.read(4)
            if len(entry) < 4:
                break
            val, = struct.unpack(">I", entry)
            entries.append(val)
    return entries

def compare_file(rel_path, read_func=None):
    w_path = os.path.join(wine_db_dir, rel_path)
    n_path = os.path.join(native_db_dir, rel_path)
    
    print(f"\n--- Comparing {rel_path} ---")
    if not os.path.exists(w_path):
        print(f"  [ERROR] Wine file missing: {w_path}")
        return
    if not os.path.exists(n_path):
        print(f"  [ERROR] Native file missing: {n_path}")
        return
        
    w_size = os.path.getsize(w_path)
    n_size = os.path.getsize(n_path)
    print(f"  Size: Wine={w_size} bytes | Native={n_size} bytes")
    
    w_hdr = parse_header(w_path)
    n_hdr = parse_header(n_path)
    print(f"  Header: Wine={w_hdr} | Native={n_hdr}")
    
    if read_func:
        w_data = read_func(w_path)
        n_data = read_func(n_path)
        print(f"  Record/Entry count: Wine={len(w_data)} | Native={len(n_data)}")
        if len(w_data) != len(n_data):
            print("  [ERROR] Mismatch in entry counts!")
        else:
            mismatches = 0
            for idx in range(len(w_data)):
                if w_data[idx] != n_data[idx]:
                    mismatches += 1
                    if mismatches <= 5:
                        print(f"    Mismatch at idx {idx}: Wine={w_data[idx]!r} | Native={n_data[idx]!r}")
            if mismatches == 0:
                print("  [SUCCESS] Entries are identical!")
            else:
                print(f"  [ERROR] Found {mismatches} mismatches!")
    else:
        # Binary comparison of the entire file excluding the creation/modification times in header (bytes 34-44)
        w_bytes = open(w_path, "rb").read()
        n_bytes = open(n_path, "rb").read()
        if len(w_bytes) != len(n_bytes):
            print("  [ERROR] Binary sizes differ!")
        else:
            # Mask out timestamps in header (bytes 34-44)
            w_masked = bytearray(w_bytes)
            n_masked = bytearray(n_bytes)
            for i in range(34, 44):
                w_masked[i] = 0
                n_masked[i] = 0
                
            # If it is 000-3MLH.pdb, mask out cafn dynamic timestamps as well
            if rel_path == "000-3MLH.pdb":
                # CAFN timestamp 1 is at bytes 86 + 12 + 44 + 34 + 56 + 56 + 14 = 272 (approx)
                # Let us locate the "CAFN" signature and mask out the 4 bytes at offset + 14 and offset + 42
                idx = w_masked.find(b"CAFN")
                if idx != -1:
                    w_masked[idx+14 : idx+18] = b"\x00"*4
                    w_masked[idx+42 : idx+46] = b"\x00"*4
                idx_n = n_masked.find(b"CAFN")
                if idx_n != -1:
                    n_masked[idx_n+14 : idx_n+18] = b"\x00"*4
                    n_masked[idx_n+42 : idx_n+46] = b"\x00"*4
                    
            if w_masked == n_masked:
                print("  [SUCCESS] Files are binary identical (excluding header timestamps)!")
            else:
                diffs = [i for i in range(len(w_masked)) if w_masked[i] != n_masked[i]]
                print(f"  [ERROR] Binary mismatch at {len(diffs)} positions! First few diff offsets: {diffs[:10]}")

compare_file("000-3MLH.pdb")
compare_file("id01/001-3MLH.pdX", read_pdx)
compare_file("md01/001d-3MLH.pdb", read_pdb_records)
compare_file("ndex/3F3F4431/000-3MLH.pdb", read_pdb_records)
compare_file("ndex/3F3F4431/id01/001-3MLH.pdX", read_ndex_pdx)
compare_file("ndex/3F3F4432/000-3MLH.pdb", read_pdb_records)
compare_file("ndex/3F3F4432/id01/001-3MLH.pdX", read_ndex_pdx)
