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

1. **複数 Butler リポジトリ対応**: 同一インスタンスで複数のリポジトリ（例: `embargo`, `DR1`, `DR2`）のデータにアクセス
2. **後方互換性**: 既存のデプロイメント設定を壊さない
3. **設定の柔軟性**: 新しいリポジトリ追加時にコード変更が不要
4. **認証の分離**: リポジトリごとに異なる認証情報を使用可能

---

## 設計案

### 案 1: CcdDataTypeConfig にリポジトリ情報を追加

**概要**: 各 `CcdDataType` に Butler リポジトリ情報を含める

```python
class CcdDataTypeConfig(BaseModel):
    name: str
    display_name: str
    collections: list[str]
    data_id_key: str = "exposure"
    order_by: list[str] = ["-exposure"]
    partial: bool = False
    # 新規追加
    butler_repo: str = "embargo"  # Butler リポジトリ名
    instrument: str = "LSSTCam"   # 使用する instrument
```

**メリット**:
- データタイプごとに異なるリポジトリを使用可能
- 設定が一箇所に集約される
- 既存の設定構造を拡張するだけ

**デメリット**:
- 同じリポジトリを複数のデータタイプで使う場合、設定が重複

**Helm values 例**:
```yaml
ccd_data_types:
  - name: raw
    display_name: Raw
    collections: ["LSSTCam/raw/all"]
    butler_repo: embargo
    instrument: LSSTCam
  - name: dr1_calexp
    display_name: DR1 CalExp
    collections: ["DR1/calexp"]
    butler_repo: dr1
    instrument: LSSTCam
```

### 案 2: Butler リポジトリを独立した設定として分離

**概要**: Butler リポジトリ定義と CcdDataType を分離し、参照関係で結ぶ

```python
class ButlerRepoConfig(BaseModel):
    name: str  # リポジトリ識別子
    uri: str   # Butler リポジトリ URI（将来的に直接指定を可能にする場合）
    instrument: str = "LSSTCam"

class CcdDataTypeConfig(BaseModel):
    name: str
    display_name: str
    collections: list[str]
    data_id_key: str = "exposure"
    order_by: list[str] = ["-exposure"]
    partial: bool = False
    butler_repo: str = "embargo"  # ButlerRepoConfig.name への参照
```

**メリット**:
- リポジトリ設定の再利用が容易
- リポジトリごとの認証情報管理が明確

**デメリット**:
- 設定がやや複雑になる
- 二つの設定間の整合性チェックが必要

**Helm values 例**:
```yaml
butler_repos:
  - name: embargo
    instrument: LSSTCam
  - name: dr1
    instrument: LSSTCam

ccd_data_types:
  - name: raw
    display_name: Raw
    collections: ["LSSTCam/raw/all"]
    butler_repo: embargo
```

### 案 3: 現状維持 + 環境変数でオーバーライド

**概要**: デフォルトリポジトリを設定で変更可能にする最小限の変更

```python
class Config(BaseSettings):
    # 新規追加
    default_butler_repo: str = "embargo"
    default_instrument: str = "LSSTCam"
```

**メリット**:
- 実装が最も簡単
- 既存の動作に影響なし

**デメリット**:
- 同時に複数リポジトリを使うことは不可能
- 将来的な拡張に限界

---

## 推奨案

**フェーズ 1 (短期)**: 案 1 を採用

現在の `CcdDataTypeConfig` に `butler_repo` と `instrument` フィールドを追加する最小限の変更。
これにより、異なるリポジトリのデータを異なる CcdDataType として定義できる。

**フェーズ 2 (中期)**: 案 2 への移行検討

複数のリポジトリを頻繁に使う運用が確立された場合、リポジトリ設定を分離する。

---

## 実装ステップ (フェーズ 1)

### 1. CcdDataTypeConfig の拡張

```python
# backend/src/quicklook/config/__init__.py
class CcdDataTypeConfig(BaseModel):
    name: str
    display_name: str
    collections: list[str]
    data_id_key: str = "exposure"
    order_by: list[str] = ["-exposure"]
    partial: bool = False
    butler_repo: str = "embargo"      # 新規
    instrument: str = "LSSTCam"       # 新規
```

### 2. butler_datasource の修正

```python
# backend/src/quicklook/datasource/butler_datasource/__init__.py
class DataTypeSpecificDataSource:
    def __init__(self, data_type_config: CcdDataTypeConfig):
        from lsst.daf.butler import Butler
        
        self._config = data_type_config
        self._butler: ButlerType = Butler(
            data_type_config.butler_repo,  # 設定から取得
            instrument=data_type_config.instrument,  # 設定から取得
            collections=data_type_config.collections,
        )
```

### 3. Helm values スキーマ更新

```json
{
  "ccd_data_type_config": {
    "properties": {
      "butler_repo": {
        "type": "string",
        "default": "embargo"
      },
      "instrument": {
        "type": "string",
        "default": "LSSTCam"
      }
    }
  }
}
```

### 4. 認証情報の対応

複数リポジトリに対応するため、各リポジトリ用の認証情報を Vault に追加：

```yaml
# secrets.yaml
applicationSecrets:
  - key: aws-credentials-embargo
  - key: aws-credentials-dr1
  - key: postgres-credentials-embargo
  - key: postgres-credentials-dr1
```

環境変数でプロファイル名を動的に設定：

```yaml
# _helpers.tpl
{{- range .Values.butler_repos }}
- name: LSST_RESOURCES_S3_PROFILE_{{ .name }}
  value: {{ .s3_endpoint | quote }}
{{- end }}
```

---

## 考慮事項

### 認証と権限

- 各リポジトリに異なるアクセス権限が必要な場合がある
- Vault シークレットを分離し、Pod にマウントするボリュームを追加

### キャッシュ管理

- 異なるリポジトリのタイルは異なるパスでキャッシュ
- `visit_name` にリポジトリ識別子を含めるか、S3 キーパターンを変更

### UI 表示

- フロントエンドでリポジトリごとにデータタイプをグループ化する UI 検討
- 現在は `ccd_data_types` をフラットに表示

### パフォーマンス

- 複数の Butler 接続を維持する場合のメモリ使用量
- 接続プールの管理

---

## タイムライン

| フェーズ | 作業内容 | 期間 |
|---------|---------|------|
| 1.1 | CcdDataTypeConfig に butler_repo, instrument 追加 | 1 日 |
| 1.2 | butler_datasource で設定を使用 | 1 日 |
| 1.3 | Helm values/schema 更新 | 0.5 日 |
| 1.4 | テスト・検証 | 1 日 |
| 2.0 | 案 2 への移行検討（必要に応じて） | TBD |

---

## 関連ドキュメント

- [Butler 公式ドキュメント](https://pipelines.lsst.io/modules/lsst.daf.butler/)
- [Phalanx デプロイメント ガイド](./phalanx.ja.md)
- [システム設計概要](./concept.ja.md)
