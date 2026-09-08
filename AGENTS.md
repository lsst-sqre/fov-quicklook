# FOV-Quicklook Codex instructions

このリポジトリでは、GitHub Copilot と Codex が同じプロジェクト規約を使う。

## 共通指示

作業を始める前に [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
を読み、その内容をこのリポジトリの共通指示として適用する。ユーザーの明示的な指示が
矛盾する場合は、ユーザーの指示を優先する。

## プロジェクトスキル

タスクが次のいずれかに該当する場合は、作業前に対応する `SKILL.md` を全文読んで、そこ
に定められた手順を適用する。これらのファイルは Copilot 用に置かれているが、Codex でも
そのまま利用する正本である。

- デプロイ、ArgoCD の状態確認・sync・restart、ログ取得、参照ブランチ切替:
  `.github/skills/argocd-deployment/SKILL.md`
- `/debug/` の Jupyter、Butler 調査、リモート Python / bash 実行:
  `.github/skills/debug-jupyter/SKILL.md`
- デプロイ後の healthz、frontend、ジョブ・キャッシュ・visit 確認、quicklook 再生成:
  `.github/skills/deploy-verification/SKILL.md`

タスクに該当しないスキルは読み込まない。スキルの指示がユーザーの明示的な指示と矛盾
する場合は、ユーザーの指示を優先する。

## 更新方針

プロジェクト全体の共通規約を変更するときは `.github/copilot-instructions.md` を更新する。
Codex だけに必要な読み込み規則を変更するときは、この `AGENTS.md` を更新する。
個別スキルの内容は `.github/skills/` 側だけを更新し、同じ内容を別の場所へ複製しない。
