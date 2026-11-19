import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import insert


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("telegram_id", BigInteger, nullable=False, unique=True),
    Column("username", String(100)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

categories = Table(
    "categories",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
    UniqueConstraint("id", "user_id", name="uq_categories_id_user"),
)

transactions = Table(
    "transactions",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("category_id", BigInteger, nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["category_id", "user_id"],
        ["categories.id", "categories.user_id"],
        name="fk_transactions_category_owner",
    ),
    CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
)


@lru_cache(maxsize=1)
def get_engine():
    load_dotenv(Path(__file__).with_name(".env"))
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not configured")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})


def create_tables() -> None:
    metadata.create_all(get_engine())


def _save_expense(connection, telegram_id: int, username: str | None, amount: Decimal, category: str) -> None:
    user_insert = insert(users).values(telegram_id=telegram_id, username=username)
    user_id = connection.execute(
        user_insert.on_conflict_do_update(
            index_elements=[users.c.telegram_id],
            set_={"username": user_insert.excluded.username},
        ).returning(users.c.id)
    ).scalar_one()

    category_insert = insert(categories).values(user_id=user_id, name=category)
    category_id = connection.execute(
        category_insert.on_conflict_do_update(
            constraint="uq_categories_user_name",
            set_={"name": category_insert.excluded.name},
        ).returning(categories.c.id)
    ).scalar_one()

    connection.execute(
        transactions.insert().values(user_id=user_id, category_id=category_id, amount=amount)
    )


def save_expense(telegram_id: int, username: str | None, amount: Decimal, category: str) -> None:
    with get_engine().begin() as connection:
        _save_expense(connection, telegram_id, username, amount, category)


if __name__ == "__main__":
    try:
        create_tables()
    except Exception:
        print("Не вдалося створити таблиці. Перевірте DATABASE_URL і доступ до бази.")
        raise SystemExit(1)
    print("Таблиці готові.")
