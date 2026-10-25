-- Step 1.5 パイロットの対象集合を中間テーブルに固定する。
--
-- 狙い: 対象の絞り込みには sciscinet_paperfields（41GB）と sciscinet_papers（12GB）の
--   フルスキャンが毎回必要になる。一度だけ払って結果を保存し、以降はこの表を参照する。
--
-- 対象: Machine learning（C119857082）、score_openalex >= 0.5、2016-2018、
--   doctype in (article, preprint)、撤回を除く。根拠は docs/pilot.md。
--
-- 第2章の比較対象になる既存指標も同時に持たせる（以降 sciscinet_papers を叩かないため）。
-- 欠損の扱いは docs/handover.md §3 を参照:
--   disruption は 0 がプレースホルダなので d_valid で判定する。
--   Atyp_* は NULL が正しい欠損。
--   引用ネットワークと整合するのは citation_count（cited_by_count ではない）。

CREATE OR REPLACE TABLE `endless-comfort-508409-q8.novelty_pilot.pilot_target_2016_2018`
AS
SELECT
  p.paperid,
  p.year,
  p.doctype,
  f.score_openalex,
  p.reference_count,
  p.citation_count,
  p.cited_by_count,
  p.C3,
  p.C5,
  p.disruption,
  p.Atyp_Median_Z,
  p.Atyp_10pct_Z,
  p.Atyp_Pairs,
  p.team_size,
  -- disruption を使ってよいか（両側 > 0）。0 埋めバイアスの除外条件。
  (p.reference_count > 0 AND p.citation_count > 0) AS d_valid,
  -- papertitleabstract に行があるか。SPECTER2 の入力が取れる見込み。
  (a.paperid IS NOT NULL) AS has_text
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers` AS p
JOIN (
  -- 1論文が同じ分野に複数行を持つ場合に備えて先に畳む
  SELECT paperid, MAX(score_openalex) AS score_openalex
  FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperfields`
  WHERE fieldid = 'C119857082'
    AND score_openalex >= 0.5
  GROUP BY paperid
) AS f
  ON p.paperid = f.paperid
LEFT JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papertitleabstract` AS a
  ON p.paperid = a.paperid
WHERE p.year BETWEEN 2016 AND 2018
  AND p.doctype IN ('article', 'preprint')
  AND p.is_retracted = FALSE
