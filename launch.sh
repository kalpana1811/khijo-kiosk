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
  http://localhost:8080
