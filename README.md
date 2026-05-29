# LM Studio AI Telegram Bot with Image Support

A Telegram AI bot that connects to a local LM Studio server using an OpenAI-compatible API.

The bot supports text conversations, role switching, chat memory per user session, formatted Telegram replies, and optional image input support for vision-capable models.

## ✨ Features

* 🤖 Telegram bot powered by a local LM Studio model
* 🔌 OpenAI-compatible API connection
* 🧠 Per-chat conversation memory
* 🎭 Multiple assistant roles
* ⌨️ Telegram reply keyboard for role selection
* 🧹 Session reset command
* ℹ️ About command with bot information
* 💬 HTML-formatted Telegram responses
* 🖼️ Optional image input support for vision-capable models
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

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/lmstudio-ai-telegram-bot.git
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

If you do not have `requirements.txt` yet, install dependencies manually:

```bash
pip install python-telegram-bot openai python-dotenv
```

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_MODEL=local-model
```

Do not upload `.env` to GitHub.

Use `.env.example` as a safe public template:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_MODEL=local-model
```

## 🔐 Git Ignore

Make sure your `.gitignore` contains:

```gitignore
.env
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
LM Studio AI Bot
```

6. Enter a username for your bot.

The username must end with `bot`.

Example:

```text
lmstudio_ai_helper_bot
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

Or, if your main file has another name:

```bash
python your_file_name.py
```

If everything is configured correctly, you should see a message in the terminal that the bot has started.

## 💬 Bot Commands

| Command     | Description                                             |
| ----------- | ------------------------------------------------------- |
| `/start`    | Start the bot and initialize the default assistant role |
| `/setstyle` | Open the role selection keyboard                        |
| `/restart`  | Clear the current chat memory                           |
| `/about`    | Show information about the bot                          |

## 🖼️ Image Support

The bot can be extended to send Telegram images to LM Studio using Base64 image input.

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

Text-only models will not be able to analyze images.

## 🛠️ Project Structure

Example structure:

```text
lmstudio-ai-telegram-bot/
├── bot.py
├── .env
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## 📄 Example requirements.txt

```txt
python-telegram-bot
openai
python-dotenv
```

## ⚠️ Security Notes

* Never commit `.env`
* Never publish your Telegram bot token
* Revoke leaked tokens immediately through BotFather
* Keep private local configuration outside GitHub
* Use `.env.example` only as a public template

## 📌 Notes

This project is designed for local AI usage with LM Studio.

The Telegram bot sends user messages to a locally running model through LM Studio's OpenAI-compatible API.

It is useful for experimenting with private local AI assistants, role-based chatbots, and Telegram integrations.

## 📜 License

MIT License
