import os
import io
import numpy as np
from PIL import Image, ImageChops, ImageStat, ExifTags
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.getenv("8493347343:AAGWKhKzFduPfQjmZLwoJ3giMvuc90oPaBc
")

# --------------------------
#   FORENSIC FUNCTIONS
# --------------------------

def extract_exif(img):
    try:
        exif_data = img._getexif()
        if not exif_data:
            return "❌ EXIF отсутствует — часто признак AI-изображения."

        readable = {}
        for tag, value in exif_data.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            readable[decoded] = value

        hints = []
        if "Software" in readable:
            sw = str(readable["Software"]).lower()
            if any(x in sw for x in ["midjourney", "diffusion", "ai", "stable", "generated"]):
                hints.append("⚠️ ПО софта указывает на генерацию нейросетью.")

        if not hints:
            hints.append("✔ EXIF выглядит естественно.")

        return "\n".join(hints) + "\n\n" + str(readable)

    except:
        return "❌ Ошибка чтения EXIF — возможно, файл был сильно изменён."

def error_level_analysis(img):
    temp = io.BytesIO()
    img.save(temp, "JPEG", quality=90)
    temp.seek(0)
    recompressed = Image.open(temp)
    diff = ImageChops.difference(img, recompressed)
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / len(stat.mean)
    return mean  # выше — больше артефактов

def noise_level(img):
    gray = img.convert("L")
    arr = np.array(gray)
    return float(np.std(arr))

# --------------------------
#   BOT LOGIC
# --------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я Inspector ADF.\n"
        "Отправь фото — я выполню forensic-анализ: EXIF, шумы, ELA.\n"
        "Помогу определить, было ли фото создано или изменено нейросетью."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Фото получено. Выполняю анализ…")

    file = await update.message.photo[-1].get_file()
    data = await file.download_as_bytearray()

    img = Image.open(io.BytesIO(data)).convert("RGB")

    # Анализ
    exif_res = extract_exif(img)
    noise = noise_level(img)
    ela = error_level_analysis(img)

    # Оценка вероятности AI
    score = 0

    if "подозр" in exif_res.lower() or "ai" in exif_res.lower():
        score += 0.4
    if noise < 8:
        score += 0.3
    if ela > 20:
        score += 0.3

    if score < 0.3:
        verdict = "✔ Низкая вероятность AI."
    elif score < 0.6:
        verdict = "⚠️ Есть подозрения на AI."
    else:
        verdict = "❌ Высокая вероятность AI-генерации."

    result = (
        "🧾 *Inspector ADF — Forensic Report*\n\n"
        f"EXIF:\n{exif_res}\n\n"
        f"📉 Noise Level: {noise:.2f}\n"
        f"📊 ELA Score: {ela:.2f}\n\n"
        f"🔎 *Вердикт:* {verdict}"
    )

    await update.message.reply_text(result, parse_mode="Markdown")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.run_polling()
