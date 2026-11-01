from aiogram import F
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from content import CORRECTION_MODES, GRAMMAR, LEVELS, SCENARIOS

BTN_CHAT = "💬 Розмова з ШІ"
BTN_SCENARIOS = "🎭 Сценарії"
BTN_VOCAB = "📖 Мій словник"
BTN_TRAIN = "🧠 Тренування"
BTN_GRAMMAR = "📚 Граматика"
BTN_PARTNER = "👥 Співрозмовник"
BTN_STATS = "📊 Прогрес"
BTN_SETTINGS = "⚙️ Налаштування"
BTN_CLUB = "🏠 Чат англійською"

MENU_TEXTS = {BTN_CHAT, BTN_SCENARIOS, BTN_VOCAB, BTN_TRAIN, BTN_GRAMMAR, BTN_PARTNER, BTN_STATS, BTN_SETTINGS, BTN_CLUB}

# Звичайний текст користувача: не кнопка меню і не команда
USER_TEXT = F.text & ~F.text.in_(MENU_TEXTS) & ~F.text.startswith("/")


def main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [BTN_CHAT, BTN_SCENARIOS],
        [BTN_VOCAB, BTN_TRAIN],
        [BTN_GRAMMAR, BTN_PARTNER],
        [BTN_STATS, BTN_SETTINGS],
        [BTN_CLUB],
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder="Write in English… ✍️",
    )


def levels_kb(with_test: bool = True) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for code, name in LEVELS.items():
        b.button(text=name, callback_data=f"lvl:{code}")
    if with_test:
        b.button(text="🎯 Пройти тест рівня", callback_data="pt:start")
    b.adjust(1)
    return b.as_markup()


def settings_kb(user: dict) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=f"🎓 Рівень: {user['level']}", callback_data="set:level")
    b.button(text=f"✏️ Виправлення: {CORRECTION_MODES[user['correction']]}", callback_data="set:corr")
    b.button(text=f"🔊 Голосові відповіді: {'✅' if user['voice_reply'] else '❌'}", callback_data="set:voice")
    b.button(text=f"⏰ Щоденні нагадування: {'✅' if user['reminders'] else '❌'}", callback_data="set:remind")
    b.button(text="🗑 Очистити історію розмови", callback_data="set:clear")
    b.adjust(1)
    return b.as_markup()


def scenarios_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, (title, _) in SCENARIOS.items():
        b.button(text=title, callback_data=f"sc:{key}")
    b.adjust(2)
    return b.as_markup()


def chat_reply_kb(show_tts: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if show_tts:
        b.button(text="🔊 Озвучити", callback_data="chat:tts")
    b.button(text="🏁 Завершити й отримати відгук", callback_data="chat:end")
    b.adjust(2)
    return b.as_markup()


def vocab_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Додати слово", callback_data="voc:add")
    b.button(text="📋 Усі слова", callback_data="voc:list:0")
    b.button(text="🗑 Видалити слово", callback_data="voc:del")
    b.button(text="🌟 Слово дня", callback_data="voc:wod")
    b.adjust(2)
    return b.as_markup()


def training_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🃏 Картки (повторення)", callback_data="tr:cards")
    b.button(text="✅ Квіз: обери переклад", callback_data="tr:quiz")
    b.button(text="✍️ Склади речення", callback_data="tr:sentence")
    b.adjust(1)
    return b.as_markup()


def next_stop_kb(next_cb: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➡️ Далі", callback_data=next_cb)
    b.button(text="⏹ Стоп", callback_data="tr:stop")
    return b.as_markup()


def grammar_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, (name, level) in GRAMMAR.items():
        b.button(text=f"{level} · {name}", callback_data=f"gr:t:{key}")
    b.adjust(2)
    return b.as_markup()


def grammar_topic_kb(key: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📝 Вправа", callback_data=f"gr:ex:{key}")
    b.button(text="🔙 До тем", callback_data="gr:list")
    return b.as_markup()
