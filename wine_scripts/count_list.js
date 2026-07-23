var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
    var rs = conn.Execute("SELECT ListID, ListPathName, Selected FROM [List]");
    while (!rs.EOF) {
        WScript.Echo("ID: " + rs.Fields(0).Value + " | Path: " + rs.Fields(1).Value + " | Selected: " + rs.Fields(2).Value);
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
