import json
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

import os
TOKEN = os.getenv("BOT_TOKEN")
IPO_CHAT_ID = -1003827093183
GENERAL_CHAT_ID = -1003827093183  # replace later if different group

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_json = os.getenv("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json.replace("\\n", "\n"))

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Avesta Leads").sheet1

def save_to_sheets(data):
    sheet.append_row(data)

language_keyboard = [
    ["O'zbek", "Русский", "English"]
]

language_markup = ReplyKeyboardMarkup(language_keyboard, resize_keyboard=True)

def get_contact_markup(lang):
    labels = {
        "O'zbek": "Telefon raqamimni yuborish",
        "Русский": "Отправить мой номер телефона",
        "English": "Share my phone number"
    }
    return ReplyKeyboardMarkup(
        [[KeyboardButton(labels.get(lang, "Share my phone number"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Avesta Investment Group-ga xush kelibsiz!\nIltimos, tilni tanlang:\n\n"
        "Добро пожаловать в Avesta Investment Group!\nПожалуйста, выберите язык:\n\n"
        "Welcome to Avesta Investment Group!\nPlease choose your language:",
        reply_markup=language_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text if update.message.text else ""

    # Language packs
    texts = {
        "O'zbek": {
            "choose_topic": "Iltimos, yo'nalishni tanlang:",
            "investments": "Investitsiya jamoamiz tez orada siz bilan bog'lanadi.",
            "partnerships": "Hamkorlik jamoamiz siz bilan bog'lanadi.",
            "support": "Qo'llab-quvvatlash jamoamiz tez orada yordam beradi.",
            "ask_request": "Iltimos, so'rovingizni yozing:",
            "thanks": "Rahmat! Jamoamiz tez orada siz bilan bog'lanadi.",
            "fallback": "Iltimos, menyudan variantni tanlang.",
            "ask_phone": "Agar sizga qo'ng'iroq qilishimizni xohlasangiz, telefon raqamingizni yuboring:",
            "phone_thanks": "Rahmat! Tez orada siz bilan bog'lanamiz.",
            "uznif": "UzNIF IPO",
            "general": "Umumiy so'rov"
        },
        "Русский": {
            "choose_topic": "Пожалуйста, выберите направление:",
            "investments": "Наша инвестиционная команда свяжется с вами в ближайшее время.",
            "partnerships": "Наша команда по партнерствам свяжется с вами.",
            "support": "Служба поддержки скоро вам поможет.",
            "ask_request": "Пожалуйста, опишите ваш запрос:",
            "thanks": "Спасибо! Наша команда скоро свяжется с вами.",
            "fallback": "Пожалуйста, выберите вариант из меню.",
            "ask_phone": "Если вы хотите, чтобы мы вам позвонили, поделитесь своим номером:",
            "phone_thanks": "Спасибо! Мы скоро с вами свяжемся.",
            "uznif": "UzNIF IPO",
            "general": "Общий запрос"
        },
        "English": {
            "choose_topic": "Please choose an option:",
            "uznif": "Our UzNIF IPO team will contact you shortly.",
            "general": "Our team will contact you regarding your inquiry.",
            "ask_request": "Please describe your request:",
            "thanks": "Thank you! Our team will contact you shortly.",
            "fallback": "Please choose an option from the menu.",
            "ask_phone": "If you would like us to call you, please share your phone number:",
            "phone_thanks": "Thank you! Our team will contact you shortly."
        }
    }

    keyboards = {
        "O'zbek": [["UzNIF IPO"], ["Umumiy so'rov"]],
        "Русский": [["UzNIF IPO"], ["Общий запрос"]],
        "English": [["UzNIF IPO"], ["General Inquiry"]]
    }

    if update.message.contact:
        contact = update.message.contact
        phone = contact.phone_number
        user = update.message.from_user
        lang = context.user_data.get("language")
        if not lang:
            await update.message.reply_text("Please restart with /start")
            return
        topic = context.user_data.get("topic", "Unknown")

        lead = context.user_data.get("lead", {})

        combined_message = f"""
New client request:

Name: {user.first_name}
Username: @{user.username}
Topic: {lead.get("topic", topic)}
Language: {lead.get("lang", lang)}

Message:
{lead.get("message", "")}

Phone: {phone}
"""

        print(combined_message)

        # Send only ONE combined message
        try:
            chat_id = IPO_CHAT_ID if lead.get("topic") == "UzNIF IPO" else GENERAL_CHAT_ID
            await context.bot.send_message(chat_id=chat_id, text=combined_message)
        except Exception as e:
            print(f"Error sending message: {e}")

        row_index = context.user_data.get("row_index")
        if row_index:
            sheet.update_cell(row_index, 7, phone)

        await update.message.reply_text(texts[lang]["phone_thanks"], reply_markup=ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True))
        return

    # Step 1: Language selection
    if text in ["O'zbek", "Русский", "English"]:
        context.user_data["language"] = text
        lang = context.user_data.get("language", "English")
        await update.message.reply_text(
            texts[lang]["choose_topic"],
            reply_markup=ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
        )

    # Step 2: Topic selection
    elif text in ["UzNIF IPO", "General Inquiry", "Umumiy so'rov", "Общий запрос"]:
        if text == "UzNIF IPO":
            context.user_data["topic"] = "UzNIF IPO"
        else:
            context.user_data["topic"] = "General Inquiry"
        lang = context.user_data.get("language")
        if not lang:
            await update.message.reply_text("Please restart with /start")
            return
        await update.message.reply_text(
            texts[lang]["ask_request"]
        )

    # Step 3: Capture request
    else:
        lang = context.user_data.get("language")
        if not lang:
            await update.message.reply_text("Please restart with /start")
            return
        topic = context.user_data.get("topic", "Unknown")
        user = update.message.from_user

        message = f"""
New client request:

Name: {user.first_name}
Username: @{user.username}
Topic: {topic}
Language: {lang}

Message:
{text}
"""

        print(message)

        # Save lead temporarily in memory
        context.user_data["lead"] = {
            "message": text,
            "topic": topic,
            "lang": lang,
            "name": user.first_name,
            "username": user.username if user.username else "",
            "date": str(update.message.date)
        }

        save_to_sheets([
            str(update.message.date),
            user.first_name,
            user.username if user.username else "",
            topic,
            lang,
            text,
            ""
        ])

        # Save row index for later update
        context.user_data["row_index"] = len(sheet.get_all_values())

        if update.message.chat.type == "private":
            await update.message.reply_text(
                texts[lang]["ask_phone"],
                reply_markup=get_contact_markup(lang)
            )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, handle_message))

app.run_polling()
