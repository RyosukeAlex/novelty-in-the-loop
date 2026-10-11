-- 【確認項目 2, 3, 4】papers の被引用数カラムの違い／C3・C5・C10 の 0 の意味／指標の欠損傾向
--
-- 目的：
--   2) cited_by_count と citation_count が何者か（一致するか、ずれ方に規則はあるか）
--   3) C3/C5/C10 の 0 が「引用なし」か「未計算」か
--      → 判定法：年ごとに見る。2022 年の論文に C10 の実数が入っていたらおかしい。
--        0 なのか NULL なのかで、未計算の表現方法が分かる
--      → 累積かどうかも検定：累積なら C3 <= C5 <= C10 が常に成り立つ
--   4) disruption / Atyp_* の欠損傾向
--      → disruption = 0 が本当の 0 か未計算のプレースホルダかを、参考文献数 0 との同時出現で見る
--
-- 設計：3 つの確認項目はすべて papers の同じ行を見るため 1 本にまとめた。
--       別々のクエリにすると year 列を 3 回スキャンして課金が増えるため。
--       参照列は year, cited_by_count, citation_count, reference_count,
--       C3, C5, C10, disruption, Atyp_Median_Z, Atyp_10pct_Z, Atyp_Pairs の 11 列。
SELECT
  year,
  COUNT(*) AS n_papers,

  -- 【2】cited_by_count vs citation_count
  COUNTIF(cited_by_count = citation_count) AS n_cite_equal,
  COUNTIF(cited_by_count > citation_count) AS n_citedby_gt,
  COUNTIF(cited_by_count < citation_count) AS n_citedby_lt,
  AVG(cited_by_count) AS avg_cited_by_count,
  AVG(citation_count) AS avg_citation_count,

  -- 【3】C3/C5/C10 の 0 と NULL の出方
  COUNTIF(C3 IS NULL) AS n_c3_null,
  COUNTIF(C3 = 0) AS n_c3_zero,
  COUNTIF(C5 IS NULL) AS n_c5_null,
  COUNTIF(C5 = 0) AS n_c5_zero,
  COUNTIF(C10 IS NULL) AS n_c10_null,
  COUNTIF(C10 = 0) AS n_c10_zero,
  -- 累積性の検定（累積なら両方 0 件になるはず）
  COUNTIF(C5 < C3) AS n_violate_c5_lt_c3,
  COUNTIF(C10 < C5) AS n_violate_c10_lt_c5,

  -- 【4】disruption / Atyp_* の欠損
  COUNTIF(disruption IS NULL) AS n_disruption_null,
  COUNTIF(disruption = 0) AS n_disruption_zero,
  -- 0 がプレースホルダかの検証：参考文献も被引用も無い論文で 0 になっていないか
  COUNTIF(disruption = 0 AND reference_count = 0) AS n_disruption_zero_norefs,
  COUNTIF(Atyp_Median_Z IS NULL) AS n_atyp_median_null,
  COUNTIF(Atyp_10pct_Z IS NULL) AS n_atyp_10pct_null,
  COUNTIF(Atyp_Pairs = 0) AS n_atyp_pairs_zero
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers`
GROUP BY year
ORDER BY year;
