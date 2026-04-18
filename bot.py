import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# =========================
# ENV VARIABLES
# =========================
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

DATA_FILE = "data.json"

# =========================
# DATA
# =========================
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load()

def user(uid):
    uid = str(uid)
    if uid not in data:
        data[uid] = {"score": 0, "xp": 0, "level": 1}
    return data[uid]

# =========================
# AI (FIXED GEMINI)
# =========================
def ai_chat(prompt):
    if not GEMINI_API_KEY:
        return "❌ AI مش متفعل"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        res = requests.post(url, json=payload)
        data = res.json()

        if "candidates" not in data:
            return f"❌ AI Error: {data}"

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        return f"❌ AI Error: {str(e)}"

# =========================
# IMAGE
# =========================
def generate_image(prompt):
    return f"https://image.pollinations.ai/prompt/{prompt}"

# =========================
# SUB CHECK (مبسط)
# =========================
async def check_sub(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return True  # لو حصل مشكلة نخليها تمر

# =========================
# MENU
# =========================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 كويز", callback_data="quiz")],
        [InlineKeyboardButton("🤖 اسأل AI", callback_data="ask")],
        [InlineKeyboardButton("🏆 نتيجتي", callback_data="score")]
    ])

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    user(uid)
    save(data)

    await update.message.reply_text("🔥 أهلاً بيك", reply_markup=menu())

# =========================
# QUIZ (بسيط)
# =========================
def question():
    return (
        "ما وظيفة الميتوكوندريا؟",
        {"A": "تخزين الماء", "B": "إنتاج الطاقة", "C": "الحماية", "D": "النقل"},
        "B"
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    ques, options, ans = question()
    context.user_data["answer"] = ans

    keyboard = [
        [InlineKeyboardButton(f"A) {options['A']}", callback_data="A")],
        [InlineKeyboardButton(f"B) {options['B']}", callback_data="B")],
        [InlineKeyboardButton(f"C) {options['C']}", callback_data="C")],
        [InlineKeyboardButton(f"D) {options['D']}", callback_data="D")]
    ]

    await q.message.reply_text(ques, reply_markup=InlineKeyboardMarkup(keyboard))

# =========================
# BUTTONS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    u = user(uid)

    if q.data in ["A", "B", "C", "D"]:
        correct = context.user_data.get("answer")

        if q.data == correct:
            u["score"] += 1
            u["xp"] += 1
            await q.message.reply_text("✅ صح يا بطل")
        else:
            await q.message.reply_text(f"❌ غلط، الصح: {correct}")

        save(data)

    elif q.data == "quiz":
        await quiz(update, context)

    elif q.data == "ask":
        await q.message.reply_text("اكتب سؤالك 🤖")

    elif q.data == "score":
        await q.message.reply_text(f"🏆 Score: {u['score']} | ⭐ Level: {u['level']}")

# =========================
# CHAT HANDLER
# =========================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    if "اشرح" in text or "لخص" in text:
        reply = ai_chat(text)
        await update.message.reply_text(reply)
        return

    reply = ai_chat(text)
    await update.message.reply_text(reply)

# =========================
# RUN BOT
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

print("🔥 BOT RUNNING...")
app.run_polling()
