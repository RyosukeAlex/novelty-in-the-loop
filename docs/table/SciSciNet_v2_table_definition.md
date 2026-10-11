# SciSciNet-v2 テーブル定義書

本研究が実際にクエリする **BigQuery 公開データセット `ksm-rch-scisciturbo.sciscinet_v2`（US リージョン、非パーティション）** の定義。

- **一次情報**：`INFORMATION_SCHEMA.COLUMNS`（列）と `__TABLES__`（行数・サイズ）を自分で抽出（`sql/get-columns.sql`, `sql/count_rows.sql`）。抽出日 2025-10-12。
- v1（MAG 版、`SciSciNet_v1_table_definition.md`）とは **ID 体系・テーブル構成が別物**。ID は OpenAlex（`W...`/`C...`/author・institution ID）。
- 「（要確認）」は実データ確認（Step 1 のデータ辞書）で埋める欄。指標定義の背景は v1 定義書 §4 も参照。
- 主要カラムの意味は **§「実データ確認の結果」** で検証済み（`sql/explore/01〜04`、2025-10-12 実行）。
  **とくに `disruption = 0` と `C5`/`C10` の切り詰めは研究の妥当性に直接響くので、使う前に必ず読むこと。**

## テーブル一覧（30件・行数降順）

| テーブル | 行数 | サイズ | 概要 |
|---|---:|---:|---|
| `sciscinet_paperrefs` | 2,494,545,461 | 115.9 GB | 引用ペア。過去ベクトル（参考文献）・未来ベクトル（被引用）の源 |
| `sciscinet_paperfields` | 1,271,891,157 | 38.4 GB | 論文×分野の対応（1論文が複数分野）。分野絞り込みに使う |
| `sciscinet_authors_paperid` | 772,984,433 | 30.5 GB | 論文×著者（軽量版） |
| `sciscinet_paper_author_affiliation` | 772,984,433 | 29.7 GB | 論文×著者×所属（著者順つき） |
| `hit_papers_level1` | 701,627,506 | 42.1 GB | 中分野(level1)での被引用上位フラグ |
| `normalized_citations_level1` | 701,627,506 | 42.1 GB | 中分野での正規化被引用数 |
| `hit_papers_level0` | 570,263,651 | 34.2 GB | 大分野(level0)での被引用上位フラグ |
| `normalized_citations_level0` | 570,263,651 | 34.2 GB | 大分野での正規化被引用数 |
| `sciscinet_paperdetails` | 249,803,279 | 311.2 GB | 論文の詳細。title/abstract/is_retracted/is_paratext も保持 |
| `sciscinet_papers` | 249,803,279 | 45.4 GB | 主論文テーブル。既存の新規性・破壊性指標が同居（第2章の比較対象） |
| `sciscinet_papersources` | 204,111,441 | 17.4 GB | 論文×掲載媒体（OA可否・ライセンス・PDF URL） |
| `sciscinet_papertitleabstract` | 122,351,775 | 251.2 GB | タイトルと要旨（転置インデックス）。テキスト特徴量の源 |
| `sciscinet_author_details` | 100,418,971 | 15.5 GB | 著者詳細（ORCID・所属など） |
| `sciscinet_authors` | 100,418,971 | 7.8 GB | 著者マスタ（h-index・性別推定など） |
| `sciscinet_link_patents` | 47,844,586 | 1.6 GB | 論文×特許 |
| `sciscinet_link_nih` | 6,546,840 | 162.6 MB | 論文×NIH助成 |
| `sciscinet_papers_pmid_pmcid` | 6,281,193 | 471.1 MB | 論文の外部ID対応（PMID/PMCID/MAG） |
| `sciscinet_link_nsf` | 1,769,355 | 44.0 MB | 論文×NSF助成 |
| `sciscinet_link_newsfeed` | 1,409,842 | 68.6 MB | 論文×ニュース |
| `sciscinet_newsfeed_metadata` | 1,409,842 | 274.1 MB | ニュース言及のメタ情報 |
| `sciscinet_link_clinicaltrials` | 612,587 | 15.2 MB | 論文×臨床試験 |
| `sciscinet_nih_metadata` | 533,653 | 65.7 MB | NIH助成のメタ情報 |
| `sciscinet_nsf_metadata` | 459,837 | 55.9 MB | NSF助成のメタ情報 |
| `sciscinet_clinicaltrials_metadata` | 273,269 | 104.2 MB | 臨床試験のメタ情報 |
| `sciscinet_sources` | 260,811 | 25.2 MB | 掲載媒体マスタ（ジャーナル・会議等） |
| `sciscinet_affiliations` | 110,553 | 13.7 MB | 機関マスタ |
| `sciscinet_link_nobellaureates` | 87,316 | 2.4 MB | 論文×ノーベル賞受賞者 |
| `sciscinet_affl_assoc_affl` | 39,239 | 1.2 MB | 機関の関連機関 |
| `funders` | 32,437 | 67.1 MB | ファンダー（助成機関）マスタ。ネストした STRUCT 多数 |
| `sciscinet_fields` | 303 | 131.2 KB | 分野マスタ（OpenAlex concept、303件・小さい） |

---

## 実データ確認の結果

`sql/explore/01〜04`（計 42.2 GB スキャン、2025-10-12 実行）で検証した。結果の CSV は `data/explore/0*.csv`。

### 1. `doctype` の値（8種・NULL なし）

| 値 | 件数 |
|---|---:|
| `article` | 197,751,962 |
| `book-chapter` | 22,339,557 |
| `dataset` | 7,553,839 |
| `preprint` | 6,518,309 |
| `dissertation` | 6,090,358 |
| `book` | 5,634,421 |
| `review` | 3,891,267 |
| `retraction` | 23,566 |

合計が 249,803,279 と一致するため **`doctype` に NULL は存在しない**（v1 では NULL あり）。
`retraction` は撤回通知そのもの。**ML 研究の対象は `article` と `preprint`**（arXiv 版を含めるかは設計判断）。

### 2. `cited_by_count` と `citation_count` の違い

1950–2024 年の 241,900,598 本で比較：

| 関係 | 件数 | 割合 |
|---|---:|---:|
| `cited_by_count = citation_count` | 216,921,633 | 89.7% |
| `cited_by_count > citation_count` | 23,443,385 | 9.7% |
| `cited_by_count < citation_count` | 1,535,580 | 0.6% |

**解釈**：`cited_by_count` は OpenAlex 側のグローバル被引用数（コーパス外からの引用も含む）、
`citation_count` は SciSciNet の論文集合内で再計算した値。ゆえに通常 `cited_by_count >= citation_count`。
一致率が古い年で低く（1995 年 82.1%）新しい年で高い（2024 年 97.6%）のは、
新しい論文は双方とも 0 に近く差が出にくいため。

> **使い分け**：引用ネットワークの解析（過去/未来ベクトル）は `paperrefs` と整合する
> `citation_count` を使う。外部との比較や全体的なインパクトは `cited_by_count`。
> 0.6% の逆転があるため完全な包含関係ではない（スナップショット時点の差と推測）。

### 3. `C3` / `C5` / `C10` — 0 は「引用なし」。ただし新しい年は切り詰められている

- **NULL は全年で 0 件。** 欠損を NULL で表現していない。
- **累積性を確認**：`C5 < C3` と `C10 < C5` がともに **全年で 0 件** → `C3 <= C5 <= C10` が常に成立。
- よって **0 は「その窓の中で観測された引用が 0」** の意味であり、「未計算」ではない。

> ⚠️ **ただし窓が閉じていない年では値が過小になる。** データは実質 2024 年までしかないため、
> 窓の残りが埋まらない。証拠として、`C3 = 0` の件数と `C10 = 0` の件数が近年で一致する：
>
> | 年 | `C3 = 0` | `C10 = 0` |
> |---|---:|---:|
> | 2020 | 6,107,255 | 5,910,045 |
> | 2021 | 5,069,718 | 5,069,713 |
> | 2022 | 5,126,266 | 5,126,266 |
> | 2023 | 6,088,502 | 6,088,502 |
> | 2024 | 6,577,495 | 6,577,495 |
>
> 2022 年以降は完全一致＝**10 年窓も 3 年窓も同じ長さしか取れていない**。
> **目安：`C3` は 2021 年まで、`C5` は 2019 年まで、`C10` は 2014 年までの論文でのみ窓が閉じている。**
> それ以降の論文で使うと系統的に過小評価になる。

### 4. `disruption` は 0 がプレースホルダ、`Atyp_*` は NULL — 欠損の表現がカラムで違う

1950–2024 年の 241,900,598 本：

| 項目 | 件数 | 割合 |
|---|---:|---:|
| `disruption IS NULL` | **0** | 0% |
| `disruption = 0` | 178,746,649 | 73.9% |
| └ うち `reference_count = 0` | 152,656,651 | 0 の 85.4% |
| `Atyp_Median_Z IS NULL` | 182,724,955 | 75.5% |

> 🚨 **研究上の罠。** D-index は前方引用と後方引用の両方を必要とするため、参考文献 0 件の論文では
> **定義できない**。にもかかわらず v2 は NULL ではなく **0 を入れている**（1.53 億本）。
> `disruption = 0` を「破壊的でない」と解釈すると、定義不能なケースを大量に混入させる。
>
> **対策：`disruption` を使うときは必ず `reference_count > 0 AND cited_by_count > 0` で絞る。**
> 第2章で D-index を比較対象にする際の前提条件とする。

一方 `Atyp_Median_Z` / `Atyp_10pct_Z` は **NULL を正しく使っている**（75.5% が NULL）。
**同じテーブル内で欠損の表現方法が統一されていない**ため、カラムごとに扱いを変える必要がある。
`Atyp_Pairs = 0` は年あたり 1〜1.6 万件程度で、NULL とは別の意味（ペアが取れなかった）。

### 5. `score_openalex` の分布 — 閾値 0.5 は ML では上位 7% を切る

| 分野 | ペア数 | max | p25 | p50 | p75 | p90 | `>= 0.5` の件数 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `C119857082` Machine learning | 3,845,961 | 0.923 | 0.000 | **0.056** | 0.350 | **0.460** | **262,620 (6.8%)** |
| `C41008148` Computer science | 83,225,522 | 1.000 | 0.254 | 0.333 | 0.437 | 0.607 | 14,918,391 (17.9%) |

- **ML の score は CS より大幅に低い**。中央値 0.056、最大でも 0.923（1.0 に届かない）。
- **閾値 0.5 は ML の p90（0.460）より上** → 残るのは全期間で 262,620 ペア（6.8%）のみ。
- NULL は 0 件。ただし p25 までが 0.000 で、**score がちょうど 0 のペアが大量に存在する**
  （なぜ 0 のペアが登録されるのかは別途要確認）。

> **設計への示唆（Step 1.5）**：README は `score_openalex >= 0.5` を案としているが、
> これは「上位 7% を取る非常に厳しい閾値」である。分野によって分布形が違うため、
> 固定値ではなく **分位点ベース（例：その分野の p90）** で決める方が分野間の比較が公平になる。
> 絶対数（全期間 26 万ペア）はパイロットの想定規模（数千〜数万本）には足りるので、
> README のタスク通り **サンプルのタイトルを見て閾値を決める**のが妥当。

### 6. `papers` と `paperdetails` は同一の論文集合（撤回はフラグで区別）

| | `papers` | `paperdetails` |
|---|---:|---:|
| 行数 | 249,803,279 | 249,803,279 |
| `is_retracted = true` | **50,101** | **50,101** |
| `is_retracted IS NULL` | 0 | 0 |
| `is_paratext = true` | （列なし） | **0** |
| `is_paratext IS NULL` | （列なし） | 0 |

- 行数・撤回件数が**完全一致** → **v2 は両テーブルが同じ論文集合を持ち、撤回を `is_retracted` で区別する設計**。
  v1（撤回論文を `paperdetails` 側にのみ保持）から**変わっている**。
- **`is_paratext` は全件 false**（NULL もなし）＝ v2 では実質機能していない列。フィルタに使っても何も落ちない。
- 撤回論文の内訳（`doctype` 別）：`article` 46,300 / `review` 1,856 / `retraction` 1,154 /
  `book-chapter` 716 / `preprint` 62 / `book` 11 / `dissertation` 2。
- 撤回は全体の 0.02% と小さいが、**第2章の指標算出では除外するか明示的に設計する**（v1 定義書 §5-8 も同趣旨）。

---

## テーブル定義

## コア（本研究で主に使う）

### `sciscinet_papers`

主論文テーブル。既存の新規性・破壊性指標が同居（第2章の比較対象）

- 行数: 249,803,279 / サイズ: 45.4 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `doi` | STRING | DOI |
| 3 | `year` | INT64 | 出版年 |
| 4 | `date` | STRING | 出版日（STRING、`YYYY-MM-DD`） |
| 5 | `doctype` | STRING | 文献種別。8種・NULLなし：`article` / `book-chapter` / `dataset` / `preprint` / `dissertation` / `book` / `review` / `retraction`（→ §1） |
| 6 | `cited_by_count` | INT64 | **OpenAlex 側のグローバル被引用数**（コーパス外の引用も含む）。通常 `>= citation_count`（→ §2） |
| 7 | `is_retracted` | BOOL | 撤回論文フラグ。**true は 50,101 件**（papers/paperdetails で一致）。v2 は撤回も本表に含める（→ §6） |
| 8 | `reference_count` | INT64 | 参考文献数 |
| 9 | `citation_count` | INT64 | **コーパス内で再計算した被引用数**。`paperrefs` と整合するのはこちら（→ §2） |
| 10 | `C3` | INT64 | 出版後3年の累積被引用数。**NULLなし・0は「引用なし」**。⚠️窓が閉じるのは2021年まで（→ §3） |
| 11 | `C5` | INT64 | 出版後5年の累積被引用数。⚠️**窓が閉じるのは2019年まで**。以降は過小（→ §3） |
| 12 | `C10` | INT64 | 出版後10年の累積被引用数。⚠️**窓が閉じるのは2014年まで**。以降は過小（→ §3） |
| 13 | `disruption` | FLOAT64 | Disruption指数（D-index）。🚨**NULLなし・73.9%が0で、その85%は参考文献0件＝定義不能**。使用時は `reference_count > 0 AND cited_by_count > 0` で絞る（→ §4） |
| 14 | `Atyp_Median_Z` | FLOAT64 | 参照ペアZ-scoreの中央値＝典型性（Uzzi et al. 2013）。**欠損はNULL**（75.5%）。`disruption` と欠損表現が違う（→ §4） |
| 15 | `Atyp_10pct_Z` | FLOAT64 | 同10パーセンタイル＝tail novelty。**欠損はNULL**（→ §4） |
| 16 | `Atyp_Pairs` | INT64 | 引用したジャーナルペア数。`0` はNULLとは別の意味（年1〜1.6万件、→ §4） |
| 17 | `WSB_mu` | FLOAT64 | WSBモデル 即時性 μ |
| 18 | `WSB_sigma` | FLOAT64 | WSBモデル 寿命 σ |
| 19 | `WSB_Cinf` | FLOAT64 | WSBモデル 究極インパクト予測 |
| 20 | `SB_B` | FLOAT64 | Sleeping Beauty 係数 B（Ke et al. 2015） |
| 21 | `SB_T` | INT64 | Awakening time（覚醒年） |
| 22 | `team_size` | INT64 | 著者数 |
| 23 | `institution_count` | INT64 | 参加機関数 |
| 24 | `patent_count` | INT64 | 特許からの被引用数 |
| 25 | `newsfeed_count` | INT64 | ニュース言及数 |
| 26 | `nct_count` | INT64 | 臨床試験からの被引用数 |
| 27 | `nih_count` | INT64 | 紐づくNIH助成数 |
| 28 | `nsf_count` | INT64 | 紐づくNSF助成数 |

### `sciscinet_paperfields`

論文×分野の対応（1論文が複数分野）。分野絞り込みに使う

- 行数: 1,271,891,157 / サイズ: 38.4 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `fieldid` | STRING | 分野ID（`sciscinet_fields.fieldid` と結合。例 `C119857082`=ML） |
| 3 | `score_openalex` | FLOAT64 | その分野への帰属度（OpenAlex concept score）。**分野で分布が大きく違う**（ML は中央値0.056・p90=0.460、CS は中央値0.333）。閾値0.5はMLでは上位6.8%（→ §5） |

### `sciscinet_paperrefs`

引用ペア。過去ベクトル（参考文献）・未来ベクトル（被引用）の源

- 行数: 2,494,545,461 / サイズ: 115.9 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `citing_paperid` | STRING | 引用する側（この論文の参考文献をたどる起点） |
| 2 | `cited_paperid` | STRING | 引用される側 |
| 3 | `year` | INT64 | citing 側の出版年 |
| 4 | `ref_year` | INT64 | cited 側の出版年 |
| 5 | `year_diff` | INT64 | `year - ref_year`。**引用窓の絞り込みに使う** |

### `sciscinet_papertitleabstract`

タイトルと要旨（転置インデックス）。テキスト特徴量の源

- 行数: 122,351,775 / サイズ: 251.2 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `title` | STRING | タイトル |
| 3 | `abstract_inverted_index` | STRING | 要旨の**転置インデックス**（`{語: [位置...]}` の JSON 文字列。復元が必要） |
| 4 | `language` | STRING | 言語コード（例 `en`） |

### `sciscinet_fields`

分野マスタ（OpenAlex concept、303件・小さい）

- 行数: 303 / サイズ: 131.2 KB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `id` | STRING | OpenAlex URL 形式（`https://openalex.org/C...`）。結合には使わない |
| 2 | `wikidata` | STRING | Wikidata ID |
| 3 | `display_name` | STRING | 表示名 |
| 4 | `level` | INT64 | 分野の階層（0=大分野, 1=中分野） |
| 5 | `description` | STRING | 分野の説明 |
| 6 | `works_count` | INT64 | 論文数 |
| 7 | `cited_by_count` | INT64 | **OpenAlex 側のグローバル被引用数**（コーパス外の引用も含む）。通常 `>= citation_count`（→ §2） |
| 8 | `image_url` | STRING | （要確認） |
| 9 | `image_thumbnail_url` | STRING | （要確認） |
| 10 | `works_api_url` | STRING | （要確認） |
| 11 | `updated_date` | STRING | （要確認） |
| 12 | `fieldid` | STRING | 分野ID（`C...`）。**結合はこの列** |

## 論文の付随情報

### `sciscinet_paperdetails`

論文の詳細。title/abstract/is_retracted/is_paratext も保持

- 行数: 249,803,279 / サイズ: 311.2 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `doi` | STRING | DOI |
| 3 | `title` | STRING | タイトル |
| 4 | `display_name` | STRING | 表示名 |
| 5 | `year` | INT64 | 出版年 |
| 6 | `date` | STRING | 出版日（STRING、`YYYY-MM-DD`） |
| 7 | `doctype` | STRING | 文献種別。8種・NULLなし：`article` / `book-chapter` / `dataset` / `preprint` / `dissertation` / `book` / `review` / `retraction`（→ §1） |
| 8 | `cited_by_count` | INT64 | **OpenAlex 側のグローバル被引用数**（コーパス外の引用も含む）。通常 `>= citation_count`（→ §2） |
| 9 | `is_retracted` | BOOL | 撤回論文フラグ。**true は 50,101 件**（papers/paperdetails で一致）。v2 は撤回も本表に含める（→ §6） |
| 10 | `is_paratext` | BOOL | ⚠️**全件 false**（NULLもなし）＝v2 では機能していない列（→ §6） |
| 11 | `cited_by_api_url` | STRING | （要確認） |
| 12 | `abstract_inverted_index` | STRING | 要旨の**転置インデックス**（`{語: [位置...]}` の JSON 文字列。復元が必要） |
| 13 | `language` | STRING | 言語コード（例 `en`） |

### `sciscinet_papersources`

論文×掲載媒体（OA可否・ライセンス・PDF URL）

- 行数: 204,111,441 / サイズ: 17.4 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `sourceid` | STRING | ソース（掲載媒体）ID |
| 3 | `landing_page_url` | STRING | （要確認） |
| 4 | `pdf_url` | STRING | （要確認） |
| 5 | `is_oa` | BOOL | （要確認） |
| 6 | `version` | STRING | （要確認） |
| 7 | `license` | STRING | （要確認） |

### `sciscinet_sources`

掲載媒体マスタ（ジャーナル・会議等）

- 行数: 260,811 / サイズ: 25.2 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `sourceid` | STRING | ソース（掲載媒体）ID |
| 2 | `display_name` | STRING | 表示名 |
| 3 | `issn` | STRING | （要確認） |
| 4 | `publisher` | STRING | （要確認） |
| 5 | `homepage_url` | STRING | （要確認） |
| 6 | `is_oa` | BOOL | （要確認） |

### `sciscinet_papers_pmid_pmcid`

論文の外部ID対応（PMID/PMCID/MAG）

- 行数: 6,281,193 / サイズ: 471.1 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `doi` | STRING | DOI |
| 3 | `mag` | INT64 | （要確認） |
| 4 | `pmid` | INT64 | （要確認） |
| 5 | `pmcid` | INT64 | （要確認） |

## 分野正規化・ヒット指標

### `hit_papers_level0`

大分野(level0)での被引用上位フラグ

- 行数: 570,263,651 / サイズ: 34.2 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `fieldid` | STRING | 分野ID（`sciscinet_fields.fieldid` と結合。例 `C119857082`=ML） |
| 3 | `year` | INT64 | 出版年 |
| 4 | `citation_count` | INT64 | （要確認） |
| 5 | `Hit_1pct` | INT64 | 同分野・同年で被引用上位1%なら1 |
| 6 | `Hit_5pct` | INT64 | 同条件で上位5%なら1 |
| 7 | `Hit_10pct` | INT64 | 同条件で上位10%なら1 |

### `hit_papers_level1`

中分野(level1)での被引用上位フラグ

- 行数: 701,627,506 / サイズ: 42.1 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `fieldid` | STRING | 分野ID（`sciscinet_fields.fieldid` と結合。例 `C119857082`=ML） |
| 3 | `year` | INT64 | 出版年 |
| 4 | `citation_count` | INT64 | （要確認） |
| 5 | `Hit_1pct` | INT64 | 同分野・同年で被引用上位1%なら1 |
| 6 | `Hit_5pct` | INT64 | 同条件で上位5%なら1 |
| 7 | `Hit_10pct` | INT64 | 同条件で上位10%なら1 |

### `normalized_citations_level0`

大分野での正規化被引用数

- 行数: 570,263,651 / サイズ: 34.2 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `fieldid` | STRING | 分野ID（`sciscinet_fields.fieldid` と結合。例 `C119857082`=ML） |
| 3 | `year` | INT64 | 出版年 |
| 4 | `citation_count` | FLOAT64 | （要確認） |
| 5 | `c0` | FLOAT64 | 同分野・同年の平均被引用数（正規化の分母） |
| 6 | `normalized_citations` | FLOAT64 | 正規化被引用数（citation_count / c0） |
| 7 | `level` | INT64 | 分野の階層（0=大分野, 1=中分野） |

### `normalized_citations_level1`

中分野での正規化被引用数

- 行数: 701,627,506 / サイズ: 42.1 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `fieldid` | STRING | 分野ID（`sciscinet_fields.fieldid` と結合。例 `C119857082`=ML） |
| 3 | `year` | INT64 | 出版年 |
| 4 | `citation_count` | FLOAT64 | （要確認） |
| 5 | `c0` | FLOAT64 | 同分野・同年の平均被引用数（正規化の分母） |
| 6 | `normalized_citations` | FLOAT64 | 正規化被引用数（citation_count / c0） |
| 7 | `level` | INT64 | 分野の階層（0=大分野, 1=中分野） |

## 著者・機関

### `sciscinet_authors`

著者マスタ（h-index・性別推定など）

- 行数: 100,418,971 / サイズ: 7.8 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `authorid` | STRING | 著者ID（OpenAlex Author ID） |
| 2 | `avg_c10` | FLOAT64 | （要確認） |
| 3 | `avg_logc10` | FLOAT64 | （要確認） |
| 4 | `productivity` | INT64 | （要確認） |
| 5 | `h_index` | INT64 | （要確認） |
| 6 | `display_name` | STRING | 表示名 |
| 7 | `inference_sources` | INT64 | （要確認） |
| 8 | `inference_counts` | INT64 | （要確認） |
| 9 | `P_gf` | FLOAT64 | （要確認） |

### `sciscinet_author_details`

著者詳細（ORCID・所属など）

- 行数: 100,418,971 / サイズ: 15.5 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `authorid` | STRING | 著者ID（OpenAlex Author ID） |
| 2 | `orcid` | STRING | （要確認） |
| 3 | `display_name` | STRING | 表示名 |
| 4 | `display_name_alternatives` | STRING | （要確認） |
| 5 | `works_count` | INT64 | 論文数 |
| 6 | `cited_by_count` | INT64 | **OpenAlex 側のグローバル被引用数**（コーパス外の引用も含む）。通常 `>= citation_count`（→ §2） |
| 7 | `last_known_institution` | STRING | （要確認） |
| 8 | `works_api_url` | STRING | （要確認） |
| 9 | `updated_date` | STRING | （要確認） |

### `sciscinet_authors_paperid`

論文×著者（軽量版）

- 行数: 772,984,433 / サイズ: 30.5 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `authorid` | STRING | 著者ID（OpenAlex Author ID） |
| 2 | `display_name` | STRING | 表示名 |
| 3 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |

### `sciscinet_paper_author_affiliation`

論文×著者×所属（著者順つき）

- 行数: 772,984,433 / サイズ: 29.7 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `author_position` | STRING | （要確認） |
| 3 | `authorid` | STRING | 著者ID（OpenAlex Author ID） |
| 4 | `institutionid` | STRING | 機関ID（OpenAlex Institution ID） |
| 5 | `raw_affiliation_string` | STRING | （要確認） |

### `sciscinet_affiliations`

機関マスタ

- 行数: 110,553 / サイズ: 13.7 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `institution_id` | STRING | 機関ID（OpenAlex Institution ID） |
| 2 | `display_name` | STRING | 表示名 |
| 3 | `ror` | STRING | （要確認） |
| 4 | `homepage_url` | STRING | （要確認） |
| 5 | `country_code` | STRING | （要確認） |
| 6 | `type` | STRING | （要確認） |
| 7 | `h_index` | INT64 | （要確認） |
| 8 | `productivity` | INT64 | （要確認） |
| 9 | `avg_c10` | FLOAT64 | （要確認） |
| 10 | `avg_logc10` | FLOAT64 | （要確認） |

### `sciscinet_affl_assoc_affl`

機関の関連機関

- 行数: 39,239 / サイズ: 1.2 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `institution_id` | STRING | 機関ID（OpenAlex Institution ID） |
| 2 | `associated_institution_id` | STRING | （要確認） |
| 3 | `relationship` | STRING | （要確認） |

## 外部リンク・メタデータ

### `funders`

ファンダー（助成機関）マスタ。ネストした STRUCT 多数

- 行数: 32,437 / サイズ: 67.1 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `id` | STRING | （要確認） |
| 2 | `display_name` | STRING | 表示名 |
| 3 | `ids` | STRUCT<…> | （要確認） |
| 4 | `alternate_titles` | STRUCT<…> | （要確認） |
| 5 | `country_code` | STRING | （要確認） |
| 6 | `country_id` | STRING | （要確認） |
| 7 | `description` | STRING | （要確認） |
| 8 | `homepage_url` | STRING | （要確認） |
| 9 | `image_url` | STRING | （要確認） |
| 10 | `image_thumbnail_url` | STRING | （要確認） |
| 11 | `roles` | STRUCT<…> | （要確認） |
| 12 | `grants_count` | INT64 | （要確認） |
| 13 | `works_count` | INT64 | 論文数 |
| 14 | `cited_by_count` | INT64 | **OpenAlex 側のグローバル被引用数**（コーパス外の引用も含む）。通常 `>= citation_count`（→ §2） |
| 15 | `summary_stats` | STRUCT<…> | （要確認） |
| 16 | `counts_by_year` | STRUCT<…> | （要確認） |
| 17 | `x_concepts` | STRUCT<…> | （要確認） |
| 18 | `updated_date` | STRING | （要確認） |
| 19 | `created_date` | STRING | （要確認） |
| 20 | `updated` | STRING | （要確認） |

### `sciscinet_link_nih`

論文×NIH助成

- 行数: 6,546,840 / サイズ: 162.6 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `award_id` | STRING | 助成の採択番号 |

### `sciscinet_link_nsf`

論文×NSF助成

- 行数: 1,769,355 / サイズ: 44.0 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `award_id` | STRING | 助成の採択番号 |

### `sciscinet_link_patents`

論文×特許

- 行数: 47,844,586 / サイズ: 1.6 GB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `patent` | STRING | （要確認） |
| 3 | `uspto` | INT64 | （要確認） |

### `sciscinet_link_clinicaltrials`

論文×臨床試験

- 行数: 612,587 / サイズ: 15.2 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `nct_id` | STRING | 臨床試験番号（ClinicalTrials.gov） |

### `sciscinet_link_newsfeed`

論文×ニュース

- 行数: 1,409,842 / サイズ: 68.6 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `newsfeed_id` | STRING | （要確認） |

### `sciscinet_link_nobellaureates`

論文×ノーベル賞受賞者

- 行数: 87,316 / サイズ: 2.4 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `laureate_id` | INT64 | （要確認） |
| 3 | `type` | INT64 | （要確認） |

### `sciscinet_nih_metadata`

NIH助成のメタ情報

- 行数: 533,653 / サイズ: 65.7 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `doi` | STRING | DOI |
| 3 | `type_crossref` | STRING | （要確認） |
| 4 | `funder_display_name` | STRING | （要確認） |
| 5 | `award_id` | STRING | 助成の採択番号 |
| 6 | `funderid` | STRING | ファンダーID（`funders` と結合） |

### `sciscinet_nsf_metadata`

NSF助成のメタ情報

- 行数: 459,837 / サイズ: 55.9 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `doi` | STRING | DOI |
| 3 | `type_crossref` | STRING | （要確認） |
| 4 | `funder_display_name` | STRING | （要確認） |
| 5 | `award_id` | STRING | 助成の採択番号 |
| 6 | `funderid` | STRING | ファンダーID（`funders` と結合） |

### `sciscinet_newsfeed_metadata`

ニュース言及のメタ情報

- 行数: 1,409,842 / サイズ: 274.1 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `doi` | STRING | DOI |
| 3 | `subj_id` | STRING | （要確認） |
| 4 | `newsfeed_id` | STRING | （要確認） |
| 5 | `timestamp` | STRING | （要確認） |

### `sciscinet_clinicaltrials_metadata`

臨床試験のメタ情報

- 行数: 273,269 / サイズ: 104.2 MB

| # | カラム | 型 | 説明 |
|---|---|---|---|
| 1 | `paperid` | STRING | 論文ID（**OpenAlex Work ID**、例 `W2945198257`）。全テーブルの結合キー |
| 2 | `nct_id` | STRING | 臨床試験番号（ClinicalTrials.gov） |
| 3 | `pmid` | INT64 | （要確認） |
| 4 | `pmcid` | INT64 | （要確認） |
| 5 | `doi` | STRING | DOI |
| 6 | `reference_type` | STRING | （要確認） |
| 7 | `citation` | STRING | （要確認） |
