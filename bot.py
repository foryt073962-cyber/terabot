import aiohttp
import html
import os
import time
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("8765085860:AAGWPNYdRPDhG_PGdcDIamMP9TS4uCpYC6A")
API_ENDPOINT = "https://terabox.anshapi.workers.dev/api/terabox-down?url="

ADMIN_ID = 6943459142
FORCE_CHANNEL = "https://t.me/+msYViqd3ictiYzZl"

COOLDOWN_SECONDS = 10
MAX_REQUESTS_PER_MINUTE = 5

DATA_FILE = "data.json"

# ===== Load Persistent Data =====
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data_store = json.load(f)
else:
    data_store = {"users": [], "total_requests": 0}

PREMIUM_USERS = set(data_store.get("premium", []))

def save_data():
    data_store["premium"] = list(PREMIUM_USERS)
    with open(DATA_FILE, "w") as f:
        json.dump(data_store, f)

# ===== Rate Limit Memory =====
user_last_request = {}
user_request_count = {}

# ---------- Helper Functions ----------

def is_folder_link(url: str):
    return "filelist?surl=" in url


def is_valid_link(url: str):
    return "terabox.com" in url


async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False


def check_rate_limit(user_id):
    if user_id in PREMIUM_USERS:
        return True, None

    current_time = time.time()

    if user_id in user_last_request:
        if current_time - user_last_request[user_id] < COOLDOWN_SECONDS:
            return False, "⏳ Please wait before sending another link."

    minute = int(current_time // 60)
    key = (user_id, minute)
    user_request_count[key] = user_request_count.get(key, 0) + 1

    if user_request_count[key] > MAX_REQUESTS_PER_MINUTE:
        return False, "🚫 Too many requests. Try again in a minute."

    user_last_request[user_id] = current_time
    return True, None


# ---------- Commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in data_store["users"]:
        data_store["users"].append(user_id)
        save_data()

    await update.message.reply_text("🚀 Send TeraBox link")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    total_users = len(data_store["users"])
    total_requests = data_store["total_requests"]

    await update.message.reply_text(
        f"📊 Bot Stats\n\n👥 Users: {total_users}\n📦 Requests: {total_requests}"
    )


async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        PREMIUM_USERS.add(user_id)
        save_data()
        await update.message.reply_text("✅ User added to premium.")
    except:
        await update.message.reply_text("❌ Usage: /addpremium user_id")


# ---------- Main Handler ----------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_url = update.message.text.strip()

    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🚫 Join channel first: {FORCE_CHANNEL}"
        )
        return

    allowed, message = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(message)
        return

    if not is_valid_link(user_url):
        await update.message.reply_text("❌ Invalid link.")
        return

    data_store["total_requests"] += 1
    save_data()

    msg = await update.message.reply_text("⚡ Fetching...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_ENDPOINT + user_url, timeout=10) as resp:
                data = await resp.json()

        file = data["data"]["list"][0]

        name = html.escape(file["server_filename"])
        size = file["formatted_size"]
        direct_link = file["direct_link"]
        stream_link = file["stream_url"]

        caption = f"📁 <b>{name}</b>\n📦 Size: {size}"

        keyboard = [[
            InlineKeyboardButton("⬇ Download", url=direct_link),
            InlineKeyboardButton("▶ Stream", url=stream_link),
        ]]

        await msg.delete()
        await update.message.reply_text(
            caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await msg.edit_text("❌ Server error.")


# ---------- Run Bot ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("addpremium", add_premium))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Pro Bot Running...")
app.run_polling()
