#!/bin/bash
cd "$(dirname "$0")"
pkill -f "python3 app.py" 2>/dev/null
sleep 0.3
pip3 install flask --quiet
python3 app.py &
sleep 1.5
open http://localhost:5000
wait
