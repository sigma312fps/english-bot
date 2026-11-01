import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Моделі Groq (безкоштовні). Якщо якусь модель приберуть — просто змініть назву в .env
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")

# Голос для озвучки (edge-tts, безкоштовно, без ключа)
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")

# Посилання на груповий чат "English only"
CLUB_LINK = os.getenv("CLUB_LINK", "https://t.me/engspeakingclub2")

# Render сам задає PORT — тоді запускаємо вебсторінку для "будильника". Локально не потрібно.
PORT = int(os.getenv("PORT", "0"))

DB_PATH = os.getenv("DB_PATH", "bot.db")

# О котрій годині надсилати щоденне слово / нагадування / тему дня в групи
DAILY_HOUR = int(os.getenv("DAILY_HOUR", "19"))
