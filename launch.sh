#!/bin/bash
pkill -f "python3 app.py"
pkill chromium
sleep 1
cd ~/khijo-kiosk
python3 app.py &
sleep 3
DISPLAY=:0 chromium-browser \
  --kiosk \
  --touch-events=enabled \
  --enable-smooth-scrolling \
  --disable-pinch \
  --noerrdialogs \
  --disable-infobars \
  --disable-translate \
  --no-first-run \
  --disable-features=TranslateUI \
  --overscroll-history-navigation=0 \
  --disable-touch-adjustment \
  --enable-viewport \
  --touch-devices=1 \
  --simulate-outdated-no-au='Tue, 31 Dec 2099 23:59:59 GMT' \
  http://localhost:5001
