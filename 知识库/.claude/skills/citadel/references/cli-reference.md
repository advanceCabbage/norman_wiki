# CLI 命令参考

完整参数说明，基于 `src/citadel/cli.ts` 实际实现。

## 通用选项

| 选项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `--mis <mis>` | string | 从配置文件读取 | 用户 MIS 号，用于认证 |
| `--raw` | flag | false | 输出原始 JSON 到 stdout（默认输出人类可读格式到 stderr） |
| `--clear-cache` | flag | — | 清除认证缓存后退出，不需要指定命令 |

## getMarkdown

获取文档 Markdown 内容。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel getMarkdown --contentId "2748397739"
```

**输出**：非 raw 模式下，文档标题/ID/长度输出到 stderr，Markdown 正文输出到 stdout。

## getDocumentJson

获取文档的底层 JSON 内容。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel getDocumentJson --contentId "1234567890"
```

**输出**：非 raw 模式下，文档标题/ID/长度输出到 stderr，JSON 正文输出到 stdout。
## getTemplateMarkdown

获取模板内容（Markdown 格式）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--templateId` | string | ✅ | — | 模板 ID |

```bash
oa-skills citadel getTemplateMarkdown --templateId "2751442505"
```

**输出**：非 raw 模式下，模板ID输出到 stderr，Markdown 内容输出到 stdout。

## getChildContent

获取子文档列表。自动查询文档所属 spaceId。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 父文档 ID |

```bash
oa-skills citadel getChildContent --contentId "2748397739"
```

**输出**：父文档标题、子文档列表（标题、ID、文档链接、类型、创建人、创建/修改时间、是否有子文档）。

## createDocument

创建学城文档。支持四种模式：直接内容、从文件读取、从模板创建、复制文档。

| 参数　　　　　 | 类型　 | 必填 | 默认值 | 说明　　　　　　　　　　　　　　　　　　　　　　　 |
| ----------------| --------| ------| --------| ----------------------------------------------------|
| `--title`　　　| string | ✅　　| —　　　| 文档标题　　　　　　　　　　　　　　　　　　　　　 |
| `--content`　　| string | 条件 | —　　　| Markdown 正文内容　　　　　　　　　　　　　　　　　|
| `--file`　　　 | string | 条件 | —　　　| 从本地文件读取 Markdown 内容（优先于 `--content`） |
| `--templateId` | string | 条件 | —　　　| 从模板创建文档　　　　　　　　　　　　　　　　　　 |
| `--copyFrom`　 | string | 条件 | —　　　| 复制来源文档的 contentId　　　　　　　　　　　　　 |
| `--parentId`　 | string | —　　| —　　　| 父文档 ID（创建子文档时使用）　　　　　　　　　　　|
| `--spaceId`　　| string | —　　| —　　　| 目标空间 ID（不指定则使用个人空间）　　　　　　　　|

> `--content` / `--file` / `--templateId` / `--copyFrom` 至少提供一个。`--file` 优先级最高，会覆盖 `--content`。
>
> 模板来源是 `km.sankuai.com/collabpage/<id>` / `km.sankuai.com/page/<id>`（尤其学城文档2.0）时，优先使用 `--copyFrom <id>`，不要先 `getMarkdown` 后再通过 `--content` 重建。

```bash
# 根文档
oa-skills citadel createDocument --title "方案" --content "# 正文"

# 子文档
oa-skills citadel createDocument --title "子文档" --content "# 内容" --parentId "2748397739"

# 从文件
oa-skills citadel createDocument --title "文档" --file ./design.md

# 指定空间
oa-skills citadel createDocument --title "文档" --content "# 正文" --spaceId "2506"

# 从模板
oa-skills citadel createDocument --title "周报" --templateId "template_123"

# 复制
oa-skills citadel createDocument --title "副本" --copyFrom "1234567890"

# 在目录下复制模板（推荐，保留 2.0 结构）
oa-skills citadel createDocument --title "测试文档" --copyFrom "2750769923" --parentId "2751336167"
```

**输出**：创建成功后一定要返回文档 ID 和文档链接，链接的拼接方式是`https://km.sankuai.com/collabpage/{pageId}`。

## updateDocumentByMd

> ⚠️ **编辑文档内容的唯一安全入口。禁止直接使用 `updateDocument`。**
>
> 学城文档底层是 ProseMirror JSON 结构，直接用 Markdown 覆盖会丢失自定义宏（合并表格、卡片、颜色、折叠块等）。必须先获取文档的 CitadelMD 格式，修改后再回传，完整流程见 [doc-update.md](doc-update.md)。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `--contentId` | string | ✅ | 文档 ID |
| `--file` | string | 条件 | 从本地 `.citadelmd` 文件读取内容（优先于 `--content`） |
| `--content` | string | 条件 | CitadelMD 格式的文档内容字符串 |
| `--title` | string | — | 同时更新文档标题（可选） |

> `--file` 或 `--content` 至少提供一个。

```bash
# 第一步：获取文档 CitadelMD 内容
oa-skills citadel getDocumentCitadelMd --contentId "1234567890" --output doc.citadelmd

# 第二步：编辑 doc.citadelmd 文件（由 AI 修改内容）

# 第三步：回传更新
oa-skills citadel updateDocumentByMd --contentId "1234567890" --file doc.citadelmd

# 同时更新标题
oa-skills citadel updateDocumentByMd --contentId "1234567890" --file doc.citadelmd --title "新标题"
```

**输出**：更新成功或失败的提示信息，以及文档链接（提醒用户刷新页面查看变更）。

## deleteDocument

删除学城文档。仅文档所有者可以删除文档。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel deleteDocument --contentId "2748397739"
```

**输出**：删除成功或失败的提示信息，并明确告知用户删除了哪些文档，给出文档ID。并提示用户如果想撤销删除，可以跟我说撤销刚才删除的文档

## restoreDocument

撤销删除/恢复已删除的学城文档。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel restoreDocument --contentId "2748397739"
```

**输出**：恢复成功或失败的提示信息，如果撤销删除失败，给出文档ID。

## moveDocument

移动学城文档到新的父文档下。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 要移动的文档 ID |
| `--newParentId` | string | 条件 | — | 目标父文档 ID（移动到空间根目录时可不填） |
| `--newSpaceId` | string | 条件 | — | 目标空间 ID（移动到空间根目录时必填） |

```bash
oa-skills citadel moveDocument --contentId "2751172779" --newParentId "1440571964"
oa-skills citadel moveDocument --contentId "2751172779" --newSpaceId "23583"
```

**输出**：移动成功或失败的提示信息。并明确告知用户移动了哪些文档，给出文档ID。并提示用户如果想撤销移动，可以跟我说撤销刚才移动的文档

## getLatestEdit

获取最近编辑的文档列表。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--offset` | number | — | 0 | 偏移量（从 0 开始） |
| `--limit` | number | — | 30 | 每页数量 |
| `--creator` | string | — | "" | 按创建者 MIS 过滤（空字符串表示当前用户） |

```bash
oa-skills citadel getLatestEdit
oa-skills citadel getLatestEdit --limit 10 --creator "zhangsan"
```

**输出**：文档标题、pageId、文档链接、文档类型（在线 WIKI/在线文档/学城文档2.0/多维表格）、修改时间、修改人。

## getRecentlyViewed

获取最近浏览的文档列表。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--pageNo` | number | — | 1 | 页码（从 1 开始） |
| `--pageSize` | number | — | 30 | 每页数量 |
| `--creator` | string | — | "" | 按创建者 MIS 过滤（空字符串表示当前用户） |

```bash
oa-skills citadel getRecentlyViewed
oa-skills citadel getRecentlyViewed --pageSize 10 --pageNo 2
```

**输出**：文档标题、pageId、文档链接、文档类型、浏览时间、作者。

> 注意：此命令用 `--pageNo`（从 1 开始），与其他命令的 `--offset`（从 0 开始）不同。

## getReceivedDocs

获取最近收到的文档列表（通过大象分享收到的）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--offset` | number | — | 0 | 偏移量（从 0 开始） |
| `--limit` | number | — | 30 | 每页数量 |

```bash
oa-skills citadel getReceivedDocs
oa-skills citadel getReceivedDocs --limit 10 --offset 30
```

**输出**：文档标题、contentId、文档链接、发送人、会话名（大象群名/个人名）、收到时间。

## getDiscussionComments

获取文档划词评论（讨论列表）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |
| `--pageNo` | number | — | 1 | 页码（从 1 开始） |
| `--pageSize` | number | — | 100 | 每页评论数 |

```bash
oa-skills citadel getDiscussionComments --contentId "2746799101"
oa-skills citadel getDiscussionComments --contentId "2746799101" --pageNo 1 --pageSize 50
```

**输出**：每条评论的 commentId、创建人、引用文本、评论内容（原始 JSON doc 格式）、时间、解决状态、回复列表。

## getFullTextComments

获取文档全文评论。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |
| `--offset` | number | — | 0 | 偏移量（从 0 开始） |
| `--limit` | number | — | 10 | 每页评论数 |

```bash
oa-skills citadel getFullTextComments --contentId "2746799101"
oa-skills citadel getFullTextComments --contentId "2746799101" --offset 10 --limit 20
```

**输出**：每条评论的 commentId、创建人、评论内容（纯文本）、时间、回复列表。

## getAllComments

获取文档的所有评论（包含划词评论和全文评论）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel getAllComments --contentId "2746799101"
```

**输出**：划词评论列表和全文评论列表。

## getDocumentStats

获取文档的统计信息（浏览量、评论数、创作时长等）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel getDocumentStats --contentId "2746799101"
```

**输出**：关注人数、收藏人数、浏览人数、浏览次数、评论数量、创作时长。

## getDocumentMetaInfo

获取文档元信息，包括父文档 ID、标题、创建者、所有者、创建时间、最后编辑时间等。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--contentId` | string | ✅ | — | 文档 ID |

```bash
oa-skills citadel getDocumentMetaInfo --contentId "1982700288"
```

**输出**：文档标题、文档ID、创建者、所有者、最后编辑者、创建时间、最后编辑时间、所属空间ID、父文档ID（及父文档链接）。

**父文档权限说明**：若返回的 `parentId` 为 `0`，表示该文档位于空间根目录，或当前用户没有查看父文档的权限，此时无法获取父文档信息，应告知用户无父文档查看权限。

## getSpaceIdByMis

根据 MIS 号获取学城个人空间 ID。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--targetMis` | string | ✅ | — | 目标用户的 MIS 号 |

```bash
oa-skills citadel getSpaceIdByMis --targetMis "misId"
```

**输出**：用户的个人空间 ID。

## getSpaceRootDocs

获取空间根目录文档列表。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `--spaceId` | string | ✅ | — | 空间 ID |

```bash
oa-skills citadel getSpaceRootDocs --spaceId "23583"
```

**输出**：空间根目录文档列表，包含文档标题、文档ID、文档链接、文档类型、创建人以及创建时间。

## listTools

列出可用的 MCP 工具列表。无额外参数。

```bash
oa-skills citadel listTools
```
