var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
    
    // Dump Category table
    WScript.Echo("=== CATEGORIES ===");
    var rsCat = conn.Execute("SELECT * FROM [Category]");
    var catFields = [];
    for (var i = 0; i < rsCat.Fields.Count; i++) {
        catFields.push(rsCat.Fields(i).Name);
    }
    WScript.Echo("Fields: " + catFields.join(", "));
    while (!rsCat.EOF) {
        var row = [];
        for (var i = 0; i < rsCat.Fields.Count; i++) {
            row.push(rsCat.Fields(i).Value);
        }
        WScript.Echo("Row: " + row.join(" | "));
        rsCat.MoveNext();
    }

    // Dump List table columns
    WScript.Echo("\n=== LISTS ===");
    var rsList = conn.Execute("SELECT * FROM [List]");
    var listFields = [];
    for (var i = 0; i < rsList.Fields.Count; i++) {
        listFields.push(rsList.Fields(i).Name);
    }
    WScript.Echo("Fields: " + listFields.join(", "));
    while (!rsList.EOF) {
        var row = [];
        for (var i = 0; i < rsList.Fields.Count; i++) {
            row.push(rsList.Fields(i).Value);
        }
        WScript.Echo("Row: " + row.join(" | "));
        rsList.MoveNext();
    }

    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
