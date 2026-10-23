-- 【Step 1.5 の前提確認】パイロットが成立する規模か
--
-- 確認したいこと：
--   (1) 母集団サイズ：ML 分野を閾値別に絞ると、年ごとに何本残るか
--       → README のパイロット想定「数千〜数万本」が満たせるか
--   (2) D-index が比較対象として使えるか
--       → §4 で判明した 0 埋め汚染を除いた後（reference_count > 0 AND citation_count > 0）
--         に何本残るか。少なすぎると「提案指標 vs D-index」の比較設計が揺らぐ
--   (3) atypicality が使えるか
--       → Atyp_Median_Z は全体で 75.5% が NULL。ML 分野で有効な本数を確認
--   (4) 過去／未来ベクトルの材料があるか
--       → 参考文献数・被引用数の平均。極端に少ないと埋め込みの重心が不安定になる
--
-- 対象年：README が候補とする 2 つの窓を一度に見る
--   2012-2014（5年窓がデータ内で完結し、長い引用窓が取れる）
--   2016-2018（深層学習期。AI Scientist の対象分野に近い）
--
-- 絞り込み条件：
--   - 分野 Machine learning（C119857082）
--   - doctype は article と preprint のみ（§1 で判明した 8 値のうち研究論文に当たるもの。
--     book-chapter / dataset / dissertation / book / review / retraction を除く）
--   - year <= 2024（§7 の日付異常を避ける。ここでは 2012-2018 なので自動的に満たす）
--
-- 注意：paperfields との JOIN で paperid（STRING・12.7 億行）を読むためスキャン量が大きい。
--       dry run で確認してから実行する。
WITH ml AS (
  SELECT paperid, score_openalex
  FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperfields`
  WHERE fieldid = 'C119857082'
)
SELECT
  p.year,

  -- (1) 閾値別の母集団サイズ（doctype で絞った後）
  COUNT(*) AS n_all_scores,
  COUNTIF(m.score_openalex >= 0.3) AS n_ge030,
  COUNTIF(m.score_openalex >= 0.4) AS n_ge040,
  COUNTIF(m.score_openalex >= 0.5) AS n_ge050,
  COUNTIF(m.score_openalex >= 0.6) AS n_ge060,

  -- (2) 閾値 0.5 の母集団のうち、D-index が有効なもの
  COUNTIF(m.score_openalex >= 0.5
          AND p.reference_count > 0 AND p.citation_count > 0) AS n_ge050_d_valid,
  -- 参考：0 埋め汚染に当たる論文（参考文献 0 件だが被引用あり＝本来 D=1）
  COUNTIF(m.score_openalex >= 0.5
          AND p.reference_count = 0 AND p.citation_count > 0) AS n_ge050_d_bias,

  -- (3) atypicality が有効なもの
  COUNTIF(m.score_openalex >= 0.5 AND p.Atyp_Median_Z IS NOT NULL) AS n_ge050_atyp_valid,

  -- (4) 過去／未来ベクトルの材料（閾値 0.5 の母集団で）
  AVG(IF(m.score_openalex >= 0.5, p.reference_count, NULL)) AS avg_refs_ge050,
  AVG(IF(m.score_openalex >= 0.5, p.citation_count, NULL)) AS avg_cites_ge050,
  -- 埋め込みの重心が安定する最低ラインとして参考文献 5 件以上を仮に置く
  COUNTIF(m.score_openalex >= 0.5 AND p.reference_count >= 5) AS n_ge050_refs5plus,
  COUNTIF(m.score_openalex >= 0.5 AND p.citation_count >= 5) AS n_ge050_cites5plus
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers` AS p
JOIN ml AS m
  ON p.paperid = m.paperid
WHERE p.year BETWEEN 2012 AND 2018
  AND p.doctype IN ('article', 'preprint')
GROUP BY p.year
ORDER BY p.year;
