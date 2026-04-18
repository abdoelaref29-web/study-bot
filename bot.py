import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🏆 Leaderboard (في الرام)
leaderboard = {}

# ================= AI =================
def ai_chat(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, json=payload)
        data = res.json()

        if "error" in data:
            return "⚠️ AI Error"

        if "candidates" not in data:
            return ""

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except:
        return ""

# ================= QUIZ =================
def generate_quiz(subject, chapter, num):
    prompt = f"""
أنت مدرس خبير في مادة {subject} للثانوية العامة.

اعمل امتحان صعب جدًا من {num} أسئلة من الباب {chapter}.

- أسئلة تحليلية
- 4 اختيارات
- مستوى صعب

رجع JSON فقط:

[
  {{
    "q": "السؤال",
    "options": ["A", "B", "C", "D"],
    "answer": "A",
    "explanation": "شرح الإجابة"
  }}
]
"""
    res = ai_chat(prompt)

    try:
        start = res.find("[")
        end = res.rfind("]") + 1
        return json.loads(res[start:end])
    except:
        return None

# ================= LEVEL =================
def get_level(score, total):
    percent = (score / total) * 100

    if percent >= 80:
        return "🔥 ممتاز"
    elif percent >= 50:
        return "👍 متوسط"
    else:
        return "📚 محتاج مذاكرة"

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 أهلاً بيك في البوت التعليمي

🎯 اكتب:
امتحان كيمياء باب 1 5

🤖 أو اسأل أي سؤال طبيعي
""")

# ================= SEND QUESTION =================
async def send_question(chat_id, context):
    quiz = context.user_data["quiz"]
    index = context.user_data["index"]

    if index >= len(quiz):
        score = context.user_data["score"]
        total = len(quiz)

        level = get_level(score, total)

        user_id = chat_id
        leaderboard[user_id] = leaderboard.get(user_id, 0) + score

        await context.bot.send_message(
            chat_id,
            f"🏁 خلصت الامتحان\n\n"
            f"✅ النتيجة: {score}/{total}\n"
            f"📊 المستوى: {level}"
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
    quiz = context.user_data["quiz"]
    index = context.user_data["index"]

    question = quiz[index]
    correct = question["answer"]
    explanation = question["explanation"]

    if user_ans == correct:
        context.user_data["score"] += 1
        await q.message.reply_text(f"✅ صح\n💡 {explanation}")
    else:
        await q.message.reply_text(f"❌ غلط\n📌 الصح: {correct}\n💡 {explanation}")

    context.user_data["index"] += 1
    await send_question(q.message.chat_id, context)

# ================= HANDLER =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # 🎯 امتحان باب
    if "امتحان" in text:
        try:
            parts = text.split()

            subject = parts[1]
            chapter = parts[3]  # باب
            num = int(parts[4])

            await update.message.reply_text("⏳ جاري تجهيز الامتحان...")

            quiz = generate_quiz(subject, chapter, num)

            if not quiz:
                await update.message.reply_text("❌ خطأ في الامتحان")
                return

            context.user_data["quiz"] = quiz
            context.user_data["index"] = 0
            context.user_data["score"] = 0

            await send_question(update.message.chat_id, context)

        except:
            await update.message.reply_text("اكتب: امتحان كيمياء باب 1 5")

    # 🤖 AI
    else:
        result = ai_chat(text)
        await update.message.reply_text(result if result else "❌ AI مش شغال")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(answer, pattern="^[A-D]$"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🔥 BOT RUNNING...")
app.run_polling()
