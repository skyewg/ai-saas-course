# Finansovik

Telegram-бот із командами `/start`, `/help` та `/expense`.

## Додавання витрати

Напишіть боту, наприклад: `/expense 120 кава` або `/expense 85,50 продукти`.
Сума має бути більшою за нуль, із не більше ніж двома знаками після коми.
Категорії створюються окремо для кожного користувача; однакова назва використовується повторно.

Перед першим використанням створіть таблиці в базі командою з теки `app`:

```powershell
.\.venv\Scripts\python.exe database.py
```

Команда створює відсутні таблиці `users`, `categories` та `transactions` і не змінює вже наявні.

## Перевірка підключення до бази даних

Додайте `DATABASE_URL` до файлу `app/.env`. У PowerShell із теки `app` виконайте:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_db.py
```

`OK` означає, що підключення та запит `SELECT 1` виконалися успішно. `NOT OK` означає, що перевірка не вдалася.
