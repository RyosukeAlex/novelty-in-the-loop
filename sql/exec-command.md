# 1. ファイルの中身を bq に渡して実行
## bq query --use_legacy_sql=false < sql/get-columns.sql

bq query
BigQueryでクエリを実行するための基本コマンドです（Google Cloud SDKに含まれます）。

--use_legacy_sql=false
古い「レガシーSQL」ではなく、現在の主流である「標準SQL（Standard SQL）」を使用してクエリを実行するように指定するオプションです。

"$(cat sql/eda.sql)"
sqlディレクトリ内にある eda.sql というファイルの中身（SQL文）を読み込み、そのまま文字列として bq query コマンドに渡しています。"（ダブルクォーテーション）で囲むことで、ファイル内の改行やスペースが崩れずに正しく読み込まれます。

cat sql/eda.sql（裏方）: まず cat コマンドが動いて、ファイルの中にあるSQLの文章を読み取ります。

bq query ...（主役）: 次に bq コマンドが、その読み取ったSQL文を受け取って、Google Cloud（BigQuery）のサーバーに送信して実行します。

$( ) という記号を使うことで、「catコマンドで読み取った結果を、そのまま bq コマンドに直接渡す」という処理を行っています。
