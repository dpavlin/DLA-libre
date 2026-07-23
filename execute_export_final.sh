#!/bin/bash
# Final working export automation script with full dialog and parsing flow management

set -x

killall -9 Xvfb wine DataManager.exe || true
rm -f /tmp/.X99-lock || true

# 1. Clear database tables
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "C:\\clear_db.js"

# 2. Launch the app
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!
sleep 2

cd "/home/dpavlin/.wine/drive_c/Program Files/3M Library Systems/Data Manager/Exe"
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!

sleep 10  # Wait for app to start and auto-detect lists

# 3. Press F5 to refresh/parse all lists
echo "[*] Triggering Refresh (F5)..."
DISPLAY=:99 xdotool key F5
sleep 35  # Wait 35 seconds for all floors to be parsed into the database

# 4. Check all export lists using menu (Alt+L, then C)
echo "[*] Checking all lists..."
DISPLAY=:99 xdotool key alt+l
sleep 1
DISPLAY=:99 xdotool key c
sleep 2

# 5. Trigger Export using menu (Alt+F, then E) to open the "Export Lists and Categories" dialog
echo "[*] Triggering Export..."
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key e
sleep 3  # Wait for the dialog to appear

# 6. Dismiss the "Export Lists and Categories" dialog by pressing Return (to click OK and start export)
DISPLAY=:99 xdotool key Return
echo "[*] Waiting for compilation (120 seconds)..."
sleep 120  # Wait 2 minutes for parsing/compilation of all 262k items to finish

# 7. Dismiss the "Export completed successfully" dialog by pressing Return
DISPLAY=:99 xdotool key Return
sleep 2

# Take screenshot to verify final state
DISPLAY=:99 ffmpeg -y -f x11grab -video_size 1024x768 -i :99 -vframes 1 /home/dpavlin/.wine/drive_c/screenshot_final_success.png

# 8. Clean Exit
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key x
sleep 4

kill -9 $WINE_PID || true
kill -9 $XVFB_PID || true
killall -9 Xvfb wine DataManager.exe || true

# 9. Verify row counts and generated files
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "C:\\dump_list_category.js"
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "C:\\count_list.js"
WINEPREFIX=/home/dpavlin/.wine wine cscript.exe //NoLogo "C:\\count_libitems.js"

echo "=== Generated Files ==="
find /home/dpavlin/DLA/Card -type f

echo "[+] Done."
