
# === НАСТРОЙКИ ===
#TELEGRAM_TOKEN = "XXX"  # Замени
#HF_TOKEN = "YYY"    # Замени

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json
import time


# ✅ ПРАВИЛЬНЫЙ ID МОДЕЛИ
MODEL_ID = "IlyaGusev/saiga_mistral_7b"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}
dialogues = {}

# === 🔄 Запрос к API ===
def query(payload):
    for _ in range(10):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            print(f"🔹 Статус: {response.status_code}")
            print(f"🔹 Ответ: {response.text[:500]}...")

            # ✅ Успешный ответ
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON", "details": response.text}

            # ✅ Модель загружается — нормально!
            elif response.status_code == 503:
                try:
                    wait = response.json().get("estimated_time", 30)
                except:
                    wait = 30
                print(f"⏳ Модель загружается... ждём {wait} сек.")
                time.sleep(wait)
                continue

            # ❌ Другие ошибки
            else:
                try:
                    error = response.json().get("error", response.text)
                except:
                    error = response.text
                return {"error": f"HTTP {response.status_code}", "details": error}

        except Exception as e:
            print(f"🌐 Ошибка: {e}")
            time.sleep(10)
            continue

    return {"error": "Не удалось загрузить модель", "details": "Превышено количество попыток."}

# === 🤖 Команды бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    dialogues[chat_id] = []
    await update.message.reply_text(
        "🇷🇺 Привет! Я бот на модели Saiga-Mistral.\n"
        "Задай любой вопрос на русском!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    if chat_id not in dialogues:
        dialogues[chat_id] = []

    await update.message.reply_text("🧠 Думаю...")

    try:
        # Формируем промпт по шаблону Saiga
        prompt_lines = []
        for turn in dialogues[chat_id][-3:]:  # последние 3 обмена
            prompt_lines.append(f"### Условие: {turn['user']}")
            prompt_lines.append(f"### Ответ: {turn['bot']}")
        
        prompt_lines.append(f"### Условие: {user_message}")
        prompt_lines.append("### Ответ:")
        prompt = "\n".join(prompt_lines)

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False
            }
        }

        output = query(payload)

        if "error" in output:
            details = str(output.get("details", ""))
            if "currently loading" in details:
                bot_reply = "🤖 Модель загружается... Подождите 1–2 минуты и попробуйте снова."
            elif "authorization" in details.lower():
                bot_reply = "❌ Ошибка авторизации. Проверьте токен."
            else:
                bot_reply = f"❌ Ошибка: {output['error']}"
        elif isinstance(output, dict) and "generated_text" in output:
            bot_reply = output["generated_text"].strip()
        else:
            bot_reply = "❌ Не удалось получить ответ."

        dialogues[chat_id].append({"user": user_message, "bot": bot_reply})
        await update.message.reply_text(bot_reply)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        print("Ошибка:", e)

# === ▶️ Запуск ===
def main():
    print("🚀 Запуск Telegram-бота...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен. Первый запрос может занять 1–2 мин.")
    app.run_polling()

if __name__ == "__main__":

    main()
