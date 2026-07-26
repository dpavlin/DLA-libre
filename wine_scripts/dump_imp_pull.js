var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
conn.Open(connStr);

// Get columns for ImpPullFormats
var rsSchema = conn.OpenSchema(20);
while (!rsSchema.EOF) {
    if (rsSchema.Fields("TABLE_NAME").Value == "ImpPullFormats") {
        WScript.Echo("ImpPullFormats columns:");
        var rsCols = conn.OpenSchema(4, [null, null, "ImpPullFormats"]);
        while (!rsCols.EOF) {
            WScript.Echo("  " + rsCols.Fields("COLUMN_NAME").Value + " (" + rsCols.Fields("DATA_TYPE").Value + ")");
            rsCols.MoveNext();
        }
        rsCols.Close();
        break;
    }
    rsSchema.MoveNext();
}
rsSchema.Close();

// Dump data
WScript.Echo("\nImpPullFormats data:");
var rs = conn.Execute("SELECT * FROM ImpPullFormats ORDER BY FormatID");
WScript.Echo(rs.Fields(0).Name + " | " + rs.Fields(1).Name + " | " + rs.Fields(2).Name + " | " + rs.Fields(3).Name + " | " + rs.Fields(4).Name);
while (!rs.EOF) {
    var row = [];
    for (var i = 0; i < rs.Fields.Count; i++) {
        try { row.push(rs.Fields(i).Value); } catch(e) { row.push("(null)"); }
    }
    WScript.Echo(row.join(" | "));
    rs.MoveNext();
}
rs.Close();

conn.Close();
