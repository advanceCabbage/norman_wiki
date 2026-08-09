# 四种 RAG 适用的场景：从 Naive RAG 到 Agentic RAG 如何选型

**RAG 检索策略并不是使用的技术越多越厉害。在 Agent 时代，更重要的是找准用户画像，并依据用户画像制定存储与检索的重点。**

## 一、Naive RAG（朴素 RAG）

### 1.1 检索流程

```text
【离线索引】文档 → 清洗 → 切块（固定长度／递归分割）→ embedding → 写入向量库
【在线查询】query → embedding → 余弦相似度检索 Top-K → 原样拼进 prompt → LLM 生成答案
```

核心特征是**单向、一次性**：检索一次，生成一次，中间没有任何加工，也没有回头路。查询词是什么，就拿什么去算相似度；检索回来什么，就往 prompt 里塞什么。

### 1.2 适用场景

- 低延迟、高并发的兜底场景（客服首轮、IDE 内文档提示）
- 语料本身已经高度结构化（如整理好的 FAQ 对）
- 单一领域的封闭文档问答：产品手册、API 文档、公司制度、课程讲义
- 答案具有“局部性”——某一个片段里就写着完整答案，不需要跨段拼凑

### 1.3 优势

- <span style="display:inline;color:#35b378;font-weight:bold;">实现成本最低</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：一个 embedding 模型 + 一个向量库就能跑</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">延迟最低</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：单次向量检索通常几十毫秒，总链路开销几乎全在 LLM 生成上</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">可解释、好排查</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：出问题只有三个地方——切块、embedding、prompt，二分法很快能定位</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">无额外模型依赖</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：不需要 rerank 模型、不需要 LLM 参与检索环节，成本可预测</span>

> 代价：口语化／模糊查询检索不准；“库里明明有但就是找不到”；跨文档汇总类问题基本答不了。

## 二、Advanced RAG（高级 RAG）

### 2.1 检索流程

仍然是单向流水线，但在检索的**前、中、后**三个位置各插入优化环节：

```text
【索引侧优化】文档 → 语义切块／按标题层级切 → 挂 metadata（来源／时间／权限／章节）
→ 可选：small-to-big（小块检索、大块喂给 LLM）、多向量索引（摘要 + 假设性问题各建一份向量）

【检索前 · Pre-retrieval】query
→ 查询改写（口语化 → 规范化）
→ 查询扩展／Multi-Query（生成 3～5 个变体同时检索）
→ 查询分解（复合问题拆成子问题）
→ HyDE（先让 LLM 编一个“假答案”，拿假答案去检索）
→ 路由（判断该查哪个索引／哪张表）

【检索中 · Retrieval】
        ┌─ 稠密向量检索（语义）─┐
query ──┤                      ├─ RRF 融合 → 候选 Top-50
        └─ 稀疏检索 BM25（关键词）┘
        + metadata 过滤（时间／权限／来源）
        + MMR（最大边际相关，压掉重复内容，保多样性）

【检索后 · Post-retrieval】
Top-50 → Cross-Encoder 重排序（bge-reranker／Cohere Rerank）→ 精排 Top-5
→ 上下文压缩（抽出片段里真正相关的句子，扔掉噪声）
→ 去重 + 位置重排（最相关的放 prompt 首尾，规避“lost in the middle”）
→ prompt → LLM
```

### 2.2 适用场景

- **生产级知识库问答**：企业内部搜索、客服系统、技术支持
- 语料体量大（十万～百万级 chunk），噪声多、来源杂
- 用户查询是自然口语（“那个报销的事怎么弄来着”），和文档书面语存在**语义鸿沟**
- **对准确率和引用溯源有硬要求**：法律、医疗、金融、合规
- 需要按权限／时间／部门做**过滤**的多租户场景

### 2.3 优势

- <span style="display:inline;color:#35b378;font-weight:bold;">同时提升召回率和精确率</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：混合检索管召回（BM25 兜住专有名词、型号、人名这类向量最不擅长的），rerank 管精确</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">直击 Naive RAG 最痛的失败模式</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：查询改写解决“问法不对”，混合检索解决“关键词漏检”，rerank 解决“相关的排在第 30 位”</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">省 token</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：先粗召回 Top-50 再精排到 Top-5，喂给 LLM 的上下文更短更干净，反而比直接塞 Top-20 更准也更便宜</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">仍是确定性流水线</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：延迟可预测、行为可复现，每个环节都能用 RAGAS 这类指标单独量化评测和调优</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">可增量演进</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：每一项优化都能独立开关、独立 A/B，不用推倒重来</span>

> 代价：链路变长，延迟通常增加 300 ms～1 s；引入 rerank 模型等新依赖；但依然是“查一次答一次”，跨文档全局问题仍然无解。

## 三、GraphRAG（图 RAG）

### 3.1 检索流程

和前两者最大的区别：**索引期做重活**，把非结构化文本变成知识图谱。

```text
【离线索引——很重、很贵】
1. 文档切块
2. 逐块调 LLM 抽取实体（人／组织／概念）与关系，并为每个实体生成描述
3. 实体消歧与合并（“张总”／“张三”／“CEO 张” → 同一节点），构建知识图谱
4. 社区检测（Leiden 算法）：把图切成层次化的社区（community）
5. 逐个社区调 LLM 生成“社区摘要报告”，形成 C0 → C1 → C2 多层级摘要金字塔

【在线查询——两种模式】
▸ Local Search（局部搜索）——回答“关于某个具体对象”的问题
query → 识别 query 中的实体 → 定位图中节点
→ 拉取该节点的：邻居实体 + 关系边 + 关联原文块 + 所属社区摘要
→ 组装上下文 → LLM 回答

▸ Global Search（全局搜索）——回答“整个语料的宏观”问题
query → 不定位节点，直接 Map-Reduce 遍历社区摘要
→ Map：每个社区摘要各产出一个“部分答案”+ 相关性打分
→ Reduce：按分数筛选并汇总 → LLM 生成最终答案

（另有 DRIFT search 等混合模式，先局部定位再向外漂移扩展）
```

### 3.2 适用场景

判断标准很明确：**语料里没有任何一段话直接写着答案，答案必须靠“拼”出来。**

- **情报分析与尽职调查**：某公司的关联方、资金链、人员交叉任职
- **全局摘要类问题**：“这批 500 份访谈的核心矛盾是什么”——这是向量检索的绝对死穴，因为不存在一个“最相似”的片段
- **多跳推理**：“负责 X 项目的那个人，还参与了哪些和 Y 相关的事”
- **天然带关系结构的领域**：医疗（疾病—基因—药物—副作用）、供应链风控、法律判例引用链、组织架构、小说人物关系
- 语料**相对稳定**、值得一次性投入重索引成本的知识资产

### 3.3 优势

- <span style="display:inline;color:#35b378;font-weight:bold;">能回答全局性／汇总性问题</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：这是所有基于相似度检索的方案都做不到的——Top-K 永远只能看到局部</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">多跳推理</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：沿着边走两三跳，把散落在不同文档里的事实串成链</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">实体级去重与归并</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：同一个对象在 50 篇文档里的不同称呼被合并成一个节点，信息自动聚合</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">可解释性强</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：答案能溯源到具体的实体节点和关系路径，而不只是“来自第 37 号文档块”</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">抗噪声</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：单篇文档的表述错误，在实体聚合和社区摘要阶段会被其他来源稀释</span>

> 代价：索引期 LLM 调用量极大（几万块文档可能烧掉数百美元和数小时）；语料增量更新是公认难题；不适合高频变动的数据。

## 四、Agentic RAG（智能体 RAG）

### 4.1 检索流程

前三者的检索路径是**写死的**，Agentic RAG 把检索变成 LLM 手里的**工具**，路径由模型自己在运行时决定。

```text
【核心是一个带条件分支的循环，而不是流水线】
query → Agent 规划
│
├─ 判断①：这问题需要检索吗？
│    否 → 直接回答（闲聊、常识、纯推理）── 结束
│    是 ↓
│
├─ 判断②：该查哪个源？（路由）
│    向量库／BM25／SQL 数据库／知识图谱／Web 搜索／内部 API
│
├─ 判断③：用什么查询词？要不要拆成多个子查询并行？
│
├──→ 调用 retrieval tool ──→ 拿到结果
│
├─ 判断④：自我评估（Grade）
│    · 检索到的文档相关吗？ ← CRAG 的做法
│    · 信息够回答问题吗？
│    · 生成的答案有事实依据吗？ ← Self-RAG 的做法
│    · 答案真的回应了用户的问题吗？
│
├─ 不合格 → 改写查询／换个数据源／补一轮检索 ──┐
│                                                  │
└──────────────────── 循环回到规划 ←───────────────┘
（带最大轮次上限，防死循环）
│
└─ 合格 → 综合所有轮次的证据 → 生成带引用的答案

【进阶：多智能体形态】
Planner Agent 拆解任务
→ Retriever Agent A（查文档）   ┐
→ Retriever Agent B（查数据库） ├ 并行
→ Retriever Agent C（查网页）   ┘
→ Synthesizer Agent 汇总去冲突 → 输出
```

工程上这通常用 **LangGraph** 这类状态机／图框架实现——因为它需要条件边、循环和共享状态，普通的 Chain 表达不了。

### 4.2 适用场景

- **深度研究型任务**：写调研报告、竞品对比、“帮我把这三个方案的优劣整理出来”
- **跨异构数据源**：一个问题同时需要查订单数据库（结构化）+ 政策文档（非结构化）+ 实时行情（API）
- **开放域兜底**：内部库查不到就自动转 Web 搜索
- **对可靠性要求高、宁慢勿错**：需要自我纠错，不能拿着不相关的上下文硬答
- 问题复杂度差异大的入口：同一个入口既有“今天几号”也有“分析下 Q3 财报趋势”，需要动态分配算力
- 需要**多轮澄清**的对话式场景

### 4.3 优势

- <span style="display:inline;color:#35b378;font-weight:bold;">自适应算力分配</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：简单问题不检索直接答（省钱省时），复杂问题自动多轮深挖——这是固定流水线做不到的</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">自我纠错能力</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：检索失败时能感知到失败并补救（换查询词、换数据源），而不是把垃圾上下文硬塞给 LLM 生成幻觉</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">多源融合</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：结构化 + 非结构化 + 实时数据，在一次回答中打通</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">能处理复合问题</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：自动分解成子问题，分别检索后再综合，而不是用一个混合查询向量去撞一堆不相关的块</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">可扩展性最好</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：新增一个数据源只是新增一个 tool，不用改动检索链路本身</span>
- <span style="display:inline;color:#35b378;font-weight:bold;">上限最高</span><span style="display:inline;color:#3f3f3f;font-weight:normal;">：它能吸收前三者作为工具——完全可以让 Agent 手里同时握着 Advanced RAG 检索器和 GraphRAG 图谱查询接口</span>

> 代价：延迟不可控（几秒到几分钟）；token 成本可能是 Naive RAG 的 10～50 倍；行为非确定性，评测和调试困难；需要严格的轮次上限和成本护栏。

## 五、选型原则

**选型的一句话原则**：先问“答案在不在单个片段里”——在，走 Naive／Advanced；不在、需要跨文档串关系，考虑 GraphRAG；不在、且连该查哪、查几次都无法预先确定，才上 Agentic。

四者不是替代关系，Agentic RAG 的工具箱里装的往往正是前三者。
