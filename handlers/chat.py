"""ШІ-співрозмовник: вільна розмова, рольові сценарії, голосові, підсумок розмови."""
import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import ai
import db
import prompts
from content import SCENARIOS
from keyboards import BTN_CHAT, BTN_SCENARIOS, USER_TEXT, chat_reply_kb, scenarios_kb
from utils import cut, esc

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == "private")

# Остання відповідь ШІ (для кнопки "Озвучити") і слова з підсумку (для кнопки "Додати")
last_reply: dict[int, str] = {}
pending_words: dict[int, list[dict]] = {}

AI_ERROR = "⚠️ ШІ зараз недоступний або перевищено ліміт запитів. Спробуй ще раз за хвилинку 🙏"


def _build_messages(user: dict, history: list[dict], voice: bool = False) -> list[dict]:
    messages = [{"role": "system", "content": prompts.tutor_system(user, voice)}]
    if history and history[0]["role"] == "assistant":
        messages.append({"role": "user", "content": "Hi!"})
    messages.extend(history)
    if history and history[-1]["role"] == "user":
        messages.append({"role": "system", "content": prompts.TUTOR_REMINDER})
    return messages


def _split_reply(raw: str) -> tuple[str, str]:
    reply, corrections = raw, ""
    if prompts.CORRECTIONS_MARK in raw:
        reply, corrections = raw.split(prompts.CORRECTIONS_MARK, 1)
    # Рядки з ❌ — це виправлення, навіть якщо модель забула роздільник
    reply_lines, corr_lines = [], []
    for line in reply.splitlines():
        (corr_lines if line.lstrip().startswith("❌") else reply_lines).append(line)
    for line in corrections.splitlines():
        # модель іноді пише "### Corrections" як заголовок — прибираємо його
        if line.strip() and not line.strip().lower().startswith("corrections"):
            corr_lines.append(line)
    return "\n".join(reply_lines).strip(), "\n".join(l.strip() for l in corr_lines).strip()


async def send_voice(message: Message, text: str):
    try:
        audio = await ai.tts(text)
        await message.answer_voice(BufferedInputFile(audio, filename="reply.mp3"))
    except Exception:
        log.exception("TTS error")
        await message.answer("⚠️ Не вдалося озвучити відповідь.")


async def process_user_text(message: Message, text: str, voice: bool = False):
    uid = message.from_user.id
    user = db.ensure_user(uid, message.from_user.first_name)
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    history = db.get_history(uid) + [{"role": "user", "content": text}]
    try:
        raw = await ai.chat(_build_messages(user, history, voice))
    except Exception:
        log.exception("AI error")
        await message.answer(AI_ERROR)
        return

    reply, corrections = _split_reply(raw)
    db.add_history(uid, "user", text)
    db.add_history(uid, "assistant", reply)
    db.register_activity(uid, xp=2, chat_message=True)
    last_reply[uid] = reply

    out = ""
    if voice:
        out += f"🎙 <i>Ти сказав(ла): {esc(text)}</i>\n\n"
    out += esc(reply)
    if corrections:
        out += f"\n\n✏️ <b>Виправлення:</b>\n{esc(corrections)}"
    await message.answer(cut(out), reply_markup=chat_reply_kb(show_tts=not user["voice_reply"]))

    if user["voice_reply"]:
        await send_voice(message, reply)


# ---------- меню ----------

@router.message(F.text == BTN_CHAT)
async def free_chat(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    db.ensure_user(uid, message.from_user.first_name)
    db.update_user(uid, scenario=None)
    db.clear_history(uid)
    await message.answer(
        "💬 <b>Вільна розмова</b>\n\n"
        "Пиши мені що завгодно англійською або надішли 🎙 голосове — я відповім і виправлю помилки.\n"
        "Не знаєш, з чого почати? Наприклад: <i>What did you do last weekend?</i>\n\n"
        "🏁 /end — завершити й отримати відгук"
    )


@router.message(F.text == BTN_SCENARIOS)
async def scenarios(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎭 <b>Рольові сценарії</b>\n\nОбери ситуацію — ШІ зіграє роль, а ти практикуєш реальний діалог:",
        reply_markup=scenarios_kb(),
    )


@router.callback_query(F.data.startswith("sc:"))
async def start_scenario(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    key = cb.data.split(":")[1]
    if key not in SCENARIOS:
        await cb.answer()
        return
    uid = cb.from_user.id
    db.ensure_user(uid, cb.from_user.first_name)
    db.update_user(uid, scenario=key)
    db.clear_history(uid)
    user = db.get_user(uid)
    await cb.answer()
    await cb.message.answer(f"🎬 Сценарій: <b>{SCENARIOS[key][0]}</b>\nВідповідай англійською! /end — завершити.")
    await cb.message.bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)

    try:
        opening = await ai.chat([
            {"role": "system", "content": prompts.tutor_system(user)},
            {"role": "user", "content": prompts.scenario_opening()},
        ])
    except Exception:
        log.exception("AI error")
        await cb.message.answer(AI_ERROR)
        return

    opening, _ = _split_reply(opening)
    db.add_history(uid, "assistant", opening)
    last_reply[uid] = opening
    await cb.message.answer(esc(opening), reply_markup=chat_reply_kb(show_tts=not user["voice_reply"]))
    if user["voice_reply"]:
        await send_voice(cb.message, opening)


# ---------- кнопки під відповіддю ----------

@router.callback_query(F.data == "chat:tts")
async def tts_last(cb: CallbackQuery):
    text = last_reply.get(cb.from_user.id)
    await cb.answer()
    if text:
        await cb.message.bot.send_chat_action(cb.message.chat.id, ChatAction.RECORD_VOICE)
        await send_voice(cb.message, text)


async def _finish(message: Message, uid: int):
    user = db.ensure_user(uid, message.chat.first_name or "")
    history = db.get_history(uid, 30)
    if sum(1 for h in history if h["role"] == "user") < 2:
        await message.answer("Поспілкуйся ще трохи (хоча б 2 повідомлення), щоб я міг дати відгук 🙂")
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        data = await ai.ask_json(prompts.summary(history, user["level"]))
    except Exception:
        log.exception("AI error")
        await message.answer(AI_ERROR)
        return

    text = f"🏁 <b>Підсумок розмови</b>\n\n⭐ Оцінка: <b>{esc(data.get('score', '?'))}/10</b>\n\n{esc(data.get('feedback', ''))}"
    mistakes = data.get("mistakes") or []
    if mistakes:
        text += "\n\n❗ <b>Над чим попрацювати:</b>\n" + "\n".join(f"• {esc(m)}" for m in mistakes)
    words = [w for w in (data.get("words") or []) if isinstance(w, dict) and w.get("word")]
    kb = None
    if words:
        text += "\n\n📖 <b>Корисні слова з цієї теми:</b>\n" + "\n".join(
            f"• <b>{esc(w['word'])}</b> — {esc(w.get('translation', ''))}" for w in words
        )
        pending_words[uid] = words
        kb = InlineKeyboardBuilder().button(text="➕ Додати слова у словник", callback_data="chat:addwords").as_markup()

    db.update_user(uid, scenario=None)
    db.clear_history(uid)
    db.register_activity(uid, xp=10)
    await message.answer(cut(text), reply_markup=kb)


@router.message(Command("end"))
async def cmd_end(message: Message, state: FSMContext):
    await state.clear()
    await _finish(message, message.from_user.id)


@router.callback_query(F.data == "chat:end")
async def cb_end(cb: CallbackQuery):
    await cb.answer()
    await _finish(cb.message, cb.from_user.id)


@router.callback_query(F.data == "chat:addwords")
async def add_summary_words(cb: CallbackQuery):
    uid = cb.from_user.id
    words = pending_words.pop(uid, [])
    added = 0
    for w in words:
        if not db.word_exists(uid, w["word"]):
            db.add_word(uid, w["word"], w.get("translation", ""), example=w.get("example", ""))
            added += 1
    await cb.answer(f"Додано слів: {added} ✅" if words else "Слова вже додано", show_alert=True)
    await cb.message.edit_reply_markup(reply_markup=None)


# ---------- повідомлення користувача ----------

@router.message(F.voice | F.audio)
async def voice_message(message: Message, state: FSMContext):
    await state.clear()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        media = message.voice or message.audio
        buf = await message.bot.download(media)
        text = await ai.transcribe(buf.read(), "voice.ogg" if message.voice else (media.file_name or "audio.mp3"))
    except Exception:
        log.exception("Transcription error")
        await message.answer("⚠️ Не вдалося розпізнати голосове. Спробуй ще раз або напиши текстом.")
        return
    if not text:
        await message.answer("🤔 Я нічого не почув. Спробуй сказати ще раз.")
        return
    await process_user_text(message, text, voice=True)


@router.message(StateFilter(None), USER_TEXT)
async def text_message(message: Message):
    await process_user_text(message, message.text)
