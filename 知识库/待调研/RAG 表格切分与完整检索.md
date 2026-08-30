# RAG 表格切分与完整检索

> 结论先行：**表格不应被当作普通长文本切块。** 想同时做到“检索不漏数据”与“命中的片段可独立理解”，需要把「找表/找行」和「取数/计算」分开：向量检索只负责候选发现；原始表（或其结构化副本）才是最终事实源。若问题含有“全部、多少、合计、平均、排名、满足条件的所有项”，仅靠 top-k chunk 检索在逻辑上无法保证不漏，必须对完整表执行受约束的查询。

## 1. 先澄清：有两种完全不同的“完整”

| 目标 | 例子 | 不能只靠什么 | 正确保证方式 |
| --- | --- | --- | --- |
| **片段完整**（被单独召回也看得懂） | “华东区 2025 Q2 营收是多少？” | 只存 `华东 / 100` 的裸行或裸单元格 | 召回时有表名、标题/时间范围、完整表头路径、行标识和值 |
| **结果完整**（答案没有漏项） | “列出所有营收低于 100 万的地区”“各区总和” | 向量库 top-k、只返回最相似的几行 | 在完整、可查询的表上执行 `WHERE/GROUP BY/ORDER BY`，返回结果集和行数 |

这一区分很关键：embedding 排序只承诺“相关性排序”，不承诺“满足谓词的集合已穷尽”。因此不应把“调大 top-k”误称为完整性方案；它只能降低漏召回概率。

这不是纯粹的架构偏好。Azure AI Search 的官方指引明确建议：对于 product database 这类结构化源，不要做 chunking，而应将字段映射到原数据源；其 RAG 指引也建议 keyword 与 vector 并行的 hybrid retrieval 来提高最大召回率。[Agentic retrieval data modeling](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-index)；[RAG retrieval overview](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)。

## 2. 为什么通用文本切块会破坏表格

表格语义来自二维关系：一个数据单元格的意义由列头、行头、分组、标题和周围说明共同决定。HTML 标准将表定义为行、列、单元格构成的二维网格，且数据单元格可关联零到多个表头；`headers`、`scope`、`rowspan`、`colspan` 都会影响关联关系。[HTML Standard：table model](https://html.spec.whatwg.org/multipage/tables.html#table-model)  

因此按 token 在中间截断会造成两类错误：

- **语义孤儿**：命中 `1,200`，却不知道它是金额、人数还是百分比；中间行没有表头也无法判断列意义。
- **集合缺口**：同一条件的行被分到多个块，top-k 只取到一部分；聚合、最大最小、排名、去重都可能错。

研究证据也与此一致。TableRAG 指出，整表输入会受上下文长度和长上下文推理退化影响，简单截断或只读 schema 又会丢失关键数据；其方案将 schema 检索与 cell 检索分开，并让程序代理访问表。[TableRAG, 2024](https://arxiv.org/html/2410.04739)（见 §1、§3.3）。它还明确区分：知道列名时，均值等计算可由程序完成；而 cell retrieval 主要用来定位关键词及其列归属（§3.3）。

## 3. 推荐架构：一份规范表，三个检索视图，一条精确取数通道

```text
Excel / HTML / Markdown
        │  解析、保留来源和二维结构
        ▼
Canonical Table（唯一事实源：schema + rows + cells + provenance）
   ├─ 表级索引：标题、说明、表头、样例/摘要 ──→ 找到候选表
   ├─ 行级索引：每行的「表头路径=值」 ────────→ 找到候选记录
   ├─ 单元格/值索引：列路径 + 值 + row_id ────→ 找到关键词、别名、精确值
   └─ SQL / DataFrame / DuckDB ────────────────→ 完整过滤、聚合、排序、Join
                                                   │
问题路由：检索型 ──> hybrid 召回 ──> 父表/行/列展开 ──> 完整上下文给 LLM
          集合/计算型 ─> schema linking ──> 受限查询 ──> 结果集 + 证据行给 LLM
```

这里的关键不是多存几份文本，而是每个索引项都有可回到规范表的稳定指针：`table_id, sheet/page, row_id, column_id, source_range, version`。索引是派生物，可以重建；规范表不可被切块结果替代。

### 3.1 Canonical Table 要保留什么

最小数据模型：

```text
Table: table_id, source_uri, source_version/hash, sheet_or_page, title/caption,
       surrounding_heading, notes, header_tree, primary_key_candidates
Column: column_id, ordinal, header_path, display_name, type, unit, format
Row:    row_id, ordinal, row_header_path, group_path
Cell:   (row_id, column_id), raw_value, display_value, formula?, provenance
```

- `header_path` 不是简单的最底层列名。多级表头应保存为 `2025 / Q2 / 营收（万元）`，而非只留“营收”。
- `raw_value` 与 `display_value` 分开；Excel 还应按需求保留公式及计算值，避免把 `10%`、日期、货币格式在解析时变形。
- `source_range` 记录 Excel 的 sheet + A1 范围、HTML 的 DOM/table/cell 路径，Markdown 的文件行范围。它既用于引用，也用于复核。
- HTML 必须解析而不是正则拍平：要保留 `caption`、`thead/tbody/tfoot`、`scope`、`headers`、合并单元格。HTML 规范要求按算法把 data cell 与其 header cell 关联起来；合并单元格覆盖多个 grid slot。[HTML Standard：header assignment](https://html.spec.whatwg.org/multipage/tables.html#forming-relationships-between-data-cells-and-header-cells)

## 4. 怎么切：按结构边界，而非 token 边界

### A. 小表：整表是一个父 chunk

若完整表（包含标题、表头、脚注）在上下文预算内，最稳妥：整表作为一个 parent chunk，同时建立行/单元格子索引。回答时直接从规范表 materialize 全表。**不要**因为可以切而切。

### B. 常规纵向表：一行为原子，多个相邻行合为子块

行块格式应是自包含 key-value，而不是 CSV 的裸值：

```text
表：2025 年区域经营报表；单位：万元；口径：含税
列：区域｜季度｜营收｜毛利率
记录：区域=华东；季度=2025-Q2；营收=1,200；毛利率=18.4%
记录：区域=华南；季度=2025-Q2；营收=980；毛利率=16.9%
来源：sheet=经营报表，rows=18-19，table_id=T42
```

规则：

1. **不把一个 data row 切开**；按行累积至 token 预算。
2. 每个块重复：表名/文档标题、限定条件（单位、期间、口径）、完整 header tree、每行的主键或行头路径。
3. 块可不重叠；“表头 + 行标识重复”比复制相邻数据行更有价值。相邻行只在需要比较/序列趋势时做少量 overlap，且 overlap 行需用相同 `row_id` 去重。
4. 大单元格（描述列、备注列）可在**该单元格内部**再切，但每个子片段必须携带同一 `row_id + header_path`，最终回答时回填整行。

近期的结构感知切分研究也采用 row-level key-value 单元，在结构边界内按 token 约束合并，而不是任意文本截断。[Structure-Aware Chunking for Tabular Data in RAG, 2026](https://arxiv.org/abs/2605.00318)

工程实现也印证这一原则：Unstructured 的官方源码将 table 默认隔离在预块中；续块可重复 table header，也可配置为不切 table。[`title.py`](https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/chunking/title.py)。这可作为“表头必须随块走、表格不能和普通段落任意混切”的实现参考，但它本身仍不能解决集合型查询的全量性。

### C. 宽表/交叉表：不要横向截成无名列

一行列太多时，按“列组”拆，但每个投影块都重复 row key、表头祖先路径和列组名：

```text
表：预算；记录：部门=研发，年度=2025
列组：2025 / Q2
字段：人力成本=120；云服务=35；设备=18
```

命中任一投影后，使用 `(table_id, row_id)` 回表补齐该行全部字段或本问题要求的列。不要让 LLM 从两个独立的横切块自行猜测拼接关系。

对交叉表可在规范层做“长表化”派生：`行维度、列维度、指标、值`；同时保留原始二维布局用于展示。TableRAG 的 schema/cell 分离亦说明，列名与具体值是不同粒度、应分别检索的对象。[TableRAG §3.3](https://arxiv.org/html/2410.04739#S3.SS3)

### D. Excel / HTML / Markdown 的特殊处理

| 来源 | 入库边界 | 必做保留 |
| --- | --- | --- |
| Excel | 一个 sheet 可能有多个逻辑表；空行、格式、合并单元格、标题行常是边界线索 | sheet 名、表的 A1 range、隐藏行/列策略、公式/值、合并区域、冻结区；不要默认把整个 sheet 当一张表 |
| HTML | 一个 `<table>` 通常是一张逻辑表，但嵌套表/布局表需识别或降级 | 原始 HTML、caption、DOM 顺序、`thead/tbody/tfoot`、`th` scope/headers、rowspan/colspan；不能只取 `td.textContent` |
| Markdown | 一个 pipe table 往往是平表，但标题/段落常在表外 | 最近的标题、表前说明、表后脚注、原始行号；它们必须作为 table context，而非普通段落丢给另一个 chunk |

## 5. 怎么检索，才能既召回又能返回完整片段

### 5.1 检索型问题：多粒度 hybrid 召回 + 确定性展开

适用：“哪个客户的续约金额是 120 万？”“Q2 华东毛利率？”

1. 对 table summary/schema、row KV、cell fact 同时做 **BM25/关键词 + 向量** 召回；数值、编码、产品名通常更适合精确/关键词匹配，语义别名更适合 dense。
2. 结果按 `table_id` 聚合、rerank，先确保候选表命中；开放域 table QA 通常也是先选候选表、再在候选表上抽取答案。[Open Domain QA over Tables via Dense Retrieval](https://aclanthology.org/2021.naacl-main.43.pdf)
3. 对命中的 `row_id` 从 canonical store 取完整行；对命中的 cell 取其所在行、header path、标题、脚注。需要比较时再补邻近行或同主键行组。
4. 将**经展开后的完整对象**（而非原始 vector chunk）给 LLM，并附来源定位。

可见，检索时的小并不等于生成上下文也小；“检索对象”与“给模型阅读的证据对象”应分离。

### 5.2 集合/计算型问题：检索用于定位，查询用于保证集合完整

适用信号：`所有/全部/分别/总计/平均/最高/最低/排名/前 N/占比/同比/满足…的`。

流程：

1. 用 table/schema/cell 检索和 query expansion 做 **schema linking**：确定表、列、同义值和可能过滤条件。
2. LLM 生成受限 DSL 或 SQL；校验只能读白名单表列、限定 `LIMIT`、禁止写操作，并对列名和值做校验。
3. 在 canonical table 的 DuckDB/SQLite/DataFrame 上执行；数据库扫描的是完整表，不是召回的若干 chunk。
4. 把查询结果、`count(*)`、聚合过程、关键证据行和来源返回给 LLM 叙述；结果过长时分页/导出，而不是偷偷截断并说“全部”。

这与 TableRAG 的实证设计相符：它用 schema retrieval 找列、cell retrieval 定位值，再让 program-aided solver 操作表；论文特别指出，已知列名后均值可由程序计算。[TableRAG §3.3](https://arxiv.org/html/2410.04739#S3.SS3)

> **硬边界**：如果业务要求“零漏项”，就不能以向量召回作为答案全集。向量召回可决定“查哪张表/哪几个字段”，但谓词筛选、聚合、排序、Join 必须对全量规范表执行。

## 6. 如何验证“没漏”与“看得懂”

### 6.1 入库完整性（可自动化为 CI）

- **行覆盖**：解析后的 row_id 集合与源表数据行集合一致；每行恰好一次进入 canonical store。
- **单元格覆盖**：每个非空源 cell 都能映射到唯一 `(row_id, column_id)`；合并单元格记录覆盖范围，不能静默复制成多个“原始事实”。
- **可逆性**：从 canonical table 重建二维值矩阵，与源表的规范化快照/hash 比对；异常表入人工复核队列，而不是猜表头。
- **索引覆盖**：每个行/单元格索引项都能回指已存在的 canonical id；建立索引后核对表/行/单元格计数、版本 hash。

### 6.2 片段完整性

给每个可直接送入 LLM 的 evidence object 做断言：`table title + header_path + row identifier + value + source pointer` 均非空（无表头的矩阵例外，必须明确标记）。随机抽样单个 chunk，要求审阅者能回答“值是什么、哪个字段、哪条记录、哪个时间/单位”。

### 6.3 检索与端到端评测

不要只看最终回答正确率，至少分层量：

| 指标 | 要问的问题 |
| --- | --- |
| Table Recall@k | 正确表是否进入候选集？ |
| Row / Cell Recall@k | 支撑答案的行/单元格是否被召回？ |
| Evidence completeness | gold evidence 集是否是召回证据集合的子集？ |
| Execution exactness | 对过滤、聚合、排序题，执行结果集/数值是否与标准查询一致？ |
| Context completeness | 给 LLM 的每条证据是否含完整 header/行/来源？ |

TableRAG 也将 column 和 cell 的 retrieval precision/recall 单独评估，而不是只看最终答案。[TableRAG §4.5](https://arxiv.org/html/2410.04739#S4.SS5)；这是适合直接复用到产品评测的思想。

## 7. 方案取舍

| 方案 | 适用 | 主要问题 |
| --- | --- | --- |
| 整表一个向量 chunk | 小表、只做概览 | 大表超 token；无法保证集合题完整 |
| 固定 token 切 Markdown/CSV | 不建议 | 切断 header-row/row-cell 关系，最容易语义孤儿 |
| 行级 KV chunk | 查单条记录、语义问答 | 聚合/“全部”仍会漏，须回表执行查询 |
| cell fact chunk | 关键词、实体、别名定位 | 单元格天然缺上下文，必须通过 row/table id 展开 |
| table + row + cell 多索引 + 规范表查询 | 企业通用推荐 | 实现复杂，需要 schema 和数据质量治理 |

## 8. 最小可行实现顺序

1. 先实现 lossless parser 与 canonical store：表、列、行、单元格、来源指针和版本。
2. 先做 table-level + row-KV 的 hybrid 索引；命中行后回表展开完整行。
3. 增加问题分类：**lookup/explain** 走 RAG，**set/aggregate** 走 schema linking + query execution。
4. 数据规模或别名很多时，再加 cell-value 索引、query expansion 和 reranker；TableRAG 已验证 schema 与 cell 的分开检索在大表任务中的价值。[论文与代码](https://github.com/google-research/google-research/tree/master/table_rag)
5. 最后用“漏一行就失败”的合成与真实问题集做回归，而不是只测“答案大致像不像”。

## 参考的一手资料

1. Chen et al.（Google Cloud AI Research / Google DeepMind 等）, [*TableRAG: Million-Token Table Understanding with Language Models*](https://arxiv.org/html/2410.04739), NeurIPS 2024。schema retrieval、cell retrieval、program-aided solver，以及 row/column 压缩的局限。
2. Herzig et al.（Google Research）, [*Open Domain Question Answering over Tables via Dense Retrieval*](https://aclanthology.org/2021.naacl-main.43.pdf), NAACL 2021。先检索候选表、再进行表内 QA 的两阶段架构及 Recall@K 评估。
3. Herzig et al.（Google Research）, [*TAPAS: Weakly Supervised Table Parsing via Pre-training*](https://aclanthology.org/2020.acl-main.398.pdf), ACL 2020。表格问答是选择单元格并可施加聚合的任务，说明 cell/aggregation 是第一类对象。
4. WHATWG, [*HTML Standard — Tables*](https://html.spec.whatwg.org/multipage/tables.html)。HTML 表格的二维 grid、跨行列及 data-cell/header-cell 关联算法。
5. Guttal et al., [*Structure-Aware Chunking for Tabular Data in Retrieval-Augmented Generation*](https://arxiv.org/abs/2605.00318), 2026 preprint。以 row-level key-value 和结构边界进行 token 受限切分的实证方案。
6. Microsoft, [*Azure AI Search — Create an agentic retrieval pipeline*](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-index)。结构化数据库字段映射、而非 chunking 的官方建议；[RAG overview](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview) 说明 hybrid keyword/vector retrieval 的召回用途。
7. Unstructured, [`unstructured/chunking/title.py`](https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/chunking/title.py)。`isolate_table`、`repeat_table_headers` 与 `skip_table_chunking` 的源码实现。

## 待验证

- 现有数据是否以“报表表格”为主（需要标题、脚注和行组），还是“业务明细表”为主（应优先 SQL/DataFrame）？二者的最佳索引预算不同。
- Excel 的公式、隐藏行列、多个表区域是否需要作为知识范围的一部分？这必须在产品层先定义，不能让 parser 擅自决定。
- 对“完整”的产品承诺是什么：返回所有结果、还是在 token 预算内给出完整计数和可下载全量？这是 UI 和接口设计问题，不是 chunk size 参数。
