#!/bin/bash
# KHIJO Kiosk Launcher
# Starts Flask server + opens Chromium in kiosk mode

cd "$(dirname "$0")"

# Kill any existing server
pkill -f "python3 app.py" 2>/dev/null
sleep 0.5

# Start server in background
python3 app.py &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to be ready
sleep 2

# Open in Chromium kiosk mode (Pi)
# chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:5000

# On Mac, open in default browser:
open http://localhost:5000

wait $SERVER_PID
