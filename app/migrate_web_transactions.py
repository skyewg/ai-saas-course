"""Оновлює схему для вебтранзакцій, зберігаючи наявні записи."""

from sqlalchemy import text
from database import get_engine


def migrate():
    with get_engine().begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(2026112301)"))
        connection.execute(text("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_local_web ON users (username) WHERE telegram_id IS NULL"))
        for table in ("transactions", "incomes"):
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS transaction_date DATE"))
            connection.execute(text(f"UPDATE {table} SET transaction_date = (created_at AT TIME ZONE 'Europe/Kyiv')::date WHERE transaction_date IS NULL"))
            connection.execute(text(f"ALTER TABLE {table} ALTER COLUMN transaction_date SET DEFAULT ((CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Kyiv')::date)"))
            connection.execute(text(f"ALTER TABLE {table} ALTER COLUMN transaction_date SET NOT NULL"))
            constraint = f"ck_{table}_amount_positive"
            connection.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}"))
            connection.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {constraint} CHECK (amount >= 0)"))
        connection.execute(text("ALTER TABLE incomes ADD COLUMN IF NOT EXISTS category_id BIGINT"))
        connection.execute(text("""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_incomes_category_owner' AND conrelid = 'incomes'::regclass) THEN
                ALTER TABLE incomes ADD CONSTRAINT fk_incomes_category_owner
                FOREIGN KEY (category_id, user_id) REFERENCES categories (id, user_id);
              END IF;
            END $$
        """))


if __name__ == "__main__":
    try:
        migrate()
    except Exception:
        print("Не вдалося оновити базу. Перевірте підключення й права доступу.")
        raise SystemExit(1)
    print("Базу оновлено.")
