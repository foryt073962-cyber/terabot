import aiohttp
import html
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003736030609   # 🔥 apna real private channel ID daalo
PRIVATE_INVITE_LINK = "https://t.me/+msYViqd3ictiYzZl"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

API_ENDPOINT = "https://terabox.anshapi.workers.dev/api/terabox-down?url="

approved_users = set()
COOLDOWN_SECONDS = 10
user_last_request = {}

# ================= JOIN REQUEST AUTO DETECT =================
async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    approved_users.add(user.id)
    print(f"Auto Access granted to {user.id}")

# ================= ACCESS CHECK =================
async def check_access(user_id, context):
    if user_id in approved_users:
        return True

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass

    return False

# ================= SEND JOIN MESSAGE =================
async def send_join_message(update: Update):
    keyboard = [[InlineKeyboardButton("🔔 Join Private Channel", url=PRIVATE_INVITE_LINK)]]

    await update.message.reply_text(
        "🚫 You must send join request to use this bot.\n\n"
        "Click below and send request.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update.effective_user.id, context):
        await send_join_message(update)
        return

    await update.message.reply_text("🚀 Send TeraBox link.")

# ================= HANDLE MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if not await check_access(user_id, context):
        await send_join_message(update)
        return

    # Cooldown
    now = time.time()
    if user_id in user_last_request:
        if now - user_last_request[user_id] < COOLDOWN_SECONDS:
            await update.message.reply_text("⏳ Wait before next request.")
            return

    user_last_request[user_id] = now

    user_url = update.message.text.strip()
    msg = await update.message.reply_text("⚡ Fetching...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_ENDPOINT + user_url, timeout=10) as resp:
                data = await resp.json()

        file = data["data"]["videos"][0]
        name = html.escape(file["name"])
        size = file["size"]
        thumb = file["thumbnail"]
        download_link = file["urls"]["download"]

        keyboard = [[InlineKeyboardButton("⬇ Download", url=download_link)]]

        await update.message.reply_photo(
            photo=thumb,
            caption=f"<b>{name}</b>\nSize: {size}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        await msg.delete()

    except Exception as e:
        print(e)
        await msg.edit_text("❌ Error fetching file.")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(ChatJoinRequestHandler(join_request_handler))

print("🚀 Bot Running...")
app.run_polling()
