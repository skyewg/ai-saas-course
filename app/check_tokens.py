import tiktoken

from ai_analysis import build_analysis_prompt, serialize_transactions
from database import get_transactions


def main() -> int:
    try:
        transactions = get_transactions()
        encoding = tiktoken.get_encoding('o200k_base')
        transaction_tokens = len(encoding.encode_ordinary(serialize_transactions(transactions)))
        request_tokens = len(encoding.encode_ordinary(build_analysis_prompt(transactions)))
    except Exception as error:
        # Database errors can contain credentials; do not print their details.
        print(f'Не вдалося підрахувати токени ({type(error).__name__}).')
        return 1

    print(f'Кількість транзакцій: {len(transactions)}')
    print(f'Транзакції: приблизно {transaction_tokens} токенів')
    print(f'Промпт і транзакції разом: приблизно {request_tokens} токенів')
    print('Оцінка tiktoken (o200k_base): Gemini використовує інший токенізатор.')
    print('Токени відповіді та додаткових параметрів запиту не враховано.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
