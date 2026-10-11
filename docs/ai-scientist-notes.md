# AI Scientist v1 / v2 実装メモ

Task 001（`docs/tasks/001-vendor-ai-scientist.md`）の確認結果。確認日：2026-09-21。
行番号はすべて下記の固定コミットに対するもの。

| | リポジトリ | 固定コミット | コミット日 | 配置 |
|---|---|---|---|---|
| v1 | SakanaAI/AI-Scientist | `1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb` | 2025-12-19 | `vendor/AI-Scientist` |
| v2 | SakanaAI/AI-Scientist-v2 | `96bd51617cfdbb494a9fc283af00fe090edfae48` | 2025-12-19 | `vendor/AI-Scientist-v2` |

---

## 1. v1 の新規性チェック（条件 A）

対象：`vendor/AI-Scientist/ai_scientist/generate_ideas.py`

### README の記載との照合

| README の記載 | 結果 | 根拠 |
|---|---|---|
| 埋め込み・コサイン類似度は使わず、LLM が検索クエリを書き、上位 10 件の要旨を読んで主観的に判断（最大 10 ラウンド） | ✅ 一致 | L356–371（system msg）、L410 `max_num_iterations=10`、L462 `result_limit=10` |
| "Decision made: novel." / "not novel." の文字列で判定。決まらなければ `novel = False` | ✅ 一致 | L448–454（`text.lower()` で部分一致）、L426 |
| クエリは「論文名や著者を思い出せると最もうまく働く」と指示 | ✅ 一致 | L401 |
| 出力は二値のみ | ✅ 一致 | L485 `idea["novel"] = novel` |
| システムプロンプトに `experiment.py` が丸ごと入る | ✅ 一致 | L368–370、読み込みは L413–414 |
| Semantic Scholar と OpenAlex を切り替えられる | ✅ 一致 | L285 `engine=`、L288 / L311 |

### README に未記載の事実（研究設計に影響するもの）

1. **生成時の自己評価スコアが判定プロンプトに入る。**
   L436 で `idea=idea`（dict 全体）がそのまま埋め込まれる。生成時の idea JSON には `"Interestingness"`・`"Feasibility"`・`"Novelty"`（1–10 の自己評価、L45–47）が含まれるため、判定 LLM は「生成側が自分で付けた新規性スコア」を見たうえで判定している（アンカリングの可能性）。
   → 評価セット（実在論文由来）ではこれらのフィールドをどう扱うかを決める必要がある（揃える／外す／固定値）。

2. **検索結果に「現在の」被引用数が表示される。**
   L295 で `citationCount` を取得し、L475 でプロンプトに `Number of citations` として出す。OpenAlex でも L344 `cited_by_count`。
   → 時点 t で切った評価では、t 以降に蓄積した被引用数という**事後情報がプロンプトに漏れる**。検索の出版年制限だけでは防げない。

3. **検索に出版年のフィルタがない。** Semantic Scholar（L289–297）、OpenAlex（L348）とも query と件数のみ。t での制限はラッパー側で実装する必要がある。

4. **OpenAlex を使ってもプロンプトは「Semantic Scholar API」と言う。** L359 は固定文言。実害は小さいが、改変として明記するかは要判断。

5. **エラーは黙ってラウンドを消費する。** L481–483 で例外をすべて握りつぶして `continue`。
   - JSON 抽出失敗（L458 の assert）も 1 ラウンド消費
   - 検索 0 件時は L463 で `papers_str = "No papers found."` を入れた直後、L467 で `enumerate(None)` が TypeError → except に落ちる。結果として "No papers found." は次ラウンドに渡るが、意図した挙動ではなく偶然動いている
   - 失敗が続くと 10 ラウンドを使い切り `novel = False`。**API 障害が「新規でない」判定に化ける**ため、ログから失敗ラウンド数を集計する必要がある

6. **結果を `base_dir/ideas.json` に書き出す。** L488–490。`base_dir` を `vendor/` 内のテンプレートにすると submodule を汚す。ラッパーでは `src/` 側の作業ディレクトリ（`experiment.py` と `prompt.json` を置く）を渡すこと。

7. **温度は 0.75。** `ai_scientist/llm.py` L150（`get_response_from_llm` のデフォルト）。複数回判定して「新規と判定された割合」を連続スコアにする方針と整合する。ただし o1 / o3 系は temperature=1・seed=0 固定（`llm.py` L200–212）。

8. **既に `"novel"` キーを持つアイデアはスキップ。** L420–422。反復判定時はキーを外してから渡す。

### 参考：Automated Reviewer（4-3 で使用）

- v1：`ai_scientist/perform_review.py` の `perform_review`（L126〜）。`"Originality"`（1–4）を含む NeurIPS 形式のスコアと `"Decision"`（Accept / Reject）を出す（L47、L59）
- デフォルトは `num_reviews_ensemble=1`（L131）。Nature 版の「5 本のアンサンブル」は引数で指定する想定
- `Originality` スコアは 4-4 の「AI の事前判断」の連続値として使える可能性がある
- **要確認：** Nature 版は o4-mini を使ったとされるが、固定コミットの `AVAILABLE_LLMS`（`llm.py` L13〜）に o4-mini はない。論文の実験コードは公開版と異なる可能性がある

---

## 2. v2 の新規性確認

対象：`vendor/AI-Scientist-v2/ai_scientist/perform_ideation_temp_free.py`、`ai_scientist/tools/semantic_scholar.py`

### 結論：独立した新規性判定器は存在しない

- 新規性の確認は、アイデア生成ループ（`generate_temp_free_idea`、L128–266）の中で、LLM が `SearchSemanticScholar` を行動として選ぶことでのみ行われる。行動は `SearchSemanticScholar` と `FinalizeIdea` の 2 つだけ（L24–39）
- **二値の novel ラベルも数値スコアもない。** 最終アイデアの JSON は Name / Title / Short Hypothesis / Related Work / Abstract / Experiments / Risk Factors and Limitations のみ（L30–37）。v1 の Interestingness / Feasibility / Novelty も消えている
- 「新規でない」アイデアを捨てる処理はない。新規性はプロンプトでの指示（L61「make sure they are novel」、L113 の reflection）と、LLM が検索結果を読んで自分で修正することに委ねられている
- 検索は「確定前に少なくとも 1 回」とプロンプトで求めるだけで、強制されない（L96）
- リポジトリ全体を `novel` で検索しても、判定ロジックはない（ヒットはプロンプト文言と査読器のみ）
- → README の記載（独立した判定器がないので 4-1・4-3 には使えない）と一致

### 検索の仕組み（`tools/semantic_scholar.py`）

- Semantic Scholar の `/paper/search` のみ。OpenAlex への切り替えはない（L65–73）
- 取得後に **現在の被引用数の降順で並べ替える**（L84）。v1 は API の関連度順のまま
  → 被引用数の多い（＝事後に成功した）論文が上位に来るため、時点 t の評価では v1 より事後情報の影響が強い
- 出版年フィルタなし（v1 と同じ）

---

## 3. LICENSE

### 事実

- **v1・v2 とも Apache 2.0 ではない。** 固定コミット時点では、両者の LICENSE は同一ファイルの「The AI Scientist Source Code License, Version 1.0, December 2025」（Responsible AI Source Code License v1.1 の派生）
- 変更履歴：
  - v1：`2906fcb`（2025-12-19）「Update license from Apache 2.0 to AI Scientist License 1.0」。それまでは Apache 2.0
  - v2：`c204ee8`（2025-12-19）「Update LICENSE」。初回コミット（2025-04-08）は Apache 2.0
- **ライセンス変更の前後でコードは同一。** 変更直前（v1 `9dffdc4`、v2 `defddb8`）から固定コミットまでの差分は `LICENSE` と `README.md` のみ
- Nature 論文の「両方 Apache 2.0」という記載は、変更前の状態を指していると考えられる（推測）

### 修論に関係しうる条項

- **3.2(e)「AI Scientist 条項」：** 「機械生成であること、または The AI Scientist を使って作成したことを、目立つ形（アブストラクト、Disclosure／Methods 節など）で明示せずに、科学論文・研究論文・技術報告を生成または頒布すること」を禁止
- **3.1：** コードの一部を頒布する場合は、ライセンス全文を同梱する
- **3.3：** 派生物の利用・頒布に関する契約には、3.2 の制限を組み込む
- **4：** 制限に違反した場合、ライセンサーはライセンスを終了できる
- README（v1 L391–395、v2 L203–207）は「本コードを使った場合、成果物の論文で AI の使用を明示する法的義務がある」と、条文より広く読める書き方をしている

### 判断が必要な点（りけ・指導教員）→ 末尾「未決事項」参照

---

## 4. 依存関係（v1 の新規性チェックだけを動かす場合）

**PyTorch・GPU なしで動く。** 使い捨ての環境（Python 3.12）で `from ai_scientist.generate_ideas import check_idea_novelty, search_for_papers` が成功し、`torch` は読み込まれなかった（API 呼び出しはしていない）。

最小構成：

| パッケージ | 理由 |
|---|---|
| `openai` | `ai_scientist/llm.py` L7（トップレベル import） |
| `anthropic` | `llm.py` L5（トップレベル import。使わなくても必要） |
| `google-generativeai` | `llm.py` L8–9（トップレベル import。**非推奨パッケージ**で import 時に警告が出る） |
| `backoff` | `generate_ideas.py` L7、`llm.py` L6 |
| `requests` | `generate_ideas.py` L8 |
| `pyalex` | OpenAlex を使う場合のみ（L312 で遅延 import） |

- `requirements.txt` の `torch`・`transformers`・`aider-chat` などは実験実行と論文執筆用で、新規性チェックには不要
- `perform_review.py`（4-3 で使う）は、追加で `numpy`・`pypdf`・`pymupdf`・`pymupdf4llm` を import する（L2–6）
- 注意：`google-generativeai` は非推奨パッケージのため、将来インストールできなくなる可能性がある。`uv.lock` でバージョンを固定すること

---

## 未決事項（りけの判断が必要）

1. **固定コミットをどちらにするか**
   - (a) 現在の HEAD（独自ライセンス）：いま固定しているもの
   - (b) ライセンス変更の直前（v1 `9dffdc4`、v2 `defddb8`）：Apache 2.0 で公開された版で、コードは (a) と同一
   - いずれにしても、修論の Methods で AI Scientist の使用を明記するのが安全
2. **ライセンス 3.2(e) の解釈を指導教員とどう確認するか**：修論本文は機械生成ではないが、AI Scientist が生成したアイデアを分析対象にし、図表や例として掲載する
3. **条件 A の公平性のための改変の範囲**：自己評価スコアの扱い（§1-1）、被引用数の表示（§1-2）、検索の出版年制限（§1-3）、プロンプトの「Semantic Scholar」という文言（§1-4）
