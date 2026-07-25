#!/usr/bin/env python3
import os
import sys
import struct
import math
import time
import argparse
import csv
import datetime

def make_pdb_header(name: str, type_str: str, creator_str: str, num_records: int, app_info_data: bytes = None, palm_time: int = 4002121804) -> bytes:
    """Generate the standard 78-byte PalmOS PDB header with optional AppInfo support."""
    name_bytes = name.encode("ascii", errors="ignore")[:31].ljust(32, b"\x00")
    attributes = 0x0000
    version = 1
    
    app_info_offset = 78 + num_records * 8 if app_info_data else 0
    
    header = struct.pack(
        ">32sHHIIIIII4s4sIIH",
        name_bytes,
        attributes,
        version,
        palm_time,     # creation date
        palm_time,     # modification date
        0,             # backup date
        0,             # modification number
        app_info_offset,
        0,             # sort info offset
        type_str.encode("ascii")[:4],
        creator_str.encode("ascii")[:4],
        0,             # unique id seed
        0,             # next record list offset
        num_records
    )
    return header

def make_metadata_block(tag: str, data: bytes, has_flag: bool = True) -> bytes:
    """Serialize a metadata block inside the AppInfo structure."""
    tag_bytes = tag.encode("ascii")
    length = len(data)
    if has_flag:
        return tag_bytes + b"\x09\xff" + struct.pack(">H", length) + data
    else:
        return tag_bytes + struct.pack(">H", length) + data

def get_master_appinfo(total_records: int, list_name: str, palm_time: int = 4002121804) -> bytes:
    """Construct the 474-byte AppInfo block for 000-3MLH.pdb."""
    vers_data = b"\x02\x03\xa1\x2a\x3f\x3fID" + struct.pack(">I", total_records)
    vers_block = make_metadata_block("vers", vers_data, has_flag=False)
    
    idx_rec_size = 16 if total_records > 65535 else 14
    idff_data = b".pdX\x00" + bytes([idx_rec_size]) + b"\x00\x03\x3f\x3fID\x00\x2a\x00\x00\x00\x0a\x3f\x3fRE\x00\x8d\x00\x0a\x00\x02\x3f\x3fSO\x00\x0d\x00\x0c\x00\x02"
    idff_block = make_metadata_block("idff", idff_data, has_flag=False)
    
    daff_data = b".pdb\x00\x57\x00\x02\x3f\x3fD1\x00\x0a\x00\x00\x00\x00\x3f\x3fD2\x00\x0a\x00\x00\x00\x00"
    daff_block = make_metadata_block("daff", daff_data, has_flag=False)
    
    reld_data = b"\x2c\x0a\x00\x01" + b"Shelf Order".ljust(44, b"\x00")
    reld_block = make_metadata_block("RELD", reld_data, has_flag=True)
    
    cald_data = b"\x2c\x0a\x00\x01" + b"Default\x00am Files\\3M Library Systems\\Data Ma\x00"
    cald_block = make_metadata_block("CALD", cald_data, has_flag=True)
    
    # CAFN block containing compilation timestamp
    cafn_data = (
        b"\xa4\x0a\x00\x01\x00\x00\x00\x00" +
        struct.pack(">I", palm_time) +
        b"\x00\x00\xe3\xbc\xae\xe5\x99\x81\xe5\x8d\x83\xe6\x85\xb4\xe6\xa5\xb4\xe4\x81\xa3\x40\x00" +
        struct.pack(">I", palm_time) +
        b"\x00\x00\xe3\xbc\xae\xe5\x99\x81" +
        b"\x00" * 122
    )
    cafn_block = make_metadata_block("CAFN", cafn_data, has_flag=True)
    
    sold_data = b"\x2c\x0a\x00\x01" + list_name.encode("utf-8")[:43].ljust(44, b"\x00")
    sold_block = make_metadata_block("SOLD", sold_data, has_flag=True)
    
    reni_data = b"\x04\x0c\x00\x01" + struct.pack(">I", total_records)
    reni_block = make_metadata_block("RENI", reni_data, has_flag=True)
    
    soni_data = b"\x04\x0c\x00\x01" + struct.pack(">I", total_records)
    soni_block = make_metadata_block("SONI", soni_data, has_flag=True)
    
    app_info_data = b"\x40\x09" + vers_block + idff_block + daff_block + reld_block + cald_block + cafn_block + sold_block + reni_block + soni_block
    return app_info_data

def get_index_appinfo(total_records: int, is_callnumber: bool = False) -> bytes:
    """Construct the 54-byte AppInfo block for index catalogs."""
    index_tag = b"D2" if is_callnumber else b"D1"
    vers_data = b"\x02\x03\xa1\x0a\x3f\x3f" + index_tag + struct.pack(">I", total_records)
    vers_block = make_metadata_block("vers", vers_data, has_flag=False)
    
    idff_len_byte = b"\x26" if is_callnumber else b"\x32"
    idff_data = b".pdX\x00\x04\x00\x02\x3f\x3f" + index_tag + b"\x80\x0a\x00\x00\x00" + idff_len_byte + b"\x3f\x3fRR\x00\x0c\x00\x00\x00\x04"
    idff_block = make_metadata_block("idff", idff_data, has_flag=False)
    
    app_info_data = b"\x40\x02" + vers_block + idff_block
    return app_info_data

def get_clean_title(r):
    # Enforce exact database truncation rules: format then clean
    title_formatted = f"title: {r['title']}"[:40]
    return title_formatted[7:].replace("\"", "").replace("\x00", "").lower()

def get_clean_callnumber(r):
    # Enforce exact database truncation rules: format then clean
    call_formatted = f"callnumber: {r['callnumber']}"[:40]
    return call_formatted[12:].replace("\"", "").replace("\x00", "").lower()

def cmd_export(args):
    """Convert a tab-delimited shelf list into the DLA database format."""
    print(f"[*] Reading input file: {args.input_file}")
    records = []
    
    list_name = os.path.basename(args.input_file).split(".")[0]
    
    with open(args.input_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        if not lines:
            print("[-] Error: Empty input file.")
            sys.exit(1)
            
        start_row = 0
        first_row = lines[0].rstrip("\r\n").split("\t")
        if len(first_row) > 0 and first_row[0].lower() in ["barcode", "barcode_no"]:
            start_row = 1
            
        shelf_idx = 0
        for i in range(start_row, len(lines)):
            line = lines[i]
            row = line.rstrip("\r\n").split("\t")
            if len(row) < 3:
                continue
            def clean_csv_field(val):
                if val.startswith('"'):
                    val = val[1:]
                if val.endswith('"'):
                    val = val[:-1]
                return val
            
            barcode = row[0].strip()
            callnumber = clean_csv_field(row[1].strip())
            title = clean_csv_field(row[2].strip())
            
            if not barcode:
                continue
                
            records.append({
                "barcode": barcode,
                "callnumber": callnumber,
                "title": title,
                "shelf_idx": shelf_idx
            })
            shelf_idx += 1
            
    total_records = len(records)
    print(f"[+] Loaded {total_records} valid records in shelf order.")
    
    # Sort dataset alphabetically by barcode BEFORE segmenting
    records = sorted(records, key=lambda r: r["barcode"])
    
    max_items = args.max_items
    num_segments = math.ceil(total_records / max_items)
    print(f"[*] Splitting into {num_segments} segments (max {max_items} items per segment).")
    
    segments = [records[i:i + max_items] for i in range(0, total_records, max_items)]
    
    # Prepare directories
    db_dir = os.path.join(args.output_dir, "Database")
    id_dir = os.path.join(db_dir, "id01")
    md_dir = os.path.join(db_dir, "md01")
    
    ndex_title_dir = os.path.join(db_dir, "ndex", "3F3F4431")
    ndex_title_id = os.path.join(ndex_title_dir, "id01")
    
    ndex_call_dir = os.path.join(db_dir, "ndex", "3F3F4432")
    ndex_call_id = os.path.join(ndex_call_dir, "id01")
    
    for d in [id_dir, md_dir, ndex_title_id, ndex_call_id]:
        os.makedirs(d, exist_ok=True)
        
    master_records_data = []
    
    # Calculate global catalog spacing
    if total_records >= 16384:
        spacing = 256
    else:
        spacing = max(256, int(total_records / 9.45))
    
    # 1. Process and write segments
    for seg_idx in range(1, num_segments + 1):
        seg_records = segments[seg_idx - 1]
        records_count = len(seg_records)
        print(f"[*] Processing Segment {seg_idx:02d} ({records_count} items)...")
        
        # Sort alphabetically by barcode for barcode index and data
        sorted_records = sorted(seg_records, key=lambda r: r["barcode"])
        
        # 1a. Write the .pdX index file (14-byte records)
        pdx_filename = f"{seg_idx:03d}-3MLH.pdX"
        pdx_header = make_pdb_header(name=f"{seg_idx:03d}-3MLH", type_str="3MLH", creator_str="3MLH", num_records=records_count)
        
        use_4_byte_idx = (total_records > 65535)
        pdx_entries = []
        for r in sorted_records:
            barcode_bytes = r["barcode"].encode("ascii", errors="ignore")[:10].ljust(10, b"\x00")
            if use_4_byte_idx:
                entry = struct.pack(">10sBBI", barcode_bytes, 0x00, 0x01, r["shelf_idx"] + 1)
            else:
                entry = struct.pack(">10sBBH", barcode_bytes, 0x00, 0x01, r["shelf_idx"] + 1)
            pdx_entries.append(entry)
            
        pdx_data = pdx_header + b"".join(pdx_entries)
        with open(os.path.join(id_dir, pdx_filename), "wb") as f_pdx:
            f_pdx.write(pdx_data)
            
        # 1b. Write the .pdb data file
        pdb_filename = f"{seg_idx:03d}d-3MLH.pdb"
        pdb_header = make_pdb_header(name=f"{seg_idx:03d}d-3MLH", type_str="3MLH", creator_str="3MLH", num_records=records_count)
        
        record_buffers = []
        for r in sorted_records:
            title_formatted = f"title: {r['title']}"[:40]
            t_trunc = title_formatted[7:]
            call_formatted = f"callnumber: {r['callnumber']}"[:40]
            c_trunc = call_formatted[12:]
            
            title_bytes = f"title: {t_trunc}\x00".encode("utf-8", errors="ignore")
            if len(title_bytes) % 2 != 0:
                title_bytes += b"\x00"
                
            call_bytes = f"callnumber: {c_trunc}\x00".encode("utf-8", errors="ignore")
            if len(call_bytes) % 2 != 0:
                call_bytes += b"\x00"
                
            rec_bytes = title_bytes + call_bytes
            record_buffers.append(rec_bytes)
            
        dir_entries = []
        current_offset = 78 + records_count * 8
        for buf in record_buffers:
            dir_entries.append(struct.pack(">II", current_offset, 0))
            current_offset += len(buf)
            
        pdb_data = pdb_header + b"".join(dir_entries) + b"".join(record_buffers)
        with open(os.path.join(md_dir, pdb_filename), "wb") as f_pdb:
            f_pdb.write(pdb_data)
            
        # 1c. Write the title search index pdX mapping (4-byte records)
        # Sort segment records by clean title
        seg_shelf_sorted = sorted(seg_records, key=lambda x: x["shelf_idx"])
        seg_title_sorted = sorted(seg_shelf_sorted, key=get_clean_title)
        
        ndex_title_entries = []
        for r in seg_title_sorted:
            # 1-based index in the barcode-sorted list
            idx = sorted_records.index(r) + 1
            ndex_title_entries.append(struct.pack(">I", idx))
            
        ndex_title_pdx = pdx_header + b"".join(ndex_title_entries)
        with open(os.path.join(ndex_title_id, pdx_filename), "wb") as f_nt:
            f_nt.write(ndex_title_pdx)
            
        # 1d. Write the callnumber search index pdX mapping (4-byte records)
        seg_call_sorted = sorted(seg_records, key=lambda x: x["shelf_idx"])
        seg_call_sorted = sorted(seg_call_sorted, key=get_clean_callnumber)
        
        ndex_call_entries = []
        for r in seg_call_sorted:
            idx = sorted_records.index(r) + 1
            ndex_call_entries.append(struct.pack(">I", idx))
            
        ndex_call_pdx = pdx_header + b"".join(ndex_call_entries)
        with open(os.path.join(ndex_call_id, pdx_filename), "wb") as f_nc:
            f_nc.write(ndex_call_pdx)
            
        # 1e. Generate master catalog record for this segment
        start_idx = (seg_idx - 1) * max_items + 1
        end_idx = (seg_idx - 1) * max_items + records_count
        num_barcodes = math.ceil(records_count / spacing)
        
        prefix = struct.pack(">IIHH", start_idx, end_idx, spacing, num_barcodes)
        
        barcode_list = []
        for k in range(num_barcodes):
            item_idx = k * spacing
            bc = sorted_records[item_idx]["barcode"]
            barcode_list.append(struct.pack(">10s", bc.encode("ascii", errors="ignore")[:10]))
            
        master_rec = prefix + b"".join(barcode_list)
        if len(master_rec) % 2 != 0:
            master_rec += b"\x00"
        master_records_data.append(master_rec)
        
    # 2. Write the master catalog 000-3MLH.pdb with AppInfo
    master_appinfo = get_master_appinfo(total_records, list_name)
    master_header = make_pdb_header(name="000-3MLH", type_str="3MLH", creator_str="3MLH", num_records=num_segments, app_info_data=master_appinfo)
    
    master_dir_entries = []
    current_offset = 78 + num_segments * 8 + len(master_appinfo)
    for buf in master_records_data:
        master_dir_entries.append(struct.pack(">II", current_offset, 0))
        current_offset += len(buf)
        
    master_data = master_header + b"".join(master_dir_entries) + master_appinfo + b"".join(master_records_data)
    with open(os.path.join(db_dir, "000-3MLH.pdb"), "wb") as f_m:
        f_m.write(master_data)
        
    # 3. Write title index catalog ndex/3F3F4431/000-3MLH.pdb
    # Sort whole dataset alphabetically by clean title
    global_shelf_sorted = sorted(records, key=lambda x: x["shelf_idx"])
    global_title_sorted = sorted(global_shelf_sorted, key=get_clean_title)
    
    title_idx_count = math.ceil(total_records / 1024)
    title_idx_prefix = struct.pack(">IIHH", 1, total_records, 1024, title_idx_count)
    
    title_idx_entries = []
    for k in range(title_idx_count):
        r = global_title_sorted[k * 1024]
        formatted_str = f"title: {r['title']}"[:40]
        entry_bytes = formatted_str.encode("utf-8", errors="ignore")[:50].ljust(50, b"\x00")
        title_idx_entries.append(entry_bytes)
        
    title_idx_rec = title_idx_prefix + b"".join(title_idx_entries)
    if len(title_idx_rec) % 2 != 0:
        title_idx_rec += b"\x00"
        
    title_appinfo = get_index_appinfo(total_records, is_callnumber=False)
    title_idx_header = make_pdb_header(name="000-3MLH", type_str="3MLH", creator_str="3MLH", num_records=1, app_info_data=title_appinfo)
    
    current_offset = 78 + 8 + len(title_appinfo)
    title_idx_dir = struct.pack(">II", current_offset, 0)
    title_idx_data = title_idx_header + title_idx_dir + title_appinfo + title_idx_rec
    with open(os.path.join(ndex_title_dir, "000-3MLH.pdb"), "wb") as f_tm:
        f_tm.write(title_idx_data)
        
    # 4. Write callnumber index catalog ndex/3F3F4432/000-3MLH.pdb
    # Sort whole dataset alphabetically by clean callnumber
    global_call_sorted = sorted(global_shelf_sorted, key=get_clean_callnumber)
    
    call_idx_count = math.ceil(total_records / 1024)
    call_idx_prefix = struct.pack(">IIHH", 1, total_records, 1024, call_idx_count)
    
    call_idx_entries = []
    for k in range(call_idx_count):
        r = global_call_sorted[k * 1024]
        formatted_str = f"callnumber: {r['callnumber']}"[:40]
        entry_bytes = formatted_str.encode("utf-8", errors="ignore")[:38].ljust(38, b"\x00")
        call_idx_entries.append(entry_bytes)
        
    call_idx_rec = call_idx_prefix + b"".join(call_idx_entries)
    if len(call_idx_rec) % 2 != 0:
        call_idx_rec += b"\x00"
        
    call_appinfo = get_index_appinfo(total_records, is_callnumber=True)
    call_idx_header = make_pdb_header(name="000-3MLH", type_str="3MLH", creator_str="3MLH", num_records=1, app_info_data=call_appinfo)
    
    current_offset = 78 + 8 + len(call_appinfo)
    call_idx_dir = struct.pack(">II", current_offset, 0)
    call_idx_data = call_idx_header + call_idx_dir + call_appinfo + call_idx_rec
    with open(os.path.join(ndex_call_dir, "000-3MLH.pdb"), "wb") as f_cm:
        f_cm.write(call_idx_data)
        
    print(f"[+] DLA database files successfully generated in: {args.output_dir}")

def cmd_import(args):
    """Extract scanned barcodes and timestamps from a DLA upload file."""
    print(f"[*] Parsing upload file: {args.input_file}")
    
    if not os.path.exists(args.input_file):
        print(f"[-] Error: File not found: {args.input_file}")
        sys.exit(1)
        
    with open(args.input_file, "rb") as f:
        data = f.read()
        
    if len(data) < 102:
        print("[-] Error: File is too small to contain a PDB header and initial records.")
        sys.exit(1)
        
    # Standard PDB header is 78 bytes, but we start searching records from offset 102
    idx = 102
    scans = []
    
    # PalmOS epoch to Unix epoch difference in seconds (1904-01-01 to 1970-01-01)
    PALM_EPOCH_DIFF = 2082844800
    
    while idx <= len(data) - 32:
        # Unpack sequence number (2 bytes) and timestamp (4 bytes)
        seq, ts = struct.unpack(">HI", data[idx : idx+6])
        barcode_bytes = data[idx+6 : idx+32].split(b"\x00")[0]
        
        # Heuristics for a valid scan record in Palm OS DLA format:
        # 1. Valid PalmOS timestamp range (from year 1975 to 2075: 2.2e9 <= ts <= 5.4e9) or ts == 0
        is_valid_ts = (2.2e9 <= ts <= 5.4e9) or (ts == 0)
        
        # 2. Barcode consists of printable ASCII characters and has a minimum length of 2
        try:
            barcode = barcode_bytes.decode("ascii")
            is_printable = len(barcode) >= 2 and all(32 <= ord(c) < 127 for c in barcode)
        except Exception:
            is_printable = False
            
        if is_valid_ts and is_printable:
            if ts == 0:
                ts_str = "N/A"
            else:
                try:
                    unix_ts = ts - PALM_EPOCH_DIFF
                    dt = datetime.datetime.fromtimestamp(unix_ts, datetime.timezone.utc)
                    ts_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    ts_str = f"Invalid (0x{ts:08x})"
            
            scans.append({
                "Seq": seq,
                "TimestampRaw": ts,
                "Timestamp": ts_str,
                "Barcode": barcode
            })
            idx += 32  # Successfully parsed 32-byte scan record, advance to the next
        else:
            idx += 1   # Alignment shift detected, scan byte-by-byte to synchronize
            
    print(f"[+] Extracted {len(scans)} scans from upload file.")
    
    with open(args.output_file, "w", encoding="utf-8", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["SequenceNumber", "Timestamp", "Barcode", "TimestampRaw"])
        for s in scans:
            writer.writerow([s["Seq"], s["Timestamp"], s["Barcode"], s["TimestampRaw"]])
            
    print(f"[+] Exported scans to CSV: {args.output_file}")

def make_pull_metadata_block(tag: str, data: bytes, format_type: str) -> bytes:
    tag_bytes = tag.encode("ascii")
    if format_type == "vers":
        header = tag_bytes + struct.pack(">H", len(data))
    elif format_type == "PLLD":
        header = tag_bytes + b"\x0a" + bytes([len(data)])
    elif format_type == "??ID":
        header = tag_bytes + b"\x09\xff" + struct.pack(">H", len(data))
    
    block = header + data
    if len(block) % 2 != 0:
        block += b"\x00"
    return block

def cmd_export_pull(args):
    """Compile a tab-delimited pull list file into a PalmOS PL*.pdb database."""
    print(f"[*] Compiling pull list: {args.input_file}")
    
    if not os.path.exists(args.input_file):
        print(f"[-] Error: File not found: {args.input_file}")
        sys.exit(1)
        
    records = []
    with open(args.input_file, "r", encoding="utf-8-sig") as f:
        # Check for header line
        first_line = f.readline()
        if not first_line.startswith("barcode") and not first_line.startswith("Barcode"):
            # Put back the line
            f.seek(0)
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or len(row) < 3:
                continue
            barcode, callnumber, title = row[0].strip(), row[1].strip(), row[2].strip()
            if barcode:
                records.append({
                    "barcode": barcode,
                    "callnumber": callnumber,
                    "title": title
                })
                
    if not records:
        print("[-] Error: No valid records found in pull list.")
        sys.exit(1)
        
    print(f"[*] Found {len(records)} pull list items.")
    
    # Description (defaults to file basename without extension, truncated to 10 chars by schema limits)
    desc = args.description if args.description else os.path.splitext(os.path.basename(args.input_file))[0]
    desc = desc[:10]
    # Build PDB Name (derived from output file basename, e.g. PL001-3MLH)
    out_basename = os.path.splitext(os.path.basename(args.output_file))[0]
    pdb_name = f"{out_basename.upper()[:5]}-3MLH"
    
    # Construct AppInfo block
    # vers block data
    # format: 02 03 f1 0a ??ID (4 bytes) + total_records (4 bytes)
    vers_data = b"\x02\x03\xf1\x0a\x3f\x3f\x49\x44" + struct.pack(">I", len(records))
    vers_block = make_pull_metadata_block("vers", vers_data, "vers")
    
    # PLLD block data (UTF-8 BOM + description + \x00)
    desc_bytes = b"\xef\xbb\xbf" + desc.encode("utf-8") + b"\x00"
    plld_block = make_pull_metadata_block("PLLD", desc_bytes, "PLLD")
    
    # Sort records by barcode to generate the ??ID index list
    sorted_records_with_idx = sorted(
        enumerate(records),
        key=lambda x: x[1]["barcode"]
    )
    # 1-based indices
    sorted_indices = [idx + 1 for idx, r in sorted_records_with_idx]
    
    # Construct ??ID block data (validation / segments config)
    id_data = b"\x02\x0d" + struct.pack(">H", len(records)) + b"".join(struct.pack(">H", idx) for idx in sorted_indices)
    id_block = make_pull_metadata_block("??ID", id_data, "??ID")
    
    # Assemble AppInfo: 2 bytes header (40 03) + vers + plld + id
    app_info = b"\x40\x03" + vers_block + plld_block + id_block
    
    # Construct records payload
    record_buffers = []
    for r in records:
        fields = []
        # Field 1: ID (Barcode)
        barcode_bytes = r["barcode"].encode("ascii", errors="ignore") + b"\x00"
        fields.append((b"ID", b"\x2a", barcode_bytes))
        
        # Field 2: SO (Shelf Order)
        fields.append((b"SO", b"\x0c", b"\x00\x00\x00\x00"))
        
        # Field 3: RE (Relative / hold type)
        fields.append((b"RE", b"\x0c", b"\x00\x00\x00\x00"))
        
        # Field 4: D1 (Title)
        title_bytes = f"title: {r['title']}".encode("utf-8", errors="ignore") + b"\x00"
        fields.append((b"D1", b"\x2a", title_bytes))
        
        # Field 5: D2 (Callnumber)
        call_bytes = f"callnumber: {r['callnumber']}".encode("utf-8", errors="ignore") + b"\x00"
        fields.append((b"D2", b"\x2a", call_bytes))
        
        # Pack fields into record buffer
        rec_buf = b"\x80\x05"  # 5 fields header
        for tag, attr, data in fields:
            field_entry = tag + attr + bytes([len(data)]) + data
            if len(field_entry) % 2 != 0:
                field_entry += b"\x00"
            rec_buf += field_entry
        record_buffers.append(rec_buf)
        
    # Build PDB Header
    pdb_header = make_pdb_header(name=pdb_name, type_str="3MPL", creator_str="3MLH", num_records=len(records))
    
    # Add AppInfo offset to PDB header, aligned to 4-byte boundary
    app_info_offset = 78 + len(records) * 8
    padding_len = (4 - (app_info_offset % 4)) % 4
    app_info_offset += padding_len
    app_info_padding = b"\x00" * padding_len
    
    # Update AppInfoID (offset 52) in PDB header
    pdb_header = pdb_header[:52] + struct.pack(">I", app_info_offset) + pdb_header[56:]
    
    # Build record offset entries
    dir_entries = []
    current_offset = app_info_offset + len(app_info)
    for buf in record_buffers:
        dir_entries.append(struct.pack(">II", current_offset, 0))
        current_offset += len(buf)
        
    # Assemble full PDB binary
    pdb_data = pdb_header + b"".join(dir_entries) + app_info_padding + app_info + b"".join(record_buffers)
    
    # Write to output file
    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
    with open(args.output_file, "wb") as f_out:
        f_out.write(pdb_data)
        
    print(f"[+] Successfully compiled Pull List to: {args.output_file}")

def extract_barcodes_from_pull_pdb(pdb_path):
    """Extract barcode list from a compiled PL*.pdb database."""
    barcodes = []
    with open(pdb_path, "rb") as f:
        data = f.read()
    
    num_recs = struct.unpack(">H", data[76:78])[0]
    for i in range(num_recs):
        offset = struct.unpack(">I", data[78+i*8 : 78+i*8+4])[0]
        next_offset = struct.unpack(">I", data[78+(i+1)*8 : 78+(i+1)*8+4])[0] if i+1 < num_recs else len(data)
        rec_data = data[offset:next_offset]
        
        idx = rec_data.find(b"ID\x2a")
        if idx != -1:
            barcode_len = rec_data[idx+3]
            barcode = rec_data[idx+4 : idx+4+barcode_len-1].decode("ascii", errors="ignore")
            barcodes.append(barcode)
    return barcodes

def cmd_import_pull(args):
    """Compare an original pull list against the returned/modified PL*.pdb from the card."""
    print(f"[*] Analyzing Pull List results...")
    
    if not os.path.exists(args.original_file):
        print(f"[-] Error: Original file not found: {args.original_file}")
        sys.exit(1)
        
    if args.original_file.lower().endswith(".pdb"):
        original_barcodes = extract_barcodes_from_pull_pdb(args.original_file)
    else:
        original_barcodes = []
        with open(args.original_file, "r", encoding="utf-8-sig") as f:
            first_line = f.readline()
            if not first_line.startswith("barcode") and not first_line.startswith("Barcode"):
                f.seek(0)
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if row:
                    original_barcodes.append(row[0].strip())
                    
    print(f"[+] Loaded {len(original_barcodes)} original items from: {args.original_file}")
    
    if not os.path.exists(args.card_file):
        print(f"[-] Error: Card file not found: {args.card_file}")
        sys.exit(1)
        
    remaining_barcodes = extract_barcodes_from_pull_pdb(args.card_file)
    print(f"[+] Loaded {len(remaining_barcodes)} remaining items from card: {args.card_file}")
    
    remaining_set = set(remaining_barcodes)
    pulled = []
    not_pulled = []
    
    for barcode in original_barcodes:
        if barcode in remaining_set:
            not_pulled.append(barcode)
        else:
            pulled.append(barcode)
            
    pulled_file = args.output_prefix + "_pulled.txt"
    with open(pulled_file, "w", encoding="utf-8") as f_p:
        for b in pulled:
            f_p.write(f"{b}\n")
            
    not_pulled_file = args.output_prefix + "_not_pulled.txt"
    with open(not_pulled_file, "w", encoding="utf-8") as f_np:
        for b in not_pulled:
            f_np.write(f"{b}\n")
            
    print(f"[SUCCESS] Pulled items ({len(pulled)}) written to: {pulled_file}")
    print(f"[SUCCESS] Not Pulled items ({len(not_pulled)}) written to: {not_pulled_file}")

def main():
    parser = argparse.ArgumentParser(description="DLA Database Converter and Scan Importer (Native Linux)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    parser_export = subparsers.add_parser("export", help="Convert tab-delimited catalog into DLA card database")
    parser_export.add_argument("input_file", help="Input shelf list file (.tab)")
    parser_export.add_argument("output_dir", help="Output directory to write 'Database' folder to")
    parser_export.add_argument("--max-items", type=int, default=16384, help="Maximum items per segment (default: 16384)")
    
    parser_export_pull = subparsers.add_parser("export-pull", help="Convert tab-delimited pull list into DLA card pull database (PL*.pdb)")
    parser_export_pull.add_argument("input_file", help="Input pull list file (.tab)")
    parser_export_pull.add_argument("output_file", help="Output pull database file path (e.g. Card/pull/PL001.pdb)")
    parser_export_pull.add_argument("--description", help="Optional description name for the pull list (defaults to file basename)")
    
    parser_import = subparsers.add_parser("import", help="Parse scanned barcodes and upload values from 001.pdX")
    parser_import.add_argument("input_file", help="Input upload 001.pdX file")
    parser_import.add_argument("output_file", help="Output CSV file path to write results")
    
    parser_import_pull = subparsers.add_parser("import-pull", help="Determine Pulled/Not Pulled results by comparing original list against card PL*.pdb")
    parser_import_pull.add_argument("original_file", help="Original pull list (.tab or .pdb)")
    parser_import_pull.add_argument("card_file", help="Returned PL*.pdb file from card")
    parser_import_pull.add_argument("output_prefix", help="Output path prefix to write _pulled.txt and _not_pulled.txt")
    
    args = parser.parse_args()
    
    if args.command == "export":
        cmd_export(args)
    elif args.command == "export-pull":
        cmd_export_pull(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "import-pull":
        cmd_import_pull(args)

if __name__ == "__main__":
    main()
