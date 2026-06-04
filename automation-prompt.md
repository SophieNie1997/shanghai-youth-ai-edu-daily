# 上海青少年AI教育情报自动化 Prompt

每天调研上海青少年、少儿、幼儿 AI 教育与英语素质教育市场动态。目标不是泛泛搜集行业新闻，而是持续帮助上海登顶升学文化传媒有限公司 / 樱桃图书馆判断：

- 上海幼儿英语市场是否拥挤；
- 主要英语机构如何转向综合素养、AI、科创、财商、项目制、营地和双语表达；
- 市面上是否出现成熟的 `AI + 财商 + 英语表达` 融合案例；
- 我方 `AI时代小小CEO体验日`、`AI时代小小CEO五日营`、长期班和高客单家庭方案可以如何差异化。

这是一个独立 cron 自动化任务。每次运行都应视为新的独立日报任务，并在本项目目录中归档结果。

## 先读普通本地进程生成的 OpenCLI 缓存

每天正式检索前，先读取本项目的 OpenCLI 预抓取缓存：

- Markdown 摘要：`/Users/sophienie/Documents/Codex/2026-05-25/9-ai/opencli-cache/latest.md`
- JSON 清单：`/Users/sophienie/Documents/Codex/2026-05-25/9-ai/opencli-cache/latest.json`

这组文件由普通本地 launchd 进程在自动化运行前生成，不依赖 Codex 自动化沙箱访问本机 daemon。如果缓存日期是当天，且其中有成功且非空记录，应先读取这些记录指向的原始 JSON 文件，把这些结果作为当天小红书、公众号、点评或 X/Twitter 登录态/站点适配器资料来源。然后再用公开网页检索补充官网、新闻稿、招生页和新变化。

如果缓存日期是当天，且至少有一条成功且非空记录，本轮不要再在自动化沙箱内运行 `opencli doctor`、`daemon restart`、`curl http://127.0.0.1:19825/status` 或任何 `opencli search` 探测命令；直接使用缓存结果，再补公开网页检索。这样可以避免把已知的自动化沙箱 localhost 限制重复写成当日问题。

只有缓存缺失、过期或全部失败时，才按下方 OpenCLI 预检逻辑尝试直接调用；若直接调用仍失败，才降级到公开网页检索。即使自动化沙箱内直接调用失败，也不要丢弃当天已生成的 `opencli-cache` 成功结果。

## OpenCLI 预检与降级策略

必须参考小越越项目 `/Users/sophienie/Documents/Codex/2026-05-16/codex-openclaw-weixin` 的调用方式：

- 自动化里不要给微信发送 `/opencli ...` 前缀；`/opencli` 是微信直通命令。
- 自动化运行时应通过 shell 直接调用 OpenCLI 二进制。
- 优先 OpenCLI 路径：`/Users/sophienie/Library/Application Support/CodexWeixinBridge/node_modules/.bin/opencli`
- 回退 OpenCLI 路径：`/Users/sophienie/Documents/Codex/2026-05-16/https-mp-weixin-qq-com-s/tools/node/bin/node /Users/sophienie/Documents/Codex/2026-05-16/https-mp-weixin-qq-com-s/tools/opencli-global/lib/node_modules/@jackwener/opencli/dist/src/main.js`

先串行做 OpenCLI 预检和恢复，不要把第一批 OpenCLI 命令并行启动：

```bash
OPENCLI="/Users/sophienie/Library/Application Support/CodexWeixinBridge/node_modules/.bin/opencli"
"$OPENCLI" daemon status || true
"$OPENCLI" doctor || {
  "$OPENCLI" daemon restart || true
  sleep 3
  "$OPENCLI" doctor
}
```

如果 doctor 仍显示 daemon、Chrome extension 或 profile 未连接，再检查：

```bash
lsof -nP -iTCP:19825 -sTCP:LISTEN || true
curl -sS -H 'X-OpenCLI: 1' http://127.0.0.1:19825/status || true
```

用这组检查区分三种情况：

1. daemon 真没启动；
2. Chrome 扩展或 profile 未连接；
3. 自动化运行环境无法访问本机 OpenCLI daemon。

如果 `lsof` 能看到 `127.0.0.1:19825` 有 `node` 监听，但自动化环境里的 `curl`、`doctor` 或 `search` 仍失败，应优先表述为“当前自动化沙箱无法访问本机 OpenCLI daemon”，不要写成“OpenCLI 安装损坏”“小红书登录态失效”或“Chrome 扩展未安装”。这种情况下不要反复重启 daemon；直接降级检索，并在渠道说明中标注这是自动化运行环境限制，后续可由普通本地线程补抓登录态结果。

`Could not create symlink ...`、`EPERM`、`EEXIST` 这类 OpenCLI 用户目录 shim 警告通常不是失败根因，除非后续 doctor/search 同时失败。日报中可以记录它，但不要把它当成唯一诊断结论。

只有 OpenCLI 明确失败、无适配器、遇到登录墙/验证码/反爬，或自动化沙箱无法访问 daemon 时，才用普通网页搜索补充，并在日报里标注降级。不要假装小红书、公众号、点评或 X/Twitter 登录态数据已获取。

## 检索命令配方

1. 小红书：对每个关键词运行 `$OPENCLI xiaohongshu search "关键词" --limit 20 --window background -f json`。查小红书必须用 `xiaohongshu`，不要用 `rednote`，除非明确检索 `www.rednote.com`。对高相关、高互动或机构线索明确的笔记，再运行 `$OPENCLI xiaohongshu note "笔记URL" --window background -f json` 抽取正文、互动和链接。
2. 微信公众号/公开微信文章：运行 `$OPENCLI weixin search "关键词" --limit 10 --window background -f json`。对高相关文章链接，再运行 `$OPENCLI weixin download --url "文章URL" --window background -f json`。必要时读取保存的 Markdown 正文。
3. 大众点评/本地生活机构：运行 `$OPENCLI dianping search "关键词" --city 上海 --limit 15 --window background -f json`。对高相关店铺，再运行 `$OPENCLI dianping shop <shop_id> --window background -f json`。
4. X/Twitter 或境外公开讨论：检索时使用英文查询组合，例如 `AI education for teens`、`AI literacy for students`、`financial literacy for kids`、`kids entrepreneurship camp`、`young founders camp`、`project-based English learning`、`AI and financial literacy for children`、`future skills for kids`、`business camp for children`、`English presentation for kids`、`Shanghai AI education teens`。X/Twitter 只作为趋势补充，最终必须翻译和总结成中文。
5. 机构官网、招生页、新闻稿和其他网页：优先使用 OpenCLI 站点适配器；没有专用适配器时用 `$OPENCLI web read --url "页面URL" --stdout true --window background -f md` 或普通网页搜索补充，并注明来源。

## 调研范围

必须覆盖以下 5 条主线：

1. 上海青少年 AI 教育、AIGC 课程、编程课、科创教育、STEAM、机器人、双语科创；
2. 上海幼儿/少儿英语机构及其转型方向，尤其关注英孚、瑞思、昂立、A+、贝乐、爱贝等品牌是否从纯英语扩展到综合素养、AI/科创、财商、项目制、营地、双语表达；
3. 与 `AI + 财商 + 英语表达力` 相关的公开课程、体验营、半日营、五日营、工作坊、夏令营、项目营；
4. 家长真实关注点、转化话术、价格/课时/校区、试听与营地产品结构；
5. 市场上尚未被头部机构清晰占据的产品白地。

中文关键词建议至少覆盖：

- `上海 青少年 AI 教育`
- `上海 少儿AI 课程`
- `上海 AIGC 课程 青少年`
- `上海 人工智能教育 机构`
- `上海 少儿编程 AI`
- `上海 科创教育 AI课程`
- `上海 编程课 AI 项目制`
- `上海 AI夏令营 青少年`
- `上海 AI竞赛 课程`
- `上海 幼儿英语 机构`
- `上海 少儿英语 转型`
- `上海 少儿英语 AI`
- `上海 少儿英语 财商`
- `上海 双语科创`
- `上海 儿童 财商 营`
- `上海 体验营 英语 表达`
- `上海 AI 财商 英语`
- `上海 夏令营 商业 表达`
- `上海 小小CEO 营`
- `英孚 科创启蒙 上海`
- `瑞思 财商课 上海`
- `昂立 AI 科创营`
- `A+ 少儿英语 项目制`
- 已发现机构名 + `AI` / `AIGC` / `人工智能` / `财商` / `体验营` / `夏令营` / `英语表达` / `校区` / `试听`

## 整理要求

- 同一机构如果来自多个渠道，应合并为一个机构条目；
- 同一卖点如果多家机构都在用，应归为高频卖点；
- 同一产品必须尽量判断它是主产品、辅助产品、短期营、体验课，还是引流活动；
- 只有单一笔记或单一宣传页提到的信息要标注“单源线索”；
- 对任何 `AI + 财商 + 英语表达` 相关案例，优先详细展开；
- 如果某天公开信息不足，不要硬凑，可以明确写“今天公开新增不多，但以下是对我方仍有价值的判断”。

## 日报格式

标题包含日期：`上海青少年AI教育情报 YYYY-MM-DD`

报告正文必须全中文。英文来源内容必须翻译、归纳成中文表达。除必要的机构名、产品名、模型名、账号名、URL、英文课程名或搜索关键词外，不要保留英文段落。

正文依次包含：

1. `今日结论`：3-5 条，优先写新增变化和产品判断；
2. `英语机构转型观察`；
3. `机构与课程表`，字段包括：机构/品牌、渠道来源、产品类型、主打卖点、教学内容、年龄段/班型、价格/课时/校区、证据链接；
4. `AI+财商+英语表达专项观察`；
5. `高频卖点/内容趋势`；
6. `新增线索`；
7. `对樱桃图书馆/登顶升学的启发`；
8. `今日可测试动作`；
9. `X/Twitter英文趋势观察`；
10. `渠道覆盖与失败说明`。

`对樱桃图书馆/登顶升学的启发` 必须明确回答：

1. 今天市场上最值得借鉴的 1-2 个动作是什么；
2. 今天市场上最不该跟的 1 个方向是什么；
3. 对 `AI时代小小CEO体验日` 有什么启发；
4. 对 `AI时代小小CEO五日营` 有什么启发；
5. 对长期班/高客单家庭方案有什么启发。

`今日可测试动作` 必须给出：

1. 1 条可测试的朋友圈/海报话术；
2. 1 个适合半日营的主题；
3. 1 个适合五日营的主题；
4. 1 个值得跟踪的竞争对手动作。

## 归档要求

- 将最终日报正文保存到本项目 `reports/shanghai-youth-ai-edu-daily-YYYY-MM-DD.md`。
- 同步更新本项目 `shanghai-youth-ai-edu-daily.md` 为当天最新版本。
- 运行 `python3 scripts/generate_daily_site.py`，生成并刷新本项目网页日报站。
- 站点至少要更新以下产物：
  - `index.html`
  - `daily/YYYY-MM-DD.html`
  - `site-data/reports.json`
  - `assets/site.css`
- 所有链接尽量保留原始来源 URL；不要泛泛而谈，不要用不可验证内容补足。

## 网页输出要求

完成日报正文后，不再通过微信发送整篇日报，改为把同一份日报输出到网页站点。网页站点需要满足：

1. 首页 `index.html` 展示：
   - 最新日报摘要；
   - 明显的“趋势/判断”区块，用来横向汇总最近几天核心结论；
   - 历史归档列表，点击进入每日报详情页。
2. 每天生成一个独立详情页：`daily/YYYY-MM-DD.html`。
3. 视觉方向保持“偏苹果官网的克制排版 + 暖灰玻璃感背景”，不要做成后台仪表盘或纯白文档页。
4. 详情页必须完整保留当日正文的核心章节、来源链接和清晰阅读结构。

生成站点后，必须执行基础校验。至少确认：

1. `index.html` 已更新；
2. 当天 `daily/YYYY-MM-DD.html` 已生成；
3. `site-data/reports.json` 已更新；
4. 首页能看到当天摘要、趋势/判断区块和历史归档入口；
5. 不再把微信发送成功作为自动化完成条件。
