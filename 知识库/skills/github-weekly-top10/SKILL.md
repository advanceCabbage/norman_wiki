---
name: github-weekly-top10
description: This skill should be used when the user wants a Chinese Markdown report of the top 10 GitHub repositories ranked by weekly star growth, with detailed core functionality, use cases, pros, and cons for each repo. Trigger phrases include "GitHub 周榜", "本周/上周 star 增长最多", "GitHub trending 周报", "最火的 GitHub 仓库", or any request to track the fastest-rising/hottest GitHub repos on a recurring weekly basis.
agent_created: true
---

# GitHub 周榜 Top 10 报告

## 目的

自动获取 GitHub 近 7 天 Star 数新增最多的 10 个仓库，并生成一份结构化的中文 Markdown 报告。每个仓库都必须包含「核心功能 / 使用场景 / 优点 / 缺点」四个小节，便于快速了解一个新仓库是否值得关注。

## 何时使用

- 用户要求「GitHub 本周/上周 Star 增长 Top 10」「本周最火的 GitHub 仓库」「GitHub 周报」等。
- 用户想周期性追踪 GitHub 上快速走红的仓库。
- 适合配合定时任务（automation），每周自动生成并落盘报告。

## 工作流程

### 1. 获取周榜数据（脚本优先）

推荐直接运行本 skill 附带的脚本 `scripts/fetch_github_weekly_top10.py`（仅依赖 Python 标准库，无需 `pip install`）：

```bash
python3 scripts/fetch_github_weekly_top10.py --output github_weekly_top10_YYYY-MM-DD.md --json data.json
```

脚本会自动完成：抓取 Trending 页面 → 解析仓库名/描述/语言/总 Star/本周新增 Star → **按本周新增 Star 降序取 Top 10** → 生成含总览表与四节占位骨架的 Markdown（核心功能已用官方描述预填，使用场景/优点/缺点留待 AI 补充）→ 同时导出 `data.json` 便于程序化处理。常用参数：`--top N`、`--since daily|weekly|monthly`、`--output 路径`、`--json 路径`。

若脚本因网络受限或 GitHub 页面结构变化而不可用，回退到用 WebFetch 访问 `https://github.com/trending?since=weekly`。该页面每个仓库右侧展示的即为「本周新增 Star 数」（stars this week）。提取前 10+ 个仓库，记录：仓库全名（owner/repo）、仓库链接、官方描述、总 Star 数、本周新增 Star 数、主要编程语言。

### 2. 按周增量重排序（关键）

若走脚本路径，此步已由脚本完成。若走 WebFetch 路径：GitHub Trending 页面原始展示顺序并非严格按本周新增 Star 排序，务必将提取到的仓库**按「本周新增 Star 数」降序重新排序**，再取 Top 10，保证排名真实反映「新增最多」。

### 3. 补充仓库详情

对每个仓库，访问其 GitHub 仓库页面（必要时读取 README 或 About 信息），获取足以撰写核心功能、使用场景、优点、缺点的信息。如描述已足够详细，可直接基于描述与 README 合理概括，不要遗漏任一仓库。

### 4. 生成报告

写入 Markdown 文件，建议文件名 `github_weekly_top10_YYYY-MM-DD.md`（YYYY-MM-DD 取生成当天或所在周日）。

报告结构：

- 一级标题：`GitHub 本周 Star 增长 Top 10`（附生成时间、统计窗口、数据来源说明）
- 总览表：`排名 | 仓库 | 链接 | 本周新增 Star | 总 Star | 语言`
- 每个仓库的详细分析，必须包含以下四节：
  - **核心功能**：2–4 段，说明它是什么、解决什么问题、核心特性与工作机制。
  - **使用场景**：列出 2–4 个典型落地场景（谁、在什么情况下会用）。
  - **优点**：列出 3–5 条主要优势。
  - **缺点**：列出 2–4 条局限或需注意的点（如成熟度、平台限制、成本、隐私等）。

### 5. 交付与摘要

报告写完后，在对话中给出一句话摘要（含文件路径）。若用于定时任务，将文件保存到指定工作目录。

## 注意事项

- 若 trending 页面无法直接抓取，改用 GitHub Search（搜索近期高 Star 增长仓库）或已连接的 github connector 作为补充，但始终以「本周新增 Star 数」为排序依据，取 Top 10 并降序排列。
- 全程保持中文输出，不输出英文报告。
- GitHub Trending 周榜为滚动 7 天窗口，非自然日历周；本周新增 Star 数为趋势页展示的近似值，会随统计时点略有波动。
- 优点/缺点基于公开描述与项目定位做客观分析，避免主观夸大；信息不足时基于描述与 README 合理概括。

## 示例触发语句

- 「帮我生成本周 GitHub Star 增长 Top 10 报告」
- 「找出上周最火的 10 个 GitHub 仓库，每个介绍功能、场景、优缺点」
- 「每周日自动出一份 GitHub 周榜报告」
