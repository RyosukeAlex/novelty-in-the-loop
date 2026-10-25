-- 対象論文に関わる引用エッジを中間テーブルに固定する。
--
-- 狙い: sciscinet_paperrefs（2.49億行・116GB）を二度と叩かないため。
--   以降、過去/未来ベクトルの近傍リストはこの表（約128万行）から導出する。
--
-- 列の選択: year / ref_year を足すと +40GB かかる（dry runで実測）。
--   近傍の出版年は sciscinet_papers から約5GBで取れるので、ここでは持たせない。
--
-- 方向の意味:
--   is_past_edge   = 対象が引用している側（cited_paperid が参考文献）→ 過去ベクトルの材料
--   is_future_edge = 対象が引用された側（citing_paperid が後続研究）→ 未来ベクトルの材料
--   5年窓（year_diff 0-5）は未来側にのみ適用（docs/pilot.md）。過去側は全参考文献を使う。

CREATE OR REPLACE TABLE `endless-comfort-508409-q8.novelty_pilot.pilot_edges`
AS
WITH target AS (
  SELECT paperid
  FROM `endless-comfort-508409-q8.novelty_pilot.pilot_target_2016_2018`
  WHERE has_text
)
SELECT
  r.citing_paperid,
  r.cited_paperid,
  r.year_diff,
  (r.citing_paperid IN (SELECT paperid FROM target)) AS is_past_edge,
  (r.cited_paperid IN (SELECT paperid FROM target)
   AND r.year_diff BETWEEN 0 AND 5)                 AS is_future_edge
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperrefs` AS r
WHERE r.citing_paperid IN (SELECT paperid FROM target)
   OR (r.cited_paperid IN (SELECT paperid FROM target)
       AND r.year_diff BETWEEN 0 AND 5)
