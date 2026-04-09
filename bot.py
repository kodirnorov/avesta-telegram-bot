import json
import os
import re
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
IPO_CHAT_ID = -1003827093183
GENERAL_CHAT_ID = -1003827093183

# ================= GOOGLE SHEETS =================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_json = os.getenv("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)

# Fix private key formatting
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Avesta Leads").sheet1


def save_to_sheets(data):
    sheet.append_row(data)


# ================= HELPERS =================

def is_existing_user(chat_id):
    records = sheet.get_all_records()
    for row in records:
        if str(row.get("Chat ID")) == str(chat_id):
            return True
    return False


def get_last_interaction(chat_id):
    records = sheet.get_all_records()
    for row in reversed(records):
        if str(row.get("Chat ID")) == str(chat_id):
            return row.get("Date")
    return None


def format_time_diff(last_time_str):
    if not last_time_str:
        return "First interaction"

    try:
        last_time = datetime.fromisoformat(last_time_str)
        now = datetime.utcnow()
        diff = now - last_time

        minutes = int(diff.total_seconds() / 60)
        hours = int(minutes / 60)
        days = int(hours / 24)

        if minutes < 60:
            return f"{minutes} min ago"
        elif hours < 24:
            return f"{hours}h ago"
        else:
            return f"{days}d ago"
    except:
        return "Unknown"


def find_last_user_row(chat_id):
    records = sheet.get_all_records()
    for i in range(len(records), 0, -1):
        if str(records[i - 1].get("Chat ID")) == str(chat_id):
            return i + 1
    return None


# ================= UI =================

language_keyboard = [["O'zbek", "Русский", "English"]]
language_markup = ReplyKeyboardMarkup(language_keyboard, resize_keyboard=True)


def get_contact_markup(lang):
    labels = {
        "O'zbek": "📞 Telefon raqamimni yuborish",
        "Русский": "📞 Отправить номер телефона",
        "English": "📞 Share my phone number"
    }

    skip_labels = {
        "O'zbek": "⏭ O‘tkazib yuborish",
        "Русский": "⏭ Пропустить",
        "English": "⏭ Skip"
    }

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(labels.get(lang), request_contact=True)],
            [skip_labels.get(lang)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Avesta Investment Group-ga xush kelibsiz!
         Iltimos, tilni tanlang:

         Добро пожаловать в Avesta Investment Group!
         Пожалуйста, выберите язык:

         Welcome to Avesta Investment Group!
         Please choose your language:",
        reply_markup=language_markup
    )


# ================= GROUP REPLY HANDLER =================

async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    original_text = update.message.reply_to_message.text or ""

    match = re.search(r'🆔\s*(\d+)', original_text)
    if not match:
        return

    chat_id = int(match.group(1))
    reply_text = update.message.text

    try:
        await context.bot.send_message(chat_id=chat_id, text=reply_text)
    except Exception as e:
        print("Error sending reply:", e)


# ================= MAIN HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id
    text = update.message.text or ""

    lang = context.user_data.get("language", "English")

    # ================= CONTACT =================
    if update.message.contact:
        phone = update.message.contact.phone_number

        row_index = find_last_user_row(chat_id)
        if row_index:
            sheet.update_cell(row_index, 8, phone)

        await update.message.reply_text("✅ Thank you! We will contact you soon.")
        return

    # ================= LANGUAGE =================
    if text in ["O'zbek", "Русский", "English"]:
        context.user_data["language"] = text

        keyboards = {
            "O'zbek": [["UzNIF IPO"], ["Umumiy so'rov"]],
            "Русский": [["UzNIF IPO"], ["Общий запрос"]],
            "English": [["UzNIF IPO"], ["General Inquiry"]],
        }

        await update.message.reply_text(
            "Please choose:",
            reply_markup=ReplyKeyboardMarkup(keyboards[text], resize_keyboard=True)
        )
        return

    # ================= TOPIC =================
    if text in ["UzNIF IPO", "General Inquiry", "Umumiy so'rov", "Общий запрос"]:
        context.user_data["topic"] = "UzNIF IPO" if text == "UzNIF IPO" else "General Inquiry"
        await update.message.reply_text("Please describe your request:")
        return

    # ================= MESSAGE =================

    topic = context.user_data.get("topic", "General Inquiry")

    existing = is_existing_user(chat_id)
    lead_type = "🔁 FOLLOW-UP" if existing else "📩 NEW LEAD"
    status = "Follow-up" if existing else "New"

    last_time = get_last_interaction(chat_id)
    time_label = format_time_diff(last_time)

    date_now = datetime.utcnow().isoformat()

    # Save EVERY interaction
    save_to_sheets([
        date_now,
        user.first_name,
        user.username if user.username else "",
        chat_id,
        topic,
        lang,
        text,
        "",
        status,
        ""
    ])

    combined_message = f"""
━━━━━━━━━━━━━━━
{lead_type}
━━━━━━━━━━━━━━━

🆔 {chat_id}
👤 {user.first_name}
🔗 @{user.username if user.username else "no_username"}

🌍 {lang}   |   📌 {topic}
📊 Status: {status}
🕒 Last contact: {time_label}

💬 {text}

📞 Not provided
"""

    target_chat = IPO_CHAT_ID if topic == "UzNIF IPO" else GENERAL_CHAT_ID

    await context.bot.send_message(chat_id=target_chat, text=combined_message)

    # Ask for phone
    if update.message.chat.type == "private":
        await update.message.reply_text(
            "If you'd like us to call you, please share your number (optional):",
            reply_markup=get_contact_markup(lang)
        )


# ================= APP =================

app = ApplicationBuilder().token(TOKEN).build()

# IMPORTANT ORDER
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_reply))
app.add_handler(MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("start", start))

app.run_polling()
