var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
    var rs = conn.OpenSchema(20); // adSchemaTables
    while (!rs.EOF) {
        var tableName = rs.Fields("TABLE_NAME").Value;
        var tableType = rs.Fields("TABLE_TYPE").Value;
        if (tableType == "TABLE") {
            try {
                var rsCount = conn.Execute("SELECT COUNT(*) FROM [" + tableName + "]");
                WScript.Echo("Table: " + tableName + " | Rows: " + rsCount.Fields(0).Value);
            } catch (ex) {
                WScript.Echo("Table: " + tableName + " | Error: " + ex.message);
            }
        }
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
