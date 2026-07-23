var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
    var rsLibItem = conn.Execute("SELECT COUNT(*) FROM [LibItem]");
    WScript.Echo("LibItem count: " + rsLibItem.Fields(0).Value);
    
    var rsList = conn.Execute("SELECT COUNT(*) FROM [List]");
    WScript.Echo("List count: " + rsList.Fields(0).Value);
    
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
