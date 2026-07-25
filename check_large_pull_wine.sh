#!/usr/bin/env bash
set -x

killall -9 Xvfb wine DataManager.exe || true
rm -f /tmp/.X99-lock || true

# Clear previous card pull folder
rm -rf /home/dpavlin/DLA/Card/pull/*
mkdir -p /home/dpavlin/DLA/Card/pull/

# 1. Run DataManager for 10 seconds to detect the new tab file and add it to database
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!
sleep 2

cd "/home/dpavlin/.wine/drive_c/Program Files/3M Library Systems/Data Manager/Exe"
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!

sleep 10
kill -9 $WINE_PID || true
sleep 2

# 2. Update database using WSH to select only pull_koha_large.tab
cat << 'EOF' > /tmp/select_large_pull.js
var conn = new ActiveXObject("ADODB.Connection");
var connStr = "Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\Program Files\\3M Library Systems\\Data Manager\\Db\\DataManager.mdb;Jet OLEDB:Database Password=technician;";
try {
    conn.Open(connStr);
    conn.Execute("UPDATE [List] SET [Selected] = False");
    
    // Find the ListID for pull_koha_large
    var rs = conn.Execute("SELECT ListID FROM [List] WHERE [ListPathName] LIKE '%pull_koha_large.tab%'");
    if (!rs.EOF) {
        var listID = rs.Fields(0).Value;
        conn.Execute("UPDATE [List] SET [Selected] = True WHERE [ListID] = " + listID);
        WScript.Echo("[+] Selected large pull list, ListID = " + listID);
    } else {
        WScript.Echo("[-] Error: pull_koha_large.tab not found in database.");
    }
    conn.Close();
} catch (e) {
    WScript.Echo("Error: " + e.message);
}
EOF
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "Z:\\tmp\\select_large_pull.js"
sleep 2

# 3. Launch app again and compile the database
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!
sleep 10

echo "[*] Triggering Export..."
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key e
sleep 3
DISPLAY=:99 xdotool key Return
sleep 5
DISPLAY=:99 xdotool key Return
sleep 10

# Exit App
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key x
sleep 4

kill -9 $WINE_PID || true
kill -9 $XVFB_PID || true
killall -9 Xvfb wine DataManager.exe || true

echo "=== Files in pull folder ==="
find /home/dpavlin/DLA/Card/pull -type f
