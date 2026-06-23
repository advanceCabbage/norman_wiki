---
name: citadel
description: "学城官方Skill：学城km/wiki/citadel/km.sankuai.com 自动化操作工具，直接调用线上接口，响应速度更快。支持读取文档信息和内容、获取模板内容、读取文档的目录、查询文档统计信息、总结文档内容、获取文档元信息（父文档ID、标题、创建者、所有者等）、查询当前文档的子文档列表，创建新的学城文档、改文档（插入图片/附件/视频/音频到文档）、删文档、复制学城文档、从模板创建学城文档、移动文档到其他文档下或者指定空间下，并支持查询用户的最近编辑/浏览、收到的文档、以及文档的全文评论和划词评论内容。当用户提到 km.sankuai.com 链接、collabpage、contentId、parentId、pageId、学城、文档、知识库、km、wiki、父文档、创建者、所有者、插入图片到文档、插入附件到文档、插入视频到文档、插入音频到文档时激活。通过 oa-skills citadel CLI 执行。"

metadata:
  skillhub.creator: "rui.zou"
  skillhub.updater: "rui.zou"
  skillhub.version: "V3"
  skillhub.source: "FRIDAY Skillhub"
  skillhub.skill_id: "3367"
  skillhub.high_sensitive: "true"
---

# 学城（km/wiki/citadel/km.sankuai.com）文档操作和管理

通过 CLI 读取学城文档的各种信息和内容、创建学城文档、移动学城文档、查看文档的划词评论，查看最近访问、编辑、收到的学城文档列表。认证自动处理。直接调用线上接口，响应速度更快。

## skill使用问题反馈

如果遇到skill的使用问题，请提[TT|https://tt.sankuai.com/public/create?cid=17&tid=357&iid=46802]进行反馈

## 前置检查：确保 CLI 最新

每次执行命令前，先检查 `@it/oa-skills` 是否为最新版本：

```bash
npm list -g @it/oa-skills --depth=0 --registry=http://r.npm.sankuai.com 2>/dev/null | grep oa-skills
```

如果未安装或版本不是最新，执行更新：

```bash
npm install -g @it/oa-skills@latest --registry=http://r.npm.sankuai.com
```

**此步骤必须在每次 skill 激活时执行一次，否则新命令可能不存在导致运行失败。**

## URL → ID 提取规则

用户给 学城（km） 链接时直接提取，不要追问：

- 文档链接：
  - `km.sankuai.com/collabpage/2748397739` → `--contentId 2748397739`
  - `km.sankuai.com/page/2748397739` → `--contentId 2748397739`
- 模板中心链接（用于从模板创建/读取模板内容）：
  - `km.sankuai.com/template-center/2751442505` → `--templateId 2751442505`
  - `km.sankuai.com/template-center/2751442505?isRelease=1` → `--templateId 2751442505`（忽略 query 参数）
模板链接 `templateId` 提取规则（必须遵守）：

1. 若链接形如 `km.sankuai.com/template-center/<数字ID>`（可带 query/hash），提取 `<数字ID>` 作为 `templateId`。
2. 若用户直接给纯数字字符串，直接作为 `templateId`。
3. 只有在以上规则都无法提取时，才追问 `templateId`。

## 意图路由

### 优先级规则（必须遵守）

1. 用户意图是“创建/新建/生成/复制文档”时，优先走 `createDocument`，不要因为出现 km 链接就先 `getMarkdown`。
2. 在创建意图里，链接只用于提取 ID：
   - 目标目录链接（`collabpage/<id>` / `page/<id>`）→ `--parentId <id>`
   - 模板中心链接（`template-center/<id>`）→ `--templateId <id>`
   - 来源文档链接（`collabpage/<id>` / `page/<id>`）→ `--copyFrom <id>`
3. 用户意图是“查看模板内容”时，执行 `getTemplateMarkdown`，不要走 `getMarkdown`。
4. 只有用户明确要求“阅读/查看/总结文档内容”且目标是文档正文时，才执行 `getMarkdown`。

### 读取学城文档 markdown（仅在阅读/总结意图下）

```bash
getMarkdown --contentId <id>
```

### 获取学城文档底层 JSON 内容

```bash
getDocumentJson --contentId <id>
```

### 获取模板内容

当用户提供模板 ID 或模板中心链接（`template-center/<id>`）并要求查看模板内容时，执行：

```bash
getTemplateMarkdown --templateId <id>
```

示例：

- `https://km.sankuai.com/template-center/2751442505?isRelease=1` → `--templateId 2751442505`
- `getTemplateMarkdown --templateId 2751442505`

### 总结学城文档

执行[references/skill-doc-view.md](references/doc-view.md)文件里的具体步骤，输出总结结果。

### 查看当前学城文档的子文档、文档结构和内容、parentId 下的文档目录

```bash
getChildContent --contentId <id>
```

### 创建/新建学城文档

```bash
createDocument --title <标题> --content <内容>
```

### 创建学城文档的子文档

```bash
createDocument --title <标题> --content <内容> --parentId <id>
```

### 编辑学城文档/更新学城文档内容/插入新内容到学城文档

执行[references/doc-update.md](references/doc-update.md)文件里的具体步骤，进行安全的文档更新，禁止直接操作修改JSON数据以及通过GUI方式进行编辑操作。

**输出**：返回编辑文档的链接，提醒用户需要刷新当前页面才能看到更新内容

### 将 AI 生成的内容（图片、附件）或本地文件（包括视频、音频）插入到学城文档

执行 [references/doc-insert.md](references/doc-insert.md) 文件里的具体步骤，将 AI 生成的图片、本地文件、本地视频或本地音频安全插入到指定学城文档。

- **插入图片**：**严禁直接将非学城图片 URL 插入文档**，必须先调用 `uploadImageToDocument` 上传。
- **插入附件**：**严禁将非学城附件 URL 直接写入 CitadelMD**，必须先调用 `uploadAttachmentToDocument` 上传（仅限 PDF/Word/Excel/ZIP 等非媒体文件，**视频和音频禁止用此命令**）。
- **插入视频**：**严禁将非学城视频 URL 直接写入 CitadelMD**，必须先调用 `uploadVideoToDocument` 上传。
- **插入音频**：**严禁将非学城音频 URL 直接写入 CitadelMD**，必须先调用 `uploadAudioToDocument` 上传。

**输出**：返回文档链接，提醒用户刷新页面查看插入的内容（图片/附件/视频/音频）。

### 从模板创建学城文档

当用户给的是模板中心链接（`km.sankuai.com/template-center/<id>`）时，按上面的规则提取 `templateId`（忽略 query 参数），然后执行：

```bash
createDocument --title <标题> --templateId <id>
```

示例：

- `https://km.sankuai.com/template-center/2751442505` → `--templateId 2751442505`
- `https://km.sankuai.com/template-center/2751442505?isRelease=1` → `--templateId 2751442505`

### 复制学城文档

```bash
createDocument --title <标题> --copyFrom <id>
```

### 在指定目录下复制模板创建文档（2.0 文档优先）

当用户说“先复制模板再填充内容”“按模板生成”等，并且模板给的是 `km.sankuai.com/collabpage/<id>` / `km.sankuai.com/page/<id>` 链接（尤其学城文档2.0）时，默认使用复制命令，不要先读取模板内容再重建：

```bash
createDocument --title <标题> --copyFrom <模板id> --parentId <目录id>
```

示例（对应用户输入）：

- 目录：`https://km.sankuai.com/collabpage/2751336167` → `--parentId 2751336167`
- 模板：`https://km.sankuai.com/collabpage/2750769923` → `--copyFrom 2750769923`
- 命令：`createDocument --title "测试文档" --copyFrom 2750769923 --parentId 2751336167`

### 删除学城文档

```bash
deleteDocument --contentId <id>
```

### 撤销删除/恢复已删除的学城文档

```bash
restoreDocument --contentId <id>
```

### 移动学城文档

```bash
# 移动到其他文档下
moveDocument --contentId <id> --newParentId <id>
# 移动到空间根目录
moveDocument --contentId <id> --newSpaceId <id>
```

### 获取/查看用户（mis）最近编辑了什么文档

```bash
getLatestEdit --limit 10
```

### 获取/查看用户（mis）最近浏览了什么文档

```bash
getRecentlyViewed --pageSize 10
```

### 获取/查看用户（mis）别人发的/收到的学城文档

```bash
getReceivedDocs --limit 10
```

### 获取学城文档的划词评论

```bash
getDiscussionComments --contentId <id>
```

### 获取学城文档的全文评论

```bash
getFullTextComments --contentId <id>
```

### 获取学城文档的所有评论（划词评论 + 全文评论）

```bash
getAllComments --contentId <id>
```

### 获取文档的统计信息（浏览量、评论数、创作时长等）

```bash
getDocumentStats --contentId <id>
```

### 获取文档元信息（父文档ID、标题、创建者、所有者、创建/编辑时间等）

```bash
getDocumentMetaInfo --contentId <id>
```

**说明**：返回文档的父文档 ID（`parentId`）、标题（`title`）、创建者（`creator`）、文档所有者（`owner`）、最后编辑者（`modifier`）、创建时间（`createTime`）、最后编辑时间（`modifyTime`）等。若 `parentId` 为 0，表示该文档位于空间根目录或当前用户无父文档查看权限。

### 根据 MIS 号获取学城个人空间 ID

```bash
getSpaceIdByMis --targetMis <mis>
```

### 获取空间根目录文档列表

```bash
getSpaceRootDocs --spaceId <id>
```

### 列出可用工具

```bash
listTools
```

## CLI 速查

所有命令格式：`oa-skills citadel <command> [options]`

通用选项：`--mis <mis>` 指定用户，`--raw` 输出 JSON 到 stdout，`--clear-cache` 清除认证缓存，`--force-ciba` 强制 CIBA 认证（跳过已有认证请求判断）。

### `getMarkdown`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getDocumentJson`

**必填参数**: `--contentId <id>`

### `getTemplateMarkdown`

**必填参数**: `--templateId <id>`
**可选参数**: 无

### `getChildContent`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `createDocument`

**必填参数**: `--title <标题>` + 内容源
**可选参数**: `--parentId <id>` `--spaceId <id>`

### `updateDocumentByMd`（编辑文档的唯一安全入口）

> ⚠️ **禁止直接调用 `updateDocument`**，所有文档内容编辑必须通过 `updateDocumentByMd` 完成。
> 完整流程见 [references/doc-update.md](references/doc-update.md)。

**必填参数**: `--contentId <id>` + `--file <citadelmd文件>` 或 `--content <citadelmd内容>`
**可选参数**: `--title <标题>`

### `uploadImageToDocument`

**必填参数**: `--contentId <id>` + `--image <路径或url>`
**可选参数**: `--alt <图片描述>`

> 上传图片到目标文档，返回学城图片 URL 和 CitadelMD 图片语法片段（`imageMd`）。
> `--image` 支持远程 URL（http/https）或本地文件路径（绝对/相对路径）。
> 后续由 AI 将 `imageMd` 插入文档 CitadelMD 内容，再通过 `updateDocumentByMd` 回传。
> 严禁将非学城链接直接插入文档。

### `uploadAttachmentToDocument`

**必填参数**: `--contentId <id>` + `--file <本地文件路径>`

> 上传本地**非媒体文件**（PDF、Word、Excel、ZIP 等）作为附件到目标文档，返回学城附件 URL 和 CitadelMD 附件语法片段（`attachmentMd`）。
> 后续由 AI 将 `attachmentMd` 插入文档 CitadelMD 内容，再通过 `updateDocumentByMd` 回传。
> 严禁将非学城附件 URL 直接插入文档。
> ⚠️ **禁止将视频（mp4/mov/avi 等）或音频（mp3/wav/aac/m4a 等）文件通过此命令上传**；视频必须使用 `uploadVideoToDocument`，音频必须使用 `uploadAudioToDocument`。使用此命令上传媒体文件将导致 URL 无法正确转换为 CDN 格式。

### `uploadVideoToDocument`

**必填参数**: `--contentId <id>` + `--file <本地视频文件路径>`
**可选参数**: `--size <文件字节数>`（AI 应先通过系统工具获取文件大小后传入，用于生成含 `size` 属性的 `videoMd`）

> 上传本地视频文件到目标文档，自动将原始 URL 转换为 CDN URL（`/api/file/cdn/<contentId>/<attachmentId>?contentType=video`），返回 CDN 视频 URL、attachmentId、jobId、size 和 CitadelMD 视频语法片段（`videoMd`）。
> 后续由 AI 将 `videoMd` 插入文档 CitadelMD 内容，再通过 `updateDocumentByMd` 回传。
> 严禁将非学城视频 URL 直接插入文档。视频上传后会触发转码，`jobId` 为转码任务 ID。

### `uploadAudioToDocument`

**必填参数**: `--contentId <id>` + `--file <本地音频文件路径>`
**可选参数**: `--size <文件字节数>`（AI 应先通过系统工具获取文件大小后传入，用于生成含 `size` 属性的 `audioMd`）

> 上传本地音频文件到目标文档，自动将原始 URL 转换为 CDN URL（`/api/file/cdn/<contentId>/<attachmentId>?contentType=audio`），返回 CDN 音频 URL、attachmentId、jobId、size 和 CitadelMD 音频语法片段（`audioMd`）。
> 后续由 AI 将 `audioMd` 插入文档 CitadelMD 内容，再通过 `updateDocumentByMd` 回传。
> 严禁将非学城音频 URL 直接插入文档。

### `deleteDocument`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `restoreDocument`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `moveDocument`

**必填参数**: `--contentId <id>`，以及 `--newParentId <id>` 或 `--newSpaceId <id>` 之一
**可选参数**: 无

### `getLatestEdit`

**必填参数**: 无
**可选参数**: `--offset 0` `--limit 30` `--creator <mis>`

### `getRecentlyViewed`

**必填参数**: 无
**可选参数**: `--pageNo 1` `--pageSize 30` `--creator <mis>`

### `getReceivedDocs`

**必填参数**: 无
**可选参数**: `--offset 0` `--limit 30`

### `getDiscussionComments`

**必填参数**: `--contentId <id>`
**可选参数**: `--pageNo 1` `--pageSize 100`

### `getFullTextComments`

**必填参数**: `--contentId <id>`
**可选参数**: `--offset 0` `--limit 10`

### `getAllComments`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getDocumentStats`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getDocumentMetaInfo`

**必填参数**: `--contentId <id>`
**可选参数**: 无

### `getSpaceIdByMis`

**必填参数**: `--targetMis <mis>`
**可选参数**: 无

### `getSpaceRootDocs`

**必填参数**: `--spaceId <id>`
**可选参数**: 无

### `listTools`

**必填参数**: 无
**可选参数**: 无

`createDocument` 内容源（至少一个）：`--content <md>` / `--file <path>` / `--templateId <id>` / `--copyFrom <id>`。`--file` 优先级最高。

> ⚠️ **文档内容编辑禁止使用 `updateDocument`**，必须走 `updateDocumentByMd` 安全更新流程，见 [references/doc-update.md](references/doc-update.md)。

> 完整参数说明、示例和输出格式见 [references/cli-reference.md](references/cli-reference.md)

## 约束

- 缺少关键参数时只追问必要字段（contentId / templateId / keyword / title），不给笼统报错
- 用户给了 km 链接时按 URL 规则直接提取 ID（contentId / parentId / templateId / copyFrom）执行，不要反复确认
- **禁止直接调用 `updateDocument` 进行文档内容编辑**；所有编辑操作必须走 `updateDocumentByMd` 流程（先 `getDocumentCitadelMd` 获取 → 修改 → `updateDocumentByMd` 回传）
- 在"复制模板/按模板创建"场景，禁止先 `getMarkdown` 再 `createDocument --content`；优先 `--copyFrom`（尤其学城文档2.0）
- 在"查看模板内容"场景，优先 `getTemplateMarkdown`，不要调用 `getMarkdown`
- `getRecentlyViewed` 用 `--pageNo`（从 1 开始），其他命令用 `--offset`（从 0 开始）
- **插入图片到文档时，严禁直接将非学城图片 URL 插入 CitadelMD**；必须先调用 `uploadImageToDocument` 将图片上传到目标文档，再将返回的 `imageMd`（学城图片 CitadelMD 语法）插入文档
- **插入附件到文档时，严禁将非学城附件 URL 直接写入 CitadelMD**；必须先调用 `uploadAttachmentToDocument` 将本地文件上传到目标文档，再将返回的 `attachmentMd`（学城附件 CitadelMD 语法）插入文档。**`uploadAttachmentToDocument` 仅限 PDF、Word、Excel、ZIP 等非媒体文件；视频必须用 `uploadVideoToDocument`，音频必须用 `uploadAudioToDocument`，绝对不可混用**
- **插入视频到文档时，严禁将非学城视频 URL 直接写入 CitadelMD**；必须先调用 `uploadVideoToDocument` 将本地视频上传到目标文档，再将返回的 `videoMd`（学城视频 CitadelMD 语法）插入文档
- **插入音频到文档时，严禁将非学城音频 URL 直接写入 CitadelMD**；必须先调用 `uploadAudioToDocument` 将本地音频上传到目标文档，再将返回的 `audioMd`（学城音频 CitadelMD 语法）插入文档

## 暂不支持

以下能力当前 **不可用**，不要伪造执行结果：

- 多维表格创建和读写

用户要求时明确说明"当前暂不支持"。

- 若用户要求“复制后再填充内容”，先按 `--copyFrom` 创建，再说明当前不支持自动编辑已创建文档。
- 替代方案：先用 `getMarkdown` 读取内容，在本地生成修改建议。

## 认证

SSO CIBA 认证，首次调用需用户在大象 App 确认。Token 自动缓存。

- 认证失败 → `oa-skills citadel --clear-cache` 后重试
- 用户说"没法手机确认" → 解释 CIBA 必须手机确认，无法跳过

### 强制认证（--force-ciba）

如果认证请求卡住或需要重新发起认证，可使用 `--force-ciba` 参数跳过"已有活跃认证请求"的判断，强制发起新的 CIBA 认证：

```bash
oa-skills citadel getMarkdown --contentId <id> --force-ciba
```

常见场景：
- 旧的认证请求一直未确认导致新请求被阻止
- 需要重新认证获取新的 token

此时系统会提示"强制 CIBA 认证"模式，用户需在大象 App 重新确认授权。

## 验证

执行完成后确认：

1. 命令退出码为 0
2. 读取类：返回了文档内容/列表
3. 创建类：返回了新文档 contentId 和链接
4. 给用户简明结论（标题、ID、数量），而非原始数据
