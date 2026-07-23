var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
} catch (e) {
    WScript.Echo("Connection failed: " + e.message);
    WScript.Quit(1);
}

var fso = new ActiveXObject("Scripting.FileSystemObject");

// Get list of tables (adSchemaTables = 20)
var rs = conn.OpenSchema(20); 
var tables = [];
while (!rs.EOF) {
    var tableType = rs.Fields("TABLE_TYPE").Value;
    if (tableType == "TABLE") {
        tables.push(rs.Fields("TABLE_NAME").Value);
    }
    rs.MoveNext();
}
rs.Close();

function escapeCSV(val) {
    if (val === null) return "";
    var s = String(val);
    s = s.replace(/"/g, '""');
    return '"' + s + '"';
}

for (var i = 0; i < tables.length; i++) {
    var tableName = tables[i];
    WScript.Echo("Dumping table to CSV: " + tableName);
    
    var rsTable = new ActiveXObject("ADODB.Recordset");
    try {
        rsTable.Open("SELECT * FROM [" + tableName + "]", conn, 1, 3);
        
        var outFile = fso.CreateTextFile("C:\\" + tableName + ".csv", true);
        
        // Write header
        var header = [];
        for (var f = 0; f < rsTable.Fields.Count; f++) {
            header.push(escapeCSV(rsTable.Fields(f).Name));
        }
        outFile.WriteLine(header.join(","));
        
        // Write rows
        var count = 0;
        while (!rsTable.EOF) {
            var row = [];
            for (var f = 0; f < rsTable.Fields.Count; f++) {
                row.push(escapeCSV(rsTable.Fields(f).Value));
            }
            outFile.WriteLine(row.join(","));
            count++;
            rsTable.MoveNext();
        }
        rsTable.Close();
        outFile.Close();
        WScript.Echo("  Dumped " + count + " rows.");
    } catch (e) {
        WScript.Echo("Failed to dump table " + tableName + ": " + e.message);
    }
}

conn.Close();
WScript.Echo("All tables dumped to CSV successfully!");
