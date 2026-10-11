-- 【確認項目 5】score_openalex の分布（ML 絞り込みの閾値 0.5 の妥当性）
--
-- 目的：パイロット（Step 1.5）で ML 分野を `score_openalex >= 0.5` で絞る予定だが、
--       その閾値で何本残るのか、分布のどこを切っているのかを知らないまま決めたくない。
--
-- 対象分野：C119857082 = Machine learning、C41008148 = Computer science（比較用）
--
-- 注意：paperfields は非パーティションのため、WHERE fieldid IN (...) でもスキャン量は減らない。
--       減るのは参照列を fieldid と score_openalex の 2 列に絞ることによる分だけ
--       （paperid は参照しない）。
SELECT
  fieldid,
  COUNT(*) AS n_pairs,
  MIN(score_openalex) AS score_min,
  MAX(score_openalex) AS score_max,
  AVG(score_openalex) AS score_avg,
  STDDEV(score_openalex) AS score_sd,
  -- 分位点（閾値をどこに置くと何が落ちるかを見る）
  APPROX_QUANTILES(score_openalex, 100)[OFFSET(10)] AS p10,
  APPROX_QUANTILES(score_openalex, 100)[OFFSET(25)] AS p25,
  APPROX_QUANTILES(score_openalex, 100)[OFFSET(50)] AS p50,
  APPROX_QUANTILES(score_openalex, 100)[OFFSET(75)] AS p75,
  APPROX_QUANTILES(score_openalex, 100)[OFFSET(90)] AS p90,
  -- 閾値ごとの残存件数（0.5 の妥当性を直接見る）
  COUNTIF(score_openalex >= 0.3) AS n_ge_030,
  COUNTIF(score_openalex >= 0.4) AS n_ge_040,
  COUNTIF(score_openalex >= 0.5) AS n_ge_050,
  COUNTIF(score_openalex >= 0.6) AS n_ge_060,
  COUNTIF(score_openalex >= 0.7) AS n_ge_070,
  COUNTIF(score_openalex IS NULL) AS n_null
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperfields`
WHERE fieldid IN ('C119857082', 'C41008148')
GROUP BY fieldid
ORDER BY fieldid;
