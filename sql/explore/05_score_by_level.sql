-- 【03 の修正版】score_openalex の分布を「同じ階層レベル」で比較する
--
-- 問題：03_score_openalex_dist.sql では Machine learning（level 1）と
--       Computer science（level 0）を比較していた。OpenAlex の concept score は
--       粒度の粗い上位概念ほど高く出やすいため、「分野による差」と「階層レベルによる差」
--       が交絡していた。
--
-- 修正：ML と同じ level 1 の CS 系分野（AI / CV / IR / DM / NLP / 理論 / 音声認識）を
--       並べて比較する。CS（level 0）も対照として残し、レベル差そのものを可視化する。
--
-- 判定：level 1 の分野が揃って低い分布なら「level 1 はこういうもの」。
--       ML だけが低ければ「ML 固有の特性」。どちらでも閾値を下げる判断は変わらないが、
--       定義書に書く理由が変わる。
--
-- 注意：非パーティションのため fieldid の IN リストを増やしてもスキャン量は変わらない
--       （参照列は fieldid と score_openalex の 2 列のみ）。
SELECT
  f.level,
  f.display_name,
  p.fieldid,
  COUNT(*) AS n_pairs,
  MAX(p.score_openalex) AS score_max,
  AVG(p.score_openalex) AS score_avg,
  APPROX_QUANTILES(p.score_openalex, 100)[OFFSET(50)] AS p50,
  APPROX_QUANTILES(p.score_openalex, 100)[OFFSET(75)] AS p75,
  APPROX_QUANTILES(p.score_openalex, 100)[OFFSET(90)] AS p90,
  APPROX_QUANTILES(p.score_openalex, 100)[OFFSET(95)] AS p95,
  COUNTIF(p.score_openalex >= 0.3) AS n_ge_030,
  COUNTIF(p.score_openalex >= 0.5) AS n_ge_050,
  -- 0.5 が上位何 % を切るか（直接比較できる形で出す）
  ROUND(COUNTIF(p.score_openalex >= 0.5) / COUNT(*) * 100, 2) AS pct_ge_050
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperfields` AS p
JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_fields` AS f
  ON p.fieldid = f.fieldid
WHERE p.fieldid IN (
  'C41008148',   -- Computer science        (level 0・対照)
  'C154945302',  -- Artificial intelligence (level 1)
  'C119857082',  -- Machine learning        (level 1・本研究の対象)
  'C31972630',   -- Computer vision         (level 1)
  'C23123220',   -- Information retrieval   (level 1)
  'C124101348',  -- Data mining             (level 1)
  'C204321447',  -- Natural language processing (level 1)
  'C80444323',   -- Theoretical computer science (level 1)
  'C28490314'    -- Speech recognition      (level 1)
)
GROUP BY f.level, f.display_name, p.fieldid
ORDER BY f.level, n_pairs DESC;
