-- 埋め込みが必要な paperid を GCS へエクスポートする（走査スクリプトの入力）。
--
-- 対象: pilot_neighbors の has_text = TRUE（499,727 件）。
--   テキストが無い論文には SPECTER2 埋め込みも存在しない（docs/tasks/003 §1）。
-- 役割の列も出す。走査後に「取れなかった論文がどの層に偏ったか」を確認するため。

EXPORT DATA OPTIONS(
  uri = 'gs://novelty-emb-508409/targets/paperids-*.csv',
  format = 'CSV',
  overwrite = true,
  header = true
) AS
SELECT paperid, is_target, is_past, is_future
FROM `endless-comfort-508409-q8.novelty_pilot.pilot_neighbors`
WHERE has_text
ORDER BY paperid
