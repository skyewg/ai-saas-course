import asyncio
import logging
import os
import re
from decimal import Decimal
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

from database import save_expense


load_dotenv(Path(__file__).with_name(".env"))

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    raise RuntimeError("BOT_TOKEN is not configured")

dispatcher = Dispatcher()


class ExpenseForm(StatesGroup):
    waiting_for_expense = State()


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Витрати")]],
    resize_keyboard=True,
)


@dispatcher.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привіт! Я бот Finansovik.",
        reply_markup=main_keyboard,
    )


@dispatcher.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Натисни «Витрати» або напиши /expense 120 кава. "
        "Щоб скасувати введення, надішли /cancel.",
        reply_markup=main_keyboard,
    )


@dispatcher.message(Command("expense"))
async def expense_command(message: Message, command: CommandObject, state: FSMContext) -> None:
    if await add_expense(message, command.args or ""):
        await state.clear()


@dispatcher.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Введення витрати скасовано.", reply_markup=main_keyboard)


@dispatcher.message(F.text == "Витрати")
async def expense_button(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseForm.waiting_for_expense)
    await message.answer("Напиши суму й категорію, наприклад: 120 кава. Щоб скасувати, надішли /cancel.")


@dispatcher.message(ExpenseForm.waiting_for_expense, F.text.startswith("/"))
async def unknown_command_during_expense(message: Message) -> None:
    await message.answer("Невідома команда. Введи суму й категорію або надішли /cancel.")


@dispatcher.message(ExpenseForm.waiting_for_expense, F.text)
async def expense_from_button(message: Message, state: FSMContext) -> None:
    if await add_expense(message, message.text or ""):
        await state.clear()


@dispatcher.message(ExpenseForm.waiting_for_expense)
async def expense_non_text(message: Message) -> None:
    await message.answer("Надішли суму й категорію текстом, наприклад: 120 кава.")


async def add_expense(message: Message, value: str) -> bool:
    parts = value.split(maxsplit=1)
    if len(parts) != 2 or not re.fullmatch(r"[0-9]{1,10}(?:[.,][0-9]{1,2})?", parts[0]):
        await message.answer("Вкажи суму та категорію, наприклад: 120 кава")
        return False

    amount = Decimal(parts[0].replace(",", "."))
    category = parts[1].strip().casefold()
    if amount <= 0 or not category or len(category) > 100:
        await message.answer("Сума має бути більшою за нуль, а категорія — до 100 символів.")
        return False

    if message.from_user is None:
        await message.answer("Не вдалося визначити користувача. Спробуй написати боту особисто.")
        return False

    try:
        await asyncio.to_thread(
            save_expense, message.from_user.id, message.from_user.username, amount, category
        )
    except Exception as error:
        logging.error("Не вдалося зберегти витрату: %s", type(error).__name__)
        await message.answer("Не вдалося зберегти витрату. Спробуй пізніше.")
        return False

    await message.answer(f"Витрату додано: {amount:.2f} — {category}.")
    return True


async def main() -> None:
    bot = Bot(token=bot_token)
    logging.info("Бот працює")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
