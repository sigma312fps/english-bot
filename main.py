import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiohttp import web

import config
import db
from handlers import admin, chat, grammar, group, partner, placement, start, vocab
from scheduler import scheduler_loop

COMMANDS = [
    BotCommand(command="start", description="Почати / головне меню"),
    BotCommand(command="help", description="Довідка"),
    BotCommand(command="add", description="Додати слово у словник"),
    BotCommand(command="word", description="Слово дня"),
    BotCommand(command="club", description="Чат англійською"),
    BotCommand(command="end", description="Завершити розмову і отримати відгук"),
    BotCommand(command="test", description="Тест рівня"),
    BotCommand(command="stats", description="Мій прогрес"),
    BotCommand(command="settings", description="Налаштування"),
    BotCommand(command="stop", description="Вийти з чату зі співрозмовником"),
]


async def _health(request: web.Request) -> web.Response:
    return web.Response(text="OK — English bot is running")


async def start_web_server(port: int):
    """Маленька вебсторінка для Render: її "смикає" cron-job.org, щоб бот не засинав."""
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logging.info("Вебсторінка працює на порту %s", port)


async def main():
    # Консоль Windows за замовчуванням не вміє виводити емодзі
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN or not config.GROQ_API_KEY:
        raise SystemExit("❌ Заповніть BOT_TOKEN і GROQ_API_KEY у файлі .env (див. README.md)")

    db.init()
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    # Порядок важливий: chat.router останній, бо ловить будь-який текст
    dp.message.outer_middleware(admin.track_activity)
    dp.callback_query.outer_middleware(admin.track_activity)
    dp.include_routers(group.router, admin.router, start.router, partner.router, placement.router,
                       vocab.router, grammar.router, chat.router)

    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)
    if config.PORT:
        await start_web_server(config.PORT)
    asyncio.create_task(scheduler_loop(bot))
    logging.info("Бот запущено ✅")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
