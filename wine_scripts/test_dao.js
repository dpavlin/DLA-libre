var fso = new ActiveXObject("Scripting.FileSystemObject");
var logFile = fso.CreateTextFile("C:\\test_dao.log", true);

try {
    logFile.WriteLine("Attempting to create DAO.DBEngine.36...");
    var x = new ActiveXObject("DAO.DBEngine.36");
    logFile.WriteLine("Success! Created DAO.DBEngine.36 object successfully.");
} catch(e) {
    logFile.WriteLine("Failed to create DAO.DBEngine.36: " + e.message + " (Code: " + e.number + ")");
}

logFile.Close();
WScript.Echo("Finished writing log.");
