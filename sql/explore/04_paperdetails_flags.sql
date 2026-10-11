-- 【確認項目 6】papers と paperdetails が同じ 249,803,279 行である理由の確認
--
-- 背景：v1 では paperdetails の方が行数が多く、撤回論文を paperdetails 側にのみ保持する設計だった。
--       v2 では両者が同一行数であり、かつ papers 側に is_retracted 列がある。
--       → v2 は「同じ論文集合を両テーブルが持ち、撤回・paratext はフラグで区別する」設計に
--         変わった可能性が高い。それを実データで確かめる。
--
-- 設計：BOOL 列 2 つのみ参照のため安価。
--       papers 側の is_retracted は 01_doctype_dist.sql で同時に取得済み（重複スキャンを避けた）。
SELECT
  COUNT(*) AS n_rows,
  COUNTIF(is_retracted) AS n_retracted,
  COUNTIF(is_retracted IS NULL) AS n_retracted_null,
  COUNTIF(is_paratext) AS n_paratext,
  COUNTIF(is_paratext IS NULL) AS n_paratext_null
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_paperdetails`;
