import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)
USERS_FILE = "users.json"

# ======================
# INIT FILE
# ======================
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# ======================
# HELPERS
# ======================
def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def send_message(chat_id, text):
    requests.post(API_URL + "/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_photo(chat_id, photo, caption=None):
    requests.post(API_URL + "/sendPhoto", data={
        "chat_id": chat_id,
        "caption": caption
    }, files={
        "photo": photo
    })

# ======================
# PLAN CHECK
# ======================
def has_active_plan(user_id):
    users = load_users()
    user_id = str(user_id)

    if user_id not in users:
        return False

    expiry = users[user_id].get("expiry")
    if not expiry:
        return False

    return datetime.now() < datetime.fromisoformat(expiry)

# ======================
# HOME
# ======================
@app.route("/", methods=["GET"])
def home():
    return "BOT RUNNING"

# ======================
# WEBHOOK
# ======================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "OK"

    msg = data["message"]

    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    chat_id = msg["chat"]["id"]

    users = load_users()

    # ======================
    # START
    # ======================
    if text == "/start":
        send_message(chat_id, """🇰🇭 សួស្តី!

សូមវាយ:
/buy ដើម្បីបើកគម្រោង

សូមអរគុណ ❤️""")
        return "OK"

    # ======================
    # BUY
    # ======================
    if text == "/buy":
        with open("qr.png", "rb") as f:
            send_photo(chat_id, f, """💳 គម្រោង

1. 3$ / សប្តាហ៍
2. 11.5$ / ខែ
3. 120$ / ឆ្នាំ

ផ្ញើ Screenshot មក Admin ❤️""")
        return "OK"

    # ======================
    # PAYMENT PROOF
    # ======================
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        send_message(ADMIN_ID, f"""💰 PAYMENT PROOF

USER: {user_id}
NAME: {msg['from'].get('first_name','')}""")

        requests.post(API_URL + "/forwardMessage", data={
            "chat_id": ADMIN_ID,
            "from_chat_id": chat_id,
            "message_id": msg["message_id"]
        })

        send_message(chat_id, "⏳ សូមរង់ចាំ Admin អនុម័ត")
        return "OK"

    # ======================
    # APPROVE (ADMIN ONLY)
    # ======================
    if text.startswith("/approve"):
        if user_id != ADMIN_ID:
            return "OK"

        try:
            _, target_id, plan = text.split()

            now = datetime.now()

            if plan == "week":
                expiry = now + timedelta(days=7)
            elif plan == "month":
                expiry = now + timedelta(days=30)
            elif plan == "year":
                expiry = now + timedelta(days=365)
            else:
                send_message(ADMIN_ID, "Plan មិនត្រឹមត្រូវ")
                return "OK"

            users[target_id] = {
                "expiry": expiry.isoformat()
            }

            save_users(users)

            send_message(int(target_id), f"""✅ APPROVED

PLAN: {plan}
EXPIRY: {expiry.strftime('%Y-%m-%d')}""")

            send_message(ADMIN_ID, "APPROVED DONE ✅")

        except Exception as e:
            send_message(ADMIN_ID, str(e))

        return "OK"

    # ======================
    # GROUP LINK
    # ======================
    if text.startswith("-100"):
        if not has_active_plan(user_id):
            send_message(chat_id, "❌ Plan ផុតកំណត់ សូម /buy")
            return "OK"

        users[str(user_id)] = users.get(str(user_id), {})
        users[str(user_id)]["group_id"] = int(text)
        save_users(users)

        send_message(chat_id, "✅ Group Connected")
        return "OK"

    # ======================
    # FORWARD MESSAGE
    # ======================
    if has_active_plan(user_id):
        user_data = users.get(str(user_id), {})
        group_id = user_data.get("group_id")

        if group_id:
            send_message(group_id, text)

    else:
        send_message(chat_id, "❌ Plan ផុតកំណត់ /buy")

    return "OK"

# ======================
# RUN
# ======================
if __name__ == "__main__":
    if WEBHOOK_URL:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
