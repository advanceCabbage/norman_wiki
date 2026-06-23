# 将 AI 生成的图片插入学城文档

学城文档图片有权限校验，**图片权限与所在文档绑定**。非学城链接的图片属于非法数据，**严禁直接插入学城文档**。

当用户要求将 AI 生成的图片插入学城文档时，严格遵循以下工作流：

## 第一步：上传图片到目标文档

```bash
uploadImageToDocument --contentId <目标文档ID> --imageUrl <AI图片URL> [--alt <图片描述>]
```

该命令会：
- 下载 AI 图片二进制数据
- 将图片上传到目标文档的学城图片空间（图片权限与该文档绑定）
- 返回学城 CDN URL 和拼装好的 **CitadelMD 图片语法片段**（`imageMd`）

输出示例：

```
✅ 图片上传成功！
```

## 第二步：获取目标文档内容

```bash
getDocumentCitadelMd --contentId <目标文档ID>
```

获取文档当前完整的 CitadelMD 内容。

## 第三步：由 AI 在指定位置插入图片语法

将第一步返回的 `imageMd`（CitadelMD 图片语法片段）插入到文档 CitadelMD 内容的用户指定位置。

CitadelMD 图片语法格式：

```
![图片描述](https://km.sankuai.com/api/file/box/...)
![图片描述](https://km.sankuai.com/api/file/box/...){width=300 height=200 align=center}
```

支持的图片属性：
- `width`：图片宽度（px）
- `height`：图片高度（px）
- `align`：对齐方式（`left` / `center` / `right`）

## 第四步：回传更新文档

```bash
updateDocumentByMd --contentId <目标文档ID> --content <修改后的CitadelMD>
```

**输出**：返回文档链接，提醒用户刷新页面查看插入的图片。

## 示例 (Example)

用户：帮我把这张图 https://example.com/ai-chart.png 插入到文档 https://km.sankuai.com/collabpage/1234567890 的"总结"章节下面

思考：我需要先上传图片到目标文档，再获取文档内容，由 AI 找到插入位置后更新文档。

```bash
# 第一步：上传图片
uploadImageToDocument --contentId 1234567890 --imageUrl "https://example.com/ai-chart.png" --alt "总结图表"

# 第二步：获取文档内容
getDocumentCitadelMd --contentId 1234567890
```

... 获取到 imageMd 和文档内容后，AI 在"总结"章节下方插入图片语法，然后：

```bash
# 第四步：更新文档
updateDocumentByMd --contentId 1234567890 --content <修改后的CitadelMD>
```

## 禁止事项

- **严禁将非学城图片 URL（包括 AI 生成的图片原始 URL）直接写入 CitadelMD**
- 必须先通过 `uploadImageToDocument` 上传图片，取得学城 CDN URL 后再插入
- 图片上传必须指定目标文档 `contentId`，图片权限与该文档绑定，不可跨文档复用

---

# 将本地文件作为附件插入学城文档

> ⚠️ **仅限非媒体文件**：PDF、Word、Excel、ZIP、TXT 等。**视频（mp4/mov/avi 等）和音频（mp3/wav/aac/m4a 等）禁止使用此工作流**——视频请使用"将本地视频文件插入学城文档"工作流，音频请使用"将本地音频文件插入学城文档"工作流。混用将导致媒体 URL 无法转换为 CDN 格式，文档内容损坏。

## 第一步：上传附件到目标文档

```bash
uploadAttachmentToDocument --contentId <目标文档ID> --file <本地文件路径>
```

该命令会：
- 以 `multipart/form-data` 方式将本地文件上传到 `POST /api/file/upload/<contentId>`
- 返回学城附件 URL（`url`）及拼装好的 **CitadelMD 附件语法片段**（`attachmentMd`）

上传接口说明：
- **URL**：`POST https://km.sankuai.com/api/file/upload/<contentId>`
- **请求**：`multipart/form-data`，字段名 `file`，值为文件二进制内容
- **响应**（示例）：
  ```json
  {
    "status": 0,
    "data": {
      "url": "https://km.sankuai.com/api/file/attachment/2752685363/228651870995",
      "attachmentId": 228651870995,
      "downloadUrl": "https://file.sankuai.com/file/dl/..."
    }
  }
  ```

## 第二步：获取目标文档内容

```bash
getDocumentCitadelMd --contentId <目标文档ID>
```

获取文档当前完整的 CitadelMD 内容。

## 第三步：由 AI 在指定位置插入附件语法

将第一步返回的 `attachmentMd`（CitadelMD 附件语法片段）插入到文档 CitadelMD 内容的用户指定位置。

CitadelMD 附件语法格式（参考 `doc-update.md` 附件节点说明）：

```
:::attachment{src="https://km.sankuai.com/api/file/attachment/<contentId>/<attachmentId>" name="文件名.pdf" size="1.2MB"}:::
```

支持的附件属性：
- `src`：学城附件 URL（上传响应的 `data.url`），**必填**
- `name`：文件名，用于展示（可从本地文件路径中提取），**必填**
- `size`：文件大小（人类可读格式，如 `1.2MB`），可选

## 第四步：回传更新文档

```bash
updateDocumentByMd --contentId <目标文档ID> --content <修改后的CitadelMD>
```

**输出**：返回文档链接，提醒用户刷新页面查看插入的附件。

## 示例 (Example)

用户：帮我把 /tmp/report.pdf 插入到文档 https://km.sankuai.com/collabpage/1234567890 的"附录"章节下面

思考：我需要先上传附件到目标文档，再获取文档内容，由 AI 找到插入位置后更新文档。

```bash
# 第一步：上传附件
uploadAttachmentToDocument --contentId 1234567890 --file "/tmp/report.pdf"

# 第二步：获取文档内容
getDocumentCitadelMd --contentId 1234567890
```

... 获取到 `attachmentMd` 和文档内容后，AI 在"附录"章节下方插入附件语法，然后：

```bash
# 第四步：更新文档
updateDocumentByMd --contentId 1234567890 --content <修改后的CitadelMD>
```

## 禁止事项

- **严禁将非学城附件 URL 直接写入 CitadelMD**，必须先上传取得学城 URL
- 附件上传必须指定目标文档 `contentId`，附件权限与该文档绑定，不可跨文档复用
- **严禁将视频（.mp4/.mov/.avi 等）或音频（.mp3/.wav/.aac/.m4a 等）文件用 `uploadAttachmentToDocument` 上传**。媒体文件必须分别通过 `uploadVideoToDocument` / `uploadAudioToDocument` 上传，否则返回的 URL 为 `/api/file/attachment/` 格式，无法自动转换为播放器所需的 CDN URL，导致文档内媒体无法播放

---

# 将本地视频文件插入学城文档

## 第一步：上传视频到目标文档

```bash
uploadVideoToDocument --contentId <目标文档ID> --file <本地视频文件路径> [--size <文件字节数>]
```

该命令会：
- 以 `multipart/form-data` 方式将本地视频上传到 `POST /api/file/uploadMedia/<contentId>`
- 将响应中的原始附件 URL 转换为 **CDN URL** 格式（`/api/file/cdn/<contentId>/<attachmentId>?contentType=video`）
- 返回 CDN 视频 URL（`url`）、视频附件 ID（`attachmentId`）、转码任务 ID（`jobId`）、文件大小（`size`）及拼装好的 **CitadelMD 视频语法片段**（`videoMd`）

**`--size` 参数说明**：AI 在调用该命令前，应先通过系统工具获取本地文件的字节大小，然后通过 `--size` 传入。这样生成的 `videoMd` 将包含 `size` 属性，学城播放器需要此属性正确渲染视频。

上传接口说明：
- **URL**：`POST https://km.sankuai.com/api/file/uploadMedia/<contentId>`
- **请求**：`multipart/form-data`，字段名 `file`，值为视频文件二进制内容
- **响应**（示例）：
  ```json
  {
    "status": 0,
    "data": {
      "url": "https://km.sankuai.com/api/file/attachment/1440571964/228893075692",
      "attachmentId": 228893075692,
      "jobId": "2037079245415616528"
    }
  }
  ```
- **CDN URL 转换规则**：将响应 `url` 中的 `/api/file/attachment/<contentId>/<attachmentId>` 段提取出 `contentId` 和 `attachmentId`，拼接为 `/api/file/cdn/<contentId>/<attachmentId>?contentType=video`（视频）

## 第二步：获取目标文档内容

```bash
getDocumentCitadelMd --contentId <目标文档ID>
```

获取文档当前完整的 CitadelMD 内容。

## 第三步：由 AI 在指定位置插入视频语法

将第一步返回的 `videoMd`（CitadelMD 视频语法片段）插入到文档 CitadelMD 内容的用户指定位置。

CitadelMD 视频语法格式：

```
:::video{url="https://km.sankuai.com/api/file/cdn/<contentId>/<attachmentId>?contentType=video" name="视频文件名.mp4" size=<字节数>}:::
```

支持的视频属性：
- `url`：学城视频 CDN URL（由 `uploadVideoToDocument` 返回的 `url` 字段），**必填**
- `name`：视频文件名，用于展示，**必填**
- `size`：文件大小（字节数，整数，无引号），学城播放器渲染所需，**强烈建议填写**
- `width`：播放器宽度（可选）
- `height`：播放器高度（可选）

## 第四步：回传更新文档

```bash
updateDocumentByMd --contentId <目标文档ID> --content <修改后的CitadelMD>
```

**输出**：返回文档链接，提醒用户刷新页面查看插入的视频。

> ⚠️ 视频上传后会触发转码（`jobId` 为转码任务 ID），转码完成前视频可能无法正常播放，属于正常现象。

## 示例 (Example)

用户：帮我把 /tmp/demo.mp4 插入到文档 https://km.sankuai.com/collabpage/1234567890 的"演示视频"章节下面

思考：我需要先上传视频到目标文档，再获取文档内容，由 AI 找到插入位置后更新文档。

```bash
# 第一步：先获取文件大小，再上传视频
# AI 应先通过系统工具（如 stat 命令）获取文件字节数
uploadVideoToDocument --contentId 1234567890 --file "/tmp/demo.mp4" --size 52428800

# 第二步：获取文档内容
getDocumentCitadelMd --contentId 1234567890
```

... 获取到 `videoMd` 和文档内容后，AI 在"演示视频"章节下方插入视频语法，然后：

```bash
# 第四步：更新文档
updateDocumentByMd --contentId 1234567890 --content <修改后的CitadelMD>
```

## 禁止事项

- **严禁将非学城视频 URL 直接写入 CitadelMD**，必须先上传取得学城 URL
- 视频上传必须指定目标文档 `contentId`，视频权限与该文档绑定，不可跨文档复用

---

# 将本地音频文件插入学城文档

## 第一步：上传音频到目标文档

```bash
uploadAudioToDocument --contentId <目标文档ID> --file <本地音频文件路径> [--size <文件字节数>]
```

该命令会：
- 以 `multipart/form-data` 方式将本地音频上传到 `POST /api/file/uploadMedia/<contentId>`
- 将响应中的原始附件 URL 转换为 **CDN URL** 格式（`/api/file/cdn/<contentId>/<attachmentId>?contentType=audio`）
- 返回 CDN 音频 URL（`url`）、音频附件 ID（`attachmentId`）、转码任务 ID（`jobId`）、文件大小（`size`）及拼装好的 **CitadelMD 音频语法片段**（`audioMd`）

**`--size` 参数说明**：AI 在调用该命令前，应先通过系统工具获取本地文件的字节大小，然后通过 `--size` 传入，这样生成的 `audioMd` 将包含 `size` 属性。

## 第二步：获取目标文档内容

```bash
getDocumentCitadelMd --contentId <目标文档ID>
```

## 第三步：由 AI 在指定位置插入音频语法

将第一步返回的 `audioMd`（CitadelMD 音频语法片段）插入到文档 CitadelMD 内容的用户指定位置。

CitadelMD 音频语法格式：

```
:::audio{url="https://km.sankuai.com/api/file/cdn/<contentId>/<attachmentId>?contentType=1" name="音频文件名.mp3" size=<字节数>}:::
```

支持的音频属性：
- `url`：学城音频 CDN URL（`/api/file/cdn/<contentId>/<attachmentId>?contentType=1`，由 `uploadAudioToDocument` 返回的 `url` 字段），**必填**
- `name`：音频文件名，用于展示，**必填**
- `size`：文件大小（字节数，整数，无引号），**强烈建议填写**
- `align`：对齐方式（`left` / `center` / `right`，可选）
- `coverImageUrl`：封面图片 URL（可选）

与视频的区别：音频使用 `:::audio{...}:::` 语法，CDN URL 的 `contentType=1`（视频为 `contentType=video`）。

## 第四步：回传更新文档

```bash
updateDocumentByMd --contentId <目标文档ID> --content <修改后的CitadelMD>
```

**输出**：返回文档链接，提醒用户刷新页面查看插入的音频。

## 示例 (Example)

```bash
# 第一步：先获取文件大小，再上传音频
uploadAudioToDocument --contentId 1234567890 --file "/tmp/podcast.mp3" --size 10485760

# 第二步：获取文档内容
getDocumentCitadelMd --contentId 1234567890
```

... 获取到 `audioMd` 和文档内容后，AI 在指定位置插入音频语法，然后：

```bash
# 第四步：更新文档
updateDocumentByMd --contentId 1234567890 --content <修改后的CitadelMD>
```

## 禁止事项

- **严禁将非学城音频 URL 直接写入 CitadelMD**，必须先上传取得学城 URL
- 音频上传必须指定目标文档 `contentId`，音频权限与该文档绑定，不可跨文档复用
