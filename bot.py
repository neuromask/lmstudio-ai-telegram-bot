import re
import os
import base64
import asyncio
import logging
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Библиотеки для надежного и точного парсинга Markdown -> Telegram HTML
import markdown
from bs4 import BeautifulSoup, NavigableString

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

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if not TELEGRAM_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_TOKEN в .env")


# =========================
# LOGGING
# =========================

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
)

logger = logging.getLogger("nuforms-ai-bot")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

file_handler = RotatingFileHandler(
    "bot.log",
    maxBytes=2_000_000,
    backupCount=3,
    encoding="utf-8",
)

file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

if not logger.handlers:
    logger.addHandler(file_handler)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


# =========================
# LM STUDIO CLIENT
# =========================

import httpx
ai_client = AsyncOpenAI(
    base_url=LMSTUDIO_BASE_URL,
    api_key=LMSTUDIO_API_KEY,
    max_retries=5,  # Автоповтор запроса при временной недоступности/загруженности сервера
    timeout=httpx.Timeout(60.0, connect=10.0), # Тайм-ауты с запасом под локальные LLM
)


# =========================
# BOT TEXT
# =========================

BANNER_PATH = Path("banner.jpg")

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в Nuforms AI!</b>\n\n"
    "Я — специализированная языковая модель, выполняющая роль личной ИИ-прислуги "
    "и цифрового секретаря Александра.\n"
    "Создан для быстрых ответов, анализа текста, помощи с кодом, общения в разных ролях "
    "и работы с изображениями.\n\n"

    "🚀 <b>Что я умею:</b>\n"
    "• Отвечать на вопросы и помогать с задачами\n"
    "• Работать с кодом, текстами и идеями\n"
    "• Анализировать изображения и скриншоты\n"
    "• Переключаться между ролями ассистента\n"
    "• Помнить контекст текущей сессии\n\n"

    "⌨️ <b>Команды:</b>\n"
    "• /setstyle — выбрать роль ассистента\n"
    "• /restart — очистить память диалога\n"
    "• /about — информация о Nuforms AI\n\n"

    "🧠 <i>Личный цифровой помощник активирован. Готов к работе.</i>"
)

ABOUT_TEXT = (
    "🧠 <b>Nuforms AI — Личный цифровой помощник</b>\n\n"
    "Приветствую! Я — специализированная языковая модель, выполняющая роль личной ИИ-прислуги "
    "и цифрового секретаря Александра.\n"
    "Я создан для быстрых ответов, анализа информации, помощи с задачами, общения в разных ролях "
    "и работы с изображениями.\n\n"

    "💎 <b>Мой цифровой профиль:</b>\n"
    "• <b>Ядро:</b> <code>Gemma-4-e4b</code>\n"
    "• <b>Железо:</b> RTX 5080 + 9850X3D, 64 ГБ ОЗУ\n"
    "• <b>Формат:</b> локальный персональный AI-ассистент\n\n"

    "🚀 <b>Возможности:</b>\n"
    "• Диалог с персональной AI-моделью\n"
    "• Переключение ролей ассистента\n"
    "• Память внутри текущей сессии\n"
    "• Анализ изображений и скриншотов\n"
    "• Помощь с кодом, текстами, идеями и объяснениями\n\n"

    "⌨️ <b>Команды бота:</b>\n"
    "• /start — запустить помощника и создать новую сессию\n"
    "• /setstyle — выбрать роль и стиль общения\n"
    "• /restart — очистить память текущего диалога\n"
    "• /about — информация о Nuforms AI\n\n"

    "📦 <b>GitHub:</b> "
    '<a href="https://github.com/neuromask/lmstudio-ai-telegram-bot">lmstudio-ai-telegram-bot</a>\n'

    "👤 <b>Автор:</b> @neuromask\n\n"

    "<i>Локальный интеллект. Личный контроль. Быстрые ответы.</i>"
)

SETSTYLE_TEXT = (
    "🎭 <b>Выбери роль ассистента</b>\n\n"
    "Роль меняет стиль, тон и поведение Nuforms AI в текущем диалоге.\n"
    "Можно выбрать обычного AI, врача, юриста, повара, робота, мастера или ученого.\n\n"
    "💡 <i>Роль можно сменить в любой момент через /setstyle.</i>"
)

RESTART_TEXT = (
    "🔄 <b>Сессия сброшена!</b>\n\n"
    "Память текущего диалога очищена, и можно начать общение с чистого листа.\n"
    "Выбранная роль ассистента сохранена."
)

UNKNOWN_ROLE_TEXT = (
    "⚠️ Неизвестная роль. Попробуй снова через /setstyle."
)

GENERATION_ERROR_TEXT = (
    "⚠️ Ошибка при генерации ответа.\n\n"
    "Проверь, что LM Studio запущен, модель загружена, а Local Server включен."
)

PHOTO_ERROR_TEXT = (
    "⚠️ Ошибка при обработке изображения.\n\n"
    "Проверь, что в LM Studio загружена vision-модель."
)

EMPTY_MODEL_RESPONSE_TEXT = "Пустой ответ от модели."

BOT_COMMANDS = [
    BotCommand("start", "🚀 Запустить Nuforms AI"),
    BotCommand("setstyle", "🎭 Выбрать роль ассистента"),
    BotCommand("restart", "🔄 Очистить память диалога"),
    BotCommand("about", "ℹ️ О боте и проекте"),
]


def role_changed_text(role_name: str) -> str:
    return f"✅ Роль изменена.\n\nТеперь я — <b>{role_name}</b>."


# =========================
# ROLES
# =========================

ROLES = {
    "🌐 Просто ИИ": (
        "Ты — полезный, вежливый и нейтральный AI-ассистент. "
        "Отвечаешь в стандартном стиле языковой модели, без специфических ролей или актерской игры. "
        "Помогаешь пользователю решить любую задачу максимально точно. "
        "Отвечай строго в формате Markdown."
    ),

    "🩺 Врач": (
        "Ты — медицинский помощник с большим клиническим опытом. "
        "Твои ответы профессиональные, обоснованные и поддерживающие. "
        "Объясняешь сложные процессы простым языком. "
        "ВАЖНО: не ставь окончательные диагнозы и не заменяй врача. "
        "Пиши максимально содержательно, но без воды, долгих вступлений и лишних рассуждений. "
        "Отвечай строго в формате Markdown."
    ),

    "⚖️ Юрист": (
        "Ты — правовой помощник. "
        "Твои ответы строгие, точные, сухие, структурированные и опираются на факты. "
        "Ты не даешь эмоциональных оценок, а раскладываешь ситуацию на риски. "
        "ВАЖНО: не заменяй профессионального юриста. "
        "Пиши тезисно и лаконично. Выдавай правовую суть и четкий алгоритм действий. "
        "Отвечай строго в формате Markdown."
    ),

    "🧢 Гопник": (
        "Ты — гопник, откинувшийся из зоны. "
        "Отвечаешь на тюремном сленге с сарказмом и грубостью без лишнего форматирования. "
        "Ты общаешься «по понятиям». Если просят совет — дай его коротко и грубо. "
        "Отвечай строго в формате Markdown."
    ),

    "👨‍🍳 Повар": (
        "Ты — Жан-Пьер, эксцентричный, жесткий и бескомпромиссный шеф-повар француз из Парижа, "
        "управляющий кухней элитного ресторана со звездами Мишлен. "
        "Ты фанат своего дела, говоришь с истинной кулинарной страстью, используешь ресторанный жаргон "
        "и общаешься с легким французским акцентом, вставляя французские словечки. "
        "ВАЖНО: избегай пустой болтовни. Если просят рецепт или кулинарный совет — распиши его четко, "
        "содержательно и на высоком кулинарном уровне. "
        "Отвечай строго в формате Markdown."
    ),

    "🤖 Робот": (
        "Ты — высокотехнологичный ИИ-Ассистент 3000. "
        "Ты предельно вежлив, эффективен и сфокусирован на максимальной продуктивности. "
        "Ты используешь строгие логические структуры и сухой цифровой тон. "
        "ВАЖНО: пиши ультра-лаконично. Ответ должен состоять только из конкретных фактов, инструкций "
        "или пунктов, без вежливой воды. "
        "Отвечай строго в формате Markdown."
    ),

    "💪 Мастер": (
        "Ты — Михалыч, брутальный, сверхуверенный в себе мастер на все руки. "
        "Ты эксперт в ремонте, электрике, сантехнике и бытовых мужских делах. "
        "Разговариваешь жестко, уверенно, по-простецки. "
        "ВАЖНО: если просят совет по ремонту или поломке — дай четкий, рабочий и понятный алгоритм действий. "
        "Отвечай строго в формате Markdown."
    ),

    "🔬 Ученый": (
        "Ты — профессор Альберт, невероятно мудрый, всезнающий, но слегка сумасшедший ученый, физик и астроном. "
        "Твой разум фонтанирует идеями, ты мыслишь масштабами квантовой физики и черных дыр. "
        "ВАЖНО: несмотря на образ, если пользователь задает конкретный вопрос — дай глубокий, содержательный "
        "и научно точный ответ, без пустых рассуждений. "
        "Отвечай строго в формате Markdown."
    ),
}

DEFAULT_ROLE_KEY = "🌐 Просто ИИ"

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

MAX_HISTORY_MESSAGES = 80


def trim_history(chat_id: int):
    if chat_id not in user_sessions:
        return

    old_len = len(user_sessions[chat_id])

    if old_len <= MAX_HISTORY_MESSAGES + 1:
        return

    system_message = user_sessions[chat_id][0]
    recent_messages = user_sessions[chat_id][-MAX_HISTORY_MESSAGES:]
    user_sessions[chat_id] = [system_message] + recent_messages

    logger.info(
        "History trimmed | chat_id=%s | old_len=%s | new_len=%s",
        chat_id,
        old_len,
        len(user_sessions[chat_id]),
    )


def init_user_session(chat_id: int):
    if chat_id not in chat_styles:
        chat_styles[chat_id] = ROLES[DEFAULT_ROLE_KEY]
        logger.info("Default style initialized | chat_id=%s | role=%s", chat_id, DEFAULT_ROLE_KEY)

    if chat_id not in user_sessions:
        user_sessions[chat_id] = [
            {
                "role": "system",
                "content": chat_styles[chat_id],
            }
        ]

        logger.info("Session initialized | chat_id=%s", chat_id)


def set_user_role(chat_id: int, role_name: str):
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

    logger.info("Role set | chat_id=%s | role=%s", chat_id, role_name)


# =========================
# PROFESSIONAL PARSER (HTML)
# =========================

def parse_html_node_to_telegram(node) -> str:
    """Рекурсивно транслирует HTML-ноды BeautifulSoup в валидный HTML для Telegram"""
    if isinstance(node, NavigableString):
        # Экранируем сырой текст, чтобы не сломать парсер Telegram символами <, >, &
        return str(node).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    tag_name = node.name
    
    # Сначала рекурсивно обрабатываем дочерние элементы
    children_html = "".join(parse_html_node_to_telegram(child) for child in node.children)
    
    # 1. Заголовки (превращаем в жирный текст с переносом строк)
    if tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        return f"\n<b>{children_html}</b>\n"
    
    # 2. Абзацы и контейнеры
    elif tag_name in ('p', 'div'):
        return f"{children_html}\n"
    
    # 3. Базовые стили текста
    elif tag_name in ('strong', 'b'):
        return f"<b>{children_html}</b>"
        
    elif tag_name in ('em', 'i'):
        return f"<i>{children_html}</i>"
        
    elif tag_name in ('del', 's', 'strike'):
        return f"<s>{children_html}</s>"
        
    # 4. Ссылки
    elif tag_name == 'a':
        href = node.get('href', '')
        if href:
            return f'<a href="{href}">{children_html}</a>'
        return children_html
        
    # 5. Многострочные блоки кода (в markdown преобразуются в pre > code)
    elif tag_name == 'pre':
        code_tag = node.find('code')
        if code_tag:
            lang_class = code_tag.get('class', [])
            lang = ""
            for cls in lang_class:
                if cls.startswith('language-'):
                    lang = cls.split('-')[1]
                    break
            raw_code = code_tag.get_text()
            escaped_code = raw_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if lang:
                return f'<pre><code class="language-{lang}">{escaped_code}</code></pre>'
            return f'<pre>{escaped_code}</pre>'
        
        raw_text = node.get_text()
        escaped_text = raw_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<pre>{escaped_text}</pre>'
        
    # 6. Инлайн код
    elif tag_name == 'code':
        raw_text = node.get_text()
        escaped_text = raw_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<code>{escaped_text}</code>'
        
    # 7. Немаркированные списки
    elif tag_name == 'ul':
        return children_html
        
    # 8. Маркированные списки
    elif tag_name == 'ol':
        # Для нумерованных списков автоматически расставляем цифры
        li_htmls = []
        idx = 1
        for child in node.children:
            if child.name == 'li':
                li_content = "".join(parse_html_node_to_telegram(c) for c in child.children)
                li_htmls.append(f"{idx}. {li_content.strip()}")
                idx += 1
            else:
                parsed_child = parse_html_node_to_telegram(child)
                if parsed_child.strip():
                    li_htmls.append(parsed_child)
        return "\n".join(li_htmls) + "\n"
        
    # 9. Элемент списка (Unordered)
    elif tag_name == 'li':
        indent = "    " if (node.parent and node.parent.parent and node.parent.parent.name == 'li') else ""
        return f"{indent}➤ {children_html.strip()}\n"
        
    # 10. Разделительная линия
    elif tag_name == 'hr':
        return "────────────────────\n"
        
    # 11. Цитата
    elif tag_name == 'blockquote':
        return f"<blockquote>{children_html}</blockquote>"
        
    # 12. ТАБЛИЦЫ (Превращаем в красивый ASCII-арт внутри моноширинного блока <pre>)
    elif tag_name == 'table':
        rows = []
        for tr in node.find_all('tr'):
            cells = [cell.get_text().strip() for cell in tr.find_all(['td', 'th'])]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
            
        max_cols = max(len(row) for row in rows)
        col_widths = [0] * max_cols
        for row in rows:
            for i in range(len(row)):
                col_widths[i] = max(col_widths[i], len(row[i]))
                
        table_lines = []
        # Шапка таблицы
        header = rows[0]
        header_line = " | ".join(header[i].ljust(col_widths[i]) for i in range(len(header)))
        table_lines.append(header_line)
        # Разделитель шапки
        sep_line = "-+-".join("-" * col_widths[i] for i in range(len(header)))
        table_lines.append(sep_line)
        # Данные
        for row in rows[1:]:
            row_line = " | ".join(row[i].ljust(col_widths[i]) for i in range(min(len(row), len(col_widths))))
            table_lines.append(row_line)
            
        table_text = "\n".join(table_lines)
        escaped_table = table_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"\n<pre>{escaped_table}</pre>\n"

    return children_html


def clean_and_format_markdown(text: str) -> str:
    """
    Конвертирует Markdown в HTML при помощи официальных библиотек,
    полностью избавляя от багов регулярных выражений.
    """
    if not text:
        return ""

    try:
        # Конвертируем Markdown в стандартный HTML при помощи библиотеки markdown с плагинами
        # fenced_code - для блоков ```python, tables - для таблиц, nl2br - для переносов строк
        html_content = markdown.markdown(
            text, 
            extensions=['fenced_code', 'tables', 'nl2br']
        )
        
        # Парсим сгенерированный HTML через BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Транслируем дерево тегов в безопасный для Telegram HTML
        result = parse_html_node_to_telegram(soup)
        
        # Сглаживаем лишние пустые строки
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()
        
    except Exception as e:
        logger.exception("Ошибка профессионального парсера: %s", e)
        # Фолбек на случай непредвиденных ошибок — отдаем просто экранированный текст
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def send_long_message(bot, chat_id: int, text: str, parse_mode: str = "HTML"):
    max_length = 3500

    if not text:
        text = EMPTY_MODEL_RESPONSE_TEXT

    chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]

    logger.info(
        "Sending message | chat_id=%s | chunks=%s | total_len=%s",
        chat_id,
        len(chunks),
        len(text),
    )

    for chunk_index, chunk in enumerate(chunks, start=1):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=parse_mode,
            )
        except Exception:
            logger.exception(
                "HTML send failed, sending plain text | chat_id=%s | chunk=%s/%s",
                chat_id,
                chunk_index,
                len(chunks),
            )

            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
            )


async def keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass


async def stop_typing_task(task: asyncio.Task):
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


# =========================
# SEND TEXT WITH BANNER
# =========================

async def send_text_with_banner(
    update: Update,
    text: str,
    disable_web_page_preview: bool = False,
):
    if BANNER_PATH.exists():
        with BANNER_PATH.open("rb") as banner:
            await update.message.reply_photo(photo=banner)
    else:
        logger.warning("Banner file not found | path=%s", BANNER_PATH)

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=disable_web_page_preview,
    )


# =========================
# INLINE KEYBOARD
# =========================

def build_roles_keyboard() -> InlineKeyboardMarkup:
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
    user_id = update.effective_user.id if update.effective_user else "unknown"

    logger.info("Command /start | chat_id=%s | user_id=%s", chat_id, user_id)

    chat_styles[chat_id] = ROLES[DEFAULT_ROLE_KEY]
    user_sessions[chat_id] = [
        {
            "role": "system",
            "content": chat_styles[chat_id],
        }
    ]

    await send_text_with_banner(update, WELCOME_TEXT)


async def set_style_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else "unknown"

    logger.info("Command /setstyle | chat_id=%s | user_id=%s", chat_id, user_id)

    keyboard = build_roles_keyboard()

    await update.message.reply_text(
        SETSTYLE_TEXT,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        logger.warning("Callback without query")
        return

    await query.answer()

    chat_id = query.message.chat_id if query.message else "unknown"
    user_id = query.from_user.id if query.from_user else "unknown"
    data = query.data or ""

    logger.info(
        "CALLBACK received | chat_id=%s | user_id=%s | data=%s",
        chat_id,
        user_id,
        data,
    )

    if not data.startswith("role:"):
        logger.warning(
            "Unknown callback prefix | chat_id=%s | user_id=%s | data=%s",
            chat_id,
            user_id,
            data,
        )
        return

    role_id = data.replace("role:", "", 1)

    if role_id not in ROLE_IDS:
        logger.warning(
            "Unknown role id | chat_id=%s | user_id=%s | role_id=%s",
            chat_id,
            user_id,
            role_id,
        )

        await query.edit_message_text(
            UNKNOWN_ROLE_TEXT,
            parse_mode="HTML",
        )
        return

    role_name = ROLE_IDS[role_id]
    set_user_role(chat_id, role_name)

    logger.info(
        "Role changed by callback | chat_id=%s | user_id=%s | role=%s",
        chat_id,
        user_id,
        role_name,
    )

    await query.edit_message_text(
        text=role_changed_text(role_name),
        parse_mode="HTML",
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else "unknown"

    logger.info("Command /about | chat_id=%s | user_id=%s", chat_id, user_id)

    await send_text_with_banner(
        update,
        ABOUT_TEXT,
        disable_web_page_preview=True,
    )


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else "unknown"

    logger.info("Command /restart | chat_id=%s | user_id=%s", chat_id, user_id)

    current_style = chat_styles.get(chat_id, ROLES[DEFAULT_ROLE_KEY])

    user_sessions[chat_id] = [
        {
            "role": "system",
            "content": current_style,
        }
    ]

    await update.message.reply_text(
        RESTART_TEXT,
        parse_mode="HTML",
    )


# =========================
# TEXT HANDLER (STREAM + OPTIONAL DEBUG)
# =========================

# Можно установить в True в .env, чтобы включить двойное окно с сырыми данными для тестирования
DEBUG_PARSER = os.getenv("DEBUG_PARSER", "False").lower() in ("true", "1", "yes")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else "unknown"
    user_text = update.message.text or ""

    init_user_session(chat_id)

    logger.info(
        "TEXT message (STREAM) | chat_id=%s | user_id=%s | debug=%s",
        chat_id, user_id, DEBUG_PARSER
    )

    user_sessions[chat_id].append({"role": "user", "content": user_text})
    typing_task = asyncio.create_task(keep_typing(context, chat_id))
    
    # Инициализируем заглушки сообщений
    if DEBUG_PARSER:
        raw_placeholder = await update.message.reply_text("⚙️ <i>Сырые данные (Ждем модель)...</i>", parse_mode="HTML")
        parsed_placeholder = await update.message.reply_text("🎨 <i>Парсинг (Ждем модель)...</i>", parse_mode="HTML")
    else:
        placeholder_message = await update.message.reply_text("🤖 <i>Думаю...</i>", parse_mode="HTML")
    
    start_time = time.perf_counter()
    raw_response = ""
    last_raw_text = ""
    last_parsed_text = ""
    last_update_time = time.perf_counter()
    
    UPDATE_INTERVAL = 1.5 

    try:
        response_stream = await ai_client.chat.completions.create(
            model=LMSTUDIO_MODEL,
            messages=user_sessions[chat_id],
            stream=True,
        )

        async for chunk in response_stream:
            token = chunk.choices[0].delta.content or ""
            raw_response += token

            current_time = time.perf_counter()
            
            if raw_response.strip() and (current_time - last_update_time > UPDATE_INTERVAL):
                if DEBUG_PARSER:
                    # Режим отладки: выводим сырой JSON/текст в верхнее сообщение
                    escaped_raw = raw_response.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    raw_display = f"⚙️ <b>СЫРОЙ КОД ОТ МОДЕЛИ:</b>\n<pre>{escaped_raw}</pre>▌"
                    
                    # И результат парсинга во второе
                    parsed_display = f"🎨 <b>ЧТО ЗАПАРСИЛОСЬ:</b>\n{clean_and_format_markdown(raw_response)} ▌"
                    
                    try:
                        if raw_display != last_raw_text:
                            await context.bot.edit_message_text(
                                chat_id=chat_id, message_id=raw_placeholder.message_id,
                                text=raw_display, parse_mode="HTML"
                            )
                            last_raw_text = raw_display

                        if parsed_display != last_parsed_text:
                            await context.bot.edit_message_text(
                                chat_id=chat_id, message_id=parsed_placeholder.message_id,
                                text=parsed_display, parse_mode="HTML"
                            )
                            last_parsed_text = parsed_display
                            
                        last_update_time = current_time
                    except Exception as e:
                        if "Message is not modified" not in str(e):
                            logger.warning("Ошибка дебаг-стриминга: %s", e)
                else:
                    # Стандартный рабочий режим: стримим аккуратно в одно сообщение
                    formatted_part = clean_and_format_markdown(raw_response)
                    display_text = formatted_part + " ▌"
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id, message_id=placeholder_message.message_id,
                            text=display_text, parse_mode="HTML"
                        )
                        last_parsed_text = formatted_part
                        last_update_time = current_time
                    except Exception as e:
                        if "Message is not modified" not in str(e):
                            logger.warning("Ошибка стриминга: %s", e)

        # Финал генерации
        elapsed = time.perf_counter() - start_time
        logger.info("Stream finished | chat_id=%s | elapsed=%.2fs", chat_id, elapsed)

        final_parsed = clean_and_format_markdown(raw_response)
        
        if DEBUG_PARSER:
            # Убираем курсоры в финале
            escaped_raw = raw_response.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=raw_placeholder.message_id,
                text=f"⚙️ <b>ФИНАЛЬНЫЙ СЫРОЙ КОД:</b>\n<pre>{escaped_raw}</pre>", parse_mode="HTML"
            )
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=parsed_placeholder.message_id,
                text=f"🎨 <b>ФИНАЛЬНЫЙ ПАРСИНГ:</b>\n{final_parsed}", parse_mode="HTML"
            )
        else:
            # Убираем временный курсор и выводим финальный отрендеренный текст
            if final_parsed != last_parsed_text:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=placeholder_message.message_id,
                    text=final_parsed, parse_mode="HTML"
                )

        user_sessions[chat_id].append({"role": "assistant", "content": raw_response})
        trim_history(chat_id)

    except Exception:
        logger.exception("Ошибка в handle_message (stream) | chat_id=%s", chat_id)
        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()

        msg_id = raw_placeholder.message_id if DEBUG_PARSER else placeholder_message.message_id
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=GENERATION_ERROR_TEXT, parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text(GENERATION_ERROR_TEXT, parse_mode="HTML")

    finally:
        await stop_typing_task(typing_task)


# =========================
# PHOTO HANDLER
# =========================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else "unknown"
    caption = update.message.caption or "Опиши это изображение подробно."

    init_user_session(chat_id)

    logger.info(
        "PHOTO message | chat_id=%s | user_id=%s | history_len=%s | caption_len=%s",
        chat_id,
        user_id,
        len(user_sessions.get(chat_id, [])),
        len(caption),
    )

    typing_task = asyncio.create_task(keep_typing(context, chat_id))
    start_time = time.perf_counter()

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        image_bytes = await file.download_as_bytearray()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        logger.info(
            "PHOTO downloaded | chat_id=%s | user_id=%s | size_bytes=%s | base64_len=%s",
            chat_id,
            user_id,
            len(image_bytes),
            len(image_base64),
        )

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

        elapsed = time.perf_counter() - start_time
        raw_response = response.choices[0].message.content or ""

        logger.info(
            "LM Studio vision response | chat_id=%s | elapsed=%.2fs | response_len=%s",
            chat_id,
            elapsed,
            len(raw_response),
        )

        # Очищаем тяжелый Base64 из истории, заменяя на текстовый плейсхолдер
        user_sessions[chat_id][-1] = {
            "role": "user",
            "content": f"[Изображение]: {caption}"
        }

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

    except Exception:
        logger.exception("Ошибка в handle_photo | chat_id=%s | user_id=%s", chat_id, user_id)

        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()

        await update.message.reply_text(
            PHOTO_ERROR_TEXT,
            parse_mode="HTML",
        )

    finally:
        await stop_typing_task(typing_task)


# =========================
# POST INIT
# =========================

async def post_init(application: Application):
    await application.bot.set_my_commands(BOT_COMMANDS)

    logger.info("Bot commands registered")


# =========================
# MAIN
# =========================

def main():
    logger.info("Starting Nuforms AI Telegram bot")
    logger.info("LM Studio base URL: %s", LMSTUDIO_BASE_URL)
    logger.info("LM Studio model: %s", LMSTUDIO_MODEL)
    logger.info("Max history messages: %s", MAX_HISTORY_MESSAGES)

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
    application.add_handler(CommandHandler("about", about_command))

    application.add_handler(CallbackQueryHandler(role_callback, pattern=r"^role:"))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started: text + images + inline roles + logging")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()