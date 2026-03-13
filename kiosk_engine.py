"""
kiosk_engine.py — Central brain of the KHIJO kiosk.
RFID scanning runs in a background thread so Flask never blocks.
"""

import json, os, sys, threading, time
sys.path.insert(0, os.path.dirname(__file__))

from modules.filter import load_data, filter_menu
from modules.recommender import get_recommendations, get_surprise, get_healthy_options, get_last_order

SIMULATION = False  # True = Mac dev (guest button), False = Pi with real RC522

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
                with _uid_lock:
                    _last_uid = str(uid)
                print(f"Card tapped: {uid}")
                time.sleep(2)  # debounce — ignore re-taps for 2 seconds
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
