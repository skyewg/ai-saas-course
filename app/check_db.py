import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def main() -> int:
    load_dotenv(Path(__file__).with_name(".env"))
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("NOT OK")
        return 1

    # Neon provides a PostgreSQL URL; select the installed psycopg driver.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = None
    try:
        engine = create_engine(database_url, connect_args={"connect_timeout": 10})
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
        if result != 1:
            print("NOT OK")
            return 1
    except Exception:
        # Connection errors may contain credentials, so don't print them.
        print("NOT OK")
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
