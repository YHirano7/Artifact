# retro-coach

Devin CLI のカスタムサブエージェント定義です。指摘を受けた後の思考補助を行います。

- 渡すもの: 受けた指摘と、そのとき出していたもの
- 返すもの: 次の一手、相手の見方の推定、振り返り（計画・予想・実際・学び）、次に使う問い

## 使い方

1. `retro-coach.md` を、使いたいプロジェクトの `.devin/agents/` に置きます。どのプロジェクトでも使う場合は `%APPDATA%\devin\agents\`（Windows）または `~/.config/devin/agents/`（macOS / Linux）に置きます。
2. Devin のセッションで「retro-coach で見て」のように名前を指定して頼みます。名前を指定しなくても、依頼内容に合えば Devin が自動で選びます。

カスタムサブエージェントは Devin CLI の実験的機能です。形式や挙動は今後変わる可能性があります。

## 同じ系統のエージェント

- `issue-framer` — 着手前（依頼を受けたとき）
- `deliverable-reviewer` — 提出前（下書きができたとき）
- `retro-coach` — 指摘を受けた後
