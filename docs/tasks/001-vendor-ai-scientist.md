# Task 001: AI Scientist v1 / v2 の取得と実装確認

## 目的

条件 A（元の新規性チェック）を正確に再現するため、AI Scientist のコードをローカルに固定し、実物で仕組みを確認する。
ウェブ経由で v1 は確認済みだが、v2 の `ai_scientist/` 内は自動アクセスが拒否されて未確認。

## やること

1. `vendor/` に git submodule として追加する
   - v1: https://github.com/SakanaAI/AI-Scientist
   - v2: https://github.com/SakanaAI/AI-Scientist-v2
   - 現時点の `main` のコミットハッシュを README の「データ・環境」表に記録する
   - **`vendor/` 内のコードは編集しない**

2. v1 の確認（README の Step 4 冒頭「条件 A の実装上の事実」と照合）
   - `ai_scientist/generate_ideas.py` の `check_idea_novelty` と `search_for_papers`
   - 記載内容とずれがあれば報告する

3. v2 の確認
   - `ai_scientist/perform_ideation_temp_free.py`：新規性の確認がどこで、どう行われているか
   - `ai_scientist/tools/semantic_scholar.py`：検索の仕組み
   - 独立した新規性判定器（外部のアイデアを判定できる関数）が存在するか
   - 二値の novel ラベルや数値スコアを出しているか

4. LICENSE の確認
   - v1 / v2 それぞれの LICENSE ファイルの種類
   - AI 使用の開示義務など、修論でコードを改変・利用する際の義務があるか
   - Nature 論文（両方 Apache 2.0 と記載）と v2 README（独自ライセンスと記載）の食い違いの実態

5. 依存関係の確認
   - v1 の新規性チェックだけを動かすのに必要な最小限のパッケージ（GPU・PyTorch なしで動くか）

## 成果物

- `docs/ai-scientist-notes.md`：上記 2〜5 の確認結果（該当ファイル・行番号付き）
- README の更新（コミットハッシュ、確認結果で事実が違った箇所）
- CLAUDE.md の「現在地」の更新

## 注意

- API キー（OpenAI、S2 など）が必要な実行はまだしない。今回はコードを読むだけ
- 判断が必要な点（ライセンス上の懸念など）は、勝手に決めずにりけに報告する
