# Continue 全文检索：trigram、FTS5 与 BM25

Continue 会先将源码切分为多个 chunk，再为 chunk 建立 SQLite FTS5 全文索引。检索链路如下：

```text
代码文件 → chunk → trigram 倒排索引 → MATCH 找候选 → BM25 排序 → 返回 Top-K chunk
```

## 1. 基于 trigram 进行分词

**trigram**（三元字符片段）是按任意连续 3 个字符的滑动窗口切分文本，而不是按空格或自然语言单词切分。

例如，标识符 `createUser` 可拆为：

```text
cre、rea、eat、ate、teU、eUs、Use、ser
```

这适合代码检索：搜索 `User` 可以命中 `createUser`、`updateUser`；搜索 `Repo` 可以命中 `UserRepository`。它无需预先识别驼峰命名、下划线或中文词边界。
**trigram 分词的结果不会在 SQLite 中以任何形式暴露给普通表，因此无法看到实际分词后的结果**

## 2. 基于 SQLite 的 FTS5 进行倒排索引

**FTS5**（Full-Text Search 5）是 SQLite 的全文检索扩展。Continue 从已有的 `chunks` 表读取代码分块，并将每个 chunk 的路径和正文写入 FTS5 虚拟表：

```sql
CREATE VIRTUAL TABLE fts USING fts5(
  path,
  content,
  tokenize = 'trigram'
);

INSERT INTO fts (path, content) VALUES (?, ?);
```

执行 `INSERT` 时，FTS5 自动按 trigram 分词，并维护内部倒排索引；业务代码不需要手动保存“片段到 chunk”的映射。Continue 额外保存 `fts.rowid → chunks.id` 的映射，以便检索命中后取回原始 chunk 的完整代码、路径和行号。

假设已有两个 chunk：

```text
Chunk 101: function createUser(name) { ... } // createUser函数被trigram分词
Chunk 102: function updateUser(id) { ... }
```

其内部倒排索引可概念化为：

| trigram | 命中的 chunk |
| ------- | --------- |
| `cre`   | 101       |
| `rea`   | 101       |
| `ate`   | 101、102   |
| `Use`   | 101、102   |

上表是逻辑示意，不是 FTS5 对外暴露的普通数据表。

## 3. 倒排索引利于检索的原因

**倒排索引**是“检索片段 → 包含该片段的 chunk 列表”的结构，与“chunk → 正文”的正向存储相反。

没有倒排索引时，搜索 `createUser` 需要逐个扫描全部 chunk，效果类似：

```sql
SELECT * FROM chunks
WHERE content LIKE '%createUser%';
```

有了倒排索引，系统可以直接读取 `cre`、`rea` 等片段对应的少量候选 chunk，再进行排序，无需扫描全部正文。代价是建索引和更新时需要额外的分词、存储与维护成本；收益是后续关键词检索更快。

## 4. 基于 BM25 对检索结果排序

**BM25** 是经典的信息检索相关性评分算法。它不在建倒排索引时为每个 chunk 预先打分；建索引阶段只维护词频、文档频率和 chunk 长度等统计信息。

用户查询时，FTS5 先通过倒排索引找出候选，再由 BM25 评分。评分会考虑：

- **查询片段在该 chunk 中出现得越多，通常越相关；**
- **查询片段在整个库中越少见，区分度越高；**
- **chunk 过长会进行长度归一化，避免超长文本仅因包含更多内容而天然靠前**。

Continue 的查询核心形式为：

```sql
SELECT ...
FROM fts
WHERE fts MATCH ?
ORDER BY bm25(fts, 10)
LIMIT ?;
```

其中 `MATCH` 通过倒排索引找候选，`bm25(...)` 负责相关性排序，`LIMIT` 返回前 N 个结果。SQLite FTS5 的 BM25 返回值越小表示相关性越高；`10` 是为 `path` 列设置的更高权重，使路径命中查询词时获得更多排序优势。

## 名词解释

| 名词      | 含义                          |
| ------- | --------------------------- |
| chunk   | 由源码切分得到、可独立检索的一小段代码文本。      |
| FTS5    | SQLite 提供的全文检索虚拟表引擎。        |
| trigram | 任意连续的 3 个字符组成的检索片段。         |
| 倒排索引    | 从检索片段快速定位到包含它的 chunk 的索引结构。 |
| BM25    | 根据词频、稀有程度和文本长度计算相关性的排序算法。   |
