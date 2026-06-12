import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.generate_daily_site import build_market_observations, build_site, parse_report


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
            self.assertTrue((root / "site-data" / "reports.json").exists())
            homepage = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("最新日报判断", homepage)
            self.assertIn("<h2>市场观察</h2>", homepage)
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
