# ベンチマーク結果と分析：まとめ

## エグゼクティブサマリー

tile-compressed FITS (RICE_1圧縮) ファイルの読み込みにおいて、**`astropy.io.fits.open(path, memmap=False)`が最速**であることが判明しました（約0.625秒）。

現在の`fast_open_comressed_fits`実装は約1.18倍遅く（0.738秒）、`mineo_fits_decompress`はRICE_1圧縮に未対応です。

## 詳細ベンチマーク結果

### テスト条件
- **ファイル**: `raw_2025092100465-R12_S21.fits` (21.29 MB)
- **圧縮形式**: RICE_1 (tile-compressed FITS)
- **実行回数**: 3回の平均
- **環境**: `/dev/shm`利用可能

### 結果

| 順位 | 方法 | 平均時間 | vs最速 | 説明 |
|------|------|----------|--------|------|
| 🥇 1 | `open(path, memmap=False)` | 0.6251s | 1.00x | **最速・推奨** |
| 🥈 2 | `open(path)` デフォルト | 0.6375s | 1.02x | 僅差 |
| 🥉 3 | `mineo + BytesIO` | 0.6407s | 1.02x | 僅差だが不要な処理 |
| 4 | 元データ → /dev/shm | 0.6494s | 1.04x | I/Oオーバーヘッド |
| 5 | mineo → /dev/shm | 0.6632s | 1.06x | I/Oオーバーヘッド |
| 6 | `fast_open_comressed_fits` | 0.7376s | 1.18x | **18%遅い** |
| 7 | `mineo + fromstring` | 0.8097s | 1.30x | 最も遅い |

## `mineo_fits_decompress`の分析結果

### ✅ サポートされる形式
- **GZIP_2圧縮** のみ
- 2次元画像データ
- BINTABLEからIMAGEへの完全な変換

### ❌ サポートされない形式（重要）

#### 1. RICE_1圧縮（今回のテストファイル）
```
ZCMPTYPE= 'RICE_1  '  ← mineo_fits_decompressは未対応
```

**結果**: 圧縮を展開せず、元のBINTABLE形式のままバイト列を返す。

#### 2. その他の制限
- 3次元以上のキューブデータ
- PLIO, HCOMPRESS等の他の圧縮アルゴリズム

### コードレビュー結果
```c
// lib/mineo-fits-decompress/fuse-fitsfs/fitsfile.c:1211-1216
if(!essential_cards->zimage
|| 2 != essential_cards->znaxis
|| 0 != strcmp(essential_cards->xtension, "BINTABLE")
|| 0 != strcmp(essential_cards->zcmptype, "GZIP_2")  // ← GZIP_2のみ！
|| !(essential_cards->bitpix >= 0 || 0 == strcmp(essential_cards->zquantiz, "NONE"))
){
    errno = EILSEQ;
    return NULL;
}
```

**結論**: `mineo_fits_decompress`はGZIP_2専用ツールであり、RICE_1（LSSTで一般的）には不適切。

## `fast_open_comressed_fits`の性能分析

### 現在の実装の問題点

1. **圧縮HDU検出**: バイト列全体をスキャン（最大100KB）
2. **astropy経由の処理**: 
   - 圧縮FITSを`astropy.io.fits.open(BytesIO(buf))`で開く
   - データを`numpy array`にコピー
   - `tobytes()`でバイト列に変換
   - `memoryview`を作成
3. **FastHdu変換**: `DataSpec`を介して再度ラップ

### オーバーヘッドの原因
```python
# データのコピーが2回発生
data_array = numpy.asarray(hdu.data)        # 1. astropyから取得
data_bytes = data_array.tobytes()           # 2. bytes化（コピー）
data_view = memoryview(data_bytes)          # 3. memoryview化
```

## 推奨事項

### ✅ 推奨: 直接`astropy.io.fits.open`を使用

```python
def preprocess_ccd_calexp(ccd_ref: CcdDataRef, path: Path) -> PreProcessedCcd:
    ccd_name = ccd_ref.ccd_name
    with timeit(f'preprocess-{ccd_ref.fullname}'):
        # シンプルかつ最速
        hdul = afits.open(path, memmap=False)
        try:
            bbox = ccds_by_name()[ccd_name].bbox
            pool: numpy.ndarray = numpy.array(hdul[1].data, dtype='<f4')
            with timeit(f'image-stat-{ccd_ref.fullname}'):
                stat = image_stat(pool)
            return PreProcessedCcd(
                data_ref=ccd_ref,
                bbox=bbox,
                pool=pool,
                stat=stat,
                amps=[],
                headers=fitsheader_to_list(hdul),
            )
        finally:
            hdul.close()
```

### 利点
- **18%高速化** (0.738s → 0.625s)
- すべての圧縮形式をサポート（RICE_1, GZIP_2, PLIO, HCOMPRESS等）
- コードがシンプル
- `fast_open_comressed_fits`と`mineo_fits_decompress`への依存を削除可能
- メンテナンスコスト削減

### `fast_open_comressed_fits`の今後

#### オプション1: 削除（推奨）
- 直接`astropy.io.fits.open`を使う方が速い
- 複雑さを削減

#### オプション2: 非圧縮FITS専用に特化
```python
def fast_open_uncompressed_fits(path: Path) -> FastHDUList:
    """非圧縮FITSファイル専用の高速パーサー"""
    # ZIMAGEがないことを確認
    with open(path, 'rb') as f:
        header_sample = f.read(10000)
    
    if b'ZIMAGE' in header_sample:
        raise ValueError("Compressed FITS not supported. Use astropy.io.fits.open instead.")
    
    # 高速パーサーを使用
    buf = path.read_bytes()
    parser = FitsParser(buf)
    return parser.parse()
```

## 使用場面の整理

### Astropyを使うべきケース（ほとんど全て）
- ✅ Tile-compressed FITS（RICE_1, GZIP_2等）
- ✅ 任意の圧縮アルゴリズム
- ✅ 3次元以上のデータ
- ✅ 標準的なFITSファイル全般
- ✅ 最高のパフォーマンスが必要な場合

### `FitsParser`を使う意義があるケース（限定的）
- ⚠️ 非圧縮FITSのみ
- ⚠️ astropy非依存の環境（組み込みシステム等）
- ⚠️ 特殊な要件（カスタム処理等）

### `mineo_fits_decompress`を使うケース（非推奨）
- ❌ GZIP_2専用（RICE_1は未対応）
- ❌ astropyより遅い場合が多い
- ❌ メンテナンスコスト

## 実装アクションプラン

### Phase 1: 性能改善（即座に実施可能）
1. `preprocess_ccd_calexp`で直接`astropy.io.fits.open`を使用
2. `preprocess_ccd_raw`で直接`astropy.io.fits.open`を使用
3. ベンチマークで効果を確認

### Phase 2: クリーンアップ（Phase 1後）
1. `fast_open_comressed_fits.py`の削除または非圧縮専用化
2. `mineo_fits_decompress`への依存削除（使われていなければ）
3. テストの更新

### Phase 3: ドキュメント更新
1. `README.md`にベンチマーク結果を追加
2. 設計判断の記録

## 結論

**最終推奨事項**: `astropy.io.fits.open(path, memmap=False)`を直接使用することで、コードをシンプルにしつつ、最高のパフォーマンスとすべての圧縮形式のサポートを実現できます。

**予想される効果**:
- 18%の性能向上
- コードの簡潔化
- メンテナンスコストの削減
- すべてのFITS圧縮形式への完全対応
