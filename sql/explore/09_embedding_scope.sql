-- 埋め込み（SPECTER2）が必要な論文の総数を数える。
-- 目的: GCS の JSONL 112ファイル（1.62TiB）の走査設計を決める。
--
-- 必要なのは次の和集合:
--   (a) 対象論文（ML 2016-2018、テキストあり）
--   (b) 対象の参考文献            → 過去ベクトル
--   (c) 対象を引用した論文（5年窓） → 未来ベクトル
--
-- 設計メモ:
--   - 対象集合は中間テーブルを参照する（sql/build/01_pilot_target.sql）。
--     paperfields/papers のフルスキャン 53GB を払わずに済む。
--   - paperrefs（2.49億行・116GB）は OR 条件で1パスにまとめ、2回スキャンを避ける。
--   - 参考文献側（b）は窓で絞らない。出版時点までの全参考文献が過去ベクトルの材料。
--   - 被引用側（c）は year_diff BETWEEN 0 AND 5（docs/pilot.md の5年窓）。

WITH target AS (
  SELECT paperid
  FROM `endless-comfort-508409-q8.novelty_pilot.pilot_target_2016_2018`
  WHERE has_text
),
edges AS (
  SELECT r.citing_paperid, r.cited_paperid, r.year_diff
  FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperrefs` AS r
  WHERE r.citing_paperid IN (SELECT paperid FROM target)
     OR (r.cited_paperid IN (SELECT paperid FROM target)
         AND r.year_diff BETWEEN 0 AND 5)
),
past AS (
  SELECT DISTINCT e.cited_paperid AS paperid
  FROM edges AS e
  WHERE e.citing_paperid IN (SELECT paperid FROM target)
),
future AS (
  SELECT DISTINCT e.citing_paperid AS paperid
  FROM edges AS e
  WHERE e.cited_paperid IN (SELECT paperid FROM target)
    AND e.year_diff BETWEEN 0 AND 5
)
SELECT
  (SELECT COUNT(*) FROM target)                      AS n_target,
  (SELECT COUNT(*) FROM past)                        AS n_past_unique,
  (SELECT COUNT(*) FROM future)                      AS n_future_unique,
  (SELECT COUNT(*) FROM edges
    WHERE citing_paperid IN (SELECT paperid FROM target))        AS n_past_edges,
  (SELECT COUNT(*) FROM edges
    WHERE cited_paperid IN (SELECT paperid FROM target)
      AND year_diff BETWEEN 0 AND 5)                             AS n_future_edges,
  (SELECT COUNT(*) FROM (
     SELECT paperid FROM target
     UNION DISTINCT SELECT paperid FROM past
     UNION DISTINCT SELECT paperid FROM future
   ))                                                AS n_embedding_needed
