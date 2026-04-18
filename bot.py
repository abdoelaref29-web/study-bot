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
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, json=payload)
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return ""

# ================= CLEAN JSON =================
def clean_json(text):
    text = text.strip()

    if "```" in text:
        text = text.split("```")[1]

    start = text.find("[")
    end = text.rfind("]") + 1
    return text[start:end]

# ================= QUIZ =================
def generate_quiz(subject, num):
    prompt = f"""
    اعمل امتحان {subject} مكون من {num} اسئلة اختيار من متعدد.

    رجع JSON فقط بالشكل ده:
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
        cleaned = clean_json(response)
        return json.loads(cleaned)
    except:
        print("AI RESPONSE:", response)
        return None

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 امتحان", callback_data="exam")],
        [InlineKeyboardButton("🤖 AI", callback_data="ai")],
        [InlineKeyboardButton("🖼️ صورة", callback_data="img")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 اختار:", reply_markup=menu())

# ================= SEND QUESTION =================
async def send_question(chat_id, context):
    quiz = context.user_data.get("quiz")
    index = context.user_data.get("index", 0)

    if index >= len(quiz):
        score = context.user_data.get("score", 0)
        await context.bot.send_message(chat_id, f"🏁 خلصت الامتحان\n✅ نتيجتك: {score}/{len(quiz)}")
        return

    q = quiz[index]

    buttons = [
        [InlineKeyboardButton(f"A) {q['options'][0]}", callback_data="A")],
        [InlineKeyboardButton(f"B) {q['options'][1]}", callback_data="B")],
        [InlineKeyboardButton(f"C) {q['options'][2]}", callback_data="C")],
        [InlineKeyboardButton(f"D) {q['options'][3]}", callback_data="D")]
    ]

    await context.bot.send_message(
        chat_id,
        f"❓ {q['q']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= HANDLE ANSWER =================
async def answer(update, context):
    q = update.callback_query
    await q.answer()

    user_ans = q.data
    quiz = context.user_data.get("quiz")
    index = context.user_data.get("index", 0)

    correct = quiz[index]["answer"]

    if user_ans == correct:
        context.user_data["score"] += 1
        await q.message.reply_text("✅ صح")
    else:
        await q.message.reply_text(f"❌ غلط - الصح: {correct}")

    context.user_data["index"] += 1
    await send_question(q.message.chat_id, context)

# ================= BUTTONS =================
async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "exam":
        await q.message.reply_text("اكتب: عايز امتحان كيميا 5")

    elif q.data == "ai":
        await q.message.reply_text("اسأل أي حاجة 🤖")

    elif q.data == "img":
        await q.message.reply_text("اكتب: لخصلي درس ...")

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
            context.user_data["score"] = 0

            await send_question(update.message.chat_id, context)

        except:
            await update.message.reply_text("❌ اكتب صح: عايز امتحان كيميا 5")

    # 🖼️ صورة
    elif "لخصلي" in text:
        summary = ai_chat(text)
        img = f"https://image.pollinations.ai/prompt/{summary}"
        await update.message.reply_text(img)

    # 🤖 AI
    else:
        reply = ai_chat(text)
        await update.message.reply_text(reply if reply else "❌ AI مش شغال")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(answer, pattern="^[A-D]$"))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🔥 BOT RUNNING...")
app.run_polling()
