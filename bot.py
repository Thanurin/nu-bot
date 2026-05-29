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
# INIT USERS FILE
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

    expiry_date = datetime.fromisoformat(expiry)
    return datetime.now() < expiry_date

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

    # =========================
    # START COMMAND
    # =========================

    if text == "/start":
        bot.send_message(
            chat_id=user_id,
            text="សួស្តី! 👋\nវាយ /buy ដើម្បីទិញគម្រោង"
        )
        return "OK"

    # =========================
    # BUY COMMAND
    # =========================

    if text == "/buy":
        bot.send_message(
            chat_id=user_id,
            text=(
                "📦 Plans:\n"
                "1. 3$/week\n"
                "2. 11.5$/month\n"
                "3. 120$/year\n\n"
                "📸 Send payment screenshot after payment."
            )
        )
        return "OK"

    # =========================
    # PAYMENT SCREENSHOT
    # =========================

    if msg.photo:
        bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 NEW PAYMENT PROOF\nUSER ID: {user_id}\nNAME: {msg.from_user.first_name}"
        )

        bot.send_message(
            chat_id=user_id,
            text="⏳ Please wait for admin approval..."
        )
        return "OK"

    # =========================
    # ADMIN APPROVE
    # =========================

    if text.startswith("/approve") and user_id == ADMIN_ID:
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
                bot.send_message(chat_id=ADMIN_ID, text="Invalid plan")
                return "OK"

            users[target_id] = {
                "expiry": expiry.isoformat()
            }

            save_users(users)

            bot.send_message(
                chat_id=int(target_id),
                text=f"✅ APPROVED!\nPlan: {plan}\nExpiry: {expiry.date()}"
            )

            bot.send_message(
                chat_id=ADMIN_ID,
                text="Approved successfully ✅"
            )

        except Exception as e:
            bot.send_message(chat_id=ADMIN_ID, text=str(e))

        return "OK"

    # =========================
    # BLOCK IF NO PLAN
    # =========================

    if not has_active_plan(user_id):
        bot.send_message(
            chat_id=user_id,
            text="❌ Your plan expired. Use /buy to continue."
        )
        return "OK"

    return "OK"

# =========================
# START APP
# =========================

if __name__ == "__main__":

    if WEBHOOK_URL:
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        print("WEBHOOK SET")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
