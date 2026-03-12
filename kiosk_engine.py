"""
kiosk_engine.py
───────────────
Central brain of the kiosk. Connects RFID → user lookup → filter → recommend.
The UI imports this file and calls get_session(uid) to get everything it needs.

Two modes:
  SIMULATION = True  → no hardware needed (laptop dev)
  SIMULATION = False → reads real RC522 RFID reader (Raspberry Pi)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from modules.filter import load_data, filter_menu
from modules.recommender import (
    get_recommendations,
    get_surprise,
    get_healthy_options,
    get_last_order,
)

# ── Set this to False when running on Raspberry Pi with real RC522 ──
SIMULATION = True


# ════════════════════════════════════════════════════════
#  RFID SCANNING
# ════════════════════════════════════════════════════════

def scan_card():
    """
    Waits for an RFID card tap and returns the UID as a string.
    Simulation mode returns a hardcoded UID for testing.
    """
    if SIMULATION:
        return "1047571399431"
    else:
        try:
            from mfrc522 import SimpleMFRC522
            reader = SimpleMFRC522()
            print("Waiting for card tap...")
            uid, _ = reader.read()
            return str(uid)
        except Exception as e:
            print(f"RFID error: {e}")
            return None


# ════════════════════════════════════════════════════════
#  USER LOOKUP
# ════════════════════════════════════════════════════════

def lookup_user(uid, users):
    """Returns the user dict if UID exists, else None."""
    return users.get(str(uid), None)


# ════════════════════════════════════════════════════════
#  MAIN SESSION BUILDER
# ════════════════════════════════════════════════════════

def get_session(uid=None):
    """
    Full pipeline: UID → user → filter → recommend → return session dict.

    Returns:
    {
        "status":          "ok" | "not_found" | "error",
        "uid":             "1047571399431",
        "user":            { name, age, allergies, avoid, dietary_preferences, order_history },
        "safe_count":      20,
        "removed_count":   70,
        "recommendations": [ dish, ... ],   # top 5
        "safe_menu":       [ dish, ... ],   # all safe dishes
        "surprise":        dish or None,
        "healthy":         [ dish, ... ],   # top 3
        "last_order":      dish or None,
    }
    """
    users, menu = load_data()

    # Step 1 — get UID
    if uid is None:
        uid = scan_card()

    if uid is None:
        return {"status": "error", "message": "RFID read failed"}

    uid = str(uid)

    # Step 2 — look up user
    user = lookup_user(uid, users)
    if user is None:
        return {
            "status":  "not_found",
            "uid":     uid,
            "message": f"Card {uid} not registered in system"
        }

    # Step 3 — filter menu
    safe_dishes, removed_dishes = filter_menu(user, menu)

    # Step 4 — recommendations
    recs         = get_recommendations(user, menu, top_n=5)
    recs         = [dish for dish, score in recs]
    surprise     = get_surprise(user, menu)
    healthy      = get_healthy_options(user, menu, top_n=3)
    last_order   = get_last_order(user, menu)

    # Step 5 — return full session
    return {
        "status":          "ok",
        "uid":             uid,
        "user":            user,
        "safe_count":      len(safe_dishes),
        "removed_count":   len(removed_dishes),
        "recommendations": recs,
        "safe_menu":       safe_dishes,
        "surprise":        surprise,
        "healthy":         healthy,
        "last_order":      last_order,
    }


# ════════════════════════════════════════════════════════
#  CATEGORY HELPER
# ════════════════════════════════════════════════════════

def group_by_category(safe_menu):
    """Groups flat list of safe dishes by category for the UI."""
    grouped = {}
    for dish in safe_menu:
        cat = dish["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(dish)
    return grouped


# ════════════════════════════════════════════════════════
#  QUICK TEST
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  KIOSK ENGINE TEST")
    print("=" * 50)

    session = get_session()

    if session["status"] == "ok":
        user = session["user"]
        print(f"\n✅ Card recognised!")
        print(f"   Name      : {user['name']}")
        print(f"   Age       : {user['age']}")
        print(f"   Allergies : {user['allergies'] or 'none'}")
        print(f"   Avoid     : {user['avoid'] or 'none'}")
        print(f"   Prefs     : {user['dietary_preferences']}")
        print(f"\n   Safe dishes   : {session['safe_count']}")
        print(f"   Removed dishes: {session['removed_count']}")
        print(f"\n🍽  Top Recommendations:")
        for dish in session["recommendations"]:
            print(f"   - {dish['name']}  £{dish['price']}")
        print(f"\n🎲  Surprise    : {session['surprise']['name'] if session['surprise'] else 'none'}")
        print(f"🔁  Last order  : {session['last_order']['name'] if session['last_order'] else 'none'}")
        print(f"🥗  Healthy     : {[d['name'] for d in session['healthy']]}")
        print(f"\n📋  Safe menu by category:")
        grouped = group_by_category(session["safe_menu"])
        for cat, dishes in grouped.items():
            print(f"   {cat} ({len(dishes)} dishes)")

    elif session["status"] == "not_found":
        print(f"\n❌ Card not recognised: {session['uid']}")
        print("   Register this card in users.json first.")
    else:
        print(f"\n⚠️  Error: {session.get('message')}")
