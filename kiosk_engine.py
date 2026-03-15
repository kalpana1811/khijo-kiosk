"""
kiosk_engine.py — Central brain of the KHIJO kiosk.
RFID scanning runs in a background thread so Flask never blocks.
"""

import json, os, sys, threading, time
sys.path.insert(0, os.path.dirname(__file__))

from modules.filter import load_data, filter_menu
from modules.recommender import get_recommendations, get_surprise, get_healthy_options, get_last_order

SIMULATION = True  # True = Mac dev (guest button), False = Pi with real RC522

# ── Audio beeps (Pi built-in audio — no external hardware needed) ─────────────
# Uses pygame + numpy to generate pure sine tones on the fly.
# Output: Pi 3.5mm jack  OR  HDMI (if screen has audio).
#
# One-time Pi setup (if not already done):
#   sudo apt install python3-pygame -y
#   sudo raspi-config → Advanced Options → Audio → Force 3.5mm  (or Force HDMI)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import pygame
    import numpy as np
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    def _make_tone(freq=880, duration=0.15, volume=0.45):
        """Generate a short sine-wave tone as a pygame Sound object."""
        sr  = 44100
        t   = np.linspace(0, duration, int(sr * duration), False)
        env = np.exp(-t * 8)                          # fast fade-out — no click
        wav = (np.sin(2 * np.pi * freq * t) * env * volume * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([wav, wav]))

    # Pre-build all tones once at import time
    _BEEP_OK    = _make_tone(880, 0.12)   # ✅ high ping  — valid card
    _BEEP_FAIL  = _make_tone(220, 0.35)   # ❌ low buzz   — unknown card
    _BEEP_ORDER = [                        # 🛎️ 3-note chime — order placed
        _make_tone(523, 0.10),
        _make_tone(659, 0.10),
        _make_tone(784, 0.20),
    ]

    def beep_ok():
        try: _BEEP_OK.play()
        except: pass

    def beep_fail():
        try: _BEEP_FAIL.play()
        except: pass

    def beep_order():
        def _seq():
            for i, s in enumerate(_BEEP_ORDER):
                time.sleep(i * 0.13)
                try: s.play()
                except: pass
        threading.Thread(target=_seq, daemon=True).start()

    print("[Audio] ✓ pygame ready — beeps enabled")

except Exception as _e:
    print(f"[Audio] disabled ({_e})  →  sudo apt install python3-pygame && pip install numpy")
    def beep_ok():    pass
    def beep_fail():  pass
    def beep_order(): pass

# ── Shared state from background RFID thread ──
_last_uid = None
_uid_lock = threading.Lock()

def _rfid_loop():
    """Background thread: continuously scans for cards and stores the UID."""
    global _last_uid
    try:
        from mfrc522 import SimpleMFRC522
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        reader = SimpleMFRC522()
        print("RFID background thread started — waiting for card taps...")
        while True:
            try:
                uid, _ = reader.read()
                uid_str = str(uid)
                # Check if this card is registered before storing
                users, _ = load_data()
                if uid_str in users:
                    beep_ok()           # ✅ known card — high ping
                    print(f"[RFID] ✓ card tapped: {uid_str} ({users[uid_str]['name']})")
                else:
                    beep_fail()         # ❌ unknown card — low buzz
                    print(f"[RFID] ✗ unknown card: {uid_str}")
                with _uid_lock:
                    _last_uid = uid_str
                time.sleep(2)           # debounce — ignore re-taps for 2 seconds
                with _uid_lock:
                    _last_uid = None
            except Exception as e:
                print(f"RFID read error: {e}")
                time.sleep(1)
    except Exception as e:
        print(f"RFID init error: {e}")

def start_rfid_thread():
    """Call once at startup to begin background RFID scanning."""
    if not SIMULATION:
        t = threading.Thread(target=_rfid_loop, daemon=True)
        t.start()

def get_pending_uid():
    """Returns UID if a card was just tapped, else None."""
    with _uid_lock:
        return _last_uid

def lookup_user(uid, users):
    return users.get(str(uid), None)

def get_session(uid=None):
    users, menu = load_data()

    if uid is None:
        uid = get_pending_uid()

    if uid is None:
        return {"status": "waiting"}

    uid = str(uid)
    user = lookup_user(uid, users)
    if user is None:
        return {"status": "not_found", "uid": uid, "message": f"Card {uid} not registered"}

    safe_dishes, removed_dishes = filter_menu(user, menu)
    recs = [dish for dish, score in get_recommendations(user, menu, top_n=5)]
    last_order = get_last_order(user, menu)

    return {
        "status":          "ok",
        "uid":             uid,
        "user":            user,
        "safe_count":      len(safe_dishes),
        "removed_count":   len(removed_dishes),
        "recommendations": recs,
        "safe_menu":       safe_dishes,
        "last_order":      last_order,
    }

def group_by_category(safe_menu):
    grouped = {}
    for dish in safe_menu:
        cat = dish["category"]
        grouped.setdefault(cat, []).append(dish)
    return grouped
