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


def send_photo(chat_id, file_id, caption=None, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "photo": file_id,
    }
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    requests.post(API + "/sendPhoto", json=payload)


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

    users = load_users()

    # ======================
    # CALLBACK (ADMIN APPROVE BUTTON)
    # ======================
    if "callback_query" in data:
        cq = data["callback_query"]
        admin_action = cq["data"]

        if admin_action.startswith("approve:"):
            _, user_id, plan = admin_action.split(":")

            now = datetime.now()

            if plan == "week":
                expiry = now + timedelta(days=7)
            elif plan == "month":
                expiry = now + timedelta(days=30)
            elif plan == "year":
                expiry = now + timedelta(days=365)
            else:
                send_message(ADMIN_ID, "❌ Invalid plan")
                return "OK"

            users[str(user_id)] = {
                "expiry": expiry.isoformat()
            }
            save_users(users)

            send_message(user_id, f"✅ Approved!\nPlan: {plan}\nExpire: {expiry.date()}")
            send_message(ADMIN_ID, "✅ User approved successfully")

        return "OK"

    # ======================
    # MESSAGE
    # ======================
    if "message" not in data:
        return "OK"

    msg = data["message"]

    user_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    chat_type = msg["chat"]["type"]

    # ======================
    # START
    # ======================
    if text == "/start":
        send_message(chat_id, "🇰🇭 សួស្តី!\n👉 វាយ /buy ដើម្បីទិញ plan")
        return "OK"

    # ======================
    # BUY (SEND QR)
    # ======================
    if text == "/buy":
        with open("qr.png", "rb") as f:
            requests.post(API + "/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption":
                        "💳 Plans:\n"
                        "1. 3$ / week\n"
                        "2. 11.5$ / month\n"
                        "3. 120$ / year\n\n"
                        "📸 Send payment screenshot after paying"
                },
                files={"photo": f}
            )
        return "OK"

    # ======================
    # 📸 PAYMENT SCREENSHOT → ADMIN NOTIFY + APPROVE BUTTON
    # ======================
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Approve Week",
                        "callback_data": f"approve:{user_id}:week"
                    },
                    {
                        "text": "💳 Month",
                        "callback_data": f"approve:{user_id}:month"
                    }
                ],
                [
                    {
                        "text": "🏆 Year",
                        "callback_data": f"approve:{user_id}:year"
                    }
                ]
            ]
        }

        send_message(
            ADMIN_ID,
            f"💰 New Payment Screenshot\nUser ID: {user_id}",
            reply_markup=keyboard
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
                    "callback_data": f"group:{chat_id}"
                }
            ]]
        }

        send_message(chat_id, "👥 Connect this group?", reply_markup=keyboard)
        return "OK"

    # ======================
    # CALLBACK (GROUP SAVE)
    # ======================
    if "callback_query" in data:
        cq = data["callback_query"]
        user_id_cb = cq["from"]["id"]
        cb_data = cq["data"]

        if cb_data.startswith("group:"):
            group_id = int(cb_data.split(":")[1])

            users[str(user_id_cb)] = users.get(str(user_id_cb), {})
            users[str(user_id_cb)]["group_id"] = group_id
            save_users(users)

            send_message(user_id_cb, "✅ Group Connected Successfully!")

        return "OK"

    # ======================
    # FORWARD SYSTEM
    # ======================
    if not has_active_plan(user_id):
        send_message(chat_id, "❌ Plan expired /buy")
        return "OK"

    user_data = users.get(str(user_id), {})
    group_id = user_data.get("group_id")

    if not group_id:
        return "OK"

    if text:
        send_message(group_id, text)

    elif "photo" in msg:
        send_photo(group_id, msg["photo"][-1]["file_id"])

    elif "video" in msg:
        requests.post(API + "/sendVideo", json={
            "chat_id": group_id,
            "video": msg["video"]["file_id"]
        })

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
