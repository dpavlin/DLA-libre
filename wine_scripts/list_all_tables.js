var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.OpenSchema(20); // adSchemaTables
    while (!rs.EOF) {
        WScript.Echo("Table: " + rs.Fields("TABLE_NAME").Value + " | Type: " + rs.Fields("TABLE_TYPE").Value);
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
