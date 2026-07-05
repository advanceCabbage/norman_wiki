# 🔧 Claude Code 使用技巧

> 汇总 Claude Code 的快捷键、命令、权限设置与实用小技巧。

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Shift + Tab` | 切换自动模式 / 计划模式（只讨论不修改） |
| `Control + G` | 打开 VSCode 编辑器，关闭后内容回写到 Claude Code |
| `Control + B` | 将启动的网页服务放到后台，不阻塞 Claude Code 执行 |
| 双击 `Esc` | 进入回滚页面，支持回滚会话 + 代码 |

> ⚠️ 回滚仅支持 Claude Code 写入的文件，bash 命令创建的内容（如 `mkdir`、`npm install`）不可回滚。

---

## 💬 常用命令


| 命令          | 功能                          |
| ----------- | --------------------------- |
| `!` 前缀      | 在 Claude Code 中直接输入 bash 命令 |
| `/tasks`    | 查看后台运行的任务                   |
| `/resume`   | 回到历史对话，选择节点继续               |
| `claude -c` | 等价于 `/resume` 选择第一个历史对话节点   |
| `/mcp`      | 查看已安装的 MCP 工具               |
| `/compact`  | 压缩历史对话上下文，可附加压缩方向说明         |
| `/clear`    | 清空上下文                       |
| `/init`     | 生成当前项目的 `CLAUDE.md` 总结文件    |
| `/memory`   | 查看记忆（项目维度 + 全局用户维度）         |
| `/hooks`    | 配置钩子（如工具使用前触发）              |
| `/agents`   | 创建 subAgent                 |
| `/plugin`   | 安装插件                        |

> `Control + O` 可查看 `/compact` 压缩后的最终结果。

---

## 🔐 权限设置

```bash
claude --enable-auto-mode
```

Claude Code 全自动执行模式，无需询问任何权限。

---

## 📋 使用技巧

### /init — 自动生成项目说明

生成 `CLAUDE.md`，存放每次需要 Claude Code 自动加载的上下文信息。

### /memory — 持久记忆

支持两个维度的记忆：**当前项目**维度和**全局用户**维度。
