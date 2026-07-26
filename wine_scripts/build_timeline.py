#!/usr/bin/env python3
"""
Build master-timeline: create properly ordered commit history.

Timeline:
1. Empty initial commit (root)
2. All 32 files added in chronological order with original timestamps from session
3. Rest of history (333ad16 through 72d4da3)

This ensures wine_scripts appear FIRST chronologically, then rest of history.
"""
import json
import re
import subprocess
import os
from pathlib import Path

AUTHOR_NAME = "Dobrica Pavlinusic"
AUTHOR_EMAIL = "dpavlin@rot13.org"

FILE_CATEGORIES = {
    "wine_scripts/dump_db.js": {"desc": "dump DataManager.mdb to JSON", "group": "Database dumps"},
    "wine_scripts/dump_db_csv.js": {"desc": "dump all tables to CSV", "group": "Database dumps"},
    "wine_scripts/dump_db_utf8.js": {"desc": "UTF-8 CSV dump via ADODB.Stream", "group": "Database dumps"},
    "wine_scripts/test_dao.js": {"desc": "DAO.DBEngine.36 COM test", "group": "Testing"},
    "wine_scripts/compare_databases.py": {"desc": "PDX/PDB file comparison", "group": "Verification"},
    "wine_scripts/setup_list.js": {"desc": "configure selected pull list in DB", "group": "Database setup"},
    "wine_scripts/count_list.js": {"desc": "list all List table entries", "group": "Database inspection"},
    "wine_scripts/show_db_tables.js": {"desc": "list tables with row counts", "group": "Database inspection"},
    "wine_scripts/dump_list_category.js": {"desc": "dump List and Category tables", "group": "Database inspection"},
    "wine_scripts/test_read_file.js": {"desc": "Wine file access test", "group": "Testing"},
    "wine_scripts/clear_db.js": {"desc": "clear LibItem and List tables", "group": "Database setup"},
    "wine_scripts/setup_checked.js": {"desc": "pre-insert checked List 58", "group": "Database setup"},
    "wine_scripts/list_all_tables.js": {"desc": "list all tables with types", "group": "Database inspection"},
    "wine_scripts/dump_ddminfo.js": {"desc": "dump DDMInfo table", "group": "Database inspection"},
    "wine_scripts/dump_format.js": {"desc": "dump Format + FormatParm joined", "group": "Database inspection"},
    "wine_scripts/list_columns.js": {"desc": "list FormatParm table columns", "group": "Database inspection"},
    "wine_scripts/list_format_columns.js": {"desc": "list Format table columns", "group": "Database inspection"},
    "wine_scripts/list_all_columns.js": {"desc": "list all columns for all tables", "group": "Database inspection"},
    "wine_scripts/dump_raw_formatparm.js": {"desc": "dump all FormatParm rows", "group": "Database inspection"},
    "wine_scripts/dump_formats.js": {"desc": "dump Format table", "group": "Database inspection"},
    "wine_scripts/dump_upload_formats.js": {"desc": "dump UploadFormat table", "group": "Database inspection"},
    "wine_scripts/dump_upload_format_parms.js": {"desc": "dump UploadFormatParm table", "group": "Database inspection"},
    "wine_scripts/dump_formats_db3.js": {"desc": "dump formats from backup DB", "group": "Database inspection"},
    "wine_scripts/count_libitems.js": {"desc": "count LibItem and List rows", "group": "Database inspection"},
    "dla_tool.py": {"desc": "native Linux DLA export/import tool", "group": "Core tool"},
    "build_all_floors.sh": {"desc": "master build script for all floors", "group": "Build automation"},
    "execute_export_final.sh": {"desc": "Wine GUI export automation", "group": "Wine automation"},
    "test_sort.py": {"desc": "sort verification test", "group": "Testing"},
    "compare_a.py": {"desc": "comparison utility for Floor A", "group": "Verification"},
    "list_libitem_columns.js": {"desc": "list LibItem table columns", "group": "Database inspection"},
    "check_seqnbr.js": {"desc": "sequence number checker", "group": "Testing"},
    "list_indexes.js": {"desc": "list database indexes", "group": "Database inspection"},
}

BASE_TO_PATH = {
    "dump_db.js": "wine_scripts/dump_db.js",
    "dump_db_csv.js": "wine_scripts/dump_db_csv.js",
    "dump_db_utf8.js": "wine_scripts/dump_db_utf8.js",
    "test_dao.js": "wine_scripts/test_dao.js",
    "compare_databases.py": "wine_scripts/compare_databases.py",
    "setup_list.js": "wine_scripts/setup_list.js",
    "count_list.js": "wine_scripts/count_list.js",
    "show_db_tables.js": "wine_scripts/show_db_tables.js",
    "dump_list_category.js": "wine_scripts/dump_list_category.js",
    "test_read_file.js": "wine_scripts/test_read_file.js",
    "clear_db.js": "wine_scripts/clear_db.js",
    "setup_checked.js": "wine_scripts/setup_checked.js",
    "list_all_tables.js": "wine_scripts/list_all_tables.js",
    "dump_ddminfo.js": "wine_scripts/dump_ddminfo.js",
    "dump_format.js": "wine_scripts/dump_format.js",
    "list_columns.js": "wine_scripts/list_columns.js",
    "list_format_columns.js": "wine_scripts/list_format_columns.js",
    "list_all_columns.js": "wine_scripts/list_all_columns.js",
    "dump_raw_formatparm.js": "wine_scripts/dump_raw_formatparm.js",
    "dump_formats.js": "wine_scripts/dump_formats.js",
    "dump_upload_formats.js": "wine_scripts/dump_upload_formats.js",
    "dump_upload_format_parms.js": "wine_scripts/dump_upload_format_parms.js",
    "dump_formats_db3.js": "wine_scripts/dump_formats_db3.js",
    "count_libitems.js": "wine_scripts/count_libitems.js",
    "dla_tool.py": "dla_tool.py",
    "build_all_floors.sh": "build_all_floors.sh",
    "execute_export_final.sh": "execute_export_final.sh",
    "test_sort.py": "test_sort.py",
    "compare_a.py": "compare_a.py",
    "list_libitem_columns.js": "list_libitem_columns.js",
    "check_seqnbr.js": "check_seqnbr.js",
    "list_indexes.js": "list_indexes.js",
}

REST_OF_HISTORY = [
    "333ad16", "85e29eb", "ca74618", "d89708f", "de0d474",
    "31bff56", "e0d4544", "6d0b266", "8a8aeb7", "e228f67",
    "c31c32b", "ccbdd31", "4fdff76", "6122aab", "7e814aa",
    "63351a4", "a1855ff", "4779aa9", "72d4da3",
]

def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)

def git_add(path):
    r = run(f'git add "{path}"')
    assert r.returncode == 0, f"git add failed: {r.stderr}"

def git_commit(msg, date_str):
    env = {
        'GIT_AUTHOR_NAME': AUTHOR_NAME, 'GIT_AUTHOR_EMAIL': AUTHOR_EMAIL,
        'GIT_AUTHOR_DATE': date_str,
        'GIT_COMMITTER_NAME': AUTHOR_NAME, 'GIT_COMMITTER_EMAIL': AUTHOR_EMAIL,
        'GIT_COMMITTER_DATE': date_str,
    }
    safe_msg = msg.replace('`', "'").replace('"', "'")
    r = run(f'git commit -m "{safe_msg}"', env={**dict(os.environ), **env})
    assert r.returncode == 0, f"git commit failed: {r.stderr}"
    print(f"  ✓ {msg[:80]}")

def extract_timestamps(transcript_path):
    """Parse transcript.jsonl to find file creation timestamps."""
    results = {}
    with open(transcript_path) as f:
        for line in f:
            d = json.loads(line)
            content = d.get('content', '')
            if not isinstance(content, str):
                continue
            path_match = re.search(r'file://([^`]+)', content)
            if not path_match:
                continue
            created_path = path_match.group(1)
            ts_match = re.search(r'Created At:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\+\d{2}:\d{2}', content)
            if ts_match:
                ts = ts_match.group(1)
                for base_name in BASE_TO_PATH:
                    if base_name in created_path:
                        file_path = BASE_TO_PATH[base_name]
                        if file_path not in results:
                            results[file_path] = ts
                            break
    return results

def extract_context(transcript_path, target_files):
    """Extract context from session - look for MODEL thinking."""
    contexts = {}
    with open(transcript_path) as f:
        for line in f:
            d = json.loads(line)
            source = d.get('source', '')
            content = d.get('content', '')
            if source != 'MODEL' or not isinstance(content, str):
                continue
            for target in target_files:
                if target in content and target not in contexts:
                    sentences = re.split(r'[.!?]', content)
                    relevant = []
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) > 30 and len(sentence) < 250:
                            if not any(skip in sentence.lower() for skip in [
                                'hint:', 'created at', 'completed at', 'created file',
                                'file path', 'total lines', 'total bytes', '17848',
                                'tool action', 'tool summary', 'run_command', 'view_file',
                                'replace_file_content', 'proactively', 'permission',
                                'terminal commands', 'git', '[master', 'create mode'
                            ]):
                                if any(kw in sentence.lower() for kw in [
                                    'jscript', 'ado', 'script', 'helper', 'utility',
                                    'used to', 'purpose', 'function', 'creates',
                                    'connects', 'dumps', 'lists', 'inspects',
                                    'checks', 'verifies', 'compares', 'configures',
                                    'database', 'wine', 'export', 'import'
                                ]):
                                    relevant.append(sentence)
                    if relevant:
                        contexts[target] = '. '.join(relevant[:1])
    return contexts

def format_date(iso_str):
    return iso_str.replace('T', 'T') + "+0200"

def build_commit_message(filepath, category_info, context):
    desc = category_info['desc']
    group = category_info['group']
    basename = filepath.split('/')[-1]
    msg = f"wine_scripts: add {basename} - {desc}"
    if context and len(context) > 20:
        msg += f"\n\n{group}: {context}"
    return msg

def main():
    transcript_path = Path("/home/dpavlin/.gemini/antigravity-cli/brain/9b03c93f-645d-4730-8b11-878c7d0e8597/.system_generated/logs/transcript.jsonl")
    
    print("Parsing transcript.jsonl for timestamps and context...")
    timestamps = extract_timestamps(transcript_path)
    contexts = extract_context(transcript_path, FILE_CATEGORIES.keys())
    
    print(f"\nFound {len(timestamps)} files with creation timestamps:")
    for filepath, ts in sorted(timestamps.items(), key=lambda x: x[1]):
        print(f"  {ts}  {filepath}")
    
    missing = [f for f in FILE_CATEGORIES if f not in timestamps]
    if missing:
        print(f"\n⚠ Missing timestamps for: {', '.join(missing)}")
    
    # Build ordered list sorted by timestamp
    files_ordered = []
    for filepath, cat_info in FILE_CATEGORIES.items():
        ts = timestamps.get(filepath, "2026-07-23T12:00:00")
        date_str = format_date(ts)
        files_ordered.append((filepath, ts, date_str))
    files_ordered.sort(key=lambda x: x[1])
    
    # Step 1: Create empty initial commit on orphan branch
    print("\nStep 1: Creating empty initial commit...")
    run('git checkout --orphan _timeline_build 2>/dev/null')
    run('git rm -r --cached . 2>/dev/null')
    run('git checkout . 2>/dev/null')
    subprocess.run('git commit --allow-empty -m "Initial commit of DLA-libre compiler, automation scripts, and auxiliary tools" --date="2026-07-23T18:52:08+0200"',
                   shell=True, env={**os.environ, 'GIT_AUTHOR_NAME': AUTHOR_NAME, 'GIT_AUTHOR_EMAIL': AUTHOR_EMAIL,
                                    'GIT_COMMITTER_NAME': AUTHOR_NAME, 'GIT_COMMITTER_EMAIL': AUTHOR_EMAIL})
    run('git checkout -b master-timeline')
    print("  ✓ Empty initial commit created on master-timeline branch")
    
    # Step 2: Add files in chronological order
    print(f"\nStep 2: Adding {len(files_ordered)} files in chronological order...")
    for filepath, ts, date_str in files_ordered:
        category_info = FILE_CATEGORIES[filepath]
        context = contexts.get(filepath, "")
        msg = build_commit_message(filepath, category_info, context)
        git_add(filepath)
        git_commit(msg, date_str)
    
    # Step 3: Cherry-pick rest of history
    print(f"\nStep 3: Adding rest of history ({len(REST_OF_HISTORY)} commits)...")
    for commit_sha in REST_OF_HISTORY:
        r = run(f'git cherry-pick {commit_sha}')
        if r.returncode != 0:
            print(f"  ⚠ Conflict in {commit_sha}, attempting to continue...")
            r = run('git cherry-pick --continue', input='y\n')
            assert r.returncode == 0, f"Cherry-pick failed for {commit_sha}: {r.stderr}"
        print(f"  ✓ Cherry-picked {commit_sha[:7]}")
    
    total = 1 + len(files_ordered) + len(REST_OF_HISTORY)
    print(f"\n✓ Done! {total} commits total")
    print("Verify with:")
    print("  git log --reverse --format='%ai %s'")

if __name__ == "__main__":
    main()
