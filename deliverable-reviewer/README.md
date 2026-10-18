# deliverable-reviewer

Devin CLI のカスタムサブエージェント定義です。提出前の思考補助を行います。

- 渡すもの: 資料・報告文・企画書・相談文の下書き
- 返すもの: 出せるかどうかの判定、受け手の目で見た詰まる箇所、欠けているメッセージ、因果と根拠の検証、比較の構造、持っていき方の下書き

## 使い方

1. `deliverable-reviewer.md` を、使いたいプロジェクトの `.devin/agents/` に置きます。どのプロジェクトでも使う場合は `%APPDATA%\devin\agents\`（Windows）または `~/.config/devin/agents/`（macOS / Linux）に置きます。
2. Devin のセッションで「deliverable-reviewer で見て」のように名前を指定して頼みます。名前を指定しなくても、依頼内容に合えば Devin が自動で選びます。

カスタムサブエージェントは Devin CLI の実験的機能です。形式や挙動は今後変わる可能性があります。

## 同じ系統のエージェント

- `issue-framer` — 着手前（依頼を受けたとき）
- `deliverable-reviewer` — 提出前（下書きができたとき）
- `retro-coach` — 指摘を受けた後
