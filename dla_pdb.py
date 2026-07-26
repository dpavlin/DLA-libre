#!/usr/bin/env python3
"""
DLA PDB/PDX reader - small library for reading PalmOS databases.

Extracted from dla_tool_lib.py (verified, parity-tested code).
Can be imported to examine existing DLA database files.
"""
import struct


def parse_pdb_header(data):
    """Parse 78-byte PalmOS PDB header. Returns dict."""
    name = data[0:32].split(b'\x00')[0].decode('ascii', errors='replace')
    attributes = struct.unpack('>H', data[32:34])[0]
    version = struct.unpack('>H', data[34:36])[0]
    create_time = struct.unpack('>I', data[36:40])[0]
    modify_time = struct.unpack('>I', data[40:44])[0]
    backup_time = struct.unpack('>I', data[44:48])[0]
    modify_num = struct.unpack('>I', data[48:52])[0]
    app_info_offset = struct.unpack('>I', data[52:56])[0]
    sort_info_offset = struct.unpack('>I', data[56:60])[0]
    type_str = data[60:64].decode('ascii', errors='replace')
    creator = data[64:68].decode('ascii', errors='replace')
    unique_id_seed = struct.unpack('>I', data[68:72])[0]
    next_rec_list = struct.unpack('>I', data[72:76])[0]
    num_records = struct.unpack('>H', data[76:78])[0]
    
    return {
        'name': name,
        'attributes': attributes,
        'version': version,
        'create_time': create_time,
        'modify_time': modify_time,
        'backup_time': backup_time,
        'modify_num': modify_num,
        'app_info_offset': app_info_offset,
        'sort_info_offset': sort_info_offset,
        'type': type_str,
        'creator': creator,
        'unique_id_seed': unique_id_seed,
        'next_rec_list': next_rec_list,
        'num_records': num_records,
    }


def parse_tagged_record(data, pos):
    """Parse a tagged record starting at pos.
    
    PalmOS tagged record format:
      2 bytes: flags (high nibble) + num_fields (low nibble)
      For each field:
        2 bytes: tag (ASCII)
        1 byte:  attribute
        1 byte:  length
        N bytes: data (padded to even boundary)
    
    Returns list of (tag, attr, length, data_bytes) tuples.
    """
    if pos + 2 > len(data):
        return None
    
    header = struct.unpack('>BB', data[pos:pos+2])
    num_fields = header[1] & 0x0f
    flags = header[1] >> 4
    
    fields = []
    pos += 2
    
    for _ in range(min(num_fields, 20)):
        if pos + 4 > len(data):
            break
            
        tag = data[pos:pos+2].decode('ascii', errors='replace')
        pos += 2
        attr = data[pos]
        pos += 1
        length = data[pos]
        pos += 1
        value = data[pos:pos+length]
        pos += length
        if length % 2 != 0:
            pos += 1
            
        fields.append((tag, attr, length, value))
    
    return fields


def parse_pdb_records(data):
    """Parse all records from a PDB file.
    
    Returns list of dicts with 'index', 'offset', 'attr', 'fields'.
    """
    header = parse_pdb_header(data)
    num_records = header['num_records']
    
    records = []
    for i in range(num_records):
        offset = struct.unpack('>I', data[78 + i*8 : 78 + i*8 + 4])[0]
        record_attr = struct.unpack('>I', data[78 + i*8 + 4 : 78 + i*8 + 8])[0]
        
        fields = parse_tagged_record(data, offset)
        if fields:
            records.append({
                'index': i,
                'offset': offset,
                'record_attr': record_attr,
                'fields': fields,
            })
    
    return records


def parse_pdx_entries(data):
    """Parse .pdX index entries.
    
    Format depends on record size:
      14-byte: [10-byte barcode][2-byte flags][2-byte shelf_index]
      16-byte: [10-byte barcode][2-byte flags][4-byte shelf_index]
    
    Returns list of dicts with barcode, flags, shelf_index.
    """
    header = parse_pdb_header(data)
    num_records = header['num_records']
    
    if num_records == 0:
        return []
    
    # Determine record size from first entry
    first_entry = data[78:78+14]
    flags = first_entry[10]
    
    entries = []
    for i in range(num_records):
        pos = 78 + i * 14
        if pos + 14 > len(data):
            break
            
        barcode = data[pos:pos+10].decode('ascii', errors='replace')
        byte10 = data[pos+10]
        byte11 = data[pos+11]
        shelf_index = struct.unpack('>H', data[pos+12:pos+14])[0]
        
        entries.append({
            'index': i,
            'barcode': barcode,
            'flags': f'0x{byte10:02x} 0x{byte11:02x}',
            'shelf_index': shelf_index,
        })
    
    return entries


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <pdb_or_pdx_file>')
        sys.exit(1)
    
    path = sys.argv[1]
    with open(path, 'rb') as f:
        data = f.read()
    
    header = parse_pdb_header(data)
    print(f"File: {path}")
    print(f"  Name: {header['name']}")
    print(f"  Type: {header['type']}")
    print(f"  Creator: {header['creator']}")
    print(f"  Records: {header['num_records']}")
    
    if header['type'] == '3MLH' and 'md01' in path:
        # Data record file - parse records
        records = parse_pdb_records(data)
        print(f"\n  {len(records)} records parsed:")
        for rec in records[:5]:
            print(f"\n    Record {rec['index']} at offset {rec['offset']}:")
            for tag, attr, length, value in rec['fields']:
                print(f"      {tag} attr=0x{attr:02x} len={length} value={value!r}")
    elif 'ndex' in path or path.endswith('.pdX'):
        # Index file - parse entries
        entries = parse_pdx_entries(data)
        print(f"\n  {len(entries)} index entries parsed:")
        for e in entries[:5]:
            print(f"    [{e['index']}] barcode={e['barcode']} flags={e['flags']} shelf={e['shelf_index']}")
