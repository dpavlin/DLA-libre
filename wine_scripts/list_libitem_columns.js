var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.OpenSchema(4); // adSchemaColumns
    while (!rs.EOF) {
        if (rs.Fields("TABLE_NAME").Value == "LibItem") {
            WScript.Echo("Col: " + rs.Fields("COLUMN_NAME").Value + 
                         " | Type: " + rs.Fields("DATA_TYPE").Value + 
                         " | MaxLen: " + rs.Fields("CHARACTER_MAXIMUM_LENGTH").Value);
        }
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
