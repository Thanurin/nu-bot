import os
import json
from datetime import datetime, timedelta

from flask import Flask, request
from telegram import Bot, Update

# =========================

# CONFIG

# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

USERS_FILE = "users.json"

# =========================

# CREATE USERS FILE

# =========================

if not os.path.exists(USERS_FILE):
with open(USERS_FILE, "w") as f:
json.dump({}, f)

# =========================

# LOAD USERS

# =========================

def load_users():
with open(USERS_FILE, "r") as f:
return json.load(f)

def save_users(data):
with open(USERS_FILE, "w") as f:
json.dump(data, f, indent=4)

# =========================

# CHECK ACTIVE PLAN

# =========================

def has_active_plan(user_id):

```
users = load_users()

user_id = str(user_id)

if user_id not in users:
    return False

expiry = users[user_id].get("expiry")

if not expiry:
    return False

expiry_date = datetime.fromisoformat(expiry)

return datetime.now() < expiry_date
```

# =========================

# HOME

# =========================

@app.route("/", methods=["GET"])
def home():
return "BOT RUNNING"

# =========================

# WEBHOOK

# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

```
data = request.get_json(force=True)

update = Update.de_json(data, bot)

if not update.message:
    return "OK"

msg = update.message

user_id = msg.from_user.id
text = msg.text or ""

users = load_users()

# =========================
# START
# =========================

if text == "/start":

    bot.send_message(
        chat_id=user_id,
        text="""
```

សួស្តី! អតិថិជនជាទីគោរព!

សូមធ្វើការបង់ប្រាក់ដោយវាយពាក្យ

/buy

ដើម្បីប្រើប្រាស់ខ្ញុំ
ព្រមទាំងជួយឧបត្ថម្ភខ្ញុំផងដែរ!

សូមអរគុណ ❤️
"""
)

```
    return "OK"

# =========================
# BUY
# =========================

if text == "/buy":

    caption = """
```

គម្រោងរបស់យើង

1. 3$/សប្តាហ៍
2. 11.5$/ខែ
3. 120$/ឆ្នាំ

សូមធ្វើការទូទាត់ប្រាក់តាមរយៈ QR-Code
ហើយផ្ញើ Screenshot មកខ្ញុំ ❤️
"""

```
    bot.send_photo(
        chat_id=user_id,
        photo=open("qr.png", "rb"),
        caption=caption
    )

    return "OK"

# =========================
# PAYMENT SCREENSHOT
# =========================

if msg.photo:

    photo_id = msg.photo[-1].file_id

    caption = f"""
```

NEW PAYMENT PROOF

USER ID: {user_id}
NAME: {msg.from_user.first_name}
"""

```
    bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=caption
    )

    bot.send_message(
        chat_id=user_id,
        text="សូមរង់ចាំ Admin អនុម័ត ❤️"
    )

    return "OK"

# =========================
# APPROVE
# =========================

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

            bot.send_message(
                chat_id=ADMIN_ID,
                text="Invalid plan"
            )

            return "OK"

        if target_id not in users:
            users[target_id] = {}

        users[target_id]["expiry"] = expiry.isoformat()

        save_users(users)

        bot.send_message(
            chat_id=int(target_id),
            text=f"""
```

✅ PAYMENT APPROVED

PLAN: {plan}

EXPIRY:
{expiry.strftime('%Y-%m-%d')}
"""
)

```
        bot.send_message(
            chat_id=ADMIN_ID,
            text="APPROVED SUCCESS ✅"
        )

    except Exception as e:

        bot.send_message(
            chat_id=ADMIN_ID,
            text=str(e)
        )

    return "OK"

# =========================
# GROUP DETECT
# =========================

if msg.chat.type in ["group", "supergroup"]:

    gid = msg.chat.id

    bot.send_message(
        chat_id=gid,
        text=f"""
```

GROUP CONNECTED ✅

GROUP ID:
{gid}

Send this group ID to bot privately.
"""
)

```
    return "OK"

# =========================
# SAVE GROUP ID
# =========================

if text.startswith("-100"):

    if not has_active_plan(user_id):

        bot.send_message(
            chat_id=user_id,
            text="""
```

❌ គម្រោងរបស់អ្នកបានផុតកំណត់

សូមវាយ

/buy

ដើម្បីបន្តប្រើប្រាស់
"""
)

```
        return "OK"

    if str(user_id) not in users:
        users[str(user_id)] = {}

    users[str(user_id)]["group_id"] = int(text)

    save_users(users)

    bot.send_message(
        chat_id=user_id,
        text="GROUP CONNECTED SUCCESS ✅"
    )

    return "OK"

# =========================
# FORWARD MESSAGE
# =========================

if has_active_plan(user_id):

    user_data = users.get(str(user_id), {})

    group_id = user_data.get("group_id")

    if group_id:

        try:

            if msg.text:

                bot.send_message(
                    chat_id=group_id,
                    text=msg.text
                )

            elif msg.photo:

                bot.send_photo(
                    chat_id=group_id,
                    photo=msg.photo[-1].file_id
                )

            elif msg.video:

                bot.send_video(
                    chat_id=group_id,
                    video=msg.video.file_id
                )

            elif msg.document:

                bot.send_document(
                    chat_id=group_id,
                    document=msg.document.file_id
                )

        except Exception as e:

            bot.send_message(
                chat_id=user_id,
                text=f"ERROR:\n{e}"
            )

else:

    bot.send_message(
        chat_id=user_id,
        text="""
```

❌ គម្រោងរបស់អ្នកបានផុតកំណត់

សូមវាយ

/buy

ដើម្បីបន្តប្រើប្រាស់
"""
)

```
return "OK"
```

# =========================

# START APP

# =========================

if **name** == "**main**":

```
if WEBHOOK_URL:

    bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook"
    )

    print("WEBHOOK SET")

app.run(
    host="0.0.0.0",
    port=int(os.getenv("PORT", 10000))
)
```
