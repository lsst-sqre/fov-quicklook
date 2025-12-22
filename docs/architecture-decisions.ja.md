# 重要なファイルと決定ポイント

| 決定 | 参照先 |
|------|-------|
| "新しい設定を追加するには?" | `backend/src/quicklook/config.py` に Pydantic フィールドを追加。環境変数は自動的に `QUICKLOOK_<field_name>` になる |
| "永続状態をどこに保存?" | PostgreSQL データベース (SQLAlchemy モデル: `backend/src/quicklook/db/`) — ジェネレーターメモリには永続化しない |
| "コーディネーターからジェネレーターを呼び出すには?" | `Rpc.create()` + RPC ハンドラーを使用 (参照: `backend/src/quicklook/rpc/` と `backend/README.ja.md` の例) |
| "Butler なしでテストするには?" | `config.data_source=dummy` を使用。`pytest.ini` が自動的に設定 |
| "ジェネレーター再起動を処理するには?" | すべての状態が失われていると仮定。再ディスパッチが必要なインフライトジョブをデータベースで確認 |
