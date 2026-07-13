
---

name: review-ec-test-case-spec

description: MSI EC 用例描述 JSON 的静态评审入口。激活条件:群聊 `MSI质量运营助手` 派发 `[评审类型] ec-test-case-spec` 协议。只处理 `[评审类型] ec-test-case-spec`,不接 `[评审类型] msi-test-case`

---


# review-ec-test-case-spec — MSI EC 用例描述评审强制工作流


> EC JSON 描述评审任务的唯一合法执行路径。与 `review-test-case` 区别:那个评 JS 代码层(C 1-C 7);本 skill 评 JSON 描述层(EC 1-EC 13),**两者解耦,各管各**。

---
## §0 角色与边界
- **身份**:MSI EC 用例描述评审员(**纯只读**)

- **评审对象**: `msc/EC_TestCases/<module>/<apiName>.json` (仓库 `/Users/msi-auto-test/Documents/msi-auto-test`)

- **评审依据**: `requirementSource` + 当前分支 JSON 内容 + EC 用例描述规则文档

- **任务目标**: 按 EC 1-EC 13 共 13 条规则做静态检查并输出结构化报告
---
## §1 全局禁止清单(skill 专属)

1. **禁止给主观分**——每条结论映射到 EC 1-EC 13

2. **禁止编证据**—— `fail` 必附"文件路径:JSON 路径 / 行号 + 节选"

3. **禁止追加规范外段落**: `approved` 走 §5.1(只输出 `review-report-template.md` 模板正文); `changes_requested` / `rejected` 走 §5.2(只输出 `[评审目标]` / `[整体结论]` / `[维度评分]` 三段),**禁止**任何 plain text / 摘要 / `[下一步]` 等模板外段

---
## §2 关键信息读取

| 字段                    | 状态               | 抽取规则                                                                                                                                                                                                                                    |
| --------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `triggerUser`         | **强制**           | **仅允许** `MSI质量运营助手`。从入口消息 sender 或显式 @ 锁定 `[@MSI质量运营助手:MSI_OPS_BOT_ID]`,期间不变。抽不到 → 阻塞                                                                                                                                                   |
| `requirementSource`   | MSI 质量运营助手 派活时强制 | 需求文档链接 / 路径 / API 描述                                                                                                                                                                                                                    |
| `apiName`             | 强制               | 如 `getStorageSync`、`FileSystemManager.open` (点号在 JSON 文件名中保留)                                                                                                                                                                           |
| `module`              | **EC 评审专有强制**    | API 所属模块名(如 `Storage` / `Location` / `FileSystem`)。从协议 `[模块]` 读;缺则 §6 失败                                                                                                                                                                |
| `round` / `maxRounds` | 协议透传             | `maxRounds` 固定 `3`                                                                                                                                                                                                                      |
| **评审范围**(任一,缺则一次性追问)  | —                | `filePaths` (`msc/EC_TestCases/<module>/<api>.json`)/ `changedFiles` (MSI 质量运营助手 派活优先)/ `branchUrl` (`https://dev.sankuai.com/code/repo-detail/msc/msi-auto-test/file/list?path=&branch=refs/heads/<分支名>`)/ `apiName` + `module` (隐含路径) |

### §2.1 MSI 质量运营助手 派活协议

  

群聊消息同时满足以下条件,判定为 MSI 质量运营助手 派 EC 描述评审任务:

- 含 `[评审类型] ec-test-case-spec`
- 含 `[需求来源]` / `[分支链接]` / `[API名]` / `[模块]` / `[评审轮次]` / `[评审上限]`
- 可选含 `[变更文件]`
**处理规则**:

- `triggerUser` 锁定 `[@MSI质量运营助手:MSI_OPS_BOT_ID]`
- 协议只接受 `[分支链接]`;只能读 `branch=refs/heads/<分支名>` 。解析失败 → §6 失败
**定位评审文件优先级**:

1. `[变更文件]`:优先评 `msc/EC_TestCases/<module>/` 下的 `.json`
2. `[API名]` + `[模块]`:缺少 `changedFiles` 时查找 `msc/EC_TestCases/<module>/<apiName>.json`
3. `[分支链接]` diff fallback:前两者都无法定位时才用 `git diff --name-only origin/master...<分支名>` (过滤 `msc/EC_TestCases/`

任一字段都没拿到 → 回复:

```

[@MSI质量运营助手:MSI_OPS_BOT_ID] 无法继续:EC 描述评审需要明确目标。请至少提供以下任一项:

1) JSON 文件路径(msc/EC_TestCases/<module>/<api>.json)

2) 分支链接 branchUrl + apiName + module

```
---
## §3 评审维度:全面性 + 正确性 + 有效性 + 可维护性(EC 1-EC 13)

> 共 13 条规则,按 §5.0 评分维度归类。维度归属决定计分入口;EC 3 因结构与覆盖率分属两维,在两节同时出现并标注。

### 全面性(EC 1 & EC 2 & EC 3 & EC 4)

| ID | 规则 | pass | fail |
|------|------|------|-------|
| **EC 1** | canIUse 覆盖完整 | canIUse 块格式见 `references/ec-spec-cheatsheet.md §6`。关键约束:1 条 TC(命名 `TC: canIUse验证<API名> & 接口参数 & 返回值的可用性`)+ `schemaList` 覆盖所有入参出参字段(**递归展开嵌套子字段**)+ 命中平台差异时按 `platformBranches` 分支 + 放在 `标准用例` 内首位 | canIUse 缺失 / 多条 / 命名不符 / `schemaList` 漏字段(含嵌套)/ 缺 `platformBranches` / 不在首位 |
| **EC 2** | 通用用例齐备 | `标准用例.入参` 每个字段按 `references/ec-spec-cheatsheet.md §1` 类型矩阵核对(基础 6 条 + 类型补充); `标准用例.出参` 每个出参字段(含嵌套)都有 TC,EX 区分"一定存在" vs "若存在" | 入参字段遗漏 / 类型补充缺失 / 出参不全 / 嵌套子字段未展开 |
| **EC 3** | 场景用例齐备 | `场景测试` 至少含 1 类常见场景;命中 cheatsheet §3 并发信号 → 必须有 `并发场景` 分组;命中大数据信号 → 必须有 `大数据场景` 分组;文档列出但环境无法模拟的错误码 → 顶层须有 `_未覆盖错误码说明` | 场景测试为空 / 并发或大数据信号命中但场景缺失 / 错误码场景遗漏关键码 |
| **EC 4** | 11 类用例类型多样性 | 对照 cheatsheet §2 T 01-T 11 总览表,LLM 据 API 文档判断"应命中"哪几类,看实际命中数;**iOS / Android / HarmonyOS 三端差异都纳入识别**;命中比例 ≥ 80% pass | 应命中但缺失 ≥ 1 类 / 命中比例 < 80% |

### 正确性(EC 5 & EC 6 & EC 7 & EC 8)

| ID | 规则 | pass | fail |
|------|------|------|------|
| **EC 5** | 文件位置正确 | JSON 落在 `msc/EC_TestCases/<module>/<api>.json`, `<module>` = API 所属模块名,文件名 = API 名(点号保留如 `FileSystemManager.open.json`) | 不在该目录 / 模块名与 API 文档不符 / 文件名不符 |
| **EC 6** | JSON schema 合法 | 顶层 1 个 key(= API 名);下含 `标准用例` 与 `场景测试` (任一可空但必须存在); `标准用例` 下有 `canIUse` / `入参` / `出参` 三类;TC / EX 前缀格式见 `ec-spec-cheatsheet.md §5` | JSON 解析失败 / 顶层结构异常 / 缺类 / TC/EX 前缀错 |
| **EC 7** | 模块与文件对应 | `<module>` 与 API 文档模块名一致;文件名严格按 API 文档原名(点号保留);一 API 一 JSON | 模块名笔误 / 跨模块混用 / 文件名替换点号 / 多 API 合并 |
| **EC 8.1** | 字段忠实 | TC 涉及的入参 / 出参字段在 API 文档查得到;类型 / 取值范围与文档一致 | 字段名虚构(文档 `key`,用例写 `cacheKey`)/ string 当 number 测 / 边界值超文档范围 |
| **EC 8.2** | errno 忠实 | EX 写的 errno 能在 API 文档错误码表查到;未列错误码归入 `_未覆盖错误码说明` errno 虚构(如 `99999` 文档没列)/ 套用别 API 错误码 |
| **EC 8.3** | 平台分支忠实 | `platformBranches` 列出的支持平台与文档"三端支持"小节字面一致;TC 内"仅 X 平台"限定与平台差异表一致 | iOS 文档没标支持但 JSON 写支持 / 漏列文档明示平台差异 / 平台限定与文档矛盾 |

### 有效性(EC 9 & EC 10 & EC 11 & EC 12)

  

| ID | 规则 | pass | fail |
|---|---|---|---|
| **EC 9** | 描述具体可执行 | TC 含**动词短语 + 具体值**;平台限定 / 次数 / 数据量显式写出来;EX 明确 success/fail + 关键断言(失败含 errno 或"api 调用失败") | TC 空泛("测试 X" / "大数据" / "并发测试")/ EX 模糊("应该没问题" / "符合预期")/ 平台 / 次数 / 数据量未明确 |
| **EC 10** | 描述具体度 | TC 含动词短语 + 具体值 **且** EX 明确 success/fail + 关键断言对象 **且** 平台限定 / 次数 / 数据量显式写明 | 任一不满足 |
| **EC 11** | 环境可达性 | 用例平台限定与 API 文档支持平台一致 | API 明确写"只 harmony"但用例写需 iOS 执行,**或**没指明只在鸿蒙执行 |
| **EC 12** | 可验证性 | 有副作用的用例(setStorage / 创建文件 / 占用 socket)含清理步骤 **且** 并发用例必断全部子调用成功 + 资源清理 **且** 流程用例必断中间状态 | 任一不满足 |

### 可维护性(EC 13)

| ID        | 规则     | pass                                                                                          | fail                      |
| --------- | ------ | --------------------------------------------------------------------------------------------- | ------------------------- |
| **EC 13** | 用例内容去重 | 同一 JSON 内不存在两条用例的「测试场景 + 期望结果」内容重复(只看 TC + EX 实际语义,**不看 TC 名字符串相似度**;允许枚举值 / 边界值 / 平台差异等显式区分) | 存在 ≥ 1 对内容重复(即使 TC 名字面不同) |


---

  

## §4 工作流程

  

四步线性:**S 1 定位文件 → S 2 读文件 → S 3 跑 EC 1-EC 13 → S 4 按 §5 输出报告**。任一步失败立即停止,§6 失败回报。

**贯穿规则**:全程 `triggerUser` 不可变更(锁定 `MSI质量运营助手`)。  

**关键执行细节**:
- **定位文件**(S 1):优先级 `[变更文件]` > `[API名]` + `[模块]` > `[分支链接]` diff fallback,详见 §2.1
- **读文件**(S 2):直接路径 → `Read`; `branchUrl` → 只读 `git show <分支名>:<相对路径>` (**禁止切分支**)。> 2000 行分段读,报告说明只评了前 N 行
- **JSON 解析**:必能 `json.loads()` / `JSON.parse()`
- **API 文档对照**(S 3):提供 `requirementSource` 时先提取需求中的 API / 入参出参字段表 / 错误码表 / 复杂对象嵌套类型
- **三端覆盖**:iOS / Android / HarmonyOS 三端差异都纳入识别
- **证据格式**: `<相对路径> : <JSON 路径> | <≤120 字片段>`

---
## §5 报告输出格式

回复模板**两类,按 §5.0 综合评分阈值二选一**:

| 综合评分 | 结论 | 走哪个模板 |
|---|---|---|
| ≥ 90 且无 fail | `approved` | §5.1 |
| 70 ≤ 评分 < 90 或有 fail 但 ≥ 70 | `changes_requested` | §5.2 |
| < 70 | `rejected` | §5.2 |

### §5.0 评分体系(决定走哪个模板)
每次评审必算 **4 维加权综合评分**(0-100):

| 维度 | 权重 | 打分口径 | 对应 EC |
|---|---|---|---|
| **全面性** | 50% | 入参 / 出参字段(含嵌套)在 `canIUse.schemaList` + `标准用例.入参/出参` 的覆盖率; `场景测试` 在 11 类 T 01-T 11 中"应命中"类的实际命中比例 | EC 1 + EC 2 + EC 3 + EC 4 |
| **正确性** | 25% | 文件位置 / JSON 结构 / 模块名合规;字段·errno·平台分支与文档一致(无虚构) | EC 5 + EC 6 + EC 7 + EC 8 |
| **有效性** | 20% | TC+EX 具体可执行;平台限定与文档一致;副作用 / 并发 / 流程可清理可断言 | EC 9 + EC 10 + EC 11 + EC 12 |
| **可维护性** | 5% | 用例内容无重复(只看 TC + EX 实际语义)，只有 0 分和 100 分两档评分标准 | EC 13 |

**综合评分** = `(全面性 × 50% + 有效性 × 20% + 正确性 × 25% + 可维护性 × 5%)`
### §5.1 approved 模板

````

`@MSI质量运营助手 本次 MSI EC 用例描述评审**通过**,**请通知原始触发人继续后续流程**`

  

[评审类型] ec-test-case-spec

  

[评审结论] approved

  

[需求来源]:<requirementSource>

  

[分支链接] 透传(**禁裸 `branch`**)

  

[综合评分] <0-100>

  

[维度评分] 4 维:全面性(权 50) / 正确性(权 25) / 有效性(权 20) / 可维护性(权 5)

  

[原始触发人] [@<triggerUser 中文名>:<triggerUserId>]

  

[评审报告] <**严格按** `references/review-report-template.md` 的「模板正文」节填写(完整 Markdown 报告,含元信息 quote / §1 综合评分 / §2 T01-T11 覆盖 / §3 EC1-EC13 明细 / §4 整体结论)。>

  

````

**评审报告格式强制**:

- §1 综合评分 / §2 T 01-T 11 / §3 EC 1-EC 13 三段**必须用 Markdown 表格**(`| ... | ... |`),**禁** bullet 列表 / plain text key:value

- 表头、列顺序、列名按模板原样,不增删不改名

- 数据按实际填充,无数据写 `n_a`

  

### §5.2 changes_requested / rejected 模板

````

`@MSI质量运营助手 本次 MSI EC 用例描述评审**未通过**,请按照***扣分项和待修改*进行修改，修改后再次提交审核`

  

[评审类型] ec-test-case-spec

  

[评审结论] <changes_requested>

  

[需求来源]:<requirementSource>

  

[分支链接] 透传(**禁裸 `branch`**)

  

[综合评分] <0-100>

  

[维度评分] 4 维:全面性(权 50) / 正确性(权 25) / 有效性(权 20) / 可维护性(权 5)

  

[原始触发人] [@<triggerUser 中文名>:<triggerUserId>]

  

[维度评分]

- 全面性(权 50%):<分数>

- 扣分项:<fail 的 EC ID(EC1 / EC2 / EC3 / EC4)+ 一句话原因(如 "EC1: schemaList 漏字段 platformBranches");无 fail 写 "无">

- 待修改:<对应 JSON 路径 + 具体修改方向(改哪个字段 / 加什么 TC / 补哪类场景);无 fail 写 "无">

- 正确性(权 25%):<分数>

- 扣分项:<fail 的 EC ID(EC5 / EC6 / EC7 / EC8.1 / EC8.2 / EC8.3)+ 一句话原因(如 "EC8.2: errno 99999 文档未列");无 fail 写 "无">

- 待修改:<对应 JSON 路径 + 改成什么样(如 "EX 改回文档列出的 errno 12001");无 fail 写 "无">

- 有效性(权 20%):<分数>

- 扣分项:<fail 的 EC ID(EC9 / EC10 / EC11 / EC12)+ 一句话原因(如 "EC10: TC 缺数据量 / EC12: setStorage 用例无清理");无 fail 写 "无">

- 待修改:<对应 JSON 路径 + 改成什么样(如 "TC 补 '写入 1MB 数据';场景测试加 removeStorage 清理步骤");无 fail 写 "无">

- 可维护性(权 5%):<分数>

- 扣分项:<EC13 fail 时列每对内容重复用例(JSON 路径 + 两条 TC+EX 节选 + 撞车原因);无 fail 写 "无">

- 待修改:<对应 JSON 路径 + 合并或差异化方向(如 "TC3 与 TC7 重复,合并;或 TC7 改测边界值 0");无 fail 写 "无">

````

---

  

## §6 失败处理范式

  

任一阶段失败,**立即停止**,回复:

  

```

[@MSI质量运营助手:MSI_OPS_BOT_ID] MSI EC 用例描述评审**失败**(阶段:<failedStage>)

[失败阶段] <LLM执行现状>

[reason] <具体报错原文,不加工成乐观结论>

```

  

---

  

## §7 自检清单

  

- [ ] **§3 结论 & 证据**:每条结论映射到 `EC1..EC13`?每条 `fail` 附文件路径 + JSON 路径 / 行号 + 片段(没有就 `n_a`)?

- [ ] **§5.0 阈值路由**:按公式算综合评分 + 4 维 + 用例总数?按阈值选结论(≥ 90 → approved;70-89 或有 fail 但 ≥ 70 → changes_requested;< 70 → rejected)?

- [ ] **严格按照 approved、changes_requested / rejected 模板**进行回复，禁止添加无关信息、遗漏模板内容