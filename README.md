# LM Studio AI Telegram Bot with Image Support

![LM Studio AI Telegram Bot](avatar.jpg)

A local Telegram AI assistant powered by LM Studio and an OpenAI-compatible API.

The bot supports streaming text responses, image analysis with vision-capable models, role switching, per-chat session memory, Markdown-to-Telegram-HTML formatting, inline role buttons, welcome/about banners, logging, and environment-based configuration.

## ✨ Features

* 🤖 Local Telegram AI assistant powered by LM Studio
* 🔌 OpenAI-compatible API connection
* ⚡ Streaming text responses with live message editing
* 🧠 Per-chat conversation memory
* ✂️ Automatic history trimming to keep sessions manageable
* 🎭 Multiple assistant roles with inline Telegram buttons
* 🖼️ Image analysis support for vision-capable models
* 🧹 Session reset command
* ℹ️ About command with project information
* 🏷️ Welcome/About banner image support via `banner.jpg`
* 💬 Markdown-to-Telegram-HTML formatting
* 📊 Basic table rendering for Telegram messages
* 🧪 Optional parser debug mode
* 📝 Rotating log file support via `bot.log`
* 🔐 Environment variables via `.env`

## 🧠 Available Roles

The bot includes several predefined assistant styles:

* 🌐 Simple AI
* 🩺 Doctor
* ⚖️ Lawyer
* 🧢 Gopnik
* 👨‍🍳 Chef
* 🤖 Robot
* 💪 Master
* 🔬 Scientist

## 📦 Requirements

* Python 3.10+
* Telegram bot token
* LM Studio installed and running
* A local model loaded in LM Studio
* LM Studio Local Server enabled
* Optional: a vision-capable model for image analysis

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/neuromask/lmstudio-ai-telegram-bot.git
cd lmstudio-ai-telegram-bot
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
.venv\Scripts\activate.bat
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_MODEL=local-model
LOG_LEVEL=INFO
DEBUG_PARSER=False
```

### Environment variable reference

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_TOKEN` | Telegram bot token from BotFather | Required |
| `LMSTUDIO_BASE_URL` | LM Studio OpenAI-compatible server URL | `http://localhost:1234/v1` |
| `LMSTUDIO_API_KEY` | API key placeholder for LM Studio | `lm-studio` |
| `LMSTUDIO_MODEL` | Model name passed to the API | `local-model` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG_PARSER` | Shows raw model output and parsed output separately | `False` |

Do not upload `.env` to GitHub.

Use `.env.example` as a safe public template:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_MODEL=local-model
LOG_LEVEL=INFO
DEBUG_PARSER=False
```

## 🔐 Git Ignore

Make sure your `.gitignore` contains:

```gitignore
.env
bot.log
bot.log.*
__pycache__/
*.pyc
.venv/
venv/
```

`.env` must stay private.

`.env.example` can be uploaded to GitHub.

## 🧩 LM Studio Setup

1. Open LM Studio.
2. Download or select a local model.
3. Load the model.
4. Open the **Local Server** tab.
5. Start the server.
6. Make sure the server URL is:

```text
http://localhost:1234/v1
```

7. Use the same value in `.env`:

```env
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

The bot uses LM Studio through the OpenAI-compatible endpoint, so it connects through the `openai` Python SDK while using your local LM Studio server.

## 🤖 How to Create a Telegram Bot

1. Open Telegram.
2. Search for:

```text
@BotFather
```

3. Start a chat with BotFather.
4. Send:

```text
/newbot
```

5. Enter a display name for your bot.

Example:

```text
Nuforms AI
```

6. Enter a username for your bot.

The username must end with `bot`.

Example:

```text
nuforms_ai_bot
```

7. BotFather will give you a bot token.

It will look similar to this:

```text
1234567890:AAExampleTokenHere
```

8. Copy the token into your `.env` file:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
```

Never publish your real Telegram token.

If you accidentally push your token to GitHub, revoke it immediately using BotFather:

```text
/revoke
```

## ▶️ Run the Bot

Start LM Studio Local Server first.

Then run:

```bash
python bot.py
```

If everything is configured correctly, you should see startup logs in the terminal and in `bot.log`.

## 💬 Bot Commands

| Command | Description |
|---|---|
| `/start` | Start Nuforms AI and create a fresh session |
| `/setstyle` | Choose the assistant role with inline buttons |
| `/restart` | Clear the current chat memory while keeping the selected role |
| `/about` | Show information about the bot and project |

## 🖼️ Banner and Avatar

The README uses:

```text
avatar.jpg
```

The bot welcome/about commands use:

```text
banner.jpg
```

Place both files in the project root:

```text
lmstudio-ai-telegram-bot/
├── avatar.jpg
├── banner.jpg
└── bot.py
```

If `banner.jpg` is missing, the bot will still send the text message and log a warning.

## 🖼️ Image Support

The bot can send Telegram images to LM Studio using Base64 image input.

This requires:

* a vision-capable model loaded in LM Studio
* image handler in the Telegram bot
* OpenAI-compatible message format using `image_url`

Example user requests:

```text
Describe this image.
What is shown here?
Analyze this screenshot.
Read the text from this image.
```

To avoid bloating the conversation history, the bot replaces the heavy Base64 image content with a lightweight text placeholder after the vision response is received.

Text-only models will not be able to analyze images.

## ⚡ Streaming Responses

Text replies are streamed from LM Studio and edited live in Telegram.

The bot first sends a temporary message:

```text
🤖 Думаю...
```

Then it updates that message while the local model generates the response.

## 🧪 Parser Debug Mode

The bot includes optional parser debugging.

Enable it in `.env`:

```env
DEBUG_PARSER=True
```

When enabled, the bot sends two debug messages:

* raw Markdown output from the model
* parsed Telegram HTML output

For normal use, keep it disabled:

```env
DEBUG_PARSER=False
```

## 📝 Logging

The bot writes logs to both the terminal and a rotating log file:

```text
bot.log
```

Log rotation is configured automatically, so old logs are kept as backups.

Recommended `.gitignore` entries:

```gitignore
bot.log
bot.log.*
```

## 🛠️ Project Structure

Example structure:

```text
lmstudio-ai-telegram-bot/
├── bot.py
├── avatar.jpg
├── banner.jpg
├── .env
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## 📄 requirements.txt

```txt
python-telegram-bot
openai
python-dotenv
httpx
Markdown
beautifulsoup4
```

## ⚠️ Security Notes

* Never commit `.env`
* Never publish your Telegram bot token
* Revoke leaked tokens immediately through BotFather
* Keep private local configuration outside GitHub
* Use `.env.example` only as a public template
* Do not commit `bot.log`, because logs may contain local debugging information

## 📌 Notes

This project is designed for private local AI usage with LM Studio.

The Telegram bot sends user messages to a locally running model through LM Studio's OpenAI-compatible API.

It is useful for experimenting with personal local AI assistants, role-based chatbots, streaming responses, image analysis, and Telegram integrations.

## 📜 License

MIT License
