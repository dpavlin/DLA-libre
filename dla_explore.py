#!/usr/bin/env python3
"""
DLA Exploration Library - dla_explore.py

A library module for exploring and working with 3M DLA (Digital Library Assistant)
PalmOS database files. Provides helper functions to parse, analyze, and build
DLA database files without running the full CLI commands.

File Formats:
-------------

1. PDB Header (78 bytes):
   Bytes 0-31:  Name (ASCII, null-padded)
   Byte 32:     Attributes
   Bytes 33-34: Version (big-endian)
   Bytes 35-38: Create Time (PalmOS epoch, big-endian)
   Bytes 39-42: Modify Time (PalmOS epoch, big-endian)
   Bytes 43-46: Backup Time (PalmOS epoch, big-endian)
   Bytes 47-50: Modify Number (big-endian)
   Bytes 51-54: Sort Info Offset (big-endian)
   Bytes 52-55: AppInfo Offset (big-endian, written at byte 52 in dla_tool.py)
   Byte 59:     Padding
   Bytes 60-63: Database Type (ASCII, e.g., "3MLH", "3MPL")
   Bytes 64-67: Database Creator (ASCII)
   Bytes 68-71: Unique ID Seed (big-endian)
   Bytes 72-75: Next Record List Offset (big-endian)
   Bytes 76-77: Number of Records (big-endian)

2. Directory Entries (8 bytes each, starting at byte 78):
   Bytes 0-3:   Record offset (big-endian)
   Bytes 4-7:   Flags (record type and length)

3. Pull List Record (3MPL type):
   Byte 0:      Flags (always 0x80)
   Byte 1:      Field count (typically 5)
   For each field:
     Bytes 0-1: Tag (2 ASCII bytes: "ID", "SO", "RE", "D1", "D2")
     Byte 2:    Attribute byte
     Byte 3:    Length of value
     Bytes 4-N: Value (N bytes)
     Byte N+4:  Padding byte if (2+1+1+N) is odd

   Field details:
   - ID: Attribute 0x2a, contains barcode (ASCII, null-terminated)
   - SO: Attribute 0x0c, contains shelf order (4 bytes big-endian uint32)
   - RE: Attribute 0x0c, contains relative/hold type (4 bytes big-endian uint32)
   - D1: Attribute 0x2a, contains primary info (title, UTF-8, null-terminated)
   - D2: Attribute 0x2a, contains secondary info (callnumber, UTF-8, null-terminated)

4. AppInfo Block (3MPL type):
   Bytes 0-1: Header (0x4003)
   For each block:
     Bytes 0-3: Tag ("vers", "PLLD", "??ID")
     Format varies by tag:
     - vers: Tag(4) + Length(2 bytes BE) + Data
     - PLLD: Tag(4) + 0x0a(1) + Length(1) + Data
     - ??ID: Tag(4) + 0x09ff(2) + Length(2 bytes BE) + Data

5. Device Upload File (3MLL type):
   Records are 32 bytes each (starting at offset 102):
   Bytes 0-1: Sequence number (big-endian uint16)
   Bytes 2-5: Timestamp (PalmOS epoch, big-endian uint32)
   Bytes 6-31: Barcode (ASCII, null-padded to 26 bytes)

Usage:
------
Import this module to access helper functions for exploring DLA files:

    import dla_explore
    
    # Parse a PDB file
    with open('file.pdb', 'rb') as f:
        data = f.read()
    
    # Get header info
    header = dla_explore.parse_pdb_header(data)
    print(f"Records: {header['num_records']}")
    
    # Parse pull list records
    pull_info = dla_explore.parse_pull_pdb(data)
    for record in pull_info['records']:
        print(f"Barcode: {record['barcode']}, SO: {record['so']}, RE: {record['re']}")

Exported Functions:
------------------
See the module docstring at the bottom for a complete list.
"""

import os
import sys
import struct
import math
import time
import argparse
import csv
import datetime

# =============================================================================
# CONSTANTS
# =============================================================================

PALM_EPOCH_DIFF = 2082844800  # Seconds between PalmOS epoch (1904-01-01) and Unix epoch (1970-01-01)
SCAN_RECORD_SIZE = 32  # Fixed size of DLA device scan record
VALID_TS_MIN = 2.2e9   # Minimum valid PalmOS timestamp (year ~1975)
VALID_TS_MAX = 5.4e9   # Maximum valid PalmOS timestamp (year ~2075)


def palm_epoch_to_datetime(seconds: int) -> datetime.datetime | None:
    """Convert PalmOS seconds (since Jan 1, 1904 UTC) to datetime.
    
    Args:
        seconds: PalmOS epoch timestamp in seconds.
        
    Returns:
        datetime object in UTC, or None if timestamp is 0.
    """
    if seconds == 0:
        return None
    epoch = datetime.datetime(1904, 1, 1, tzinfo=datetime.timezone.utc)
    return epoch + datetime.timedelta(seconds=seconds)


def palm_timestamp_to_display(ts: int) -> str:
    """Convert a raw PalmOS timestamp to a human-readable display string.
    
    Args:
        ts: Raw PalmOS epoch timestamp in seconds.
        
    Returns:
        Display string like '2018-07-19 10:30:00 UTC' or 'N/A' or 'Invalid (0x...)'
    """
    if ts == 0:
        return "N/A"
    try:
        unix_ts = ts - PALM_EPOCH_DIFF
        dt = datetime.datetime.fromtimestamp(unix_ts, datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return f"Invalid (0x{ts:08x})"


def parse_pdb_header(data: bytes) -> dict:
    """Parse the 78-byte PalmOS PDB header.
    
    Args:
        data: Raw bytes starting at PDB header.
        
    Returns:
        Dict with keys: name, attributes, version, create_time, modify_time,
        backup_time, modify_num, app_info_offset, sort_info_offset, type, creator,
        unique_id_seed, next_rec_list, num_records
    """
    name = data[0:32].split(b'\x00')[0].decode('ascii', errors='replace')
    return {
        'name': name,
        'attributes': struct.unpack('B', data[32:33])[0],
        'version': struct.unpack('>H', data[33:35])[0],
        'create_time': struct.unpack('>I', data[35:39])[0],
        'modify_time': struct.unpack('>I', data[39:43])[0],
        'backup_time': struct.unpack('>I', data[43:47])[0],
        'modify_num': struct.unpack('>I', data[47:51])[0],
        'app_info_offset': struct.unpack('>I', data[52:56])[0],
        'sort_info_offset': struct.unpack('>I', data[55:59])[0],
        'type': data[60:64].decode('ascii', errors='replace'),
        'creator': data[64:68].decode('ascii', errors='replace'),
        'unique_id_seed': struct.unpack('>I', data[68:72])[0],
        'next_rec_list': struct.unpack('>I', data[72:76])[0],
        'num_records': struct.unpack('>H', data[76:78])[0],
    }


def get_record_offsets(data: bytes) -> list:
    """Get list of record offsets from a PDB file.
    
    Args:
        data: Raw PDB file bytes.
        
    Returns:
        List of (offset, flags, length) tuples for each record.
    """
    num_recs = struct.unpack('>H', data[76:78])[0]
    offsets = []
    for i in range(num_recs):
        offset = struct.unpack('>I', data[78+i*8 : 78+i*8+4])[0]
        flags = struct.unpack('>I', data[78+i*8+4 : 78+i*8+8])[0]
        offsets.append((offset, flags & 0xFF, (flags >> 8) & 0xFFFF))
    return offsets


def parse_tagged_record(data: bytes, offset: int, length: int) -> dict:
    """Parse a tagged record from a PDB file.
    
    Args:
        data: Raw file bytes.
        offset: Starting offset of the record.
        length: Record length.
        
    Returns:
        Dict with 'header' (flags, type) and 'fields' list of (tag, attr, length, value).
    """
    rec_end = offset + length
    header = struct.unpack('>HB I', data[offset:offset+7])
    flags = header[0]
    rec_type = struct.unpack('>I', data[offset+3:offset+7])[0]
    
    fields = []
    idx = offset + 7
    while idx + 7 < rec_end:
        tag = data[idx:idx+4].decode('ascii', errors='replace')
        attr = data[idx+4]
        field_len = struct.unpack('>H', data[idx+5:idx+7])[0]
        value = data[idx+7:idx+7+field_len]
        fields.append((tag, attr, field_len, value))
        idx += 7 + field_len
        if idx >= rec_end:
            break
    
    return {
        'flags': flags,
        'type': rec_type,
        'fields': fields,
    }


def read_pdb_file(path: str) -> tuple:
    """Read and parse a complete PDB file.
    
    Args:
        path: Path to the PDB file.
        
    Returns:
        Tuple of (header_dict, list_of_parsed_records).
    """
    with open(path, 'rb') as f:
        data = f.read()
    header = parse_pdb_header(data)
    records = []
    num_recs = header['num_records']
    for i in range(num_recs):
        offset = struct.unpack('>I', data[78+i*8 : 78+i*8+4])[0]
        flags = struct.unpack('>I', data[78+i*8+4 : 78+i*8+8])[0]
        rec_len = (flags >> 8) & 0xFFFF
        if offset + rec_len <= len(data):
            rec = parse_tagged_record(data, offset, rec_len)
            rec['offset'] = offset
            rec['flags'] = flags & 0xFF
            records.append(rec)
    return header, records


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


def clean_csv_field(val: str) -> str:
    """Clean a CSV field value by stripping surrounding quotes.
    
    Args:
        val: Raw CSV field value.
        
    Returns:
        Cleaned value with surrounding quotes removed.
    """
    if val.startswith('"'):
        val = val[1:]
    if val.endswith('"'):
        val = val[:-1]
    return val


def parse_input_file(input_path: str, has_header: bool = True) -> list:
    """Parse a tab-delimited shelf list input file.
    
    Args:
        input_path: Path to the input .tab file.
        has_header: Whether the first line is a header (default True).
        
    Returns:
        List of record dicts with keys: barcode, callnumber, title, shelf_idx.
    """
    records = []
    
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        if not lines:
            return records
            
        start_row = 0
        if has_header:
            first_row = lines[0].rstrip("\r\n").split("\t")
            if len(first_row) > 0 and first_row[0].lower() in ["barcode", "barcode_no"]:
                start_row = 1
                
        shelf_idx = 0
        for i in range(start_row, len(lines)):
            line = lines[i]
            row = line.rstrip("\r\n").split("\t")
            if len(row) < 3:
                continue
            
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
            
    return records


def compute_segment_config(total_records: int, max_items: int = 1000) -> dict:
    """Compute segment configuration for a catalog.
    
    Args:
        total_records: Total number of records.
        max_items: Maximum items per segment.
        
    Returns:
        Dict with num_segments, segments (list of record ranges), spacing, use_4_byte_idx.
    """
    num_segments = math.ceil(total_records / max_items)
    spacing = 256 if total_records >= 16384 else max(256, int(total_records / 9.45))
    use_4_byte_idx = (total_records > 65535)
    
    segments = []
    for seg_idx in range(num_segments):
        start = seg_idx * max_items
        end = min(start + max_items, total_records)
        segments.append({
            'index': seg_idx + 1,
            'start': start,
            'end': end,
            'count': end - start,
        })
    
    return {
        'num_segments': num_segments,
        'segments': segments,
        'spacing': spacing,
        'use_4_byte_idx': use_4_byte_idx,
    }


def build_segment_index(seg_records: list, use_4_byte_idx: bool) -> bytes:
    """Build the .pdX index file data for a segment.
    
    Args:
        seg_records: List of record dicts sorted by barcode.
        use_4_byte_idx: Whether to use 4-byte shelf indices.
        
    Returns:
        Bytes for the .pdX index file (excluding header).
    """
    pdx_entries = []
    for r in seg_records:
        barcode_bytes = r["barcode"].encode("ascii", errors="ignore")[:10].ljust(10, b"\x00")
        if use_4_byte_idx:
            entry = struct.pack(">10sBBI", barcode_bytes, 0x00, 0x01, r["shelf_idx"] + 1)
        else:
            entry = struct.pack(">10sBBH", barcode_bytes, 0x00, 0x01, r["shelf_idx"] + 1)
        pdx_entries.append(entry)
    return b"".join(pdx_entries)


def build_segment_data(seg_records: list) -> bytes:
    """Build the .pdb data file content for a segment.
    
    Args:
        seg_records: List of record dicts sorted by barcode.
        
    Returns:
        Bytes for the .pdb data content (excluding header and dir entries).
    """
    record_buffers = []
    for r in seg_records:
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
    
    return b"".join(record_buffers)


def build_segment_dir_entries(record_buffers: list) -> bytes:
    """Build directory entries for a segment's .pdb file.
    
    Args:
        record_buffers: List of record data buffers.
        
    Returns:
        Bytes for the directory entries.
    """
    dir_entries = []
    current_offset = 78 + len(record_buffers) * 8
    for buf in record_buffers:
        dir_entries.append(struct.pack(">II", current_offset, 0))
        current_offset += len(buf)
    return b"".join(dir_entries)


def build_master_record(seg_records: list, spacing: int) -> bytes:
    """Build a master catalog record for a segment.
    
    Args:
        seg_records: Sorted segment records.
        spacing: Catalog spacing.
        
    Returns:
        Bytes for the master catalog record.
    """
    num_barcodes = math.ceil(len(seg_records) / spacing)
    
    # Start and end indices (1-based)
    start_idx = seg_records[0]['shelf_idx'] + 1 if seg_records else 0
    end_idx = seg_records[-1]['shelf_idx'] + 1 if seg_records else 0
    
    prefix = struct.pack(">IIHH", start_idx, end_idx, spacing, num_barcodes)
    
    barcode_list = []
    for k in range(num_barcodes):
        item_idx = k * spacing
        if item_idx < len(seg_records):
            bc = seg_records[item_idx]["barcode"]
            barcode_list.append(struct.pack(">10s", bc.encode("ascii", errors="ignore")[:10]))
    
    master_rec = prefix + b"".join(barcode_list)
    if len(master_rec) % 2 != 0:
        master_rec += b"\x00"
    return master_rec

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


# =============================================================================
# UPLOAD FILE PARSING (device scan records)
# =============================================================================

def parse_upload_file(data: bytes, start_offset: int = 102) -> list:
    """Parse scan records from a DLA device upload file.
    
    Scans byte-by-byte looking for valid 32-byte scan records.
    
    Args:
        data: Raw file bytes.
        start_offset: Where to start scanning (default 102, after PDB header).
        
    Returns:
        List of scan record dicts with keys: Seq, TimestampRaw, Timestamp, Barcode.
    """
    scans = []
    idx = start_offset
    
    while idx <= len(data) - SCAN_RECORD_SIZE:
        # Unpack sequence number (2 bytes) and timestamp (4 bytes)
        seq, ts = struct.unpack(">HI", data[idx : idx+6])
        barcode_bytes = data[idx+6 : idx+32].split(b"\x00")[0]
        
        # Heuristics for a valid scan record in Palm OS DLA format:
        # 1. Valid PalmOS timestamp range (from year 1975 to 2075: 2.2e9 <= ts <= 5.4e9) or ts == 0
        is_valid_ts = (VALID_TS_MIN <= ts <= VALID_TS_MAX) or (ts == 0)
        
        # 2. Barcode consists of printable ASCII characters and has a minimum length of 2
        try:
            barcode = barcode_bytes.decode("ascii")
            is_printable = len(barcode) >= 2 and all(32 <= ord(c) < 127 for c in barcode)
        except Exception:
            is_printable = False
            
        if is_valid_ts and is_printable:
            ts_str = palm_timestamp_to_display(ts)
            scans.append({
                "Seq": seq,
                "TimestampRaw": ts,
                "Timestamp": ts_str,
                "Barcode": barcode
            })
            idx += SCAN_RECORD_SIZE
        else:
            idx += 1
            
    return scans


def try_parse_scan_at(data: bytes, offset: int) -> dict | None:
    """Try to parse a single scan record at the given offset.
    
    Args:
        data: Raw file bytes.
        offset: Offset to try parsing from.
        
    Returns:
        Scan record dict, or None if not a valid record at this offset.
    """
    if offset + SCAN_RECORD_SIZE > len(data):
        return None
        
    seq, ts = struct.unpack(">HI", data[offset : offset+6])
    barcode_bytes = data[offset+6 : offset+32].split(b"\x00")[0]
    
    is_valid_ts = (VALID_TS_MIN <= ts <= VALID_TS_MAX) or (ts == 0)
    
    try:
        barcode = barcode_bytes.decode("ascii")
        is_printable = len(barcode) >= 2 and all(32 <= ord(c) < 127 for c in barcode)
    except Exception:
        is_printable = False
        
    if is_valid_ts and is_printable:
        return {
            "Seq": seq,
            "TimestampRaw": ts,
            "Timestamp": palm_timestamp_to_display(ts),
            "Barcode": barcode,
            "Offset": offset
        }
    return None


def scan_record_stats(scans: list) -> dict:
    """Compute statistics over a list of scan records.
    
    Args:
        scans: List of scan record dicts.
        
    Returns:
        Dict with statistics like total, valid_ts, zero_ts, ts_range, etc.
    """
    total = len(scans)
    valid_ts = [s for s in scans if s["TimestampRaw"] > 0]
    zero_ts = [s for s in scans if s["TimestampRaw"] == 0]
    
    seq_values = [s["Seq"] for s in scans]
    ts_values = [s["TimestampRaw"] for s in scans if s["TimestampRaw"] > 0]
    
    stats = {
        "total": total,
        "valid_ts_count": len(valid_ts),
        "zero_ts_count": len(zero_ts),
        "seq_min": min(seq_values) if seq_values else 0,
        "seq_max": max(seq_values) if seq_values else 0,
        "seq_sorted_min": min(seq_values) if seq_values else 0,
        "seq_sorted_max": max(sorted(seq_values)) if seq_values else 0,
    }
    
    if len(ts_values) > 1:
        diffs = [ts_values[i+1] - ts_values[i] for i in range(len(ts_values)-1)]
        stats["ts_positive_diffs"] = sum(1 for d in diffs if d > 0)
        stats["ts_negative_diffs"] = sum(1 for d in diffs if d < 0)
        stats["ts_same_diffs"] = sum(1 for d in diffs if d == 0)
        stats["ts_diff_count"] = len(diffs)
        stats["ts_min_diff"] = min(diffs)
        stats["ts_max_diff"] = max(diffs)
    
    if ts_values:
        stats["ts_min"] = min(ts_values)
        stats["ts_max"] = max(ts_values)
        stats["ts_min_dt"] = palm_epoch_to_datetime(min(ts_values))
        stats["ts_max_dt"] = palm_epoch_to_datetime(max(ts_values))
    
    return stats

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

def update_pull_index(output_dir, pdb_basename, num_records, desc):
    index_path = os.path.join(output_dir, "PL000.tmp")
    entries = {}
    
    try:
        list_idx = int(pdb_basename.upper().replace("PL", ""))
    except ValueError:
        list_idx = 1
        
    if os.path.exists(index_path) and os.path.getsize(index_path) >= 34:
        try:
            with open(index_path, "rb") as f:
                data = f.read()
            num_lists = struct.unpack(">H", data[2:4])[0]
            for i in range(num_lists):
                offset = 4 + i * 30
                if offset + 30 <= len(data):
                    entry_data = data[offset : offset + 30]
                    l_idx = struct.unpack(">H", entry_data[4:6])[0]
                    l_count = struct.unpack(">H", entry_data[6:8])[0]
                    l_name = entry_data[10:16].split(b"\x00")[0].decode("ascii", errors="ignore")
                    l_desc_raw = entry_data[16:30]
                    if l_desc_raw.startswith(b"\xef\xbb\xbf"):
                        l_desc = l_desc_raw[3:].split(b"\x00")[0].decode("utf-8", errors="ignore")
                    else:
                        l_desc = l_desc_raw.split(b"\x00")[0].decode("utf-8", errors="ignore")
                    entries[l_idx] = {
                        "count": l_count,
                        "name": l_name,
                        "desc": l_desc
                    }
        except Exception:
            pass
            
    entries[list_idx] = {
        "count": num_records,
        "name": pdb_basename.upper()[:5],
        "desc": desc[:10]
    }
    
    num_lists = len(entries)
    header = b"\x00\x40" + struct.pack(">H", num_lists)
    
    entries_data = []
    for l_idx in sorted(entries.keys()):
        ent = entries[l_idx]
        name_bytes = ent["name"].encode("ascii")[:5].ljust(6, b"\x00")
        desc_bytes = (b"\xef\xbb\xbf" + ent["desc"].encode("utf-8"))[:13].ljust(14, b"\x00")
        
        entry_bin = (
            b"\x00\x00\x00\x00" +
            struct.pack(">H", l_idx) +
            struct.pack(">H", ent["count"]) +
            b"\x00\x00" +
            name_bytes +
            desc_bytes
        )
        entries_data.append(entry_bin)
        
    payload = header + b"".join(entries_data)
    target_len = max(64, ((len(payload) + 31) // 32) * 32)
    payload = payload.ljust(target_len, b"\x00")
    
    with open(index_path, "wb") as f_out:
        f_out.write(payload)
    print(f"[+] Updated Pull List Index: {index_path}")

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
    
    # Update Pull List Index PL000.tmp
    output_dir = os.path.dirname(os.path.abspath(args.output_file))
    pdb_basename = os.path.splitext(os.path.basename(args.output_file))[0]
    update_pull_index(output_dir, pdb_basename, len(records), desc)

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


# =============================================================================
# PULL LIST PARSING & RECORD BUILDING
# =============================================================================

def parse_pull_pdb(data: bytes) -> dict:
    """Parse a PL*.pdb pull list database into structured format.
    
    Uses the same approach as extract_barcodes_from_pull_pdb - reads record
    offsets from the directory and extracts data between consecutive offsets.
    
    Args:
        data: Raw PDB file bytes.
        
    Returns:
        Dict with 'header', 'app_info', and 'records' (list of records with fields).
    """
    header = parse_pdb_header(data)
    
    # Parse AppInfo block
    app_info_offset = header['app_info_offset']
    app_info = {}
    if app_info_offset and app_info_offset < len(data):
        app_info = parse_pull_appinfo(data[app_info_offset:])
    
    # Parse records - use same approach as original extract_barcodes_from_pull_pdb
    records = []
    num_recs = header['num_records']
    for i in range(num_recs):
        offset = struct.unpack('>I', data[78+i*8 : 78+i*8+4])[0]
        next_offset = struct.unpack('>I', data[78+(i+1)*8 : 78+(i+1)*8+4])[0] if i+1 < num_recs else len(data)
        rec_data = data[offset:next_offset]
        rec = parse_pull_record(rec_data)
        rec['offset'] = offset
        records.append(rec)
    
    return {
        'header': header,
        'app_info': app_info,
        'records': records,
    }


def parse_pull_appinfo(data: bytes) -> dict:
    """Parse the AppInfo block of a PL*.pdb file.
    
    Args:
        data: Raw AppInfo bytes.
        
    Returns:
        Dict with keys like 'vers', 'plld', 'id_list'.
    """
    result = {}
    idx = 0
    
    # First 2 bytes are header
    if len(data) < 2:
        return result
    
    while idx + 5 <= len(data):
        tag = data[idx:idx+4]
        if tag in (b'vers', b'PLLD', b'??ID'):
            if tag == b'vers':
                # Format: tag (4) + length (2 bytes)
                if idx + 6 <= len(data):
                    length = struct.unpack('>H', data[idx+4:idx+6])[0]
                    value = data[idx+6:idx+6+length]
                    result['vers'] = value
                    idx += 6 + length
                    continue
            elif tag == b'PLLD':
                # Format: tag (4) + 0x0a (1) + length (1)
                if idx + 6 <= len(data):
                    length = data[idx+5]
                    value = data[idx+6:idx+6+length]
                    result['plld'] = value
                    idx += 6 + length
                    continue
            elif tag == b'??ID':
                # Format: tag (4) + 0x09ff (2) + length (2) + data
                if idx + 8 <= len(data):
                    length = struct.unpack('>H', data[idx+6:idx+8])[0]
                    value = data[idx+8:idx+8+length]
                    result['id_list'] = value
                    idx += 8 + length
                    continue
        
        idx += 1
    
    return result


def parse_pull_record(data: bytes) -> dict:
    """Parse a single pull list record into structured format.
    
    Pull list records use 2-byte tags with this structure:
        Byte 0: flags (always 0x80)
        Byte 1: field_count (number of fields, typically 5)
        
        For each field:
            Bytes 0-1: tag (2 ASCII bytes, e.g., "ID", "SO", "RE", "D1", "D2")
            Byte 2: attribute (field attribute byte)
            Byte 3: length (length of value in bytes)
            Bytes 4-N: value (length bytes)
            Byte N+4: padding byte if (2 + 1 + 1 + length) is odd
    
    Args:
        data: Record bytes.
        
    Returns:
        Dict with 'fields' list of (tag, attr, value) and convenience keys.
    """
    fields = []
    idx = 2  # Skip 2-byte header (flags + count)
    field_count = data[1]
    
    for _ in range(field_count):
        if idx + 4 > len(data):
            break
        tag = data[idx:idx+2].decode('ascii', errors='replace')
        attr = data[idx+2]
        field_len = data[idx+3]
        value = data[idx+4:idx+4+field_len]
        fields.append((tag, attr, value))
        
        # Advance to next field, accounting for padding
        field_size = 4 + field_len  # 2(tag) + 1(attr) + 1(len) + N(value)
        if field_size % 2 != 0:
            field_size += 1  # Add padding byte
        idx += field_size
    
    # Convenience access
    barcode = ''
    so = 0
    re = 0
    d1 = ''
    d2 = ''
    
    for tag, attr, value in fields:
        if tag == 'ID':
            barcode = value.rstrip(b'\x00').decode('ascii', errors='ignore')
        elif tag == 'SO':
            so = struct.unpack('>I', value[:4])[0] if len(value) >= 4 else 0
        elif tag == 'RE':
            re = struct.unpack('>I', value[:4])[0] if len(value) >= 4 else 0
        elif tag == 'D1':
            d1 = value.rstrip(b'\x00').decode('utf-8', errors='ignore')
        elif tag == 'D2':
            d2 = value.rstrip(b'\x00').decode('utf-8', errors='ignore')
    
    return {
        'fields': fields,
        'barcode': barcode,
        'so': so,
        're': re,
        'd1': d1,
        'd2': d2,
    }


def build_pull_record(barcode: str, callnumber: str, title: str,
                      so_value: int = 0, re_value: int = 0) -> bytes:
    """Build a single pull list record buffer.
    
    Pull list records use 2-byte tags:
        2 bytes: flags + field_count
        Then for each field:
            2 bytes: tag (ID, SO, RE, D1, D2)
            1 byte: attribute
            1 byte: length
            length bytes: value
    
    Args:
        barcode: Item barcode.
        callnumber: Call number.
        title: Book title.
        so_value: Shelf order value (default 0).
        re_value: Relative/hold value (default 0).
        
    Returns:
        Bytes buffer for a single pull list record.
    """
    fields = []
    
    # Field 1: ID (Barcode)
    barcode_bytes = barcode.encode("ascii", errors="ignore") + b"\x00"
    fields.append((b"ID", b"\x2a", barcode_bytes))
    
    # Field 2: SO (Shelf Order)
    so_bytes = struct.pack(">I", so_value)
    fields.append((b"SO", b"\x0c", so_bytes))
    
    # Field 3: RE (Relative / hold type)
    re_bytes = struct.pack(">I", re_value)
    fields.append((b"RE", b"\x0c", re_bytes))
    
    # Field 4: D1 (Title)
    title_bytes = f"title: {title}".encode("utf-8", errors="ignore") + b"\x00"
    fields.append((b"D1", b"\x2a", title_bytes))
    
    # Field 5: D2 (Callnumber)
    call_bytes = f"callnumber: {callnumber}".encode("utf-8", errors="ignore") + b"\x00"
    fields.append((b"D2", b"\x2a", call_bytes))
    
    # Pack fields into record buffer (2-byte tags)
    rec_buf = b"\x80\x05"  # 5 fields header
    for tag, attr, data_val in fields:
        field_entry = tag + attr + bytes([len(data_val)]) + data_val
        if len(field_entry) % 2 != 0:
            field_entry += b"\x00"
        rec_buf += field_entry
    
    return rec_buf


def parse_pull_input(input_path: str, delimiter: str = "\t") -> list:
    """Parse a tab-delimited pull list file into record dicts.
    
    Args:
        input_path: Path to the tab-delimited file.
        delimiter: Field delimiter (default tab).
        
    Returns:
        List of record dicts with keys: barcode, callnumber, title.
    """
    records = []
    with open(input_path, "r", encoding="utf-8-sig") as f:
        # Check for header line
        first_line = f.readline()
        if not first_line.startswith("barcode") and not first_line.startswith("Barcode"):
            # Put back the line
            f.seek(0)
        reader = csv.reader(f, delimiter=delimiter)
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
    return records

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


# =============================================================================
# PULL RESULTS COMPARISON (no CLI args needed)
# =============================================================================

def compare_pull_results(original_barcodes: list, remaining_barcodes: list) -> dict:
    """Compare original pull list against remaining items (after pull).
    
    Args:
        original_barcodes: Barcodes from original pull list.
        remaining_barcodes: Barcodes remaining in card file.
        
    Returns:
        Dict with 'pulled', 'not_pulled', 'pulled_count', 'not_pulled_count'.
    """
    remaining_set = set(remaining_barcodes)
    pulled = []
    not_pulled = []
    
    for barcode in original_barcodes:
        if barcode in remaining_set:
            not_pulled.append(barcode)
        else:
            pulled.append(barcode)
            
    return {
        'pulled': pulled,
        'not_pulled': not_pulled,
        'pulled_count': len(pulled),
        'not_pulled_count': len(not_pulled),
    }


def write_pull_results(pulled: list, not_pulled: list, output_prefix: str) -> tuple:
    """Write pulled/not-pulled results to files.
    
    Args:
        pulled: List of pulled barcodes.
        not_pulled: List of not-pulled barcodes.
        output_prefix: Output file prefix.
        
    Returns:
        Tuple of (pulled_file_path, not_pulled_file_path).
    """
    pulled_file = output_prefix + "_pulled.txt"
    with open(pulled_file, "w", encoding="utf-8") as f:
        for b in pulled:
            f.write(f"{b}\n")
            
    not_pulled_file = output_prefix + "_not_pulled.txt"
    with open(not_pulled_file, "w", encoding="utf-8") as f:
        for b in not_pulled:
            f.write(f"{b}\n")
            
    return pulled_file, not_pulled_file

# DLA Tool Library
# =================
# This module is the library version of dla_tool.py.
# Import this module to use the core functions in your own code.
# See dla_tool.py for the CLI interface.
#
# Exported functions:
#
#   PDB Header/Record Parsing:
#     make_pdb_header(), parse_pdb_header(), get_record_offsets(),
#     parse_tagged_record(), read_pdb_file()
#
#   Timestamp Conversion:
#     palm_epoch_to_datetime(), palm_timestamp_to_display()
#
#   AppInfo/Metadata:
#     make_metadata_block(), get_master_appinfo(), get_index_appinfo()
#
#   Data Cleaning:
#     get_clean_title(), get_clean_callnumber(), clean_csv_field()
#
#   Upload/Import Parsing:
#     cmd_import(), parse_upload_file(), try_parse_scan_at(),
#     scan_record_stats()
#
#   Pull List Parsing:
#     parse_pull_pdb(), parse_pull_appinfo(), parse_pull_record(),
#     extract_barcodes_from_pull_pdb(), parse_pull_input()
#
#   Pull List Building:
#     make_pull_metadata_block(), build_pull_record()
#
#   Export Helpers:
#     parse_input_file(), compute_segment_config(), build_segment_index(),
#     build_segment_data(), build_segment_dir_entries(), build_master_record()
#
#   Pull Results:
#     compare_pull_results(), write_pull_results()
#
#   CLI Commands (full workflows):
#     cmd_export(), cmd_import(), cmd_export_pull(), cmd_import_pull()
#     update_pull_index()

if __name__ == "__main__":
    main()
