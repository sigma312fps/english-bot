"""Анонімний чат 1-на-1 з іншим користувачем — тільки англійською."""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import ai
import db
import prompts
from content import LEVELS
from keyboards import BTN_PARTNER, MENU_TEXTS
from utils import esc, is_mostly_cyrillic

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == "private")

queue: list[int] = []
pairs: dict[int, int] = {}


def _level(uid: int) -> str:
    user = db.get_user(uid)
    return LEVELS.get(user["level"], "?") if user else "?"


async def _search(message: Message, uid: int):
    if uid in pairs:
        await message.answer("Ти вже в розмові 🙂 /stop — завершити, /next — інший співрозмовник.")
        return
    if uid in queue:
        await message.answer("🔎 Все ще шукаю… /stop — скасувати.")
        return
    if queue:
        other = queue.pop(0)
        pairs[uid], pairs[other] = other, uid
        text = ("🎉 <b>Співрозмовника знайдено!</b> Рівень: {level}\n\n"
                "🇬🇧 Спілкуйтесь <b>тільки англійською</b>. Say hi! 👋\n"
                "/stop — завершити · /next — інший співрозмовник")
        await message.answer(text.format(level=_level(other)))
        await message.bot.send_message(other, text.format(level=_level(uid)))
        return
    queue.append(uid)
    await message.answer(
        "🔎 Шукаю співрозмовника… Щойно хтось ще натисне «👥 Співрозмовник», я вас з'єднаю.\n/stop — скасувати."
    )


async def _stop(message: Message, uid: int, notify_self: bool = True) -> bool:
    if uid in queue:
        queue.remove(uid)
        if notify_self:
            await message.answer("Пошук скасовано.")
        return True
    other = pairs.pop(uid, None)
    if other is None:
        return False
    pairs.pop(other, None)
    if notify_self:
        await message.answer("👋 Розмову завершено. Натисни «👥 Співрозмовник», щоб знайти нового.")
    try:
        await message.bot.send_message(other, "👋 Співрозмовник завершив розмову. Натисни «👥 Співрозмовник», щоб знайти нового.")
    except Exception:
        pass
    return True


@router.message(F.text == BTN_PARTNER)
async def find_partner(message: Message, state: FSMContext):
    await state.clear()
    db.ensure_user(message.from_user.id, message.from_user.first_name)
    await _search(message, message.from_user.id)


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    if not await _stop(message, message.from_user.id):
        await message.answer("Ти зараз не в розмові з людиною.")


@router.message(Command("next"))
async def cmd_next(message: Message):
    await _stop(message, message.from_user.id, notify_self=False)
    await _search(message, message.from_user.id)


def _in_pair(message: Message) -> bool:
    if message.from_user.id not in pairs:
        return False
    text = message.text or ""
    return text not in MENU_TEXTS and not text.startswith("/")


@router.message(F.func(_in_pair))
async def relay(message: Message):
    other = pairs[message.from_user.id]
    if message.text and is_mostly_cyrillic(message.text):
        # Не пересилаємо — підказуємо, як сказати англійською
        try:
            hint = await ai.ask(prompts.translate_to_english(message.text), temperature=0.3, max_tokens=200)
            await message.answer(f"🇬🇧 English only, please! Спробуй так:\n<i>{esc(hint)}</i>")
        except Exception:
            await message.answer("🇬🇧 English only, please! Спробуй написати англійською 🙂")
        return
    try:
        await message.bot.copy_message(other, message.chat.id, message.message_id)
        db.register_activity(message.from_user.id, xp=1)
    except Exception:
        log.exception("Relay error")
        await _stop(message, message.from_user.id)
