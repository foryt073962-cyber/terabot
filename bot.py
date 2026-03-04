
import aiohttp
import html
import re
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
ContextTypes,
filters
)

BOT_TOKEN = "8765085860:AAGWPNYdRPDhG_PGdcDIamMP9TS4uCpYC6A"
API_ENDPOINT = "https://terabox.anshapi.workers.dev/api/terabox-down?url="

#---------- Helpers ----------

def is_folder_link(url: str):
return "filelist?surl=" in url

def is_valid_link(url: str):
return "terabox.com" in url or "1024terabox.com" in url or "1024tera.com" in url or "terasharefile.com" in url

#---------- Start Command ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"🚀 Send TeraBox file or folder link\n\n"
"⚡ Direct Fast Upload Supported"
)

#---------- Main Message Handler ----------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_url = update.message.text.strip()

if not is_valid_link(user_url):  
    await update.message.reply_text("❌ Invalid TeraBox link.")  
    return  

msg = await update.message.reply_text("⚡ Fetching data...")  

try:  
    async with aiohttp.ClientSession() as session:  
        async with session.get(API_ENDPOINT + user_url) as resp:  
            data = await resp.json()  

    if not data.get("data"):  
        await msg.edit_text("❌ Failed to fetch data.")  
        return  

    # If folder  
    if is_folder_link(user_url):  
        await handle_folder(update, context, data["data"])  
        await msg.delete()  
        return  

    # If single file  
    await handle_single_file(update, data["data"])  
    await msg.delete()  

except Exception as e:  
    await msg.edit_text(f"❌ Error: {e}")

#---------- Handle Single File ----------

async def handle_single_file(update, file_data):

# Check format safely  
if "videos" in file_data:  
    file = file_data["videos"][0]  
    name = html.escape(file["name"])  
    size = file["size"]  
    thumb = file["thumbnail"]  
    download_link = file["urls"]["download"]  
    stream_link = file["urls"]["stream"]  

elif "list" in file_data:  
    file = file_data["list"][0]  
    name = html.escape(file["server_filename"])  
    size = file["formatted_size"]  
    thumb = file["thumbs"]["url1"]  
    download_link = file["direct_link"]  
    stream_link = file["stream_url"]  

else:  
    await update.message.reply_text("❌ Unknown file format.")  
    return  

caption = f"📁 <b>{name}</b>\n📦 Size: {size}"  

keyboard = [[  
    InlineKeyboardButton("⬇ Download", url=download_link),  
    InlineKeyboardButton("▶ Stream", url=stream_link),  
]]  

await update.message.reply_photo(  
    photo=thumb,  
    caption=caption,  
    parse_mode="HTML",  
    reply_markup=InlineKeyboardMarkup(keyboard),  
)  

await update.message.reply_document(  
    document=download_link,  
    caption=caption,  
    parse_mode="HTML",  
)

#---------- Handle Folder ----------

async def handle_folder(update, context, folder_data):
files = folder_data["list"]

context.user_data["folder_files"] = files  

buttons = []  
for index, file in enumerate(files):  
    buttons.append([  
        InlineKeyboardButton(  
            f"{file['server_filename']} ({file['formatted_size']})",  
            callback_data=f"file_{index}"  
        )  
    ])  

await update.message.reply_text(  
    "📂 Select a file:",  
    reply_markup=InlineKeyboardMarkup(buttons)  
)

#---------- Callback for Folder File Selection ----------

async def file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

index = int(query.data.split("_")[1])  
file = context.user_data["folder_files"][index]  

name = html.escape(file["server_filename"])  
size = file["formatted_size"]  
thumb = file["thumbs"]["url1"]  
direct_link = file["direct_link"]  
stream_link = file["stream_url"]  

caption = f"📁 <b>{name}</b>\n📦 Size: {size}"  

keyboard = [  
    [  
        InlineKeyboardButton("⬇ Download", url=direct_link),  
        InlineKeyboardButton("▶ Stream", url=stream_link),  
    ]  
]  

await query.message.reply_photo(  
    photo=thumb,  
    caption=caption,  
    parse_mode="HTML",  
    reply_markup=InlineKeyboardMarkup(keyboard),  
)  

# Direct Fast Upload  
await query.message.reply_document(  
    document=direct_link,  
    caption=caption,  
    parse_mode="HTML",  
)

#---------- Run Bot ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(file_callback))

print("🚀 Bot Running...")
app.run_polling()
