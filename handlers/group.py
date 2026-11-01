"""Груповий чат "English only": нагадування про мову, мут за ігнорування, антиспам, тема дня."""
import logging
import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

import ai
import daily
import db
import moderation
import prompts
from utils import esc, is_mostly_cyrillic

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

RULES = (
    "🇬🇧 <b>English-only chat</b>\n\n"
    "1. Пишемо тільки англійською — помилки не страшні, головне практика!\n"
    "2. Не знаєш, як сказати? Напиши українською — я підкажу англійський варіант.\n"
    f"3. Хто ігнорує правило: {moderation.WARNINGS_BEFORE_MUTE} попередження, далі мут на 1–5 хв.\n"
    "4. Смайлики й стікери — можна, але без спаму 😉\n"
    "5. Будьте ввічливими й підтримуйте одне одного.\n\n"
    "/topic — тема для обговорення"
)

_no_rights_warned: set[int] = set()


def _is_emoji_like(message: Message) -> bool:
    """Стікери, гіфки, кубики і повідомлення без жодної літери (лише смайлики/знаки)."""
    if message.sticker or message.animation or message.dice:
        return True
    text = message.text or ""
    return bool(text) and not any(ch.isalpha() for ch in text)


async def _is_admin(message: Message) -> bool:
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def _mute(message: Message, minutes: int) -> bool:
    if await _is_admin(message):
        return False
    try:
        await message.bot.restrict_chat_member(
            message.chat.id,
            message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=int(time.time()) + minutes * 60,
        )
        return True
    except Exception:
        log.exception("Не вдалося замутити")
        if message.chat.id not in _no_rights_warned:
            _no_rights_warned.add(message.chat.id)
            await message.answer("⚠️ Щоб я міг модерувати чат, зробіть мене адміністратором "
                                 "з правами «Блокувати користувачів» і «Видаляти повідомлення».")
        return False


async def _delete(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


@router.message(F.new_chat_members)
async def welcome(message: Message):
    db.save_group(message.chat.id, message.chat.title or "")
    names = ", ".join(esc(m.first_name) for m in message.new_chat_members if not m.is_bot)
    if names:
        await message.answer(f"👋 Welcome, {names}!\n\n{RULES}")
    else:
        await message.answer(RULES)


@router.message(Command("rules"))
async def rules(message: Message):
    db.save_group(message.chat.id, message.chat.title or "")
    await message.answer(RULES)


@router.message(Command("topic"))
async def topic(message: Message):
    db.save_group(message.chat.id, message.chat.title or "")
    try:
        question = await daily.topic_of_day()
    except Exception:
        log.exception("AI error")
        await message.answer("⚠️ Try again later.")
        return
    await message.answer(f"💭 <b>Topic of the day</b>\n\n{esc(question)}")


@router.message()
async def moderate(message: Message):
    db.save_group(message.chat.id, message.chat.title or "")
    # Повідомлення від імені каналу/анонімного адміна і від ботів не модеруємо
    if not message.from_user or message.from_user.is_bot or message.sender_chat:
        return
    user = message.from_user.mention_html()

    # --- смайлики / стікери: мову не перевіряємо, лише стежимо за спамом ---
    if _is_emoji_like(message):
        action, minutes = moderation.spam_hit(message.chat.id, message.from_user.id)
        if action == "warn":
            await _delete(message)
            await message.answer(f"🙏 {user}, please don't spam stickers/emoji. Next ones will be removed.")
        elif action == "delete":
            await _delete(message)
        elif action == "mute":
            await _delete(message)
            if await _mute(message, minutes):
                await message.answer(f"🔇 {user} is muted for {minutes} min for spamming stickers/emoji.")
        return

    # --- мова ---
    text = message.text or message.caption or ""
    if not is_mostly_cyrillic(text):
        return

    count, minutes = moderation.language_violation(message.chat.id, message.from_user.id)
    try:
        hint = await ai.ask(prompts.translate_to_english(text), temperature=0.3, max_tokens=200)
    except Exception:
        hint = ""
    hint_text = f"\nYou can say:\n<i>{esc(hint)}</i>" if hint else ""

    if minutes and await _mute(message, minutes):
        await message.reply(
            f"🔇 {user} is muted for <b>{minutes} min</b> for ignoring the English-only rule.{hint_text}"
        )
    elif minutes:
        # адміна замутити не можна — просто нагадуємо
        await message.reply(f"🇬🇧 English only, please!{hint_text}")
    else:
        await message.reply(
            f"🇬🇧 {user}, English only, please!{hint_text}\n\n"
            f"⚠️ Warning {count}/{moderation.WARNINGS_BEFORE_MUTE} — after that you'll be muted for a few minutes."
        )
