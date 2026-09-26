# Codex 双测监控站（codex-dual-probe）

每 30 分钟通过 Codex CLI（模型 `gpt-6-astra`，思考强度 medium）跑两个固定测试，并在静态网页上展示结果。

## 两个测试

1. **逻辑答题 · 糖果题**：预期答案 21。判定方式：取模型回复末行「答案：<数字>」与 21 比对，不在全文里搜数字。
2. **HTML 生成 · 鹈鹕骑行**：让模型生成「SVG 绘制皮卡丘开飞机的 2D 动画」的 HTML。判定方式：返回可渲染 HTML 即记为已生成，不对画面质量打分。

## 网页（site/index.html）

线上地址：<https://haoshendong.github.io/codex-dual-probe/>（GitHub Pages，仓库根路径自动跳转到 `site/`）。每轮测试完成后 `run.sh` 自动提交 `data/` 和 `previews/` 并推送，Pages 随之更新。

- **24 小时检测 Timeline**：测试一最近 24 小时每轮的通过/未通过状态，并统计通过率。
- **3×6 动画预览**：测试二生成的 HTML 以 iframe 嵌入展示，每页 3 行 × 6 列共 18 个，支持分页。
- 直接用浏览器打开 `site/index.html` 即可（数据经 `data/data.js` 以 script 方式加载，file:// 协议可用）；也可以在仓库根目录跑 `python3 -m http.server 8000` 后访问 `http://localhost:8000/site/`。
- 页面每 5 分钟自动刷新一次。

## 目录

```
prompts/    两个测试的题目原文
runner/     run_tests.py：调用 Codex、判定、写数据
run.sh      cron 入口（flock 防重叠）
data/       results.json 全量历史 + data.js 网页数据源
previews/   测试二生成的 HTML 文件
logs/       每轮模型原始回复、运行日志、锁文件
site/       静态网页
```

## 定时任务

crontab 条目（每 30 分钟一轮）：

```
*/30 * * * * /home/dhs/home/codex-dual-probe/run.sh >> /home/dhs/home/codex-dual-probe/logs/cron.log 2>&1
```

手动跑一轮：`./run.sh`
