
```shell

#!/usr/bin/env bash

# prepare-context.sh — review-impl-vs-test-case 前置脚本

# 吞 STEP 1-5:协议解析 / platform 推断 / clone / git diff / 用例文件提取

#

# 入参:

# $1 = PR_URL sankuai GitLab MR 链接

# $2 = CASE_BRANCH_URL 测试用例分支 URL(含 branch=refs/heads/<branch>)

# $3 = TRIGGER_USER_JSON 触发人 JSON,形如 '{"name":"张三","id":"RD123456"}'

#

# 出参:

# stdout = context.json 绝对路径

# /tmp/msi-review/<runId>/ = code.diff + cases/<api>.js

#

# 退出码:

# 0 成功

# 10 必填字段缺失 / URL 格式不符 / triggerUser JSON 不合法

# 11 platform 未在 21 仓白名单

# 13 测试用例分支无 AI_TestCases JS

# 14 clone / fetch MR ref / git show 失败

# 15 diff > 3000 行

  

set -uo pipefail

  

# ============================================================

# 0. 常量与路径

# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

MAPPING_FILE="$SKILL_DIR/references/platform-repo-mapping.md"

MSI_AUTO_TEST_REPO="${MSI_AUTO_TEST_REPO:-/Users/msi-auto-test/Documents/msi-auto-test}"

CLONE_SCRIPT="$SCRIPT_DIR/clone-repos.sh"

REPOS_DIR="/Users/msi-auto-test/Documents/repos"

  

export GIT_TERMINAL_PROMPT=0

export GIT_SSH_COMMAND="ssh -oBatchMode=yes -oStrictHostKeyChecking=accept-new"

  

# ============================================================

# 1. 入参校验

# ============================================================

PR_URL="${1:-}"

CASE_URL="${2:-}"

TRIGGER_USER="${3:-}"

  

if [[ -z "$PR_URL" || -z "$CASE_URL" || -z "$TRIGGER_USER" ]]; then

echo "ERR_10: 缺少必填参数。用法: prepare-context.sh <PR_URL> <CASE_BRANCH_URL> <TRIGGER_USER_JSON>" >&2

exit 10

fi

  

# 校验 triggerUser JSON 形态(必须含 name / id)

if ! echo "$TRIGGER_USER" | grep -Eq '"name"[[:space:]]*:[[:space:]]*"[^"]+"'; then

echo "ERR_10: TRIGGER_USER_JSON 缺 name 字段,需形如 {\"name\":\"...\",\"id\":\"...\"}" >&2

exit 10

fi

if ! echo "$TRIGGER_USER" | grep -Eq '"id"[[:space:]]*:[[:space:]]*"[^"]+"'; then

echo "ERR_10: TRIGGER_USER_JSON 缺 id 字段" >&2

exit 10

fi

  

# ============================================================

# 2. 工作目录

# ============================================================

RUN_ID="$(date +%s)-$$"

WORK_DIR="/tmp/msi-review/$RUN_ID"

mkdir -p "$WORK_DIR/cases"

  

# JSON 字符串编码 helper(优先 python3,fallback sed)

json_quote() {

if command -v python3 >/dev/null 2>&1; then

printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'

elif command -v python >/dev/null 2>&1; then

printf '%s' "$1" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))'

else

printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"

fi

}

  

# ============================================================

# 3. PR URL 解析 + platform 查表

# ============================================================

if [[ "$PR_URL" =~ ^https://dev\.sankuai\.com/code/repo-detail/([^/]+)/([^/]+)/merge_requests/([0-9]+) ]]; then

ORG="${BASH_REMATCH[1]}"

REPO="${BASH_REMATCH[2]}"

MR_ID="${BASH_REMATCH[3]}"

PR_FETCH_REF="refs/merge-requests/$MR_ID/head"

elif [[ "$PR_URL" =~ ^https://dev\.sankuai\.com/code/repo-detail/([^/]+)/([^/]+)/pr/([0-9]+)/overview ]]; then

ORG="${BASH_REMATCH[1]}"

REPO="${BASH_REMATCH[2]}"

MR_ID="${BASH_REMATCH[3]}"

PR_FETCH_REF="refs/pull-requests/$MR_ID/from"

else

echo "ERR_10: PR URL 格式不符,需为 https://dev.sankuai.com/code/repo-detail/<org>/<repo>/merge_requests/<id> 或 https://dev.sankuai.com/code/repo-detail/<org>/<repo>/pr/<id>/overview" >&2

exit 10

fi

SLUG="$ORG/$REPO"

  

if [[ ! -f "$MAPPING_FILE" ]]; then

echo "ERR_11: platform-repo-mapping.md 不存在: $MAPPING_FILE" >&2

exit 11

fi

  

MAPPING_LINE="$(grep -E "^\| ${SLUG//\//\\/} \| " "$MAPPING_FILE" 2>/dev/null || true)"

if [[ -z "$MAPPING_LINE" ]]; then

echo "ERR_11: platform 未识别。slug=$SLUG 不在 21 仓白名单。请扩 platform-repo-mapping.md。" >&2

exit 11

fi

PLATFORM="$(echo "$MAPPING_LINE" | awk -F '|' '{gsub(/^[ \t]+|[ \t]+$/,"",$3); print $3}')"

TARGET_BRANCH="$(echo "$MAPPING_LINE" | awk -F '|' '{gsub(/^[ \t]+|[ \t]+$/,"",$4); print $4}')"

  

if [[ -z "$PLATFORM" || -z "$TARGET_BRANCH" ]]; then

echo "ERR_11: 解析 platform-repo-mapping.md 行失败: $MAPPING_LINE" >&2

exit 11

fi

  

# ============================================================

# 4. case URL 解析

# ============================================================

if [[ ! "$CASE_URL" =~ branch=refs/heads/([^&]+) ]]; then

echo "ERR_10: 测试用例分支 URL 缺 branch=refs/heads/<branch> 段" >&2

exit 10

fi

CASE_BRANCH="${BASH_REMATCH[1]}"

  

# ============================================================

# 5. clone 单端代码仓

# ============================================================

if [[ ! -x "$CLONE_SCRIPT" ]]; then

echo "ERR_14: 找不到 clone-repos.sh ($CLONE_SCRIPT);本脚本应与 clone-repos.sh 同目录" >&2

exit 14

fi

  

if ! bash "$CLONE_SCRIPT" -p "$PLATFORM" -j 2 >&2; then

echo "ERR_14: clone-repos.sh -p $PLATFORM 失败" >&2

exit 14

fi

  

CODE_REPO_DIR="$REPOS_DIR/$PLATFORM/$REPO"

if [[ ! -d "$CODE_REPO_DIR/.git" ]]; then

echo "ERR_14: 代码仓未拉取成功: $CODE_REPO_DIR" >&2

exit 14

fi

  

# ============================================================

# 6. fetch MR ref + target 分支

# ============================================================

if ! git -C "$CODE_REPO_DIR" fetch origin "$PR_FETCH_REF:refs/remotes/origin/mr-$MR_ID" --quiet 2>>"$WORK_DIR/fetch.err"; then

echo "ERR_14: fetch MR ref 失败 (mrId=$MR_ID),可能 MR 不存在或权限不足。详情:" >&2

cat "$WORK_DIR/fetch.err" >&2

exit 14

fi

  

if ! git -C "$CODE_REPO_DIR" fetch origin "+refs/heads/$TARGET_BRANCH:refs/remotes/origin/$TARGET_BRANCH" --quiet 2>>"$WORK_DIR/fetch.err"; then

echo "ERR_14: fetch target 分支 $TARGET_BRANCH 失败" >&2

cat "$WORK_DIR/fetch.err" >&2

exit 14

fi

  

# ============================================================

# 7. 出 diff(限语言后缀)

# ============================================================

CODE_DIFF="$WORK_DIR/code.diff"

git -C "$CODE_REPO_DIR" diff --unified=3 \

"origin/$TARGET_BRANCH...origin/mr-$MR_ID" \

-- '*.swift' '*.m' '*.mm' '*.kt' '*.java' '*.ets' '*.ts' '*.js' \

> "$CODE_DIFF" 2>>"$WORK_DIR/diff.err" || {

echo "ERR_14: git diff 失败" >&2

cat "$WORK_DIR/diff.err" >&2

exit 14

}

  

DIFF_LINE_COUNT=$(wc -l < "$CODE_DIFF" | tr -d ' ')

if [[ "$DIFF_LINE_COUNT" -gt 3000 ]]; then

echo "ERR_15: diff 过大 ($DIFF_LINE_COUNT 行 > 3000),请拆 PR 后再评审" >&2

exit 15

fi

  

# ============================================================

# 8. msi-auto-test 仓 + 测试用例分支

# ============================================================

if [[ ! -d "$MSI_AUTO_TEST_REPO/.git" ]]; then

echo "ERR_14: msi-auto-test 仓不存在或非 git 仓库: $MSI_AUTO_TEST_REPO" >&2

exit 14

fi

  

if ! git -C "$MSI_AUTO_TEST_REPO" fetch origin "+refs/heads/$CASE_BRANCH:refs/remotes/origin/$CASE_BRANCH" --quiet 2>>"$WORK_DIR/fetch.err"; then

echo "ERR_14: msi-auto-test fetch $CASE_BRANCH 失败,可能分支不存在" >&2

cat "$WORK_DIR/fetch.err" >&2

exit 14

fi

  

if ! git -C "$MSI_AUTO_TEST_REPO" fetch origin "+refs/heads/master:refs/remotes/origin/master" --quiet 2>>"$WORK_DIR/fetch.err"; then

echo "ERR_14: msi-auto-test fetch master 失败" >&2

exit 14

fi

  

# 列变更的 AI_TestCases JS 文件

CHANGED_FILES="$(git -C "$MSI_AUTO_TEST_REPO" diff --name-only "origin/master..origin/$CASE_BRANCH" -- 'msc/AI_TestCases/*.js' 'msc/AI_TestCases/**/*.js' 2>/dev/null | grep -E '^msc/AI_TestCases/.*\.js$' || true)"

  

if [[ -z "$CHANGED_FILES" ]]; then

echo "ERR_13: 测试用例分支 $CASE_BRANCH 未发现任何 msc/AI_TestCases/**/*.js 改动,请检查分支是否正确" >&2

exit 13

fi

  

# ============================================================

# 9. 拷贝每个 .js 到 WORK_DIR/cases + 拼 apiNames / caseFiles

# ============================================================

SEEN_APIS_FILE="$WORK_DIR/.seen_apis"

: > "$SEEN_APIS_FILE"

  

CASE_FILES_JSON="["

API_NAMES_JSON="["

FIRST_CASE=1

FIRST_API=1

  

while IFS= read -r FILE; do

[[ -z "$FILE" ]] && continue

API_NAME="$(basename "$FILE" .js)"

LOCAL_PATH="$WORK_DIR/cases/$API_NAME.js"

git -C "$MSI_AUTO_TEST_REPO" show "origin/$CASE_BRANCH:$FILE" > "$LOCAL_PATH" 2>>"$WORK_DIR/fetch.err" || {

echo "ERR_14: git show $FILE @ $CASE_BRANCH 失败" >&2

cat "$WORK_DIR/fetch.err" >&2

exit 14

}

  

if [[ $FIRST_CASE -eq 0 ]]; then CASE_FILES_JSON+=","; fi

CASE_FILES_JSON+="{\"apiName\":$(json_quote "$API_NAME"),\"path\":$(json_quote "$LOCAL_PATH"),\"repoPath\":$(json_quote "$FILE")}"

FIRST_CASE=0

  

if ! grep -qx "$API_NAME" "$SEEN_APIS_FILE"; then

echo "$API_NAME" >> "$SEEN_APIS_FILE"

if [[ $FIRST_API -eq 0 ]]; then API_NAMES_JSON+=","; fi

API_NAMES_JSON+="$(json_quote "$API_NAME")"

FIRST_API=0

fi

done <<< "$CHANGED_FILES"

  

CASE_FILES_JSON+="]"

API_NAMES_JSON+="]"

  

# ============================================================

# 10. 产出 context.json

# ============================================================

CONTEXT_FILE="$WORK_DIR/context.json"

WARNINGS_JSON="[]"

  

cat > "$CONTEXT_FILE" <<EOF

{

"runId": $(json_quote "$RUN_ID"),

"platform": $(json_quote "$PLATFORM"),

"repoSlug": $(json_quote "$SLUG"),

"mrId": $(json_quote "$MR_ID"),

"targetBranch": $(json_quote "$TARGET_BRANCH"),

"caseBranch": $(json_quote "$CASE_BRANCH"),

"caseBranchUrl": $(json_quote "$CASE_URL"),

"prUrl": $(json_quote "$PR_URL"),

"apiNames": $API_NAMES_JSON,

"codeDiffPath": $(json_quote "$CODE_DIFF"),

"diffLineCount": $DIFF_LINE_COUNT,

"caseFiles": $CASE_FILES_JSON,

"triggerUser": $TRIGGER_USER,

"warnings": $WARNINGS_JSON

}

EOF

  

echo "$CONTEXT_FILE"

exit 0

```
