-- ML 2016-2018 のパイロット対象について、テキスト（title/abstract）と
-- 既存指標（D-index / atypicality）が同時に揃う本数を数える。
-- 目的: 検証②（テキストから「動き」を予測）の実効サンプル数を確定する。
--
-- 設計メモ:
--   - papertitleabstract は 251GB だが paperid 列しか読まないので安い。
--     「テキストがあるか」は行の存在で判定でき、title/abstract 本体は不要。
--   - 0埋めバイアス除去は reference_count > 0 AND citation_count > 0（docs/handover.md §3-1）。
--   - cited_by_count ではなく citation_count を使う（§3-3）。

WITH target AS (
  SELECT DISTINCT
    p.paperid,
    p.reference_count,
    p.citation_count,
    p.Atyp_Median_Z
  FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers` AS p
  JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperfields` AS f
    ON p.paperid = f.paperid
  WHERE p.year BETWEEN 2016 AND 2018
    AND p.doctype IN ('article', 'preprint')
    AND p.is_retracted = FALSE
    AND f.fieldid = 'C119857082'        -- Machine learning
    AND f.score_openalex >= 0.5
)
SELECT
  COUNT(*)                                            AS n_target,
  COUNTIF(t.paperid IS NOT NULL)                      AS n_has_text,
  COUNTIF(g.d_valid)                                  AS n_d_valid,
  COUNTIF(g.Atyp_Median_Z IS NOT NULL)                AS n_atyp_valid,
  -- 検証②の実効サンプル: テキストと D-index が両方使える
  COUNTIF(t.paperid IS NOT NULL AND g.d_valid)        AS n_text_and_d,
  -- 三つ揃い（atypicality も含めた比較用）
  COUNTIF(t.paperid IS NOT NULL
          AND g.d_valid
          AND g.Atyp_Median_Z IS NOT NULL)            AS n_text_d_atyp,
  -- 参考文献 >=5 かつ被引用 >=5（過去/未来ベクトルが安定する条件）
  COUNTIF(t.paperid IS NOT NULL
          AND g.reference_count >= 5
          AND g.citation_count >= 5)                  AS n_text_and_vec5
FROM (
  SELECT *, (reference_count > 0 AND citation_count > 0) AS d_valid
  FROM target
) AS g
LEFT JOIN `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papertitleabstract` AS t
  ON g.paperid = t.paperid
