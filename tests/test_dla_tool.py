#!/usr/bin/env python3
"""
Test suite for dla_tool.py (CLI) vs dla_tool_lib.py (library).

For each command (export, export-pull, import, import-pull):
1. Run the CLI version with a test input file.
2. Run the library version with the same input file.
3. Compare all output files byte-for-byte.
4. Assert they are identical.

Uses historic inventory data from /home/dpavlin/DLA/ as input sources.
"""
import os
import sys
import shutil
import tempfile
import hashlib
import unittest

# Import both the CLI and library
import dla_tool as cli
import dla_tool_lib as lib


# ---------------------------------------------------------------------------
# Test data paths
# ---------------------------------------------------------------------------
TAB_FILES = [
    "/home/dpavlin/DLA/ShelfOrderList/A.tab",
    "/home/dpavlin/DLA/PullList/pull1.tab",
    "/home/dpavlin/DLA/test/upload/inv/001.pdX",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def file_hash(path):
    """Return MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_dirs(dir_a, dir_b):
    """Compare two directories recursively. Returns list of differing files."""
    diffs = []
    all_files = set()
    for root, _, files in os.walk(dir_a):
        rel = os.path.relpath(root, dir_a)
        for f in files:
            if rel == ".":
                all_files.add(f)
            else:
                all_files.add(os.path.join(rel, f))
    for root, _, files in os.walk(dir_b):
        rel = os.path.relpath(root, dir_b)
        for f in files:
            if rel == ".":
                all_files.add(f)
            else:
                all_files.add(os.path.join(rel, f))

    for f in sorted(all_files):
        path_a = os.path.join(dir_a, f)
        path_b = os.path.join(dir_b, f)
        if os.path.exists(path_a) and os.path.exists(path_b):
            h_a = file_hash(path_a)
            h_b = file_hash(path_b)
            if h_a != h_b:
                diffs.append(f"  {f}: CLI={h_a}  LIB={h_b}")
        elif os.path.exists(path_a):
            diffs.append(f"  {f}: MISSING in library")
        else:
            diffs.append(f"  {f}: MISSING in CLI")
    return diffs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestExport(unittest.TestCase):
    """Compare dla_tool export vs dla_tool_lib.cmd_export."""

    def setUp(self):
        self.cli_dir = tempfile.mkdtemp()
        self.lib_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.cli_dir, ignore_errors=True)
        shutil.rmtree(self.lib_dir, ignore_errors=True)

    def test_export_floor_a(self):
        input_file = "/home/dpavlin/DLA/ShelfOrderList/A.tab"
        if not os.path.exists(input_file):
            self.skipTest(f"Input file not found: {input_file}")

        # CLI run
        cli_args = cli.argparse.Namespace(
            input_file=input_file,
            output_dir=self.cli_dir,
            max_items=16384,
        )
        cli.cmd_export(cli_args)

        # Library run
        lib_args = lib.argparse.Namespace(
            input_file=input_file,
            output_dir=self.lib_dir,
            max_items=16384,
        )
        lib.cmd_export(lib_args)

        diffs = compare_dirs(
            os.path.join(self.cli_dir, "Database"),
            os.path.join(self.lib_dir, "Database"),
        )
        if diffs:
            self.fail("Export mismatch:\n" + "\n".join(diffs))


class TestExportPull(unittest.TestCase):
    """Compare dla_tool export-pull vs dla_tool_lib.cmd_export_pull."""

    def setUp(self):
        self.cli_dir = tempfile.TemporaryDirectory()
        self.lib_dir = tempfile.TemporaryDirectory()
        self.cli_out = os.path.join(self.cli_dir.name, "PL001.pdb")
        self.lib_out = os.path.join(self.lib_dir.name, "PL001.pdb")

    def tearDown(self):
        self.cli_dir.cleanup()
        self.lib_dir.cleanup()

    def test_export_pull_small(self):
        input_file = "/home/dpavlin/DLA/PullList/pull1.tab"
        if not os.path.exists(input_file):
            self.skipTest(f"Input file not found: {input_file}")

        # CLI run
        cli_args = cli.argparse.Namespace(
            input_file=input_file,
            output_file=self.cli_out,
            description="test",
        )
        cli.cmd_export_pull(cli_args)

        # Library run
        lib_args = lib.argparse.Namespace(
            input_file=input_file,
            output_file=self.lib_out,
            description="test",
        )
        lib.cmd_export_pull(lib_args)

        # Compare PDB files
        h_cli = file_hash(self.cli_out)
        h_lib = file_hash(self.lib_out)
        self.assertEqual(h_cli, h_lib, f"export-pull PDB mismatch: CLI={h_cli} LIB={h_lib}")

        # Compare PL000.tmp (should be identical since same input)
        cli_tmp = self.cli_dir.name + "/PL000.tmp"
        lib_tmp = self.lib_dir.name + "/PL000.tmp"
        if os.path.exists(cli_tmp) and os.path.exists(lib_tmp):
            h_cli_tmp = file_hash(cli_tmp)
            h_lib_tmp = file_hash(lib_tmp)
            self.assertEqual(h_cli_tmp, h_lib_tmp,
                             f"PL000.tmp mismatch: CLI={h_cli_tmp} LIB={h_lib_tmp}")


class TestImport(unittest.TestCase):
    """Compare dla_tool import vs dla_tool_lib.cmd_import."""

    def setUp(self):
        self.cli_dir = tempfile.TemporaryDirectory()
        self.lib_dir = tempfile.TemporaryDirectory()
        self.cli_out = os.path.join(self.cli_dir.name, "output.csv")
        self.lib_out = os.path.join(self.lib_dir.name, "output.csv")

    def tearDown(self):
        self.cli_dir.cleanup()
        self.lib_dir.cleanup()

    def test_import_scan(self):
        input_file = "/home/dpavlin/DLA/test/upload/inv/001.pdX"
        if not os.path.exists(input_file):
            self.skipTest(f"Input file not found: {input_file}")

        # CLI run
        cli_args = cli.argparse.Namespace(
            input_file=input_file,
            output_file=self.cli_out,
        )
        cli.cmd_import(cli_args)

        # Library run
        lib_args = lib.argparse.Namespace(
            input_file=input_file,
            output_file=self.lib_out,
        )
        lib.cmd_import(lib_args)

        # Compare only CSV files (not /tmp socket files etc)
        csv_diffs = []
        all_files = set()
        for root, _, files in os.walk(self.cli_dir.name):
            for f in files:
                if f.endswith(".csv"):
                    all_files.add(f)
        for root, _, files in os.walk(self.lib_dir.name):
            for f in files:
                if f.endswith(".csv"):
                    all_files.add(f)

        for f in sorted(all_files):
            path_a = os.path.join(self.cli_dir.name, f)
            path_b = os.path.join(self.lib_dir.name, f)
            h_a = file_hash(path_a)
            h_b = file_hash(path_b)
            if h_a != h_b:
                csv_diffs.append(f"  {f}: CLI={h_a}  LIB={h_b}")

        if csv_diffs:
            self.fail("Import mismatch:\n" + "\n".join(csv_diffs))


class TestImportPull(unittest.TestCase):
    """Compare dla_tool import-pull vs dla_tool_lib.cmd_import_pull."""

    def setUp(self):
        self.cli_dir = tempfile.TemporaryDirectory()
        self.lib_dir = tempfile.TemporaryDirectory()
        self.cli_prefix = os.path.join(self.cli_dir.name, "result")
        self.lib_prefix = os.path.join(self.lib_dir.name, "result")

    def tearDown(self):
        self.cli_dir.cleanup()
        self.lib_dir.cleanup()

    def test_import_pull(self):
        # Use the small pull list
        original_file = "/home/dpavlin/DLA/PullList/pull1.tab"
        # We need a card file - use the CLI-generated one as a stand-in
        card_file = "/home/dpavlin/DLA/test/E2/Export/pull/PL001.pdb"
        if not os.path.exists(original_file) or not os.path.exists(card_file):
            self.skipTest("Test files not found")

        # CLI run
        cli_args = cli.argparse.Namespace(
            original_file=original_file,
            card_file=card_file,
            output_prefix=self.cli_prefix,
        )
        cli.cmd_import_pull(cli_args)

        # Library run
        lib_args = lib.argparse.Namespace(
            original_file=original_file,
            card_file=card_file,
            output_prefix=self.lib_prefix,
        )
        lib.cmd_import_pull(lib_args)

        diffs = compare_dirs(self.cli_dir.name, self.lib_dir.name)
        if diffs:
            self.fail("import-pull mismatch:\n" + "\n".join(diffs))


if __name__ == "__main__":
    unittest.main()
