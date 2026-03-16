"""
kiosk_engine.py — Central brain of the KHIJO kiosk.
- RFID scanning in background thread
- Ultrasonic sensor detects person approaching
- Audio via espeak + aplay (default device)
"""
import json, os, sys, threading, time
sys.path.insert(0, os.path.dirname(__file__))
from modules.filter import load_data, filter_menu
from modules.recommender import get_recommendations, get_surprise, get_healthy_options, get_last_order

SIMULATION = False  # True = Mac dev, False = Pi

# ── Shared state ──
_last_uid = None
_uid_lock = threading.Lock()
_person_present = False
_audio_played = False  # tracks if we already played audio for this person

# ── Audio helpers ──
def speak_async(text):
    threading.Thread(
        target=lambda: os.system(f'espeak "{text}" --stdout | aplay - 2>/dev/null'),
        daemon=True
    ).start()

def play_ding():
    threading.Thread(
        target=lambda: os.system(
            'python3 -c "'
            'import math,wave,struct; sr=44100; dur=0.5; freq=880;'
            'frames=b\"\".join(struct.pack(\"<h\",int(28000*math.sin(2*math.pi*freq*i/sr)*max(0,1-i/(sr*dur*0.7)))) for i in range(int(sr*dur)));'
            'f=open(\"/tmp/ding.wav\",\"wb\");'
            'import wave as wv; w=wv.open(f); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(frames); w.close()'
            '" && aplay /tmp/ding.wav 2>/dev/null'
        ),
        daemon=True
    ).start()

def stop_audio():
    os.system('pkill -f "espeak" 2>/dev/null; pkill -f "aplay" 2>/dev/null')

# ── Ultrasonic sensor loop ──
def _ultrasonic_loop():
    global _person_present, _audio_played
    try:
        import RPi.GPIO as GPIO
        TRIG = 23
        ECHO = 24
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)
        print("Ultrasonic sensor started...")

        consecutive_near = 0
        consecutive_far = 0
        THRESHOLD = 35  # cm
        CONFIRM = 3     # consecutive readings needed

        while True:
            try:
                GPIO.output(TRIG, False)
                time.sleep(0.1)
                GPIO.output(TRIG, True)
                time.sleep(0.00001)
                GPIO.output(TRIG, False)

                start = time.time()
                timeout = start + 0.1
                while GPIO.input(ECHO) == 0 and time.time() < timeout:
                    start = time.time()
                while GPIO.input(ECHO) == 1 and time.time() < timeout:
                    end = time.time()

                try:
                    distance = round((end - start) * 17150, 1)
                    if distance > 1000:
                        time.sleep(0.5)
                        continue

                    if distance < THRESHOLD:
                        consecutive_near += 1
                        consecutive_far = 0
                    else:
                        consecutive_far += 1
                        consecutive_near = 0

                    # Person arrived - play audio ONCE
                    if consecutive_near >= CONFIRM and not _person_present:
                        _person_present = True
                        _audio_played = False
                        print(f"Person confirmed at {distance}cm")

                    if _person_present and not _audio_played:
                        _audio_played = True
                        speak_async("Tap your SafeBite card")

                    # Person left - reset everything
                    if consecutive_far >= CONFIRM and _person_present:
                        _person_present = False
                        _audio_played = False
                        consecutive_near = 0
                        print("Person left")

                except:
                    pass

                time.sleep(0.5)
            except Exception as e:
                print(f"Ultrasonic error: {e}")
                time.sleep(1)
    except Exception as e:
        print(f"Ultrasonic init error: {e}")

# ── RFID background thread ──
def _rfid_loop():
    global _last_uid, _person_present, _audio_played
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
                stop_audio()
                _person_present = False
                _audio_played = False
                play_ding()
                time.sleep(2)
                with _uid_lock:
                    _last_uid = None
            except Exception as e:
                print(f"RFID read error: {e}")
                time.sleep(1)
    except Exception as e:
        print(f"RFID init error: {e}")

def start_rfid_thread():
    if not SIMULATION:
        threading.Thread(target=_rfid_loop, daemon=True).start()
        threading.Thread(target=_ultrasonic_loop, daemon=True).start()

def get_pending_uid():
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

    name = user.get('name', '').split()[0]
    speak_async(f"Hi {name}, let me filter the menu for you")

    safe_dishes, removed_dishes = filter_menu(user, menu)
    recs = [dish for dish, score in get_recommendations(user, menu, top_n=3)]
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
