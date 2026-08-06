开源平替产品：https://github.com/langfuse/langfuse

## 一、LangSmith 有哪些功能
##### 1.1 可观测性
- **Tracing** （追踪） ：**一次请求的完整执行记录**，包括 LLM、工具、检索每一步的输入、输出、token、耗时等数据，用于排查和复盘
- **Threads**（会话线程）：**把同一多轮对话的多条 trace 串成一个线程来看**，可以通过 session_id、thread_id 或 conversation_id 关联多条 Trace
- **Dashboards**（监控看板）：把追踪数据聚合成随时间的趋势图（请求量、错误率、延迟分位、token/成本、反馈）
- **Insights**（洞察）：自动对流量做聚类分析，发现高频问题/模式，**<font color="#c0504d">付费功能</font>**

##### 1.2 评估与质量
- **Datasets & Experiments（数据集与实验）**：Dataset 是可重复使用的测试样本集合；Experiment 是让某一版目标程序跑完整个数据集后形成的一组结果
- **Evaluators（评估器）**：配置自动打分（LLM-as-judge / 规则），规模化衡量输出质量
- **Annotation Queues（标注队列）**：把 trace 推给人工打分/标注，产出高质量评估数据
- **Feedback / Scores（反馈评分）**：给单条 run 打 👍/👎 或数值分，作为质量信号

##### 1.3 Prompt 工程
- **Prompts（提示词管理）**：版本化管理、对比、复用 prompt
- **Playground（试验场）**：界面里直接改 prompt/模型/参数试跑，快速迭代

一句话概括：**LangSmith = 可观测性（Tracing/监控）+ 评估（数据集/评估器/标注）+ Prompt 迭代（管理/Playground）+ 运行部署（Studio/Deployments/网关）** 的一站式 LLM 应用工程平台
## 二、一条可审计的改进链
1. **Tracing 定位**。 查看失败 Trace，确认模型没有选择线路查询工具，而不是工具调用失败
2. **形成 Dataset**。 把代表性失败 Trace 加入数据集，补充输入、期望工具选择、参考处理结果和场景元数据
3. **设计 Evaluator**。 用代码检查工具名和参数；用人工或经过校准的 LLM-as-Judge 评价最终建议是否充分
4. **运行 Experiment**。 在同一数据集上比较旧 Prompt、新 Prompt、不同模型或工具描述，并同时观察准确率、格式、延迟和成本
5. **通过质量门禁**。 只有关键指标满足阈值且没有明显回归，才把 Prompt Commit 提升到 staging，再提升到 production
6. **线上验证**。 对新的生产 Trace 进行采样和无参考评测，设置错误率、延迟、成本或 Feedback 告警，再把新发现的失败样本送回 Datase
这个闭环的价值不在于“平台自动优化了 Agent”，而在于每次改变都有证据链：失败 Trace、Dataset Example、Experiment、Evaluator 结果、Prompt Commit、Deployment Revision 和新生产 Trace 可以被明确关联 
