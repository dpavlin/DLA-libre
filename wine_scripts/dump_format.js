var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    
    // Dump joined Format and FormatParm
    WScript.Echo("=== FORMAT PARAMETERS ===");
    var sql = "SELECT f.FormatName, fp.ParmName, fp.ParmValue " +
              "FROM [Format] f INNER JOIN [FormatParm] fp ON f.FormatID = fp.FormatID " +
              "ORDER BY f.FormatName, fp.ParmName";
    var rs = conn.Execute(sql);
    while (!rs.EOF) {
        WScript.Echo("Format: " + rs.Fields("FormatName").Value + 
                     " | Parm: " + rs.Fields("ParmName").Value + 
                     " | Value: " + rs.Fields("ParmValue").Value);
        rs.MoveNext();
    }
    
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
