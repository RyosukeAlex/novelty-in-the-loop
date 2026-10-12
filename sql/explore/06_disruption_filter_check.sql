-- 【追加確認】disruption の 0 埋めは「欠損」か「系統的な下方バイアス」か
--             ＋ スナップショットの実際の終端日
--
-- 動機1（D=1 問題）：
--   D = (n_i - n_j) / (n_i + n_j + n_k)
--   参考文献が 0 件の論文では、その参考文献を引用する後続研究が存在しえないため
--   n_j = n_k = 0 が確定する。したがって被引用が 1 件以上あれば D = n_i / n_i = 1 と
--   **定義上一意に決まる**。被引用も 0 件のときだけ 0/0 で計算不能。
--   → v2 がこれらをまとめて 0 にしているなら、「本来 D=1 の論文を 0 にしている」
--     ことになり、単なる欠損処理ではなく **系統的な下方バイアス** である。
--     その規模をここで数える。
--
-- 動機2（フィルタ条件の誤り）：
--   定義書には `reference_count > 0 AND cited_by_count > 0` と書いたが、
--   cited_by_count は OpenAlex のグローバル値なので「コーパス外からは引用されているが
--   コーパス内の引用は 0」の論文が通過してしまう。その論文では n_i が 0 で D は計算できない。
--   正しくは citation_count（コーパス内再計算値）で絞る必要がある。
--   → 誤ったフィルタが何本を通過させてしまうかを数えて、修正の必要性を定量化する。
--
-- 動機3（スナップショット終端）：
--   C3/C5/C10 の「窓が閉じている年」の目安は、データの終端が 2024 年の何月かで 1 年ずれる。
--
-- 設計：参照列は date, reference_count, citation_count, cited_by_count, disruption の 5 列。
SELECT
  -- 【動機3】スナップショットの終端
  MAX(date) AS max_date,
  MAX(CASE WHEN year <= 2024 THEN date END) AS max_date_le2024,

  COUNT(*) AS n_total,

  -- 【動機1】参考文献 0 件の内訳
  --   本来 D=1 であるべき論文（0 埋めされているなら下方バイアス）
  COUNTIF(reference_count = 0 AND citation_count > 0) AS n_ref0_cited,
  COUNTIF(reference_count = 0 AND citation_count > 0 AND disruption = 0) AS n_ref0_cited_stored0,
  --   真に計算不能な論文（0/0）
  COUNTIF(reference_count = 0 AND citation_count = 0) AS n_ref0_nocite,

  -- 【動機2】フィルタ条件の比較
  --   D が計算できる論文（正しいフィルタ）
  COUNTIF(reference_count > 0 AND citation_count > 0) AS n_computable_correct,
  --   誤ったフィルタ（cited_by_count 版）が通す論文
  COUNTIF(reference_count > 0 AND cited_by_count > 0) AS n_computable_wrong,
  --   誤ったフィルタだけが通してしまう論文＝コーパス内被引用 0 なのに通過する
  COUNTIF(reference_count > 0 AND cited_by_count > 0 AND citation_count = 0) AS n_wrongly_passed,

  -- 計算可能な論文の中で disruption = 0 のもの（これは本物の 0 の可能性がある）
  COUNTIF(reference_count > 0 AND citation_count > 0 AND disruption = 0) AS n_computable_d0
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers`;
