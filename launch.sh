#!/bin/bash
pkill -f "python3 app.py"
pkill -f "led_controller"
pkill chromium
pkill onboard
sleep 1
cd ~/khijo-kiosk

# Start LED controller with sudo
sudo python3 led_controller.py &
sleep 1

# Start Flask server
python3 app.py &
sleep 3

# Start Chromium kiosk
DISPLAY=:0 chromium-browser \
  --kiosk \
  --touch-events=enabled \
  --enable-virtual-keyboard \
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
