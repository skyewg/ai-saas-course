import asyncio
import logging
import os
import re
from decimal import Decimal
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from dotenv import load_dotenv

from database import save_expense


load_dotenv(Path(__file__).with_name(".env"))

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    raise RuntimeError("BOT_TOKEN is not configured")

dispatcher = Dispatcher()

@dispatcher.message(CommandStart())
async def start_command(message: Message) -> None:
    await message.answer(
        "Привіт! Я бот Finansovik.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dispatcher.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Це бот Finansovik. Щоб додати витрату, напиши: /expense 120 кава"
    )


@dispatcher.message(Command("expense"))
async def expense_command(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) != 2 or not re.fullmatch(r"[0-9]{1,10}(?:[.,][0-9]{1,2})?", parts[0]):
        await message.answer("Вкажи суму та категорію, наприклад: /expense 120 кава")
        return

    amount = Decimal(parts[0].replace(",", "."))
    category = parts[1].strip().casefold()
    if amount <= 0 or not category or len(category) > 100:
        await message.answer("Сума має бути більшою за нуль, а категорія — до 100 символів.")
        return

    if message.from_user is None:
        await message.answer("Не вдалося визначити користувача. Спробуй написати боту особисто.")
        return

    try:
        await asyncio.to_thread(
            save_expense, message.from_user.id, message.from_user.username, amount, category
        )
    except Exception as error:
        logging.error("Не вдалося зберегти витрату: %s", type(error).__name__)
        await message.answer("Не вдалося зберегти витрату. Спробуй пізніше.")
        return

    await message.answer(f"Витрату додано: {amount:.2f} — {category}.")


async def main() -> None:
    bot = Bot(token=bot_token)
    logging.info("Бот працює")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
