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
        header = f.read(78)
        if len(header) < 78:
            print("[-] Error: File is too small to contain a PDB header.")
            sys.exit(1)
            
        num_records, = struct.unpack(">H", header[76:78])
        print(f"[*] PDB Header reports {num_records} records.")
        
        f.seek(102)
        
        scans = []
        while True:
            chunk = f.read(32)
            if len(chunk) < 32:
                break
                
            seq, ts = struct.unpack(">HI", chunk[0:6])
            barcode = chunk[6:].split(b"\x00")[0].decode("ascii", errors="ignore")
            
            if not barcode:
                continue
                
            if ts == 0:
                ts_str = "N/A"
            else:
                try:
                    dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
                    ts_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    ts_str = f"Invalid (0x{ts:08x})"
                    
            scans.append({
                "Seq": seq,
                "TimestampRaw": ts,
                "Timestamp": ts_str,
                "Barcode": barcode
            })
            
    print(f"[+] Extracted {len(scans)} scans from upload file.")
    
    with open(args.output_file, "w", encoding="utf-8", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["SequenceNumber", "Timestamp", "Barcode", "TimestampRaw"])
        for s in scans:
            writer.writerow([s["Seq"], s["Timestamp"], s["Barcode"], s["TimestampRaw"]])
            
    print(f"[+] Exported scans to CSV: {args.output_file}")

def main():
    parser = argparse.ArgumentParser(description="DLA Database Converter and Scan Importer (Native Linux)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    parser_export = subparsers.add_parser("export", help="Convert tab-delimited catalog into DLA card database")
    parser_export.add_argument("input_file", help="Input shelf list file (.tab)")
    parser_export.add_argument("output_dir", help="Output directory to write 'Database' folder to")
    parser_export.add_argument("--max-items", type=int, default=16384, help="Maximum items per segment (default: 16384)")
    
    parser_import = subparsers.add_parser("import", help="Parse scanned barcodes and upload values from 001.pdX")
    parser_import.add_argument("input_file", help="Input upload 001.pdX file")
    parser_import.add_argument("output_file", help="Output CSV file path to write results")
    
    args = parser.parse_args()
    
    if args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)

if __name__ == "__main__":
    main()
