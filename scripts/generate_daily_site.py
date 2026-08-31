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


@dataclass(frozen=True)
class MarketObservation:
    label: str
    title: str
    brief: str
    detail: str
    use_cases: list[str]
    actions: list[str]
    evidence: list[str]


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
.market-section { position: relative; }
.market-board { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: start; }
.market-sticker {
  border: 1px solid rgba(139, 82, 35, 0.16);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255,255,255,0.9), rgba(246, 226, 193, 0.72)),
    var(--paper);
  box-shadow: 0 14px 34px rgba(76, 56, 35, 0.08);
  overflow: hidden;
}
.market-sticker summary {
  display: grid;
  grid-template-columns: 46px 1fr;
  gap: 14px;
  padding: 18px 20px;
  cursor: pointer;
  list-style: none;
}
.market-sticker summary::-webkit-details-marker { display: none; }
.market-sticker summary::after {
  content: "展开";
  grid-column: 2;
  width: fit-content;
  margin-top: 2px;
  border-radius: 999px;
  border: 1px solid rgba(169, 90, 42, 0.18);
  color: #7a4d2f;
  background: rgba(255,255,255,0.56);
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
}
.market-sticker[open] summary::after { content: "收起"; }
.sticker-number {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: rgba(169, 90, 42, 0.14);
  color: #7a4d2f;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.sticker-copy { display: grid; gap: 7px; min-width: 0; }
.sticker-category { color: var(--accent); font-size: 12px; font-weight: 800; }
.sticker-copy strong { font-size: 19px; line-height: 1.25; letter-spacing: -0.02em; overflow-wrap: anywhere; }
.sticker-copy span:last-child { color: var(--muted); font-size: 14px; line-height: 1.65; overflow-wrap: anywhere; }
.sticker-detail { padding: 0 20px 20px 80px; }
.sticker-detail p { color: var(--muted); line-height: 1.75; margin: 0 0 12px; overflow-wrap: anywhere; }
.sticker-application {
  border-left: 3px solid rgba(169, 90, 42, 0.4);
  background: rgba(255,255,255,0.44);
  border-radius: 0 16px 16px 0;
  padding: 12px 14px;
  line-height: 1.7;
  color: #4f4a43;
  overflow-wrap: anywhere;
}
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
  .feature, .detail-layout, .trend-grid, .market-board, .archive-item, .meta-row { grid-template-columns: 1fr; }
  .hero h1 { font-size: clamp(34px, 11vw, 46px); line-height: 1.08; letter-spacing: -0.02em; overflow-wrap: anywhere; }
  .hero p { font-size: 16px; overflow-wrap: anywhere; }
  .feature { padding: 20px; }
  .feature-copy h2 { font-size: 30px; }
  .summary-card .claim { font-size: 23px; overflow-wrap: anywhere; }
  .market-sticker summary { grid-template-columns: 42px 1fr; padding: 16px; }
  .sticker-detail { padding: 0 16px 18px 72px; }
  .archive-item .jump { justify-self: start; }
  .toc { position: static; }
  .page { width: min(1120px, calc(100vw - 20px)); padding-top: 24px; }
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
    market_observations = render_market_observations(build_market_observations())
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
      <h1>每天一页<br>上海青少年 AI 教育市场观察</h1>
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

    {market_observations}

    <section class="section">
      <div class="section-head">
        <h2>历史归档</h2>
        <p>按日期浏览，保留各日当时的判断；旧结论请结合最新一期的补证与纠正阅读。</p>
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
    used_bullets: set[str] = set()
    trend_specs = [
        ("市场拥挤度", ["拥挤", "幼少儿英语", "幼儿英语", "英语市场"], "多种英语、科创与项目产品并存；公开供给不能直接证明门店饱和、预算转移或家长付费意愿。"),
        ("产品白地", ["白地", "三融合", "财商"], "AI产品与真实交易已有青少年个案；适龄、可复制的财商判断与英语表达教学仍需逐项核验。"),
        ("竞争演化", ["公共", "结果物", "作品集", "路演", "高客单", "创业", "展示"], "比较可运行程度、用户反馈、财务口径和儿童贡献；招生展示、成交与学习成效是不同证据。"),
    ]
    trends = []
    for tag, keywords, description in trend_specs:
        bullet = pick_bullet(all_bullets, keywords, used_bullets)
        if not bullet:
            trends.append((tag, f"{tag}仍需补证", "最近几期暂无可明确归入此主题的结论，请查看每日详情与来源边界。"))
            continue
        used_bullets.add(bullet)
        report_date = next(report.date for report in reports if bullet in report.summary_bullets)
        trends.append((tag, headline_from_bullet(bullet), f"依据 {report_date} 日报。{description}"))
    return trends


def build_market_observations() -> list[MarketObservation]:
    return [
        MarketObservation(
            label="招生卖点",
            title="英语主课与项目应用需分工",
            brief="英语PBL、双语科创与阅读已是既有供给；仅换一个项目标签不足以证明差异化。",
            detail="本轮品牌官网可见多种相邻产品，但不能推出纯英语已失去溢价。建议保留系统英语学习的价值，将财商项目定位为分层应用场景，分别评价财商判断和语言表达。",
            use_cases=["招生卖点", "产品开发"],
            actions=[
                "先核对孩子英语水平，再设置一句价值说明或进阶问答。",
                "让英语承载询问需求、解释选择等任务，不承诺点子一定被购买。",
            ],
            evidence=[
                "2026-08-31: 英孚、瑞思、爱贝等官网基线复核，未确认本周上海融合新品。",
                "2026-08-31: A加教育集团与维多利亚Arts Plus分开核验，不能合并主体。",
            ],
        ),
        MarketObservation(
            label="课程设计",
            title="成果展示也已进入公共课堂",
            brief="松江暑托班已出现AI创意生成与成果路演；有作品不等于有可用产品。",
            detail="松江官方报道披露214节AI+STEM课程与现场创作。它支持公共供给已实施的判断，不证明付费转化或学习成效；我方应比较功能测试与修改证据，而不是只比较展示效果。",
            use_cases=["课程设计", "招生卖点"],
            actions=[
                "围绕同一个问题完成第一版、测试、成本取舍和第二版。",
                "分开记录生成的图像、可操作原型与实际使用结果。",
            ],
            evidence=[
                "2026-08-28: 松江区政府发布智期科技AI+STEM暑托班实施报道。",
                "2026-08-31: 日报区分三维创意模型、可运行AI原型与真实交易。",
            ],
        ),
        MarketObservation(
            label="产品白地",
            title="融合机会要经得起反例检验",
            brief="英语商业模拟、AI营销营和青少年AI成交个案已存在，不能称三个关键词仍是白地。",
            detail="包校与ABS提供既有课程基线，上海学生参加杭州卖客松提供可运行产品和交易个案。尚待验证的是低龄可复制教学中，AI原型、财务判断与英文问答是否围绕同一项目推进。",
            use_cases=["产品开发", "招生卖点"],
            actions=[
                "竞品逐项核对年龄、原型、用户、财务、英语、迭代与儿童贡献。",
                "不把未检出完整案例写成市场不存在，也不承诺创业收益。",
            ],
            evidence=[
                "2026-08-18: 包校与ABS修正广义三融合白地判断。",
                "2026-08-25至27: 杭州网及后续报道补齐上海学生AI产品真实成交与成人渠道边界。",
            ],
        ),
        MarketObservation(
            label="转化路径",
            title="半日体验要做低风险闭环",
            brief="先验证孩子能否做出一次有理由的修改，再决定是否升级到长期学习。",
            detail="A加官网的月付与先学后付可作为低承诺入口参照，不代表履约安全已验证。体验日先试一个原型、一次反馈和一句解释，完整成果须以试营完成率为依据，不预设转化有效。",
            use_cases=["课程设计", "招生卖点"],
            actions=[
                "真实参与者先征得同意；老师模拟用户时明确标注角色测试。",
                "明确阶段交付、费用与退出规则；公开儿童影像另行征得授权。",
            ],
            evidence=[
                "2026-08-31: A加官网付费结构为本轮补证，未披露上线日期与具体退款规则。",
                "2026-08-31: 日报建议用小范围试营验证交付与理解，不宣称已提高转化。",
            ],
        ),
        MarketObservation(
            label="长期班",
            title="长期班检验连续修改能力",
            brief="同一项目的反馈、版本和解释能力可连续观察，但能否带来续费仍需验证。",
            detail="建议把技术演示、用户采用、财务假设与AI使用过程分开记录。作品集服务于观察学习变化，不等同于升学保障；跨月复测也不必每月重做一个新项目。",
            use_cases=["产品开发", "课程设计"],
            actions=[
                "保留同一项目两版原型和一个月后的真实反馈。",
                "按年龄与英语水平设置不同输出，记录教师和AI帮助的部分。",
            ],
            evidence=[
                "2026-08-24: 日报记录上海开发者成长中心的连续成长方向。",
                "2026-08-31: 复核Technovation分龄提交与原创贡献要求，仅作方法参照。",
            ],
        ),
        MarketObservation(
            label="差异化",
            title="不把成交额当作学习成绩",
            brief="真实订单值得研究，但家庭渠道、成人帮助和成本口径必须一同记录。",
            detail="卖客松个案的多数订单通过母亲账号售出，赛事计分收入不等于全成本利润。课程可以借鉴真实反馈与财务核对，不能将个案收入、名校场地或CEO身份转换成学习和招生保证。",
            use_cases=["产品开发", "招生卖点"],
            actions=[
                "分列收入、工具与推广成本、退款、渠道来源及成人协助。",
                "比较孩子为何改、如何解释，不比较谁的家长带来更多订单。",
            ],
            evidence=[
                "2026-08-21及25: 杭州网现场与赛后报道提供产品演示、用户迟疑及计分规则。",
                "2026-08-27: 杭州市政府英文站转述报道交代母亲直播与短视频渠道。",
            ],
        ),
    ]


def render_market_observations(observations: list[MarketObservation]) -> str:
    items = "\n".join(
        render_market_observation(observation, index)
        for index, observation in enumerate(observations, start=1)
    )
    return f"""
    <section class="section market-section" id="market-observations">
      <div class="section-head">
        <h2>市场观察</h2>
        <p>截至2026-08-31的证据与待验证产品建议；招生应用前仍需核对实际交付。</p>
      </div>
      <div class="market-board">{items}</div>
    </section>
    """.strip()


def render_market_observation(observation: MarketObservation, index: int) -> str:
    application = "可落地动作：" + join_inline_items(observation.actions)
    evidence = "日报依据：" + join_inline_items(observation.evidence)
    return f"""
    <details class="market-sticker">
      <summary>
        <span class="sticker-number">{index:02d}</span>
        <span class="sticker-copy">
          <span class="sticker-category">{html.escape(observation.label)}</span>
          <strong>{html.escape(observation.title)}</strong>
          <span>{html.escape(observation.brief)}</span>
        </span>
      </summary>
      <div class="sticker-detail">
        <p>{linkify_inline(observation.detail)}</p>
        <div class="sticker-application">{linkify_inline(application)}<br>{linkify_inline(evidence)}</div>
      </div>
    </details>
    """.strip()


def join_inline_items(items: list[str]) -> str:
    clean_items = [item.rstrip("。；; ") for item in items]
    return "；".join(clean_items) + "。"


def pick_bullet(bullets: list[str], keywords: list[str], used_bullets: set[str] | None = None) -> str:
    used_bullets = used_bullets or set()
    for bullet in bullets:
        # Classify the claim itself, not a later qualification such as “没有英语教学证据”.
        claim = bullet.split("。", 1)[0]
        if bullet not in used_bullets and any(keyword in claim for keyword in keywords):
            return bullet
    return ""


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
    """.strip()


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
    prev_link = f'<a href="{Path(prev_report.detail_path).name}">← {prev_report.date}</a>' if prev_report else "<span></span>"
    next_link = f'<a href="{Path(next_report.detail_path).name}">{next_report.date} →</a>' if next_report else "<span></span>"
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
        # Keep the source caveats before/after a Markdown table in the web edition.
        table_start = content.find(next(line for line in content.splitlines() if line.strip().startswith("|")))
        before_table = content[:table_start].strip()
        after_table = "\n".join(
            line for line in content[table_start:].splitlines()
            if not (line.strip().startswith("|") and line.strip().endswith("|"))
        ).strip()
        return render_generic_section(before_table) + table_html + render_generic_section(after_table)
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
    token_pattern = re.compile(
        r"`[^`]+`|\[[^\]]+\]\(https?://[^\s)]+\)|https?://[^\s<>]+"
    )
    trailing_url_punctuation = ".,;:!?，。；：！？、）)]}》】"
    rendered: list[str] = []
    cursor = 0

    for match in token_pattern.finditer(text):
        rendered.append(html.escape(text[cursor : match.start()]))
        token = match.group(0)

        if token.startswith("`"):
            rendered.append(f"<code>{html.escape(token[1:-1])}</code>")
        elif token.startswith("["):
            markdown_match = re.fullmatch(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", token)
            if markdown_match is None:
                rendered.append(html.escape(token))
            else:
                label, url = markdown_match.groups()
                rendered.append(
                    f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
                )
        else:
            url = token.rstrip(trailing_url_punctuation)
            punctuation = token[len(url) :]
            if url:
                safe_url = html.escape(url, quote=True)
                rendered.append(f'<a href="{safe_url}">{safe_url}</a>')
            rendered.append(html.escape(punctuation))

        cursor = match.end()

    rendered.append(html.escape(text[cursor:]))
    return "".join(rendered)


def section_id(title: str) -> str:
    title = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", title).strip("-").lower()
    return title or "section"


def headline_from_bullet(text: str, limit: int = 44) -> str:
    # A reporting-window prefix is metadata, not a meaningful headline.
    text = re.sub(
        r"^\d{1,2}\s*月\s*\d{1,2}(?:\s*[–—~～至-]\s*(?:\d{1,2}\s*月\s*)?\d{1,2})?\s*日[，,:：]\s*",
        "",
        text,
    )
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
