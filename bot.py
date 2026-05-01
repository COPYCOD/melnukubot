import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from python_aternos import Client, ServerStatus

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────
# Ці значення задаються в Railway → Variables (або в .env локально)
# НЕ вписуй реальні дані сюди — тільки через змінні середовища!
#
#   BOT_TOKEN  ← токен від @BotFather
#   AT_USER    ← логін Aternos (ім'я користувача)
#   AT_PASS    ← пароль Aternos
#
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
AT_USER: str   = os.environ["AT_USER"]
AT_PASS: str   = os.environ["AT_PASS"]

# ─── Router ─────────────────────────────────────────────────────────────────
router = Router()

# ─── Aternos helpers ────────────────────────────────────────────────────────

def get_server():
    client = Client.from_credentials(AT_USER, AT_PASS)
    servers = client.list_servers()
    if not servers:
        raise RuntimeError("No servers found on this Aternos account.")
    server = servers[0]
    server.fetch()
    return server


def status_label(server) -> str:
    status_map = {
        ServerStatus.ON:        "🟢 Онлайн",
        ServerStatus.OFF:       "🔴 Офлайн",
        ServerStatus.STARTING:  "🟡 Запускається",
        ServerStatus.STOPPING:  "🟠 Зупиняється",
        ServerStatus.LOADING:   "🔵 Завантажується",
        ServerStatus.PREPARING: "🔵 Підготовка",
        ServerStatus.QUEUE:     "⏳ У черзі",
        ServerStatus.SAVING:    "💾 Зберігається",
    }
    return status_map.get(server.status, f"❓ {server.status}")


# ─── Handlers ───────────────────────────────────────────────────────────────

@router.message(Command("startserver"))
async def cmd_startserver(message: Message) -> None:
    await message.answer("⏳ Перевіряю стан сервера...")
    try:
        server = await asyncio.to_thread(get_server)

        if server.status in (ServerStatus.ON, ServerStatus.STARTING):
            await message.answer(
                f"ℹ️ Сервер вже *{status_label(server)}* — нічого запускати.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        if server.status == ServerStatus.QUEUE:
            await message.answer("⏳ Сервер вже *у черзі на запуск*. Зачекай.", parse_mode=ParseMode.MARKDOWN)
            return

        await asyncio.to_thread(server.start)
        await message.answer("🚀 Команда запуску надіслана! Сервер незабаром онлайн.")

    except Exception as exc:
        logger.exception("startserver error")
        await message.answer(f"❌ Помилка: `{exc}`", parse_mode=ParseMode.MARKDOWN)


@router.message(Command("offserver"))
async def cmd_offserver(message: Message) -> None:
    await message.answer("⏳ Зупиняю сервер...")
    try:
        server = await asyncio.to_thread(get_server)

        if server.status in (ServerStatus.OFF, ServerStatus.STOPPING):
            await message.answer(
                f"ℹ️ Сервер вже *{status_label(server)}*.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await asyncio.to_thread(server.stop)
        await message.answer("🛑 Команда зупинки надіслана!")

    except Exception as exc:
        logger.exception("offserver error")
        await message.answer(f"❌ Помилка: `{exc}`", parse_mode=ParseMode.MARKDOWN)


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    await message.answer("⏳ Отримую список гравців...")
    try:
        server = await asyncio.to_thread(get_server)

        if server.status != ServerStatus.ON:
            await message.answer(
                f"⚠️ Сервер *{status_label(server)}* — список гравців недоступний.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        players = server.players
        if not players:
            await message.answer("👻 Зараз на сервері нікого немає.")
        else:
            names = "\n".join(f"  • `{p}`" for p in players)
            await message.answer(
                f"👥 *Гравці онлайн* ({len(players)}/{server.slots}):\n{names}",
                parse_mode=ParseMode.MARKDOWN,
            )

    except Exception as exc:
        logger.exception("list error")
        await message.answer(f"❌ Помилка: `{exc}`", parse_mode=ParseMode.MARKDOWN)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer("⏳ Збираю інформацію...")
    try:
        server = await asyncio.to_thread(get_server)

        player_count = len(server.players) if server.status == ServerStatus.ON else 0
        slots = server.slots or "?"

        text = (
            f"📊 *Статус сервера*\n\n"
            f"🏷 Адреса:    `{server.address}`\n"
            f"📡 Стан:      {status_label(server)}\n"
            f"🎮 Версія:    `{server.version}`\n"
            f"👥 Гравців:   `{player_count}/{slots}`\n"
        )
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)

    except Exception as exc:
        logger.exception("status error")
        await message.answer(f"❌ Помилка: `{exc}`", parse_mode=ParseMode.MARKDOWN)


# ─── Entry point ────────────────────────────────────────────────────────────

async def main() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot started")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
