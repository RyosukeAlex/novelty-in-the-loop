-- 過去/未来ベクトルの材料になる近傍論文（651,370本）に、出版年・種別・テキスト有無を付ける。
--
-- 狙い: 近傍側の品質を測る。対象論文のテキストは86.9%揃っていたが、
--   参考文献側は古い論文を含むため、全体平均（49%）に近い可能性がある。
--   過去ベクトルは参考文献の埋め込み平均なので、欠損率が重心を歪める。
--
-- 対象論文自身も含む（埋め込み走査の対象リストとして使うため）。role で区別する。

CREATE OR REPLACE TABLE `endless-comfort-508409-q8.novelty_pilot.pilot_neighbors`
AS
WITH roles AS (
  SELECT paperid, TRUE AS is_target, FALSE AS is_past, FALSE AS is_future
  FROM `endless-comfort-508409-q8.novelty_pilot.pilot_target_2016_2018`
  WHERE has_text
  UNION ALL
  SELECT DISTINCT cited_paperid, FALSE, TRUE, FALSE
  FROM `endless-comfort-508409-q8.novelty_pilot.pilot_edges`
  WHERE is_past_edge
  UNION ALL
  SELECT DISTINCT citing_paperid, FALSE, FALSE, TRUE
  FROM `endless-comfort-508409-q8.novelty_pilot.pilot_edges`
  WHERE is_future_edge
),
merged AS (
  SELECT
    paperid,
    LOGICAL_OR(is_target) AS is_target,
    LOGICAL_OR(is_past)   AS is_past,
    LOGICAL_OR(is_future) AS is_future
  FROM roles
  GROUP BY paperid
)
SELECT
  m.paperid,
  m.is_target,
  m.is_past,
  m.is_future,
  p.year,
  p.doctype,
  (a.paperid IS NOT NULL) AS has_text
FROM merged AS m
LEFT JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers` AS p
  ON m.paperid = p.paperid
LEFT JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papertitleabstract` AS a
  ON m.paperid = a.paperid
