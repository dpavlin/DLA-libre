var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=Z:\\home\\dpavlin\\DLA\\DLA-program-i-files\\program\\3M Library Systems\\Data Manager\\db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    
    // Dump Format table
    WScript.Echo("=== Formats ===");
    var rs = conn.Execute("SELECT * FROM [Format]");
    while (!rs.EOF) {
        WScript.Echo("FormatID: " + rs.Fields("FormatID").Value + 
                     " | Name: " + rs.Fields("FormatName").Value + 
                     " | Parser: " + rs.Fields("ParserName").Value);
        rs.MoveNext();
    }
    
    // Dump FormatParm table
    WScript.Echo("\n=== Format Parameters ===");
    rs = conn.Execute("SELECT * FROM [FormatParm]");
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
