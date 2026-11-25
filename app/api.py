import asyncio
import logging
import os
import json
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from aiohttp import web

from ai_analysis import AnalysisUnavailable, analyze_transactions
from database import delete_transaction, get_summary, get_transactions, save_web_transaction, update_transaction


def validate_transaction(data: object) -> tuple[str, Decimal, str, date]:
    if not isinstance(data, dict):
        raise ValueError("Надішліть дані у форматі JSON-об’єкта.")

    operation_type = data.get("type")
    types = {"expense": "expense", "income": "income", "витрата": "expense", "витрати": "expense", "дохід": "income"}
    if not isinstance(operation_type, str) or operation_type.strip().casefold() not in types:
        raise ValueError("Тип операції має бути income або expense.")
    operation_type = types[operation_type.strip().casefold()]

    amount_input = data.get("amount")
    if isinstance(amount_input, bool) or not isinstance(amount_input, (str, int, Decimal)):
        raise ValueError("Вкажіть невід’ємну суму з не більше ніж двома знаками після коми.")
    amount_text = str(amount_input).strip().replace(",", ".")
    if not re.fullmatch(r"[0-9]{1,10}(?:\.[0-9]{1,2})?", amount_text):
        raise ValueError("Вкажіть невід’ємну суму з не більше ніж двома знаками після коми.")
    amount = Decimal(amount_text)

    category = data.get("category")
    if not isinstance(category, str):
        raise ValueError("Категорія має містити лише літери.")
    category = category.strip().casefold()
    if (not category or len(category) > 100 or not any(char.isalpha() for char in category)
            or any(not (unicodedata.category(char)[0] in ("L", "M") or char in " '-’ʼ") for char in category)):
        raise ValueError("Категорія має містити лише літери, пробіли, дефіс або апостроф (до 100 символів).")

    date_input = data.get("date")
    if date_input in (None, ""):
        transaction_date = datetime.now(ZoneInfo("Europe/Kyiv")).date()
    else:
        if not isinstance(date_input, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_input):
            raise ValueError("Вкажіть дату у форматі РРРР-ММ-ДД.")
        try:
            transaction_date = date.fromisoformat(date_input)
        except ValueError:
            raise ValueError("Вкажіть дійсну дату у форматі РРРР-ММ-ДД.") from None

    return operation_type, amount, category, transaction_date


async def create_transaction_handler(request: web.Request) -> web.Response:
    if request.content_type != "application/json":
        return web.json_response({"error": "Надішліть дані у форматі JSON."}, status=415)
    try:
        data = json.loads(await request.text(), parse_float=Decimal)
        operation_type, amount, category, transaction_date = validate_transaction(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return web.json_response({"error": "Некоректний JSON."}, status=400)
    except ValueError as error:
        return web.json_response({"error": str(error)}, status=400)

    try:
        transaction_id = await asyncio.to_thread(
            save_web_transaction, operation_type, amount, category, transaction_date
        )
    except Exception as error:
        logging.error("Не вдалося зберегти транзакцію: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося зберегти транзакцію."}, status=503)

    return web.json_response({
        "id": transaction_id,
        "type": operation_type,
        "amount": format(amount, ".2f"),
        "category": category,
        "date": transaction_date.isoformat(),
    }, status=201)


async def transactions_handler(request: web.Request) -> web.Response:
    try:
        transactions = await asyncio.to_thread(get_transactions)
    except Exception as error:
        logging.error("Не вдалося отримати транзакції: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося отримати транзакції."}, status=503)

    return web.json_response(transactions)


async def summary_handler(request: web.Request) -> web.Response:
    try:
        summary = await asyncio.to_thread(get_summary)
    except Exception as error:
        logging.error("Не вдалося отримати підсумок: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося отримати підсумок."}, status=503)

    return web.json_response(summary)


async def analyze_transactions_handler(request: web.Request) -> web.Response:
    try:
        transactions = await asyncio.to_thread(get_transactions)
    except Exception as error:
        logging.error('Не вдалося отримати транзакції для аналізу: %s', type(error).__name__)
        return web.json_response({'error': 'Не вдалося отримати транзакції.'}, status=503)

    try:
        result = await asyncio.to_thread(analyze_transactions, transactions)
    except AnalysisUnavailable as error:
        return web.json_response({'error': str(error)}, status=503)
    except Exception as error:
        logging.error('Не вдалося проаналізувати транзакції: %s', type(error).__name__)
        return web.json_response({'error': 'Не вдалося проаналізувати транзакції.'}, status=503)
    return web.json_response(result)


async def delete_transaction_handler(request: web.Request) -> web.Response:
    transaction_id_text = request.match_info["id"]
    operation_types = request.query.getall("type", [])
    if (not re.fullmatch(r"[0-9]{1,19}", transaction_id_text)
            or not 0 < int(transaction_id_text) <= 9223372036854775807
            or len(operation_types) != 1 or operation_types[0] not in ("income", "expense")):
        return web.json_response({"error": "Вкажіть коректний ID і тип транзакції."}, status=400)

    try:
        deleted = await asyncio.to_thread(delete_transaction, int(transaction_id_text), operation_types[0])
    except Exception as error:
        logging.error("Не вдалося видалити транзакцію: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося видалити транзакцію."}, status=503)

    if not deleted:
        return web.json_response({"error": "Транзакцію не знайдено."}, status=404)
    return web.Response(status=204)


async def update_transaction_handler(request: web.Request) -> web.Response:
    transaction_id_text = request.match_info["id"]
    original_types = request.query.getall("type", [])
    if (not re.fullmatch(r"[0-9]{1,19}", transaction_id_text)
            or not 0 < int(transaction_id_text) <= 9223372036854775807
            or len(original_types) != 1 or original_types[0] not in ("income", "expense")):
        return web.json_response({"error": "Вкажіть коректний ID і поточний тип транзакції."}, status=400)
    if request.content_type != "application/json":
        return web.json_response({"error": "Надішліть дані у форматі JSON."}, status=415)
    try:
        data = json.loads(await request.text(), parse_float=Decimal)
        operation_type, amount, category, transaction_date = validate_transaction(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return web.json_response({"error": "Некоректний JSON."}, status=400)
    except ValueError as error:
        return web.json_response({"error": str(error)}, status=400)

    try:
        updated_id = await asyncio.to_thread(
            update_transaction, int(transaction_id_text), original_types[0],
            operation_type, amount, category, transaction_date,
        )
    except Exception as error:
        logging.error("Не вдалося оновити транзакцію: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося оновити транзакцію."}, status=503)
    if updated_id is None:
        return web.json_response({"error": "Транзакцію не знайдено."}, status=404)
    return web.json_response({
        "id": updated_id, "type": operation_type, "amount": format(amount, ".2f"),
        "category": category, "date": transaction_date.isoformat(),
    })


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/transactions", transactions_handler, allow_head=False)
    app.router.add_post("/api/transactions", create_transaction_handler)
    app.router.add_delete("/api/transactions/{id}", delete_transaction_handler)
    app.router.add_put("/api/transactions/{id}", update_transaction_handler)
    app.router.add_get("/api/summary", summary_handler, allow_head=False)
    app.router.add_post('/api/ai/analize-transactions', analyze_transactions_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=os.getenv("API_HOST", "127.0.0.1"), port=8080)
