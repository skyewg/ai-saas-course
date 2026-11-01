import asyncio
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    raise RuntimeError("BOT_TOKEN is not configured")

dispatcher = Dispatcher()


@dispatcher.message(CommandStart())
async def start_command(message: Message) -> None:
    await message.answer("Привіт! Я готовий до роботи 👋")


@dispatcher.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Я допомагаю знаходити цікаві місця поруч, де можна гуляти пішки."
    )


async def main() -> None:
    bot = Bot(token=bot_token)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
