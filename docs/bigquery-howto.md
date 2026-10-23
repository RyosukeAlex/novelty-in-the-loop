# BigQuery 作業手順書（SciSciNet-v2）

最終更新: 2026-10-17

ターミナルから `bq` CLI で SciSciNet-v2 を叩き、結果を CSV で手元に落とすまでの手順。
**無料枠（クエリスキャン 1TB/月）で運用しているため、dry run を飛ばさないこと。**

---

## 0. 全体の流れ

```
SQL を書く  →  dry run でスキャン量を確認  →  本実行して CSV 保存  →  SQL をコミット
sql/explore/NN_*.sql        （課金 0）         data/explore/NN_*.csv    （data/ は Git 管理外）
```

1ステップでも飛ばすと、①無料枠を無駄に食う ②後から「この数字どのクエリで出した？」が分からなくなる。

---

## 1. 前提の確認

初回、あるいは「認証が切れた？」と思ったときだけ。

```bash
# bq / gcloud が入っているか
which bq gcloud

# 誰として、どのプロジェクトで動いているか
gcloud config list
```

期待する状態:

| 項目 | 値 |
|---|---|
| account | `ryosuke.volley6@gmail.com` |
| project | `endless-comfort-508409-q8` ← **課金先（自分のプロジェクト）** |
| データの場所 | `ksm-rch-scisciturbo.sciscinet_v2`（他人のプロジェクト・US リージョン） |

**データは他人のプロジェクトにあるが、スキャン量は「クエリを投げた側」＝自分のプロジェクトに計上される。**
だから無料枠を気にする必要がある。

認証が切れていたら:

```bash
gcloud auth login            # ブラウザが開く
gcloud auth application-default login   # Python から叩くとき用（別物）
```

---

## 2. SQL を書く

置き場所は `sql/explore/NN_<内容>.sql`（連番 + スネークケース）。

**ファイル冒頭に `--` コメントで「何を確認したいのか」を書く。** 既存の `sql/explore/06_*.sql` `07_*.sql` がその形。
数ヶ月後に読むのは自分なので、SQL 本体より動機のほうが価値がある。

列の選び方だけが課金額を決める（→ §5）。`SELECT *` は書かない。

---

## 3. dry run（必須・課金 0）

```bash
bq query --use_legacy_sql=false --dry_run < sql/explore/07_pilot_feasibility.sql
```

出力例:

```
Query successfully validated. Assuming the tables are not modified,
running this query will process 53299812274 bytes of data.
```

→ 53,299,812,274 bytes ≒ **53.3 GB**。月1TB枠の約 5%。これなら実行してよい。

判断の目安:

| スキャン量 | 判断 |
|---|---|
| 〜100 GB | そのまま実行してよい |
| 100 GB 〜 300 GB | 列を削れないか見直す。月内の累計を意識する |
| 300 GB 超 | 一度止まる。中間テーブルを作る設計に切り替える（→ §6） |

GB に直すワンライナー:

```bash
bq query --use_legacy_sql=false --dry_run < sql/explore/07_pilot_feasibility.sql \
  | grep -o '[0-9]\{6,\}' | awk '{printf "%.2f GB\n", $1/1024/1024/1024}'
```

---

## 4. 本実行して CSV に保存

```bash
bq query --use_legacy_sql=false --format=csv --max_rows=100000 \
  < sql/explore/07_pilot_feasibility.sql \
  > data/explore/07_pilot_feasibility.csv
```

各フラグの意味:

| フラグ | なぜ必要か |
|---|---|
| `--use_legacy_sql=false` | 標準SQL を使う。付けないと旧構文で解釈されてエラーになる |
| `--format=csv` | そのままファイルに落とせる。付けないと装飾付きの表で出る（目視用） |
| `--max_rows=100000` | **付けないと100行で黙って切れる。** 行数が読めないときは必ず付ける |
| `< file.sql` | SQL を標準入力から渡す（→ §5 の落とし穴） |

実行後、行数と中身を確認:

```bash
wc -l data/explore/07_pilot_feasibility.csv
column -s, -t < data/explore/07_pilot_feasibility.csv | less -S   # 読みやすく表示
```

**`data/` は `.gitignore` で管理外。コミットするのは `sql/` だけ。**
数字そのものを残したいときは、結論を `docs/pilot.md` に表として転記する。

---

## 5. 落とし穴（踏んだもの）

### 5-1. `"$(cat ...)"` で渡すと失敗する

```bash
# NG: 先頭の -- コメントが bq のフラグと解釈される
bq query --use_legacy_sql=false "$(cat sql/explore/07_pilot_feasibility.sql)"

# OK: 標準入力から渡す
bq query --use_legacy_sql=false < sql/explore/07_pilot_feasibility.sql
```

### 5-2. `WHERE` も `LIMIT` もスキャン量を減らさない

SciSciNet-v2 のテーブルは**非パーティション**。BigQuery は列指向なので、
**課金されるのは「読んだ列のサイズ × 全行」。行の絞り込みは課金に効かない。**

- `LIMIT 100` でも 11.2 GB 読む
- 減らす唯一の方法は**参照する列を減らすこと**
- 中身を覗くだけなら課金 0 の `bq head -n 10 ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers`

### 5-3. 同じクエリの再実行は課金 0

24時間以内に**完全に同一の** SQL を投げるとキャッシュが返る。
逆に言えば、コメントを1文字直すとキャッシュは効かない。試行錯誤は dry run で詰めてから本実行する。

### 5-4. JOIN は両方のテーブルのスキャン量が乗る

`07_pilot_feasibility.sql` が 53 GB なのは `sciscinet_paperfields`（12.7億行）の `paperid`（STRING）を
読むため。`sciscinet_paperrefs` を2回叩くようなクエリは一気に膨らむので dry run を特に慎重に。

---

## 6. 中間テーブルを作る（これから必要になる）

同じ絞り込みを何度もかけるなら、結果をテーブルに保存して以降はそれを読む。
**データセットは US リージョンに作る**（`sciscinet_v2` と同じリージョンでないと JOIN できない）。

```bash
# データセットを一度だけ作る（※作成前に確認を取る）
bq --location=US mk --dataset endless-comfort-508409-q8:novelty_wip

# クエリ結果をテーブルに保存
bq query --use_legacy_sql=false \
  --destination_table=endless-comfort-508409-q8:novelty_wip.pilot_targets \
  --replace \
  < sql/build/01_pilot_targets.sql
```

以降は `novelty_wip.pilot_targets`（数万行）を読むだけになり、スキャン量が数桁下がる。
ストレージは 10GB/月まで無料。

---

## 7. Python から実行するとき

課金の上限をコード側で必ず縛る。これを忘れると事故る。

```python
from google.cloud import bigquery

client = bigquery.Client(project="endless-comfort-508409-q8")
job_config = bigquery.QueryJobConfig(
    maximum_bytes_billed=100 * 1024**3,  # 100 GB を超えたらジョブを失敗させる
    dry_run=False,
)
df = client.query(sql, job_config=job_config).to_dataframe()
```

実行は uv 経由:

```bash
uv run python src/<script>.py
```

---

## 8. よく使う参照系（すべて課金 0 か極小）

```bash
# テーブル一覧
bq ls ksm-rch-scisciturbo:sciscinet_v2

# スキーマを見る
bq show --schema --format=prettyjson ksm-rch-scisciturbo:sciscinet_v2.sciscinet_papers

# 中身を10行覗く（課金 0）
bq head -n 10 ksm-rch-scisciturbo:sciscinet_v2.sciscinet_papers

# 全テーブルの行数・サイズ（メタデータのみ）
bq query --use_legacy_sql=false --format=csv < sql/count_rows.sql

# 全テーブルの列定義（メタデータのみ）
bq query --use_legacy_sql=false --format=csv --max_rows=2000 < sql/get-columns.sql
```

`INFORMATION_SCHEMA` と `__TABLES__` はメタデータなのでスキャン課金が発生しない。
スキーマを確認したいだけのときに本体テーブルを叩かないこと。

---

## 9. 今月の使用量を確認する

[BigQuery の料金画面](https://console.cloud.google.com/billing) か、ジョブ履歴から:

```bash
bq ls -j -a --max_results=20
bq show --format=prettyjson -j <job_id> | grep -E 'totalBytesProcessed|totalBytesBilled'
```

---

## 10. 関連文書

- `docs/handover.md` §3 — データ上の前提（disruption の 0 埋め、C3/C5/C10 の窓、閾値問題）。**クエリを書く前に読む**
- `docs/pilot.md` — パイロットの対象期間と絞り込み条件の決定
- `docs/table/SciSciNet_v2_table_definition.md` — テーブル定義
- `sql/exec-command.md` — `bq query` の各要素の説明（初学メモ）
