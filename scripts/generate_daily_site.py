from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SECTION_TITLES = [
    "今日结论",
    "英语机构转型观察",
    "机构与课程表",
    "AI+财商+英语表达专项观察",
    "高频卖点/内容趋势",
    "新增线索",
    "对樱桃图书馆/登顶升学的启发",
    "今日可测试动作",
    "X/Twitter英文趋势观察",
    "渠道覆盖与失败说明",
]


@dataclass
class Report:
    date: str
    title: str
    summary_bullets: list[str]
    archive_headline: str
    archive_summary: str
    trend_bullets: list[str]
    detail_path: str
    sections: dict[str, str]
    source_path: str


def parse_report(path: Path) -> Report:
    text = path.read_text(encoding="utf-8").strip()
    lines = text.splitlines()
    title = normalize_heading(lines[0].strip())
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    if not date_match:
        raise ValueError(f"Could not find date in title: {title}")
    date = date_match.group(1)
    sections = split_sections(lines[1:])
    summary_bullets = extract_numbered_items(sections.get("今日结论", ""))
    if not summary_bullets:
        raise ValueError(f"Report has no 今日结论 bullets: {path}")
    trend_bullets = summary_bullets[:3]
    archive_headline = headline_from_bullet(summary_bullets[0])
    archive_summary = summary_bullets[1] if len(summary_bullets) > 1 else summary_bullets[0]
    return Report(
        date=date,
        title=title,
        summary_bullets=summary_bullets,
        archive_headline=archive_headline,
        archive_summary=archive_summary,
        trend_bullets=trend_bullets,
        detail_path=f"daily/{date}.html",
        sections=sections,
        source_path=str(path),
    )


def split_sections(lines: list[str]) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in lines:
        line = raw.strip()
        normalized = normalize_heading(line)
        if normalized in SECTION_TITLES:
            current = normalized
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(raw.rstrip())
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def normalize_heading(text: str) -> str:
    return re.sub(r"^#+\s*", "", text).strip()


def extract_numbered_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^\d+\.\s*(.+)$", stripped)
        if match:
            items.append(match.group(1).strip())
    return items


def collect_reports(root: Path) -> list[Report]:
    paths = [
        *sorted((root / "reports").glob("shanghai-youth-ai-edu-daily-*.md")),
        *sorted(root.glob("shanghai-youth-ai-edu-daily-*.md")),
        *sorted(root.glob("shanghai-youth-ai-edu-*.md")),
    ]
    reports_by_date: dict[str, Report] = {}
    for path in paths:
        report = parse_report(path)
        reports_by_date.setdefault(report.date, report)
    return sorted(reports_by_date.values(), key=lambda report: report.date, reverse=True)


def build_site(root: Path) -> None:
    reports = collect_reports(root)
    if not reports:
        raise ValueError("No reports found in reports/")
    assets_dir = root / "assets"
    daily_dir = root / "daily"
    data_dir = root / "site-data"
    assets_dir.mkdir(parents=True, exist_ok=True)
    daily_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    write_assets(assets_dir)
    write_json_index(data_dir / "reports.json", reports)
    write_homepage(root / "index.html", reports)
    write_detail_pages(root, reports)


def write_assets(assets_dir: Path) -> None:
    css = """/* 暖灰苹果风日报站样式 */
:root {
  --bg: linear-gradient(180deg, #ebe6de 0%, #f3f0eb 38%, #e0d8ce 100%);
  --paper: rgba(255, 255, 255, 0.68);
  --paper-strong: rgba(255, 255, 255, 0.84);
  --ink: #1f1f20;
  --muted: #686259;
  --line: rgba(33, 28, 22, 0.08);
  --accent: #a95a2a;
  --link: #0a66d1;
  --shadow: 0 20px 60px rgba(76, 56, 35, 0.08);
  --radius-xl: 34px;
  --radius-lg: 26px;
  --radius-md: 18px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Helvetica Neue", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at 10% 0%, rgba(244, 209, 170, 0.42), transparent 22%),
    radial-gradient(circle at 90% 5%, rgba(255, 255, 255, 0.75), transparent 18%),
    radial-gradient(circle at 65% 100%, rgba(196, 183, 170, 0.24), transparent 28%),
    var(--bg);
}
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.page { width: min(1120px, calc(100vw - 32px)); margin: 0 auto; padding: 40px 0 72px; }
.hero { padding: 28px 0 24px; text-align: center; }
.eyebrow { color: var(--accent); font-size: 13px; font-weight: 700; margin-bottom: 10px; }
.hero h1 { font-size: clamp(42px, 6vw, 64px); line-height: 1.02; letter-spacing: -0.045em; margin: 0; }
.hero p { color: var(--muted); font-size: clamp(18px, 2.3vw, 22px); line-height: 1.45; max-width: 760px; margin: 18px auto 0; }
.feature, .trend-card, .summary-card, .detail-card, .archive-wrap, .toc {
  background: var(--paper);
  border: 1px solid rgba(255,255,255,0.45);
  box-shadow: var(--shadow);
  backdrop-filter: blur(14px);
}
.feature { border-radius: var(--radius-xl); padding: 28px; display: grid; grid-template-columns: 1.3fr .85fr; gap: 20px; }
.feature-copy h2 { font-size: 34px; line-height: 1.12; letter-spacing: -0.03em; margin: 8px 0 12px; }
.feature-copy p { color: var(--muted); line-height: 1.68; font-size: 17px; }
.bullet-list { margin: 20px 0 0; padding-left: 22px; line-height: 1.8; }
.summary-card { border-radius: var(--radius-lg); padding: 22px; display: flex; flex-direction: column; justify-content: space-between; }
.summary-card .date { color: var(--muted); font-size: 14px; }
.summary-card .claim { font-size: 28px; line-height: 1.18; letter-spacing: -0.03em; margin-top: 12px; }
.summary-card .cta { margin-top: 18px; color: var(--accent); font-weight: 700; }
.section { margin-top: 42px; }
.section-head { text-align: center; margin-bottom: 18px; }
.section-head h2 { font-size: 38px; line-height: 1.08; letter-spacing: -0.035em; margin: 0; }
.section-head p { color: var(--muted); font-size: 17px; margin: 8px 0 0; }
.trend-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.trend-card { border-radius: 28px; padding: 22px; }
.trend-card .tag { color: var(--accent); font-size: 12px; font-weight: 700; margin-bottom: 10px; }
.trend-card h3 { font-size: 25px; line-height: 1.18; letter-spacing: -0.025em; margin: 0 0 10px; }
.trend-card p { color: var(--muted); font-size: 15px; line-height: 1.68; margin: 0; }
.archive-wrap { border-radius: var(--radius-xl); overflow: hidden; }
.archive-item { display: grid; grid-template-columns: 120px 1fr 110px; gap: 18px; padding: 20px 24px; border-top: 1px solid var(--line); align-items: center; }
.archive-item:first-child { border-top: 0; }
.archive-item strong { font-size: 15px; }
.archive-item .headline { font-size: 18px; margin-bottom: 4px; }
.archive-item p { margin: 0; color: var(--muted); line-height: 1.6; font-size: 14px; }
.archive-item .jump { justify-self: end; color: var(--accent); font-weight: 700; }
.detail-hero { text-align: left; padding-top: 12px; }
.detail-layout { display: grid; grid-template-columns: minmax(220px, 280px) minmax(0, 1fr); gap: 24px; align-items: start; }
.toc { border-radius: 24px; padding: 18px; position: sticky; top: 18px; min-width: 0; }
.toc h3 { margin: 0 0 12px; font-size: 18px; }
.toc ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.toc a { color: var(--muted); font-size: 14px; }
.detail-card { border-radius: var(--radius-xl); padding: 28px; min-width: 0; max-width: 100%; overflow: hidden; }
.detail-card section + section { margin-top: 28px; }
.detail-card h2 { font-size: 28px; line-height: 1.15; letter-spacing: -0.025em; margin: 0 0 14px; }
.detail-card p { line-height: 1.8; margin: 10px 0; overflow-wrap: anywhere; }
.detail-card ol, .detail-card ul { padding-left: 22px; line-height: 1.8; }
.detail-card li { margin-bottom: 8px; overflow-wrap: anywhere; }
.entry-card { border: 1px solid var(--line); border-radius: 20px; padding: 16px 18px; background: var(--paper-strong); margin: 14px 0; }
.entry-card h4 { margin: 0 0 10px; font-size: 18px; }
.table-wrap { max-width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 20px; background: var(--paper-strong); }
table { width: 100%; border-collapse: collapse; min-width: 860px; }
th, td { text-align: left; vertical-align: top; padding: 14px 16px; border-top: 1px solid var(--line); line-height: 1.65; overflow-wrap: anywhere; }
thead th { border-top: 0; font-size: 14px; color: var(--muted); font-weight: 700; background: rgba(255,255,255,.52); }
.meta-list { display: grid; gap: 8px; margin: 0; }
.meta-row { display: grid; grid-template-columns: 140px 1fr; gap: 10px; align-items: baseline; }
.meta-row dt { color: var(--muted); font-weight: 600; }
.meta-row dd { margin: 0; }
.footer-nav { margin-top: 28px; display: flex; justify-content: space-between; gap: 12px; }
.small-note { color: var(--muted); font-size: 13px; line-height: 1.6; }
code { background: rgba(255,255,255,.7); border-radius: 8px; padding: 1px 6px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .92em; }
@media (max-width: 900px) {
  .feature, .detail-layout, .trend-grid, .archive-item, .meta-row { grid-template-columns: 1fr; }
  .archive-item .jump { justify-self: start; }
  .toc { position: static; }
  .page { width: min(100vw - 20px, 1120px); padding-top: 24px; }
}
"""
    js = """document.documentElement.dataset.site = 'shanghai-youth-ai-edu';"""
    (assets_dir / "site.css").write_text(css, encoding="utf-8")
    (assets_dir / "site.js").write_text(js, encoding="utf-8")


def write_json_index(path: Path, reports: list[Report]) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "date": report.date,
                    "title": report.title,
                    "archiveHeadline": report.archive_headline,
                    "archiveSummary": report.archive_summary,
                    "summaryBullets": report.summary_bullets[:3],
                    "detailPath": report.detail_path,
                }
                for report in reports
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_homepage(path: Path, reports: list[Report]) -> None:
    latest = reports[0]
    trends = build_trends(reports[:5])
    archive_items = "\n".join(render_archive_item(report) for report in reports)
    trend_cards = "\n".join(
        f"""
        <article class="trend-card">
          <div class="tag">{html.escape(tag)}</div>
          <h3>{html.escape(headline)}</h3>
          <p>{linkify_inline(description)}</p>
        </article>
        """
        for tag, headline, description in trends
    )
    summary_list = "".join(f"<li>{linkify_inline(item)}</li>" for item in latest.summary_bullets[:3])
    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>上海青少年 AI 教育情报</title>
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <main class="page">
    <header class="hero">
      <div class="eyebrow">上海青少年 AI 教育情报</div>
      <h1>每天一页<br>看清上海少儿 AI 与英语市场。</h1>
      <p>持续跟踪上海青少年 AI 教育、英语素质教育、财商与创业表达的市场变化，把每日判断沉淀为可阅读、可归档、可回看的研究型日报站。</p>
    </header>

    <section class="feature">
      <div class="feature-copy">
        <div class="eyebrow">Latest Issue</div>
        <h2>最新一期摘要</h2>
        <p>摘要包含最值得看的判断、趋势和归档，完整正文、机构表、证据链接和渠道说明请进入每天的独立详情页阅读。</p>
        <ol class="bullet-list">{summary_list}</ol>
      </div>
      <aside class="summary-card">
        <div>
          <div class="date">{latest.date}</div>
          <div class="claim">{linkify_inline(latest.archive_headline)}</div>
        </div>
        <a class="cta" href="{latest.detail_path}">查看当日详情页 →</a>
      </aside>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>趋势 / 判断</h2>
        <p>横向汇总最近几天最值得反复看的核心结论。</p>
      </div>
      <div class="trend-grid">{trend_cards}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>历史归档</h2>
        <p>按日期浏览，进入单日报详情页。</p>
      </div>
      <div class="archive-wrap">{archive_items}</div>
    </section>
  </main>
  <script src="assets/site.js"></script>
</body>
</html>
"""
    path.write_text(body, encoding="utf-8")


def build_trends(reports: list[Report]) -> list[tuple[str, str, str]]:
    all_bullets = [bullet for report in reports for bullet in report.summary_bullets]
    return [
        ("市场拥挤度", headline_from_bullet(pick_bullet(all_bullets, ["拥挤", "英语"])), "家长对纯英语课程的耐心在下降，能承接项目制、综合素养和展示结果的产品更容易拿到预算。"),
        ("产品白地", headline_from_bullet(pick_bullet(all_bullets, ["白地", "头部", "财商"])), "低龄 `AI+财商+英语表达` 还没有形成稳定头部，仍有空间做出结果更清晰的产品结构。"),
        ("竞争演化", headline_from_bullet(pick_bullet(all_bullets, ["结果物", "展示", "高客单", "创业"])), "被购买的越来越不是抽象知识点，而是商业计划书、AI 海报、路演和作品集这类可展示成果。"),
    ]


def pick_bullet(bullets: list[str], keywords: list[str]) -> str:
    for bullet in bullets:
        if any(keyword in bullet for keyword in keywords):
            return bullet
    return bullets[0]


def render_archive_item(report: Report) -> str:
    return f"""
    <article class="archive-item">
      <strong>{report.date}</strong>
      <div>
        <div class="headline">{linkify_inline(report.archive_headline)}</div>
        <p>{linkify_inline(report.archive_summary)}</p>
      </div>
      <a class="jump" href="{report.detail_path}">阅读全文</a>
    </article>
    """


def write_detail_pages(root: Path, reports: list[Report]) -> None:
    for index, report in enumerate(reports):
        prev_report = reports[index - 1] if index > 0 else None
        next_report = reports[index + 1] if index + 1 < len(reports) else None
        html_text = render_detail_page(report, prev_report, next_report)
        (root / report.detail_path).write_text(html_text, encoding="utf-8")


def render_detail_page(report: Report, prev_report: Report | None, next_report: Report | None) -> str:
    toc_items = "".join(
        f'<li><a href="#{section_id(title)}">{html.escape(title)}</a></li>'
        for title in report.sections
    )
    sections_html = "\n".join(render_section(title, content) for title, content in report.sections.items())
    prev_link = f'<a href="{prev_report.detail_path}">← {prev_report.date}</a>' if prev_report else "<span></span>"
    next_link = f'<a href="{next_report.detail_path}">{next_report.date} →</a>' if next_report else "<span></span>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(report.title)}</title>
  <link rel="stylesheet" href="../assets/site.css">
</head>
<body>
  <main class="page">
    <header class="hero detail-hero">
      <div class="eyebrow"><a href="../index.html">返回首页</a></div>
      <h1>{html.escape(report.title)}</h1>
      <p>完整保留当日判断、机构观察、课程线索、启发与来源说明。</p>
    </header>

    <div class="detail-layout">
      <aside class="toc">
        <h3>章节导航</h3>
        <ul>{toc_items}</ul>
      </aside>
      <article class="detail-card">
        {sections_html}
        <div class="footer-nav">{prev_link}{next_link}</div>
        <p class="small-note">原始 Markdown 档案：{html.escape(report.source_path)}</p>
      </article>
    </div>
  </main>
  <script src="../assets/site.js"></script>
</body>
</html>
"""


def render_section(title: str, content: str) -> str:
    if title == "机构与课程表":
        inner = render_catalog_section(content)
    else:
        inner = render_generic_section(content)
    return f'<section id="{section_id(title)}"><h2>{html.escape(title)}</h2>{inner}</section>'


def render_catalog_section(content: str) -> str:
    table_html = render_markdown_table(content)
    if table_html:
        return table_html
    blocks = split_numbered_blocks(content)
    if not blocks:
        return render_generic_section(content)
    rendered = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        heading = re.sub(r"^\d+\.\s*", "", lines[0])
        pairs = []
        extra = []
        pending_key: str | None = None
        for line in lines[1:]:
            if line.startswith("http://") or line.startswith("https://"):
                if pending_key is not None:
                    pairs.append((pending_key, line))
                else:
                    extra.append(line)
                continue
            normalized = line.replace("：", ":")
            if ":" in normalized:
                key, value = normalized.split(":", 1)
                key = key.strip()
                value = value.strip()
                pending_key = key
                if value:
                    pairs.append((key, value))
            else:
                extra.append(line)
        meta = "".join(
            f'<div class="meta-row"><dt>{html.escape(key)}</dt><dd>{linkify_inline(value)}</dd></div>'
            for key, value in pairs
        )
        extra_html = "".join(f"<p>{linkify_inline(line)}</p>" for line in extra)
        rendered.append(
            f'<article class="entry-card"><h4>{linkify_inline(heading)}</h4><dl class="meta-list">{meta}</dl>{extra_html}</article>'
        )
    return "".join(rendered)


def render_generic_section(content: str) -> str:
    blocks = split_blocks(content)
    rendered = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if all(re.match(r"^\d+\.\s+.+$", line) for line in lines):
            items = "".join(f"<li>{linkify_inline(re.sub(r'^\d+\.\s*', '', line))}</li>" for line in lines)
            rendered.append(f"<ol>{items}</ol>")
            continue
        if all(re.match(r"^[-*]\s+.+$", line) for line in lines):
            items = "".join(f"<li>{linkify_inline(re.sub(r'^[-*]\s*', '', line))}</li>" for line in lines)
            rendered.append(f"<ul>{items}</ul>")
            continue
        rendered.append("".join(f"<p>{linkify_inline(line)}</p>" for line in lines))
    return "".join(rendered)


def render_markdown_table(content: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 2:
        return ""
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    thead = "".join(f"<th>{linkify_inline(header)}</th>" for header in headers)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{linkify_inline(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>'


def split_blocks(content: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", content.strip()) if block.strip()]


def split_numbered_blocks(content: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if re.match(r"^\d+\.\s+", line.strip()):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(block).strip() for block in blocks]


def linkify_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    url_pattern = re.compile(r"(https?://[^\s<]+)")
    return url_pattern.sub(lambda match: f'<a href="{match.group(1)}">{match.group(1)}</a>', escaped)


def section_id(title: str) -> str:
    title = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", title).strip("-").lower()
    return title or "section"


def headline_from_bullet(text: str, limit: int = 44) -> str:
    colon = "：" if "：" in text else ":" if ":" in text else ""
    if colon and text.startswith("今天"):
        tail = text.split(colon, 1)[1].strip()
        for tail_sep in ("。", "；", "，"):
            tail_head = tail.split(tail_sep, 1)[0].strip()
            if 8 <= len(tail_head) <= limit:
                return tail_head + (tail_sep if tail_sep in ("。", "；") else "")
    for sep in ("。", "；", "，", ":"):
        head = text.split(sep, 1)[0].strip()
        if 8 <= len(head) <= limit and not (head.startswith("今天") and len(head) < 14):
            return head + (sep if sep in ("。", "；") else "")
        if sep == ":" and ":" in text and len(head) < 14:
            tail = text.split(sep, 1)[1].strip()
            for tail_sep in ("。", "；", "，"):
                tail_head = tail.split(tail_sep, 1)[0].strip()
                if 8 <= len(tail_head) <= limit:
                    return tail_head + (tail_sep if tail_sep in ("。", "；") else "")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def main() -> int:
    root = Path.cwd()
    build_site(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
