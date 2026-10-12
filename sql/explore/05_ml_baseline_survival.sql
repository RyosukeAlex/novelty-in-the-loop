-- ML分野・2012〜2014年において、
--   (a) score_openalex の帯ごとに対象が何本あるか（閾値決定のため）
--   (b) そのうち D-index が有効な論文が何本残るか（第2章の比較対象が成立するか）
--   (c) atypicality が有効な論文が何本残るか（代替の比較対象）
-- を同時に出す。
--
-- D-index の有効条件：reference_count > 0 AND citation_count > 0
--   （disruption 列は参考文献0件の論文をすべて 0 で埋めており、
--     定義上 D=1 になるべきものと計算不能なものが混在している）
-- cited_by_count ではなく citation_count を使う（paperrefs と整合するため）
WITH ml AS (
  SELECT
    p.paperid,
    p.year,
    f.score_openalex,
    p.reference_count,
    p.citation_count,
    p.disruption,
    p.Atyp_Median_Z
  FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers` AS p
  JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperfields` AS f
    ON p.paperid = f.paperid
  WHERE p.year BETWEEN 2012 AND 2014
    AND f.fieldid = 'C119857082'          -- Machine learning
    AND p.doctype IN ('article', 'preprint')
    AND p.is_retracted = FALSE
)
SELECT
  CASE
    WHEN score_openalex >= 0.5 THEN 'a_0.5+'
    WHEN score_openalex >= 0.4 THEN 'b_0.4-0.5'
    WHEN score_openalex >= 0.3 THEN 'c_0.3-0.4'
    WHEN score_openalex >= 0.2 THEN 'd_0.2-0.3'
    WHEN score_openalex >= 0.1 THEN 'e_0.1-0.2'
    ELSE                              'f_0.0-0.1'
  END AS score_band,
  COUNT(*)                                                          AS n_papers,
  COUNTIF(reference_count > 0 AND citation_count > 0)               AS n_dindex_valid,
  COUNTIF(Atyp_Median_Z IS NOT NULL)                                AS n_atyp_valid,
  COUNTIF(reference_count > 0 AND citation_count > 0
          AND Atyp_Median_Z IS NOT NULL)                            AS n_both_valid,
  ROUND(AVG(reference_count), 1)                                    AS avg_refs,
  ROUND(AVG(citation_count), 1)                                     AS avg_cites
FROM ml
GROUP BY score_band
ORDER BY score_band
