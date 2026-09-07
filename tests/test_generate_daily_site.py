import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.generate_daily_site import (
    Report,
    build_market_observations,
    build_site,
    build_trends,
    headline_from_bullet,
    linkify_inline,
    parse_report,
    render_catalog_section,
)


class ParseReportTests(unittest.TestCase):
    def test_parse_report_extracts_summary_and_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shanghai-youth-ai-edu-daily-2026-06-04.md"
            path.write_text(
                textwrap.dedent(
                    """\
                    上海青少年AI教育情报 2026-06-04

                    今日结论
                    1. 第一条判断。
                    2. 第二条判断。
                    3. 第三条判断。

                    英语机构转型观察
                    1. 观察内容。

                    渠道覆盖与失败说明
                    1. 说明内容。
                    """
                ),
                encoding="utf-8",
            )

            report = parse_report(path)

            self.assertEqual(report.date, "2026-06-04")
            self.assertEqual(report.title, "上海青少年AI教育情报 2026-06-04")
            self.assertEqual(report.summary_bullets[:2], ["第一条判断。", "第二条判断。"])
            self.assertIn("英语机构转型观察", report.sections)
            self.assertEqual(report.archive_headline, "第一条判断。")

    def test_parse_report_supports_markdown_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shanghai-youth-ai-edu-daily-2026-05-31.md"
            path.write_text(
                textwrap.dedent(
                    """\
                    # 上海青少年AI教育情报 2026-05-31

                    ## 今日结论
                    1. 旧格式第一条。
                    2. 旧格式第二条。

                    ## 渠道覆盖与失败说明
                    1. 说明内容。
                    """
                ),
                encoding="utf-8",
            )

            report = parse_report(path)

            self.assertEqual(report.title, "上海青少年AI教育情报 2026-05-31")
            self.assertEqual(report.summary_bullets[0], "旧格式第一条。")


class BuildSiteTests(unittest.TestCase):
    def test_linkify_inline_preserves_markdown_and_bare_url_boundaries(self) -> None:
        rendered = linkify_inline(
            "来源：[官网](https://example.com/a?x=1&y=2)；"
            "[PDF](https://example.com/file.pdf)。补充：https://example.com/news。"
        )

        self.assertIn('<a href="https://example.com/a?x=1&amp;y=2">官网</a>；', rendered)
        self.assertIn('<a href="https://example.com/file.pdf">PDF</a>。', rendered)
        self.assertIn('<a href="https://example.com/news">https://example.com/news</a>。', rendered)
        self.assertNotIn("](<a", rendered)

    def test_build_trends_uses_distinct_bullets_when_keywords_overlap(self) -> None:
        reports = [
            Report(
                date="2026-06-12",
                title="上海青少年AI教育情报 2026-06-12",
                summary_bullets=[
                    "今天最值得关注的是小红书正文级线索 AI赋能财商课 已经不只是标题：其内容明确写到项目展示和双语场景。",
                    "上海幼少儿英语市场依旧拥挤，且头部英语机构已从语言课转向综合能力、科创、AI 或全科智习。",
                    "高客单营地被购买的越来越不是抽象知识点，而是商业计划书、AI海报、路演和作品集这类成果。",
                ],
                archive_headline="",
                archive_summary="",
                trend_bullets=[],
                detail_path="daily/2026-06-12.html",
                sections={},
                source_path="",
            )
        ]

        trends = build_trends(reports)
        headlines = [headline for _, headline, _ in trends]

        self.assertEqual(len(headlines), len(set(headlines)))
        self.assertIn("高客单营地", headlines[2])

    def test_market_observations_cover_course_product_and_enrollment(self) -> None:
        observations = build_market_observations()

        self.assertGreaterEqual(len(observations), 5)
        combined_use_cases = {use_case for item in observations for use_case in item.use_cases}
        self.assertIn("课程设计", combined_use_cases)
        self.assertIn("产品开发", combined_use_cases)
        self.assertIn("招生卖点", combined_use_cases)
        for observation in observations:
            self.assertTrue(observation.title)
            self.assertTrue(observation.brief)
            self.assertTrue(observation.detail)
            self.assertTrue(observation.actions)
            self.assertTrue(observation.evidence)

    def test_trends_classify_claim_not_later_qualifications(self) -> None:
        report = Report(
            date="2026-08-31", title="上海青少年AI教育情报 2026-08-31",
            summary_bullets=[
                "青少年可运行AI产品与真实成交已有反例，不能单独当作白地。没有英语教学证据。",
                "上海公共AI供给已出现创意生成与路演。不能证明付费需求。",
                "上海幼少儿英语是选择多的市场；本轮不足以证明饱和。",
            ],
            archive_headline="", archive_summary="", trend_bullets=[],
            detail_path="daily/2026-08-31.html", sections={}, source_path="",
        )
        trends = build_trends([report])
        self.assertIn("幼少儿英语", trends[0][1])
        self.assertIn("真实成交", trends[1][1])
        self.assertIn("公共AI供给", trends[2][1])
        self.assertTrue(all("2026-08-31" in description for _, _, description in trends))

    def test_headline_does_not_reduce_to_reporting_window(self) -> None:
        headline = headline_from_bullet(
            "8 月 19–24 日，上海公共AI基础体验的供给持续增加，"
            "多个区域披露教育应用方向，长期学习效果和家庭付费转化仍然需要验证。"
        )
        self.assertFalse(headline.startswith("8 月"))
        self.assertIn("上海公共AI", headline)

    def test_trends_do_not_relabel_unmatched_bullets(self) -> None:
        self.assertEqual(len(build_trends([])), 3)
        self.assertTrue(all("仍需补证" in headline for _, headline, _ in build_trends([])))

    def test_catalog_keeps_source_caveats_outside_table(self) -> None:
        rendered = render_catalog_section(
            "以下只代表公开表述。\n\n| 品牌 | 价格 |\n| --- | --- |\n| 示例 | 未核 |\n\n"
            "现售、实际交付、成交与效果不是同一证据等级。"
        )
        self.assertIn("以下只代表公开表述", rendered)
        self.assertIn("现售、实际交付、成交与效果不是同一证据等级", rendered)
        self.assertLess(rendered.index("以下只代表"), rendered.index("<table>"))
        self.assertGreater(rendered.index("现售、实际交付"), rendered.index("</table>"))

    def test_market_observations_do_not_claim_unverified_demand(self) -> None:
        observations = build_market_observations()
        copy = " ".join(
            " ".join([item.title, item.brief, item.detail, *item.actions])
            for item in observations
        )
        for unsupported_claim in [
            "纯英语不再支撑高溢价", "说明需求存在", "就能成为五日营的强入口",
            "家长更容易为作品集", "把产品命名和交付锁定",
        ]:
            self.assertNotIn(unsupported_claim, copy)
        self.assertIn("成人帮助", copy)
        self.assertIn("全成本利润", copy)
        self.assertIn("仍需验证", copy)

    def test_build_site_writes_home_detail_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_dir = root / "reports"
            reports_dir.mkdir()
            (reports_dir / "shanghai-youth-ai-edu-daily-2026-06-03.md").write_text(
                "上海青少年AI教育情报 2026-06-03\n\n今日结论\n1. 旧日报判断。\n\n渠道覆盖与失败说明\n1. 说明。\n",
                encoding="utf-8",
            )
            (reports_dir / "shanghai-youth-ai-edu-daily-2026-06-04.md").write_text(
                "上海青少年AI教育情报 2026-06-04\n\n今日结论\n1. 最新日报判断。\n2. 第二条。\n\n渠道覆盖与失败说明\n1. 说明。\n",
                encoding="utf-8",
            )

            build_site(root)

            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "daily" / "2026-06-04.html").exists())
            detail = (root / "daily" / "2026-06-04.html").read_text(encoding="utf-8")
            self.assertIn('href="2026-06-03.html"', detail)
            self.assertNotIn('href="daily/2026-06-03.html"', detail)
            self.assertTrue((root / "site-data" / "reports.json").exists())
            homepage = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("最新日报判断", homepage)
            self.assertIn("<h2>市场观察</h2>", homepage)
            self.assertIn("截至2026-06-04的证据与待验证产品建议", homepage)
            self.assertNotIn("截至2026-08-31的证据与待验证产品建议", homepage)
            self.assertNotIn("市场观察贴纸", homepage)
            self.assertIn('id="market-observations"', homepage)
            self.assertIn('class="market-board"', homepage)
            self.assertGreaterEqual(homepage.count('class="market-sticker"'), 5)
            self.assertIn('class="sticker-number">01', homepage)
            self.assertIn('class="sticker-application"', homepage)
            self.assertNotIn('class="insight-sticker"', homepage)
            self.assertIn("<details", homepage)
            css = (root / "assets" / "site.css").read_text(encoding="utf-8")
            self.assertIn("暖灰", css)
            self.assertIn("calc(100vw - 20px)", css)
            data = json.loads((root / "site-data" / "reports.json").read_text(encoding="utf-8"))
            self.assertEqual(data[0]["date"], "2026-06-04")

    def test_build_site_includes_legacy_root_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_dir = root / "reports"
            reports_dir.mkdir()
            (reports_dir / "shanghai-youth-ai-edu-daily-2026-06-04.md").write_text(
                "上海青少年AI教育情报 2026-06-04\n\n今日结论\n1. 最新日报判断。\n\n渠道覆盖与失败说明\n1. 说明。\n",
                encoding="utf-8",
            )
            (root / "shanghai-youth-ai-edu-2026-05-28.md").write_text(
                "# 上海青少年AI教育情报 2026-05-28\n\n## 今日结论\n1. 早期根目录日报判断。\n\n## 渠道覆盖与失败说明\n1. 说明。\n",
                encoding="utf-8",
            )

            build_site(root)

            self.assertTrue((root / "daily" / "2026-05-28.html").exists())
            data = json.loads((root / "site-data" / "reports.json").read_text(encoding="utf-8"))
            self.assertEqual([item["date"] for item in data], ["2026-06-04", "2026-05-28"])


class CliTests(unittest.TestCase):
    def test_cli_builds_site_for_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_dir = root / "reports"
            reports_dir.mkdir()
            (reports_dir / "shanghai-youth-ai-edu-daily-2026-06-04.md").write_text(
                "上海青少年AI教育情报 2026-06-04\n\n今日结论\n1. 今日判断。\n\n渠道覆盖与失败说明\n1. 说明。\n",
                encoding="utf-8",
            )

            script_src = Path(__file__).resolve().parent.parent / "scripts" / "generate_daily_site.py"
            script_dir = root / "scripts"
            script_dir.mkdir()
            script_dst = script_dir / "generate_daily_site.py"
            script_dst.write_text(script_src.read_text(encoding="utf-8"), encoding="utf-8")

            result = subprocess.run(
                ["python3", str(script_dst)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "daily" / "2026-06-04.html").exists())


if __name__ == "__main__":
    unittest.main()
