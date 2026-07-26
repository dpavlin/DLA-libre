#!/usr/bin/env bash
set -x

killall -9 Xvfb wine DataManager.exe || true
rm -f /tmp/.X99-lock || true

# Launch App under XVFB
Xvfb :99 -screen 0 1024x768x24 &
XVFB_PID=$!
sleep 2

cd "/home/dpavlin/.wine/drive_c/Program Files/3M Library Systems/Data Manager/Exe"
WINEPREFIX=/home/dpavlin/.wine DISPLAY=:99 wine DataManager.exe &
WINE_PID=$!

sleep 12

# Take screenshot to see if Pull Lists is green and pull1.tab is listed!
DISPLAY=:99 ffmpeg -y -f x11grab -video_size 1024x768 -i :99 -vframes 1 /home/dpavlin/.wine/drive_c/screenshot_pull_lists.png

kill -9 $WINE_PID || true
kill -9 $XVFB_PID || true
killall -9 Xvfb wine DataManager.exe || true
