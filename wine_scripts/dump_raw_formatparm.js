var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.Execute("SELECT * FROM [FormatParm]");
    while (!rs.EOF) {
        WScript.Echo("FormatID: " + rs.Fields("FormatID").Value + 
                     " | Parm: " + rs.Fields("ParmName").Value + 
                     " | Value: " + rs.Fields("ParmValue").Value);
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
