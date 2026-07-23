var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
} catch (e) {
    WScript.Echo("Connection failed: " + e.message);
    WScript.Quit(1);
}

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
    WScript.Echo("Dumping table to CSV (UTF-8): " + tableName);
    
    var rsTable = new ActiveXObject("ADODB.Recordset");
    try {
        rsTable.Open("SELECT * FROM [" + tableName + "]", conn, 1, 3);
        
        var stream = new ActiveXObject("ADODB.Stream");
        stream.Type = 2; // adTypeText
        stream.Charset = "utf-8";
        stream.Open();
        
        // Write header
        var header = [];
        for (var f = 0; f < rsTable.Fields.Count; f++) {
            header.push(escapeCSV(rsTable.Fields(f).Name));
        }
        stream.WriteText(header.join(",") + "\r\n");
        
        // Write rows
        var count = 0;
        while (!rsTable.EOF) {
            var row = [];
            for (var f = 0; f < rsTable.Fields.Count; f++) {
                row.push(escapeCSV(rsTable.Fields(f).Value));
            }
            stream.WriteText(row.join(",") + "\r\n");
            count++;
            rsTable.MoveNext();
        }
        rsTable.Close();
        
        stream.SaveToFile("C:\\" + tableName + ".csv", 2); // adSaveCreateOverWrite
        stream.Close();
        WScript.Echo("  Dumped " + count + " rows.");
    } catch (e) {
        WScript.Echo("Failed to dump table " + tableName + ": " + e.message);
    }
}

conn.Close();
WScript.Echo("All tables dumped to CSV (UTF-8) successfully!");
