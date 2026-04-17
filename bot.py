import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# =========================
# KEYS
# =========================
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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
# AI (حل نهائي)
# =========================
def ai_chat(prompt):
    if not GEMINI_API_KEY:
        return "❌ مفيش API KEY"

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, json=payload)
        data = res.json()

        # لو فيه error من Google
        if "error" in data:
            return f"❌ AI Error:\n{data['error']['message']}"

        # لو مفيش candidates
        if "candidates" not in data:
            return f"❌ AI Unexpected Response:\n{data}"

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        return f"❌ خطأ في AI: {e}"

# =========================
# IMAGE
# =========================
def generate_image(prompt):
    return f"https://image.pollinations.ai/prompt/{prompt}"

# =========================
# QUESTION
# =========================
def question():
    return (
        "ما وظيفة الميتوكوندريا؟",
        {
            "A": "تخزين الماء",
            "B": "إنتاج الطاقة",
            "C": "الحماية",
            "D": "النقل"
        },
        "B"
    )

# =========================
# MENU
# =========================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 كويز", callback_data="quiz")],
        [InlineKeyboardButton("🤖 اسأل AI", callback_data="ask")],
        [InlineKeyboardButton("📖 شرح درس", callback_data="lesson")],
        [InlineKeyboardButton("🖼️ لخص في صورة", callback_data="imgsum")],
        [InlineKeyboardButton("🏆 نتيجتي", callback_data="score")]
    ])

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user(uid)
    save(data)

    await update.message.reply_text("🔥 أهلاً بيك يا بطل", reply_markup=menu())

# =========================
# QUIZ
# =========================
async def quiz(update, context):
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
async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    u = user(uid)

    data_btn = q.data

    if data_btn in ["A", "B", "C", "D"]:
        correct = context.user_data.get("answer")

        if data_btn == correct:
            u["score"] += 1
            u["xp"] += 1

            if u["xp"] % 5 == 0:
                u["level"] += 1
                await q.message.reply_text("🔥 Level Up!")

            await q.message.reply_text("✅ صح يا وحش")
        else:
            await q.message.reply_text(f"❌ غلط، الصح: {correct}")

        save(data)

    elif data_btn == "quiz":
        await quiz(update, context)

    elif data_btn == "lesson":
        await q.message.reply_text("اكتب: اشرح + اسم الدرس")

    elif data_btn == "ask":
        await q.message.reply_text("اسأل أي حاجة 🤖")

    elif data_btn == "imgsum":
        await q.message.reply_text("اكتب: لخصلي درس ...")

    elif data_btn == "score":
        await q.message.reply_text(f"🏆 Score: {u['score']} | ⭐ Level: {u['level']}")

# =========================
# CHAT
# =========================
async def check(update, context):
    text = update.message.text

    if "بوت" in text:
        await update.message.reply_text("أنا معاك 💪")
        return

    if "اشرح" in text:
        reply = ai_chat(text)
        await update.message.reply_text(reply)
        return

    if "لخصلي" in text:
        summary = ai_chat(text)
        img = generate_image(summary)
        await update.message.reply_text(img)
        return

    reply = ai_chat(text)
    await update.message.reply_text(reply)

# =========================
# RUN
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check))

print("🔥 BOT RUNNING...")
app.run_polling()
