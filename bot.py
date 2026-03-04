import aiohttp
import html
import os
import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
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

# 🔥 PRIVATE CHANNEL INVITE LINK
PRIVATE_INVITE_LINK = "https://t.me/+msYViqd3ictiYzZl"

API_ENDPOINT = "https://terabox.anshapi.workers.dev/api/terabox-down?url="

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

COOLDOWN_SECONDS = 10
MAX_REQUESTS_PER_MINUTE = 5

user_last_request = {}
user_request_count = {}
approved_users = set()

# ================= JOIN REQUEST HANDLER =================
async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    approved_users.add(user.id)
    print(f"Access granted to {user.id}")

# ================= FORCE CHECK =================
async def check_access(user_id):
    return user_id in approved_users

# ================= JOIN MESSAGE =================
async def send_join_message(update: Update):
    keyboard = [
        [InlineKeyboardButton("🔔 Join Private Channel", url=PRIVATE_INVITE_LINK)],
        [InlineKeyboardButton("✅ I Sent Request", callback_data="check_join")]
    ]

    await update.message.reply_text(
        "🚫 You must send join request to use this bot.\n\n"
        "1️⃣ Click Join\n"
        "2️⃣ Send Request\n"
        "3️⃣ Come back and click 'I Sent Request'",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= RECHECK =================
async def recheck_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await check_access(query.from_user.id):
        await query.message.edit_text("✅ Access Granted! Now send your link.")
    else:
        await query.answer("❌ Request not detected yet!", show_alert=True)

# ================= RATE LIMIT =================
def check_rate_limit(user_id):
    current_time = time.time()

    if user_id in user_last_request:
        if current_time - user_last_request[user_id] < COOLDOWN_SECONDS:
            return False, "⏳ Please wait before sending another link."

    minute = int(current_time // 60)
    key = (user_id, minute)
    user_request_count[key] = user_request_count.get(key, 0) + 1

    if user_request_count[key] > MAX_REQUESTS_PER_MINUTE:
        return False, "🚫 Too many requests. Try again later."

    user_last_request[user_id] = current_time
    return True, None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update.effective_user.id):
        await send_join_message(update)
        return

    await update.message.reply_text("🚀 Send TeraBox link.")

# ================= HANDLE MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if not await check_access(user_id):
        await send_join_message(update)
        return

    allowed, message = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(message)
        return

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

    except:
        await msg.edit_text("❌ Error fetching file.")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(recheck_join, pattern="check_join"))
app.add_handler(ChatJoinRequestHandler(join_request_handler))

print("🚀 Bot Running...")
app.run_polling()
