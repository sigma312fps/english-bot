"""Особистий словник і тренування слів."""
import logging
import random
import re

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import ai
import daily
import db
import prompts
from keyboards import BTN_TRAIN, BTN_VOCAB, USER_TEXT, next_stop_kb, training_kb, vocab_kb
from utils import esc

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == "private")

PAGE_SIZE = 15


class VocabSG(StatesGroup):
    adding = State()
    deleting = State()
    sentence = State()


def _say_kb(word_id: int):
    return InlineKeyboardBuilder().button(text="🔊 Вимова", callback_data=f"say:{word_id}").as_markup()


def _progress(box: int) -> str:
    return "🟢" if box >= db.LEARNED_BOX else "🟡" if box >= 2 else "🔴"


# ---------- словник ----------

@router.message(F.text == BTN_VOCAB)
async def vocab_menu(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    db.ensure_user(uid, message.from_user.first_name)
    await message.answer(
        "📖 <b>Мій словник</b>\n\n"
        f"Слів: <b>{db.count_words(uid)}</b> · вивчено: <b>{db.count_learned(uid)}</b> · "
        f"на повторення: <b>{db.count_due(uid)}</b>\n\n"
        "Додавай слова англійською або українською — ШІ сам підбере переклад, транскрипцію і приклад.\n"
        "Швидко: <code>/add apple, ризикувати, look forward to</code>",
        reply_markup=vocab_kb(),
    )


async def add_words(message: Message, uid: int, raw: str):
    items = [w.strip() for w in re.split(r"[,;\n]", raw) if w.strip()][:10]
    if not items:
        await message.answer("Напиши слово або кілька слів через кому.")
        return
    user = db.ensure_user(uid, message.chat.first_name or "")
    for item in items:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        try:
            data = await ai.ask_json(prompts.enrich_word(item, user["level"]))
        except Exception:
            log.exception("AI error")
            await message.answer(f"⚠️ Не вдалося обробити «{esc(item)}», спробуй пізніше.")
            continue
        if data.get("error") or not data.get("word"):
            await message.answer(f"🤔 «{esc(item)}»: {esc(data.get('error', 'не схоже на слово'))}")
            continue
        if db.word_exists(uid, data["word"]):
            await message.answer(f"ℹ️ «{esc(data['word'])}» вже є у словнику.")
            continue
        word_id = db.add_word(uid, data["word"], data.get("translation", ""), data.get("transcription", ""),
                              data.get("example", ""), data.get("example_uk", ""))
        db.register_activity(uid, xp=1)
        await message.answer("✅ Додано:\n\n" + daily.word_card(data), reply_markup=_say_kb(word_id))


@router.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    if command.args:
        await add_words(message, message.from_user.id, command.args)
    else:
        await state.set_state(VocabSG.adding)
        await message.answer("✍️ Напиши слово (або кілька через кому), яке хочеш додати:")


@router.callback_query(F.data == "voc:add")
async def cb_add(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(VocabSG.adding)
    await cb.message.answer("✍️ Напиши слово (або кілька через кому), яке хочеш додати:")


@router.message(VocabSG.adding, USER_TEXT)
async def adding(message: Message, state: FSMContext):
    await state.clear()
    await add_words(message, message.from_user.id, message.text)


@router.callback_query(F.data.startswith("voc:list:"))
async def cb_list(cb: CallbackQuery):
    uid = cb.from_user.id
    page = int(cb.data.split(":")[2])
    total = db.count_words(uid)
    await cb.answer()
    if total == 0:
        await cb.message.answer("Словник поки порожній. Натисни «➕ Додати слово» 🙂")
        return
    words = db.list_words(uid, page * PAGE_SIZE, PAGE_SIZE)
    lines = [
        f"{page * PAGE_SIZE + i + 1}. {_progress(w['box'])} <b>{esc(w['word'])}</b> — {esc(w['translation'])}"
        for i, w in enumerate(words)
    ]
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    b = InlineKeyboardBuilder()
    if page > 0:
        b.button(text="⬅️", callback_data=f"voc:list:{page - 1}")
    if page < pages - 1:
        b.button(text="➡️", callback_data=f"voc:list:{page + 1}")
    text = (f"📋 <b>Слова</b> (стор. {page + 1}/{pages})\n🔴 нове · 🟡 вчу · 🟢 вивчено\n\n" + "\n".join(lines))
    if cb.message.text and cb.message.text.startswith("📋"):
        await cb.message.edit_text(text, reply_markup=b.as_markup())
    else:
        await cb.message.answer(text, reply_markup=b.as_markup())


@router.callback_query(F.data == "voc:del")
async def cb_del(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(VocabSG.deleting)
    await cb.message.answer("🗑 Напиши англійське слово, яке треба видалити:")


@router.message(VocabSG.deleting, USER_TEXT)
async def deleting(message: Message, state: FSMContext):
    await state.clear()
    if db.delete_word_by_text(message.from_user.id, message.text):
        await message.answer(f"🗑 «{esc(message.text)}» видалено.")
    else:
        await message.answer(f"Слова «{esc(message.text)}» немає у словнику.")


@router.callback_query(F.data.startswith("say:"))
async def cb_say(cb: CallbackQuery):
    w = db.get_word(cb.from_user.id, int(cb.data.split(":")[1]))
    await cb.answer()
    if not w:
        return
    await cb.message.bot.send_chat_action(cb.message.chat.id, ChatAction.RECORD_VOICE)
    text = w["word"] + (". " + w["example"] if w["example"] else "")
    try:
        audio = await ai.tts(text)
        await cb.message.answer_voice(BufferedInputFile(audio, filename="word.mp3"))
    except Exception:
        log.exception("TTS error")
        await cb.message.answer("⚠️ Не вдалося озвучити.")


# ---------- слово дня ----------

async def _send_wod(message: Message):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        w = await daily.word_of_day()
    except Exception:
        log.exception("AI error")
        await message.answer("⚠️ Не вдалося отримати слово дня, спробуй пізніше.")
        return
    kb = InlineKeyboardBuilder().button(text="➕ У словник", callback_data="wod:add").as_markup()
    await message.answer("🌟 <b>Слово дня</b>\n\n" + daily.word_card(w), reply_markup=kb)


@router.message(Command("word"))
async def cmd_word(message: Message):
    await _send_wod(message)


@router.callback_query(F.data == "voc:wod")
async def cb_wod(cb: CallbackQuery):
    await cb.answer()
    await _send_wod(cb.message)


@router.callback_query(F.data == "wod:add")
async def cb_wod_add(cb: CallbackQuery):
    uid = cb.from_user.id
    db.ensure_user(uid, cb.from_user.first_name)
    try:
        w = await daily.word_of_day()
    except Exception:
        await cb.answer("Спробуй пізніше", show_alert=True)
        return
    if not w.get("word") or db.word_exists(uid, w["word"]):
        await cb.answer("Це слово вже є у словнику 👍", show_alert=True)
        return
    db.add_word(uid, w["word"], w.get("translation", ""), w.get("transcription", ""),
                w.get("example", ""), w.get("example_uk", ""))
    await cb.answer("Додано у словник ✅", show_alert=True)


# ---------- тренування ----------

@router.message(F.text == BTN_TRAIN)
async def training_menu(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    db.ensure_user(uid, message.from_user.first_name)
    await message.answer(
        "🧠 <b>Тренування слів</b>\n\n"
        f"На повторення сьогодні: <b>{db.count_due(uid)}</b>\n\n"
        "🃏 Картки — інтервальне повторення: слова, які ти знаєш, з'являються рідше\n"
        "✅ Квіз — обери правильний переклад\n"
        "✍️ Речення — склади речення зі словом, ШІ перевірить",
        reply_markup=training_kb(),
    )


@router.callback_query(F.data == "tr:stop")
async def cb_stop(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer("Тренування завершено 💪")
    await cb.message.edit_reply_markup(reply_markup=None)


async def _send_card(message: Message, uid: int):
    w = db.due_word(uid)
    if not w:
        text = ("🎉 На сьогодні все повторено! Повертайся завтра або додай нові слова."
                if db.count_words(uid) else "Словник порожній — спочатку додай слова в 📖 Мій словник.")
        await message.answer(text)
        return
    b = InlineKeyboardBuilder()
    b.button(text="👀 Показати переклад", callback_data=f"card:show:{w['id']}")
    b.button(text="⏹ Стоп", callback_data="tr:stop")
    b.adjust(1)
    transcription = f"  {esc(w['transcription'])}" if w["transcription"] else ""
    await message.answer(f"🃏 <b>{esc(w['word'])}</b>{transcription}\n\nЗгадай переклад 🤔", reply_markup=b.as_markup())


@router.callback_query(F.data == "tr:cards")
async def cb_cards(cb: CallbackQuery):
    await cb.answer()
    await _send_card(cb.message, cb.from_user.id)


@router.callback_query(F.data.startswith("card:"))
async def cb_card(cb: CallbackQuery):
    _, action, word_id = cb.data.split(":")
    uid = cb.from_user.id
    w = db.get_word(uid, int(word_id))
    await cb.answer()
    if not w:
        return
    if action == "show":
        b = InlineKeyboardBuilder()
        b.button(text="✅ Знаю", callback_data=f"card:yes:{w['id']}")
        b.button(text="❌ Не пам'ятаю", callback_data=f"card:no:{w['id']}")
        b.button(text="🔊", callback_data=f"say:{w['id']}")
        b.adjust(2, 1)
        await cb.message.edit_text("🃏 " + daily.word_card(w), reply_markup=b.as_markup())
        return
    correct = action == "yes"
    db.review_word(uid, w["id"], correct)
    db.register_activity(uid, xp=1)
    await cb.message.edit_text("🃏 " + daily.word_card(w) + ("\n\n✅ Знаю" if correct else "\n\n❌ Повторимо ще"))
    await _send_card(cb.message, uid)


@router.callback_query(F.data == "tr:quiz")
async def cb_quiz(cb: CallbackQuery):
    uid = cb.from_user.id
    await cb.answer()
    words = db.random_words(uid, 4)
    if len(words) < 4:
        await cb.message.answer("Для квізу потрібно хоча б 4 слова у словнику 📖")
        return
    target = random.choice(words)
    random.shuffle(words)
    b = InlineKeyboardBuilder()
    for w in words:
        b.button(text=w["translation"][:60], callback_data=f"qz:{target['id']}:{w['id']}")
    b.adjust(1)
    await cb.message.answer(f"✅ Як перекладається <b>{esc(target['word'])}</b>?", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("qz:"))
async def cb_quiz_answer(cb: CallbackQuery):
    _, target_id, chosen_id = cb.data.split(":")
    uid = cb.from_user.id
    w = db.get_word(uid, int(target_id))
    await cb.answer()
    if not w:
        return
    correct = target_id == chosen_id
    db.review_word(uid, w["id"], correct)
    db.register_activity(uid, xp=2 if correct else 0)
    head = "✅ Правильно!" if correct else "❌ Ні, правильна відповідь:"
    await cb.message.edit_text(
        f"{head}\n<b>{esc(w['word'])}</b> — {esc(w['translation'])}", reply_markup=next_stop_kb("tr:quiz")
    )


@router.callback_query(F.data == "tr:sentence")
async def cb_sentence(cb: CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    await cb.answer()
    w = db.due_word(uid) or (db.random_words(uid, 1) or [None])[0]
    if not w:
        await cb.message.answer("Словник порожній — спочатку додай слова в 📖 Мій словник.")
        return
    await state.set_state(VocabSG.sentence)
    await state.update_data(word_id=w["id"])
    await cb.message.answer(
        f"✍️ Склади речення англійською зі словом <b>{esc(w['word'])}</b> ({esc(w['translation'])}):"
    )


@router.message(VocabSG.sentence, USER_TEXT)
async def sentence_answer(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    await state.clear()
    w = db.get_word(uid, data.get("word_id", 0))
    if not w:
        return
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        result = await ai.ask(prompts.check_sentence(w["word"], w["translation"], message.text), temperature=0.3)
    except Exception:
        log.exception("AI error")
        await message.answer("⚠️ ШІ зараз недоступний, спробуй пізніше.")
        return
    db.register_activity(uid, xp=3)
    db.review_word(uid, w["id"], not result.startswith("❌"))
    await message.answer(esc(result), reply_markup=next_stop_kb("tr:sentence"))
