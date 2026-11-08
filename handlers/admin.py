from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

import config
import db

router = Router()
router.message.filter(F.chat.type == "private", F.from_user.id.in_(config.ADMIN_IDS))


async def track_activity(handler, event, data):
    """Запам'ятовує, що людина сьогодні користувалась ботом в особистих повідомленнях."""
    message = event if isinstance(event, Message) else event.message
    if event.from_user and message and message.chat.type == "private":
        db.log_activity(event.from_user.id)
    return await handler(event, data)


def _short_date(day: str) -> str:
    return date.fromisoformat(day).strftime("%d.%m")


def analytics_text(s: dict) -> str:
    days = "\n".join(f"{_short_date(day)}: <b>{count}</b>" for day, count in s["by_day"])
    since = f"\n\nℹ️ Дані зібрано з {_short_date(s['since'])}" if s["since"] else ""
    return (
        "📈 <b>Аналітика бота</b>\n\n"
        f"👥 Усього користувачів: <b>{s['users']}</b>\n"
        f"🆕 Нових: сьогодні <b>{s['new_today']}</b>, за 7 днів <b>{s['new_7d']}</b>\n"
        f"🔥 Активних: сьогодні <b>{s['active_today']}</b>, за 7 днів <b>{s['active_7d']}</b>, "
        f"за 30 днів <b>{s['active_30d']}</b>\n\n"
        f"💬 Повідомлень ШІ-співрозмовнику: <b>{s['messages']}</b>\n"
        f"📖 Слів у словниках: <b>{s['words']}</b>\n"
        f"🏠 Груп: <b>{s['groups']}</b>\n\n"
        f"<b>Активних по днях:</b>\n{days}"
        f"{since}"
    )


@router.message(Command("analytics"))
async def analytics(message: Message):
    await message.answer(analytics_text(db.analytics()))
