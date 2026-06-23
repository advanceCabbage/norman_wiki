# 编辑/更新/插入新内容到学城文档指南

编辑/更新/插入新内容到学城文档是一个高危操作。学城文档的底层数据是基于 ProseMirror 生成的 JSON 结构，其中可能包含大量 Markdown 语法无法描述的特殊定制宏（如：包含合并单元格的表格，表格嵌套表格，特定的卡片、嵌入的第三方组件、文字颜色/背景色/对齐方式、展开卡片等）。

## 强势使用方式：CitadelMD 安全更新（零数据丢失）

**CitadelMD** 是一种基于 ProseMirror JSON 的扩展 Markdown 格式，通过 `:::tag{attrs}` 语法完整编码所有自定义宏节点，**100% 保留文档结构**，不会产生任何数据丢失。

### 完整工作流

#### 第一步：获取文档的 CitadelMD 内容

```bash
# 直接打印到终端
oa-skills citadel getDocumentCitadelMd --contentId <id>

# 保存到文件（推荐，便于编辑）
oa-skills citadel getDocumentCitadelMd --contentId <id> --output doc.citadelmd
```

#### 第二步：修改 CitadelMD 内容

直接编辑 `.citadelmd` 文件，或者由 AI 对内容进行增、删、改操作。

CitadelMD 是学城专用的扩展 Markdown 格式，完整语法如下：

---

### 标准 Markdown（普通内容直接使用）

```
# 一级标题
## 二级标题
### 三级标题（支持 H1-H6）

普通段落文字。连续行会合并为同一段落。

---   （分割线）

> 这是一段引用文字

- 无序列表项 1
- 无序列表项 2

1. 有序列表项 1
2. 有序列表项 2

- [x] 已完成的任务
- [ ] 未完成的任务

​```typescript
const hello = 'world';
console.log(hello);
​```
（代码块支持语言标识，如 python / java / bash / typescript 等）

| 姓名 | 部门 |
| --- | --- |
| 张三 | 研发部 |
（标准表格，无合并单元格）

![图片描述](https://example.com/image.png)
![图片描述](https://example.com/image.png){width=300 height=200 align=center}
（图片可附加尺寸和对齐属性）
```

---

### 文字样式（Marks）

```
**加粗文字**
*斜体文字*
__下划线文字__
~~删除线文字~~
`行内代码`
^上标^
~下标~

:[color]{#ff0000}红色文字[/color]
:[color]{#0066cc}蓝色文字[/color]
:[bg]{#ffff00}黄色背景[/bg]
:[font]{size=20}大号字体[/font]
:[font]{size=12}小号字体[/font]
```

> 颜色值支持十六进制（`#rrggbb`）或 CSS 颜色名。字体大小单位为 px（整数）。

---

### 行内宏节点

```
:[mention]{name="张三" uid="zhangsan" empId="123456"}
（@提及用户，name=显示名、uid=MIS号、empId=工号）

:[time]{date="1742220000000"}
:[time]{date="1742220000000" showTime}
（日期/时间引用，date 传入毫秒时间戳；showTime 表示同时显示具体时间，省略则只显示日期）

:[anchor]{id="section-1"}
（页面锚点，用于内部跳转）

:[status]{pattern="default" color=""}待处理[/status]
:[status]{pattern="success" color="green"}已完成[/status]
:[status]{pattern="warning" color="orange"}进行中[/status]
:[status]{pattern="error" color="red"}已取消[/status]
（状态标签，pattern 取值：default / success / warning / error / fill）

:[emoji]{name="smile"}
:[emoji]{name="thumbsup"}
（表情符号，name 为表情标识符）

$E = mc^2$
（行内 LaTeX 数学公式）

:[link]{href="https://km.sankuai.com" autoUpdate}学城首页[/link]
（自动更新标题的链接，普通链接直接用标准 Markdown：[文字](url)）

:[data2chart]{id="f91521b14fa7d8fe52eb" pageId="2752474861"}
（数据图表行内引用，id 和 pageId 必须保留原值）

:[footnote]{id="96ef140e-f997-4981-a9bb-037d2f0e1d39" annotate=""}
（脚注锚点，id 必须保留原值，annotate 为注释文字）
```

---

### 块级宏节点

#### 段落对齐与缩进（paragraph）

```
:::paragraph{align=right indent=0}
右对齐段落
:::

:::paragraph{align=center indent=0}
居中对齐段落
:::

:::paragraph{align=justify indent=0}
两端对齐段落
:::

:::paragraph{align=left indent=1}
缩进段落（indent 为缩进级别，0=无缩进）
:::
```

> `align` 取值：`left`（左对齐，默认，可省略此块）、`right`（右对齐）、`center`（居中）、`justify`（两端对齐）。

#### 折叠块（collapse）

```
:::collapse{active}
折叠块标题
---
折叠块内容，可以包含任意 Markdown。

支持多段落、列表等。
:::

:::collapse{}
默认折叠（不带 active）
---
点击才能看到的内容
:::
```

> `active` 表示默认展开，去掉则默认折叠。标题和内容之间用 `---` 分隔。

#### 文档标题（title）

```
:::title
文档标题文字
:::
```

> 文档标题块，每篇文档只有一个，位于正文最前面。

#### 提示框（note）

```
:::note{type=info}
信息提示标题
---
这里是提示内容。
:::

:::note{type=warn}
警告标题
---
警告内容。
:::

:::note{type=error}
错误标题
---
错误内容。
:::
```

> `type` 取值：`info`（信息）、`warn`（警告）、`error`（错误）、`note`（默认）。

#### 数学公式块（latex_block）

```
$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$
```

#### PlantUML 图表

```
:::plantuml{width=400 height=300}
@startuml
A -> B : 请求
B -> A : 响应
@enduml
:::
```

#### Drawio 流程图

```
:::drawio{src="https://km.sankuai.com/api/file/cdn/xxx" width=554 height=387}:::
```

> `src` 为图文件地址，必须保留原值。⚠️ 不要手动修改 Drawio 内容。

#### 思维导图（minder）

```
:::minder{src="https://km.sankuai.com/api/file/cdn/xxx" width=800 height=80}:::
```

> `src` 为图文件地址，必须保留原值。⚠️ 不要手动修改思维导图内容。

#### 原始 Markdown 宏（markdown raw）

```
:::markdown
**这里是原始 Markdown 内容**，会以 Markdown 宏节点嵌入文档
:::
```

#### 原始 HTML 宏（html raw）

```
:::html
<div class="custom">自定义 HTML 内容</div>
:::
```

#### 含合并单元格的表格（table extended）

```
:::table{borderColor="#dddddd" borderStyle="solid" borderWidth=1 responsive=false}
[
  [
    {"type":"table_header","attrs":{"colspan":2,"rowspan":1,"colwidth":[120,120],"bgColor":null,"verticalAlign":null},"content":"合并两列的标题"},
    {"type":"table_header","attrs":{"colspan":1,"rowspan":1,"colwidth":[120],"bgColor":null,"verticalAlign":null},"content":"第三列"}
  ],
  [
    {"type":"table_cell","attrs":{"colspan":1,"rowspan":1,"colwidth":[120],"bgColor":null,"verticalAlign":null},"content":"A"},
    {"type":"table_cell","attrs":{"colspan":1,"rowspan":1,"colwidth":[120],"bgColor":null,"verticalAlign":null},"content":"B"},
    {"type":"table_cell","attrs":{"colspan":1,"rowspan":1,"colwidth":[120],"bgColor":null,"verticalAlign":null},"content":"C"}
  ]
]
:::
```

> ⚠️ 合并单元格表格以 JSON 格式存储，`:::table{...}` 中的属性（`borderColor`/`borderStyle`/`borderWidth`/`responsive`）必须保留原值。单元格 `attrs` 中的 `colwidth` 数组需和列数对应。`content` 字段支持完整 CitadelMD 语法。

#### 目录（catalog）

```
:::catalog{style=none}:::
:::catalog{style=number}:::
:::catalog{style=circle}:::
```

> `style` 取值：`none`（无序号）、`number`（数字）、`circle`（圆点）、`rect`（方块）、`point`（点）。

#### 甘特图（gantt）

```
:::gantt{id="gantt-001" height=400 version=1}:::
```

> ⚠️ 甘特图为只读引用，仅保留 id/height/version，不支持手动编辑内容。

#### 日历（calendar）

```
:::calendar{id=1 view=month docId=100}:::
```

> `view` 取值：`month`（月视图）、`week`（周视图）。

#### 文档目录树（page_tree）

```
:::page_tree{spaceId="space-001" pageId="page-001" maxDepth=3}:::
```

#### 多维表格引用（xtable）

```
:::xtable{nodeId="node-xt-001" xtableId="xt-001"}:::
```

> ⚠️ 多维表格为只读引用，不支持手动编辑，保留原值即可。

#### 空间更新卡片（spaceupdate）

```
:::spaceupdate{spaceId="space-001"}:::
```

#### 附件（attachment）

```
:::attachment{src="https://km.sankuai.com/file/xxx" name="文档.pdf" size="1.2MB"}:::
```

#### 音频（audio）

```
:::audio{url="https://km.sankuai.com/api/file/cdn/xxx" name="录音.mp3" size="862.55KB" align="left"}:::
```

#### 视频（video）

```
:::video{url="https://km.sankuai.com/api/file/cdn/xxx" name="视频.mp4" size="21.15MB" width=640 height=360 align="left"}:::
```

> 注意：`audio` 和 `video` 使用 `url=` 而非 `src=`，必须保留原值。

#### 不支持的宏（not_support）

```
:::not_support{source="confluence" macro="jira" macroId="m001" pageId="123"}:::
```

> ⚠️ 这是从其他平台迁移来的不支持的宏，**请勿删除**，原样保留。

#### 控件（control）

```
:::control{type="date" name="日期控件" key="mykey" value="1773888071769"}:::
:::control{type="date_range" name="日期范围" key="mykey2" value="1773244800000,1773849599999"}:::
```

> `type` 取值：`date`（日期控件）、`date_range`（日期范围控件）。`key` 是控件唯一标识，必须保留原值；`value` 为毫秒时间戳（日期范围用逗号分隔两个时间戳）。

#### 文档列表视图（doc_list_view）

```
:::doc_list_view{parentDocType="current" spaceId=0 pageId=0 displayType="catalog" order="asc" displayCount=14}:::
```

> `parentDocType` 取值：`current`（当前文档）。其他属性保留原值。

#### 附录（appendix）

```
:::appendix:::
```

> 附录分隔符，保留原值。其后的 `:::footnote_list` 包含脚注数据，整块原样保留，**禁止修改**。

#### 嵌入卡片（open_card / open_link / open_iframe）

```
:::open_card{url="https://example.com" nodeId="node-001" type="link" align=left}:::
:::open_link{url="https://example.com" title="标题" nodeId="node-002"}:::
:::open_iframe{height=500 nodeId="node-003" type="wpsExcel" align="left" attachmentId=228524748073}:::
```

---

### 特殊居中/右对齐标题

```
:::heading{level=2 align=center}
居中的二级标题
:::

:::heading{level=3 align=right}
右对齐的三级标题
:::
```

> 只有非左对齐标题才使用此语法，普通左对齐标题直接用 `## 标题` 即可。

---

### 编辑注意事项

1. **保留所有宏节点**：任何 `:::tag{...}:::` 或 `:[tag]{...}` 节点，若不需要修改则原样保留
2. **不要修改 id 字段**：`gantt`、`drawio`、`minder`、`xtable` 等节点的 `id` 是服务端资源标识，必须保留
3. **合并单元格表格**：`:::table` 块内的 JSON 只改 `content` 字段内的文字，不要改 `colspan`/`rowspan` 结构；
4. **每个单元格的 `content` 字段不能为空字符串，若单元格为空则保留 `"content": ""`**（转换时会自动生成一个空 paragraph）；
5. **新增表格时第一行必须是表头行（`type: "table_header"`），不能全部使用 `table_cell`**
6. **空行分隔块**：不同的块元素之间需要有空行分隔，列表项之间不加空行
7. **行内宏不换行**：所有 `:[tag]{...}` 行内宏必须写在同一行内，不能跨行

#### 第三步：回传更新

```bash
# 从文件更新
oa-skills citadel updateDocumentByMd --contentId <id> --file doc.citadelmd

# 同时更新标题
oa-skills citadel updateDocumentByMd --contentId <id> --file doc.citadelmd --title "新标题"
```

#### 调试：查看 CitadelMD 转换为 JSON 的结果

如需验证转换是否正确，可以先转换为 JSON 检查：

```bash
oa-skills citadel convertMdToJson --file doc.citadelmd --output doc.json
```

---

## 总结

| 方式 | 命令 | 数据安全 | 推荐 |
|------|------|----------|------|
| CitadelMD 更新 | `updateDocumentByMd` | ✅ 完全安全 | ✅ 推荐 |

**优先使用 CitadelMD 方式进行文档更新。保护用户的数据完整性是第一原则。**

**输出** 完成编辑后返回用户文档链接，让用户可以直接点击查看文档变更的内容
