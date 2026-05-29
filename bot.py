import os
import json
from datetime import datetime, timedelta

from flask import Flask, request
from telegram import Bot, Update

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

USERS_FILE = "users.json"

# =========================
# CREATE FILE IF NOT EXISTS
# =========================

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# =========================
# LOAD / SAVE USERS
# =========================

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# CHECK PLAN
# =========================

def has_active_plan(user_id):
    users = load_users()
    user_id = str(user_id)

    if user_id not in users:
        return False

    expiry = users[user_id].get("expiry")
    if not expiry:
        return False

    return datetime.now() < datetime.fromisoformat(expiry)

# =========================
# HOME ROUTE
# =========================

@app.route("/", methods=["GET"])
def home():
    return "BOT RUNNING"

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)

    if not update.message:
        return "OK"

    msg = update.message
    user_id = msg.from_user.id
    text = msg.text or ""

    users = load_users()

    # ================= START =================
    if text == "/start":
        bot.send_message(
            chat_id=user_id,
            text="👋 សួស្តី!\n\nសូមវាយ /buy ដើម្បីមើលគម្រោង និងចាប់ផ្តើមប្រើប្រាស់បូត ❤️"
        )
        return "OK"

    # ================= BUY =================
    if text == "/buy":
        bot.send_message(
            chat_id=user_id,
            text=(
                "💰 គម្រោងរបស់យើង៖\n\n"
                "1️⃣ 3$ / 7 ថ្ងៃ\n"
                "2️⃣ 11.5$ / 30 ថ្ងៃ\n"
                "3️⃣ 120$ / 1 ឆ្នាំ\n\n"
                "📌 សូមស្កេន QR បង់ប្រាក់\n"
                "📸 បន្ទាប់មកផ្ញើ Screenshot មកខ្ញុំ"
            )
        )
        return "OK"

    # ================= PAYMENT SCREENSHOT =================
    if msg.photo:
        photo_id = msg.photo[-1].file_id

        bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 មានការបង់ប្រាក់ថ្មី\n\nUser ID: {user_id}"
        )

        bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id
        )

        bot.send_message(
            chat_id=user_id,
            text="⏳ សូមរង់ចាំ Admin អនុម័តការបង់ប្រាក់ ❤️"
        )
        return "OK"

    # ================= APPROVE =================
    if text.startswith("/approve"):
        if user_id != ADMIN_ID:
            return "OK"

        try:
            parts = text.split()
            target_id = parts[1]
            plan = parts[2]

            now = datetime.now()

            if plan == "week":
                expiry = now + timedelta(days=7)
            elif plan == "month":
                expiry = now + timedelta(days=30)
            elif plan == "year":
                expiry = now + timedelta(days=365)
            else:
                bot.send_message(chat_id=ADMIN_ID, text="❌ Plan មិនត្រឹមត្រូវ")
                return "OK"

            if target_id not in users:
                users[target_id] = {}

            users[target_id]["expiry"] = expiry.isoformat()
            save_users(users)

            bot.send_message(
                chat_id=int(target_id),
                text=(
                    "✅ ការទូទាត់ត្រូវបានអនុម័ត!\n\n"
                    f"📦 Plan: {plan}\n"
                    f"📅 ផុតកំណត់: {expiry.strftime('%Y-%m-%d')}\n\n"
                    "🎉 សូមអរគុណ!"
                )
            )

            bot.send_message(chat_id=ADMIN_ID, text="✅ Approved success")

        except Exception as e:
            bot.send_message(chat_id=ADMIN_ID, text=str(e))

        return "OK"

    # ================= EXPIRED CHECK =================
    if not has_active_plan(user_id):
        bot.send_message(
            chat_id=user_id,
            text=(
                "❌ គម្រោងរបស់អ្នកបានផុតកំណត់\n\n"
                "👉 សូមវាយ /buy ដើម្បីបន្តប្រើប្រាស់"
            )
        )
        return "OK"

    # ================= DEFAULT RESPONSE =================
    bot.send_message(
        chat_id=user_id,
        text="✅ អ្នកអាចប្រើបូតបានហើយ!"
    )

    return "OK"

# =========================
# START SERVER
# =========================

if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
