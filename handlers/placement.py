"""Тест для визначення рівня."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db
from content import LEVELS, PLACEMENT_TEST, level_by_score
from keyboards import main_menu
from utils import esc

router = Router()


def _question(idx: int):
    q, options, _ = PLACEMENT_TEST[idx]
    b = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        b.button(text=opt, callback_data=f"pt:a:{idx}:{i}")
    b.adjust(2)
    text = f"🎯 <b>Питання {idx + 1}/{len(PLACEMENT_TEST)}</b>\n\n{esc(q)}"
    return text, b.as_markup()


async def _start(message: Message, state: FSMContext):
    await state.update_data(pt_idx=0, pt_score=0)
    text, kb = _question(0)
    await message.answer("Обери правильний варіант у кожному реченні. Питання стають складнішими 📈")
    await message.answer(text, reply_markup=kb)


@router.message(Command("test"), F.chat.type == "private")
async def cmd_test(message: Message, state: FSMContext):
    db.ensure_user(message.from_user.id, message.from_user.first_name)
    await _start(message, state)


@router.callback_query(F.data == "pt:start")
async def cb_start(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _start(cb.message, state)


@router.callback_query(F.data.startswith("pt:a:"))
async def cb_answer(cb: CallbackQuery, state: FSMContext):
    _, _, idx, opt = cb.data.split(":")
    idx, opt = int(idx), int(opt)
    data = await state.get_data()
    if data.get("pt_idx") != idx:  # повторне натискання на старе питання
        await cb.answer()
        return

    q, options, correct = PLACEMENT_TEST[idx]
    score = data.get("pt_score", 0) + (1 if opt == correct else 0)
    mark = "✅" if opt == correct else f"❌ (правильно: {esc(options[correct])})"
    await cb.message.edit_text(f"{esc(q.replace('___', options[opt]))} {mark}")
    await cb.answer()

    idx += 1
    if idx < len(PLACEMENT_TEST):
        await state.update_data(pt_idx=idx, pt_score=score)
        text, kb = _question(idx)
        await cb.message.answer(text, reply_markup=kb)
        return

    await state.update_data(pt_idx=None, pt_score=0)
    level = level_by_score(score)
    db.ensure_user(cb.from_user.id, cb.from_user.first_name)
    db.update_user(cb.from_user.id, level=level)
    db.register_activity(cb.from_user.id, xp=10)
    await cb.message.answer(
        f"🏆 Результат: <b>{score}/{len(PLACEMENT_TEST)}</b>\n"
        f"Твій рівень: <b>{LEVELS[level]}</b>\n\n"
        "Я підлаштую розмови й вправи під нього. Змінити рівень можна в ⚙️ Налаштуваннях.",
        reply_markup=main_menu(),
    )
