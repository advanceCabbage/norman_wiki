# 🧩 Obsidian 插件清单与用法

> 我当前 Obsidian 库已安装并启用的社区插件。换电脑/换终端后，可让 Claude 照本文「给 Claude 的安装指引」一节重新装好，并据「逐个插件用法」上手使用。

---

## 已安装插件总览

| 插件名 | 插件 ID | 版本 | 一句话作用 |
| --- | --- | --- | --- |
| Linter | `obsidian-linter` | 1.32.0 | 自动规范化 Markdown 排版（标题空格、列表符号、中英文空格、清理空行） |
| Easy Typing | `easy-typing-obsidian` | 6.0.8 | 中英文/数字间自动加空格，标点优化，边打边美化 |
| Advanced Tables | `table-editor-obsidian` | 0.23.2 | 表格自动对齐、Tab 跳格、排序、增删行列 |
| Editing Toolbar | `editing-toolbar` | 4.0.8 | 顶部所见即所得格式按钮栏，像 Word |
| Outliner | `obsidian-outliner` | 4.10.2 | 列表/大纲增强，整块缩进、移动 |
| Paste URL into selection | `url-into-selection` | 1.11.4 | 选中文字粘贴链接，自动变 `[文字](url)` |
| Style Settings | `obsidian-style-settings` | 1.0.9 | 可视化调主题字体、间距、颜色 |
| Contextual Typography | `obsidian-contextual-typography` | 2.2.5 | 优化阅读模式排版样式 |
| Minimal Theme Settings | `obsidian-minimal-settings` | 8.2.3 | 配合 Minimal 主题做精细排版调整 |

---

## 逐个插件用法

### Linter（排版规范化）⭐
- `⌘ + P` → `Lint current file` 格式化当前笔记
- `⌘ + P` → `Lint all files in vault` 全库格式化（首次慎用，会大量改动旧笔记）
- 设置里可开「保存时自动格式化」（Lint on save）
- 常用规则：标题前后空行、列表统一用 `-`、中英文之间自动空格、清理多余空行

### Easy Typing（中文写作）⭐
- 装好即生效，无需配置：边打字边在中英文/数字间自动补空格
- 设置里可调：标点自动转换、首字母大写、自定义符号配对

### Advanced Tables（表格）
- 手敲两行骨架后自动接管：`| a | b |` + `| - | - |`
- `Tab` 下一格（行尾自动建行）、`⇧+Tab` 上一格、`回车` 下一行
- `⌘ + P` → `Advanced Tables: Open table controls` 调出增删行列/对齐/排序面板

### Editing Toolbar（格式工具栏）
- 编辑时顶部/浮动出现按钮栏，点按即可加粗、标题、颜色、高亮等
- 设置里可自定义按钮、样式（顶部固定 / 跟随光标）

### Outliner（大纲增强）
- `Tab` / `⇧+Tab` 缩进/反缩进整个列表块（含子项）
- `⌘ + ⌥ + ↑/↓` 上下移动整个列表块
- 让多级列表操作像专业大纲工具

### Paste URL into selection（粘贴成链接）
- 选中一段文字 → 直接 `⌘ + V` 粘贴 URL → 自动变成 `[选中文字](url)`

### Style Settings（主题可视化设置）
- `设置 → Style Settings` 出现可视化面板，调字体、行距、颜色等
- 依赖支持该插件的主题（如 Minimal、AnuPpuccin）

### Contextual Typography
- 无需操作，自动给阅读模式套更好的排版样式（标签包裹，便于 CSS 美化）

### Minimal Theme Settings
- 需配合 **Minimal 主题** 使用，`设置 → Minimal Theme Settings` 调列宽、字号、配色等

---

## 给 Claude 的安装指引（换机器后照做）

> 目标：在新机器的 Obsidian 库里还原上面 9 个插件。优先用方式 A，简单可靠。

### 方式 A：Obsidian 内置市场（推荐，让用户点几下）
1. 打开 Obsidian → `设置 → 第三方插件（Community plugins）` → 关闭安全模式
2. 点「浏览（Browse）」，按上表的**插件名**逐个搜索 → Install → Enable
3. 一致性检查：启用列表应与本文「插件 ID」一致

### 方式 B：Claude 自动装（命令行）
社区插件本质是放在 `<库根>/.obsidian/plugins/<插件ID>/` 下的三个文件：`manifest.json`、`main.js`、（可选）`styles.css`。流程：
1. 对每个插件 ID，从其 GitHub Releases 下载最新版的 `manifest.json` / `main.js` / `styles.css`
2. 放进 `.obsidian/plugins/<插件ID>/`
3. 把所有插件 ID 写入 `.obsidian/community-plugins.json`（数组，见下）
4. 重启 Obsidian 生效

各插件 GitHub 仓库：

| 插件 ID | 仓库 |
| --- | --- |
| `obsidian-linter` | platers/obsidian-linter |
| `easy-typing-obsidian` | Yaozhuwa/easy-typing-obsidian |
| `table-editor-obsidian` | tgrosinger/advanced-tables-obsidian |
| `editing-toolbar` | cumany/obsidian-editing-toolbar |
| `obsidian-outliner` | vslinko/obsidian-outliner |
| `url-into-selection` | denolehov/obsidian-url-into-selection |
| `obsidian-style-settings` | mgmeyers/obsidian-style-settings |
| `obsidian-contextual-typography` | mgmeyers/obsidian-contextual-typography |
| `obsidian-minimal-settings` | kepano/obsidian-minimal-settings |

`.obsidian/community-plugins.json` 内容（启用列表）：

```json
[
  "obsidian-linter",
  "easy-typing-obsidian",
  "table-editor-obsidian",
  "editing-toolbar",
  "obsidian-outliner",
  "url-into-selection",
  "obsidian-style-settings",
  "obsidian-contextual-typography",
  "obsidian-minimal-settings"
]
```

### 方式 C：跟着库走（最省事）
若把 `.obsidian/plugins/` 一起提交进 git 仓库，新机器克隆后插件即自带，只需在 Obsidian 里启用即可。

---

*最后更新：2026-06-29*
