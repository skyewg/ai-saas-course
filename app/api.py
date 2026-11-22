import asyncio
import logging
import os

from aiohttp import web

from database import get_summary, get_transactions


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
    app.router.add_get("/api/summary", summary_handler, allow_head=False)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=os.getenv("API_HOST", "127.0.0.1"), port=8080)
