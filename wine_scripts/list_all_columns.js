var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.OpenSchema(4); // adSchemaColumns
    var currentTable = "";
    while (!rs.EOF) {
        var tableName = rs.Fields("TABLE_NAME").Value;
        var columnName = rs.Fields("COLUMN_NAME").Value;
        
        // Skip system tables (starting with MSys)
        if (tableName.substring(0, 4) != "MSys") {
            if (tableName != currentTable) {
                WScript.Echo("\nTable: " + tableName);
                currentTable = tableName;
            }
            WScript.Echo("  Column: " + columnName);
        }
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
