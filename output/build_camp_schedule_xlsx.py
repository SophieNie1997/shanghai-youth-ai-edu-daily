from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import zipfile


OUT_DIR = Path("/Users/sophienie/Documents/Codex/2026-05-25/9-ai/output")
OUT_PATH = OUT_DIR / "AI时代小小CEO五日营_每日课程安排.xlsx"


TITLE = "AI时代小小CEO五日营｜每日课程安排"
SUBTITLE = "主线：发现问题 → 验证需求 → 做出方案 → 学会定价 → 双语发布"


HEADERS = [
    "时间",
    "DAY 1\n发现好问题\n从兴趣到创业点子",
    "DAY 2\n找到真需求\n看看谁真的会想要",
    "DAY 3\n做出第一版\n把点子变成小产品",
    "DAY 4\n学会做生意\n会定价，也会算账",
    "DAY 5\n自信去发布\n双语展示我的公司",
]


ROWS = [
    [
        "上午",
        "• 开营破冰，理解什么是“小公司”\n• 从生活里找真实问题\n• 组队分工：CEO / 产品 / 品牌 / 表达",
        "• 认识目标用户、场景与痛点\n• 学会设计访谈问题\n• 梳理谁最可能成为第一位客户",
        "• 认识 MVP：先做可展示版本\n• 画产品草图与页面结构\n• 明确产品的 3 条核心卖点",
        "• 财商核心课：收入、成本、利润、回本\n• 区分固定成本、可变成本、隐藏成本\n• 做一页纸商业地图",
        "• 学会 3 分钟讲清楚问题与价值\n• 双语表达训练：核心句型 + 自信呈现\n• 发布会彩排与 Q&A 训练",
    ],
    [
        "下午",
        "• AI 发散多个产品或服务点子\n• 挑出“最值得做”的方向\n• 完成立项卡与 30 秒项目介绍",
        "• 整理真实反馈，区分“喜欢”和“愿意买”\n• 形成用户画像卡与痛点清单\n• 删掉不必要功能，校准方向",
        "• 用 AI 做海报、原型与展示页\n• 搭建产品页 / 销售页初版\n• 试展并根据反馈继续优化",
        "• 观察竞品，理解为什么价格不同\n• 用 AI 做 Logo、口号、海报与文案\n• 写出推广计划卡",
        "• 家长 Demo Day / 小小CEO发布会\n• 每组完成中英双语展示\n• 评委反馈、颁奖与成长复盘",
    ],
    [
        "当日交付",
        "• 公司名\n• 项目立项卡\n• 目标用户初版",
        "• 用户访谈记录\n• 用户画像卡\n• 痛点清单",
        "• 产品原型\n• 展示页初版\n• 产品卖点 3 条",
        "• 成本表\n• 价格表\n• 商业地图",
        "• 双语路演\n• 最终展示页\n• 成长复盘卡",
    ],
]


def col_letter(idx: int) -> str:
    letters = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def cell_ref(row: int, col: int) -> str:
    return f"{col_letter(col)}{row}"


def inline_str_cell(ref: str, text: str, style: int) -> str:
    safe_text = escape(text)
    return (
        f'<c r="{ref}" s="{style}" t="inlineStr">'
        f"<is><t xml:space=\"preserve\">{safe_text}</t></is></c>"
    )


def build_sheet_xml() -> str:
    row_parts = []

    def add_row(r: int, values: list[str], style_map: list[int], height: int | None = None) -> None:
        attrs = [f'r="{r}"']
        if height is not None:
            attrs.append(f'ht="{height}" customHeight="1"')
        cells = []
        for c, value in enumerate(values, start=1):
            if value == "":
                continue
            cells.append(inline_str_cell(cell_ref(r, c), value, style_map[c - 1]))
        row_parts.append(f"<row {' '.join(attrs)}>{''.join(cells)}</row>")

    add_row(1, [TITLE, "", "", "", "", ""], [1, 0, 0, 0, 0, 0], 32)
    add_row(2, [SUBTITLE, "", "", "", "", ""], [2, 0, 0, 0, 0, 0], 24)
    add_row(3, ["", "", "", "", "", ""], [0, 0, 0, 0, 0, 0], 10)
    add_row(4, HEADERS, [3, 3, 3, 3, 3, 3], 44)
    add_row(5, ROWS[0], [4, 5, 5, 5, 5, 5], 110)
    add_row(6, ROWS[1], [4, 6, 6, 6, 6, 6], 110)
    add_row(7, ROWS[2], [7, 8, 8, 8, 8, 8], 76)

    cols = (
        '<cols>'
        '<col min="1" max="1" width="10" customWidth="1"/>'
        '<col min="2" max="6" width="20" customWidth="1"/>'
        '</cols>'
    )

    merges = (
        "<mergeCells count=\"2\">"
        "<mergeCell ref=\"A1:F1\"/>"
        "<mergeCell ref=\"A2:F2\"/>"
        "</mergeCells>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheetViews><sheetView workbookViewId=\"0\"><pane ySplit=\"4\" topLeftCell=\"A5\" activePane=\"bottomLeft\" state=\"frozen\"/></sheetView></sheetViews>"
        "<sheetFormatPr defaultRowHeight=\"18\"/>"
        f"{cols}"
        "<sheetData>"
        f"{''.join(row_parts)}"
        "</sheetData>"
        f"{merges}"
        "<pageMargins left=\"0.4\" right=\"0.4\" top=\"0.55\" bottom=\"0.55\" header=\"0.3\" footer=\"0.3\"/>"
        "</worksheet>"
    )


def build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font>
      <sz val="10"/>
      <name val="PingFang SC"/>
      <family val="2"/>
      <color rgb="FF2B2B2B"/>
    </font>
    <font>
      <b/>
      <sz val="15"/>
      <name val="PingFang SC"/>
      <family val="2"/>
      <color rgb="FFFFFFFF"/>
    </font>
    <font>
      <sz val="10"/>
      <name val="PingFang SC"/>
      <family val="2"/>
      <color rgb="FF8B4A36"/>
    </font>
    <font>
      <b/>
      <sz val="10"/>
      <name val="PingFang SC"/>
      <family val="2"/>
      <color rgb="FF2B2B2B"/>
    </font>
  </fonts>
  <fills count="8">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF46C1B"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFF2EC"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFDE2DB"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFF6F2"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFF7EC"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFCE9E3"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border>
      <left/><right/><top/><bottom/><diagonal/>
    </border>
    <border>
      <left style="thin"><color rgb="FFFFFFFF"/></left>
      <right style="thin"><color rgb="FFFFFFFF"/></right>
      <top style="thin"><color rgb="FFFFFFFF"/></top>
      <bottom style="thin"><color rgb="FFFFFFFF"/></bottom>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="9">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="3" fillId="7" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="left" vertical="top" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="left" vertical="top" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="3" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="left" vertical="top" wrapText="1"/>
    </xf>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>
"""


def build_workbook_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="五日营课表" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""


def build_root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def build_workbook_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


def build_content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def build_core_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>AI时代小小CEO五日营课表</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-06-02T06:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-06-02T06:00:00Z</dcterms:modified>
</cp:coreProperties>
"""


def build_app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Excel</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>1</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="1" baseType="lpstr">
      <vt:lpstr>五日营课表</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
</Properties>
"""


def build_xlsx(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", build_content_types())
        zf.writestr("_rels/.rels", build_root_rels())
        zf.writestr("docProps/core.xml", build_core_xml())
        zf.writestr("docProps/app.xml", build_app_xml())
        zf.writestr("xl/workbook.xml", build_workbook_xml())
        zf.writestr("xl/_rels/workbook.xml.rels", build_workbook_rels())
        zf.writestr("xl/styles.xml", build_styles_xml())
        zf.writestr("xl/worksheets/sheet1.xml", build_sheet_xml())


if __name__ == "__main__":
    build_xlsx(OUT_PATH)
    print(OUT_PATH)
