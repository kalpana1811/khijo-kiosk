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
        if sess.get('status') == 'ok':
            return jsonify(_enrich(sess))
        return jsonify(sess)
    except Exception as e:
        print(f"Session error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"status": "waiting"})

@app.route('/api/session/<uid>')
def session_uid(uid):
    try:
        sess = kiosk_engine.get_session(uid=uid)
        if sess.get('status') == 'ok':
            return jsonify(_enrich(sess))
        return jsonify(sess)
    except Exception as e:
        print(f"Session UID error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/endsession', methods=['GET', 'POST'])
def end_session():
    try:
        kiosk_engine.end_session()
    except Exception as e:
        print(f"End session error: {e}")
    return jsonify({"status": "ok"})

@app.route('/api/nextcustomer', methods=['GET', 'POST'])
def next_customer():
    try:
        kiosk_engine.play_next_ting()
    except Exception as e:
        print(f"Next ting error: {e}")
    return jsonify({"status": "ok"})

@app.route('/api/order', methods=['GET', 'POST'])
def order_placed():
    try:
        kiosk_engine.play_order_beep()
    except Exception as e:
        print(f"Order beep error: {e}")
    return jsonify({"status": "ok"})

def _enrich(sess):
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
    print("\n🐙 KHIJO server starting at http://localhost:5001\n")
    kiosk_engine.start_rfid_thread()
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
