var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
    WScript.Echo("Successfully connected to DataManager.mdb.");
    
    // 1. Unselect all lists
    conn.Execute("UPDATE [List] SET [Selected] = False");
    WScript.Echo("Unselected all lists.");
    
    // 2. Select ListID 58 (Floor A) and update its path
    conn.Execute("UPDATE [List] SET [Selected] = True, [ListPathName] = 'D:\\DLA\\ShelfOrderList\\A.tab' WHERE [ListID] = 58");
    WScript.Echo("Selected list 58 (Floor A) and set path to D:\\DLA\\ShelfOrderList\\A.tab.");
    
    conn.Close();
    WScript.Echo("Setup completed successfully.");
} catch (e) {
    WScript.Echo("Error during database update: " + e.message);
    WScript.Quit(1);
}
