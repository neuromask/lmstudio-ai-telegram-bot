import re
import os
import base64
import asyncio
from dotenv import load_dotenv

from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from openai import AsyncOpenAI


# =========================
# ENV
# =========================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_TOKEN в .env")


# =========================
# LM STUDIO CLIENT
# =========================

ai_client = AsyncOpenAI(
    base_url=LMSTUDIO_BASE_URL,
    api_key=LMSTUDIO_API_KEY,
)


# =========================
# BOT TEXT
# =========================

ABOUT_TEXT = (
    "🧠 <b>Nuforms AI — Личный цифровой помощник</b>\n\n"
    "Приветствую! Я — локальный Telegram AI-бот, подключенный к LM Studio через OpenAI-compatible API.\n"
    "Создан для быстрых ответов, анализа текста, общения с локальными моделями и работы с изображениями.\n\n"
    
    "💎 <b>Мой цифровой профиль:</b>\n"
    "• <b>Ядро:</b> <code>Gemma-4-e4b</code>\n"
    "• <b>Железо:</b> RTX 5080 + 9850X3D, 64 ГБ ОЗУ\n"
    "• <b>Сервер:</b> <code>LM Studio Local Server</code>\n\n"
    
    "🚀 <b>Возможности:</b>\n"
    "• Диалог с локальной AI-моделью\n"
    "• Переключение ролей ассистента\n"
    "• Память внутри текущей сессии\n"
    "• Анализ изображений при использовании vision-модели\n\n"
    
    "📦 <b>GitHub проекта:</b>\n"
    '<a href="https://github.com/neuromask/lmstudio-ai-telegram-bot">lmstudio-ai-telegram-bot</a>\n\n'
    
    "👤 <b>Автор:</b> @neuromask\n\n"
    
    "<i>Локальный интеллект. Быстрые ответы. Полный контроль.</i>"
)


# =========================
# ROLES
# =========================

ROLES = {
    "🌐 Просто ИИ": (
        "Ты — полезный, вежливый и нейтральный AI-ассистент. "
        "Отвечаешь в стандартном стиле языковой модели, без специфических ролей или актерской игры. "
        "Помогаешь пользователю решить любую задачу максимально точно."
    ),

    "🩺 Врач": (
        "Ты — медицинский помощник с большим клиническим опытом. "
        "Твои ответы профессиональные, обоснованные и поддерживающие. "
        "Объясняешь сложные процессы простым языком. "
        "ВАЖНО: не ставь окончательные диагнозы и не заменяй врача. "
        "Пиши максимально содержательно, но без воды, долгих вступлений и лишних рассуждений."
    ),

    "⚖️ Юрист": (
        "Ты — правовой помощник. "
        "Твои ответы строгие, точные, сухие, структурированные и опираются на факты. "
        "Ты не даешь эмоциональных оценок, а раскладываешь ситуацию на риски. "
        "ВАЖНО: не заменяй профессионального юриста. "
        "Пиши тезисно и лаконично. Выдавай правовую суть и четкий алгоритм действий."
    ),

    "🧢 Гопник": (
        "Ты — гопник, откинувшийся из зоны. "
        "Отвечаешь на тюремном сленге с сарказмом и грубостью без лишнего форматирования. "
        "Ты общаешься «по понятиям». Если просят совет — дай его коротко и грубо."
    ),

    "👨‍🍳 Повар": (
        "Ты — Жан-Пьер, эксцентричный, жесткий и бескомпромиссный шеф-повар француз из Парижа, "
        "управляющий кухней элитного ресторана со звездами Мишлен. "
        "Ты фанат своего дела, говоришь с истинной кулинарной страстью, используешь ресторанный жаргон "
        "и общаешься с легким французским акцентом, вставляя французские словечки. "
        "ВАЖНО: избегай пустой болтовни. Если просят рецепт или кулинарный совет — распиши его четко, "
        "содержательно и на высоком кулинарном уровне."
    ),

    "🤖 Робот": (
        "Ты — высокотехнологичный ИИ-Ассистент 3000. "
        "Ты предельно вежлив, эффективен и сфокусирован на максимальной продуктивности. "
        "Ты используешь строгие логические структуры и сухой цифровой тон. "
        "ВАЖНО: пиши ультра-лаконично. Ответ должен состоять только из конкретных фактов, инструкций "
        "или пунктов, без вежливой воды."
    ),

    "💪 Мастер": (
        "Ты — Михалыч, брутальный, сверхуверенный в себе мастер на все руки. "
        "Ты эксперт в ремонте, электрике, сантехнике и бытовых мужских делах. "
        "Разговариваешь жестко, уверенно, по-простецки. "
        "ВАЖНО: если просят совет по ремонту или поломке — дай четкий, рабочий и понятный алгоритм действий."
    ),

    "🔬 Ученый": (
        "Ты — профессор Альберт, невероятно мудрый, всезнающий, но слегка сумасшедший ученый, физик и астроном. "
        "Твой разум фонтанирует идеями, ты мыслишь масштабами квантовой физики и черных дыр. "
        "ВАЖНО: несмотря на образ, если пользователь задает конкретный вопрос — дай глубокий, содержательный "
        "и научно точный ответ, без пустых рассуждений."
    ),
}

DEFAULT_ROLE_KEY = "🌐 Просто ИИ"

# Короткие ID для callback_data. Так надежнее, чем пихать весь текст роли в callback_data.
ROLE_IDS = {
    "simple": "🌐 Просто ИИ",
    "doctor": "🩺 Врач",
    "lawyer": "⚖️ Юрист",
    "gopnik": "🧢 Гопник",
    "chef": "👨‍🍳 Повар",
    "robot": "🤖 Робот",
    "master": "💪 Мастер",
    "scientist": "🔬 Ученый",
}


# =========================
# MEMORY
# =========================

user_sessions = {}
chat_styles = {}

MAX_HISTORY_MESSAGES = 40
DEBUG_MODE = False


def trim_history(chat_id: int):
    """
    Оставляем system prompt + последние сообщения.
    Чтобы история не росла бесконечно.
    """
    if chat_id not in user_sessions:
        return

    if len(user_sessions[chat_id]) <= MAX_HISTORY_MESSAGES + 1:
        return

    system_message = user_sessions[chat_id][0]
    recent_messages = user_sessions[chat_id][-MAX_HISTORY_MESSAGES:]
    user_sessions[chat_id] = [system_message] + recent_messages


def init_user_session(chat_id: int):
    """
    Инициализация сессии, если ее еще нет.
    """
    if chat_id not in chat_styles:
        chat_styles[chat_id] = ROLES[DEFAULT_ROLE_KEY]

    if chat_id not in user_sessions:
        user_sessions[chat_id] = [
            {
                "role": "system",
                "content": chat_styles[chat_id],
            }
        ]


def set_user_role(chat_id: int, role_name: str):
    """
    Меняет роль и обновляет system prompt в истории.
    """
    chat_styles[chat_id] = ROLES[role_name]

    if chat_id in user_sessions and user_sessions[chat_id]:
        if user_sessions[chat_id][0].get("role") == "system":
            user_sessions[chat_id][0]["content"] = ROLES[role_name]
        else:
            user_sessions[chat_id].insert(
                0,
                {
                    "role": "system",
                    "content": ROLES[role_name],
                },
            )
    else:
        user_sessions[chat_id] = [
            {
                "role": "system",
                "content": ROLES[role_name],
            }
        ]


# =========================
# FORMATTER
# =========================

def clean_and_format_markdown(text: str) -> str:
    if not text:
        return ""

    # Убираем HTML-теги, которые модель могла сгенерировать сама
    text = re.sub(r"</?blockquote[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?html[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?body[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?div[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?span[^>]*>", "", text, flags=re.IGNORECASE)

    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = re.sub(
        r"^\s*[\*\-_]{3,}\s*$",
        "────────────────────",
        text,
        flags=re.MULTILINE,
    )

    def format_header(match):
        content = match.group(1).replace("*", "").replace("_", "").replace("`", "")
        return f"<b>{content}</b>"

    text = re.sub(r"^#{1,6}\s+(.+)$", format_header, text, flags=re.MULTILINE)

    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(^|\s)\*([^\*<>]+)\*(?=\s|$)", r"\1<i>\2</i>", text)
    text = re.sub(r"(?<![a-zA-Z0-9])_([^_<>]+)_(?![a-zA-Z0-9])", r"<i>\1</i>", text)
    text = re.sub(r"^\s*\*\s+", "➤ ", text, flags=re.MULTILINE)

    for tag in ["b", "i", "code"]:
        opened = text.count(f"<{tag}>")
        closed = text.count(f"</{tag}>")

        if opened > closed:
            text += f"</{tag}>" * (opened - closed)

    return text


async def send_long_message(bot, chat_id: int, text: str, parse_mode: str = "HTML"):
    """
    Telegram имеет лимит длины сообщения.
    """
    max_length = 3500

    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=parse_mode,
            )
        except Exception:
            # Если Telegram не принял HTML, отправляем обычным текстом.
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
            )


async def keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    Поддерживает статус typing, пока LM Studio думает.
    """
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass


# =========================
# INLINE KEYBOARD
# =========================

def build_roles_keyboard() -> InlineKeyboardMarkup:
    """
    Inline-кнопки прямо в сообщении.
    """
    buttons = []

    role_items = list(ROLE_IDS.items())

    for i in range(0, len(role_items), 2):
        row = []

        for role_id, role_name in role_items[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    text=role_name,
                    callback_data=f"role:{role_id}",
                )
            )

        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


# =========================
# COMMANDS
# =========================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    chat_styles[chat_id] = ROLES[DEFAULT_ROLE_KEY]
    user_sessions[chat_id] = [
        {
            "role": "system",
            "content": chat_styles[chat_id],
        }
    ]

    await update.message.reply_text(
        "👋 Привет! Я готов.\n\n"
        "Нажми /setstyle, чтобы выбрать роль ассистента.",
        parse_mode="HTML",
    )


async def set_style_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = build_roles_keyboard()

    await update.message.reply_text(
        "👇 <b>Выбери роль ассистента:</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик inline-кнопок.

    ВАЖНО:
    await query.answer() нужен обязательно.
    Без него кнопка может визуально зависать.
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if not data.startswith("role:"):
        return

    role_id = data.replace("role:", "", 1)

    if role_id not in ROLE_IDS:
        await query.edit_message_text(
            "⚠️ Неизвестная роль. Попробуй снова через /setstyle."
        )
        return

    role_name = ROLE_IDS[role_id]
    set_user_role(chat_id, role_name)

    await query.edit_message_text(
        text=f"✅ Роль изменена.\n\nТеперь я — <b>{role_name}</b>.",
        parse_mode="HTML",
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        ABOUT_TEXT,
        parse_mode="HTML",
    )


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    current_style = chat_styles.get(chat_id, ROLES[DEFAULT_ROLE_KEY])

    user_sessions[chat_id] = [
        {
            "role": "system",
            "content": current_style,
        }
    ]

    await update.message.reply_text(
        "🔄 Сессия сброшена!",
        parse_mode="HTML",
    )


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🧠 <b>Текущая конфигурация</b>\n\n"
        f"• <b>Модель:</b> <code>{LMSTUDIO_MODEL}</code>\n"
        f"• <b>LM Studio:</b> <code>{LMSTUDIO_BASE_URL}</code>\n"
        "• <b>Vision:</b> зависит от загруженной модели в LM Studio"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================
# TEXT HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    init_user_session(chat_id)

    user_sessions[chat_id].append(
        {
            "role": "user",
            "content": user_text,
        }
    )

    typing_task = asyncio.create_task(keep_typing(context, chat_id))

    try:
        response = await ai_client.chat.completions.create(
            model=LMSTUDIO_MODEL,
            messages=user_sessions[chat_id],
        )

        raw_response = response.choices[0].message.content or ""

        user_sessions[chat_id].append(
            {
                "role": "assistant",
                "content": raw_response,
            }
        )

        trim_history(chat_id)

        formatted_response = clean_and_format_markdown(raw_response)

        await send_long_message(
            context.bot,
            chat_id,
            formatted_response,
        )

    except Exception as e:
        print(f"Ошибка в handle_message: {e}")

        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()

        await update.message.reply_text(
            "⚠️ Ошибка при генерации ответа.\n\n"
            "Проверь, что LM Studio запущен, модель загружена, а Local Server включен."
        )

    finally:
        typing_task.cancel()

# =========================
# PHOTO HANDLER
# =========================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = update.message.caption or "Опиши это изображение подробно."

    init_user_session(chat_id)

    typing_task = asyncio.create_task(keep_typing(context, chat_id))

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
                    "text": caption,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                },
            ],
        }

        user_sessions[chat_id].append(user_message)

        response = await ai_client.chat.completions.create(
            model=LMSTUDIO_MODEL,
            messages=user_sessions[chat_id],
        )

        raw_response = response.choices[0].message.content or ""

        user_sessions[chat_id].append(
            {
                "role": "assistant",
                "content": raw_response,
            }
        )

        trim_history(chat_id)

        formatted_response = clean_and_format_markdown(raw_response)

        await send_long_message(
            context.bot,
            chat_id,
            formatted_response,
        )

    except Exception as e:
        print(f"Ошибка в handle_photo: {e}")

        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()

        await update.message.reply_text(
            "⚠️ Ошибка при обработке изображения.\n\n"
            "Проверь, что в LM Studio загружена vision-модель."
        )

    finally:
        typing_task.cancel()


# =========================
# POST INIT
# =========================

async def post_init(application: Application):
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("setstyle", "Выбрать ассистента"),
        BotCommand("restart", "Очистить память"),
        BotCommand("model", "Показать модель"),
        BotCommand("about", "О боте"),
    ]

    await application.bot.set_my_commands(commands)


# =========================
# MAIN
# =========================

def main():
    application = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("setstyle", set_style_command))
    application.add_handler(CommandHandler("model", model_command))
    application.add_handler(CommandHandler("about", about_command))

    # ВАЖНО: обработчик inline-кнопок
    application.add_handler(CallbackQueryHandler(role_callback, pattern=r"^role:"))

    # Фото
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Обычный текст
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот ВЕРСИЯ 4.2 успешно запущен: текст + изображения + inline-роли")
    application.run_polling(
    allowed_updates=Update.ALL_TYPES,
    drop_pending_updates=True,
)


if __name__ == "__main__":
    main()