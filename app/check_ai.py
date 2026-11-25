import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


def main() -> int:
    load_dotenv(Path(__file__).with_name('.env'))
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        print('NOT OK: GEMINI_API_KEY не знайдено у файлі app/.env або змінних середовища.')
        return 1

    try:
        with genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000)) as client:
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents='Привіт! Коротко підтвердь, що ти працюєш.',
            )
        answer = response.text
        if not answer or not answer.strip():
            print('NOT OK: модель повернула порожню відповідь.')
            return 1
    except errors.APIError as error:
        # Do not print the server response: it might contain sensitive details.
        print(f'NOT OK: Gemini API повернув помилку HTTP {error.code}.')
        return 1
    except Exception:
        print('NOT OK: не вдалося зв’язатися з Gemini API. Перевірте підключення та налаштування.')
        return 1

    print('OK: Gemini працює.')
    print(f'Відповідь: {answer.strip()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
