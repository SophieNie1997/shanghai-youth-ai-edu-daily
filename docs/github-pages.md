# GitHub Pages 发布说明

这个项目已经准备为 GitHub Pages 静态站发布。

## 本地构建

```bash
python3 -m unittest discover -s tests -v
python3 scripts/generate_daily_site.py
```

## 首次发布

1. 在 GitHub 创建一个空仓库，建议仓库名为 `shanghai-youth-ai-edu-daily`。
2. 回到本地项目目录，添加远端并推送：

```bash
git remote add origin https://github.com/<your-user>/shanghai-youth-ai-edu-daily.git
git push -u origin main
```

3. 在 GitHub 仓库页面进入 `Settings` -> `Pages`。
4. 将 `Build and deployment` 的 `Source` 设置为 `GitHub Actions`。
5. 打开 `Actions` 页面，等待 `Deploy GitHub Pages` workflow 成功。

成功后，GitHub Pages URL 通常是：

```text
https://<your-user>.github.io/shanghai-youth-ai-edu-daily/
```

## 每日更新

自动化每天更新 Markdown 和网页产物后，提交并推送到 `main`。GitHub Actions 会自动重新部署网站。
