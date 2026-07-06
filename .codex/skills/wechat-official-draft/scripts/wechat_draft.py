#!/usr/bin/env python3
"""
微信公众号 —— 直连官方 API 发草稿（draft/add）

纯标准库实现，无需第三方平台。用你自己的 AppID + AppSecret。

用法:
  # 1) 测试凭证 / 拿 access_token
  python wechat_draft.py token

  # 2) 发草稿（封面必填，微信要求 thumb_media_id）
  python wechat_draft.py add \
      --md article.md \
      --title "标题" \
      --author "作者" \
      --cover cover.jpg \
      --digest "摘要(可选)" \
      --source-url "https://原文链接(可选)"

凭证读取顺序：命令行 > 环境变量 > 同目录/当前目录的 .env
  WECHAT_APPID / WECHAT_APPSECRET
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request
import uuid

API = "https://api.weixin.qq.com/cgi-bin"


# ---------- 基础工具 ----------
def load_env():
    """从 .env 读取 KEY=VALUE（当前目录、脚本目录）。"""
    paths = [os.path.join(os.getcwd(), ".env"),
             os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")]
    for p in paths:
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def die(msg):
    print(f"错误: {msg}", file=sys.stderr)
    sys.exit(1)


def truncate_bytes(text, max_bytes):
    """按 UTF-8 字节数安全截断（避免微信 45004 摘要过长）。"""
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text
    return data[:max_bytes].decode("utf-8", "ignore")


def http_get_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post_file(url, file_bytes, filename):
    """multipart/form-data 上传，字段名固定为 media。"""
    boundary = "----wxdraft" + uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += (f'Content-Disposition: form-data; name="media"; '
             f'filename="{filename}"\r\n').encode()
    body += f"Content-Type: {ctype}\r\n\r\n".encode()
    body += file_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def check_wx(resp):
    if isinstance(resp, dict) and resp.get("errcode"):
        die(f"微信接口返回 {resp.get('errcode')}: {resp.get('errmsg')}")
    return resp


def read_source(path_or_url):
    """返回 (bytes, filename)，支持本地文件或 http(s) URL。"""
    if re.match(r"^https?://", path_or_url):
        with urllib.request.urlopen(path_or_url, timeout=60) as r:
            data = r.read()
        name = os.path.basename(urllib.parse.urlparse(path_or_url).path) or "image.jpg"
        return data, name
    if not os.path.isfile(path_or_url):
        die(f"找不到文件: {path_or_url}")
    with open(path_or_url, "rb") as f:
        return f.read(), os.path.basename(path_or_url)


# ---------- 微信 API ----------
def get_token():
    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_APPSECRET")
    if not appid or not secret:
        die("缺少 WECHAT_APPID / WECHAT_APPSECRET（命令行参数、环境变量或 .env 均可）")
    url = (f"{API}/token?grant_type=client_credential"
           f"&appid={urllib.parse.quote(appid)}&secret={urllib.parse.quote(secret)}")
    resp = check_wx(http_get_json(url))
    return resp["access_token"]


def upload_permanent_image(token, path_or_url):
    """永久素材（封面用）。返回 media_id。"""
    data, name = read_source(path_or_url)
    url = f"{API}/material/add_material?access_token={token}&type=image"
    resp = check_wx(http_post_file(url, data, name))
    return resp["media_id"]


def upload_content_image(token, path_or_url):
    """正文图片。返回可用于正文的 mmbiz URL。"""
    data, name = read_source(path_or_url)
    url = f"{API}/media/uploadimg?access_token={token}"
    resp = check_wx(http_post_file(url, data, name))
    return resp["url"]


def add_draft(token, article):
    url = f"{API}/draft/add?access_token={token}"
    resp = check_wx(http_post_json(url, {"articles": [article]}))
    return resp["media_id"]


def update_draft(token, media_id, article, index=0):
    """更新已存在草稿的第 index 篇（订阅号可用）。"""
    url = f"{API}/draft/update?access_token={token}"
    return check_wx(http_post_json(
        url, {"media_id": media_id, "index": index, "articles": article}))


def publish_draft(token, media_id):
    """正式发表草稿（订阅号发布能力 freepublish）。"""
    url = f"{API}/freepublish/submit?access_token={token}"
    return check_wx(http_post_json(url, {"media_id": media_id}))


def preview_draft(token, media_id, towxname):
    """把草稿以「图文预览」形式推送到指定微信号（注意：此接口通常仅服务号可用）。"""
    url = f"{API}/message/mass/preview?access_token={token}"
    payload = {"towxname": towxname,
               "mpnews": {"media_id": media_id},
               "msgtype": "mpnews"}
    return check_wx(http_post_json(url, payload))


# ---------- 状态记忆（记住当前处理中的草稿） ----------
STATE_FILE = os.path.join(os.getcwd(), ".wechat_state.json")


def save_state(**kw):
    data = load_state()
    data.update(kw)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_state():
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def resolve_media_id(arg_media_id):
    if arg_media_id:
        return arg_media_id
    mid = load_state().get("media_id")
    if not mid:
        die("未指定 --media-id，且无历史状态。请先 add 或显式传入。")
    return mid


# ---------- 轻量 Markdown -> HTML ----------
def md_to_html(md):
    """优先用 markdown 库；没有则用内置精简转换器。"""
    try:
        import markdown  # type: ignore
        return markdown.markdown(
            md, extensions=["extra", "sane_lists", "nl2br"])
    except Exception:
        return _builtin_md(md)


def _inline(text):
    text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)",
                  lambda m: f'<img src="{m.group(1)}">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def _esc_html(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _esc_code_line(text):
    escaped = _esc_html(text)
    leading = len(escaped) - len(escaped.lstrip(" "))
    if leading:
        escaped = "&nbsp;" * leading + escaped[leading:]
    return escaped or "&nbsp;"


def _wechat_code_block(lines, lang="text"):
    """生成公众号稳定代码块：每行一个 code，避免保存/预览时换行被过滤。"""
    lang = (lang or "text").strip().split()[0]
    if not lang:
        lang = "text"
    code_lines = lines or [""]
    line_numbers = "".join(
        f'<span style="display:block;">{idx}</span>'
        for idx in range(1, len(code_lines) + 1)
    )
    code = "".join(
        '<code style="display:block;white-space:pre-wrap;'
        'font-family:Consolas,Monaco,monospace;font-size:14px;'
        'line-height:1.75;color:#333;background:transparent;'
        'padding:0;margin:0;border:none;">'
        f'{_esc_code_line(line)}</code>'
        for line in code_lines
    )
    return (
        '<pre class="code-snippet_nowrap" '
        f'data-lang="{_esc_html(lang)}" '
        'style="display:block;background:#f7f7f7;border:1px solid #eee;'
        'border-radius:4px;padding:14px 12px;margin:18px 0;'
        'white-space:normal;overflow-x:auto;font-size:14px;'
        'line-height:1.75;font-family:Consolas,Monaco,monospace;">'
        '<span class="line-number" style="display:block;float:left;'
        'color:#c8c8c8;text-align:right;padding-right:12px;'
        f'font-size:14px;line-height:1.75;">{line_numbers}</span>'
        f'{code}</pre>'
    )


def _builtin_md(md):
    out, i = [], 0
    lines = md.split("\n")
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("```"):  # 代码块
            lang = line[3:].strip() or "text"
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append(_wechat_code_block(buf, lang))
            continue
        # 表格：|a|b| 且下一行是 |---|---| 分隔线
        if (line.lstrip().startswith("|") and i + 1 < n
                and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1])):
            def _cells(row):
                return [c.strip() for c in row.strip().strip("|").split("|")]
            headers = _cells(line)
            i += 2
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(_cells(lines[i])); i += 1
            th = "".join(f"<th>{_inline(h)}</th>" for h in headers)
            trs = []
            for idx, r in enumerate(rows):
                tds = "".join(f"<td>{_inline(c)}</td>" for c in r)
                bg = ' style="background:#f2f9f5;"' if idx % 2 == 1 else ""
                trs.append(f"<tr{bg}>{tds}</tr>")
            out.append(f"<table><thead><tr>{th}</tr></thead>"
                       f"<tbody>{''.join(trs)}</tbody></table>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lv = len(m.group(1))
            out.append(f"<h{lv}>{_inline(m.group(2))}</h{lv}>")
            i += 1; continue
        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                content = _inline(re.sub(r"^\s*[-*+]\s+", "", lines[i]))
                items.append(f"<li>{content}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                content = _inline(re.sub(r"^\s*\d+\.\s+", "", lines[i]))
                items.append(f"<li>{content}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>"); continue
        if line.startswith(">"):
            text = line.lstrip("> ").rstrip()
            text = re.sub(r"^\[!\w+\]\s*", "", text)  # 去掉 GitHub 提示块标记 [!NOTE] 等
            out.append(f"<blockquote>{_inline(text)}</blockquote>")
            i += 1; continue
        if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", line):
            out.append("<hr>"); i += 1; continue
        if line.strip() == "":
            i += 1; continue
        out.append(f"<p>{_inline(line)}</p>")
        i += 1
    return "\n".join(out)


def rewrite_images(token, html, base_dir):
    """把正文里的 <img src> 上传到微信并替换（跳过已是 mmbiz 的）。"""
    def repl(m):
        src = m.group(1)
        if "mmbiz.qpic.cn" in src:
            return m.group(0)
        target = src
        if not re.match(r"^https?://", src):
            target = os.path.join(base_dir, src)
        try:
            new_url = upload_content_image(token, target)
            print(f"  上传正文图片: {src} -> {new_url}")
            return m.group(0).replace(src, new_url)
        except SystemExit:
            print(f"  警告: 图片上传失败，保留原链接: {src}", file=sys.stderr)
            return m.group(0)
    return re.sub(r'<img[^>]*src="([^"]+)"', repl, html)


# ---------- 内联排版样式（微信会剥离 <style>/class，必须内联） ----------
# 绿色主题，字号/行距为公众号阅读优化。
ACCENT = "#35b378"
BASE_STYLE = ("font-family:-apple-system,'Optima','PingFang SC','Microsoft YaHei',"
              "sans-serif;font-size:16px;color:#3f3f3f;line-height:1.75;"
              "letter-spacing:.5px;word-break:break-word;")
TAG_STYLES = {
    "h1": "font-size:22px;font-weight:bold;color:#222;margin:26px 0 18px;text-align:center;",
    "h2": (f"font-size:19px;font-weight:bold;color:#fff;background:{ACCENT};"
           "display:inline-block;padding:5px 14px;border-radius:4px;margin:28px 0 16px;"),
    "h3": (f"font-size:17px;font-weight:bold;color:{ACCENT};"
           f"border-left:4px solid {ACCENT};padding-left:10px;margin:24px 0 12px;"),
    "h4": "font-size:16px;font-weight:bold;color:#333;margin:20px 0 10px;",
    "p": "margin:16px 0;line-height:1.85;",
    "blockquote": (f"border-left:4px solid {ACCENT};background:#f6fbf8;color:#666;"
                   "padding:12px 16px;margin:18px 0;border-radius:0 4px 4px 0;font-size:15px;"),
    "ul": "padding-left:1.4em;margin:16px 0;",
    "ol": "padding-left:1.4em;margin:16px 0;",
    "li": "margin:8px 0;line-height:1.75;",
    "hr": "border:none;border-top:1px solid #e6e6e6;margin:26px 0;",
    "strong": f"color:{ACCENT};font-weight:bold;",
    "em": "font-style:italic;color:#555;",
    "a": f"color:{ACCENT};text-decoration:none;border-bottom:1px solid {ACCENT};",
    "img": "max-width:100%;display:block;margin:18px auto;border-radius:6px;",
    "table": "width:100%;border-collapse:collapse;margin:18px 0;font-size:14px;",
    "th": (f"border:1px solid #cfe9dd;background:{ACCENT};color:#fff;"
           "padding:8px 10px;text-align:left;font-weight:bold;"),
    "td": "border:1px solid #e6e6e6;padding:8px 10px;color:#3f3f3f;",
}
PRE_STYLE = ("background:#2d2d2d;color:#e6e6e6;padding:16px;border-radius:6px;"
             "white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;"
             "font-size:14px;line-height:1.6;margin:18px 0;"
             "font-family:Consolas,Monaco,'Courier New',monospace;")
CODE_RESET = "background:transparent;color:inherit;padding:0;font-size:14px;"
CODE_INLINE = ("background:#f2f2f2;color:#c0341d;padding:2px 6px;border-radius:3px;"
               "font-size:14px;font-family:Consolas,Monaco,'Courier New',monospace;")


def apply_inline_styles(html):
    """给已生成的 HTML 各标签注入内联样式，兼容 markdown 库与内置转换器。"""
    code_blocks = []

    def protect_code_block(m):
        code_blocks.append(m.group(0))
        return f"@@WECHAT_CODE_BLOCK_{len(code_blocks) - 1}@@"

    html = re.sub(
        r'<pre class="code-snippet_nowrap".*?</pre>',
        protect_code_block,
        html,
        flags=re.S,
    )
    # 代码块：先处理 <pre><code>，避免内部 code 被行内样式污染
    html = re.sub(r"<pre>\s*<code[^>]*>",
                  f'<pre style="{PRE_STYLE}"><code style="{CODE_RESET}">', html)
    # 行内 code（无属性的才是行内）
    html = html.replace("<code>", f'<code style="{CODE_INLINE}">')
    # 其余标签（带或不带已有属性，如 <a href>、<img src>）
    for tag, style in TAG_STYLES.items():
        html = re.sub(rf"<{tag}(\s[^>]*)?>",
                      lambda m, s=style, t=tag: f'<{t}{m.group(1) or ""} style="{s}">',
                      html)
    html = f'<section style="{BASE_STYLE}">{html}</section>'
    for idx, block in enumerate(code_blocks):
        html = html.replace(f"@@WECHAT_CODE_BLOCK_{idx}@@", block)
    return html


# ---------- CLI ----------
def cmd_token(_):
    print(get_token())


def cmd_preview(args):
    token = get_token()
    resp = preview_draft(token, args.media_id, args.to)
    print(f"✅ 已推送预览到微信号 {args.to}")
    print(f"   msg_id={resp.get('msg_id')}  返回: {resp.get('errmsg', 'ok')}")


def build_article(token, args, thumb_media_id=None):
    """读取 md → 转 HTML → 内联样式 → 上传正文图 → 组装 article 字典。
    thumb_media_id 传入则复用（update 场景），否则用 --cover 上传。"""
    if args.appid:
        os.environ["WECHAT_APPID"] = args.appid
    if args.secret:
        os.environ["WECHAT_APPSECRET"] = args.secret
    if not os.path.isfile(args.md):
        die(f"找不到 markdown 文件: {args.md}")
    with open(args.md, encoding="utf-8") as f:
        md = f.read()

    html = md_to_html(md)
    # 去掉正文首个 H1（微信用 title 字段单独显示标题，避免重复）
    html = re.sub(r"<h1[^>]*>.*?</h1>", "", html, count=1, flags=re.S)
    if not args.no_style:
        html = apply_inline_styles(html)
    html = rewrite_images(token, html, os.path.dirname(os.path.abspath(args.md)))

    if thumb_media_id is None:
        if not args.cover:
            die("需要封面：首次 add 必须传 --cover")
        thumb_media_id = upload_permanent_image(token, args.cover)
        print(f"封面已上传，thumb_media_id={thumb_media_id}")

    raw_digest = args.digest or re.sub(r"<[^>]+>", "", html)
    digest = truncate_bytes(raw_digest.strip(), 120)  # 微信 digest 上限 120 字节
    article = {
        "title": args.title[:64],
        "author": args.author or "",
        "digest": digest,
        "content": html,
        "content_source_url": args.source_url or "",
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 1 if args.open_comment else 0,
        "only_fans_can_comment": 1 if args.fans_only_comment else 0,
    }
    return article, thumb_media_id


def cmd_add(args):
    token = get_token()
    print("已获取 access_token")
    article, thumb = build_article(token, args)
    draft_id = add_draft(token, article)
    save_state(media_id=draft_id, thumb_media_id=thumb, title=article["title"],
               md=os.path.abspath(args.md))
    print(f"\n✅ 草稿已创建！draft media_id = {draft_id}（已记入 .wechat_state.json）")
    print("下一步：到后台『草稿箱 → 预览』推送到手机确认；改用 update，发布用 publish。")


def cmd_update(args):
    token = get_token()
    print("已获取 access_token")
    media_id = resolve_media_id(args.media_id)
    st = load_state()
    # 未给新封面则复用上次的 thumb_media_id
    thumb = None
    if not args.cover:
        thumb = st.get("thumb_media_id")
        if not thumb:
            die("无历史封面，请用 --cover 指定封面")
    article, thumb = build_article(token, args, thumb_media_id=thumb)
    update_draft(token, media_id, article)
    save_state(media_id=media_id, thumb_media_id=thumb, title=article["title"],
               md=os.path.abspath(args.md))
    print(f"\n✅ 草稿已更新（media_id={media_id}）。到后台『草稿箱 → 预览』再看一次。")


def cmd_publish(args):
    token = get_token()
    media_id = resolve_media_id(args.media_id)
    if not args.yes:
        die("发布是正式发表操作。确认无误请加 --yes 再执行。")
    resp = publish_draft(token, media_id)
    print(f"\n🚀 已提交发表！publish_id={resp.get('publish_id')}  {resp.get('errmsg','ok')}")
    print("发表为异步，稍后可在后台『发表记录』查看结果。")


def cmd_state(_):
    st = load_state()
    if not st:
        print("（无状态）")
        return
    for k, v in st.items():
        print(f"{k}: {v}")


def main():
    load_env()
    p = argparse.ArgumentParser(description="微信公众号官方 API 发草稿")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("token", help="获取 access_token（测试凭证/IP白名单）").set_defaults(func=cmd_token)

    pv = sub.add_parser("preview", help="把草稿预览推送到指定微信号")
    pv.add_argument("--media-id", required=True, help="草稿 media_id")
    pv.add_argument("--to", required=True, help="接收预览的微信号")
    pv.set_defaults(func=cmd_preview)

    def add_content_args(sp, cover_required):
        sp.add_argument("--md", required=True, help="markdown 文件路径")
        sp.add_argument("--title", required=True, help="标题（≤64字）")
        sp.add_argument("--cover", required=cover_required,
                        help="封面图（本地路径或URL）" + ("，首次必填" if cover_required else "，不填则复用上次"))
        sp.add_argument("--author", default="", help="作者")
        sp.add_argument("--digest", default="", help="摘要，留空则自动截取正文")
        sp.add_argument("--source-url", dest="source_url", default="", help="原文链接")
        sp.add_argument("--appid", help="覆盖 WECHAT_APPID")
        sp.add_argument("--secret", help="覆盖 WECHAT_APPSECRET")
        sp.add_argument("--open-comment", action="store_true", help="开启留言")
        sp.add_argument("--fans-only-comment", action="store_true", help="仅粉丝可留言")
        sp.add_argument("--no-style", action="store_true", help="不注入内联排版样式")

    a = sub.add_parser("add", help="从 markdown 新建草稿")
    add_content_args(a, cover_required=True)
    a.set_defaults(func=cmd_add)

    u = sub.add_parser("update", help="更新已存在的草稿（默认取上次的 media_id）")
    add_content_args(u, cover_required=False)
    u.add_argument("--media-id", help="草稿 media_id（默认取 .wechat_state.json）")
    u.set_defaults(func=cmd_update)

    pub = sub.add_parser("publish", help="正式发表草稿（需 --yes）")
    pub.add_argument("--media-id", help="草稿 media_id（默认取 .wechat_state.json）")
    pub.add_argument("--yes", action="store_true", help="确认发表")
    pub.set_defaults(func=cmd_publish)

    sub.add_parser("state", help="查看当前记忆的草稿状态").set_defaults(func=cmd_state)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
