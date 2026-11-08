import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Моделі Groq (безкоштовні). Якщо якусь модель приберуть — просто змініть назву в .env
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")

# Entrim AI (платно). Якщо ключ заданий, текстові запити йдуть сюди, інакше на Groq. Голосові завжди на Groq.
ENTRIM_API_KEY = os.getenv("ENTRIM_API_KEY", "").strip()
ENTRIM_BASE_URL = os.getenv("ENTRIM_BASE_URL", "https://api.entrim.ai/v1")
ENTRIM_MODEL = os.getenv("ENTRIM_MODEL", "zai-org/GLM-5.3-Flash")
CHAT_MODEL = ENTRIM_MODEL if ENTRIM_API_KEY else GROQ_MODEL

# Голос для озвучки (edge-tts, безкоштовно, без ключа)
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")

# Посилання на груповий чат "English only"
CLUB_LINK = os.getenv("CLUB_LINK", "https://t.me/engspeakingclub2")

# Render сам задає PORT — тоді запускаємо вебсторінку для "будильника". Локально не потрібно.
PORT = int(os.getenv("PORT", "0"))

DB_PATH = os.getenv("DB_PATH", "bot.db")

# Хмарна база Turso (безкоштовно): дані не стираються після перезапуску. Без неї база лежить у файлі DB_PATH
TURSO_URL = os.getenv("TURSO_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
TURSO_REPLICA_PATH = os.getenv("TURSO_REPLICA_PATH", "turso_replica.db")

# Telegram ID людей, яким доступна команда /analytics (через кому)
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(",", " ").split()}

# О котрій годині надсилати щоденне слово / нагадування / тему дня в групи
DAILY_HOUR = int(os.getenv("DAILY_HOUR", "19"))
