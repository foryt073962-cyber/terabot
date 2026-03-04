

import aiohttp
import html
import os
import time
import re
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatJoinRequestHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_ID = -1003736030609  # 🔥 APNA PRIVATE CHANNEL ID DAALO
PRIVATE_INVITE_LINK = "https://t.me/+msYViqd3ictiYzZl"

API_ENDPOINT = "https://terabox.anshapi.workers.dev/api/terabox-down?url="

ALLOWED_DOMAINS = [
    "terabox.com",
    "1024terabox.com",
    "1024tera.com",
    "terasharefile.com"
]

COOLDOWN_SECONDS = 10

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

# ================= MEMORY =================

approved_users = set()
user_last_request = {}

# ================= DOMAIN VALIDATION =================

def is_valid_link(url: str):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain in ALLOWED_DOMAINS
    except:
        return False

# ================= JOIN REQUEST AUTO DETECT =================

async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    approved_users.add(user.id)
    print(f"Auto access granted → {user.id}")

# ================= ACCESS CHECK =================

async def check_access(user_id, context):

    # If already detected request
    if user_id in approved_users:
        return True

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass

    return False

# ================= JOIN MESSAGE =================

async def send_join_message(update: Update):
    keyboard = [
        [InlineKeyboardButton("🔔 Join Private Channel", url=PRIVATE_INVITE_LINK)]
    ]

    await update.message.reply_text(
        "🚫 You must send join request to use this bot.\n\n"
        "Click below and send request.\n"
        "After sending request, just send your link again.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await check_access(update.effective_user.id, context):
        await send_join_message(update)
        return

    await update.message.reply_text("🚀 Send your TeraBox link.")

# ================= HANDLE MESSAGE =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    # Access check
    if not await check_access(user_id, context):
        await send_join_message(update)
        return

    user_url = update.message.text.strip()

    # Domain check
    if not is_valid_link(user_url):
        await update.message.reply_text(
            "❌ Invalid link!\n\n"
            "Supported domains:\n"
            "• terabox\n"
            "• 1024terabox\n"
            "• 1024tera\n"
            "• terashare"
        )
        return

    # Cooldown
    now = time.time()
    if user_id in user_last_request:
        if now - user_last_request[user_id] < COOLDOWN_SECONDS:
            await update.message.reply_text("⏳ Please wait before next request.")
            return

    user_last_request[user_id] = now

    msg = await update.message.reply_text("⚡ Fetching...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_ENDPOINT + user_url, timeout=15) as resp:
                data = await resp.json()

        if not data.get("data"):
            await msg.edit_text("❌ Failed to fetch file.")
            return

        file_data = data["data"]["videos"][0]

        name = html.escape(file_data["name"])
        size = file_data["size"]
        thumb = file_data["thumbnail"]
        download_link = file_data["urls"]["download"]

        keyboard = [
            [InlineKeyboardButton("⬇ Download", url=download_link)]
        ]

        await update.message.reply_photo(
            photo=thumb,
            caption=f"<b>{name}</b>\nSize: {size}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        await msg.delete()

    except Exception as e:
        print("Error:", e)
        await msg.edit_text("❌ Server error while fetching file.")

# ================= RUN =================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(ChatJoinRequestHandler(join_request_handler))

print("🚀 Bot Running...")
app.run_polling()
