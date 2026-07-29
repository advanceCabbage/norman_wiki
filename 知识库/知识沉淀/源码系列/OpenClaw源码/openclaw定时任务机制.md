#### 一、定时任务执行流程

**核心调度流程**：CronService 始终围绕“最早到期的任务”设置一个全局定时器。它先找出所有启用任务中最接近当前时间的任务 ，计算距离该任务的剩余时间。
- 若最近任务在 **60 秒以后**，则只设置一个 **60 秒** 的 `setTimeout`；60 秒后重新读取任务状态、重新寻找最近任务。
- 若最近任务在 **60 秒以内**，则按实际剩余时间设置 `setTimeout`，到点立即执行。
- Timer 触发后，先筛选所有已到期且未执行中的任务，标记 `runningAtMs` 并持久化，再执行任务。
- 任务结束后，更新执行结果并计算其下一次 `nextRunAtMs`；随后再次寻找全局最近任务，进入下一轮调度

**详细调度流程**

- **保存定时任务**：用户创建“每天上午 9 点执行”的 Cron Job，Gateway 将任务保存到 `jobs.json`。
- **计算首次执行时间**：CronService 读取所有启用任务，计算每个任务的 `nextRunAtMs`；该任务例如为今天或明天的 09:00:00。
- **选择最近任务**：CronService 找出所有启用任务中最早的 `nextRunAtMs`。
- **计算等待时长**：根据最近任务计算：delay = nextRunAtMs - 当前时间
- **设置全局定时器**：使用：setTimeout(onTimer, Math.min(delay, 60_000))，最长等待 60 秒；若任务只剩 10 秒，则等待 10 秒后触发
- **检查到期任务**：Timer 触发后，CronService 重新加载任务并筛选满足以下条件的 Job
```
enabled = true
runningAtMs 不存在
当前时间 >= nextRunAtMs
```
- **标记任务执行中**：对到期任务先写入并持久化：runningAtMs = 当前时间，防止 timer 重复触发或手工执行导致同一任务并发运行。
- **路由任务执行方式**：根据 `sessionTarget` 决定执行路径：
	-  `main`：写入 system event，立即唤醒或等待下一次 Heartbeat；
	-  `isolated`：创建新的独立 Cron Session，启动一次完整 Agent Loop
- **记录执行结果**：任务结束后更新
- **计算下一次执行时间**：若任务成功且是每日任务，重新计算下一个上午 9 点：nextRunAtMs = 下一次 09:00:00
- **失败时进行退避**：若任务失败，按连续失败次数设置指数退避时间，再写入新的 `nextRunAtMs`
- **进入下一轮调度**：持久化更新后的任务状态，重新选择所有任务中最近的 `nextRunAtMs`，设置下一次全局 `setTimeout`

#### 二、定时三种任务类型及两种执行策略

**三种任务类型**
- `at`：一次性 ISO 时间；
- `every`：基于 `anchorMs` 的固定毫秒间隔；
- `cron`：5 段或 6 段 Cron 表达式，使用 `croner` 解析，支持 IANA 时区

**两种执行策略**
- Main：把任务送入已有主会话
- Isolated：启动一次独立 Agent Loop

OpenClaw 不在 CronService 运行时判断 Main 或 Isolated；目标类型由创建任务时的模型工具调用决定。自然语言任务默认优先建成 isolated agentTurn，只有用户明确需要复用主会话或注入 heartbeat system event 时，才创建 main systemEvent。
#### 三、定时任务容错机制
- **循环任务执行成功**：将 `consecutiveErrors` 清零，更新 `lastRunAtMs`、`lastRunStatus = "ok"`，然后按 schedule 计算正常的下一次 `nextRunAtMs`。
- **一次性 `at` 任务成功**：若 `deleteAfterRun: true`（默认值），直接从 `jobs.json` 删除；若 `deleteAfterRun: false`，保留任务记录但设置 `enabled: false`，不会再次触发。
- **一次性 `at` 任务失败或跳过**：不会删除任务记录，但会直接禁用。这样即使它的 `at` 时间已经过去，也不会在后续 timer tick 中反复触发。
- **循环任务执行失败**：这是指任务已经进入执行阶段，但 Agent Loop、Heartbeat、渠道投递等返回 error。此时 `consecutiveErrors` 加一，任务仍保持启用，并按指数退避重试，30s → 1m → 5m → 15m → 1h
- **Cron 正常重排保护**：对于 `schedule.kind = "cron"` 的循环任务，无论成功还是非退避的正常重排，下一次 `nextRunAtMs` 至少要晚于本次执行结束时间 2 秒，防止 Croner 在同一秒返回当前时间、导致任务自旋重触发。
- **排期计算失败**：这是另一类错误，指任务尚未执行，系统在计算 `nextRunAtMs` 时就失败，例如表达式、时区或 schedule 数据异常。此时增加 `scheduleErrorCount`、清空 `nextRunAtMs`；连续 3 次失败后自动设置 `enabled: false`。  
    即：**执行失败是退避重试；排期失败是连续三次后禁用。**
- **执行超时**：CronService 对单次 Job 有默认 10 分钟的总 wall-clock watchdog。`agentTurn.payload.timeoutSeconds` 可覆盖该时间；设为 `0` 或负数时，关闭 CronService 这一层的超时限制。超时会中止执行并按“任务执行失败”进入结果处理。
- **状态持久化与重调度**：无论成功、失败、跳过、删除或禁用，都会更新 Job state 并持久化到 `jobs.json`，然后重新寻找全局最早的 `nextRunAtMs`，设置下一轮全局 timer