#!/usr/bin/env bash
set -x

killall -9 Xvfb wine DataManager.exe || true
rm -f /tmp/.X99-lock || true

# 1. Setup Card Upload folders
mkdir -p /home/dpavlin/DLA/Card/upload/inv/
rm -f /home/dpavlin/DLA/Card/upload/inv/*
rm -rf /home/dpavlin/DLA/Import/*
mkdir -p /home/dpavlin/DLA/Import/

# Copy sample upload file
cp /home/dpavlin/DLA/test/upload/inv/001.pdX /home/dpavlin/DLA/Card/upload/inv/001.pdX

# 2. Launch App under XVFB
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!
sleep 2

cd "/home/dpavlin/.wine/drive_c/Program Files/3M Library Systems/Data Manager/Exe"
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!

sleep 10

# 3. Trigger Import using menu (Alt+F, then I)
echo "[*] Triggering Import..."
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key i
sleep 5

# Take screenshot to see if a dialog is shown
DISPLAY=:99 ffmpeg -y -f x11grab -video_size 1024x768 -i :99 -vframes 1 /home/dpavlin/.wine/drive_c/screenshot_import_dialog.png

# 4. Try pressing Return to dismiss any OK dialogs
DISPLAY=:99 xdotool key Return
sleep 3

# Take another screenshot
DISPLAY=:99 ffmpeg -y -f x11grab -video_size 1024x768 -i :99 -vframes 1 /home/dpavlin/.wine/drive_c/screenshot_import_done.png

# 5. Clean Exit
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key x
sleep 4

kill -9 $WINE_PID || true
kill -9 $XVFB_PID || true
killall -9 Xvfb wine DataManager.exe || true

echo "=== Files in Import folder ==="
find /home/dpavlin/DLA/Import -type f
