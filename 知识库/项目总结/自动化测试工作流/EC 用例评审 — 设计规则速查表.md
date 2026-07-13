# EC 用例评审 — 设计规则速查表


本文件是 `generate-ec-test-case-spec/references/ec-spec-rules.md §2 + §3` 的**评审视角精炼**,只录入评审 EC 1-EC 9 时实际需要对照的内容。设计完整规则见源文件;评审时只需查本表。

---
## 1. 入参类型 × 场景必有 case 矩阵(用于评审 EC 4)

  

每个入参字段按所属类型行核对 JSON 是否包含对应 case(必/非 = 必填和非必填都要;必 = 仅必填):

| 类型 | 必有场景 |
|---|---|
| **string** | 正确值 / 类型错误 / null / undefined / 不传 / 空字符串(必) / 超长 ≥10000(必/非) |
| **number** | 正确值 / 类型错误 / null / undefined / 不传 / 0(必)/ 范围边界 4 条(若文档标注范围) |
| **boolean** | true(独立 case)/ false(独立 case)/ 类型错误 / null / undefined / 不传 |
| **enum** / 多类型 | 每个枚举值各 1 条 / 非枚举值 / null / undefined / 不传 |
| **object** | 正确值 / 类型错误 / 数组撞车(传数组)/ null / undefined / 不传 / 空对象 |
| **array** | 正确值 / 类型错误 / null / undefined / 不传 / 空数组 / 元素枚举值补充(若元素是枚举) |
| **callback** | 正确值 / undefined;事件 API 默认必填 |

**类型特殊补充**:

- number 文档标注范围 → 4 条边界 case(下限 / 上限 / 下限-1 / 上限+1)

- array 元素是枚举 → 5 条枚举补充(单合法 / 全合法 / 单非法 / 混合 / 重复)

- 超时字段名(`timeout` / `*WaitTime` / `*Timeout`)→ 传过小值触发文档超时错误码

- **禁止**校验 `success` / `fail` / `complete` 回调字段(异步 API 默认有,不需要 case)

  

---

  

## 2. T 01-T 11 类型与触发信号(用于评审 EC 8 + §5.0 全面性)

  

| 编号 | 类型 | 触发信号(命中即应该有) |
|---|---|---|
| **T 01** | 正向 | 所有 API(强制) |
| **T 02** | 反向 | 所有 API(强制) |
| **T 03** | 异常 | 文档列错误码 / 工单含异常 / 状态机调用 |
| **T 04** | 边界 | 入参含范围 / 集合 / 枚举边界 |
| **T 05** | 流程 | 多步业务流程 / API 间状态依赖 |
| **T 06** | 权限 | 文档声明权限 / 操作敏感资源 / 错误码 59995-60001 |
| **T 07** | 安全 | 加密 / 注入风险 / 敏感数据 |
| **T 08** | 性能 | 响应/内存约束 / 入参出参大体积 / 高频调用 |
| **T 09** | 兼容性 | 文档明示网络 / 系统版本 / 机型差异 |
| **T 10** | 幂等 / 重试 | 写操作 / 状态变更 / 共享资源 |
| **T 11** | 降级与容错 | 依赖外部 SDK / 网络 / 本地资源 |

T 01/T 02 所有 API 强制命中;T 03-T 11 按信号判断"应命中",未命中需有合理依据。

---

  

## 3. 高级场景触发信号详表(用于评审 EC 5)

  

| 场景 | 触发信号(命中任一就应该有该分组) |
|---|---|
| **并发** | ① 共享底层资源(文件 / 网络池 / IPC / 麦克风 / 相机) ② 全局单例(Manager / Context / Task 后缀) ③ 文档/工单含「并发 / 线程 / 串行 / 独占 / 竞争 / crash / ANR」 ④ 频繁调用类基础 API |
| **大数据** | ① 文档约束大小 ② 错误码含 size/length 类 ③ 入参出参可能传大值(string / Array / object / ArrayBuffer / filePath / 响应体) ④ 批量 API(batch* / multi* / fetchAll) |
| **权限** | ① 文档明示权限 ② 操作敏感资源(相机 / 麦克风 / 定位 / 通讯录 / 相册 / 蓝牙 / NFC / 生物识别) ③ 错误码 59995 / 60001 ④ 文档列三端权限差异 |
| **安全** | ① API 名 / 入参含 encrypt / decrypt / sign / verify / hash / token ② 入参可注入(SQL / shell / 路径 / HTML / JSON) ③ 处理敏感数据 ④ 文档含"加密存储 / 签名校验" |
| **性能** | ① 文档含响应时间 / 耗时 / 内存 / 卡顿 / ANR ② 高频路径(启动 / 首屏 / 列表 / 动画帧) ③ 已命中并发或大数据 |
| **降级容错** | ① 依赖外部 SDK(Pike / 支付 / 高德 / Lottie) ② 依赖网络 ③ 依赖本地资源 ④ 文档含"兜底 / 降级 / fallback / 本地缓存 / 重试 / 离线" |
| **异常** | ① 状态机错误(未 connect 时 send) ② 资源耗尽(fd / socket / 内存) ③ 环境异常(时间倒流 / 磁盘满 / 沙箱权限丢失) |
| **跨环境兼容** | 限定三维度:网络 / 系统版本 / 机型(应用宿主 / 客户端差异由 canIUse `platformBranches` 处理,不在 case 范围) |

---

  

## 4. 错误码处理(用于评审 EC 5)

  

- 文档错误码**能在当前环境模拟** → JSON 必须有对应 fail case

- 文档错误码**无法在当前环境模拟**(如 iOS 文件句柄异常)→ JSON 顶层必须有 `_未覆盖错误码说明` 字段(格式见 `generate-ec-test-case-spec/references/ec-json-schema.md §7`)

- 错误码仅在部分平台返回(如 59995 仅 Android / HarmonyOS)→ TC 描述显式标注"仅 X 平台断言"

  

## 5. TC + EX 基本结构

每一条用例由 **TC**(Test Case 测试场景)+ **EX**(Expected 期望结果)+ 占位 `{}` 三层构成:

  

```json

"TC: <场景描述>": {

"EX: <期望结果>": {}

}

```

  

### 5.1 TC 描述规则

  

- 以 `TC: ` 开头(冒号后有空格)

- 用**动词短语 + 具体值**,避免空泛描述(反例: `TC: 测试 cid` / `TC: 大数据` / `TC: 并发测试`)

- 涉及平台限定 / 次数 / 数据量时显式写出来(如 `仅 iOS 执行`、`连续调用 5 次`、`传入 1MB 字符串`)

  

### 5.2 EX 描述规则

  

- 以 `EX: ` 开头(冒号后有空格)

- 明确说明 success / fail + 关键断言;失败时文档有错误码则写明 errno,无错误码则写 "api 调用失败"

- 业务有效性(如 fd 非空、距离非负)在 EX 里显式表达

- EX 下必须是空对象 `{}` 占位,**不要**塞其他内容;**唯一例外**:canIUse 的 EX 下允许带结构化内容(见 §6)

  

示例:

  

- `"EX: api 调用成功, 返回 fd 为 string 类型且不为空字符串"`

- `"EX: api 调用失败, errno=20007 (Android) / 59995 (HarmonyOS) / 29999 (iOS),按平台分支断言"`

  

## 6. `标准用例.canIUse` 结构(特殊形态)

  

按 `ec-spec-rules.md` §1.1 硬约束,canIUse 必须放在 `标准用例` 顶层首位(在 `入参` / `出参` **之前**),且只有**一条** TC。EX 下的内容签名:

  

```

{ schemaList, platformBranches?: { notAndroid?, notHarmony?, notIOS? }, negativeSchemas? }

```

  

实际形态见 §8 onLocationChange 样本(含 schemaList / platformBranches 三类分支 / negativeSchemas)。

  

> **注意**:canIUse 的 EX 下**例外允许**带结构化内容,因为 schema 列表本身是 canIUse case 的核心数据。这是 `TC + EX + {}` 占位结构的**唯一例外**。

  

字段说明:

  

| 字段 | 含义 | 后续代码翻译 |
|---|---|---|
| `schemaList` | 所有平台的参数合集、并集 | 直接 push 到 canIUseData |
| `platformBranches.notAndroid` | Android 不支持的字段 | `if (!util.isAndroid)` push |
| `platformBranches.notHarmony` | HarmonyOS 不支持的字段 | `if (!util.isHarmony)` push |
| `platformBranches.notIOS` | iOS 不支持或灰度中的字段 | `if (!util.isIOS)` push |
| `negativeSchemas` | 负向校验,应返回 false 的字段 | 校验断言取反 |

schema 命名规则、平台判断规则、嵌套字段展开要求详见 `ec-spec-rules.md` §1.2 / §1.3。