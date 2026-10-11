-- SciSciNet-v2の全テーブルの列定義を一覧表示する。

SELECT
    table_name, 
    column_name,
    data_type,
    is_nullable,
    ordinal_position
FROM `ksm-rch-scisciturbo.sciscinet_v2.INFORMATION_SCHEMA.COLUMNS`
ORDER BY table_name, ordinal_position;