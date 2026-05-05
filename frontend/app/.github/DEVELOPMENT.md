# FOV-Quicklook フロントエンド開発ガイド

## 概要

このドキュメントはフロントエンド（React/TypeScript）開発に特化したガイドです。
プロジェクト全体の概要は `/.github/copilot-instructions.md` を参照してください。

---

## 技術スタック

- **React 18** + **TypeScript**
- **Vite** (ビルドツール)
- **Redux Toolkit** (状態管理)
- **RTK Query** (API クライアント、OpenAPI から自動生成)
- **SCSS Modules** (スタイリング)
- **Vitest** (テスト)

---

## ディレクトリ構造

| パス | 目的 |
|------|------|
| `src/components/` | 再利用可能な UI コンポーネント |
| `src/pages/` | ページコンポーネント |
| `src/store/` | Redux ストア設定 |
| `src/store/api/` | RTK Query (OpenAPI から自動生成) |
| `src/hooks/` | カスタムフック |
| `src/utils/` | ユーティリティ関数 |
| `src/StellarGlobe/` | 天球可視化コンポーネント |

---

## コードスタイル

### TypeScript

- 厳密な型チェックを使用
- `any` 使用時は `// @ts-ignore` + 理由コメント必須
- 型定義は明示的に（推論に頼りすぎない）

### React

- 関数型コンポーネントを使用
- 状態管理には React Hooks (`useState`, `useEffect`, etc.)
- Redux 状態にはカスタムフック (`useSelector`, `useDispatch`)

### UI テキスト

- **ユーザーに見えるテキスト（ボタン、ラベル、confirm ダイアログ等）は英語のみ**
- 日本語は使用しない

---

## 開発コマンド

```bash
npm run dev          # 開発サーバー起動
npm run build        # プロダクションビルド
npm run type-check   # 型チェック
npm run lint         # ESLint
npm run test         # Vitest でテスト実行
```

---

## SCSS スタイル

### 型生成

スタイルを編集したら、必ず以下を実行して型定義を更新：

```bash
npm run scss-types
```

これにより SCSS モジュールの型エラーが解消されます。

### 規約

- CSS Modules を使用（`*.module.scss`）
- クラス名は camelCase

---

## API クライアント (RTK Query)

### 自動生成

バックエンドの OpenAPI スキーマから API クライアントを生成：

```bash
npm run api:rtk-query
```

生成されたファイル: `src/store/api/openapi.ts`

### 使用方法

```typescript
import { useGetVisitsQuery } from '../store/api/openapi'

const { data, isLoading, error } = useGetVisitsQuery()
```

---

## テスト

- **Vitest** + **React Testing Library** を使用
- テストファイルは `*.test.ts` または `*.test.tsx`

```bash
npm run test         # テスト実行
```

---

## Git コミット

- **コミットメッセージは英語**で記述

---

## 依存ライブラリ（主要）

| ライブラリ | 用途 |
|-----------|------|
| `@reduxjs/toolkit` | 状態管理 |
| `react-router-dom` | ルーティング |
| `@stellar-globe/*` | 天球可視化（`frontend/lib/stellar-globe/` に vendoring したローカルパッケージ） |
| `@hpcc-js/wasm-zstd` | Zstd 圧縮/展開 |
| `classnames` | 条件付きクラス名 |

---

## よくある落とし穴

- SCSS 編集後に `npm run scss-types` を忘れると型エラーになる
- API スキーマ変更後は `npm run api:rtk-query` で再生成が必要
