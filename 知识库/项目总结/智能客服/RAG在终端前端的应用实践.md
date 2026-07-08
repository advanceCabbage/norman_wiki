# 一、背景

RAG（**Retrieval-Augmented Generation，检索增强生成**）是由 Meta 团队于 2020 年提出的融合检索与生成的技术方法。其核心机制是让大语言模型在生成回答前，先从外部文档库检索相关信息作为依据，从而提升回答准确性。随着 2022 年后大模型时代的到来，该方法使得无需重新训练整个模型，仅通过附加知识库即可增强模型性能，成为提升 LLM 准确性的重要解决方案。在 AI 技术快速发展的背景下，终端平台亟需应对研发效率低下、人力短缺、答疑成本和技术栈限制等核心挑战，构建基于 RAG 的知识库成为关键解决方案。

# 二、目标

通过构建 MTD RAG 与 MSI RAG 实现以下目标：

1. **提升开发效率** ：借助 MTD RAG 技术，在 25 个系统内自动生成符合美团 UI 规范的代码，减少人工编码的时间和复杂度
    
2. **统一技术栈** ：通过 RAG 将监控的 MTD-Vue 组件转换为 MTD-React 组件，实现技术栈的无缝迁移，约提升 30%开发效率，具体实践可参考[基于 Cursor 进行 Vue 2 React 转换实践](https://km.sankuai.com/collabpage/2708552510)
    
3. **降低客服成本** ：通过 MSI 智能机器人优化客服流程，利用 RAG 技术大幅提升问题解决效率，从而降低客服运营成本，近两周数据统计显示平均 4 人/日，日均咨询 6~7 次智能客服
    
4. **降低业务接入成本** ：借助 MSI MCP，结合 RAG 的能力简化业务接入流程，减少业务使用 MSI 的成本投入，据不完全统计已有三个以上业务方在使用 MSI MCP
    

# 三、技术方案

## 3.1 知识库设计方案

一个完整的知识库由知识库构建阶段（完成文档向量化存储）和检索增强阶段（实现上下文感知生成）两部分组成，从而形成完整的检索-生成闭环系统

- **知识库构建阶段**：对知识库文档进行解析、拆分、索引构建和入库。这部分会从用户给定的文档、图片、表格和外部 URL 等资源中提取内容，然后通过 chunking（可以认为是将连续的文本分成一个个小块）进行合理切割，再使用 Embedding 模型变成向量数据存入向量数据库或 Elasticsearch 等载体中
    

- **检索增强阶段**：当用户输入问题之后，会对 query 进行分析，如关键词提取、意图识别等，然后再根据不同的检索策略进行知识库的多种召回检索等。如果是做向量数据库的检索，会先将查询内容通过 Embedding 模型转化为向量数据，接着在向量数据库中进行相似度匹配，比如从百万的数据块中找出匹配度较高的 100 个，然后再将这 100 个数据块进行更精准的重排序（如使用 [RRF（Reciprocal Rank Fusion）](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)），将最相关的 top k 结果找到，最后将用户问题，经过技术处理的 top k 数据块，还有 prompt 一起提交给 LLM，让它生成最终可靠的答案![[6856f498-a217-4281-9d57-e42950dcf52f.png]]
## 3.2 知识库构建阶段

知识库构建阶段包括**源文档优化、文本分割、向量化模型选择、相似度策略选择和入库**等模块，旨在将源文档转化为结构化、可检索的知识单元，为知识查询和智能应用提供高质量数据基础。该阶段通过文档清洗与优化确保数据准确性，通过文本分割生成语义片段，利用向量化模型实现文本数值化，并通过相似度测量实现精准匹配。最终，处理后的知识单元存储于知识库中，形成高效、可扩展的管理系统，为问答系统、智能推荐、语义搜索等应用提供支持

#### 3.2.1 源文档优化

在知识库检索环节中，源文档质量和结构是决定最终效果好坏的重要因素之一，以下是我们对源文档做的一些优化：

1. **文档 AI 友好化：**MTD-RAG 场景下需要借助 AI 生成代码能力，因此我们对 MTD 文档添加对 AI 友好的注释，帮助 AI 更好地理解
2. **摘要总结**：利用大模型能力对MTD组件能力进行摘要总结并涵盖使用场景，对MSI API功能总结涵盖入参、返参信息进一步完善功能描述，增加检索命中率

| 文档优化前                                                    | 文档优化后                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| getLocation 属于位置模块，getLocation 的功能是：获取当前的地理位置、速度。以及逆地理信息 | getLocation 属于位置模块，getLocation 的功能是：获取当前的地理位置、速度。以及逆地理信息<br> |


#### 3.2.2 文本分割

文本分割（text splitting）**，**或称为文本分块（text chunking），是指将长文本分解为较小的文本块，这些块会被 Embedding、索引、存储，用于后续的数据检索。通过将大型文档分解成易于管理的部分（如章节、段落，甚至是句子），可以提高搜索准确性和 LLM 处理性能，主要体现如下

- **提高搜索准确性**：较小的文本块允许更精确的关键词匹配和语义相似性检索
    
- **提升模型性能**：LLM 处理长文本时可能性能受限，通过将文本分割为较小片段并逐一检索后输入模型，可提升处理效率和理解准确性，从而提高查询结果的精确度
    
- **优化计算资源**：使用更小的文本块可以提高内存效率，并允许更好地并行化处理任务
    

**以下介绍常用的文本分割策略，以及策略适用场景与优劣势**

|策略类型|策略描述|策略优势|适用场景|是否采用|
|---|---|---|---|---|
|**Length-based**  <br>**(基于长度)**|Token-based（基于 Token）：根据 **Token 数量**分割文本<br><br>Character-based（基于字符）：根据**字符数量**分割文本（目前公司内部平台例如 SalesMind、Friday 均支持 **1000 字符长度**以内的自定义分割）|优势：实现直接、一致的块大小<br><br>劣势：未考虑语义内容，可能**导致相关联的信息被分割开**，例如：整段函数代码或完整的句子被截断在不同的块中|- **适合格式：** 简单的纯文本文档，尤其是没有复杂结构或语义关联的文档。<br>    <br>- **不适合格式：** 包含长句、代码片段或需要保持语义连贯性的文档||
|**Document-structured based**  <br>**(基于文档结构)**|具有**固有的结构的文档**，例如 HTML、Markdown 或 JSON 文件<br><br>例如：Markdown 文本可以使用标题（#）、列表（-）等来进行分块|优势：保证分块后的内容在结构上的完整性和逻辑性连贯<br><br>劣势：在公司内部平台例如 SalesMind、Friday 均受限于最大 **1000 字符长度限制**<br><br>我们实际使用中遇到的问题<br><br>​ ![image.png](https://km.sankuai.com/api/file/cdn/2709576823/162173853151?contentType=1&isNewContent=false)<br><br>按照文档结构切割文本，出现回答某个 API 信息时，检索出来的 API 信息只有其中一部分。举个例子：问 getLocation 的用法，回答时缺失部分字段，原因是**丢失的字段因字符长度限制被分割到其余的块中**，并未被检索返回<br><br>  <br>使用**双通道索引架构**处理文档之后的效果<br><br>![image.png](https://km.sankuai.com/api/file/cdn/2709576823/162172309772?contentType=1&isNewContent=false) |- **适合格式：** 结构化的文档，如 Markdown、HTML、JSON 等，这些文档本身具有明确的结构标记（如标题、列表、段落等）。<br>    <br>- **不适合格式：** 长篇连续文本或缺乏明显结构标记的文档|​采用|
|**Semantic meaning based**  <br>**(语义意义基础)**|基于语义的分割实际上考虑了文本的内容。而其他方法使用文档或文本结构作为语义意义的代理，这种方法则**直接分析文本的语义**。实现方式有多种，但概念上是**在文本意义发生显著变化时进行分割**。<br><br>例如：<br><br>[Percentile](https://python.langchain.com/docs/how_to/semantic-chunker/#percentile)，计算句子之间的所有差异，然后任何大于 X 百分位数的差异都会进行分割<br><br>[Standard Deviation](https://python.langchain.com/docs/how_to/semantic-chunker/#standard-deviation)，任何大于 X 个标准差的差异将被分割|优势：有助于创建更具语义连贯性的块，可能提高检索或摘要等下游任务的质量<br><br>劣势：目前公司内部知识库平台均未支持语义分块能力，Friday 平台将在后续计划支持，具体时间点未敲定。SalesMind 平台无支持计划|- **适合格式：** 需要保持语义连贯性的文档，如长篇连续文本、新闻文章、学术论文等。<br>    <br>- **不适合格式：** 简单的结构化文档或短文本，因为语义分析的成本较高且目前技术支持有限||
|**Dual-Channel Indexing**<br><br>**(双通道索引架构)**|也可称为 Q&A 架构，对 Question 进行向量化，Answer 用作普通存储，Q 和 A 之间建立索引关系。向量检索匹配到 Q 时，同时将 A 一起返回|优势：Answer 内容不会被切割，也不会参与向量化。利于成本节省适合组件库、API、代码块等场景使用<br><br>劣势：对 Answer 内容总结要求高，否则检索质量会急速下降<br><br>我们在实际使用中遇到的问题简述<br><br>问题描述：咨询某个功能应该使用哪个 API 时，未准确回答出准确的组件。举个例子：问我期望获取当前位置的经纬度，应该用哪个 API？回答时未准确检索到 Location API。<br><br>原因描述：getLocation 优化前的描述为“获取当前的地理位置、速度。以及逆地理信息”未包含对经纬度的描述<br><br>优化后的 Question：“该 API 用于获取当前地理位置、速度和逆地理信息。可以通过调用 API 来实现单次定位，也可以使用持续定位接口 `msi.onLocationChange`。主要参数包括坐标类型（`type`，可选 `wgs84` 或 `gcj02`）、美团独有信息（`_mt`），以及成功与失败的回调函数。API 返回的核心参数包含：纬度（`latitude`）、经度（`longitude`）、速度（`speed`）、精度（`accuracy`）、高度（`altitude`）、垂直精度（`verticalAccuracy`）、水平精度（`horizontalAccuracy`）、定位来源（`provider`）和获取时间戳（`mtTimestamp`）。此外，返回的美团信息可能包含详细地址、城市、县区等信息。”|- **适合格式：** Q&A 形式的文档，如 FAQ、知识库问答、代码片段说明等。<br>    <br>- **不适合格式：** 非问答形式的连续文本或结构化文档。|​采用|
除了上面所说的文本分割策略，还有很多其他的分割策略，比如：递归字符文本分割，还有使用 NLTK 分割器的 NLTKTextSplitter 等。**文本分割并没有固定的最佳策略，选择哪种方式取决于具体的需求和场景，需要根据业务情况进行调整和优化**


#### 3.2.3 向量化模型

> Friday 平台采用自研 embedding 模型，不支持用户选择。SalesMind 支持 [Friday模式广场](https://aigc.sankuai.com/ml/modelPlaza?searchValue=LongCat)上所有文本 embedding 模型，Friday 平台支持的向量模型有限仅支持 6 种 embedding 模型

**Embedding 的本质是一种将高维稀疏数据转换为计算机易于处理的低维稠密向量的技术，通过这种转换，能够捕捉数据中的语义或特征关系**。具体来说，Embedding 用一个多维稠密向量来表示事物的多维特征，从而在一个连续的向量空间中刻画事物之间的相似性和差异性。以下是 Friday 平台支持的 6 种 embedding 模型

|维度高低|优势|劣势|
|---|---|---|
|高维度|表达能力强、区分度高、支持复杂语义关系|计算资源需求高、过拟合风险、稀疏性问题|
|低维度|计算效率高、硬件要求低、适合小规模数据|表达能力有限、区分度不足、易受语义冲突影响|
在当前场景下，我们更加关注检索的准确性，因此牺牲了部分性能，选择了更多维度的 **text-embedding-3-large** 向量模型

|公司|向量模型|向量维度|是否采用|
|---|---|---|---|
|Open AI|**text-embedding-3-small**|1536||
|**text-embedding-3-large**|3072|​采用|
|**text-embedding-ada-002**|1536||
|百川|**Baichuan-Text-Embedding**|1024||
|美团自研|**text-embedding-miffy-002**|768||
|Minmax|**embo-01**|768~1536||
#### 3.2.4 测量相似度

|向量相似度度量类型|描述|适用场景|是否采用|
|---|---|---|---|
|**Cosine Similarity（**余弦相似度**）**|衡量两个向量之间角度的余弦值|主要用于衡量两个向量在方向上的相似性，而不考虑向量的实际长度。**适用于文本数据处理，如文档相似性计算和文本分类**|​采用|
|**Euclidean Distance（**欧几里得距离**）**|衡量两点之间的直线距离|用于计算点之间的线性距离，适合需要考虑向量之间绝对差距的场景，如**图像处理和聚类分析**||
|**Dot Product（**点积相似度**）**|衡量一个向量在另一个向量上的投影|指两个向量之间的点积值。优点在于它简单易懂，计算速度快，并且兼顾了向量的长度和方向。**适用于图像识别、****语义搜索和文档分类等**。||
## 3.3 知识库检索增强

#### 3.3.1 问题分析增强

知识库检索增强环节对用户的 query 进行理解是一个重要步骤，这一步也叫做问题分析增强。问题分析增强指的是对用户提出的问题进行深入分析，提取出关键信息，从而更准确地从知识库中检索出与用户查询最相关的信息，进而生成高质量的回答。问题分析增强的核心原理是：利用大模型将原始用户查询转换为更有效的搜索查询，这种转换可以**从简单的关键词提取到复杂的查询扩展和重构**。以下是各种策略的详细描述

|策略名称|概念|适用场景|是否采用|
|---|---|---|---|
|[**MultiQueryRetriever**](https://python.langchain.com/docs/how_to/MultiQueryRetriever/)**(多查询)**|MultiQueryRetriever 是一种通过生成多种视角的查询来检索相关文档的方法。它使用LLM从用户输入的查询生成多个不同的查询视角，然后为每个查询检索一组相关文档，并合并这些结果以获得更全面的文档集合|当期望通过提供问题的多种表述来确保检索的高召回率<br><br>```<br>QUERY_PROMPT = PromptTemplate(<br>    input_variables=["question"],<br>    template="""You are an AI language model assistant. Your task is to generate five <br>    different versions of the given user question to retrieve relevant documents from a vector <br>    database. By generating multiple perspectives on the user question, your goal is to help<br>    the user overcome some of the limitations of the distance-based similarity search. <br>    Provide these alternative questions separated by newlines.<br>    Original question: {question}""",<br>)<br>llm = ChatOpenAI(temperature=0)<br>```||
|[**Decomposition**](https://github.com/langchain-ai/rag-from-scratch/blob/main/rag_from_scratch_5_to_9.ipynb)**(分解)**|将一个问题分解成一系列更简单的子问题，这些子问题可以依次解决（使用第一个问题的答案+检索来回答第二个问题）或并行解决（将每个答案整合成最终答案）|当期望问题可以被分解成更小的子问题<br><br>```<br>from langchain.prompts import ChatPromptTemplate<br><br># Decomposition<br>template = """You are a helpful assistant that generates multiple sub-questions related to an input question. \n<br>The goal is to break down the input into a set of sub-problems / sub-questions that can be answers in isolation. \n<br>Generate multiple search queries related to: {question} \n<br>Output (3 queries):"""<br>prompt_decomposition = ChatPromptTemplate.from_template(template)<br>```||
|**[Step-back](https://github.com/langchain-ai/rag-from-scratch/blob/main/rag_from_scratch_5_to_9.ipynb)(后退)**|提高LLM进行抽象推理的能力，它引导LLM在回答问题前进行深度思考和抽象处理，将复杂问题分解为更高层次的问题，其包含如下两个主要步骤。<br><br>1. **抽象（Abstraction）**：不是直接针对问题进行回答，而是首先促使LLM提出一个更高级别的「回溯问题」（step-back question），这个问题涉及更广泛的高级概念或原则，并检索与这些概念或原则相关的相关事实。<br>    <br>2. **推理（Reasoning）**：在高级概念或原则的基础上，利用语言模型的内在推理能力，对原始问题进行推理解答，这种方法被称为基于抽象的推理（Abstraction-grounded Reasoning）<br>    <br><br>举个例子<br><br>输入：警察可以合法逮捕吗？<br><br>输出：警察可以做什么？<br><br>输入：Jan Sindel 出生在哪个国家？<br><br>输出：Jan Sindel 的个人经历是什么？|当需要更高层次的概念理解时<br><br>```<br># Few Shot Examples<br>from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate<br>examples = [<br>    {<br>        "input": "Could the members of The Police perform lawful arrests?",<br>        "output": "what can the members of The Police do?",<br>    },<br>    {<br>        "input": "Jan Sindel’s was born in what country?",<br>        "output": "what is Jan Sindel’s personal history?",<br>    },<br>]<br># We now transform these to example messages<br>example_prompt = ChatPromptTemplate.from_messages(<br>    [<br>        ("human", "{input}"),<br>        ("ai", "{output}"),<br>    ]<br>)<br>few_shot_prompt = FewShotChatMessagePromptTemplate(<br>    example_prompt=example_prompt,<br>    examples=examples,<br>)<br>prompt = ChatPromptTemplate.from_messages(<br>    [<br>        (<br>            "system",<br>            """You are an expert at world knowledge. <br>            Your task is to step back and paraphrase a question to a more generic step-back question, <br>            which is easier to answer. Here are a few examples:""",<br>        ),<br>        # Few shot examples<br>        few_shot_prompt,<br>        # New question<br>        ("user", "{question}"),<br>    ]<br>)<br>```||
|**[hypothetical_document_embeddings](https://github.com/langchain-ai/rag-from-scratch/blob/main/rag_from_scratch_5_to_9.ipynb)**  <br>**(假设文档嵌入)**|首先，HyDE针对query直接生成一个假设性文档或者回答（hypo_doc），接着对这个假设性回答进行向量化处理，与文档共享更相似的语义空间，最后使用向量化的假设性回答作为context，以文档相似度搜索去检索相似文档|当在使用原始用户输入检索相关文档时遇到挑战，query和doc不在同一个语义空间。此时直接将query和doc向量化，再基于向量相似性来检索，检索的精度有限而且噪声比较大<br><br>```<br># HyDE document genration<br>template = """Please write a scientific paper passage to answer the question<br>Question: {question}<br>Passage:"""<br>prompt_hyde = ChatPromptTemplate.from_template(template)<br>generate_docs_for_retrieval = (<br>    prompt_hyde \| ChatOpenAI(temperature=0) \| StrOutputParser() <br>)<br><br># Run<br>question = "What is task decomposition for LLM agents?"<br>generate_docs_for_retrieval.invoke({"question":question})<br><br># Retrieve<br>retrieval_chain = generate_docs_for_retrieval \| retriever <br>retireved_docs = retrieval_chain.invoke({"question":question})<br>retireved_docs<br><br># RAG<br>template = """Answer the following question based on this context:<br><br>{context}<br><br>Question: {question}<br>"""<br><br>prompt = ChatPromptTemplate.from_template(template)<br><br>final_rag_chain = (<br>    prompt<br>    \| llm<br>    \| StrOutputParser()<br>)<br><br>final_rag_chain.invoke({"context":retireved_docs,"question":question})<br>```||
除了上面所说的问题分析增强策略之外，还有 RAG-Fusion、query 分解-IR-CoT 等策略，具体策略选择还需结合业务实际情况进行抉择。然而，在实际应用中，我们选择了一种更加直接且高效的策略：**基于 MTD 组件库的使用场景总结，结合大模型的能力进行问题扩展和组件推荐** 。我们通过以下步骤实现问题分析增强
- **MTD 组件库的使用场景总结** ：
    
    - 首先，我们将 MTD 组件库中的各个组件的使用场景进行了全面的梳理和总结。这些使用场景包括但不限于：
        
        - 组件的功能描述
            
        - 组件的适用范围和典型应用场景
            
        - 组件的常见用法
- **大模型驱动的上下文扩展** ：
	- 在接收到用户的问题后，我们将 MTD 组件库的使用场景作为上下文（context），并将其与用户的问题一起输入到大模型中
	 - 大模型的任务是根据上下文内容，判断用户问题并返回可能涉及的组件
- **组件推荐与答案生成** ：
	- 基于大模型的输出，检索知识库获取组件详细信息

#### 3.3.2 检索生成
| 策略名称                                       | 策略描述                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 策略实现方式                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 是否采用 |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| **Ensemble**(集合)                           | **通过集成方法组合多个检索器，**例如同时检索向量数据库、词汇索引数据库，结合多个检索器的搜索结果，使用**[RRF（相互排名融合）](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)**算法来重排。<br><br>RRF（Reciprocal Rank Fusion）的特点<br><br>1. **简单性和高效性** ：<br>    <br>    - RRF的核心思想非常简单：对于每个文档，计算其在所有排名列表中的“互惠排名”分数，并将这些分数相加。<br>        <br>    - 互惠排名分数定义为 _r_+_k_1​，其中 _r_ 是文档在某个列表中的排名，_k_ 是一个常数（通常取值为60）。<br>        <br>    - 这种方法不需要对排名列表进行复杂的重新排序或调整，计算成本低，适合处理大规模数据。<br>        <br>2. **鲁棒性** ：<br>    <br>    - RRF对噪声和不一致的排名列表具有较强的鲁棒性。即使某些列表的质量较差，RRF仍然能够生成合理的合并结果。<br>        <br>    - 它不会过度依赖任何一个列表，而是通过综合多个列表的信息来平衡结果。<br>        <br>3. **无需训练或参数调整** ：<br>    <br>    - RRF不需要任何训练数据或复杂的参数调优。它仅依赖于排名位置，因此适用于各种场景，尤其是当不同来源的排名机制差异较大时。<br>        <br>4. **公平性** ：<br>    <br>    - RRF对所有输入列表一视同仁，没有偏向性。它假设每个列表提供的信息都有一定的价值，从而避免了对某些列表的过度依赖。<br>        <br>5. **适用范围广** ：<br>    <br>    - RRF不仅适用于联邦搜索（federated search），还可以用于其他需要合并多个排名列表的任务，如推荐系统、多模型集成等。 | 1. Langchain支持RRF算法，详情可见[结合多个检索器的结果示例](https://python.langchain.com/docs/how_to/ensemble_retriever/)<br>    <br><br>```<br>from langchain.retrievers import EnsembleRetriever<br><br>ensemble_retriever = EnsembleRetriever(<br>    retrievers=[bm25_retriever, vector_store_retriever], weights=[0.5, 0.5]<br>)<br>```<br><br>2. 公司内部平台SalesMind支持Ensemble策略和RRF算法，在RAG检索生成上我们选用了混合检索+RRF算法<br><br>点击展开内容<br><br>![image.png](https://km.sankuai.com/api/file/cdn/2709576823/162028552578?contentType=1&isNewContent=false) | ​采用  |
| **Source Document Retention**  <br>(源文档保留) | **使检索器能够返回原始文档，确保模型不会丢失文档的上下文**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 1. [**ParentDocument（父文档）**](https://python.langchain.com/docs/how_to/parent_document_retriever/)：将父文档拆分成多个子文档或将父文档内容总结为单个/多个子文档，子文档是检索的基础。子文档与父文档之间存在映射关系，确保检索到的子文档能够追溯到其对应的父文档。采用**双通道索引架构**，只需对子文档做向量存储，并存储子文档与父文档之间的映射关系。**我们在MTD组件和MSI API的存储上均是采取该模式**<br>    <br>2. **[Multi Vector（多向量）](https://python.langchain.com/docs/how_to/multi_vector/)：**每个文档会被分割成多个片段（chunks），或者从不同角度提取特征，为每个片段或特征生成独立的向量表示，向量之间通过元数据（metadata）关联，确保可以追溯到原始文档（多向量策略与父文档策略相似，鉴于使用时在相对较复杂，暂不推荐）<br>                                         | ​采用  |
|                                            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |      |

#### 3.3.3 检索结果优化
![[412e6f51-9e21-436c-a2e0-3a1727ece8ff.png]]

设置文档评分器，借助大模型能力，过滤出与问题相关的检索文档。评估规则：**将检索结果依次作为上下文并传入用户问题，利用大模型判断当前检索内容是否能解答用户问题，能则判定为相关**

文档评分器能很好过滤出不相关文档，提升解答问题质量。然而，基于 MTD 组件库的特点，我们发现通过设置知识库返回文章的**相关性阈值** ，同样能够高效地过滤掉不相关的文章。这种方法不仅简化了流程，还避免了因调用大模型进行逐条评估而带来的额外耗时问题。考虑到大模型调用的成本和性能开销，在最终方案中，我们选择了通过**设定阈值** 的方式来实现文档过滤。这种方式在实际应用中表现优异，既保证了检索结果的相关性，又显著提升了系统的响应速度和效率。因此，在最终形态中，我们去掉了文档评分器，转而依赖于更加轻量化的阈值过滤机制，达到了同样的目标，同时优化了整体性能

