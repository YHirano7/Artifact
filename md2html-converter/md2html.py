#!/usr/bin/env python3
"""md2html — Markdown (+ Mermaid) を固定デザインの単一HTMLに変換するローカルツール.

依存: pip install markdown pygments
使い方:
    python md2html.py doc.md                  # doc.html を同じ場所に出力
    python md2html.py docs/ -o dist/          # ディレクトリを一括変換（構造を維持）
    python md2html.py doc.md --embed-images   # ローカル画像をbase64で埋め込み（1ファイルで配布可）
    python md2html.py doc.md --mermaid-js ./mermaid.min.js   # mermaidをインライン化（完全オフライン）
    python md2html.py docs/ -o dist/ --watch  # 変更を監視して自動再変換
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import mimetypes
import re
import sys
import time
from pathlib import Path

try:
    import markdown
    from markdown.extensions import Extension
    from markdown.preprocessors import Preprocessor
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import TextLexer, get_lexer_by_name
    from pygments.util import ClassNotFound
except ImportError:
    sys.exit("依存ライブラリがありません: pip install markdown pygments")

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
LIGHT_CODE_STYLE = "friendly"
DARK_CODE_STYLE = "monokai"


# ---------------------------------------------------------------- Markdown 拡張
class FencePreprocessor(Preprocessor):
    """フェンス付きコードを自前で処理する.

    - ```mermaid → <pre class="mermaid">（ブラウザ側で描画）
    - それ以外   → Pygments でハイライト
    標準の fenced_code はリスト内のフェンスを扱えないため、インデント付きでも拾う。
    """

    FENCE = re.compile(
        r"^(?P<indent>[ ]*)(?P<fence>`{3,}|~{3,})[ \t]*(?P<lang>[\w+#.-]*)[^\n]*\n"
        r"(?P<code>.*?)(?<=\n)(?P=indent)(?P=fence)[ \t]*$",
        re.MULTILINE | re.DOTALL,
    )

    def run(self, lines):
        text = "\n".join(lines)

        def repl(m: re.Match) -> str:
            indent, lang = m.group("indent"), m.group("lang").lower()
            code = "\n".join(
                ln[len(indent):] if ln.startswith(indent) else ln.lstrip(" ")
                for ln in m.group("code").removesuffix("\n").split("\n")
            )
            if lang == "mermaid":
                block = ('<figure class="mermaid-wrap">'
                         f'<pre class="mermaid">{html.escape(code)}</pre></figure>')
            else:
                try:
                    lexer = get_lexer_by_name(lang) if lang else TextLexer()
                except ClassNotFound:
                    lexer = TextLexer()
                block = highlight(code + "\n", lexer, HtmlFormatter(cssclass="hl", wrapcode=True))
                if lang:
                    block = block.replace('<div class="hl">',
                                          f'<div class="hl" data-lang="{html.escape(lang)}">', 1)
            return f"\n{indent}{self.md.htmlStash.store(block)}\n"

        return self.FENCE.sub(repl, text).split("\n")


class FenceExtension(Extension):
    def extendMarkdown(self, md):
        # 標準 fenced_code_block（優先度25）より先に走らせる
        md.preprocessors.register(FencePreprocessor(md), "md2html_fence", 30)


# ---------------------------------------------------------------- 前処理・後処理
def split_front_matter(text: str) -> tuple[dict, str]:
    """YAML風フロントマター（key: value の単純形式のみ）を分離する."""
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip().strip("'\"")
    return meta, text[m.end():]


LIST_ITEM = re.compile(r"^([ \t]*)([-*+]|\d+[.)])[ \t]+")
FENCE_LINE = re.compile(r"^[ \t]*(`{3,}|~{3,})")


def normalize_list_indent(text: str) -> str:
    """GitHub流の2〜3スペースのネストを、Python-Markdownが要求する4スペース単位へ揃える."""
    out, stack = [], []          # stack: 各ネスト階層の元インデント幅
    fence, fence_delta = None, 0
    for line in text.split("\n"):
        expanded = line.expandtabs(4)
        indent = len(expanded) - len(expanded.lstrip(" "))

        if fence:                                     # フェンス内は開始行と同じだけずらす
            if FENCE_LINE.match(line) and expanded.strip().startswith(fence):
                fence = None
            out.append(_shift(expanded, fence_delta) if stack else line)
            continue

        if not line.strip():
            out.append(line)
            continue

        m = LIST_ITEM.match(expanded)
        if m:
            while stack and stack[-1] > indent:
                stack.pop()
            if not stack or stack[-1] != indent:
                stack.append(indent)
            new_indent = 4 * (len(stack) - 1)
        elif indent == 0:
            stack = []                                # リストの外に出た
            new_indent = 0
        elif stack:                                   # 継続行: 親項目の1段下に置く
            depth = sum(1 for s in stack if s < indent)
            new_indent = 4 * depth
        else:
            new_indent = indent

        delta = new_indent - indent
        fm = FENCE_LINE.match(line)
        if fm:
            fence, fence_delta = fm.group(1), delta
        out.append(_shift(expanded, delta) if stack else line)
    return "\n".join(out)


def _shift(line: str, delta: int) -> str:
    if delta >= 0:
        return " " * delta + line
    strip = min(-delta, len(line) - len(line.lstrip(" ")))
    return line[strip:]


ALERT_TYPES = {
    "NOTE": "Note", "TIP": "Tip", "IMPORTANT": "Important",
    "WARNING": "Warning", "CAUTION": "Caution",
}


def postprocess(body: str, src_dir: Path, embed_images: bool) -> str:
    # タスクリスト: <li>[ ] / <li>[x]（段落入りリストにも対応）
    def task(m: re.Match) -> str:
        checked = " checked" if m.group(2).lower() == "x" else ""
        return f'{m.group(1)}<input type="checkbox" disabled{checked}> '

    body = re.sub(r"(<li>(?:\s*<p>)?)\[([ xX])\]\s", task, body)
    body = body.replace("<li><input", '<li class="task"><input')
    body = re.sub(r"<li>(\s*<p>)<input", r'<li class="task">\1<input', body)

    # GitHub形式のアラート: > [!NOTE]
    def alert(m: re.Match) -> str:
        kind = m.group(1).upper()
        return (f'<blockquote class="alert alert-{kind.lower()}">\n'
                f'<p class="alert-title">{ALERT_TYPES[kind]}</p>\n<p>')

    body = re.sub(
        r"<blockquote>\s*<p>\[!(" + "|".join(ALERT_TYPES) + r")\]\s*(?:<br\s*/?>)?\s*",
        alert, body, flags=re.IGNORECASE,
    )
    body = body.replace("<p>\n</p>", "").replace("<p></p>", "")

    # 表は横スクロールできるようラップ
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>")

    # 画像: 遅延読み込み + 任意でbase64埋め込み
    def img(m: re.Match) -> str:
        tag, src = m.group(0), m.group(1)
        if embed_images and not re.match(r"^(https?:|data:|//)", src):
            path = (src_dir / html.unescape(src)).resolve()
            if path.is_file():
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                data = base64.b64encode(path.read_bytes()).decode()
                tag = tag.replace(f'src="{src}"', f'src="data:{mime};base64,{data}"')
            else:
                print(f"  ! 画像が見つかりません: {src}", file=sys.stderr)
        return tag.replace("<img ", '<img loading="lazy" ', 1)

    body = re.sub(r'<img [^>]*?src="([^"]+)"[^>]*>', img, body)
    return body


# ---------------------------------------------------------------- テンプレート
def code_css() -> str:
    light = HtmlFormatter(style=LIGHT_CODE_STYLE).get_style_defs(".hl")
    dark = HtmlFormatter(style=DARK_CODE_STYLE).get_style_defs(":root.dark .hl")
    def scoped(css: str, prefix: str) -> str:
        # pygments が出す非スコープの pre/linenos 規則と背景色はテンプレート側に任せる
        keep = [ln for ln in css.splitlines()
                if ln.startswith(prefix + " .") and "{ background:" not in ln]
        return "\n".join(keep)

    return scoped(light, ".hl") + "\n" + scoped(dark, ":root.dark .hl")


TEMPLATE_CSS = r"""
:root{
  --bg:#fbfaf7; --surface:#ffffff; --text:#1f2328; --muted:#5f6670; --border:#e4e1da;
  --accent:#2f5d8a; --accent-soft:#e8eef5; --code-bg:#f4f2ed; --mark:#fff1b8;
  --note:#2f5d8a; --tip:#2e7d4f; --important:#6b4fa3; --warning:#9a6700; --caution:#b42318;
  --font: "Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic UI","Meiryo",system-ui,sans-serif;
  --mono: "SFMono-Regular","JetBrains Mono","Consolas","Menlo",ui-monospace,monospace;
}
:root.dark{
  --bg:#15171a; --surface:#1c1f23; --text:#e6e6e3; --muted:#9aa1a9; --border:#2d3238;
  --accent:#8db4dc; --accent-soft:#1f2a36; --code-bg:#22262b; --mark:#5a4a12;
  --note:#8db4dc; --tip:#6cc08b; --important:#b49ae6; --warning:#e0b04a; --caution:#f07a6e;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth; scroll-padding-top:24px}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);
  font-size:16px;line-height:1.85;letter-spacing:.02em;-webkit-font-smoothing:antialiased;
  font-feature-settings:"palt" 1}
.layout{display:grid;grid-template-columns:minmax(0,1fr);max-width:1180px;margin:0 auto;padding:0 16px}
@media (min-width:1100px){.layout.has-toc{grid-template-columns:240px minmax(0,1fr);gap:56px}}

/* ヘッダ */
.doc-header{padding:56px 0 28px;border-bottom:1px solid var(--border);margin-bottom:36px}
.doc-header h1{font-size:2rem;line-height:1.4;margin:0 0 12px;letter-spacing:.01em}
.doc-meta{color:var(--muted);font-size:.85rem}
.doc-meta span+span::before{content:"·";margin:0 .6em}

/* 目次 */
.toc{font-size:.85rem;line-height:1.6}
.toc-inner{position:sticky;top:24px;max-height:calc(100vh - 48px);overflow:auto;padding:56px 0 24px}
.toc-title{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.toc ul{list-style:none;margin:0;padding:0}
.toc ul ul{padding-left:12px}
.toc a{display:block;padding:4px 10px;color:var(--muted);text-decoration:none;border-left:2px solid var(--border)}
.toc a:hover{color:var(--text)}
.toc a.active{color:var(--accent);border-left-color:var(--accent);background:var(--accent-soft)}
@media (max-width:1099px){
  .toc-inner{position:static;max-height:none;padding:0;margin:24px 0 0;
    border:1px solid var(--border);border-radius:8px;background:var(--surface)}
  .toc details{padding:10px 14px}
  .toc summary{cursor:pointer;color:var(--muted);font-weight:600}
  .toc-title{display:none}
}
@media (min-width:1100px){ .toc summary{display:none} }

/* 本文 */
main{min-width:0;max-width:780px;padding-bottom:96px}
.content h2{font-size:1.45rem;margin:2.6em 0 .8em;padding-bottom:.35em;border-bottom:1px solid var(--border);line-height:1.45}
.content h3{font-size:1.18rem;margin:2em 0 .6em;line-height:1.5}
.content h4{font-size:1rem;margin:1.6em 0 .5em}
.content h1{font-size:1.7rem;margin:2em 0 .8em}
.content :is(h1,h2,h3,h4) .headerlink{margin-left:.4em;color:var(--border);text-decoration:none;opacity:0;transition:opacity .15s}
.content :is(h1,h2,h3,h4):hover .headerlink{opacity:1;color:var(--muted)}
.content p,.content ul,.content ol,.content dl{margin:0 0 1.15em}
.content li{margin:.25em 0}
.content li > ul,.content li > ol{margin:.25em 0 0}
.content a{color:var(--accent);text-underline-offset:3px;text-decoration-thickness:1px}
.content strong{font-weight:700}
.content mark{background:var(--mark);color:inherit;padding:0 .15em;border-radius:2px}
.content hr{border:0;border-top:1px solid var(--border);margin:3em 0}
.content img{max-width:100%;height:auto;border-radius:6px}
.content li.task{list-style:none;margin-left:-1.4em}
.content li.task input{margin:0 .5em 0 0;accent-color:var(--accent);transform:translateY(1px)}

.content blockquote{margin:0 0 1.2em;padding:.6em 1.1em;border-left:3px solid var(--border);color:var(--muted);background:var(--surface);border-radius:0 6px 6px 0}
.content blockquote > :last-child{margin-bottom:0}
.alert{--c:var(--note);border-left-color:var(--c)!important;color:var(--text)!important}
.alert-title{font-weight:700;color:var(--c);margin:0 0 .3em!important;font-size:.9rem;letter-spacing:.04em}
.alert-tip{--c:var(--tip)} .alert-important{--c:var(--important)}
.alert-warning{--c:var(--warning)} .alert-caution{--c:var(--caution)}

/* コード */
.content code{font-family:var(--mono);font-size:.86em;background:var(--code-bg);padding:.15em .4em;border-radius:4px}
.content pre{margin:0 0 1.3em;background:var(--code-bg);border:1px solid var(--border);border-radius:8px;padding:14px 16px;overflow:auto;line-height:1.6}
.content pre code{background:none;padding:0;font-size:.84rem}
.content .hl{background:none}

/* 表 */
.table-wrap{overflow-x:auto;margin:0 0 1.4em;border:1px solid var(--border);border-radius:8px}
.content table{border-collapse:collapse;width:100%;font-size:.92rem;line-height:1.6}
.content th,.content td{padding:9px 14px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}
.content th{background:var(--surface);font-weight:700;white-space:nowrap}
.content tr:last-child td{border-bottom:0}
.content tbody tr:nth-child(even){background:color-mix(in srgb,var(--surface) 55%,transparent)}

/* Mermaid */
.mermaid-wrap{margin:0 0 1.6em;padding:20px;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow-x:auto;text-align:center}
.content pre.mermaid{background:none;border:0;padding:0;margin:0;overflow:visible;font-family:var(--mono);font-size:.82rem;color:var(--muted);white-space:pre;text-align:left}
.content pre.mermaid[data-processed]{white-space:normal;text-align:center;font-family:var(--font)}
.content pre.mermaid svg{max-width:100%;height:auto}
.mermaid-error{color:var(--caution);font-size:.85rem;text-align:left;white-space:pre-wrap}

/* 脚注 */
.footnote{margin-top:3em;font-size:.88rem;color:var(--muted)}
.footnote hr{margin:0 0 1em}

/* テーマ切替 */
.theme-toggle{position:fixed;right:16px;bottom:16px;width:40px;height:40px;border-radius:50%;
  border:1px solid var(--border);background:var(--surface);color:var(--muted);cursor:pointer;font-size:16px;line-height:1}
.theme-toggle:hover{color:var(--text)}

@media (max-width:640px){
  body{font-size:15px}
  .doc-header{padding-top:32px}
  .doc-header h1{font-size:1.55rem}
}
@media print{
  :root{--bg:#fff}
  .toc,.theme-toggle,.headerlink{display:none!important}
  .layout{display:block;max-width:none;padding:0}
  main{max-width:none}
  .content pre,.mermaid-wrap,.table-wrap,figure{break-inside:avoid}
  .content a{color:inherit}
}
"""

TEMPLATE_JS = r"""
(function(){
  var root=document.documentElement, KEY='md2html-theme';
  function stored(){try{return localStorage.getItem(KEY)}catch(e){return null}}
  function apply(t){root.classList.toggle('dark',t==='dark')}
  var t=stored()||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
  apply(t);
  window.__md2html={toggle:function(){
    t=root.classList.contains('dark')?'light':'dark'; apply(t);
    try{localStorage.setItem(KEY,t)}catch(e){}
    renderMermaid();
  }};
  var sources=null;
  function renderMermaid(){
    if(!window.mermaid) return;
    var nodes=document.querySelectorAll('pre.mermaid');
    if(!sources) sources=[].map.call(nodes,function(n){return n.textContent});
    nodes.forEach(function(n,i){n.removeAttribute('data-processed'); n.textContent=sources[i];});
    var dark=root.classList.contains('dark');
    mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:dark?'dark':'neutral',
      fontFamily:getComputedStyle(document.body).fontFamily});
    mermaid.run({nodes:nodes,suppressErrors:true}).catch(function(e){console.error(e)});
  }
  window.addEventListener('DOMContentLoaded',function(){
    renderMermaid();
    // 目次のハイライト
    var links=[].slice.call(document.querySelectorAll('.toc a'));
    if(!links.length||!('IntersectionObserver' in window)) return;
    var map={}; links.forEach(function(a){map[decodeURIComponent(a.hash.slice(1))]=a});
    var obs=new IntersectionObserver(function(es){
      es.forEach(function(e){ if(e.isIntersecting){
        links.forEach(function(a){a.classList.remove('active')});
        var a=map[e.target.id]; if(a) a.classList.add('active');
      }});
    },{rootMargin:'0px 0px -70% 0px'});
    Object.keys(map).forEach(function(id){var h=document.getElementById(id); if(h) obs.observe(h)});
  });
})();
"""

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="md2html">
<title>{title}</title>
<style>{css}</style>
<style>{code_css}</style>
<script>{js}</script>
{mermaid_script}
</head>
<body>
<div class="layout{layout_class}">
{toc}
<main>
<header class="doc-header">
<h1>{title}</h1>
<div class="doc-meta">{meta}</div>
</header>
<article class="content">
{body}
</article>
</main>
</div>
<button class="theme-toggle" type="button" onclick="__md2html.toggle()" aria-label="テーマ切替">◐</button>
</body>
</html>
"""


# ---------------------------------------------------------------- 変換本体
def build_markdown() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=[
            FenceExtension(),
            "extra",          # tables / fenced_code / footnotes / attr_list / def_list / abbr / md_in_html
            "codehilite",
            "toc",
            "sane_lists",
        ],
        extension_configs={
            "codehilite": {"css_class": "hl", "guess_lang": False},
            "toc": {"permalink": "#", "toc_depth": "2-3", "slugify": slugify},
        },
    )


def slugify(value: str, separator: str) -> str:
    """日本語見出しでも空にならないslug."""
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", separator, value) or "section"


def convert(src: Path, dst: Path, opts) -> None:
    text = src.read_text(encoding="utf-8")
    meta, body_md = split_front_matter(text)

    # タイトル: front matter > 先頭の H1（本文から除去）> ファイル名
    title = meta.get("title")
    h1 = re.match(r"^\s*#\s+(.+?)\s*#*\s*$", body_md, re.MULTILINE)
    if h1 and not body_md[: h1.start()].strip():
        title = title or h1.group(1)
        body_md = body_md[h1.end():]
    title = title or src.stem

    body_md = normalize_list_indent(body_md)

    # Python-Markdown は空行を挟んだ引用を1つに結合するため、アラート開始行の前で区切る
    body_md = re.sub(r"(?m)^(>[ \t]*\[!(?:" + "|".join(ALERT_TYPES) + r")\])",
                     r"<!-- -->\n\n\1", body_md, flags=re.IGNORECASE)

    md = build_markdown()
    body = postprocess(md.convert(body_md), src.parent, opts.embed_images)

    toc_html = ""
    has_toc = opts.toc and len(md.toc_tokens) + sum(len(t["children"]) for t in md.toc_tokens) >= 3
    if has_toc:
        toc_html = (
            '<nav class="toc" aria-label="目次"><div class="toc-inner"><details open>'
            '<summary>目次</summary><p class="toc-title">Contents</p>'
            f"{md.toc}</details></div></nav>"
        )

    meta_items = []
    for key in ("author", "date"):
        if meta.get(key):
            meta_items.append(f"<span>{html.escape(meta[key])}</span>")
    if not meta.get("date"):
        mtime = dt.datetime.fromtimestamp(src.stat().st_mtime)
        meta_items.append(f"<span>更新 {mtime:%Y-%m-%d}</span>")

    if "pre class=\"mermaid\"" not in body:
        mermaid_script = ""
    elif opts.mermaid_js:
        mermaid_script = f"<script>{Path(opts.mermaid_js).read_text(encoding='utf-8')}</script>"
    else:
        mermaid_script = f'<script src="{MERMAID_CDN}"></script>'

    page = PAGE.format(
        lang=meta.get("lang", "ja"),
        title=html.escape(title),
        css=TEMPLATE_CSS,
        code_css=code_css(),
        js=TEMPLATE_JS,
        mermaid_script=mermaid_script,
        layout_class=" has-toc" if has_toc else "",
        toc=toc_html,
        meta="".join(meta_items),
        body=body,
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(page, encoding="utf-8")
    print(f"✓ {src} → {dst}")


def collect_jobs(inputs: list[str], output: str | None) -> list[tuple[Path, Path]]:
    jobs = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            out_root = Path(output) if output else p
            for f in sorted(p.rglob("*.md")):
                jobs.append((f, (out_root / f.relative_to(p)).with_suffix(".html")))
        elif p.is_file():
            if output and (Path(output).suffix.lower() == ".html") and len(inputs) == 1:
                dst = Path(output)
            elif output:
                dst = Path(output) / p.with_suffix(".html").name
            else:
                dst = p.with_suffix(".html")
            jobs.append((p, dst))
        else:
            print(f"! 見つかりません: {raw}", file=sys.stderr)
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown(+Mermaid) → 単一HTML 変換ツール")
    ap.add_argument("inputs", nargs="+", help=".md ファイルまたはディレクトリ")
    ap.add_argument("-o", "--output", help="出力先（.html ファイル or ディレクトリ）")
    ap.add_argument("--embed-images", action="store_true", help="ローカル画像をbase64で埋め込む")
    ap.add_argument("--mermaid-js", metavar="PATH", help="mermaid.min.js をインライン化（オフライン用）")
    ap.add_argument("--no-toc", dest="toc", action="store_false", help="目次を出さない")
    ap.add_argument("--watch", action="store_true", help="変更を監視して再変換")
    opts = ap.parse_args()

    jobs = collect_jobs(opts.inputs, opts.output)
    if not jobs:
        return 1

    def run(targets):
        for src, dst in targets:
            try:
                convert(src, dst, opts)
            except Exception as e:  # 1ファイルの失敗で全体を止めない
                print(f"✗ {src}: {e}", file=sys.stderr)

    run(jobs)
    if not opts.watch:
        return 0

    print("監視中… (Ctrl+C で終了)")
    stamps = {s: s.stat().st_mtime for s, _ in jobs}
    try:
        while True:
            time.sleep(1)
            jobs = collect_jobs(opts.inputs, opts.output)  # 新規ファイルも拾う
            changed = []
            for s, d in jobs:
                m = s.stat().st_mtime
                if stamps.get(s) != m:
                    stamps[s] = m
                    changed.append((s, d))
            run(changed)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
