var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
conn.Open(connStr);

// Dump List table
WScript.Echo("=== List Table ===");
var rs = conn.Execute("SELECT * FROM List");
var cols = [];
for (var i = 0; i < rs.Fields.Count; i++) cols.push(rs.Fields(i).Name);
WScript.Echo(cols.join(" | "));
while (!rs.EOF) {
    var row = [];
    for (var i = 0; i < rs.Fields.Count; i++) {
        try { row.push(rs.Fields(i).Value); } catch(e) { row.push("(null)"); }
    }
    WScript.Echo(row.join(" | "));
    rs.MoveNext();
}
rs.Close();

// Dump ExpPullFormats
WScript.Echo("\n=== ExpPullFormats ===");
var rs2 = conn.Execute("SELECT * FROM ExpPullFormats");
var cols2 = [];
for (var i = 0; i < rs2.Fields.Count; i++) cols2.push(rs2.Fields(i).Name);
WScript.Echo(cols2.join(" | "));
while (!rs2.EOF) {
    var row2 = [];
    for (var i = 0; i < rs2.Fields.Count; i++) {
        try { row2.push(rs2.Fields(i).Value); } catch(e) { row2.push("(null)"); }
    }
    WScript.Echo(row2.join(" | "));
    rs2.MoveNext();
}
rs2.Close();

// Dump ListGroup
WScript.Echo("\n=== ListGroup ===");
try {
    var rs3 = conn.Execute("SELECT * FROM ListGroup");
    var cols3 = [];
    for (var i = 0; i < rs3.Fields.Count; i++) cols3.push(rs3.Fields(i).Name);
    WScript.Echo(cols3.join(" | "));
    while (!rs3.EOF) {
        var row3 = [];
        for (var i = 0; i < rs3.Fields.Count; i++) {
            try { row3.push(rs3.Fields(i).Value); } catch(e) { row3.push("(null)"); }
        }
        WScript.Echo(row3.join(" | "));
        rs3.MoveNext();
    }
    rs3.Close();
} catch(e) {
    WScript.Echo("Error: " + e.message);
}

conn.Close();
