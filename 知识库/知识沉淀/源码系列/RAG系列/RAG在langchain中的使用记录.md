## 零、学习实战目标
| 你的学习点                               | 归属阶段        | 说明                                       |
| ----------------------------------- | ----------- | ---------------------------------------- |
| txt/md 解析、切分、embedding、入库、向量检索、检索接口 | **P1(第一版)** | 现在就做,打通闭环                                |
| 按段落 / 按语义切分、总结索引+原文存储               | **P2**      | 同一批文档跑不同切分策略对比                           |
| 关键字检索(SQLite FTS5)                  | **P2**      | 向量之外的另一条腿                                |
| 混合检索怎么实现                            | **P2**      | 向量+关键字,用 RRF/加权融合                        |
| 排序算法有哪些、各适合什么场景                     | **P2**      | RRF / 加权 / cross-encoder 重排 / MMR,边做边讲原理 |
| 换向量库:PostgreSQL(pgvector)、Milvus    | **P2/P3**   | 靠 config 工厂切换,顺带讲选型                      |
| 各家向量库对比、如何选型、本地部署                   | **P2/P3**   | 结合实操讲原理                                  |
| PDF 解析                              | **P2**      | 加一种 loader                               |
| 表格 / 图片解析                           | **P3**      | 独立课题                                     |
| **音视频解析**                           | **P3(或不做)** | 本质是 Whisper 转录管线,独立大工程                   |
| 识别/拆分/改写用户问题(query 理解)              | **P3**      | 独立课题                                     |

##  一、阶段一：打通主流程
#### 1.1 向量入库
- 待切割文本类型：Markdown 文件
- 切割文本实现：纯 JS 实现，遇到#号就切割，对于切割后的段落再使用 langchain 的RecursiveCharacterTextSplitter 的splitText 执行一次，原因是设置的chunkSize：500，chunkOverlap：80。目的是防止按段落切割出来的片段长于 500 字符
- 基于智谱的embedding-3 模型进行向量化，通过调用智谱 API 接口实现向量化。但ZhipuEmbeddings extends Embeddings，其中Embeddings 是@langchain/core/embeddings 定义的
- **首先**调用addDocuments 方法把每个pageContent 变成向量，**然后**(向量 + 正文 + metadata) 写进 LibSQL。返回写入记录的 id 列表。这里涉及到 langchain 的语法，还不是特别清楚

#### 1.2 向量检索

基类内部两步(@langchain/core)
- **查询和文档必须用同一个模型向量化**，用同一模型将用户的问题向量化① embedQuery(query，我们实现的) ─→ ZhipuEmbeddings.embedQuery ─→ 智谱 API ─→ 1024 维查询向量
- **找出相似度接近的片段** ：[[向量检索优化手段之-创建向量索引]]
	- 在启动项目或录入数据到向量数据库时会构建**向量索引**
	- 查询阶段通过**向量索引**机制能加快检索的速度
	- 最终找出向量相似使用的是 LibSQL 实现的 similaritySearchVectorWithScore 方法
- **找出原文档内容**
	- **原文不是从向量还原出来的**，(向量是有损单向的,变不回文字)
	- **入库时我们把 `content` 原文和向量存在了同一行**,检索时按 rowid 去表里把它取回来
## 二、阶段二：丰富能力
#### 2.1 实现按段落 / 按语义切分、总结索引+原文存储
##### 2.1.1 实现总结索引 + 原文存储
1. **首先**将整篇文档调用 LLM 总结为一段摘要
2. **其次**将摘要作为 pageContent 内容，整篇完整的文档作为 metadata 对象中的字段存储
3. **接着**将pageContent 进行向量化。向量数据库中有三个字段 content、metadata、embedding
4. **最后**将 pageContent 和对应的 metadata 数据以及存入数据库，通常向量检索是匹配embedding，然后返回存储了原文的pageContent，但对于总结类型的向量来说，需要返回metadata 中的 original 字段（也就是摘要前的原文）

```json
// 向量数据库存储的内容
{
	pageContent:"总结的摘要",
	metadata:{
		type: "summary", // 统一契约的判别器,表示摘要类型
		docId: raw.source, // 父指针（当前 == source）
		source: raw.source, // 文档的路径
		original: raw.content, // ← 检索命中后要返回的「原文」
	},
	embedding:"XXX" // 向量化后的数字
}

```

#### 2.2 按照语义切分段落

- **首先**按照中英文句号、换行对文档进行按句子维度切分
- **然后**调用智谱 embedding 模型，对每个句子进行向量化
- **接着**使用cosineDistance 函数计算相邻两个句子之间的余弦距离
- **其次**对比两两句子余弦距离差距最大的 5%句子，将差距最大的 5%句子进行切分，其余句子自动归并为一段
- **最后**将分好段落的内容，复用RecursiveCharacterTextSplitter 进行按照字符数量切割一次，避免出现大段内容，导致超出我们设置的最长切片长度 500 字符的限制。再将最后的内容写入向量数据库
##### 2.2.1 计算句子之间余弦距离的算法
这是一个业界通用的数学公式，目的计算两个向量的夹角大小，文本变成向量,比的是两向量的夹角——夹角越小越相似;余弦相似度只看方向、不看长度。**为什么不看长度**:分母除以两向量的模长做归一化,所以只反映方向(语义),不受文本长短影响

【备选】LangChain 也内置了向量数学工具 @langchain/core/utils/math，有 cosineSimilarity / normalize / maximalMarginalRelevance(MMR) 等；但那是「矩阵批量版」（吃两批向量、返回相似度矩阵、且返回的是相似度不是距离），
##### 2.2.2 判断句子是否应该分段的方案

- **percentile**：所有相邻距离的第 N 百分位(默认95)；直观、自适应文档;最常用
- **standard_deviation**：均值 + k×标准差；把"距离异常大"的当断点;假设距离近似正态
- **interquartile(IQR)**：用四分位距 Q3−Q1 定阈值；对极端值更**稳健**,不易被个别超大距离带偏
- **gradient**：对距离的**变化率(梯度)**再取百分位；适合**句子都很像**的场景(如法律/医疗,绝对距离都偏高、拉不开差距),看"相对突变"而非绝对值

##### 2.2.3 语义切分流派

 1. **相邻距离断点**：相邻句语义突变处切
 2. **带 buffer 的变体**：断句后先和邻居拼再 embedding（**langchian 的用法默认为 1**），简单来说就是三个句子一起 embedding
 3. **LLM / 命题式**:让 LLM 直接判断边界
 4. **聚类式**:把语义相近的句子**聚类**成块(可跨不相邻句)
 5. **结构/层级式**:按标题、章节等文档结构切

## 三、支持混合检索
#### 3.1 实现基于 FTS 5 的关键字检索

**数据录入阶段**
- **首先**基于已经被全文分块好的片段进行存储
- **其次**创建一张基于 FTS 5 的 trigram 分词索引表
```ts
// FTS5 虚拟表：content 用 trigram 分词做全文检索；metadata 用 UNINDEXED
// 只存不索引（存 JSON，检索命中后用来还原来源/标题等）
await db.execute(
`CREATE VIRTUAL TABLE IF NOT EXISTS ${FTS_TABLE} ` +
`USING fts5(content, metadata UNINDEXED, tokenize='trigram')`,
);
```
- **然后**将分好块的内容存入表中，包含：被检索 content 和 metadata 
```ts
db.batch(
	docs.map((doc) => ({
		sql: `INSERT INTO ${FTS_TABLE}(content, metadata) VALUES (:content, :metadata)`,
		args: {
			content: doc.pageContent,
			metadata: JSON.stringify(doc.metadata),
	},
	})),
);
```
- **最后**：我们只建了一张虚拟表 `vectors_fts`,但SQLite 在背后自动帮我们建了五张真正存数据的表（**这无需我们操作，也不能操作**）。五张虚拟表的作用和内容分别是：记住倒**排索引本体**、**索引段的目录**、**原始内容的副本**即可

| 影子表                         | 作用                                                  | 实测内容                                            |
| --------------------------- | --------------------------------------------------- | ----------------------------------------------- |
| ** `vectors_fts` **         | 你唯一该碰的**虚拟表/入口**,INSERT、`MATCH` 查询都走它               | —(本身不存数据)                                       |
| ** `vectors_fts_data` **    | **倒排索引本体**:trigram → 哪些文档含它,二进制 b-tree。`MATCH` 快就靠它 | 一堆索引 blob                                       |
| ** `vectors_fts_idx` **     | 索引段的**目录**:记录每个词的数据在 `_data` 的哪段,加速定位               | 段元信息                                            |
| ** `vectors_fts_content` ** | **原始行值的副本**:你 INSERT 的每列都存一份,供 `SELECT` 取回          | `{id:1, c0:'向量数据库怎么选型', c1:'{"type":"chunk"}'}` |
| ** `vectors_fts_docsize` ** | 每行的**词数(长度)**,给 **bm 25** 排序算权重用                    | `{id:1, sz:<07 00>}`                            |
| ** `vectors_fts_config` **  | 建表**配置**(FTS 5 格式版本、分词器等)                           | `{k:'version', v:4}`                            |

**数据检索阶段**
- **首先**将用户的 query 变成 FTS 5 的 MATCH 表达式，仅仅是按照空格将 query 切分，并使用 OR 连接。我们的任务就完成了，后续 FTS 5 拿到我们给的内容后，会严格按照 trigram 分词器对我们传入的内容进行分词
- **然后**实现 SQL 语句，指定使用 FTS5 的 bm25 算法进行相关性打分和排序
```ts
// bm25(表名) 是 FTS5 内置的相关性打分；rank 默认就是 bm25，ORDER BY rank
// 把最相关的排在前面（bm25 越负越相关）。
db.execute({
	sql:
	`SELECT content, metadata, bm25(${FTS_TABLE}) AS score ` +
	`FROM ${FTS_TABLE} WHERE ${FTS_TABLE} MATCH :q ORDER BY rank LIMIT :k`,
	args: { q: match, k },
});
```
- 将检索结果返回，bm25 返回的结果中，最相关的排在最前面的，默认是按照升序（也就是数值越小越相关），因此我们在返回给用户看的分数时就需要将小的分数处理为大的，方便用户理解

#### 3.2 实现混合检索
- **首先**在检索入口增加 hybrid 混合检索，传入 hybrid 时才走混合检索
- **然后**并发进行向量检索和关键字检索
- **接着**将向量检索和关键字检索的结果，对结果进行去重处理。因为向量检索和关键字检索都是基于相同的 chunk 实现存储的，matedata 中有携带 chunkIndex。因此可以使用chunkIndex 相同作为去除唯一标识。**同时**记录每条返回内容在各自检索结果中的排名，例如：当前内容在向量检索中排第一，在关键字检索中排第三
- **其次**按照 RRF（Reciprocal Rank Fusion 倒序排序融合）进行排序
- **最后** 按照融合分降序，取 ToP K

更多混合检索排序算法见[[混合检索结果融合与排序方法]]。**另外工程级别的设计还应该包含：调用重排模型，传入用户的问题和 RRF 得到的 TopK，让大模型进行最后的排序**。例如：Voyage `rerank-2.5`  或 Qwen 3-Reranker

#### 3.3 实现 MMR

**MMR （Maximal Marginal Relevance）最大边际相关：去冗余、要多样** [[混合检索结果融合与排序方法]]

- **首先**前序步骤和「实现混合检索」一致，分别从向量检索和关键字检索返回 20 条数据，然后进行去重和排序
- **然后**对去重和排序后的结果，裁剪 20 条数据。将这 20 条数据进行向量化，同时将用户的问题也进行向量化
- **最后**调用 langchain 的maximalMarginalRelevance 方法进行 MMR 排序。设置相关性和多样性分别占比 50%，最后返回 5 条排名在前面的数据
```ts
import { maximalMarginalRelevance } from "@langchain/core/utils/math";

// MMR 在池内挑 topK；返回候选下标，按 MMR 挑选顺序排列。
const selected = maximalMarginalRelevance(
	queryVector, // 用户输入，算“相关性”用:cos(query, 候选片段内容)
	poolVectors, // 候选们的向量:既算相关性,也算“候选之间”的相似度(惩罚项)
	config.search.mmr.lambda, // 上面那个 λ:相关 vs 多样 的权重
	topK, // 选几条 = 循环几轮
);
```

## 四、扩展文档类型
#### 4.1 支持 PDF 切分
- **首先**引入unpdf 库，
- **然后**使用 unpdf 库提取 PDF 文本，并将各页文本用换行拼成一篇文档
- **最后**用分块切割的思路对整篇 PDF 进行分块、向量化、入库
- **注意**：1. 表格会被拍平为普通文本 2. 图片无法解读 3. 扫描件/图片型 PDF 无法抽取文字内容
```ts
import { extractText, getDocumentProxy } from "unpdf";
/**
* 用 unpdf(基于 pdfjs)抽取 PDF 的文本。mergePages=true 把各页文本用换行拼成一整篇，
* 之后交给切分器处理(和 txt/md 走同一条流水线)。
* 注意：只抽“文本层”。扫描件(图片型PDF)抽不出文字，需 OCR，属于 P3。
*/

async function extractPdf(path: string): Promise<string> {
	const buffer = await readFile(path);
	const pdf = await getDocumentProxy(new Uint8Array(buffer));
	const { text } = await extractText(pdf, { mergePages: true });
	return text;
}
```

## 五、切换向量数据库 PostgreSQL
#### 5.1 PostgreSQL 安装
- 安装并打开 docker
- 使用 docker 下载包含 pgvector 扩展的 PostgreSQL 镜像
- 创建并启动 PostgreSQL 容器；启动时将容器的 `5432` 端口映射到本机端口，并挂载 Docker 数据卷保存数据库文件，确保容器重启或重新创建后数据仍可保留
**小知识**：创建数据卷可以确保删除容器时，数据还在。通过 PostgreSQL 写入的数据会落盘到本机；使用命名数据卷，是为了让这些真实数据库文件不随容器删除而消失，并且便于复用、备份和管理。PostgreSQL 落盘到本机磁盘的数据和数据卷是同一份数据。假设我们不创建数据卷，实际 PostgreSQL 也会默认创建一份数据卷。

#### 5.2 PostgreSQL 的可视化工具 DBeaver
- **首先**下载并安装 DBeaver
- **然后**通过新建连接与 docker 启动的 PostgreSQL 数据库建立连接，需要输入端口、数据库名称、数据库账号、数据库密码
- **最后**可以看到 PostgreSQL 相关的数据，善用表刷新功能确保看到的数据是实时的，另外 DBeaver 还支持很多可视化数据库例如：SQLite、MongoDB、Oracle 等

#### 5.3 代码层面录入文档到 PostgreSQL
##### 5.3.1 向量型数据录入
- **首先**对文档进行分块，可以是语义也是标题分块
- **其次**使用 langchain 封装好的PGVectorStore 方法（可以省很多事）
	- 1. 与数据库建立连接；传入数据库 host、port、database、user、password 等
	- 2. 指定表名及表的字段名
	- 3. 指定余弦相似度
- **然后**也基于 langchain 提供的createHnswIndex 方法创建索引，目的是提升检索效率，效果于 SQLite 中的一样[[向量检索优化手段之-创建向量索引]]
- **最后** 对向量化的文档入库
```ts
import { PGVectorStore } from "@langchain/community/vectorstores/pgvector";

// PGVectorStore.initialize 会自动 `CREATE EXTENSION vector` 并建表(带向量列维度)，
// 所以我们不用像 LibSQL 那样手写 DDL。返回的 similaritySearch 分数同样是余弦距离。
const store = await PGVectorStore.initialize(embeddings, {
	postgresConnectionOptions: {
		host: pg.host,
		port: pg.port,
		database: pg.database,
		user: pg.user,
		password: pg.password,
	},

	tableName: pg.table,	
	// 显式指定列名，和 LibSQL 表对齐（换库只换底层，字段名保持一致）。	
	// LibSQLVectorStore 内部把 content/metadata 写死，embedding 由 config.db.column 指定；	
	// 这里让 PG 用同样的列名。id 是 PG 的主键，相当于 LibSQL 的隐式 rowid。	
	columns: {	
		idColumnName: "id",
		contentColumnName: "content", // PG 默认是 "text"，改成 "content" 对齐 LibSQL
		metadataColumnName: "metadata",
		vectorColumnName: config.db.column, // "embedding"
	},
	distanceStrategy: "cosine", // 与我们一贯的余弦保持一致
	dimensions: config.zhipu.dimensions, // 1024，和 embedding 维度对齐
});

// 建 HNSW 近似最近邻索引(pgvector)。不建索引时 PG 是【暴力全表扫描】(数据量大就慢)；
// HNSW 类比 LibSQL 的 libsql_vector_idx，让检索走近似图搜索、快很多。
// 内部是 CREATE INDEX IF NOT EXISTS(幂等，可每次启动安全调用)；
// m=16 / efConstruction=64 用 pgvector 默认；距离函数按 distanceStrategy(cosine) 自动选。

await store.createHnswIndex({ dimensions: config.zhipu.dimensions });
```
##### 5.3.2 原文数据录入，支持关键字检索
- **首先**单独开一个同 PostgreSQL 的连接池，创建表及表字段
- **接着**为表创建 trigram 索引，关键字是 `gin_trgm_ops` ，以 content 字段建立索引，后续录入到表中的文章都会自动被 trigram 分词并建立索引
- **最后** 将分块的内容录入到全文检索向量表中
```ts
// GIN + gin_trgm_ops：三元组倒排索引，加速 ILIKE 子串匹配（中文同样有效）。
await pool.query(
`CREATE INDEX IF NOT EXISTS idx_${KW_TABLE}_trgm ` +
`ON ${KW_TABLE} USING gin (content gin_trgm_ops)`,
);
```

#### 5.4 代码层面 PostgreSQL混合检索
- **关键字检索**
	- **首先**将用户输入按照空格分割
	- **其次**使用%将分割的内容拼接
	- **然后**将用户的输入连同查询语句一起发送给数据库，数据库自然会对 query 进行 trigram 分词并检索
	- **最后**返回最相关的 topK 内容
```ts
// ILIKE ANY(patterns)：命中任一词即可（对应 FTS5 的 OR）；
// word_similarity(query, content)：整条 query 与内容的相关度（0~1，越大越相关）。
const res = await pool.query(
	`SELECT content, metadata, word_similarity($1, content) AS sim	
	FROM ${KW_TABLE}	
	WHERE content ILIKE ANY($2)	
	ORDER BY sim DESC	
	LIMIT $3`,
	[query, patterns, k],
);
```
- **向量检索**
	- 由于 langchian 封装了similaritySearchWithScore 方法，因此不同的向量数据库在向量检索时都调用相同的方法即可，不同之处在于 store.similaritySearchWithScore。这里的 stor 是 SQLiteStore 还是 PostgreSQLStore
	- similaritySearchWithScore 实际是两个步骤
		- **步骤一**调用对应 store 提供的embedQuery 方法对用户的问题进行向量化，这里都是基于ZhipuEmbeddings，因此SQLiteStore 或PostgreSQLStore 都是相同的
		- **步骤二**假设是SQLiteStore 则 langchain 转化语句为，大致为帮助理解即可。不必纠结细节，langchain 会处理好
`
```sql
// 属于SQLiteStore的
FROM vector_top_k(
  'idx_vectors_embedding',
  vector(:queryVector),
  :k
)

// 属于PostgreSQLStore的
SELECT *,
  "embedding" <=> $1 AS "_distance"
FROM vectors
ORDER BY "_distance" ASC
LIMIT $2
```


## 六、切换向量数据库 Milvus