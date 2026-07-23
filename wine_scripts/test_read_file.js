var fso = new ActiveXObject("Scripting.FileSystemObject");
try {
    var file = fso.OpenTextFile("D:\\DLA\\ShelfOrderList\\A.tab", 1);
    WScript.Echo("Line 1: " + file.ReadLine());
    file.Close();
} catch (e) {
    WScript.Echo("Error reading file: " + e.message);
}
