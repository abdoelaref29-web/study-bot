import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= AI =================
def ai_chat(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        res = requests.post(url, json=payload)
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("AI ERROR:", e)
        return ""

# ================= IMAGE =================
def generate_image(prompt):
    return f"https://image.pollinations.ai/prompt/{prompt}"

# ================= QUIZ =================
def generate_quiz(subject, num):
    prompt = f"""
    اعمل امتحان {subject} مكون من {num} اسئلة اختيار من متعدد.

    رجع JSON فقط بدون أي كلام:

    [
      {{
        "q": "السؤال",
        "options": ["A", "B", "C", "D"],
        "answer": "A"
      }}
    ]
    """

    response = ai_chat(prompt)

    try:
        data = json.loads(response)
        return data
    except:
        print("AI RESPONSE:", response)
        return None

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 امتحان", callback_data="exam")],
        [InlineKeyboardButton("🤖 AI", callback_data="ai")],
        [InlineKeyboardButton("🖼️ صورة", callback_data="img")],
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 اختار اللي عايزه", reply_markup=menu())

# ================= BUTTONS =================
async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "exam":
        await q.message.reply_text("اكتب مثلا: عايز امتحان كيميا 10 سؤال")

    elif q.data == "ai":
        await q.message.reply_text("اسأل أي حاجة 🤖")

    elif q.data == "img":
        await q.message.reply_text("اكتب: لخصلي درس ...")

# ================= SEND QUESTION =================
async def send_question(update, context):
    quiz = context.user_data.get("quiz")
    index = context.user_data.get("index", 0)

    if not quiz or index >= len(quiz):
        await update.message.reply_text("✅ خلصت الامتحان")
        return

    q = quiz[index]

    text = f"{q['q']}\n\n"
    for i, opt in enumerate(q["options"]):
        text += f"{chr(65+i)}) {opt}\n"

    await update.message.reply_text(text)

# ================= HANDLE MESSAGE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # 🎯 امتحان
    if "امتحان" in text:
        try:
            parts = text.split()
            subject = parts[2]
            num = int(parts[3])

            await update.message.reply_text("⏳ جاري التحميل...")

            quiz = generate_quiz(subject, num)

            if not quiz:
                await update.message.reply_text("❌ فشل الامتحان")
                return

            context.user_data["quiz"] = quiz
            context.user_data["index"] = 0

            await send_question(update, context)

        except:
            await update.message.reply_text("❌ اكتب صح: عايز امتحان كيميا 10 سؤال")

    # ▶️ التالي
    elif "التالي" in text:
        context.user_data["index"] += 1
        await send_question(update, context)

    # 🖼️ صورة
    elif "لخصلي" in text:
        summary = ai_chat(text)
        img = generate_image(summary)
        await update.message.reply_text(img)

    # 🤖 AI
    else:
        reply = ai_chat(text)
        await update.message.reply_text(reply if reply else "❌ AI مش شغال")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🔥 BOT RUNNING...")
app.run_polling()
