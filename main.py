import os, json, random, string
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "Hexfilestorebot")

ADMIN_IDS = [123456789]  # apna Telegram ID yaha dalo

bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "files.json"
BAN_FILE = "bans.json"
CHANNEL_FILE = "channels.json"

sessions = {}
admin_state = {}

bot.set_my_commands([
    types.BotCommand("start", "Bot Start"),
    types.BotCommand("genlink", "Multiple file store link"),
    types.BotCommand("done", "Generate share link"),
    types.BotCommand("settings", "Admin Settings"),
    types.BotCommand("ban", "Ban User"),
    types.BotCommand("unban", "Unban User")
])

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def make_code(n=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_banned(user_id):
    bans = load_json(BAN_FILE, {})
    return str(user_id) in bans

def load_channels():
    return load_json(CHANNEL_FILE, [])

def save_channels(data):
    save_json(CHANNEL_FILE, data)

def is_joined(user_id):
    channels = load_channels()
    if not channels:
        return True

    for ch in channels:
        try:
            member = bot.get_chat_member(ch["chat_id"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def join_buttons():
    markup = types.InlineKeyboardMarkup()
    for ch in load_channels():
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["link"]))
    markup.add(types.InlineKeyboardButton("✅ Joined / Check", callback_data="check_join"))
    return markup

def send_join_message(chat_id):
    bot.send_message(
        chat_id,
        "🔒 File lene ke liye pehle sabhi channels join karo.",
        reply_markup=join_buttons()
    )

def send_file(chat_id, file_id, file_type):
    if file_type == "document":
        bot.send_document(chat_id, file_id)
    elif file_type == "photo":
        bot.send_photo(chat_id, file_id)
    elif file_type == "video":
        bot.send_video(chat_id, file_id)
    elif file_type == "audio":
        bot.send_audio(chat_id, file_id)
    elif file_type == "voice":
        bot.send_voice(chat_id, file_id)
    else:
        bot.send_document(chat_id, file_id)

def send_stored_file(message, code):
    db = load_json(DB_FILE, {})

    if code not in db:
        bot.reply_to(message, "❌ File nahi mili ya link galat hai.")
        return

    data = db[code]

    if data["type"] == "multiple":
        bot.reply_to(message, f"✅ {len(data['files'])} files bhej raha hoon...")
        for f in data["files"]:
            send_file(message.chat.id, f["file_id"], f["type"])
    else:
        send_file(message.chat.id, data["file_id"], data["type"])

@bot.message_handler(commands=["start"])
def start(message):
    user = message.from_user
    name = user.first_name or "No Name"
    username = f"@{user.username}" if user.username else "No username"

    bot.send_message(
        message.chat.id,
        f"👤 Name: {name}\n"
        f"🔰 Username: {username}\n"
        f"🆔 ID: `{user.id}`",
        parse_mode="Markdown"
    )

    if is_banned(user.id):
        bot.reply_to(message, "🚫 Aap banned ho.")
        return

    if not is_joined(user.id):
        send_join_message(message.chat.id)
        return

    parts = message.text.split()
    if len(parts) > 1:
        send_stored_file(message, parts[1])
    else:
        bot.reply_to(
            message,
            "👻 File Store Bot\n\n"
            "Single file bhejo ya multiple file link ke liye /genlink use karo."
        )

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if is_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified")
        bot.send_message(call.message.chat.id, "✅ Verified! Ab file link dubara open karo.")
    else:
        bot.answer_callback_query(call.id, "❌ Pehle sabhi channels join karo.", show_alert=True)

@bot.chat_join_request_handler()
def approve_join_request(request):
    try:
        bot.approve_chat_join_request(request.chat.id, request.from_user.id)
    except:
        pass

@bot.message_handler(commands=["genlink"])
def genlink(message):
    if is_banned(message.from_user.id):
        return

    sessions[str(message.from_user.id)] = []
    bot.reply_to(message, "📁 Multiple files bhejo.\n\nSab file bhejne ke baad /done bhejo.")

@bot.message_handler(commands=["done"])
def done(message):
    user_id = str(message.from_user.id)

    if user_id not in sessions or len(sessions[user_id]) == 0:
        bot.reply_to(message, "❌ Pehle /genlink karo aur files bhejo.")
        return

    db = load_json(DB_FILE, {})
    code = make_code()

    db[code] = {
        "type": "multiple",
        "files": sessions[user_id],
        "user_id": user_id
    }

    save_json(DB_FILE, db)
    del sessions[user_id]

    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.reply_to(message, f"✅ Multiple files store ho gayi!\n\n🔗 Share Link:\n{link}")

def save_session_or_single(message, file_id, file_type, file_name):
    if is_banned(message.from_user.id):
        return

    user_id = str(message.from_user.id)

    if user_id in sessions:
        sessions[user_id].append({
            "file_id": file_id,
            "type": file_type,
            "file_name": file_name
        })
        bot.reply_to(message, f"✅ Added: {file_name}\nTotal: {len(sessions[user_id])}")
        return

    db = load_json(DB_FILE, {})
    code = make_code()

    db[code] = {
        "type": file_type,
        "file_id": file_id,
        "file_name": file_name,
        "user_id": user_id
    }

    save_json(DB_FILE, db)

    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.reply_to(message, f"✅ File store ho gayi!\n\n🔗 Share Link:\n{link}")

@bot.message_handler(content_types=["document"])
def document(message):
    save_session_or_single(message, message.document.file_id, "document", message.document.file_name)

@bot.message_handler(content_types=["photo"])
def photo(message):
    save_session_or_single(message, message.photo[-1].file_id, "photo", "photo.jpg")

@bot.message_handler(content_types=["video"])
def video(message):
    save_session_or_single(message, message.video.file_id, "video", "video.mp4")

@bot.message_handler(content_types=["audio"])
def audio(message):
    save_session_or_single(message, message.audio.file_id, "audio", "audio.mp3")

@bot.message_handler(content_types=["voice"])
def voice(message):
    save_session_or_single(message, message.voice.file_id, "voice", "voice.ogg")

@bot.message_handler(commands=["settings"])
def settings(message):
    if not is_admin(message.from_user.id):
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"))
    markup.add(types.InlineKeyboardButton("📋 Channel List", callback_data="list_channel"))
    markup.add(types.InlineKeyboardButton("🗑 Delete Channel", callback_data="delete_channel"))
    markup.add(types.InlineKeyboardButton("📊 Total Files", callback_data="total_files"))

    bot.send_message(message.chat.id, "⚙️ Admin Settings", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["add_channel", "list_channel", "delete_channel", "total_files"])
def settings_buttons(call):
    if not is_admin(call.from_user.id):
        return

    if call.data == "add_channel":
        admin_state[call.from_user.id] = "waiting_channel"
        bot.send_message(
            call.message.chat.id,
            "📢 Channel details bhejo:\n\n"
            "Format:\n"
            "`Channel Name | chat_id | invite_link`\n\n"
            "Public example:\n"
            "`My Channel | @mychannel | https://t.me/mychannel`\n\n"
            "Private example:\n"
            "`Private Channel | -1001234567890 | https://t.me/+abcd1234`",
            parse_mode="Markdown"
        )

    elif call.data == "list_channel":
        channels = load_channels()
        if not channels:
            bot.send_message(call.message.chat.id, "❌ Koi channel add nahi hai.")
            return

        text = "📋 Channel List:\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']}\nID: `{ch['chat_id']}`\nLink: {ch['link']}\n\n"

        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    elif call.data == "delete_channel":
        admin_state[call.from_user.id] = "delete_channel"
        bot.send_message(call.message.chat.id, "🗑 Delete number bhejo.\nExample: `1`", parse_mode="Markdown")

    elif call.data == "total_files":
        db = load_json(DB_FILE, {})
        bot.send_message(call.message.chat.id, f"📊 Total stored links: {len(db)}")

@bot.message_handler(func=lambda m: m.from_user.id in admin_state)
def admin_input(message):
    if not is_admin(message.from_user.id):
        return

    state = admin_state.get(message.from_user.id)

    if state == "waiting_channel":
        try:
            name, chat_id, link = [x.strip() for x in message.text.split("|")]

            if chat_id.startswith("-100"):
                chat_id = int(chat_id)

            channels = load_channels()
            channels.append({
                "name": name,
                "chat_id": chat_id,
                "link": link
            })
            save_channels(channels)

            admin_state.pop(message.from_user.id, None)
            bot.reply_to(message, "✅ Channel add ho gaya.")
        except:
            bot.reply_to(message, "❌ Format galat hai.\nUse:\nChannel Name | chat_id | invite_link")

    elif state == "delete_channel":
        try:
            index = int(message.text.strip()) - 1
            channels = load_channels()

            if index < 0 or index >= len(channels):
                bot.reply_to(message, "❌ Number galat hai.")
                return

            removed = channels.pop(index)
            save_channels(channels)
            admin_state.pop(message.from_user.id, None)

            bot.reply_to(message, f"✅ Deleted: {removed['name']}")
        except:
            bot.reply_to(message, "❌ Sirf number bhejo.")

@bot.message_handler(commands=["ban"])
def ban(message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Use: /ban USER_ID")
        return

    bans = load_json(BAN_FILE, {})
    bans[parts[1]] = True
    save_json(BAN_FILE, bans)
    bot.reply_to(message, "🚫 User banned.")

@bot.message_handler(commands=["unban"])
def unban(message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Use: /unban USER_ID")
        return

    bans = load_json(BAN_FILE, {})
    bans.pop(parts[1], None)
    save_json(BAN_FILE, bans)
    bot.reply_to(message, "✅ User unbanned.")

print("Bot started...")
bot.infinity_polling()
