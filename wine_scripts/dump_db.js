var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";

try {
    conn.Open(connStr);
} catch (e) {
    WScript.Echo("Connection failed: " + e.message);
    WScript.Quit(1);
}

var fso = new ActiveXObject("Scripting.FileSystemObject");
var outFile = fso.CreateTextFile("C:\\db_dump.json", true);

// Get list of tables (adSchemaTables = 20)
var rs = conn.OpenSchema(20); 
var tables = [];
while (!rs.EOF) {
    var tableType = rs.Fields("TABLE_TYPE").Value;
    if (tableType == "TABLE") {
        tables.push(rs.Fields("TABLE_NAME").Value);
    }
    rs.MoveNext();
}
rs.Close();

var dbData = {};

for (var i = 0; i < tables.length; i++) {
    var tableName = tables[i];
    WScript.Echo("Dumping table: " + tableName);
    dbData[tableName] = [];
    
    var rsTable = new ActiveXObject("ADODB.Recordset");
    try {
        rsTable.Open("SELECT * FROM [" + tableName + "]", conn, 1, 3);
        
        while (!rsTable.EOF) {
            var row = {};
            for (var f = 0; f < rsTable.Fields.Count; f++) {
                var fName = rsTable.Fields(f).Name;
                var val = rsTable.Fields(f).Value;
                if (val === null) {
                    row[fName] = null;
                } else {
                    row[fName] = String(val);
                }
            }
            dbData[tableName].push(row);
            rsTable.MoveNext();
        }
        rsTable.Close();
    } catch (e) {
        WScript.Echo("Failed to dump table " + tableName + ": " + e.message);
    }
}

// Simple JSON stringify helper for legacy JScript environment
function jsonStringify(obj) {
    if (obj === null) return "null";
    if (typeof obj === "string") {
        return '"' + obj.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t') + '"';
    }
    if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
    if (obj instanceof Array) {
        var arr = [];
        for (var i = 0; i < obj.length; i++) {
            arr.push(jsonStringify(obj[i]));
        }
        return "[" + arr.join(",") + "]";
    }
    if (typeof obj === "object") {
        var props = [];
        for (var key in obj) {
            props.push('"' + key + '":' + jsonStringify(obj[key]));
        }
        return "{" + props.join(",") + "}";
    }
    return '"' + String(obj) + '"';
}

outFile.Write(jsonStringify(dbData));
outFile.Close();
conn.Close();
WScript.Echo("Schema and data dump complete!");
