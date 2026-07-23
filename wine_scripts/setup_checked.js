var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    conn.Execute("DELETE FROM [LibItem]");
    conn.Execute("DELETE FROM [List]");
    
    // Insert List 58 with Selected = True and NbrItems = 0
    var sql = "INSERT INTO [List] (ListID, ListPathName, Description, FormatName, SeqNbr, Selected, NbrItems, ListType) " +
              "VALUES (58, 'D:\\DLA\\ShelfOrderList\\A.tab', 'A', 'tab delimited', 9999999, True, 0, 1)";
    conn.Execute(sql);
    WScript.Echo("[+] Pre-inserted checked List 58.");
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
