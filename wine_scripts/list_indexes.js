var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.OpenSchema(12); // adSchemaIndexes
    while (!rs.EOF) {
        if (rs.Fields("TABLE_NAME").Value == "LibItem") {
            WScript.Echo("Idx: " + rs.Fields("INDEX_NAME").Value + " | Col: " + rs.Fields("COLUMN_NAME").Value + " | Primary: " + rs.Fields("PRIMARY_KEY").Value);
        }
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
