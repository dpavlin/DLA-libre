import struct

# Read Wine mapping
wine_map = []
pdx_path = "/home/dpavlin/DLA/Card/Database/ndex/3F3F4431/id01/001-3MLH.pdX"
with open(pdx_path, "rb") as f:
    f.read(78) # header
    for _ in range(2760):
        val, = struct.unpack(">I", f.read(4))
        wine_map.append(val)

# Load A.tab
tab_lines = [line.strip().split("\t") for line in open("/home/dpavlin/DLA/ShelfOrderList/A.tab", "r").readlines()]
tab_data = [line for line in tab_lines if len(line) >= 3 and line[0] != "barcode"]
# Sort by barcode to get the same 1-based indexing as the barcode-sorted segment
barcode_sorted = sorted(tab_data, key=lambda x: x[0])

# Enforce title length limit when sorting, or format it
def get_title(row):
    # Enforce truncation exactly like data record: f"title: {title}"[:40][7:]
    title_formatted = f"title: {row[2]}"[:40]
    return title_formatted[7:]

# Create a list of tuples (1-based index, title, row)
indexed_rows = [(i + 1, get_title(row), row) for i, row in enumerate(barcode_sorted)]

# Let us try different sorting methods
# 1. Simple case-insensitive sorting (lowercased)
sorted_1 = sorted(indexed_rows, key=lambda x: x[1].lower())
map_1 = [x[0] for x in sorted_1]

# 2. Case-insensitive sorting with special char replacements if needed?
# Let us compare map_1 with wine_map
mismatches_1 = 0
for idx in range(len(wine_map)):
    if wine_map[idx] != map_1[idx]:
        mismatches_1 += 1
        if mismatches_1 <= 10:
            print(f"Mismatch {mismatches_1} at idx {idx}: Wine maps to {wine_map[idx]} (title: {get_title(barcode_sorted[wine_map[idx]-1])}), Native maps to {map_1[idx]} (title: {get_title(barcode_sorted[map_1[idx]-1])})")

print(f"Total mismatches with simple case-insensitive: {mismatches_1} out of 2760")
