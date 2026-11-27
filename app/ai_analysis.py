import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict


class Analysis(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    summary: str
    top_expence_categories: list[str]
    risk: list[str]
    advice: list[str]


class AnalysisUnavailable(Exception):
    pass


PROMPT_PATH = Path(__file__).with_name('ai_prompt.txt')


def serialize_transactions(transactions: list[dict]) -> str:
    # IDs are not needed for analysis and should not be sent to the model.
    fields = ('type', 'amount', 'category', 'date', 'created_at')
    data = [{key: item.get(key) for key in fields} for item in transactions]
    return json.dumps(data, ensure_ascii=False)


def build_analysis_prompt(transactions: list[dict]) -> str:
    return PROMPT_PATH.read_text(encoding='utf-8').rstrip() + '\n' + serialize_transactions(transactions)


def analyze_transactions(transactions: list[dict]) -> dict:
    load_dotenv(Path(__file__).with_name('.env'))
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise AnalysisUnavailable('Ключ Gemini API не налаштовано.')

    prompt = build_analysis_prompt(transactions)
    preferred = 'gemini-3.1-flash-lite'
    config = types.GenerateContentConfig(response_mime_type='application/json', response_json_schema=Analysis.model_json_schema())

    try:
        with genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000)) as client:
            def attempt(model: str) -> dict | None:
                try:
                    response = client.models.generate_content(model=model, contents=prompt, config=config)
                    return Analysis.model_validate_json(response.text or '').model_dump()
                except Exception as error:
                    # Error messages can contain request data or credentials.
                    logging.warning('Gemini model %s failed: %s', model, type(error).__name__)
                    return None

            result = attempt(preferred)
            if result is not None:
                return result

            for model in client.models.list():
                name = model.name or ''
                short_name = name.removeprefix('models/')
                if (short_name == preferred or not short_name.startswith('gemini-')
                        or any(part in short_name for part in ('image', 'audio', 'tts', 'live', 'robotics'))
                        or 'generateContent' not in (model.supported_actions or [])):
                    continue
                result = attempt(name)
                if result is not None:
                    return result
    except Exception as error:
        logging.error('Gemini API unavailable: %s', type(error).__name__)

    raise AnalysisUnavailable('Не вдалося отримати аналіз від доступних моделей Gemini.')
