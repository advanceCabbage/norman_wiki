## 一、代码回退 （rewind）原理
首先 Claude code 通过会话为维度创建文件修改快照，共能保存 20 次文件快照。其次假设一次会话中涉及多个文件修改也算一次文件快照，最后当文件快照超过 20 次时，从最早创建的快照开始删除，保持最多 20 次快照记录。
**快照存储位置**：
```
~/.claude/file-history/<session-id>/
```
每个备份文件名是“原始文件路径的 SHA-256 前 16 位 + 版本号”，例如:
```
~/.claude/file-history/abc-session-id/9f86d081884c7d65@v1
```
**通过用户消息 UUID 关联快照**：
- 创建快照时传入用户当前的消息 UUID
- 获取快照时精确匹配 UUID，回退到对应的 UUID 的消息版本

```typescript
type FileHistorySnapshot = {
  messageId: UUID
  trackedFileBackups: Record<string, FileHistoryBackup>
  timestamp: Date
}
```

## 二、approve、reject 原理
**定义**：**Approve / Reject**：在 `Edit` / `Write` 工具真正写入磁盘之前进行权限决策与交互确认
**执行链路**：`FileEditTool` 和 `FileWriteTool` 都实现了 `checkPermissions()`，执行链路为：
- 命中 `deny` 规则：直接拒绝
- 受保护路径（例如 `.git`、`.claude` 等）：通常要求确认
- 当前处于 `acceptEdits` 模式、文件位于允许工作目录，或命中 `allow` 规则：自动允许
- 其余写操作：默认 `ask`
```
模型请求 Edit / Write
-> 工具 checkPermissions()
-> hasPermissionsToUseTool()
-> allow / deny / ask
-> ask 时打开权限确认 UI
-> 用户 Approve 后才执行 tool.call()
```
- **Approve**：可能同时写入本次或会话级的允许规则，然后执行真正的文件工具。
- **Reject**：不会执行 `FileEditTool` / `FileWriteTool` 的写盘逻辑；拒绝结果回到工具执行链路，模型可据此调整方案或停止