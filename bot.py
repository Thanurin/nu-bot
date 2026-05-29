import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

API = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)
USERS_FILE = "users.json"


# ======================
# DB
# ======================
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ======================
# SEND MESSAGE
# ======================
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    requests.post(API + "/sendMessage", json=payload)


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

    # ----------------------
    # CALLBACK HANDLER FIRST
    # ----------------------
    if "callback_query" in data:
        cq = data["callback_query"]
        user_id = cq["from"]["id"]
        data_cb = cq["data"]

        if data_cb.startswith("connect_group:"):
            group_id = int(data_cb.split(":")[1])

            users = load_users()
            users[str(user_id)] = users.get(str(user_id), {})
            users[str(user_id)]["group_id"] = group_id
            save_users(users)

            send_message(user_id, "✅ Group Connected Successfully!")
        return "OK"

    if "message" not in data:
        return "OK"

    msg = data["message"]

    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    users = load_users()
    user_key = str(user_id)

    # ======================
    # START
    # ======================
    if text == "/start":
        send_message(chat_id,
            "🇰🇭 សួស្តី!\n\n👉 វាយ /buy ដើម្បីចាប់ផ្តើម")
        return "OK"

    # ======================
    # BUY
    # ======================
    if text == "/buy":
        send_message(chat_id,
            "💳 គម្រោង:\n\n"
            "1. 3$ / week\n"
            "2. 11.5$ / month\n"
            "3. 120$ / year\n\n"
            "ផ្ញើ screenshot មក admin ❤️"
        )
        return "OK"

    # ======================
    # AUTO DETECT GROUP (NO -100 INPUT)
    # ======================
    if msg["chat"]["type"] in ["group", "supergroup"]:

        group_id = chat_id

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Connect This Group",
                        "callback_data": f"connect_group:{group_id}"
                    }
                ]
            ]
        }

        send_message(
            chat_id,
            "🤖 Bot detected this group\n\nចុចប៊ូតុងខាងក្រោមដើម្បីភ្ជាប់ group 👇",
            reply_markup=keyboard
        )

        return "OK"

    # ======================
    # FORWARD SYSTEM
    # ======================
    if not has_active_plan(user_id):
        send_message(chat_id, "❌ Plan expired /buy")
        return "OK"

    user_data = users.get(user_key, {})
    group_id = user_data.get("group_id")

    if not group_id:
        return "OK"

    # TEXT
    if text:
        send_message(group_id, text)

    # PHOTO
    elif "photo" in msg:
        requests.post(API + "/sendPhoto", json={
            "chat_id": group_id,
            "photo": msg["photo"][-1]["file_id"]
        })

    # VIDEO
    elif "video" in msg:
        requests.post(API + "/sendVideo", json={
            "chat_id": group_id,
            "video": msg["video"]["file_id"]
        })

    # DOCUMENT
    elif "document" in msg:
        requests.post(API + "/sendDocument", json={
            "chat_id": group_id,
            "document": msg["document"]["file_id"]
        })

    return "OK"


# ======================
# RUN
# ======================
if __name__ == "__main__":
    if WEBHOOK_URL:
        requests.get(f"{API}/setWebhook?url={WEBHOOK_URL}/webhook")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
