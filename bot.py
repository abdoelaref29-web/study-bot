import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================= AI =================
def ai_chat(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()

        print("GEMINI RESPONSE:", data)

        if "error" in data:
            return ""

        if "candidates" not in data:
            return ""

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("AI ERROR:", e)
        return ""

# ================= CLEAN JSON =================
def clean_json(text):
    try:
        text = text.strip()

        if "```" in text:
            text = text.split("```")[1]

        start = text.find("[")
        end = text.rfind("]") + 1

        return text[start:end]
    except:
        return "[]"

# ================= QUIZ =================
def generate_quiz(subject, num):
    prompt = f"""
أنت مدرس خبير في مادة {subject} للثانوية العامة.

اعمل امتحان صعب جدًا مكون من {num} أسئلة اختيار من متعدد.

- الأسئلة تحليلية
- 4 اختيارات
- مستوى صعب

رجع JSON فقط بدون أي كلام:

[
  {{
    "q": "السؤال",
    "options": ["A", "B", "C", "D"],
    "answer": "A",
    "explanation": "شرح الإجابة"
  }}
]
"""

    response = ai_chat(prompt)

    if not response:
        return None

    try:
        cleaned = clean_json(response)
        return json.loads(cleaned)
    except Exception as e:
        print("QUIZ ERROR:", e)
        print("RAW:", response)
        return None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 أهلاً بيك

🎯 اكتب:
امتحان كيمياء 5

🤖 أو اسأل أي سؤال طبيعي
""")

# ================= SEND QUESTION =================
async def send_question(chat_id, context):
    quiz = context.user_data.get("quiz", [])
    index = context.user_data.get("index", 0)

    if index >= len(quiz):
        score = context.user_data.get("score", 0)

        await context.bot.send_message(
            chat_id,
            f"🏁 خلصت الامتحان\n\n✅ نتيجتك: {score}/{len(quiz)}"
        )
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

# ================= ANSWER =================
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_ans = q.data
    quiz = context.user_data.get("quiz", [])
    index = context.user_data.get("index", 0)

    question = quiz[index]
    correct = question.get("answer", "")
    explanation = question.get("explanation", "")

    if user_ans == correct:
        context.user_data["score"] += 1
        await q.message.reply_text(f"✅ صح 🎉\n💡 {explanation}")
    else:
        await q.message.reply_text(f"❌ غلط\n📌 الصح: {correct}\n💡 {explanation}")

    context.user_data["index"] += 1
    await send_question(q.message.chat_id, context)

# ================= HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # 🎯 امتحان
    if "امتحان" in text:
        try:
            parts = text.split()

            subject = parts[1]
            num = int(parts[2])

            await update.message.reply_text("⏳ جاري تجهيز الامتحان...")

            quiz = generate_quiz(subject, num)

            if not quiz:
                await update.message.reply_text("❌ فشل في إنشاء الامتحان")
                return

            context.user_data["quiz"] = quiz
            context.user_data["index"] = 0
            context.user_data["score"] = 0

            await send_question(update.message.chat_id, context)

        except:
            await update.message.reply_text("اكتب: امتحان كيمياء 5")

    # 🤖 AI
    else:
        result = ai_chat(text)

        if result:
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("❌ حصل خطأ في AI")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(answer, pattern="^[A-D]$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🔥 BOT RUNNING...")
app.run_polling()
