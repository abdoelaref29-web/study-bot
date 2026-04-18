import os
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DATA_FILE = "data.json"

# ================= SAVE =================
def load():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

users = load()

def get_user(uid, name):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"name": name, "xp": 0, "level": 1, "score": 0}
    return users[uid]

# ================= AI =================
def ai_text(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = {"contents":[{"parts":[{"text":prompt}]}]}

    try:
        res = requests.post(url, json=data).json()
        return res["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "❌ AI Error"

# ================= IMAGE =================
def ai_image(prompt):
    return f"https://image.pollinations.ai/prompt/{prompt}"

# ================= EXAM =================
def generate_exam(subject):
    prompt = f"""
اعمل امتحان {subject} 10 اسئلة اختيار من متعدد.
كل سؤال 4 اختيارات والإجابة الصحيحة.
"""

    text = ai_text(prompt)

    questions = []
    parts = text.split("سؤال")

    for p in parts[1:]:
        lines = p.split("\n")
        q = lines[0]

        opts = []
        ans = ""

        for l in lines:
            if l.startswith(("A","B","C","D")):
                opts.append(l)
            if "الإجابة" in l:
                ans = l.split(":")[-1].strip()

        if len(opts) == 4:
            questions.append((q, opts, ans))

    return questions

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 امتحان", callback_data="exam")],
        [InlineKeyboardButton("🤖 AI", callback_data="ai")],
        [InlineKeyboardButton("🖼️ صورة", callback_data="img")],
        [InlineKeyboardButton("🏆 الترتيب", callback_data="top")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 اختار:", reply_markup=menu())

# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    user = get_user(uid, q.from_user.first_name)

    if q.data == "exam":
        await q.message.reply_text("اكتب: امتحان + المادة")

    elif q.data == "ai":
        await q.message.reply_text("اسأل 🤖")

    elif q.data == "img":
        await q.message.reply_text("اكتب: لخصلي + الدرس")

    elif q.data == "top":
        top = sorted(users.values(), key=lambda x: x["xp"], reverse=True)[:5]

        text = "🏆 الأفضل:\n"
        for i, u in enumerate(top):
            text += f"{i+1}- {u['name']} | XP: {u['xp']}\n"

        await q.message.reply_text(text)

    elif q.data.startswith("ans_"):
        ans = q.data.split("_")[1]

        if ans == context.user_data["answer"]:
            user["xp"] += 2
            await q.message.reply_text("✅ صح")
        else:
            await q.message.reply_text(f"❌ غلط\nالصح: {context.user_data['answer']}")

        context.user_data["q"] += 1

        if context.user_data["q"] < len(context.user_data["exam"]):
            await send_q(q, context)
        else:
            user["level"] += 1
            await q.message.reply_text("🎉 خلصت الامتحان!")

        save(users)

# ================= SEND Q =================
async def send_q(q, context):
    i = context.user_data["q"]
    exam = context.user_data["exam"]

    ques, opts, ans = exam[i]
    context.user_data["answer"] = ans

    kb = []
    for o in opts:
        kb.append([InlineKeyboardButton(o, callback_data=f"ans_{o[0]}")])

    await q.message.reply_text(f"سؤال {i+1}:\n{ques}", reply_markup=InlineKeyboardMarkup(kb))

# ================= CHAT =================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.message.from_user.id)
    user = get_user(uid, update.message.from_user.first_name)

    # امتحان
    if "امتحان" in text:
        subject = text.replace("امتحان","").strip()

        await update.message.reply_text("⏳ جاري التحميل...")

        exam = generate_exam(subject)

        if not exam:
            await update.message.reply_text("❌ فشل الامتحان")
            return

        context.user_data["exam"] = exam
        context.user_data["q"] = 0

        await send_q(update, context)
        return

    # صورة
    if "لخصلي" in text:
        summary = ai_text(text)
        img = ai_image(summary)
        await update.message.reply_photo(img, caption="🖼️ ملخص")
        return

    # AI
    reply = ai_text(text)
    await update.message.reply_text(reply)

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

print("🔥 BOT RUNNING...")
app.run_polling()
