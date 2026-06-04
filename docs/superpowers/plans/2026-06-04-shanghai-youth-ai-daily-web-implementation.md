# Shanghai Youth AI Daily Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static daily-report website from the existing Markdown reports, replace the automation's WeChat delivery requirement, and regenerate the homepage, detail pages, and archive on each run.

**Architecture:** A single Python generator script will read Markdown reports from `reports/`, extract a small structured model, render static HTML into `index.html` and `daily/*.html`, and write shared assets plus a JSON index. Tests will lock the parsing and generation behavior before implementation, and `automation-prompt.md` will be updated so future runs treat site generation as the final delivery step.

**Tech Stack:** Python 3.12 standard library, `unittest`, static HTML/CSS/JSON

---

### Task 1: Lock the report parsing contract

**Files:**
- Create: `tests/test_generate_daily_site.py`
- Create: `scripts/generate_daily_site.py`

- [ ] **Step 1: Write the failing tests**

```python
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.generate_daily_site import parse_report


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_daily_site.ParseReportTests.test_parse_report_extracts_summary_and_sections`
Expected: FAIL with `ModuleNotFoundError` or missing `parse_report`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Report:
    date: str
    title: str
    summary_bullets: list[str]
    archive_headline: str
    sections: dict[str, str]


def parse_report(path: Path) -> Report:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_daily_site.ParseReportTests.test_parse_report_extracts_summary_and_sections`
Expected: PASS

### Task 2: Lock full site generation

**Files:**
- Modify: `tests/test_generate_daily_site.py`
- Modify: `scripts/generate_daily_site.py`

- [ ] **Step 1: Write the failing tests**

```python
from scripts.generate_daily_site import build_site


class BuildSiteTests(unittest.TestCase):
    def test_build_site_writes_home_detail_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_dir = root / "reports"
            reports_dir.mkdir()
            (reports_dir / "shanghai-youth-ai-edu-daily-2026-06-03.md").write_text(
                "上海青少年AI教育情报 2026-06-03\\n\\n今日结论\\n1. 旧日报判断。\\n\\n渠道覆盖与失败说明\\n1. 说明。\\n",
                encoding="utf-8",
            )
            (reports_dir / "shanghai-youth-ai-edu-daily-2026-06-04.md").write_text(
                "上海青少年AI教育情报 2026-06-04\\n\\n今日结论\\n1. 最新日报判断。\\n2. 第二条。\\n\\n渠道覆盖与失败说明\\n1. 说明。\\n",
                encoding="utf-8",
            )

            build_site(root)

            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "daily" / "2026-06-04.html").exists())
            self.assertTrue((root / "site-data" / "reports.json").exists())
            self.assertIn("最新日报判断", (root / "index.html").read_text(encoding="utf-8"))
            self.assertIn("暖灰", (root / "assets" / "site.css").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_daily_site.BuildSiteTests.test_build_site_writes_home_detail_and_json`
Expected: FAIL because `build_site` or generated files do not exist

- [ ] **Step 3: Write minimal implementation**

```python
def build_site(root: Path) -> None:
    reports = load_reports(root / "reports")
    write_assets(root / "assets")
    write_index(root, reports)
    write_detail_pages(root, reports)
    write_json_index(root, reports)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_daily_site.BuildSiteTests.test_build_site_writes_home_detail_and_json`
Expected: PASS

### Task 3: Replace automation delivery instructions

**Files:**
- Modify: `automation-prompt.md`
- Modify: `scripts/generate_daily_site.py`

- [ ] **Step 1: Write the failing test**

```python
class CliTests(unittest.TestCase):
    def test_cli_builds_site_for_current_project(self) -> None:
        ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_generate_daily_site.CliTests.test_cli_builds_site_for_current_project`
Expected: FAIL because CLI entrypoint is missing

- [ ] **Step 3: Write minimal implementation**

```python
def main() -> int:
    root = Path(__file__).resolve().parent.parent
    build_site(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Then update `automation-prompt.md` so the archive/output section and final delivery section require:

- saving Markdown reports as before
- running `python3 scripts/generate_daily_site.py`
- verifying `index.html`, `daily/YYYY-MM-DD.html`, and `site-data/reports.json`
- no WeChat send step

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_generate_daily_site.CliTests.test_cli_builds_site_for_current_project`
Expected: PASS

### Task 4: Verify the whole website against real reports

**Files:**
- Modify: `scripts/generate_daily_site.py` as needed
- Modify: `assets/site.css` as needed
- Modify: `index.html`, `daily/*.html`, `site-data/reports.json` by running the generator

- [ ] **Step 1: Build the real site**

Run: `python3 scripts/generate_daily_site.py`
Expected: exit 0 and regenerated website files

- [ ] **Step 2: Verify generated outputs exist**

Run: `test -f index.html && test -f daily/2026-06-04.html && test -f site-data/reports.json && echo OK`
Expected: `OK`

- [ ] **Step 3: Verify tests all pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests PASS

- [ ] **Step 4: Manually inspect key content**

Run: `sed -n '1,120p' index.html && printf '\\n---\\n' && sed -n '1,120p' daily/2026-06-04.html`
Expected: homepage contains latest summary + trend section + archive entries; detail page contains the full report content
