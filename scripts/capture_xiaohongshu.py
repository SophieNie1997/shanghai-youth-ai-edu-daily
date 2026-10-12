#!/usr/bin/env python3
"""Read search and note payloads before sanitizing anything written to cache."""
import argparse
from datetime import datetime
from pathlib import Path
import json
import os
import re
import subprocess
import time
from urllib.parse import urlsplit, parse_qs
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OPENCLI = Path(os.environ.get('OPENCLI_BIN') or '/Users/sophienie/Library/Application Support/CodexWeixinBridge/node_modules/.bin/opencli')
DEFAULT_QUERIES = ['上海 AI 财商 英语', '上海 幼儿英语 机构', '上海 AI 国庆营']
SENSITIVE_KEY = re.compile(r'token|cookie|authorization|password|secret|session|signature|finalurl|share_id', re.I)
URL_PATTERN = re.compile(r'https?://[^\s"<>\]\)]+')
NOTE_PATH = re.compile(r'^/(?:explore|search_result|discovery/item)/([a-f0-9]{24})(?:/|$)', re.I)


def note_id(url):
    parsed = urlsplit(str(url))
    host = (parsed.hostname or '').lower()
    if host != 'xiaohongshu.com' and not host.endswith('.xiaohongshu.com'):
        return None
    match = NOTE_PATH.match(parsed.path)
    return match.group(1) if match else None


def canonical_url(url):
    id = note_id(url)
    return f'https://www.xiaohongshu.com/explore/{id}' if id else str(url)


def sanitize(value):
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items() if not SENSITIVE_KEY.search(k)}
    if isinstance(value, list):
        return [sanitize(v) for v in value if not (isinstance(v, dict) and SENSITIVE_KEY.search(str(v.get('field', ''))))]
    if isinstance(value, str):
        def clean_url(match):
            url = match.group()
            if note_id(url):
                return canonical_url(url)
            # Public note URLs are canonicalized above; scrub credentials in diagnostics.
            return re.sub(r'([?&])(?:xsec_token|share_id|share_token|access_token|auth_token|session_token|signature)=[^&\s]+', r'\1', url, flags=re.I)
        value = URL_PATTERN.sub(clean_url, value)
        return re.sub(r'\b(?:xsec_token|share_token|access_token|cookie|authorization|password|secret)\s*[:=]\s*[^\s,;]+', '[redacted]', value, flags=re.I)
    return value


def items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ['results', 'items', 'notes']:
            if isinstance(payload.get(key), list):
                return payload[key]
        if 'data' in payload:
            return items(payload['data'])
    return []


def has_body(payload):
    if isinstance(payload, list):
        return any(str(row.get('field', '')).lower() in ['content', 'description', 'body', '正文'] and isinstance(row.get('value'), str) and row['value'].strip() for row in payload if isinstance(row, dict))
    if isinstance(payload, dict):
        if payload.get('ok') is False:
            return False
        return any(isinstance(payload.get(k), str) and payload[k].strip() for k in ['content', 'description', 'body']) or any(has_body(payload[k]) for k in ['data', 'metadata', 'note'] if k in payload)
    return False


def run_cli(args):
    # A process error may echo argv, so return it only through the sanitizer below.
    try:
        result = subprocess.run([str(OPENCLI), *args], capture_output=True, text=True, timeout=70)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, '', 'OpenCLI command timed out after 70 seconds'
    except OSError as error:
        return 1, '', str(error)


def atomic_write(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(value, encoding='utf-8')
    tmp.replace(path)


def capture_queries(output_dir, queries, runner=run_cli, progress=None):
    if not 1 <= len(queries) <= 3:
        raise ValueError('Use one to three Xiaohongshu queries')
    output_dir.mkdir(parents=True, exist_ok=True)
    records, seen = [], set()

    def capture(id, channel, query, args):
        started = time.monotonic()
        code, stdout, stderr = runner(args)
        # Only connection errors receive the explicitly bounded retries.
        for delay in [2, 4, 8]:
            if code == 0 or not re.search(r'browser bridge(?: extension)? (?:is )?not connected|no browser bridge profiles? connected|no connected browser profiles?|failed to connect to browser bridge', stderr, re.I):
                break
            time.sleep(delay)
            code, stdout, stderr = runner(args)
        try:
            payload = json.loads(stdout)
        except ValueError:
            payload = {'unparsed': stdout}
        if channel == 'xiaohongshu':
            rows = items(payload)[:8]
            # Preserve signed URLs in this in-memory list for note calls.
            payload = rows
            ok = code == 0 and bool(rows)
            count = len(rows) if ok else 0
        else:
            ok = code == 0 and has_body(payload)
            count = 1 if ok else 0
        out = output_dir / f'{id}.json'
        err = output_dir / f'{id}.stderr.txt'
        atomic_write(out, json.dumps(sanitize(payload), ensure_ascii=False, indent=2) + '\n')
        atomic_write(err, str(sanitize(stderr)) + '\n')
        record = dict(id=id, channel=channel, query=sanitize(query), ok=ok, exitCode=code, resultCount=count, stdoutFile=str(out), stderrFile=str(err), captureMethod='opencli_chrome', durationMs=round((time.monotonic()-started)*1000))
        records.append(record)
        if progress:
            progress({k: record[k] for k in ['id', 'channel', 'ok', 'exitCode', 'resultCount']})
        return payload if ok else []

    for index, query in enumerate(queries, 1):
        raw = capture(f'xhs-{index:02}', 'xiaohongshu', query, ['xiaohongshu', 'search', query, '--limit', '8', '-f', 'json', '--window', 'background', '--site-session', 'persistent', '--keep-tab', 'false'])
        for row in raw[:2]:
            signed_url = row.get('url', '')
            id = note_id(signed_url)
            if not id or id in seen:
                continue
            if not parse_qs(urlsplit(signed_url).query).get('xsec_token'):
                # Do not invoke note with a URL known to be unusable.
                if progress:
                    progress({'id': id, 'ok': False, 'error': 'Search result lacks required signature'})
                continue
            seen.add(id)
            capture(f'xhs-note-{len(seen):02}', 'xiaohongshu-note', canonical_url(signed_url), ['xiaohongshu', 'note', signed_url, '--window', 'background', '--site-session', 'persistent', '--keep-tab', 'false', '-f', 'json'])
    return records


def write_cache(root, date, records, queries):
    cache = root / 'opencli-cache'
    file = cache / 'latest.json'
    previous = json.loads(file.read_text()) if file.exists() else {}
    old = previous.get('records', []) if previous.get('date') == date else []
    # Keep all previously collected non-Xiaohongshu channels.
    merged = [r for r in old if r.get('channel') not in ['xiaohongshu', 'xiaohongshu-note']] + records
    manifest = {k: v for k, v in previous.items() if k not in ['records', 'detailCaptureLimitation'] and previous.get('date') == date}
    manifest.update(date=date, generatedAt=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), credentialHandling='Signed search URLs passed to note in memory; all saved payloads, errors and manifest fields sanitized.', records=merged, xiaohongshuQueries=queries)
    manifest['detailRecovery'] = {'recoveredAt': manifest['generatedAt'], 'successfulBodies': sum(r['ok'] for r in records if r['channel'] == 'xiaohongshu-note'), 'method': 'fresh signatures from targeted searches; no preflight probes'}
    text = json.dumps(sanitize(manifest), ensure_ascii=False, indent=2) + '\n'
    atomic_write(cache / date / 'manifest.json', text)
    atomic_write(file, text)
    lines = [f'# OpenCLI 预抓取缓存 - 上海青少年AI教育情报 - {date}', '', f'- 生成时间：{manifest["generatedAt"]}', '- 小红书修复：搜索原链接只在进程内用于详情读取；文件与展示链接均脱敏。']
    for channel in ['xiaohongshu', 'xiaohongshu-note', 'weixin', 'dianping', 'twitter']:
        rr = [r for r in merged if r['channel'] == channel]
        lines.append(f'- {channel}：{len(rr)} 次读取，{sum(bool(r["ok"]) for r in rr)} 次成功非空，共 {sum(r.get("resultCount") or 0 for r in rr)} 条记录。')
    lines += ['- 小红书每查询最多保留 8 条，仅前两条展开；正文成功须有非空内容。', '- 正文补抓获用户明确要求，未执行 doctor、daemon 重启或连接探测；其他渠道沿用同日缓存。', '- 搜索摘要不等于正文，招生计划不等于实际交付。']
    md = '\n'.join(lines) + '\n'
    atomic_write(cache / 'latest.md', md)
    atomic_write(cache / date / 'manifest.md', md)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat())
    parser.add_argument('--query', action='append')
    parser.add_argument('--repair-from-cache', action='store_true', help='Refresh signatures for the same-day cached search queries; preserve other channels')
    parser.add_argument('--manifest-only', action='store_true', help='For launchd prefetch: write xhs-manifest.json without replacing latest channel cache')
    args = parser.parse_args()
    queries = args.query or DEFAULT_QUERIES
    if args.repair_from_cache:
        prior = json.loads((ROOT / 'opencli-cache/latest.json').read_text())
        if prior.get('date') != args.date:
            parser.error('Repair requires cache date to match the requested date')
        queries = list(dict.fromkeys(r['query'] for r in prior['records'] if r['channel'] == 'xiaohongshu'))[:3]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.date):
        parser.error('Date must use YYYY-MM-DD')
    output_dir = ROOT / 'opencli-cache' / args.date
    records = capture_queries(output_dir, queries, progress=lambda r: print(json.dumps(r, ensure_ascii=False), flush=True))
    if args.manifest_only:
        atomic_write(output_dir / 'xhs-manifest.json', json.dumps({'date': args.date, 'records': records}, ensure_ascii=False, indent=2) + '\n')
    else:
        write_cache(ROOT, args.date, records, queries)


if __name__ == '__main__':
    main()
