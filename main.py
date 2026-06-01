import os
import json
import random
import string
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "files.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def make_code(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👻 File Store Bot\n\n"
        "Koi bhi file bhejo, main store karke share code de dunga.\n\n"
        "Share karne ke liye command milega:\n"
        "/get_CODE"
    )

@bot.message_handler(commands=["get"])
def get_help(message):
    bot.reply_to(message, "Use karo: /get_CODE\nExample: /get_aB12xyZ9")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/get_"))
def get_file(message):
    code = message.text.replace("/get_", "").strip()
    db = load_db()

    if code not in db:
        bot.reply_to(message, "❌ File nahi mili ya code galat hai.")
        return

    file_id = db[code]["file_id"]
    file_type = db[code]["type"]

    bot.reply_to(message, "✅ File mil gayi, bhej raha hoon...")

    if file_type == "document":
        bot.send_document(message.chat.id, file_id)
    elif file_type == "photo":
        bot.send_photo(message.chat.id, file_id)
    elif file_type == "video":
        bot.send_video(message.chat.id, file_id)
    elif file_type == "audio":
        bot.send_audio(message.chat.id, file_id)
    elif file_type == "voice":
        bot.send_voice(message.chat.id, file_id)
    else:
        bot.send_document(message.chat.id, file_id)

def store_file(message, file_id, file_type, file_name="unknown"):
    db = load_db()
    code = make_code()

    db[code] = {
        "file_id": file_id,
        "type": file_type,
        "file_name": file_name,
        "user_id": message.from_user.id,
        "username": message.from_user.username
    }

    save_db(db)

    bot.reply_to(
        message,
        f"✅ File store ho gayi!\n\n"
        f"🔗 Share command:\n"
        f"/get_{code}\n\n"
        f"Is command ko kisi ko bhi bhej do, wo file le sakta hai."
    )

@bot.message_handler(content_types=["document"])
def handle_document(message):
    file_id = message.document.file_id
    file_name = message.document.file_name
    store_file(message, file_id, "document", file_name)

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    store_file(message, file_id, "photo", "photo.jpg")

@bot.message_handler(content_types=["video"])
def handle_video(message):
    file_id = message.video.file_id
    store_file(message, file_id, "video", "video.mp4")

@bot.message_handler(content_types=["audio"])
def handle_audio(message):
    file_id = message.audio.file_id
    store_file(message, file_id, "audio", "audio.mp3")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    file_id = message.voice.file_id
    store_file(message, file_id, "voice", "voice.ogg")

print("Bot started...")
bot.infinity_polling()
