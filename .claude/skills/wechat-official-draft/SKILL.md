---
name: wechat-official-draft
description: 微信公众号(WeChat Official Account)完整发文工作流——直连官方 API：读润色规则做 UI 润色(含表格/代码/引用等全套美化)、建草稿+封面、更新草稿、正式发表。用用户自己的 AppID+AppSecret，不经过第三方。当用户要润色/发布/更新/发表公众号文章时使用。
---

# 微信公众号官方发文工作流

直连微信官方接口，用用户自己的 AppID + AppSecret 完成"润色 → 建草稿 → 预览确认 → 发表"闭环。纯 Python 标准库，无需 pip 安装。

> **本 skill 自成一体**：UI 美化（字体/主色/标题/加粗/引用/代码块/图片/**表格斑马纹**）已全部内置在样式引擎里。**不要**再调用 `wechat-article-formatter` 或任何第三方渲染服务（bm.md、limyai 等）。只用本 skill 即可完成整个工作流。

---

## 严格工作流（必须按顺序执行，不要跳步）

触发：用户提供【文章 md 文件】+【封面图】，要求发布/润色公众号。

**第 0 步 · 前置检查（首次或报错时）**
- 确认项目根目录有 `.env`（含 `WECHAT_APPID` / `WECHAT_APPSECRET`）。
- 运行 `python3 $S token`，能打印 access_token 才继续；报 `40164` 见文末错误码处理。

**第 1 步 · 润色（只做 UI/格式，禁止改动观点与事实）**
1. 读取本 skill 目录下的 `polish-rules.md`。
2. 把原文**复制成一份工作副本**（放 scratchpad 或临时目录），**绝不修改用户原始文件**。
3. 按 `polish-rules.md` 的「内容类规则」处理工作副本（如开头关注引导、结尾 CTA、段落拆分、中英文空格等，未开启的规则不加）。
4. 「样式类规则」无需手动做，脚本会自动内联注入。

**第 2 步 · 建草稿**
```bash
python3 $S add --md <工作副本> --title "<标题>" --author "norman" --cover <封面图>
```
- 成功后 media_id 自动写入项目根目录 `.wechat_state.json`。
- 正文里的本地/外链图片会自动上传微信；首个 H1 自动去除。

**第 3 步 · 请用户预览（关键：停在这里等用户）**
- 明确告诉用户：去 **公众号后台 → 内容管理 → 草稿箱 → 打开该草稿 → 预览 → 填写微信号推送到手机**。
- ⚠️ 认证订阅号无法用 API 预览（`message/mass/preview` 报 48001），预览**只能走后台手动这一步**。
- **必须等用户反馈**，不要自作主张继续。

**第 4 步 · 按反馈迭代（可多轮）**
- 用户提 UI 意见 → 修改工作副本或样式 → 更新同一草稿（默认复用上次 media_id 和封面）：
```bash
python3 $S update --md <工作副本> --title "<标题>"
```
- 更新后回到第 3 步，请用户再预览。

**第 5 步 · 确认后发表（必须用户显式确认）**
- 仅当用户明确说"确认发布/发表"时执行；`--yes` 是强制确认位，缺少会被拦下：
```bash
python3 $S publish --yes
```
- 发表为异步，之后可在后台「发表记录」查看。

---

## 前提条件

1. **账号权限**：`draft/add`、`draft/update`、`freepublish/submit` 需已认证的服务号/订阅号。
2. **IP 白名单**：公众号后台 → 开发接口管理 → IP白名单，加入调用方公网 IP。否则报 `40164`。
3. **凭证**：项目根目录 `.env`（参考 `.env.example`）：`WECHAT_APPID` / `WECHAT_APPSECRET`。

## 命令速查

脚本（项目级 skill，从项目根目录运行）：`.claude/skills/wechat-official-draft/scripts/wechat_draft.py`（下称 `$S`）

| 命令 | 说明 |
|---|---|
| `python3 $S token` | 测凭证 + IP 白名单 |
| `python3 $S add --md <f> --title <t> --cover <img> [--author --digest --source-url --open-comment --no-style]` | 新建草稿（首次必填 --cover） |
| `python3 $S update [--media-id <id>] --md <f> --title <t> [--cover <img>]` | 更新草稿（默认取 state 的 id，不传 --cover 复用上次封面） |
| `python3 $S publish [--media-id <id>] --yes` | 正式发表（须 --yes） |
| `python3 $S state` | 查看当前记忆的草稿 |
| `python3 $S preview --media-id <id> --to <微信号>` | 单独推预览（仅服务号可用） |

## 样式引擎（美化，全部内置）

- Markdown→HTML：优先 `markdown` 库，否则内置转换器（标题/加粗/斜体/列表/引用/代码块/链接/图片/**表格**）。
- 内联注入样式（默认开启，`--no-style` 关闭）：绿色主题 `#35b378`、Optima/微软雅黑字体、H2 白字绿底、H3 绿字绿边、加粗变绿、引用绿边浅底、代码块深色、行内代码红字、图片圆角居中、**表格表头绿底+隔行斑马纹**。
- 微信会剥离 `<style>`/class，故样式逐标签内联；全程本地生成，不依赖任何第三方。

## 常见错误码

- `40164`：当前公网 IP 未在白名单 → 后台加入。
- `48001` unauthorized api：账号无该接口权限（订阅号无群发/预览权限属正常）。
- `40007` invalid media_id：草稿 id 失效（多为草稿已被删）→ 重新 add。
- `45004` digest too long：摘要超 120 字节 → 脚本已自动按字节截断，一般不会遇到。
- `40125` invalid appsecret：AppSecret 错误或已重置。
