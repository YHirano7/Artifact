# llm-inference-and-decoding

LLMの推論実行と出力制御の仕組み（「①PrefillとDecodeの物理的・計算的違いとKVキャッシュ管理」→「②LogitsからのサンプリングとConstrained Decoding」→「③Test-Time ComputeとReasoning強化学習」）を、エージェントハーネス側の設計（「KVキャッシュヒット率10倍差」「Response PrefillによるLogitマスク」「Extended / Interleaved Thinking」）と結びつけて体系的に学ぶ4段階のインフォグラフィックです。

| ファイル | 難易度 | 答える問い | 結論 |
|---|---|---|---|
| `inference-rank-0-beginner` | 初級（Rank 0） | LLMがプロンプトを読んで1語ずつ返し、JSONを守り、考えて答えるまでに裏側で何が起きているか | LLMの応答は「まとめ読み（Prefill）→ 1語ずつの確率くじ引き（Decode）」の反復であり、計算メモ（KVキャッシュ）・違反くじ除外（Logitマスク）・下書き（思考トークン）の3つで制御する |
| `inference-rank-1-intermediate` | 中級（Rank I） | なぜPrefillとDecodeでボトルネックが180度逆転し、FlashAttention・PagedAttention・GQAはどうやってMemory Wallと断片化を突破するのか | Prefillは「計算律速（行列×行列）」、Decodeは「HBM帯域律速（行列×ベクトル）」であり、SRAMタイリング・OS型ページング・KVヘッド共有で壁を突破する |
| `inference-rank-2-advanced` | 上級（Rank II） | ハーネス側の「KVキャッシュ10倍差」と「100%構造化出力」は、推論エンジン内部でどう実装され、どこで破綻するのか | KVキャッシュ10倍差は「連鎖ブロックハッシュ／Radix木」で実装され、100%構造化出力は「FSM語彙インデックス・PDA文脈独立キャッシュ」で高速化される |
| `inference-rank-3-special` | 特級（Rank III） | なぜ `<think>` トークンで14倍巨大なモデルを凌駕でき、GRPOはどうやって自己検証を創発させ、ハーネス側のThinking制御とどう噛み合うのか | 思考トークンはKVキャッシュを作業記憶として消費する「直列テスト時計算」であり、GRPOが価値関数と累積KL罰則を撤廃したことで自己検証が創発する |

`inference-rank-0-beginner`（初級）→ `inference-rank-1-intermediate`（中級）→ `inference-rank-2-advanced`（上級）→ `inference-rank-3-special`（特級）の順にステップアップします。

## ファイル形式

- `.png` — 横2100px相当を2倍解像度（幅4200px）で出力した画像
