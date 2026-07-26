#!/usr/bin/env bash
set -x

killall -9 Xvfb wine DataManager.exe || true
rm -f /tmp/.X99-lock || true

# 1. Clear Card Database folder
rm -rf /home/dpavlin/DLA/Card/Database/*
mkdir -p /home/dpavlin/DLA/Card/Database/

# 2. Launch App under XVFB
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!
sleep 2

cd "/home/dpavlin/.wine/drive_c/Program Files/3M Library Systems/Data Manager/Exe"
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!

sleep 10

# 3. Trigger Export using menu (Alt+F, then E)
echo "[*] Triggering Export..."
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key e
sleep 3
# Press Return to accept validation warnings / confirm OK
DISPLAY=:99 xdotool key Return
sleep 5

# Press Return again just in case there is a second dialog
DISPLAY=:99 xdotool key Return
sleep 10

# Capture screenshot to verify success
DISPLAY=:99 ffmpeg -y -f x11grab -video_size 1024x768 -i :99 -vframes 1 /home/dpavlin/.wine/drive_c/screenshot_export_pull_done.png

# Exit
DISPLAY=:99 xdotool key alt+f
sleep 1
DISPLAY=:99 xdotool key x
sleep 4

kill -9 $WINE_PID || true
kill -9 $XVFB_PID || true
killall -9 Xvfb wine DataManager.exe || true

echo "=== Files in Database folder ==="
find /home/dpavlin/DLA/Card/Database -type f
