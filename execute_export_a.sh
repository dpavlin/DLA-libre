#!/usr/bin/env bash
set -x

killall -9 Xvfb wine DataManager.exe || true
rm -f /tmp/.X99-lock || true

# Temporarily move other lists out of monitored folder
mv /home/dpavlin/DLA/ShelfOrderList/B.tab /home/dpavlin/DLA/
mv /home/dpavlin/DLA/ShelfOrderList/C.tab /home/dpavlin/DLA/
mv /home/dpavlin/DLA/ShelfOrderList/D.tab /home/dpavlin/DLA/
mv /home/dpavlin/DLA/ShelfOrderList/E.tab /home/dpavlin/DLA/
mv /home/dpavlin/DLA/ShelfOrderList/F.tab /home/dpavlin/DLA/

# 1. Clear database
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "C:\\clear_db.js"

# 2. Setup list (Select only Floor A and set path to A.tab)
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "C:\\setup_list.js"

# 3. Launch the app under XVFB
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!
sleep 2

cd "/home/dpavlin/.wine/drive_c/Program Files/3M Library Systems/Data Manager/Exe"
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!

sleep 10

# 4. Refresh / Parse lists (F5)
echo "[*] Triggering Refresh (F5)..."
DISPLAY=:99 xdotool key F5
sleep 15  # Wait for parsing Floor A (2760 items) to finish

# 5. Check all export lists using menu (Alt+L, then C)
echo "[*] Checking all lists..."
DISPLAY=:99 xdotool key alt+l
sleep 1
DISPLAY=:99 xdotool key c
sleep 2

# 6. Trigger Export using menu (Alt+F, then E)
echo "[*] Triggering Export..."
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key e
sleep 3

# 7. Press Return to start export
DISPLAY=:99 xdotool key Return
echo "[*] Waiting for compilation..."
sleep 25  # Wait for Floor A compilation

# 8. Press Return to dismiss "Export completed successfully"
DISPLAY=:99 xdotool key Return
sleep 2

# 9. Clean Exit
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key x
sleep 4

kill -9 $WINE_PID || true
kill -9 $XVFB_PID || true
killall -9 Xvfb wine DataManager.exe || true

# Restore other lists back to monitored folder
mv /home/dpavlin/DLA/B.tab /home/dpavlin/DLA/ShelfOrderList/
mv /home/dpavlin/DLA/C.tab /home/dpavlin/DLA/ShelfOrderList/
mv /home/dpavlin/DLA/D.tab /home/dpavlin/DLA/ShelfOrderList/
mv /home/dpavlin/DLA/E.tab /home/dpavlin/DLA/ShelfOrderList/
mv /home/dpavlin/DLA/F.tab /home/dpavlin/DLA/ShelfOrderList/

echo "=== Generated Files under /home/dpavlin/DLA/Card/Database/ ==="
find /home/dpavlin/DLA/Card/Database/ -type f
