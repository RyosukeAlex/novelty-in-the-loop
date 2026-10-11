# SciSciNet テーブル定義書

出典: Lin, Z., Yin, Y., Liu, L. & Wang, D. *SciSciNet: A large-scale open data lake for the science of science research.* Scientific Data 10:315 (2023). https://doi.org/10.1038/s41597-023-02198-9

| 項目 | 内容 |
|---|---|
| データ名 | SciSciNet |
| 配布元 | Figshare（https://doi.org/10.6084/m9.figshare.c.6076908.v1） |
| ソースコード | https://github.com/kellogg-cssi/SciSciNet |
| ファイル形式 | 全ファイル TSV |
| 主たる基盤データ | Microsoft Academic Graph (MAG) 2021年12月6日版（原データ 270,694,050 publication records） |
| 収録規模 | 論文 134,129,188 / 著者 134,197,162 / 機関 26,998 / ジャーナル 49,066 / 会議シリーズ 4,551 / 分野 19 (Level-0) + 292 (Level-1) |
| スナップショット時点 | MAG 最終版（2021年12月）に基づく静的スナップショット |
| ライセンス | CC BY 4.0（論文本体） |

---

## 1. ファイル一覧

| # | ファイル名 | レコード数 | 区分 | 概要 |
|---|---|---:|---|---|
| 1 | SciSciNet_Papers | 134,129,188 | マスタ | 主論文テーブル。ID・区分・各種カウント・算出指標 |
| 2 | SciSciNet_PaperDetails | 136,726,948 | マスタ | 論文の詳細情報（タイトル・掲載誌・撤回情報等）。撤回論文・paper family の付随論文も含む |
| 3 | SciSciNet_Authors_Gender | 134,197,162 | マスタ | 著者 ID・氏名・キャリアレベル指標・name-gender 推定 |
| 4 | SciSciNet_Affiliations | 26,998 | マスタ | 所属機関 ID・名称・所在地・機関レベル指標 |
| 5 | SciSciNet_Fields | 311 | マスタ | 研究分野 ID（Top=19, Sub=292） |
| 6 | SciSciNet_Journals | 49,066 | マスタ | ジャーナル ID・名称・ISSN・出版社 |
| 7 | SciSciNet_ConferenceSeries | 4,551 | マスタ | 会議シリーズ ID・名称 |
| 8 | SciSciNet_PaperAuthorAffiliations | 413,869,501 | リンク（内部） | 論文 – 著者 – 所属 の対応 |
| 9 | SciSciNet_PaperReferences | 1,588,739,703 | リンク（内部） | 引用ペア（citing – cited） |
| 10 | SciSciNet_PaperFields | 277,494,994 | リンク（内部） | 論文 – 分野 の対応＋分野正規化指標 |
| 11 | SciSciNet_Link_NSF | 1,309,518 | リンク（外部・上流） | 論文 – NSF アワード |
| 12 | SciSciNet_Link_NIH | 6,013,187 | リンク（外部・上流） | 論文 – NIH プロジェクト |
| 13 | SciSciNet_Link_Patents | 38,740,313 | リンク（外部・下流） | 論文 – 特許（USPTO/EPO） |
| 14 | SciSciNet_Link_ClinicalTrials | 438,220 | リンク（外部・下流） | 論文 – 臨床試験（NCT） |
| 15 | SciSciNet_Link_Twitter | 55,846,550 | リンク（外部・下流） | 論文 – ツイート |
| 16 | SciSciNet_Link_Newsfeed | 595,241 | リンク（外部・下流） | 論文 – ニュース／ブログ記事 |
| 17 | SciSciNet_Link_NobelLaureates | 87,316 | リンク（外部） | 論文 – ノーベル賞受賞者 |
| 18 | SciSciNet_NSF_Metadata | 489,446 | メタデータ | NSF アワードのメタ情報（nsf.gov 由来） |
| 19 | SciSciNet_Newsfeed_Metadata | 947,160 | メタデータ | ニュース言及のメタ情報（Crossref Event API 由来） |
| 20 | SciSciNet_Twitter_Metadata | 59,593,281 | メタデータ | ツイート言及のメタ情報（Crossref Event API 由来） |

---

## 2. ER 構造（概要）

```
SciSciNet_Affiliations ──┐
                         ├── SciSciNet_PaperAuthorAffiliations ──┐
SciSciNet_Authors_Gender ┘                                       │
                                                                 ▼
SciSciNet_Fields ── SciSciNet_PaperFields ──────────► SciSciNet_Papers ◄── SciSciNet_PaperReferences
                                                        │   (PK: PaperID)       (Citing/Cited)
                                                        │
      ┌─────────────────────────────────────────────────┼─────────────────────────────────┐
      ▼                    ▼                   ▼        ▼          ▼            ▼         ▼
  Link_NIH            Link_NSF          Link_Patents  Link_      Link_       Link_    Link_Nobel
                          │                           Clinical   Twitter     Newsfeed  Laureates
                          ▼                           Trials        │            │
                   NSF_Metadata                                     ▼            ▼
                                                           Twitter_Metadata  Newsfeed_Metadata

SciSciNet_Papers ── (JournalID) ──► SciSciNet_Journals
SciSciNet_Papers ── (ConferenceSeriesID) ──► SciSciNet_ConferenceSeries
SciSciNet_Papers ── (PaperID) ──► SciSciNet_PaperDetails （撤回論文・family 付随論文も保持）
```

- 全体の結合キーは原則 `PaperID`（MAG Paper ID）。
- 同名の ID カラムを持つテーブル同士は結合可能。
- 外部リンクテーブルは PaperID と外部 ID の複合主キー。

---

## 3. テーブル定義

### 3.1 SciSciNet_Papers（主論文テーブル）

レコード数: 134,129,188

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer (long) | PK | 論文の一意な MAG Paper ID |
| 2 | DOI | String | | 論文の DOI |
| 3 | DocType | String | | Book / BookChapter / Conference / Dataset / Journal / Repository / Thesis / NULL（不明） |
| 4 | Year | Integer | | 出版年 |
| 5 | Date | DateTime | | 出版日（YYYY-MM-DD） |
| 6 | JournalID | Integer (long) | FK → Journals | 掲載ジャーナルの MAG Journal ID |
| 7 | ConferenceSeriesID | Integer (long) | FK → ConferenceSeries | 掲載会議シリーズの MAG ID |
| 8 | Reference_Count | Integer | | 参考文献数（主論文集合内で再計算済み） |
| 9 | Citation_Count | Integer | | 被引用数（主論文集合内で再計算済み） |
| 10 | C5 | Integer | | 出版後5年間の被引用数（〜2016年出版論文で算出） |
| 11 | C10 | Integer | | 出版後10年間の被引用数（〜2011年出版論文で算出） |
| 12 | Disruption | Float | | Disruption score（Wu et al. 2019 定義） |
| 13 | Atyp_Median_Z | Float | | 参照ジャーナルペア Z-score の中央値（Uzzi et al. 2013）＝典型性 |
| 14 | Atyp_10pct_Z | Float | | 同 10パーセンタイル値＝新規性（tail novelty） |
| 15 | Atyp_Pairs | Integer | | 当該論文が引用したジャーナルペアの数（Uzzi et al. 2013） |
| 16 | WSB_mu | Float | | WSB モデルの即時性 μ |
| 17 | WSB_sigma | Float | | WSB モデルの寿命 σ |
| 18 | WSB_Cinf | Integer | | WSB モデルによる究極的インパクト予測値 |
| 19 | SB_B | Float | | Sleeping beauty 係数 B（Ke et al. 2015） |
| 20 | SB_T | Integer | | Awakening time（覚醒年） |
| 21 | Team_Size | Integer | | 著者数（チームサイズ） |
| 22 | Institution_Count | Integer | | 参加機関数 |
| 23 | Patent_Count | Integer | | USPTO/EPO 特許からの被引用数 |
| 24 | Newsfeed_Count | Integer | | Newsfeed におけるニュース言及数 |
| 25 | Tweet_Count | Integer | | Twitter における言及数（ER 図では Twitter_Count 表記） |
| 26 | NCT_Count | Integer | | ClinicalTrials.gov 臨床試験からの被引用数 |
| 27 | NIH_Count | Integer | | 紐づく NIH 助成の数 |
| 28 | NSF_Count | Integer | | 紐づく NSF 助成の数 |

**構築時のフィルタ条件（重要）**
- DocType が patent のレコードを除外。
- DocType・DOI いずれも欠損のレコードを除外。
- MAG の paper family（プレプリント／会議版など同一論文の複数エンティティ）を 1 件の primary paper に集約。
- 撤回論文は本テーブルに含めない（`SciSciNet_PaperDetails` 側に保持）。
- 内訳: journal 90,764,813 / book 4,629,342 / book chapter 3,932,366 / conference 5,123,597 / dataset 145,594 / repository 3,083,949 / thesis 5,998,509 / other 20,451,018。

**指標の算出対象件数**
| 指標 | 件数 | 条件 |
|---|---:|---|
| Disruption | 48,581,274 | 前方・後方引用を各1件以上持つ論文 |
| Novelty / Conventionality | 44,143,650 | 1950–2021 のジャーナル論文 |
| Sleeping beauty | 52,699,363 | 被引用1件以上のジャーナル論文 |

---

### 3.2 SciSciNet_PaperDetails（論文詳細）

レコード数: 136,726,948

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK | MAG Paper ID |
| 2 | DOI | String | | DOI |
| 3 | DocType | String | | Book / BookChapter / Conference / Dataset / Journal / Repository / Thesis / NULL |
| 4 | PaperTitle | String | | 論文タイトル |
| 5 | BookTitle | String | | 書籍タイトル |
| 6 | Year | Integer | | 出版年 |
| 7 | Date | DateTime | | 出版日（YYYY-MM-DD） |
| 8 | Publisher | String | | 出版社名 |
| 9 | JournalID | Integer | FK | MAG Journal ID |
| 10 | ConferenceSeriesID | Integer | FK | MAG ConferenceSeries ID |
| 11 | OriginalVenue | String | | 原掲載媒体名 |
| 12 | Volume | String | | 巻 |
| 13 | Issue | String | | 号 |
| 14 | FirstPage | String | | 開始ページ |
| 15 | LastPage | String | | 終了ページ |
| 16 | FamilyID | Integer | FK → Papers | 同一 paper family における primary Paper ID |
| 17 | RetractionType | String | | "Retracted Publication" / "Retraction Notice" |
| 18 | ReferenceCount | Integer | | MAG 原データ上の参考文献数 |
| 19 | CitationCount | Integer | | MAG 原データ上の被引用数 |

> `Papers` の再計算値と異なり、本テーブルの Reference/Citation は MAG 原データ値。撤回論文・family 付随論文もここに含まれるため、タイトル取得や撤回フラグ判定はこのテーブルを参照する。

---

### 3.3 SciSciNet_Authors_Gender（著者）

レコード数: 134,197,162

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | AuthorID | Integer (long) | PK | MAG Author ID |
| 2 | Author_Name | String | | 著者名（原表記） |
| 3 | H-index | Integer | | 著者の h-index |
| 4 | Productivity | Integer | | 総出版数 |
| 5 | Average_C10 | Float | | 平均 c10 |
| 6 | Average_LogC10 | Float | | 平均 log c10（0 回避のため c10+1 で算出） |
| 7 | Inference_Sources | Integer | | name-gender 推定に用いたソースデータセット数 |
| 8 | Inference_Counts | Integer | | ソース中の当該ファーストネーム＋性別ラベルの実測件数 |
| 9 | P(gf) | Float | | 当該名が female とされる確率 |

- 性別推定は Van Buskirk et al. (2022) の手法。36 ソース・150 か国以上の cultural consensus model。
- 全著者のうち 23.26%（31,224,458 名）はイニシャルのみで推定対象外。
- 推定値が付与されたのは 86,286,037 名。max uncertainty threshold = 0.26、サンプルの 85% を分類。
- 名前ベースの性別推定は原理的に不完全であり、利用時は限界を考慮すること（論文の明記事項）。

---

### 3.4 SciSciNet_Affiliations（所属機関）

レコード数: 26,998

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | AffiliationID | Integer (long) | PK | MAG Affiliation ID |
| 2 | Affiliation_Name | String | | 機関名（原表記） |
| 3 | GridID | String | | GRID ID |
| 4 | Official_Page | String | | 公式サイト URL |
| 5 | ISO3166Code | String | | ISO 3166 二文字国コード |
| 6 | Latitude | Float | | 緯度 |
| 7 | Longitude | Float | | 経度 |
| 8 | H-index | Integer | | 機関の h-index |
| 9 | Productivity | Integer | | 機関の総出版数 |
| 10 | Average_C10 | Float | | 平均 c10 |
| 11 | Average_LogC10 | Float | | 平均 log c10 |

---

### 3.5 SciSciNet_Fields（分野）

レコード数: 311

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | FieldID | Integer | PK | MAG Field of Study ID |
| 2 | Field_Name | String | | 分野名（原表記） |
| 3 | Field_Type | String | | "Top"（Level-0, 19件）/ "Sub"（Level-1, 292件） |

---

### 3.6 SciSciNet_Journals（ジャーナル）

レコード数: 49,066

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | JournalID | Integer | PK | MAG Journal ID |
| 2 | Journal_Name | String | | ジャーナル名 |
| 3 | ISSN | String | | ISSN |
| 4 | Publisher | String | | 出版社 |
| 5 | Webpage | String | | 公式 URL |

---

### 3.7 SciSciNet_ConferenceSeries（会議シリーズ）

レコード数: 4,551

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | ConferenceSeriesID | Integer | PK | MAG ConferenceSeries ID |
| 2 | Abbr_Name | String | | 略称 |
| 3 | ConferenceSeries_Name | String | | 正式名称 |

---

### 3.8 SciSciNet_PaperAuthorAffiliations（論文–著者–所属）

レコード数: 413,869,501

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | AuthorID | Integer | PK, FK → Authors | MAG Author ID |
| 3 | AffiliationID | Integer | PK, FK → Affiliations | MAG Affiliation ID（NULL 許容） |
| 4 | AuthorSequenceNumber | Integer | | 著者順（1 始まり） |

> Team_Size / Institution_Count / Productivity / H-index はこのテーブルの集計から算出されている。

---

### 3.9 SciSciNet_PaperReferences（引用関係）

レコード数: 1,588,739,703

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | Citing_PaperID | Integer | PK, FK → Papers | 引用する側の Paper ID |
| 2 | Cited_PaperID | Integer | PK, FK → Papers | 引用される側の Paper ID |

- 引用ペアは主論文 134M の集合内に閉じている（両端とも `SciSciNet_Papers` に存在）。
- 同一 family 内の引用は primary paper に集約し、重複ペアは削除済み。
- MAG 原データとの Spearman 相関: 被引用 0.991 / 参考文献 0.994。

---

### 3.10 SciSciNet_PaperFields（論文–分野）

レコード数: 277,494,994

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | FieldID | Integer | PK, FK → Fields | MAG Field ID |
| 3 | Hit_1pct | Integer | | 同一レベル分野・同一年で被引用上位 1% なら 1、それ以外 0 |
| 4 | Hit_5pct | Integer | | 同条件で上位 5% なら 1 |
| 5 | Hit_10pct | Integer | | 同条件で上位 10% なら 1 |
| 6 | C_f | Float | | 正規化被引用数（Radicchi et al. 2008） |

> 1 論文が複数分野に紐づくため、正規化指標は論文–分野ペア単位で保持される。分野横断の集計では重複カウントに注意。

---

### 3.11 SciSciNet_Link_NIH（論文–NIH 助成）

レコード数: 6,013,187（論文 2,636,061 件 × NIH プロジェクト 379,014 件）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | NIH_Project_Number | String | PK | NIH コアプロジェクト番号 |

- ソース: NIH ExPORTER / RePORTER のリンクテーブル（2021-05-16 更新版）。
- PMID を中間キーとして突合し、原リンクテーブルの 98.9% 超を Paper ID に一致させている。

---

### 3.12 SciSciNet_Link_NSF（論文–NSF アワード）

レコード数: 1,309,518（高信頼リンク 1,130,641＋fuzzy 178,877／NSF アワード 148,148 件 × 論文 929,258 件）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | NSF_Award_Number | String | PK | NSF アワード番号 |
| 3 | Type | String | | "First"・"Crossref" = 完全一致、"Second" = fuzzy match |
| 4 | Diff_ZScore | Float | | "Second" 型でのヒューリスティック Z-score 差分 |

**突合プロセス（4段階）**
1. DOI 完全一致 → 350,611 件（26.0%）
2. タイトル正規化後の完全一致 → 246,701 件（18.3%）
3. Elasticsearch による検索＋2位スコアを帰無モデルとした有意判定（P=0.05）→ 467,159 件（34.6%）。閾値未満でも上位2件の Z-score 差が大きいものは fuzzy link として収録
4. Crossref funder-paper データで補完 → 305,314 件

> 厳密な分析では `Type` で fuzzy match（"Second"）を除外するか、`Diff_ZScore` で閾値を設けることを推奨。

---

### 3.13 SciSciNet_Link_Patents（論文–特許）

レコード数: 38,740,313（特許 2,360,587 件 × 論文 4,627,035 件）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | PatentID | String | PK | 特許 ID（Marx & Fuegi データセット） |
| 3 | Type | Integer | | 1 = USPTO 由来、0 = それ以外（EPO） |

- ソース: Marx & Fuegi の Reliance on Science コーパス v34（2021-12-24 時点）。

---

### 3.14 SciSciNet_Link_ClinicalTrials（論文–臨床試験）

レコード数: 438,220（臨床試験 61,447 件 × 論文 337,430 件）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | NCT_Number | String | PK | National Clinical Trial 番号 |

- ソース: AACT（ClinicalTrials.gov 集約DB、2022-01-26 時点）。背景文献として参照された論文に限定（result paper は除外）。
- PMID を中間キーとして突合。
- 国別の収録分布には偏りがある（米国 153,632 件に対し日本等は相対的に少ない）。

---

### 3.15 SciSciNet_Link_Twitter（論文–ツイート）

レコード数: 55,846,550（論文 4,329,443 件 × ツイート 53,053,505 件）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | TweetID | Integer | PK | Tweet ID |

- ソース: Crossref Event API（2017-02-07 〜 2022-01-17）。正規化 DOI で突合、原データの 94% 超をカバー。

---

### 3.16 SciSciNet_Link_Newsfeed（論文–ニュース）

レコード数: 595,241（論文 307,959 件 × Web ページ 370,065 件）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | NewsfeedID | String | PK | Newsfeed ID |

- ソース: Crossref Event API（2017-04-05 〜 2022-01-16）。正規化 DOI 突合で原データの 94.9% をカバー。

---

### 3.17 SciSciNet_Link_NobelLaureates（論文–ノーベル賞受賞者）

レコード数: 87,316（物理 20,434 / 化学 38,133 / 生理学・医学 28,749）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | PaperID | Integer | PK, FK → Papers | MAG Paper ID |
| 2 | LaureateID | Integer | PK | ノーベル賞受賞者 ID（Li et al. 2019） |
| 3 | Type | Integer | | 1 = 受賞対象論文、0 = それ以外 |

- 対象期間: 1900–2016 年の受賞者。受賞対象論文だけでなくキャリア全体の論文を含む。

---

### 3.18 SciSciNet_NSF_Metadata（NSF アワード メタデータ）

レコード数: 489,446（1959 年以降の全 NSF アワード）

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | NSF_Award_Number | String | PK | NSF アワード番号 |
| 2 | Title | String | | アワードのタイトル |
| 3 | Publication_Research | String | | 当該アワードに紐づく出版物（生テキスト） |
| 4 | Date | DateTime | | NSF Grants Officer による署名日 |

- nsf.gov のアワードページをクロールして取得（"Publications as a result of this research" 欄をパース）。

---

### 3.19 SciSciNet_Newsfeed_Metadata（ニュース言及 メタデータ）

レコード数: 947,160

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | NewsfeedID | String | PK, FK → Link_Newsfeed | ニュース記事／ブログ記事の Newsfeed ID |
| 2 | Occurred_Time | DateTime | | 記事の公開日時 |
| 3 | ObjectID | String | | 言及対象の DOI オブジェクトリンク |
| 4 | Subject_Infomation | String | | 言及元に関する詳細情報（原文ママのカラム名） |

---

### 3.20 SciSciNet_Twitter_Metadata（ツイート言及 メタデータ）

レコード数: 59,593,281

| # | カラム名 | 型 | キー | 説明 |
|---|---|---|---|---|
| 1 | TweetID | Integer | PK, FK → Link_Twitter | Tweet ID |
| 2 | Occurred_Time | DateTime | | ツイートの投稿日時 |
| 3 | ObjectID | String | | 言及対象の DOI オブジェクトリンク |
| 4 | OriginalTweetID | String | | ツイートの Web リンク |

---

## 4. 算出指標の定義（補足）

| 指標 | カラム | 定義 |
|---|---|---|
| Disruption (D) | Papers.Disruption | D = (n_i − n_j) / (n_i + n_j + n_k)。n_i: 当該論文のみを引用する後続研究数、n_j: 当該論文とその参考文献の両方を引用する数、n_k: 参考文献のみを引用する数 |
| 正規化被引用 (c_f) | PaperFields.C_f | 被引用数 c ÷ 同一分野・同一年の平均被引用数 c_0 |
| Hit paper | PaperFields.Hit_*pct | 同一分野・同一年の被引用上位 1/5/10% |
| WSB モデル | Papers.WSB_mu / sigma / Cinf | 選好的接続・加齢・適応度を取り込んだ累積被引用モデル。math/physics 分野（10年で10被引用以上）および 1960s–1990s 全分野で推定 |
| Sleeping beauty (B) | Papers.SB_B / SB_T | 出版年〜最大被引用年までの直線からの乖離の総和。SB_T は覚醒年 |
| Novelty / Conventionality | Papers.Atyp_10pct_Z / Atyp_Median_Z | 参照ジャーナルペアの Z-score 分布。中央値＝典型性、10パーセンタイル＝tail novelty。ランダム化ネットワーク 10 本と比較して算出 |
| h-index | Authors/Affiliations.H-index | h 本の論文が各 h 回以上引用されている最大の h |
| 平均 log c10 | Average_LogC10 | log(c10 + 1) の平均（Q パラメータに関連） |

---

## 5. 利用上の注意

1. **静的スナップショット**: MAG 2021年12月版に基づく。以降の論文・引用は含まれない。継続更新が必要な場合は OpenAlex 等との併用を検討。
2. **助成リンクの範囲**: 上流の助成リンクは NSF と NIH のみ。他国・他機関のファンディングは対象外。
3. **特許リンクの範囲**: USPTO と EPO からの引用に限定。
4. **臨床試験リンク**: ClinicalTrials.gov 由来のため国別分布が不均一。
5. **メディア言及**: Crossref がトラッキングしているソースに依存。Newsfeed は 2017年4月以降、Twitter は 2017年2月以降。
6. **NSF リンクの品質**: `Type` が "Second" のものは fuzzy match。精度重視の分析では除外推奨。
7. **名寄せの不完全性**: 著者名寄せは MAG のアルゴリズムに依拠し完全ではない。性別推定も同様に不完全。
8. **撤回論文の扱い**: `SciSciNet_Papers` には含まれず `SciSciNet_PaperDetails` 側にのみ存在。撤回論文を分析対象に含めるかどうかは明示的に設計すること。
9. **指標の欠損**: C5/C10・WSB・Disruption 等は算出条件を満たす論文にのみ値が入る。欠損を 0 とみなさないこと。
10. **外部検証結果**: Dimensions との DOI 突合で 84,936,278 件が共通（Dimensions の 79.74%、SciSciNet の 85.97%）。被引用数の Spearman 相関 0.946、一致係数 0.940。
