"""
led_controller.py — Runs with sudo, watches /tmp/led_cmd for color commands.
Run with: sudo python3 led_controller.py
"""
import time, os
from rpi_ws281x import PixelStrip, Color

strip = PixelStrip(8, 18, 800000, 10, False, 255, 0)
strip.begin()

COLORS = {
    'yellow': Color(255, 100, 0),
    'green':  Color(0, 255, 0),
    'red':    Color(255, 0, 0),
    'off':    Color(0, 0, 0),
}

def set_color(name):
    c = COLORS.get(name, COLORS['off'])
    for i in range(8):
        strip.setPixelColor(i, c)
    strip.show()

CMD_FILE = '/tmp/led_cmd'

# Start yellow
set_color('yellow')
last_cmd = 'yellow'

print("LED controller started - watching /tmp/led_cmd")
while True:
    try:
        if os.path.exists(CMD_FILE):
            with open(CMD_FILE) as f:
                cmd = f.read().strip()
            if cmd != last_cmd:
                set_color(cmd)
                last_cmd = cmd
                print(f"LED -> {cmd}")
    except Exception as e:
        print(f"LED error: {e}")
    time.sleep(0.2)
