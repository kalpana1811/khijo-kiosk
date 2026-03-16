"""
kiosk_engine.py — Central brain of the KHIJO kiosk.
- RFID scanning in background thread
- Ultrasonic sensor detects person approaching
- Audio via espeak + aplay (default device)
"""
import json, os, sys, threading, time, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from modules.filter import load_data, filter_menu
from modules.recommender import get_recommendations, get_surprise, get_healthy_options, get_last_order

SIMULATION = False  # True = Mac dev, False = Pi

# ── Shared state ──
_last_uid = None
_uid_lock = threading.Lock()
_welcome_speaking = False
_person_present = False

# ── Audio helpers ──
def speak(text):
    os.system(f'espeak "{text}" --stdout | aplay - 2>/dev/null')

def speak_async(text):
    threading.Thread(
        target=lambda: os.system(f'espeak "{text}" --stdout | aplay - 2>/dev/null'),
        daemon=True
    ).start()

def play_ding():
    threading.Thread(
        target=lambda: os.system(
            'python3 -c "'
            'import math,wave,struct,os; sr=44100; dur=0.5; freq=880;'
            'frames=b\"\".join(struct.pack(\"<h\",int(28000*math.sin(2*math.pi*freq*i/sr)*max(0,1-i/(sr*dur*0.7)))) for i in range(int(sr*dur)));'
            'f=open(\"/tmp/ding.wav\",\"wb\");'
            'import wave as wv; w=wv.open(f); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(frames); w.close()'
            '" && aplay /tmp/ding.wav 2>/dev/null'
        ),
        daemon=True
    ).start()

def stop_audio():
    os.system('pkill -f "espeak" 2>/dev/null; pkill -f "aplay" 2>/dev/null')

# ── Welcome audio loop ──
def welcome_loop():
    global _welcome_speaking
    while _welcome_speaking:
        os.system('espeak "Tap your SafeBite card" --stdout | aplay - 2>/dev/null')
        time.sleep(4)

def start_welcome_audio():
    global _welcome_speaking
    if _welcome_speaking:
        return
    _welcome_speaking = True
    threading.Thread(target=welcome_loop, daemon=True).start()

def stop_welcome_audio():
    global _welcome_speaking
    _welcome_speaking = False
    stop_audio()

# ── Ultrasonic sensor loop ──
def _ultrasonic_loop():
    global _person_present
    try:
        import RPi.GPIO as GPIO
        TRIG = 23
        ECHO = 24
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)
        print("Ultrasonic sensor started...")
        
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
                    if distance < 100 and not _person_present:
                        _person_present = True
                        print(f"Person detected at {distance}cm — starting welcome audio")
                        start_welcome_audio()
                    elif distance >= 100 and _person_present:
                        _person_present = False
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
                stop_welcome_audio()
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
