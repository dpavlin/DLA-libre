var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    var rs = conn.Execute("SELECT Barcode, Primary, SeqNbr FROM LibItem WHERE SeqNbr IN (863, 864, 865, 866) ORDER BY SeqNbr");
    while (!rs.EOF) {
        WScript.Echo("BC: [" + rs.Fields("Barcode").Value + "] | Primary: [" + rs.Fields("Primary").Value + "] | SeqNbr: [" + rs.Fields("SeqNbr").Value + "]");
        rs.MoveNext();
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
