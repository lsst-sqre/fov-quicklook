---
name: deploy-verification
description: >
  fov-quicklookアプリケーションのデプロイ後の動作確認を行う。
  gafaelfawrトークンの取得、healthzエンドポイントの確認、フロントエンドアクセスの検証、
  ジョブ一覧・キャッシュ管理・visit一覧・quicklook再生成（WebSocket進捗監視付き）。
  デプロイ確認、動作確認、ヘルスチェック、アプリケーション検証に関するタスクで使用する。
---

# デプロイ検証スキル

## 概要

`backend/dev/verify-deploy.sh` を使って、デプロイ後のfov-quicklookアプリケーションの動作を確認する。

## 前提条件

- gafaelfawr トークンが `backend/dev/.gafaelfawr-token` に保存されていること
- トークンはブラウザの認証セッションに紐づくため、セッション切れの場合は再取得が必要
- WebSocket進捗監視には `websockets` ライブラリが必要（`backend/.venv` 内に含まれている）

## トークンの取得と設定

1. ブラウザで https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/ にアクセス（認証済み状態）
2. 開発者ツールを開く
3. 任意のリクエストを選択し「Copy as cURL」を実行
4. 以下のコマンドでトークンを抽出・保存:

```bash
cd backend/dev
./verify-deploy.sh extract-token "<コピーしたcurlコマンド>"
```

gafaelfawr cookieを含む任意のページのリクエストで構わない。

## 基本チェック

### healthz エンドポイント

```bash
./verify-deploy.sh healthz
```

出力例:
```
=== healthz エンドポイント確認 ===
✓ Status: 200
{
    "status": "ok",
    "coordinator_id": "c-e0d6a61955c8475aae542706b87841ed",
    "revision": "4af99a2112d93d6e8a38dc8918a3b8762da037db"
}
```

- `status: ok` → coordinatorが稼働中
- `revision` → デプロイされたGitリビジョン

### フロントエンド

```bash
./verify-deploy.sh frontend
```

### 全基本チェック

```bash
./verify-deploy.sh all
```

## API操作

### ジョブ一覧

```bash
./verify-deploy.sh jobs
```

アクティブなquicklook生成ジョブの一覧を表示する。

### キャッシュ一覧

```bash
./verify-deploy.sh cache
```

出力例:
```
キャッシュエントリ数: 10
合計サイズ: 139.1 GB

visit_name                                         ready   disk_usage created_at
----------------------------------------------------------------------------------------------------
embargo:raw:2026012800342                           True      13.4 GB  2026-02-10T02:05:14
main:raw:2026012800215                              True      13.3 GB  2026-02-10T05:07:29
```

### キャッシュ削除

```bash
./verify-deploy.sh cache-delete embargo:raw:2026012800326
```

### visit一覧

```bash
# デフォルト: data_type=raw, repository_name=embargo, limit=10
./verify-deploy.sh visits

# mainリポジトリのraw
./verify-deploy.sh visits raw main

# embargoのpreliminary_visit_image、20件
./verify-deploy.sh visits preliminary_visit_image embargo 20
```

出力例:
```
id                                          day_obs     filter exp_time observation_type
--------------------------------------------------------------------------------------------------------------
embargo:raw:2026012800343                  20260128       r_57     30.0 acq
embargo:raw:2026012800342                  20260128       r_57     30.0 acq
```

### quicklook再生成（進捗監視付き）

```bash
./verify-deploy.sh regenerate embargo:raw:2026012800326
```

キャッシュに存在するvisitの場合は先にキャッシュを削除:

```bash
./verify-deploy.sh cache-delete embargo:raw:2026012800326
./verify-deploy.sh regenerate embargo:raw:2026012800326
```

出力例:
```
=== quicklook再生成: embargo:raw:2026012800326 ===
POST /api/quicklooks  {"visit": "embargo:raw:2026012800326"}

WebSocket で進捗を監視中...

[   1.3s] Stage: generate_single_fits_tiles
  generate_single_fits_tiles: 150/197 (76%)
[   9.9s] Stage: merge_tiles
  merge_tiles: 5/8 (62%)
[  19.2s] Stage: upload_to_object_storage
  transfer_tiles: 6/8 (75%)
[  40.5s] Stage: ready

✓ 完了! 生成時間: 40.5秒
```

パイプラインステージ:
1. `generate_single_fits_tiles` — FITS→タイル変換
2. `merge_tiles` — Generator間でタイルマージ
3. `upload_to_object_storage` — S3アップロード
4. `ready` — 完了

## デプロイ後の典型的な検証フロー

```bash
cd backend/dev

# 1. ArgoCD でデプロイ状態を確認
./argocd.sh status

# 2. 基本チェック
./verify-deploy.sh all

# 3. visit一覧取得
./verify-deploy.sh visits

# 4. キャッシュ状態確認
./verify-deploy.sh cache

# 5. 再生成テスト（キャッシュ削除 → 再生成 → 生成時間計測）
./verify-deploy.sh cache-delete embargo:raw:2026012800326
./verify-deploy.sh regenerate embargo:raw:2026012800326

# 6. キャッシュに追加されたことを確認
./verify-deploy.sh cache
```

## visit_nameの形式

`{repository_name}:{data_type}:{exposure_id}`

利用可能なdata_type/repository_nameの組み合わせ:

| repository_name | data_type | 説明 |
|---|---|---|
| `embargo` | `raw` | Raw (Embargo) |
| `embargo` | `post_isr_image` | Post-ISR (Embargo) |
| `embargo` | `preliminary_visit_image` | Preliminary (Embargo) |
| `main` | `raw` | Raw (Main) |
| `main` | `post_isr_image` | Post-ISR (Main) |
| `main` | `preliminary_visit_image` | Preliminary (Main) |

## トークンの仕組み

- gafaelfawr はRubin Science Platformの認証基盤
- ブラウザでRSPにログインすると `gafaelfawr` cookieが設定される
- `verify-deploy.sh` はこのcookieをリクエストヘッダーに付与してアプリケーションにアクセスする
- トークンは `.gafaelfawr-token` ファイルに保存され、`.gitignore` で除外されている

## 安全性

- トークンファイル（`.gafaelfawr-token`）は `.gitignore` で除外
- アクセス先は `https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/` のみ
- 読み取り専用の操作（GET）と管理操作（DELETE、POST）を含む
