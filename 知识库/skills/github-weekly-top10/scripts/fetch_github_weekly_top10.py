#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_github_weekly_top10.py

获取 GitHub Trending 周榜（stars this week 最多的仓库），按"本周新增 Star"降序
取 Top N，生成一份 Markdown 报告。

设计原则（与 SKILL.md 配合）：
- 脚本只负责"确定性"的部分：抓取、解析、排序、产出数据表与报告骨架。
- 定性分析（使用场景 / 优点 / 缺点）由 AI 基于仓库详情补全，脚本仅预留占位。

仅依赖 Python 标准库，无需 pip install，任意环境可直接运行。

用法：
    python3 fetch_github_weekly_top10.py                 # 默认写 github_weekly_top10_YYYY-MM-DD.md
    python3 fetch_github_weekly_top10.py --top 20        # 取前 20
    python3 fetch_github_weekly_top10.py --since daily   # daily / weekly / monthly
    python3 fetch_github_weekly_top10.py --output out.md # 指定输出文件
    python3 fetch_github_weekly_top10.py --json data.json# 同时导出结构化 JSON
"""

import argparse
import datetime as _dt
import json
import re
import sys
import urllib.request

TRENDING_URL = "https://github.com/trending?since={since}"

# 伪装成浏览器 UA，避免被 GitHub 直接 403
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# 每个仓库 article 块的字段正则
_RE_ARTICLE = re.compile(r'<article class="Box-row">(.*?)</article>', re.DOTALL)
_RE_REPO = re.compile(r'<h2[^>]*>\s*<a[^>]*href="(/[^"?]+)"', re.DOTALL)
_RE_DESC = re.compile(
    r'class="col-9 color-fg-muted[^"]*">(.*?)</p>', re.DOTALL
)
# 星标数在 <a> 内被 svg 图标隔开，需跳过 svg 再取数字
_RE_TOTAL = re.compile(r'href="[^"]*/stargazers"[^>]*>.*?</svg>\s*([\d,]+)\s*</a>', re.DOTALL)
_RE_LANG = re.compile(r'itemprop="programmingLanguage">([^<]+)<')
_RE_WEEKLY = re.compile(r'([\d,]+)\s+stars this week')


def _clean(text: str) -> str:
    """去换行、收尾空白、解码常见 HTML 实体。"""
    if text is None:
        return ""
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )


def _to_int(s: str) -> int:
    return int(s.replace(",", "").strip() or 0)


def fetch_trending(since: str) -> str:
    url = TRENDING_URL.format(since=since)
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_repos(html: str, top: int):
    repos = []
    for block in _RE_ARTICLE.findall(html):
        m_repo = _RE_REPO.search(block)
        if not m_repo:
            continue
        full = m_repo.group(1).strip("/")
        if full.count("/") != 1:
            continue  # 跳过非 owner/repo 的链接
        owner, name = full.split("/", 1)

        desc = _clean(_RE_DESC.search(block).group(1)) if _RE_DESC.search(block) else ""
        lang = _clean(_RE_LANG.search(block).group(1)) if _RE_LANG.search(block) else ""
        total = _to_int(_RE_TOTAL.search(block).group(1)) if _RE_TOTAL.search(block) else 0
        weekly = _to_int(_RE_WEEKLY.search(block).group(1)) if _RE_WEEKLY.search(block) else 0

        repos.append(
            {
                "rank": 0,
                "full_name": full,
                "owner": owner,
                "name": name,
                "url": f"https://github.com/{full}",
                "description": desc,
                "language": lang,
                "stars_total": total,
                "stars_weekly": weekly,
            }
        )

    # 按本周新增 Star 降序重排序（趋势页原始顺序并非严格按周增量）
    repos.sort(key=lambda r: r["stars_weekly"], reverse=True)
    for i, r in enumerate(repos[:top], 1):
        r["rank"] = i
    return repos[:top]


def build_markdown(repos, since: str, generated_at: str) -> str:
    lines = []
    lines.append("# GitHub 本周 Star 增长 Top 10\n")
    lines.append(f"> 统计窗口：GitHub Trending（since={since}）")
    lines.append(f"> 排序依据：本周新增 Star 数（降序）")
    lines.append(f"> 数据生成时间：{generated_at}")
    lines.append(f"> 数据来源：https://github.com/trending?since={since}\n")

    # 总览表
    lines.append("## 总览表\n")
    lines.append("| 排名 | 仓库 | 链接 | 本周新增 Star | 总 Star | 语言 |")
    lines.append("|------|------|------|--------------:|--------:|------|")
    for r in repos:
        lines.append(
            f"| {r['rank']} | {r['full_name']} "
            f"| {r['url']} | {r['stars_weekly']:,} | {r['stars_total']:,} | {r['language'] or '-'} |"
        )
    lines.append("")

    # 每个仓库：脚本填确定字段，定性分析预留给 AI
    lines.append("## 仓库详细分析\n")
    for r in repos:
        lines.append(f"### {r['rank']}. {r['full_name']} "
                     f"⭐ 本周 +{r['stars_weekly']:,}（累计 {r['stars_total']:,}）")
        lines.append(f"- 语言：{r['language'] or '未知'}")
        lines.append(f"- 链接：{r['url']}")
        lines.append(f"- 描述：{r['description'] or '（无描述）'}")
        lines.append("")
        lines.append("**核心功能**（基于上述描述自动提取，建议由 AI 润色展开）")
        lines.append(f"> {r['description'] or '待补充'}")
        lines.append("")
        lines.append("**使用场景**（待 AI 基于仓库详情补充）")
        lines.append("> 待补充")
        lines.append("")
        lines.append("**优点**（待 AI 基于仓库详情补充）")
        lines.append("> 待补充")
        lines.append("")
        lines.append("**缺点**（待 AI 基于仓库详情补充）")
        lines.append("> 待补充")
        lines.append("")

    lines.append("---")
    lines.append("*说明：本报告由脚本完成数据抓取与排序；「使用场景 / 优点 / 缺点」"
                 "为占位，需由 AI 结合仓库 README 撰写。本周新增 Star 为趋势页近似值，"
                 "会随统计时点波动。*")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Fetch GitHub weekly top-starred repos.")
    ap.add_argument("--top", type=int, default=10, help="取前 N 个（默认 10）")
    ap.add_argument("--since", default="weekly",
                    choices=["daily", "weekly", "monthly"],
                    help="趋势时间窗口（默认 weekly）")
    ap.add_argument("--output", default=None,
                    help="Markdown 输出路径（默认 github_weekly_top10_YYYY-MM-DD.md）")
    ap.add_argument("--json", default=None, help="同时导出结构化 JSON 的路径")
    args = ap.parse_args()

    generated_at = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = _dt.datetime.now().strftime("%Y-%m-%d")

    try:
        html = fetch_trending(args.since)
    except Exception as e:  # noqa: BLE001
        print(f"[错误] 抓取 GitHub Trending 失败：{e}", file=sys.stderr)
        sys.exit(1)

    repos = parse_repos(html, args.top)
    if not repos:
        print("[错误] 未解析到任何仓库，可能 GitHub 页面结构已变化或网络受限。", file=sys.stderr)
        sys.exit(2)

    md = build_markdown(repos, args.since, generated_at)

    out_path = args.output or f"github_weekly_top10_{date_str}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[完成] 已写出 {len(repos)} 个仓库到：{out_path}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(
                {"generated_at": generated_at, "since": args.since, "repos": repos},
                f, ensure_ascii=False, indent=2,
            )
        print(f"[完成] 已导出结构化 JSON 到：{args.json}")

    # 顺便在 stdout 打印 Top 列表，方便管道使用
    print("\n排名 | 仓库 | 本周新增 | 总Star")
    for r in repos:
        print(f"{r['rank']:>2} | {r['full_name']:<40} | {r['stars_weekly']:>6,} | {r['stars_total']:>6,}")


if __name__ == "__main__":
    main()
