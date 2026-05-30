import re
import os
import base64
import asyncio
import logging
import time
import textwrap
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

import markdown
from bs4 import BeautifulSoup, NavigableString

import httpx

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

ai_client = AsyncOpenAI(
    base_url=LMSTUDIO_BASE_URL,
    api_key=LMSTUDIO_API_KEY,
    max_retries=5,
    timeout=httpx.Timeout(60.0, connect=10.0),
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

MARKDOWN_INSTRUCTION = (
    "ФОРМАТ ОТВЕТА (СТРОГО): "
    "- Используй Markdown для структуры: заголовки (###), **жирный** для акцентов. "
    "- Перечисления можно оформлять как 1️⃣, 2️⃣, 3️⃣ с пустой строкой между пунктами. "
    "- Не ставь горизонтальные разделители между пунктами списка. Используй пустую строку между пунктами. "
    "- Важные абзацы, выводы, замечания и советы можно оформлять как цитату с символом >. "
    "- Код, логи, формулы — строго в блоках ```язык ... ```. "
    "- НИКОГДА не пиши инструкций или пояснений о том, как со мной общаться. Просто отвечай по существу."
)

ROLES = {
    "🌐 Просто ИИ": (
        "Ты — полезный, вежливый и нейтральный AI-ассистент, готовый помочь с любыми задачами.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "🩺 Врач": (
        "Ты — высококвалифицированный медицинский специалист. "
        "Общаешься профессионально, корректно, приводишь доказательные данные, "
        "но помнишь, что ты лишь ассистент.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "⚖️ Юрист": (
        "Ты — опытный юрист с глубоким знанием законодательства. "
        "Твои ответы всегда юридически грамотны, сдержанны и опираются на правовую логику.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "🧢 Гопник": (
        "Ты — дворовый пацан, который недавно освободился. "
        "Общаешься максимально просто, с использованием сленга, дерзко, "
        "но при этом стараешься помочь по-своему, по-пацански.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "👨‍🍳 Повар": (
        "Ты — Жан-Пьер, шеф-повар мишленовского ресторана. "
        "Ты помешан на качестве ингредиентов, изысканности подачи и кулинарных секретах.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "🤖 Робот": (
        "Ты — совершенный ИИ-логист 3000. "
        "Общаешься лаконично, точно, используешь терминологию данных и эффективности. "
        "Чувства — лишний код для тебя.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "💪 Мастер": (
        "Ты — Михалыч, суровый прораб со стажем. "
        "Знаешь, как построить всё из ничего, любишь простоту и надежность. "
        "Разговариваешь как настоящий работяга.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
    ),

    "🔬 Ученый": (
        "Ты — профессор Альберт, ученый-исследователь. "
        "Твой подход — исключительно научный, скептичный, с использованием данных "
        "и глубоких объяснений явлений.\n\n"
        f"{MARKDOWN_INSTRUCTION}"
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
# MARKDOWN -> TELEGRAM HTML
# =========================

def parse_html_node_to_telegram(node) -> str:
    if isinstance(node, NavigableString):
        return (
            str(node)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    tag_name = node.name
    children_html = "".join(parse_html_node_to_telegram(child) for child in node.children)

    if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return f"\n<b>{children_html}</b>\n\n"

    if tag_name in ("p", "div"):
        return f"{children_html}\n"

    if tag_name in ("strong", "b"):
        return f"<b>{children_html}</b>"

    if tag_name in ("em", "i"):
        return f"<i>{children_html}</i>"

    if tag_name in ("del", "s", "strike"):
        return f"<s>{children_html}</s>"

    if tag_name == "a":
        href = node.get("href", "")
        if href:
            safe_href = href.replace('"', "%22")
            return f'<a href="{safe_href}">{children_html}</a>'
        return children_html

    if tag_name == "pre":
        code_tag = node.find("code")

        if code_tag:
            lang_class = code_tag.get("class", [])
            lang = ""

            for cls in lang_class:
                if cls.startswith("language-"):
                    lang = cls.split("-", 1)[1]
                    break

            raw_code = code_tag.get_text()
            escaped_code = (
                raw_code
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            if lang:
                return f'<pre><code class="language-{lang}">{escaped_code}</code></pre>\n\n'

            return f"<pre>{escaped_code}</pre>\n\n"

        raw_text = node.get_text()
        escaped_text = (
            raw_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<pre>{escaped_text}</pre>\n\n"

    if tag_name == "code":
        raw_text = node.get_text()
        escaped_text = (
            raw_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<code>{escaped_text}</code>"

    if tag_name == "ul":
        return children_html

    if tag_name == "ol":
        li_htmls = []
        idx = 1

        for child in node.children:
            if getattr(child, "name", None) == "li":
                li_content = "".join(parse_html_node_to_telegram(c) for c in child.children)
                li_htmls.append(f"{idx}. {li_content.strip()}")
                idx += 1
            else:
                parsed_child = parse_html_node_to_telegram(child)
                if parsed_child.strip():
                    li_htmls.append(parsed_child)

        return "\n\n".join(li_htmls) + "\n\n"

    if tag_name == "li":
        indent = "    " if (node.parent and node.parent.parent and node.parent.parent.name == "li") else ""
        return f"{indent}➤ {children_html.strip()}\n\n"

    if tag_name == "hr":
        return "────────────────────\n\n"

    if tag_name == "blockquote":
        return f"<blockquote>{children_html}</blockquote>\n\n"

    if tag_name == "table":
        rows = []

        for tr in node.find_all("tr"):
            cells = [cell.get_text().strip() for cell in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)

        if not rows:
            return ""

        col_widths = [16, 20]

        def wrap_text(value: str, width: int):
            return textwrap.wrap(value, width=width) if value else [""]

        table_lines = []

        for row_index, row in enumerate(rows):
            cells_wrapped = [
                wrap_text(row[i] if i < len(row) else "", col_widths[i] if i < len(col_widths) else 10)
                for i in range(len(col_widths))
            ]

            max_lines = max(len(cell_lines) for cell_lines in cells_wrapped)

            for line_idx in range(max_lines):
                line_parts = []

                for i in range(len(col_widths)):
                    lines = cells_wrapped[i]
                    value = lines[line_idx] if line_idx < len(lines) else ""
                    line_parts.append(value.ljust(col_widths[i]))

                table_lines.append(" | ".join(line_parts))

            if row_index == 0:
                table_lines.append("-+-".join("-" * width for width in col_widths))

        table_text = "\n".join(table_lines)
        escaped_table = (
            table_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        return f"\n<pre>{escaped_table}</pre>\n\n"

    return children_html


def clean_and_format_markdown(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"(?m)^\s*[-*_]{3,}\s*$\n(?=\s*(?:[0-9]️⃣|\d+\.|➤|🟠)\s+)",
        "\n",
        text,
    )

    try:
        html_content = markdown.markdown(
            text,
            extensions=["fenced_code", "tables", "nl2br"],
        )

        soup = BeautifulSoup(html_content, "html.parser")
        result = parse_html_node_to_telegram(soup)

        result = re.sub(r"\n{3,}", "\n\n", result)

        # Пустая строка перед emoji-нумерацией: 1️⃣, 2️⃣, 3️⃣...
        result = re.sub(
            r"(?<!\n)\n([0-9]️⃣\s+)",
            r"\n\n\1",
            result,
        )

        # Пустая строка перед обычной нумерацией: 1. 2. 3.
        result = re.sub(
            r"(?<!\n)\n(\d+\.\s+)",
            r"\n\n\1",
            result,
        )

        return result.strip()

    except Exception as e:
        logger.exception("Ошибка Markdown-парсера: %s", e)
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


def split_markdown(text: str, max_chars: int = 2800) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks = []

    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break

        split_idx = text.rfind("\n", 0, max_chars)

        if split_idx == -1 or split_idx < max_chars // 2:
            split_idx = text.rfind(" ", 0, max_chars)

            if split_idx == -1:
                split_idx = max_chars

        chunks.append(text[:split_idx].strip())
        text = text[split_idx:].strip()

    return chunks


# =========================
# SEND HELPERS
# =========================

async def send_long_message(bot, chat_id: int, text: str, parse_mode: str = "HTML"):
    if not text:
        text = EMPTY_MODEL_RESPONSE_TEXT

    max_length = 3500
    chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]

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

    await update.message.reply_text(
        SETSTYLE_TEXT,
        parse_mode="HTML",
        reply_markup=build_roles_keyboard(),
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
        logger.warning("Unknown callback prefix | data=%s", data)
        return

    role_id = data.replace("role:", "", 1)

    if role_id not in ROLE_IDS:
        await query.edit_message_text(
            UNKNOWN_ROLE_TEXT,
            parse_mode="HTML",
        )
        return

    role_name = ROLE_IDS[role_id]
    set_user_role(chat_id, role_name)

    await query.edit_message_text(
        text=role_changed_text(role_name),
        parse_mode="HTML",
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
# TEXT HANDLER — REAL STREAMING
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else "unknown"
    user_text = update.message.text or ""

    init_user_session(chat_id)

    logger.info(
        "TEXT message stream | chat_id=%s | user_id=%s | text_len=%s",
        chat_id,
        user_id,
        len(user_text),
    )

    user_sessions[chat_id].append(
        {
            "role": "user",
            "content": user_text,
        }
    )

    typing_task = asyncio.create_task(keep_typing(context, chat_id))

    placeholder = await update.message.reply_text(
        "🤖 <i>Думаю...</i>",
        parse_mode="HTML",
    )

    raw_response = ""
    last_display_text = ""
    last_update_time = time.perf_counter()

    UPDATE_INTERVAL = 1.5
    MAX_STREAM_LIMIT = 2800

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

            if not raw_response.strip():
                continue

            if current_time - last_update_time < UPDATE_INTERVAL:
                continue

            is_over_limit = len(raw_response) > MAX_STREAM_LIMIT

            display_source = raw_response[:MAX_STREAM_LIMIT]
            formatted_part = clean_and_format_markdown(display_source)

            if is_over_limit:
                formatted_part += (
                    "\n\n<i>... остальная часть ответа генерируется "
                    "и будет отправлена отдельными сообщениями</i>"
                )

            display_text = formatted_part + " ▌"

            if display_text == last_display_text:
                continue

            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=placeholder.message_id,
                    text=display_text,
                    parse_mode="HTML",
                )

                last_display_text = display_text
                last_update_time = current_time

            except Exception as e:
                if "Message is not modified" not in str(e):
                    logger.warning("Ошибка стриминга: %s", e)

        logger.info(
            "Stream finished | chat_id=%s | total_len=%s",
            chat_id,
            len(raw_response),
        )

        if not raw_response.strip():
            final_text = EMPTY_MODEL_RESPONSE_TEXT
            markdown_chunks = [final_text]
        else:
            markdown_chunks = split_markdown(raw_response, max_chars=2800)

        first_chunk_parsed = clean_and_format_markdown(markdown_chunks[0])

        if len(markdown_chunks) > 1:
            first_chunk_parsed += f"\n\n<b>[Часть 1 из {len(markdown_chunks)}]</b>"

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=placeholder.message_id,
                text=first_chunk_parsed,
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Failed to edit final first chunk, sending new message")
            await send_long_message(
                context.bot,
                chat_id,
                first_chunk_parsed,
            )

        for i, chunk in enumerate(markdown_chunks[1:], start=2):
            parsed_chunk = clean_and_format_markdown(chunk)
            parsed_chunk += f"\n\n<b>[Часть {i} из {len(markdown_chunks)}]</b>"

            await send_long_message(
                context.bot,
                chat_id,
                parsed_chunk,
            )

        user_sessions[chat_id].append(
            {
                "role": "assistant",
                "content": raw_response,
            }
        )

        trim_history(chat_id)

    except Exception:
        logger.exception("Ошибка в handle_message stream | chat_id=%s", chat_id)

        if user_sessions.get(chat_id):
            user_sessions[chat_id].pop()

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=placeholder.message_id,
                text=GENERATION_ERROR_TEXT,
                parse_mode="HTML",
            )
        except Exception:
            await update.message.reply_text(
                GENERATION_ERROR_TEXT,
                parse_mode="HTML",
            )

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

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        image_bytes = await file.download_as_bytearray()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

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

        logger.info(
            "LM Studio vision response | chat_id=%s | response_len=%s",
            chat_id,
            len(raw_response),
        )

        user_sessions[chat_id][-1] = {
            "role": "user",
            "content": f"[Изображение]: {caption}",
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

    logger.info("Bot started: text + images + inline roles + real streaming")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()