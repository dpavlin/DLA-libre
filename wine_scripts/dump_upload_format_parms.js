var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.Execute("SELECT * FROM [UploadFormatParm]");
    while (!rs.EOF) {
        WScript.Echo("UploadFormatID: " + rs.Fields("FormatID").Value + 
                     " | ParmID: " + rs.Fields("FormatParmID").Value + 
                     " | Index: " + rs.Fields("ParmIndex").Value + 
                     " | Value: " + rs.Fields("ParmValue").Value);
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
