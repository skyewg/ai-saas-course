import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import ai_analysis
import api


class AnalysisTests(unittest.TestCase):
    def test_falls_back_after_invalid_answer_and_excludes_ids(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.side_effect = [
            SimpleNamespace(text='not json'),
            SimpleNamespace(text=json.dumps({
                'summary': 'Висновок', 'top_expence_categories': ['кава'],
                'risk': [], 'advice': ['Плануйте витрати'],
            })),
        ]
        client.models.list.return_value = [
            SimpleNamespace(name='models/gemini-3.1-flash-lite', supported_actions=['generateContent']),
            SimpleNamespace(name='models/gemini-example-image', supported_actions=['generateContent']),
            SimpleNamespace(name='models/gemini-example', supported_actions=['generateContent']),
        ]
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}), patch.object(ai_analysis.genai, 'Client', return_value=client):
            result = ai_analysis.analyze_transactions([
                {'type': 'expense', 'amount': '20.00', 'category': 'кава', 'user_id': 12345}
            ])
        self.assertEqual(result['top_expence_categories'], ['кава'])
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(client.models.generate_content.call_args.kwargs['model'], 'models/gemini-example')
        prompt = client.models.generate_content.call_args.kwargs['contents']
        self.assertTrue(prompt.startswith(ai_analysis.PROMPT_PATH.read_text(encoding='utf-8').rstrip() + '\n'))
        self.assertNotIn('12345', prompt)

    def test_endpoint_returns_analysis_and_reports_database_failure(self):
        expected = {'summary': 'Добре', 'top_expence_categories': [], 'risk': [], 'advice': []}
        with patch.object(api, 'get_transactions', return_value=[]), patch.object(api, 'analyze_transactions', return_value=expected):
            response = asyncio.run(api.analyze_transactions_handler(None))
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), expected)
        with patch.object(api, 'get_transactions', side_effect=RuntimeError('private')):
            response = asyncio.run(api.analyze_transactions_handler(None))
        self.assertEqual(response.status, 503)
        self.assertNotIn('private', response.text)


if __name__ == '__main__':
    unittest.main()
