# issue-framer

Devin CLI のカスタムサブエージェント定義です。着手前の思考補助を行います。

- 渡すもの: 依頼文、タスク、企画の種
- 返すもの: 目的の一文、答えるべき論点、埋まっている前提、依頼者への確認事項（案つき）、調べ方と止めどころ、作業の割り付け

## 使い方

1. `issue-framer.md` を、使いたいプロジェクトの `.devin/agents/` に置きます。どのプロジェクトでも使う場合は `%APPDATA%\devin\agents\`（Windows）または `~/.config/devin/agents/`（macOS / Linux）に置きます。
2. Devin のセッションで「issue-framer で見て」のように名前を指定して頼みます。名前を指定しなくても、依頼内容に合えば Devin が自動で選びます。

カスタムサブエージェントは Devin CLI の実験的機能です。形式や挙動は今後変わる可能性があります。

## 同じ系統のエージェント

- `issue-framer` — 着手前（依頼を受けたとき）
- `deliverable-reviewer` — 提出前（下書きができたとき）
- `retro-coach` — 指摘を受けた後
