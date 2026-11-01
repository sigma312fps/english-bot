"""Посібник з граматики: пояснення тем і вправи з перевіркою ШІ."""
import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import ai
import db
import prompts
from content import GRAMMAR
from keyboards import BTN_GRAMMAR, USER_TEXT, grammar_kb, grammar_topic_kb
from utils import cut, esc

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == "private")

# Кеш пояснень, щоб не витрачати ліміт ШІ на однакові запити
_explanations: dict[tuple[str, str], str] = {}


class GrammarSG(StatesGroup):
    answering = State()


@router.message(F.text == BTN_GRAMMAR)
async def grammar_menu(message: Message, state: FSMContext):
    await state.clear()
    db.ensure_user(message.from_user.id, message.from_user.first_name)
    await message.answer("📚 <b>Граматика</b>\n\nОбери тему — я поясню її і дам вправу:", reply_markup=grammar_kb())


@router.callback_query(F.data == "gr:list")
async def cb_list(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    await cb.message.answer("📚 Обери тему:", reply_markup=grammar_kb())


@router.callback_query(F.data.startswith("gr:t:"))
async def cb_topic(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    key = cb.data.split(":")[2]
    if key not in GRAMMAR:
        await cb.answer()
        return
    user = db.ensure_user(cb.from_user.id, cb.from_user.first_name)
    await cb.answer()
    await cb.message.bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)

    cache_key = (key, user["level"])
    if cache_key not in _explanations:
        try:
            _explanations[cache_key] = await ai.ask(prompts.grammar_explain(key, user["level"]), temperature=0.3,
                                                    max_tokens=1200)
        except Exception:
            log.exception("AI error")
            await cb.message.answer("⚠️ ШІ зараз недоступний, спробуй пізніше.")
            return
    text = f"📚 <b>{esc(GRAMMAR[key][0])}</b>\n\n{esc(_explanations[cache_key])}"
    await cb.message.answer(cut(text), reply_markup=grammar_topic_kb(key))


@router.callback_query(F.data.startswith("gr:ex:"))
async def cb_exercise(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[2]
    if key not in GRAMMAR:
        await cb.answer()
        return
    user = db.ensure_user(cb.from_user.id, cb.from_user.first_name)
    await cb.answer()
    await cb.message.bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)
    try:
        exercise = await ai.ask(prompts.grammar_exercise(key, user["level"]), temperature=0.9)
    except Exception:
        log.exception("AI error")
        await cb.message.answer("⚠️ ШІ зараз недоступний, спробуй пізніше.")
        return
    await state.set_state(GrammarSG.answering)
    await state.update_data(topic=key, exercise=exercise)
    await cb.message.answer(
        f"📝 <b>Вправа: {esc(GRAMMAR[key][0])}</b>\n\n{esc(exercise)}\n\n"
        "✍️ Надішли відповіді одним повідомленням, наприклад:\n<code>1. goes\n2. are playing\n…</code>"
    )


@router.message(GrammarSG.answering, USER_TEXT)
async def check_answers(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    key = data.get("topic")
    if key not in GRAMMAR:
        return
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        result = await ai.ask(prompts.grammar_check(key, data["exercise"], message.text), temperature=0.2)
    except Exception:
        log.exception("AI error")
        await message.answer("⚠️ ШІ зараз недоступний, спробуй пізніше.")
        return
    db.register_activity(message.from_user.id, xp=5)
    b = InlineKeyboardBuilder()
    b.button(text="📝 Ще вправа", callback_data=f"gr:ex:{key}")
    b.button(text="🔙 До тем", callback_data="gr:list")
    await message.answer(f"🧾 <b>Перевірка</b>\n\n{esc(result)}", reply_markup=b.as_markup())
