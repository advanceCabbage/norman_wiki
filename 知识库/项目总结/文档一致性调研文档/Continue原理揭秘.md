## 一、Continue 是什么

Continue 是一款开源框架，在 github 上拥有 27.4 K Start，github 地址: [https://github.com/continuedev/continue](https://github.com/continuedev/continue)，官网地址：[https://hub.continue.dev/](https://hub.continue.dev/)。

## 二、Continue 功能介绍

Continue** 使开发者能够创建、共享和使用自定义 AI 代码助手，通过我们的开源 VS Code 和 JetBrains 扩展以及模型、规则、提示、文档和其他构建模块的中心**

- **在侧边栏中聊天以理解和迭代代码**
- **自动完成以在您键入时接收内联代码建议**
- **编辑以在不离开当前文件的情况下修改代码**
- **代理以对您的代码库进行更实质性的更改**

## 三、Continue CodeBase 方案详解

### 3.1 CodeBase 的定义是什么？

在软件开发中，代码库（codebase）是用于构建特定软件系统、应用程序或软件组件一组的源代码 ------来自维基百科

### 3.2 Continue CodeBase 具备什么能力？

Continue CodeBase 由**文件索引创建**和**文件检索**两部分组成**。Continue CodeBase 实现了一个多维度、智能化的代码理解系统**，通过四种专业化索引（**分块索引、代码片段索引、全文搜索索引、向量索引**）共同协同工作，并结合** [Tree-sitter](https://github.com/tree-sitter-grammars) **语法解析的智能分块算法和多模型支持的**向量化技术**，能够从结构化符号搜索、关键词匹配到语义相似性理解等多个层面深度解析代码库，并通过**多策略检索管道**和** LLM 重排序机制**，提供快速响应的高质量代码搜索、理解和推荐能力，**从而将传统的文本搜索升级为具备语义理解的智能代码助手基础设施**
![[0746339b-84ac-47ef-ad8b-4e0e26e9a8b0.png]]
### 3.3 文件索引创建阶段方案设计

文件索引创建由 4 种索引创建方式共同组成，分别是：**ChunkCodeBaseIndex(分块索引)、CodeSnippetsCodeBaseIndex(分段索引)、FullTextSearchCodeBaseIndex（全文索引）、LanceDbIndex（向量索引）**

#### 3.3.1 **ChunkCodeBaseIndex(分块索引)**

**ChunkCodeBaseIndex 核心原理：**是将代码文件按照智能分块策略切分成适合处理的代码片段，首先通过 `ShouldChunk` 函数过滤掉**超过 1 MB 的大文件和无扩展名文件**，然后使用** Tree-sitter 进行语法感知的代码分块（优先）或基础文本分块（降级）**，确保每个分块在指定的 token 限制内（默认 500 tokens），最终将这些**分块存储到 SQLite 数据库**中作为其他索引类型（全文搜索、向量搜索）的基础数据源。它是项目索引系统的基础层，为上层的语义搜索、关键词检索等功能提供了标准化的代码片段数据，同时通过智能分块**保持了代码的逻辑完整性和可读性**

##### **3.3.1.1 ChunkCodeBaseIndex 整体设计图如下：**
![[74a32fab-d5fc-46ef-9590-66a404d1a95d.png]]
##### 3.3.1.2 数据库表设计

chunkCodeBaseIndex 通过两张表支持存储数据，分别是**主表**** chunks**** 用于存储分块的核心数据，标签表 ****chunk_tags**** 用于存储分块与标签的关系**，一个分块可以有多个标签（相同内容在不同分支场景），一个标签可以关联多个分块（同一文件不同分块场景）。**通过事务机制保证主表与标签表插入的一致性**。

###### 为什么需要标签表？

chunk_tags 标签表的核心作用是**内容去重**与**缓存复用机制**。

|核心功能|应用场景|
|---|---|
|内容去重|核心机制：基于 cacheKey 的内容去重  <br>原理：相同内容的文件共享相同的 cacheKey，数据库中只存储一份 chunks 数据，通过 chunk_tags 实现多分支关联|
|缓存复用机制|场景：多分支切换时的性能优化、改变文件目录，文件内容不变化场景|

chunks 主表详细设计如下：

|字段名|数据类型|约束条件|业务含义|设计意图|
|---|---|---|---|---|
| `id` |INTEGER|PRIMARY KEY AUTOINCREMENT|分块唯一标识符|自增主键，确保每个分块的唯一性|
| `cacheKey` |TEXT|NOT NULL|文件内容 MD 5 哈希|**内容寻址机制**：相同内容文件共享缓存，实现去重优化  <br>例如：不同分支的相同文件，共享 cacheKey|
| `path` |TEXT|NOT NULL|完整文件路径|支持跨目录搜索和文件定位|
| `idx` |INTEGER|NOT NULL|分块序号|**顺序保持**：维护同文件内分块的逻辑顺序关系|
| `startLine` |INTEGER|NOT NULL|分块起始行号|**精确定位**：支持 IDE 级别的代码跳转和定位|
| `endLine` |INTEGER|NOT NULL|分块结束行号|**精确定位**：支持 IDE 级别的代码跳转和定位|
| `content` |TEXT|NOT NULL|分块实际内容|直接可用的搜索内容，避免重复文件读取|

chunk_tags 标签表详细设计如下：

|字段名|数据类型|约束条件|业务含义|设计意图|
|---|---|---|---|---|
| `id` |INTEGER|PRIMARY KEY AUTOINCREMENT|关联记录唯一标识|自增主键，标识每条关联关系|
| `tag` |TEXT|NOT NULL|标签字符串|分支/目录/模型等标识信息<br><br>格式为：`{directory}::{branch}::{artifactId}`<br><br>在 chunkCodeBaseIndex 场景下 `artifactId` 值固定为“chunks”<br><br>举例："/Users/dev/project/src::main::chunks"|
| `chunkId` |INTEGER|NOT NULL, FOREIGN KEY|关联的分块 ID|外键引用 chunks.id，建立关联关系|
|-|-|UNIQUE (tag, chunkId)|唯一约束|**防重复关联**：同一分块不能重复关联相同标签|

##### **3.3.1.3 文件分块核心逻辑**

###### **3.3.1.3.1** Tree-sitter 介绍

[Tree-sitter](https://tree-sitter.github.io/tree-sitter/) 是一种解析器生成工具和增量解析库。它可以为一个源文件构建一个具体语法树，并在源文件编辑时高效地更新语法树。Tree-sitter 的目标是：

- **足够通用**，可以解析任何编程语言
- **足够快速**，能够在文本编辑器的每个按键时进行解析
- **足够健壮**，即使在存在语法错误的情况下也能提供有用结果
- **无依赖性**，因此运行时库（用纯 C 编写）可以嵌入到任何应用程序中
###### 3.3.1.3.2 文件分块整体设计图
![[0c3346c1-cb62-43f3-bafc-cb0b9e8c74b8.png]]
###### 3.3.1.3.2 智能折叠策略实际应用场景解析
![[1b7145b4-2c5a-4cfc-af17-82c8bc0fd09b.png]]
##### **3.3.1.4 ChunkCodeBaseIndex 优劣势汇总**

**优势分析汇总**

|类别|具体表现|量化指标|业务影响|
|---|---|---|---|
|**性能优势**|智能代码分块提升检索精度|搜索速度提升 10-100 倍，内存使用减少 60-80%|用户获得更快速、更精确的代码搜索体验|
|并行文件处理优化构建速度|时间复杂度从 O(n)降至 O(1)|显著减少索引构建等待时间，提升开发效率|
|**架构优势**|作为其他索引类型的统一数据源|为 3+种索引类型提供标准化数据接口|确保多索引系统的数据一致性和协同工作|
|事务性批量操作保证数据完整性|原子性操作，0%数据不一致风险|提供可靠的数据存储和索引构建保障|
|**存储优势**|内容去重机制节省存储空间|节省 60-80%存储空间，多分支项目存储效率提升 3-5 倍|降低服务器存储成本，支持更大规模项目|
|缓存复用实现快速分支切换|分支切换从 2-10 分钟降至 1-3 秒，性能提升 100-200 倍|消除分支切换等待时间，支持敏捷开发流程|
|**扩展优势**|灵活的多分支索引管理|支持无限数量分支，增量添加时间复杂度 O(1)|完美支持 Git 工作流和多分支并行开发|
|多目录过滤和标签系统|支持任意目录组合，标签关联查询性能稳定|适应复杂项目结构和个性化索引需求|

**劣势分析汇总**

|类别|具体表现|量化指标|业务影响|
|---|---|---|---|
|**功能限制**|大文件处理的硬性阈值限制|1 MB 以上文件被完全跳过|用户可能错过重要代码引用，AI 理解能力受限|
|**依赖风险**|其他索引对 ChunkCodebaseIndex 强依赖|3+种索引类型完全依赖，单点故障风险 100%|基础索引失败会导致整个搜索系统不可用|
|**复杂性成本**|数据一致性维护挑战|需要维护 2 个表的一致性，错误排查难度提升 50%|增加系统维护复杂度和故障诊断时间|

#### 3.3.2 **CodeSnippetsCodeBaseIndex**

**CodeSnippetsCodeBaseIndex 核心原理：**是利用 Tree-sitter 语法解析器将代码文件解析成**抽象语法树（AST）**，然后通过语言特定的 `.scm` 查询模式**从 AST 中精确提取函数、类、方法等结构化代码元素，并保存其签名信息和精确位置**，从而实现语义级别的代码理解和符号导航。与其他基于文本分块的索引不同，它直接理解代码的语法结构，**不受文件大小限制**，**能够为 AI 代码助手提供精确的符号定位、代码结构分析和智能导航能力**

##### **3.3.2.1 CodeSnippetsCodeBaseIndex 整体设计图**
![[5e570feb-485c-463a-8b44-91df744ea1d3.png]]
##### **3.3.2.3 .scm 查询模式详细方案**

###### .scm 查询模式结构及作用是什么？

.scm 查询模式的作用：结合 AST 树结构，精确匹配提取出当前语言代码中包含的**方法节点、类节点、函数节点、接口/枚举**等提取

.scm 查询模式的结构：
```
; 类定义查询
(
  (comment)? @comment
  (class_declaration
    name: (_) @name
  ) @definition
)

; 函数定义查询
(
  (comment)? @comment
  (function_declaration
    name: (_) @name
    parameters: (_) @parameters
  ) @definition
)

; 方法定义查询
(
  (comment)? @comment
  (method_definition
    name: (_) @name
    parameters: (_) @parameters
  ) @definition
)

; 接口定义查询
(
  (comment)? @comment
  (interface_declaration
    name: (_) @name) @definition
)
```

.scm 匹配 AST 树示例，以 typescript 为示例
```
// 源代码
async function getUserById(id: string): Promise<User> {
  return await userService.findById(id);
}

// 对应的AST结构
function_declaration {
  "async"
  name: identifier { "getUserById" }
  parameters: formal_parameters {
    required_parameter {
      pattern: identifier { "id" }
      type: type_annotation {
        predefined_type { "string" }
      }
    }
  }
  return_type: type_annotation {
    generic_type {
      name: identifier { "Promise" }
      type_arguments: type_arguments {
        predefined_type { "User" }
      }
    }
  }
  body: statement_block { ... }
}
```

```
;; 查询模式
(function_declaration
  name: (identifier) @function.name
  parameters: (formal_parameters) @function.params
  body: (statement_block) @function.body
) @function.definition

;; 匹配结果
@function.name -> "getUserById"
@function.params -> "(id: string)"
@function.body -> "{ return await userService.findById(id); }"
@function.definition -> 整个函数声明节点
```

###### .scm查询模式相对传统正则表达式的差异是什么？

|维度|.scm查询模式|传统正则表达式|
|---|---|---|
|**语法结构**|声明式语法，基于AST节点结构|字符串模式匹配，基于文本特征|
|**可读性**|高（语法树结构清晰）|低（复杂正则难以理解）|
|**准确性**|基于语法分析，语法级别精确匹配|基于文本匹配，文本级别模糊匹配|
#### **3.3.3 FullTextSearchCodeBaseIndex（全文索引）**

**FullTextSearchCodeBaseIndex 的核心原理：**是**基于 SQLite 的 FTS 5 全文搜索引擎**，依赖 `ChunkCodebaseIndex` 提供的代码分块数据，通过 **trigram 分词技术**将代码内容构建成倒排索引，并使用** BM 25 算法进行相关性评分和排序**。它对用户查询进行 **NLP 预处理**（词干提取、停用词移除、三元组生成），然后在 FTS 索引中执行高效的关键词匹配，能够快速定位包含特定关键词的代码片段，**为项目提供传统而可靠的精确文本搜索能力，是语义搜索的重要补充**，**特别适合查找具体的 API 名称、变量名或代码片段**

##### 3.3.3.3 **trigram 分词**

**trigram** 是一种文本分词技术，特别适用于全文搜索引擎，**核心原理是将一行代码从头到尾每三个字符组成一个词语**
```
// Trigram分词示例
const text = "getUserById";

// 传统的trigram分词过程：
const trigrams = [
  "get",  // 位置0-2
  "etU",  // 位置1-3  
  "tUs",  // 位置2-4
  "Use",  // 位置3-5
  "ser",  // 位置4-6
  "erB",  // 位置5-7
  "rBy",  // 位置6-8
  "ByI",  // 位置7-9
  "yId"   // 位置8-10
];
```

```
// 分词匹配过程示例 

const searchExamples = {
  // 用户搜索: "getUser"
  query: "getUser",
  queryTrigrams: ["get", "etU", "tUs", "Use", "ser"],
  
  // 候选文档: "getUserById"  
  documentTrigrams: ["get", "etU", "tUs", "Use", "ser", "erB", "rBy", "ByI", "yId"],
  
  // 匹配结果: 5个trigram匹配
  matches: ["get", "etU", "tUs", "Use", "ser"],
  matchScore: 5/5, // 100%匹配
  
  result: "成功匹配，即使查询词不完整"
};
```

**trigram与传统的分词思路（即单个词语作为一个分词）对比**

|特性|传统单词分词|Trigram分词|
|---|---|---|
|**索引大小**|小|大（约2-3倍）|
|**查询速度**|快|中等|
|**匹配精度**|高（精确匹配）|中等（模糊匹配）|
|**容错能力**|无|强|
|**部分匹配**|不支持|支持|
|**CamelCase**|需要特殊处理|自然支持|
##### 3.3.3.4 **BM 25 算法**

**BM 25（维基百科）也被称为** `**Okapi BM25**` **，是一种用于信息检索系统的排序函数，用于估计文档与给定搜索查询的相关性**，是由英国一批信息检索领域的计算机科学家开发的排序算法。这里的“BM”是“最佳匹配”（Best Match）的简称。

那么 BM 25 是怎么定义的呢？可参考相关文档：[34 032 | 经典搜索核心算法：BM25及其变种（内附全年目录）](https://km.sankuai.com/page/473232426)、[0 BM25](https://km.sankuai.com/page/686885381)。一般来说，**经典的 BM 25 分为三个部分**：

1. **单词和目标文档的相关性**
    
2. **单词和查询关键词的相关性**
    
3. **单词的权重部分**
##### 3.3.3.5 **倒排索引技术**

倒排索引（Inverted Index）是一种索引数据结构，它存储了从内容中的每个唯一词项到包含该词项的文档列表的映射关系。相关文档可见：[正排索引与倒排索引](https://km.sankuai.com/collabpage/1360298601#b-0e70118ef74f4bd38a886ebcc13bae9b)、[8 06 | 如何用Elasticsearch构建商品搜索系统？](https://km.sankuai.com/page/471611579)

- **正常思维**：从文档找词项（我有这个文档，它包含哪些词？）
    
- **倒排思维**：从词项找文档（我要找这个词，哪些文档包含它？）
```
// 正向索引：文档 → 词项列表
const forwardIndex = {
  doc1: ["function", "getUserById", "return", "user"],
  doc2: ["class", "UserService", "getUserById", "method"],
  doc3: ["interface", "User", "properties", "methods"]
};

// 倒排索引：词项 → 文档列表  
const invertedIndex = {
  "function": [doc1],
  "getUserById": [doc1, doc2],
  "class": [doc2],
  "UserService": [doc2],
  "interface": [doc3],
  "User": [doc3]
};
```

#### **3.3.4 LanceDbIndex（向量索引）**
**LanceDbIndex 的核心原理**:是将代码分块通过嵌入模型转换为高维向量并**存储在 LanceDB 中，同时在 SQLite 中保存元数据**，通过向量相似度搜索实现语义级别的代码理解和检索，为 AI 代码助手提供超越关键词匹配的智能语义搜索能力

**具备以下核心技术优势  
1. 双重存储架构：LanceDB 高效向量搜索，SQLite 结构化元数据，UUID 精确数据关联，确保数据一致性
2. 语义理解能力：概念级别匹配，上下文相关性，模式识别能力，意图理解
3. ![[1628ccde-4489-4129-ba92-5dd6becf6112.png]]
##### 3.3.4.1 向量检索整体设计图
![[6507d842-f929-4992-9a76-6a729d2ceafa.png]]
### 3.4 检索增强
![[a19bd6de-b6ba-41d8-b09d-59a47b02ff48.png]]
#### 3.4.1 RepoMap 智能选择详细方案
![[80ccf428-4f8c-49ff-ab76-7f8c97eb4448.png]]