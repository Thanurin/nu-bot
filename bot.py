import os
import json
import requests
from datetime import datetime
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
    if not data:
        return "OK"

    if "message" not in data:
        return "OK"

    msg = data["message"]

    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    chat_type = msg["chat"]["type"]

    users = load_users()

    # ======================
    # START
    # ======================
    if text == "/start":
        send_message(chat_id, "🇰🇭 សួស្តី!\n\n👉 វាយ /buy ដើម្បីចាប់ផ្តើម")
        return "OK"

    # ======================
    # BUY
    # ======================
    if text == "/buy":
        with open("qr.png", "rb") as f:
            requests.post(API + "/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption":
                        "💳 គម្រោង:\n\n"
                        "1. 3$ / week\n"
                        "2. 11.5$ / month\n"
                        "3. 120$ / year\n\n"
                        "ផ្ញើ Screenshot មក Admin ❤️"
                },
                files={"photo": f}
            )
        return "OK"

    # ======================
    # GROUP CONNECT
    # ======================
    if text == "/connect" and chat_type in ["group", "supergroup"]:

        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "✅ Connect This Group",
                    "callback_data": f"connect:{chat_id}"
                }
            ]]
        }

        send_message(chat_id,
            "🤖 Bot detected this group\nចុចប៊ូតុងខាងក្រោមដើម្បីភ្ជាប់ 👇",
            reply_markup=keyboard
        )
        return "OK"

    # ======================
    # CALLBACK
    # ======================
    if "callback_query" in data:
        cq = data["callback_query"]
        user_id_cb = cq["from"]["id"]
        cb_data = cq["data"]

        if cb_data.startswith("connect:"):
            group_id = int(cb_data.split(":")[1])

            users[str(user_id_cb)] = users.get(str(user_id_cb), {})
            users[str(user_id_cb)]["group_id"] = group_id
            save_users(users)

            send_message(user_id_cb, "✅ Group Connected Successfully!")

        return "OK"

    # ======================
    # PLAN CHECK
    # ======================
    if not has_active_plan(user_id):
        send_message(chat_id, "❌ Plan expired /buy")
        return "OK"

    # ======================
    # GET GROUP
    # ======================
    user_data = users.get(str(user_id), {})
    group_id = user_data.get("group_id")

    if not group_id:
        return "OK"

    # ======================
    # FORWARD SYSTEM + ADMIN NOTIFY FIXED
    # ======================

    # TEXT
    if text:
        send_message(group_id, text)

        # ADMIN NOTIFY
        send_message(ADMIN_ID, f"💬 Text Message\nUser: {user_id}\nText: {text}")

    # PHOTO
    elif "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        requests.post(API + "/sendPhoto", json={
            "chat_id": group_id,
            "photo": file_id
        })

        send_message(ADMIN_ID, f"🖼 Photo Received\nUser: {user_id}")

    # VIDEO
    elif "video" in msg:
        file_id = msg["video"]["file_id"]

        requests.post(API + "/sendVideo", json={
            "chat_id": group_id,
            "video": file_id
        })

        send_message(ADMIN_ID, f"🎥 Video Received\nUser: {user_id}")

    # DOCUMENT
    elif "document" in msg:
        file_id = msg["document"]["file_id"]

        requests.post(API + "/sendDocument", json={
            "chat_id": group_id,
            "document": file_id
        })

        send_message(ADMIN_ID, f"📄 Document Received\nUser: {user_id}")

    return "OK"


# ======================
# RUN
# ======================
if __name__ == "__main__":
    if WEBHOOK_URL:
        requests.get(f"{API}/setWebhook?url={WEBHOOK_URL}/webhook")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
