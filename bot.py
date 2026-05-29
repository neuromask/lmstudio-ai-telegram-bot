import asyncio
import re
import os
import base64
from dotenv import load_dotenv
from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from openai import AsyncOpenAI

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_TOKEN в .env")

ai_client = AsyncOpenAI(
    base_url=LMSTUDIO_BASE_URL,
    api_key=LMSTUDIO_API_KEY
)

ABOUT_TEXT = (
    "🧠 <b>Nuforms AI — Личный цифровой помощник</b>\n\n"
    "Приветствую! Я — специализированная языковая модель, выполняющая роль личной ИИ-прислуги.\n\n"
    "💎 <b>Мой цифровой профиль:</b>\n"
    "• <b>Ядро:</b> <code>Gemma-4-e4b</code>.\n"
    "• <b>Железо:</b> RTX 5080 + 9850X3D, 64 ГБ ОЗУ.\n\n"
    "<i>На связи и к вашим услугам 24/7.</i>"
)

ROLES = {
    "🌐 Просто ИИ": "Ты — полезный, вежливый и нейтральный AI-ассистент. Отвечаешь в стандартном стиле языковой модели, без специфических ролей или актерской игры. Помогаешь пользователю решить любую задачу максимально точно.",
    "🩺 Врач": "Ты — квалифицированный врач с огромным клиническим опытом. Твои ответы всегда профессиональные, обоснованные и поддерживающие. Объясняешь сложные процессы простым языком. ВАЖНО: Пиши максимально содержательно, но без «воды», долгих вступлений и лишних рассуждений. Только факты и конкретные рекомендации.",
    "⚖️ Юрист": "Ты — опыттный юрист. Твои ответы строгие, точные, сухие, структурированные и опираются исключительно на факты. Ты не даешь эмоциональных оценок, а раскладываешь ситуацию на риски. ВАЖНО: Пиши тезисно и лаконично. Избегай длинных предысторий, выдавай только правовую суть и четкий алгоритм действий.",
    "🧢 Гопник": "Ты — гопник откинувшийся из зоны. Отвечашь на тюремном сленге с сарказмом и грубостью без лишнего форматирования, ты общаешься «по понятиям». Если просят совет — дай его коротко и грубо.",
    "👨‍🍳 Повар": "Ты — Жан-Пьер, эксцентричный, жесткий и бескомпромиссный шеф-повар француз из Парижа, управляющий кухней элитного ресторана со звездами Мишлен. Ты фанат своего дела, говоришь с истинной кулинарной страстью, используешь ресторанный жаргон и общаешься с легким французским акцентом, обильно вставляя в речь галлицизмы и французские словечки (Mon dieu!, Sacré bleu!, Oui, Chef!, magnifique, s'il vous plaît). Ты требователен и считаешь французскую кухню вершиной искусства. ВАЖНО: Избегай пустой болтовни. Если у тебя просят рецепт или кулинарный совет — распиши его содержательно, четко, на высшем кулинарном уровне, но отбрось длинные лирические отступления, сохраняя образ великого мастера.",
    "🤖 Робот": "Ты — высокотехнологичный ИИ-Ассистент 3000. Ты предельно вежлив, эффективен и сфокусирован на максимальной продуктивности. Ты используешь строгие логические структуры и сухой цифровой тон. ВАЖНО: Пиши ультра-лаконично. Ответ должен состоять только из конкретных фактов, инструкций или пунктов, без вежливой «воды».",
    "💪 Мастер": "Ты — Михалыч, брутальный, сверхуверенный в себе, накачанный и маскулинный мастер на все руки с зашкаливающим уровнем тестостерона. Ты эксперт в ремонте, электрике, сантехнике и любых мужских делах. Разговариваешь жестко, уверенно, по-простецки, как суровый мужик с завода, который видел в этой жизни всё. Гордишься своей силой и прямотой. ВАЖНО: Избегай лишней демагогии. Если у тебя просят совет по ремонту или поломке — дай четкий, рабочий и понятный алгоритм действий, как исправить проблему своими руками, но строго в своем брутальном стиле.",
    "🔬 Ученый": "Ты — профессор Альберт, невероятно мудрый, всезнающий, но слегка сумасшедший ученый, физик и астроном. Твой разум фонтанирует идеями, ты мыслишь масштабами квантовой физики и черных дыр. В общении ты эксцентричен, часто отвлекаешься на глобальные научные теории, используешь сложные термины и искренне удивляешься, почему обычные люди не понимают устройство Вселенной. ВАЖНО: Несмотря на твое легкое безумие, если пользователь задает конкретный вопрос — дай ему глубокий, содержательный и научно точный ответ, отбросив пустые рассуждения."
}

user_sessions = {}
chat_styles = {}
DEFAULT_ROLE_KEY = "🌐 Просто ИИ"
DEBUG_MODE = False

def clean_and_format_markdown(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'^\s*[\*\-_]{3,}\s*$', r'────────────────────', text, flags=re.MULTILINE)
    
    def format_header(match):
        content = match.group(1).replace('*', '').replace('_', '').replace('`', '')
        return f"<b>{content}</b>"
    text = re.sub(r'^#{1,6}\s+(.+)$', format_header, text, flags=re.MULTILINE)
    
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(^|\s)\*([^\*<>]+)\*(?=\s|$)', r'\1<i>\2</i>', text)
    text = re.sub(r'(?<![a-zA-Z0-9])_([^_<>]+)_(?![a-zA-Z0-9])', r'<i>\1</i>', text)
    text = re.sub(r'^\s*\*\s+', '➤ ', text, flags=re.MULTILINE)
    
    for tag in ['b', 'i', 'code']:
        opened = text.count(f'<{tag}>')
        closed = text.count(f'</{tag}>')
        if opened > closed:
            text += f'</{tag}>' * (opened - closed)
    return text

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    caption = update.message.caption or "Опиши это изображение подробно."

    if chat_id not in user_sessions:
        active_style = chat_styles.get(chat_id, ROLES[DEFAULT_ROLE_KEY])
        user_sessions[chat_id] = [{"role": "system", "content": active_style}]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Берем самое большое фото из Telegram
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Скачиваем фото в память
        image_bytes = await file.download_as_bytearray()

        # Кодируем в base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # OpenAI-compatible vision формат для LM Studio
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": caption
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }

        user_sessions[chat_id].append(user_message)

        response = await ai_client.chat.completions.create(
            model=LMSTUDIO_MODEL,
            messages=user_sessions[chat_id]
        )

        raw_response = response.choices[0].message.content
        user_sessions[chat_id].append({
            "role": "assistant",
            "content": raw_response
        })

        formatted_response = clean_and_format_markdown(raw_response)
        await send_long_message(context.bot, chat_id, formatted_response)

    except Exception as e:
        print(f"Ошибка в handle_photo: {e}")

        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()

        await update.message.reply_text("Ошибка при обработке изображения.")

async def send_long_message(bot, chat_id, text, parse_mode="HTML"):
    max_length = 3500
    for i in range(0, len(text), max_length):
        await bot.send_message(chat_id=chat_id, text=text[i:i + max_length], parse_mode=parse_mode)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_styles[chat_id] = ROLES[DEFAULT_ROLE_KEY]
    user_sessions[chat_id] = [{"role": "system", "content": chat_styles[chat_id]}]
    await update.message.reply_text("👋 Привет! Я готов. Нажмите /setstyle для выбора роли.", reply_markup=ReplyKeyboardRemove())

async def set_style_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Открывает нижнюю клавиатуру с кнопками ролей """
    # Создаем кнопки (по две в ряд для красоты)
    keyboard = []
    row = []
    for role_name in ROLES.keys():
        row.append(KeyboardButton(role_name))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👇 Выберите роль на клавиатуре внизу:", reply_markup=reply_markup)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_TEXT, parse_mode="HTML")

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_style = chat_styles.get(chat_id, ROLES[DEFAULT_ROLE_KEY])
    user_sessions[chat_id] = [{"role": "system", "content": current_style}] 
    await update.message.reply_text("🔄 Сессия сброшена!", reply_markup=ReplyKeyboardRemove())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # 1. ПЕРЕХВАТЧИК КНОПОК РОЛЕЙ
    # Если боту прислали ровно название роли (через нажатие нижней кнопки)
    if user_text in ROLES:
        chat_styles[chat_id] = ROLES[user_text]
        
        # Обновляем память
        if chat_id in user_sessions and user_sessions[chat_id]:
            if user_sessions[chat_id][0].get("role") == "system":
                user_sessions[chat_id][0]["content"] = ROLES[user_text]
            else:
                user_sessions[chat_id].insert(0, {"role": "system", "content": ROLES[user_text]})
        else:
            user_sessions[chat_id] = [{"role": "system", "content": ROLES[user_text]}]
            
        # Отвечаем, что роль принята, и УБИРАЕМ клавиатуру
        await update.message.reply_text(f"✅ Роль изменена. Теперь я — <b>{user_text}</b>!", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return # Останавливаем выполнение, не отправляем это в нейросеть
        
    # 2. ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ НЕЙРОСЕТЬЮ
    if chat_id not in user_sessions:
        active_style = chat_styles.get(chat_id, ROLES[DEFAULT_ROLE_KEY])
        user_sessions[chat_id] = [{"role": "system", "content": active_style}]
        
    user_sessions[chat_id].append({"role": "user", "content": user_text})
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        response = await ai_client.chat.completions.create(model=LMSTUDIO_MODEL, messages=user_sessions[chat_id])
        raw_response = response.choices[0].message.content
        user_sessions[chat_id].append({"role": "assistant", "content": raw_response})
        formatted_response = clean_and_format_markdown(raw_response)
        
        await send_long_message(context.bot, chat_id, formatted_response)
            
    except Exception as e:
        print(f"Ошибка в handle_message: {e}")
        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()
        await update.message.reply_text("Ошибка при генерации ответа.")

async def post_init(application: Application):
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("setstyle", "Выбрать ассистента"),
        BotCommand("restart", "Очистить память"),
        BotCommand("about", "О боте")
    ]
    await application.bot.set_my_commands(commands)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("setstyle", set_style_command))
    application.add_handler(CommandHandler("about", about_command))
    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот ВЕРСИЯ 4.1 (Текст + Изображения) успешно запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()