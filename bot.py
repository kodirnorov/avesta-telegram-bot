import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# ===== CONFIG =====
TOKEN = os.getenv("BOT_TOKEN")
IPO_CHAT_ID = -1003827093183
GENERAL_CHAT_ID = -1003827093183

TEAM_MEMBERS = ["Adhamjon", "Arnold", "Dimitriy"]
lead_counter = 0

# ===== GOOGLE SHEETS =====
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

# ===== UI =====
language_keyboard = [["O'zbek", "Русский", "English"]]
language_markup = ReplyKeyboardMarkup(language_keyboard, resize_keyboard=True)

def get_contact_markup(lang):
    labels = {
        "O'zbek": {"share": "Telefon raqamimni yuborish", "skip": "O‘tkazib yuborish"},
        "Русский": {"share": "Отправить мой номер телефона", "skip": "Пропустить"},
        "English": {"share": "Share my phone number", "skip": "Skip"}
    }

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(labels[lang]["share"], request_contact=True)],
            [labels[lang]["skip"]]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_post_contact_markup(lang):
    labels = {
        "O'zbek": ["🔁 Yana savol berish", "🏠 Bosh menyu"],
        "Русский": ["🔁 Задать еще вопрос", "🏠 Главное меню"],
        "English": ["🔁 Ask another question", "🏠 Main menu"]
    }

    return ReplyKeyboardMarkup(
        [[labels[lang][0]], [labels[lang][1]]],
        resize_keyboard=True
    )

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Avesta Investment Group-ga xush kelibsiz!\nIltimos, tilni tanlang:\n\n"
        "Добро пожаловать в Avesta Investment Group!\nПожалуйста, выберите язык:\n\n"
        "Welcome to Avesta Investment Group!\nPlease choose your language:",
        reply_markup=language_markup
    )

# ===== MAIN HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global lead_counter

    text = update.message.text if update.message.text else ""

    texts = {
        "O'zbek": {
            "choose_topic": "Iltimos, yo'nalishni tanlang:",
            "ask_request": "Iltimos, so'rovingizni yozing:",
            "phone_thanks": "Rahmat! Tez orada siz bilan bog'lanamiz.",
            "ask_phone": "Agar sizga qo'ng'iroq qilishimizni xohlasangiz, telefon raqamingizni yuboring:\n\n💡 Telefon raqam javobni tezroq olishga yordam beradi"
        },
        "Русский": {
            "choose_topic": "Пожалуйста, выберите направление:",
            "ask_request": "Пожалуйста, опишите ваш запрос:",
            "phone_thanks": "Спасибо! Мы скоро с вами свяжемся.",
            "ask_phone": "Если вы хотите, чтобы мы вам позвонили, поделитесь своим номером:\n\n💡 Номер телефона поможет быстрее с вами связаться"
        },
        "English": {
            "choose_topic": "Please choose an option:",
            "ask_request": "Please describe your request:",
            "phone_thanks": "Thank you! Our team will contact you shortly.",
            "ask_phone": "If you would like us to call you, please share your phone number:\n\n💡 Sharing your phone helps us contact you faster"
        }
    }

    keyboards = {
        "O'zbek": [["UzNIF IPO"], ["Umumiy so'rov"]],
        "Русский": [["UzNIF IPO"], ["Общий запрос"]],
        "English": [["UzNIF IPO"], ["General Inquiry"]]
    }

    # ===== POST CONTACT ACTIONS =====
    if text in ["🔁 Yana savol berish", "🔁 Задать еще вопрос", "🔁 Ask another question"]:
        lang = context.user_data.get("language", "English")
        await update.message.reply_text(texts[lang]["ask_request"])
        return

    if text in ["🏠 Bosh menyu", "🏠 Главное меню", "🏠 Main menu"]:
        context.user_data.clear()
        await start(update, context)
        return

    # ===== PHONE OR SKIP =====
    if update.message.contact or text in ["O‘tkazib yuborish", "Пропустить", "Skip"]:
        user = update.message.from_user
        lang = context.user_data.get("language", "English")
        topic = context.user_data.get("topic", "Unknown")
        lead = context.user_data.get("lead", {})

        phone = update.message.contact.phone_number if update.message.contact else "Not provided"

        combined_message = f"""
🆕 NEW LEAD

👤 {user.first_name}
📌 {topic}
🌐 {lang}

💬 {lead.get("message", "")}
🔗 @{user.username if user.username else "no_username"}
📞 {phone}

🆔 CHAT_ID: {update.message.chat_id}
"""

        chat_id = IPO_CHAT_ID if topic == "UzNIF IPO" else GENERAL_CHAT_ID
        await context.bot.send_message(chat_id=chat_id, text=combined_message)

        row_index = context.user_data.get("row_index")
        if row_index:
            sheet.update_cell(row_index, 8, phone)

        await update.message.reply_text(
            texts[lang]["phone_thanks"],
            reply_markup=get_post_contact_markup(lang)
        )
        return

    # ===== LANGUAGE =====
    if text in ["O'zbek", "Русский", "English"]:
        context.user_data["language"] = text
        await update.message.reply_text(
            texts[text]["choose_topic"],
            reply_markup=ReplyKeyboardMarkup(keyboards[text], resize_keyboard=True)
        )
        return

    # ===== TOPIC =====
    if text in ["UzNIF IPO", "General Inquiry", "Umumiy so'rov", "Общий запрос"]:
        context.user_data["topic"] = "UzNIF IPO" if text == "UzNIF IPO" else "General Inquiry"
        lang = context.user_data.get("language", "English")
        await update.message.reply_text(texts[lang]["ask_request"])
        return

    # ===== MESSAGE =====
    lang = context.user_data.get("language", "English")
    topic = context.user_data.get("topic", "Unknown")
    user = update.message.from_user

    assigned_to = TEAM_MEMBERS[lead_counter % len(TEAM_MEMBERS)]
    lead_counter += 1

    save_to_sheets([
        str(update.message.date),
        user.first_name,
        user.username if user.username else "",
        update.message.chat_id,
        topic,
        lang,
        text,
        "",
        "NEW",
        assigned_to,
        ""
    ])

    context.user_data["row_index"] = len(sheet.get_all_values())
    context.user_data["lead"] = {"message": text}

    await update.message.reply_text(
        texts[lang]["ask_phone"],
        reply_markup=get_contact_markup(lang)
    )

# ===== GROUP REPLY HANDLER =====
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type not in ["group", "supergroup"]:
        return

    if not update.message.reply_to_message:
        return

    original_text = update.message.reply_to_message.text
    reply_text = update.message.text.strip()

    if not original_text or "CHAT_ID:" not in original_text:
        return

    try:
        chat_id = None
        for line in original_text.split("\n"):
            if "CHAT_ID:" in line:
                chat_id = int(line.replace("🆔 CHAT_ID:", "").strip())
                break

        if not chat_id:
            return

        values = sheet.get_all_values()

        for i, row in enumerate(values):
            if str(chat_id) == row[3]:
                row_index = i + 1

                # FOLLOW-UP
                if reply_text.lower() in ["follow", "follow up", "follow-up"]:
                    sheet.update_cell(row_index, 9, "FOLLOW-UP")
                    await update.message.reply_text("✅ Marked as FOLLOW-UP")
                    return

                # Send reply to user
                await context.bot.send_message(chat_id=chat_id, text=reply_text)

                # Update status
                if row[8] == "NEW":
                    sheet.update_cell(row_index, 9, "CONTACTED")

                    created_time = datetime.fromisoformat(row[0])
                    minutes = int((datetime.utcnow() - created_time).total_seconds() / 60)

                    sheet.update_cell(row_index, 11, f"{minutes} min")

                return

    except Exception as e:
        print(f"Reply error: {e}")

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_reply))

app.run_polling()
