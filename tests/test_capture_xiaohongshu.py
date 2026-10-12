import json
from pathlib import Path
import tempfile
import unittest

from scripts.capture_xiaohongshu import capture_queries, note_id, sanitize, write_cache


class CaptureTests(unittest.TestCase):
    def test_signed_url_reaches_note_but_never_disk(self):
        calls = []
        first = 'a' * 24
        second = 'b' * 24
        secret = 'TEST_SIGNATURE_DO_NOT_STORE'
        signed = f'https://www.xiaohongshu.com/search_result/{first}?xsec_token={secret}&xsec_source=pc_search'
        def runner(args):
            calls.append(args)
            if args[1] == 'search':
                rows = [{'url': signed, 'title': 'First'}, {'url': f'https://www.xiaohongshu.com/discovery/item/{second}?xsec_token={secret}', 'title': 'Second'}]
                rows.extend({'url': f'https://www.xiaohongshu.com/explore/{n:024x}?xsec_token={secret}'} for n in range(10))
                return 0, json.dumps(rows), ''
            self.assertIn(secret, args[2])
            return 0, json.dumps([{'field': 'content', 'value': 'Real note body'}, {'field': 'url', 'value': args[2]}, {'field': 'xsec_token', 'value': secret}]), f'Observed URL: {args[2]}'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'opencli-cache/2026-10-12'
            records = capture_queries(output, ['query'], runner=runner)
            manifest = write_cache(root, '2026-10-12', records, ['query'])
            self.assertEqual([r['resultCount'] for r in records], [8, 1, 1])
            self.assertEqual(len(calls), 3)
            self.assertEqual(manifest['detailRecovery']['successfulBodies'], 2)
            for file in root.rglob('*'):
                if file.is_file():
                    text = file.read_text()
                    self.assertNotIn(secret, text)
                    self.assertNotIn('xsec_token=', text)
            self.assertEqual(json.loads((output / 'xhs-01.json').read_text())[0]['url'], f'https://www.xiaohongshu.com/explore/{first}')

    def test_no_signature_or_no_body_is_not_success(self):
        id = 'c' * 24
        def runner(args):
            if args[1] == 'search':
                return 0, json.dumps([{'url': f'https://www.xiaohongshu.com/explore/{id}'}, {'url': f'https://www.xiaohongshu.com/explore/{"d"*24}?xsec_token=test'}]), ''
            return 0, json.dumps([{'field': 'title', 'value': 'Title only'}, {'field': 'content', 'value': None}]), ''
        with tempfile.TemporaryDirectory() as tmp:
            rows = capture_queries(Path(tmp), ['query'], runner=runner)
            self.assertEqual(len(rows), 2)
            self.assertFalse(rows[1]['ok'])
            self.assertEqual(rows[1]['resultCount'], 0)

    def test_recovery_preserves_other_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / 'opencli-cache'
            (cache / '2026-10-12').mkdir(parents=True)
            (cache / 'latest.json').write_text(json.dumps({'date': '2026-10-12', 'detailCaptureLimitation': 'old failure', 'records': [{'id': 'weixin-01', 'channel': 'weixin', 'ok': True, 'resultCount': 10}, {'id': 'xhs-old', 'channel': 'xiaohongshu', 'ok': False}]}))
            result = write_cache(root, '2026-10-12', [], ['query'])
            self.assertEqual(result['records'][0]['id'], 'weixin-01')
            self.assertNotIn('detailCaptureLimitation', result)
            self.assertEqual(len(result['records']), 1)

    def test_domain_and_nested_error_sanitization(self):
        id = 'e' * 24
        self.assertIsNone(note_id(f'https://xiaohongshu.com.evil.example/explore/{id}?xsec_token=test'))
        self.assertEqual(note_id(f'https://www.xiaohongshu.com/search_result/{id}'), id)
        value = sanitize({'finalUrl': 'secret', 'metadata': {'access_token': 'secret', 'url': f'https://www.xiaohongshu.com/search_result/{id}?xsec_token=secret'}, 'error': 'xsec_token=secret'})
        self.assertNotIn('secret', json.dumps(value))


if __name__ == '__main__':
    unittest.main()
