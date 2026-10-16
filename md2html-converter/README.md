# md2html

Markdown（Mermaid 図を含む）を、固定デザインの単一 HTML に変換するローカル CLI。

## セットアップ

```bash
pip install markdown pygments
```

## 使い方

```bash
python md2html.py doc.md                    # doc.html を同じ場所に出力
python md2html.py doc.md -o out.html        # 出力ファイル名を指定
python md2html.py docs/ -o dist/            # ディレクトリを一括変換（構造を維持）
python md2html.py doc.md --embed-images     # ローカル画像を base64 埋め込み（1ファイル配布向け）
python md2html.py docs/ -o dist/ --watch    # 保存のたびに自動再変換
```

### 完全オフラインで使う場合

既定では Mermaid を CDN（jsDelivr, v11）から読み込みます。ネットワークに出られない環境や、HTML を単体で配る場合は一度だけ取得してインライン化します。

```bash
curl -L -o mermaid.min.js https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js
python md2html.py doc.md --mermaid-js mermaid.min.js
```

（1 ファイルあたり約 3MB 増えます）

## 対応記法

| 記法 | 備考 |
|---|---|
| ```` ```mermaid ```` | ブラウザ側で描画。ライト/ダークに追従 |
| コードブロック | Pygments でビルド時ハイライト。リスト内のフェンスも可 |
| 表 / 脚注 / 定義リスト / attr_list | Python-Markdown `extra` |
| タスクリスト `- [ ]` `- [x]` | |
| GitHub アラート `> [!NOTE]` 等 | NOTE / TIP / IMPORTANT / WARNING / CAUTION |
| フロントマター | `title` `author` `date` `lang`（単純な key: value のみ） |
| 2〜3 スペースのネストリスト | 4 スペースへ自動正規化 |

タイトルは「フロントマターの title → 先頭の `# 見出し` → ファイル名」の順で決まり、見出しが 3 つ以上あれば目次を生成します（`--no-toc` で無効化）。

## デザインの変更

テンプレートは `md2html.py` 内の `TEMPLATE_CSS`（色は `:root` / `:root.dark` のトークン）と `PAGE` に集約しています。コードの配色は `LIGHT_CODE_STYLE` / `DARK_CODE_STYLE`（Pygments のスタイル名）で差し替えられます。

## 既知の制約

- 同じ階層で `-` リストと `1.` リストを混在させると、後者が前の項目の本文として扱われる（Python-Markdown の仕様）
- フロントマターは YAML の完全なパーサではない（リスト・ネスト不可）
