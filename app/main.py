import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    raise RuntimeError("BOT_TOKEN is not configured")

dispatcher = Dispatcher()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚶 Знайти місця поруч")]],
    resize_keyboard=True,
)


@dispatcher.message(CommandStart())
async def start_command(message: Message) -> None:
    await message.answer(
        "Привіт! Натисни кнопку нижче, щоб почати пошук.",
        reply_markup=main_keyboard,
    )


@dispatcher.message(F.text == "🚶 Знайти місця поруч")
async def find_nearby_places(message: Message) -> None:
    await message.answer("Надішли свою геолокацію, щоб я знайшов місця поруч.")


@dispatcher.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Я допомагаю знаходити цікаві місця поруч, де можна гуляти пішки."
    )


async def main() -> None:
    bot = Bot(token=bot_token)
    logging.info("Бот працює")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
