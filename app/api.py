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

from database import get_summary, get_transactions, save_web_transaction, update_transaction, delete_transaction


def validate_transaction(data: object) -> tuple[str, Decimal, str, date]:
    if not isinstance(data, dict):
        raise ValueError("Надішліть JSON-об’єкт.")
    kinds = {"expense": "expense", "income": "income", "витрата": "expense", "витрати": "expense", "дохід": "income"}
    kind = data.get("type")
    if not isinstance(kind, str) or kind.strip().casefold() not in kinds:
        raise ValueError("Тип операції має бути income або expense.")
    kind = kinds[kind.strip().casefold()]
    raw_amount = data.get("amount")
    if isinstance(raw_amount, bool) or not isinstance(raw_amount, (str, int, Decimal)):
        raise ValueError("Вкажіть невід’ємну суму з не більше ніж двома знаками після коми.")
    amount_text = str(raw_amount).strip().replace(",", ".")
    if not re.fullmatch(r"[0-9]{1,10}(?:\.[0-9]{1,2})?", amount_text):
        raise ValueError("Вкажіть невід’ємну суму з не більше ніж двома знаками після коми.")
    category = data.get("category")
    if not isinstance(category, str):
        raise ValueError("Категорія має містити лише літери.")
    category = category.strip().casefold()
    if (not category or len(category) > 100 or not any(c.isalpha() for c in category)
            or any(not (unicodedata.category(c)[0] in ("L", "M") or c in " '-’ʼ") for c in category)):
        raise ValueError("Категорія має містити лише літери, пробіли, дефіс або апостроф.")
    raw_date = data.get("date")
    if raw_date in (None, ""):
        operation_date = datetime.now(ZoneInfo("Europe/Kyiv")).date()
    else:
        if not isinstance(raw_date, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw_date):
            raise ValueError("Вкажіть дату у форматі РРРР-ММ-ДД.")
        try:
            operation_date = date.fromisoformat(raw_date)
        except ValueError:
            raise ValueError("Вкажіть дійсну дату.") from None
    return kind, Decimal(amount_text), category, operation_date


async def read_transaction(request: web.Request):
    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType(text="Очікується JSON.")
    try:
        return validate_transaction(json.loads(await request.text(), parse_float=Decimal))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise web.HTTPBadRequest(text="Некоректний JSON.") from None
    except ValueError as error:
        raise web.HTTPBadRequest(text=str(error)) from None


def target_from_request(request: web.Request) -> tuple[int, str]:
    raw_id = request.match_info["id"]
    kinds = request.query.getall("type", [])
    if (not re.fullmatch(r"[0-9]{1,19}", raw_id) or not 0 < int(raw_id) <= 9223372036854775807
            or len(kinds) != 1 or kinds[0] not in ("income", "expense")):
        raise web.HTTPBadRequest(text="Вкажіть коректний ID і тип транзакції.")
    return int(raw_id), kinds[0]


async def create_transaction_handler(request: web.Request) -> web.Response:
    try:
        kind, amount, category, operation_date = await read_transaction(request)
        entry_id = await asyncio.to_thread(save_web_transaction, kind, amount, category, operation_date)
    except web.HTTPException as error:
        return web.json_response({"error": error.text}, status=error.status)
    except Exception as error:
        logging.error("Не вдалося зберегти транзакцію: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося зберегти транзакцію."}, status=503)
    return web.json_response({"id": entry_id, "type": kind, "amount": format(amount, ".2f"),
                              "category": category, "date": operation_date.isoformat()}, status=201)


async def update_transaction_handler(request: web.Request) -> web.Response:
    try:
        entry_id, previous_kind = target_from_request(request)
        kind, amount, category, operation_date = await read_transaction(request)
        new_id = await asyncio.to_thread(update_transaction, entry_id, previous_kind, kind, amount, category, operation_date)
    except web.HTTPException as error:
        return web.json_response({"error": error.text}, status=error.status)
    except Exception as error:
        logging.error("Не вдалося оновити транзакцію: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося оновити транзакцію."}, status=503)
    if new_id is None:
        return web.json_response({"error": "Транзакцію не знайдено."}, status=404)
    return web.json_response({"id": new_id, "type": kind, "amount": format(amount, ".2f"),
                              "category": category, "date": operation_date.isoformat()})


async def delete_transaction_handler(request: web.Request) -> web.Response:
    try:
        entry_id, kind = target_from_request(request)
        deleted = await asyncio.to_thread(delete_transaction, entry_id, kind)
    except web.HTTPException as error:
        return web.json_response({"error": error.text}, status=error.status)
    except Exception as error:
        logging.error("Не вдалося видалити транзакцію: %s", type(error).__name__)
        return web.json_response({"error": "Не вдалося видалити транзакцію."}, status=503)
    if not deleted:
        return web.json_response({"error": "Транзакцію не знайдено."}, status=404)
    return web.Response(status=204)


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


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/transaction", transactions_handler, allow_head=False)
    app.router.add_post("/api/transaction", create_transaction_handler)
    app.router.add_put("/api/transactions/{id}", update_transaction_handler)
    app.router.add_delete("/api/transactions/{id}", delete_transaction_handler)
    app.router.add_get("/api/summary", summary_handler, allow_head=False)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=os.getenv("API_HOST", "127.0.0.1"), port=8080)
