# Butler 複数リポジトリ対応 設計戦略

## 現状分析

### 現在の構造

FOV-Quicklook は現在、以下の構成で Butler `embargo` リポジトリに接続しています：

```python
# backend/src/quicklook/datasource/butler_datasource/__init__.py
self._butler: ButlerType = Butler(
    'embargo',  # ← ハードコード
    instrument=default_instrument,
    collections=data_type_config.collections,
)
```

### ハードコードされている箇所

1. **butler_datasource/__init__.py**: `Butler('embargo', ...)` の呼び出し
2. **k8s/helmchart/values.yaml**: `butler_settings.data_repos.embargo`
3. **Helm テンプレート**: `LSST_RESOURCES_S3_PROFILE_embargo` 環境変数

### 現在の設定可能な部分

- `collections`: `CcdDataTypeConfig` 経由で設定可能
- `instrument`: `default_instrument = 'LSSTCam'` としてハードコード
- 認証情報: Vault/Secrets 経由で設定可能

---

## 目標

1. **複数 Butler リポジトリ対応**: 同一インスタンスで複数のリポジトリ（例: `embargo`, `main`）のデータにアクセス
2. **後方互換性**: 既存のデプロイメント設定を壊さない
3. **設定の柔軟性**: 新しいリポジトリ追加時にコード変更が不要
4. **認証の分離**: リポジトリごとに異なる認証情報を使用可能

### 対象リポジトリ

- **embargo**: エンバーゴ期間中のデータ（現在のデフォルト）
- **main**: 公開済みの本番データ

---

## 設計案

### 案 1: CcdDataTypeConfig にリポジトリ情報を追加（採用）

**概要**: 各 `CcdDataType` に Butler リポジトリ情報を含める

```python
class CcdDataTypeConfig(BaseModel):
    """CCDデータタイプの設定"""
    
    # 識別子（URL、キャッシュパス等で使用）
    id: str  # 例: 'embargo/raw', 'main/calexp'
    
    # 表示名（UI表示用）
    display_name: str  # 例: 'Raw', 'CalExp (Main)'
    
    # Butler クエリ設定
    name: str  # Butler dataset type name (例: 'raw', 'calexp')
    collections: list[str]  # Butlerコレクション名
    data_id_key: str = "exposure"  # データ識別キー
    order_by: list[str] = ["-exposure"]  # クエリの並び順
    partial: bool = False  # 部分読み込みを使用するか
    
    # Butler リポジトリ設定
    repository_name: str = "embargo"  # Butler リポジトリ名
    instrument: str = "LSSTCam"  # 使用する instrument
```

**設計のポイント**:

1. **`id` と `name` の分離**:
   - `id`: システム内部での一意識別子。URL パス、S3 キャッシュパス、フロントエンドでの識別に使用
     - 例: `embargo/raw`, `main/calexp`
   - `name`: Butler の dataset type 名。Butler クエリで使用
     - 例: `raw`, `calexp`, `post_isr_image`
   
2. **`repository_name`**: Butler リポジトリ名（`embargo`, `main` など）
   - `Butler(repository_name, ...)` の第一引数として使用

3. **`instrument`**: Butler の instrument 名（デフォルト: `LSSTCam`）

**メリット**:
- データタイプごとに異なるリポジトリを使用可能
- 設定が一箇所に集約される
- 既存の設定構造を拡張するだけ
- `id` と `name` の分離により、同じデータタイプを異なるリポジトリから取得可能

**デメリット**:
- 同じリポジトリを複数のデータタイプで使う場合、設定が重複

**Helm values 例**:
```yaml
# デフォルト設定（embargo リポジトリのみ）
ccd_data_types:
  - id: raw
    name: raw
    display_name: Raw
    collections: ["LSSTCam/raw/all"]
    repository_name: embargo
    instrument: LSSTCam
    data_id_key: exposure
    order_by: ["-day_obs", "-exposure"]
    partial: false

# 複数リポジトリ使用時の例
ccd_data_types:
  - id: embargo/raw
    name: raw
    display_name: Raw (Embargo)
    collections: ["LSSTCam/raw/all"]
    repository_name: embargo
    instrument: LSSTCam
  - id: main/calexp
    name: calexp
    display_name: CalExp (Main)
    collections: ["LSSTCam/runs/DR1"]
    repository_name: main
    instrument: LSSTCam
```

### 案 2: Butler リポジトリを独立した設定として分離

**概要**: Butler リポジトリ定義と CcdDataType を分離し、参照関係で結ぶ

```python
class ButlerRepoConfig(BaseModel):
    name: str  # リポジトリ識別子
    uri: str   # Butler リポジトリ URI
    instrument: str = "LSSTCam"

class CcdDataTypeConfig(BaseModel):
    id: str
    name: str
    display_name: str
    collections: list[str]
    repository_name: str = "embargo"  # ButlerRepoConfig.name への参照
```

**メリット**:
- リポジトリ設定の再利用が容易
- リポジトリごとの認証情報管理が明確

**デメリット**:
- 設定がやや複雑になる
- 二つの設定間の整合性チェックが必要

### 案 3: 現状維持 + 環境変数でオーバーライド

**概要**: デフォルトリポジトリを設定で変更可能にする最小限の変更

**デメリット**:
- 同時に複数リポジトリを使うことは不可能
- 将来的な拡張に限界

---

## 推奨案: 案 1 を採用

現在の `CcdDataTypeConfig` に `repository_name` と `instrument` フィールドを追加し、`id` と `name` を分離する。

**理由**:
1. 最小限の変更で複数リポジトリに対応可能
2. `embargo` と `main` の両方からデータを取得できる
3. 将来的なリポジトリ追加も設定変更のみで対応可能

---

## 実装ステップ

### 1. CcdDataTypeConfig の拡張

```python
# backend/src/quicklook/config/__init__.py
class CcdDataTypeConfig(BaseModel):
    """CCDデータタイプの設定"""
    
    # 識別子（URL、キャッシュパス等で使用）
    id: str  # 例: 'raw', 'embargo/raw'
    
    # 表示名（UI表示用）
    display_name: str
    
    # Butler クエリ設定
    name: str  # Butler dataset type name
    collections: list[str]
    data_id_key: str = "exposure"
    order_by: list[str] = ["-exposure"]
    partial: bool = False
    
    # Butler リポジトリ設定
    repository_name: str = "embargo"
    instrument: str = "LSSTCam"
```

### 2. butler_datasource の修正

```python
# backend/src/quicklook/datasource/butler_datasource/__init__.py
class DataTypeSpecificDataSource:
    def __init__(self, data_type_config: CcdDataTypeConfig):
        from lsst.daf.butler import Butler
        
        self._config = data_type_config
        self._butler: ButlerType = Butler(
            data_type_config.repository_name,  # 設定から取得
            instrument=data_type_config.instrument,  # 設定から取得
            collections=data_type_config.collections,
        )
```

### 3. 影響を受ける箇所

現在 `CcdDataType` (`name` フィールド) が使われている箇所を `id` に置き換える:

- **URL パス**: `/api/quicklooks/{data_type}/{exposure}` → `id` を使用
- **S3 キャッシュキー**: `quicklooks/{data_type}:{visit}/...` → `id` を使用
- **フロントエンド**: data type の選択・表示 → `id` を使用

**Butler クエリ**では引き続き `name` を使用:
- `butler.query_datasets(data_type_config.name, ...)`

### 4. Helm values スキーマ更新

```json
{
  "ccd_data_type_config": {
    "properties": {
      "id": {
        "type": "string",
        "description": "Unique identifier for the data type (used in URLs, cache paths)"
      },
      "name": {
        "type": "string",
        "description": "Butler dataset type name for queries"
      },
      "repository_name": {
        "type": "string",
        "default": "embargo",
        "description": "Butler repository name"
      },
      "instrument": {
        "type": "string",
        "default": "LSSTCam",
        "description": "Butler instrument name"
      }
    },
    "required": ["id", "name", "display_name", "collections"]
  }
}
```

### 5. 認証情報の対応

複数リポジトリに対応するため、各リポジトリ用の認証情報を設定:

```yaml
# values.yaml
butler_settings:
  envs:
    - name: LSST_RESOURCES_S3_PROFILE_embargo
      value: "https://sdfembs3.sdf.slac.stanford.edu"
    - name: LSST_RESOURCES_S3_PROFILE_main
      value: "https://s3dfrgw.slac.stanford.edu"
  data_repos:
    embargo: "s3://embargo@rubin-summit-users/butler.yaml"
    main: "s3://main@rubin-users/butler.yaml"
```

---

## 考慮事項

### キャッシュ管理

- `id` がキャッシュキーの一部となるため、異なるリポジトリのタイルは自動的に分離される
- 例: `quicklooks/raw:12345/...` vs `quicklooks/main/calexp:12345/...`

### UI 表示

- `display_name` を使用してユーザーフレンドリーな名前を表示
- デフォルト設定（embargo のみ）では `display_name` にリポジトリ名を含める必要なし

### 後方互換性

- デフォルト値 (`repository_name: "embargo"`, `instrument: "LSSTCam"`) により既存の設定は変更不要
- `id` フィールドを追加するが、設定しない場合は `name` と同じ値を使用

---

## デフォルト設定

embargo リポジトリのみを使用する場合の設定:

```yaml
ccd_data_types:
  - id: raw
    name: raw
    display_name: Raw
    collections: ["LSSTCam/raw/all"]
    data_id_key: exposure
    order_by: ["-day_obs", "-exposure"]
    partial: false
    repository_name: embargo
    instrument: LSSTCam
  - id: post_isr_image
    name: post_isr_image
    display_name: Post-ISR
    collections: ["LSSTCam/runs/nightlyValidation"]
    data_id_key: exposure
    order_by: ["-exposure"]
    partial: true
    repository_name: embargo
    instrument: LSSTCam
  - id: preliminary_visit_image
    name: preliminary_visit_image
    display_name: Preliminary
    collections: ["LSSTCam/runs/nightlyValidation"]
    data_id_key: visit
    order_by: ["-visit"]
    partial: true
    repository_name: embargo
    instrument: LSSTCam
```

---

## 関連ドキュメント

- [Butler 公式ドキュメント](https://pipelines.lsst.io/modules/lsst.daf.butler/)
- [Phalanx デプロイメント ガイド](./phalanx.ja.md)
- [システム設計概要](./concept.ja.md)
