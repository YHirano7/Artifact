# llm-internal-circuits-infographics

LLMがプロンプト文字列を受け取ってから内部表現を作り次の1語を予測するまでの仕組み（「①トークナイザ（BPE / Unigram / トークン化の罠）→ ②Embeddingと位置符号化（RoPE / ALiBi / NTK / YaRN）→ ③Transformer内部の回路（Residual Stream、Self-AttentionのInduction Heads・メタ勾配によるIn-Context Learningの発現機構、FFN/MLP層のKey-Value記憶とROME知識編集）」）を、原典論文と一次解説に基づいて初級〜特級の4段階ステップアップのインフォグラフィックにまとめたものです。

| ファイル | ランク | 答える問い | 結論 |
|---|---|---|---|
| `00-rank-0-beginner` | 初級（Rank 0） | 文字列から次の一語が出るまでに内部で何が起きているか | ①文字をトークン番号に割り → ②意味ベクトル＋位置の時計針（RoPE）を付け → ③共有黒板（Residual Stream）の上で「文脈を写すAttention」と「知識を引くFFN」を交互に足し算して次の1語を予測する |
| `01-rank-1-intermediate` | 中級（Rank I） | なぜ推論以前の段階（算術・多言語・Glitch）で失敗し、位置はどう相対距離化されるか | 推論以前の失敗は「トークン分割境界の不一致（L2R/R2L・多言語格差）」と「未学習埋め込み（Glitch Tokens）」で起き、位置情報は「RoPEの2次元回転行列」で内積の相対距離（m−n）へ変換される |
| `02-rank-2-advanced` | 上級（Rank II） | なぜ学習長を超えると破綻してYaRNで回復し、どう2層回路が創発するか | 外挿の破綻は「臨界次元（第92次元）以降の未学習角度」と「均一補間での高周波喪失」で起き、内部では「Residual Stream上のK-Composition」が2層でInduction Head（`[A][B]…[A]→[B]`）を創発させる |
| `03-rank-3-special` | 特級（Rank III） | なぜ重み更新なしで文脈学習でき、事実知識はどこに宿りどう編集できるか | In-Context Learningは「Induction Headの相転移」と「Attention＝メタ勾配の双対性（および実モデルでの反証）」で説明され、事実知識は「主語終端×中期MLP層のKey-Value連想メモリ」に局在しランク1更新（ROME）で直接書き換えられる |

`00`（初級）が数式なしの全体地図になっており、`01`（中級）→ `02`（上級）→ `03`（特級）の順に原典論文の数理・回路分解・測定データへ深く入ります。

## ファイル形式

- `.png` — 横2100px相当を2倍解像度（幅4200px）で出力した画像
- `.html` — PNGの元になった単体HTML。外部リソースを参照しないため、ブラウザで開けばそのまま表示できます。修正する場合はHTMLを編集し、headless Chromeでスクリーンショットを撮り直してください

## 主な出典（各図の下部にも記載）

- **① トークナイザとトークン化の罠**: Sennrich et al. (ACL 2016, arXiv:1508.07909) / Kudo (ACL 2018, arXiv:1804.10959) / Kudo & Richardson (EMNLP 2018, arXiv:1808.06226) / Karpathy "minbpe & Let's build the GPT Tokenizer" (2024) / Singh & Strouse (2024, arXiv:2402.14903) / Petrov et al. (NeurIPS 2023, arXiv:2305.15425) / Ali et al. (2023, arXiv:2310.08754) / Rumbelow & Watkins "SolidGoldMagikarp" (2023)
- **② 位置符号化と長文脈拡張**: Su et al. "RoFormer" (2021, arXiv:2104.09864) / Press et al. "ALiBi" (ICLR 2022, arXiv:2108.12409) / Chen et al. "Position Interpolation" (2023, arXiv:2306.15595) / Peng et al. "YaRN" (ICLR 2024, arXiv:2309.00071) / EleutherAI Blog "Extending the RoPE" (2023) / Liu et al. "Scaling Laws of RoPE-based Extrapolation" (ICLR 2024, arXiv:2310.05209)
- **③ Transformer Circuits・ICL・FFN記憶・ROME**: Elhage et al. "A Mathematical Framework for Transformer Circuits" (Anthropic 2021) / Olsson et al. "In-context Learning and Induction Heads" (Anthropic 2022, arXiv:2209.11895) / Elhage et al. "Privileged Bases" (Anthropic 2023) / Crosbie & Shutova (2024, arXiv:2407.07011) / Bietti et al. (NeurIPS 2023, arXiv:2306.00802) / Reddy (ICLR 2024, arXiv:2312.03002) / Dai et al. (ACL Findings 2023, arXiv:2212.10559) / Von Oswald et al. (ICML 2023, arXiv:2212.07677) / Akyürek et al. (ICLR 2023, arXiv:2211.15661) / Shen et al. (ICML 2024, arXiv:2310.08540) / Geva et al. (EMNLP 2021, arXiv:2012.14913; EMNLP 2022) / Dai et al. "Knowledge Neurons" (ACL 2022, arXiv:2104.08696) / Meng, Bau et al. "ROME" (NeurIPS 2022, arXiv:2202.05262)
