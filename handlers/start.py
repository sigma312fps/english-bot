from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import db
from content import CORRECTION_MODES, LEVELS
from keyboards import BTN_CLUB, BTN_SETTINGS, BTN_STATS, levels_kb, main_menu, settings_kb
from utils import esc

router = Router()
router.message.filter(F.chat.type == "private")

WELCOME = (
    "👋 Привіт, <b>{name}</b>!\n\n"
    "Я — бот для вивчення англійської 🇬🇧. Ось що я вмію:\n"
    "💬 спілкуватись з тобою англійською (текстом і голосовими) та виправляти помилки\n"
    "🎭 розігрувати життєві ситуації: кафе, співбесіда, аеропорт, презентація…\n"
    "📖 вести твій особистий словник і тренувати слова\n"
    "📚 пояснювати граматику і давати вправи\n"
    "👥 знаходити живого співрозмовника для практики\n"
    "🏠 запрошувати в груповий чат, де всі говорять англійською\n"
    "🔥 рахувати твій прогрес і стрік\n\n"
    "Для початку обери свій рівень або пройди короткий тест 👇"
)

HELP = (
    "<b>Як користуватись ботом</b>\n\n"
    "💬 Просто пиши або надсилай голосові англійською — ШІ відповість і виправить помилки.\n"
    "🎭 <b>Сценарії</b> — рольові діалоги (співбесіда, кафе…). /end — завершити й отримати відгук.\n"
    "📖 <b>Словник</b> — /add слово — додати слово (можна кілька через кому, можна українською).\n"
    "🧠 <b>Тренування</b> — картки з інтервальним повторенням, квіз, складання речень.\n"
    "📚 <b>Граматика</b> — пояснення тем і вправи з перевіркою.\n"
    "👥 <b>Співрозмовник</b> — анонімний чат з іншою людиною лише англійською. /stop — вийти, /next — інший.\n"
    "🏠 <b>Чат англійською</b> — /club — посилання на груповий чат.\n"
    "🌟 /word — слово дня\n"
    "🎯 /test — тест рівня\n"
    "📊 /stats — прогрес, ⚙️ /settings — налаштування"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = db.get_user(message.from_user.id)
    if user is None:
        db.create_user(message.from_user.id, message.from_user.first_name)
        await message.answer(WELCOME.format(name=esc(message.from_user.first_name)), reply_markup=levels_kb())
    else:
        await message.answer(
            f"З поверненням, <b>{esc(user['name'])}</b>! 🔥 Стрік: {user['streak']} дн.\n"
            "Пиши мені англійською або обирай розділ у меню 👇",
            reply_markup=main_menu(),
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP, reply_markup=main_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Головне меню 👇", reply_markup=main_menu())


@router.callback_query(F.data.startswith("lvl:"))
async def choose_level(cb: CallbackQuery):
    level = cb.data.split(":")[1]
    db.ensure_user(cb.from_user.id, cb.from_user.first_name)
    db.update_user(cb.from_user.id, level=level)
    await cb.answer()
    await cb.message.edit_text(f"✅ Твій рівень: <b>{LEVELS[level]}</b>")
    await cb.message.answer(
        "Чудово! Тепер можеш просто написати мені щось англійською, наприклад:\n"
        "<i>Hi! My name is … and I want to improve my English.</i>\n\n"
        "Або обери розділ у меню 👇 (/help — довідка)",
        reply_markup=main_menu(),
    )


# ---------- чат англійською ----------

@router.message(Command("club"))
@router.message(F.text == BTN_CLUB)
async def club(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardBuilder().button(text="🏠 Приєднатися до чату", url=config.CLUB_LINK).as_markup()
    await message.answer(
        "🏠 <b>English Speaking Club</b>\n\n"
        "Груповий чат, де всі спілкуються <b>тільки англійською</b> 🇬🇧\n"
        "• щодня бот публікує тему для обговорення\n"
        "• не знаєш, як сказати? Напиши українською — бот підкаже англійський варіант\n"
        "• смайлики й стікери можна, але без спаму 😉\n\n"
        "⚠️ Хто постійно ігнорує правило «English only», отримує мут на кілька хвилин.\n\n"
        f"👉 {config.CLUB_LINK}",
        reply_markup=kb,
        disable_web_page_preview=True,
    )


# ---------- статистика ----------

@router.message(Command("stats"))
@router.message(F.text == BTN_STATS)
async def stats(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    user = db.ensure_user(uid, message.from_user.first_name)
    await message.answer(
        "📊 <b>Твій прогрес</b>\n\n"
        f"🎓 Рівень: <b>{LEVELS.get(user['level'], user['level'])}</b>\n"
        f"⭐ XP: <b>{user['xp']}</b>\n"
        f"🔥 Стрік: <b>{user['streak']}</b> дн. поспіль\n"
        f"💬 Повідомлень ШІ-співрозмовнику: <b>{user['messages']}</b>\n"
        f"📖 Слів у словнику: <b>{db.count_words(uid)}</b> (вивчено: {db.count_learned(uid)})\n"
        f"🧠 На повторення сьогодні: <b>{db.count_due(uid)}</b>"
    )


# ---------- налаштування ----------

def _settings_text(user: dict) -> str:
    return (
        "⚙️ <b>Налаштування</b>\n\n"
        f"🎓 Рівень — під нього ШІ підбирає складність мови.\n"
        f"✏️ Виправлення — зараз: <b>{CORRECTION_MODES[user['correction']]}</b>.\n"
        "🔊 Голосові відповіді — ШІ відповідатиме ще й аудіо.\n"
        "⏰ Нагадування — щодня слово дня і нагадування про стрік."
    )


@router.message(Command("settings"))
@router.message(F.text == BTN_SETTINGS)
async def settings(message: Message, state: FSMContext):
    await state.clear()
    user = db.ensure_user(message.from_user.id, message.from_user.first_name)
    await message.answer(_settings_text(user), reply_markup=settings_kb(user))


@router.callback_query(F.data.startswith("set:"))
async def settings_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    user = db.ensure_user(uid, cb.from_user.first_name)
    action = cb.data.split(":")[1]

    if action == "level":
        await cb.answer()
        await cb.message.edit_text("Обери рівень:", reply_markup=levels_kb())
        return
    if action == "corr":
        modes = list(CORRECTION_MODES)
        db.update_user(uid, correction=modes[(modes.index(user["correction"]) + 1) % len(modes)])
    elif action == "voice":
        db.update_user(uid, voice_reply=0 if user["voice_reply"] else 1)
    elif action == "remind":
        db.update_user(uid, reminders=0 if user["reminders"] else 1)
    elif action == "clear":
        db.clear_history(uid)
        db.update_user(uid, scenario=None)
        await cb.answer("Історію розмови очищено 🧹", show_alert=True)

    user = db.get_user(uid)
    await cb.message.edit_text(_settings_text(user), reply_markup=settings_kb(user))
    await cb.answer()
