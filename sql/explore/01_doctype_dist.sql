-- 【確認項目 1, 6(papers側)】doctype の値分布と、撤回フラグの分布
--
-- 目的：
--   - doctype にどんな値が入り、それぞれ何件か（定義書の「文献種別」欄を埋める）
--   - papers に撤回論文が含まれるか（v1 では paperdetails 側に分離されていた）
--
-- 設計：doctype と is_retracted の 2 列のみ参照。is_retracted は BOOL なので追加コストはほぼ無い。
--       1 と 6 を 1 本にまとめ、doctype 列の重複スキャンを避けている。
SELECT
  doctype,
  is_retracted,
  COUNT(*) AS n_papers
FROM `ksm-rch-scisciturbo.sciscinet_v2.sciscinet_papers`
GROUP BY doctype, is_retracted
ORDER BY n_papers DESC;
