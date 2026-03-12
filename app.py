"""
app.py — KHIJO Flask server
"""
from flask import Flask, jsonify
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kiosk_engine
from modules.filter import load_data, get_all_dishes

app = Flask(__name__)

@app.route('/')
def index():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'index.html')
    with open(path, 'r') as f:
        return f.read(), 200, {'Content-Type': 'text/html'}

@app.route('/api/session')
def session():
    try:
        sess = kiosk_engine.get_session()
        return jsonify(_enrich(sess))
    except Exception as e:
        print(f"Session error: {e}")
        return jsonify({"status": "waiting", "error": str(e)})

@app.route('/api/session/<uid>')
def session_uid(uid):
    try:
        sess = kiosk_engine.get_session(uid=uid)
        # If not found, try it as a direct users.json key (guest login)
        if sess.get('status') == 'not_found':
            from modules.filter import load_data
            users, _ = load_data()
            if uid in users:
                # Manually build session for guest
                import kiosk_engine as ke
                user = users[uid]
                _, menu = load_data()
                from modules.filter import get_safe_menu, get_all_dishes
                safe_menu = get_safe_menu(user, menu)
                from modules.recommender import get_recommendations, get_last_order
                recs = get_recommendations(user, safe_menu)
                last = get_last_order(user, menu)
                sess = {
                    "status": "ok",
                    "uid": uid,
                    "user": {
                        "name": user["name"],
                        "allergies": user.get("allergies", []),
                        "dietary_preferences": user.get("dietary_preferences", []),
                    },
                    "recommendations": recs,
                    "safe_menu": safe_menu,
                    "safe_count": len(safe_menu),
                    "last_order": last,
                }
        return jsonify(_enrich(sess))
    except Exception as e:
        print(f"Session UID error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)})

def _enrich(sess):
    if sess.get('status') == 'ok':
        _, menu = load_data()
        all_dishes = get_all_dishes(menu)
        for d in all_dishes:
            d.setdefault('image', '')
        for d in sess.get('recommendations', []):
            d.setdefault('image', '')
        for d in sess.get('safe_menu', []):
            d.setdefault('image', '')
        sess['all_menu'] = all_dishes
    return sess

if __name__ == '__main__':
    print("\n🐙 KHIJO server starting at http://localhost:8080\n")
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
