"""Щоденні розсилки: слово дня + нагадування про стрік, тема дня в групи."""
import asyncio
import logging
from datetime import date, datetime

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import daily
import db
from utils import esc

log = logging.getLogger(__name__)


async def send_daily(bot: Bot):
    today = date.today().isoformat()
    try:
        word = await daily.word_of_day()
        topic = await daily.topic_of_day()
    except Exception:
        log.exception("Не вдалося згенерувати щоденний контент")
        return

    kb = InlineKeyboardBuilder().button(text="➕ У словник", callback_data="wod:add").as_markup()
    for user in db.users_with_reminders():
        text = "🌟 <b>Слово дня</b>\n\n" + daily.word_card(word)
        if user["last_active"] != today:
            text += (f"\n\n🔥 Сьогодні ти ще не займався(лась)! Стрік: {user['streak']} дн. — "
                     "напиши мені щось англійською, щоб не втратити його 💪")
        try:
            await bot.send_message(user["id"], text, reply_markup=kb)
        except Exception:
            log.info("Не вдалося надіслати користувачу %s", user["id"])
        await asyncio.sleep(0.05)

    for chat_id in db.all_groups():
        try:
            await bot.send_message(chat_id, f"💭 <b>Topic of the day</b>\n\n{esc(topic)}")
        except Exception:
            db.remove_group(chat_id)


async def scheduler_loop(bot: Bot):
    last_sent = None
    while True:
        now = datetime.now()
        if now.hour == config.DAILY_HOUR and last_sent != now.date():
            last_sent = now.date()
            await send_daily(bot)
        await asyncio.sleep(60)
