# 🔧 gnhf

> 一个 ralph/autoresearch 风格的编排工具，让代码代理在你睡觉时自主循环跑，每轮迭代提交一次小的、有文档记录的 git 变更。

🌐 **仓库**：[kunchenguid/gnhf](https://github.com/kunchenguid/gnhf)

---

## 核心功能

- **自主循环**：持续运行到设定的迭代次数或 token 上限，每次成功迭代自动 commit，失败回滚
- **多代理支持**：兼容 Claude Code、Codex、Rovo Dev、OpenCode、GitHub Copilot CLI，可通过 ACP 接入其他代理
- **工作树模式**：用 git worktree 让多个代理并发工作在同一仓库

## 技术栈

TypeScript / Node.js · pnpm · tsdown · vitest

## 待调研

- 实际跑一轮，看夜间无人值守的稳定性和成本
- 与 Claude Code 的配合方式
