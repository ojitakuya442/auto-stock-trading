# Auto Stock Trading（自動株取引Bot）

## 概要

予算 **10万円スタート**で、日本株を中心とした自動売買システムを構築する個人プロジェクト。
まずは**調査 → 設計 → ペーパートレード → 少額実弾**の順で段階的に進める。

## 方針サマリ（2026-04-23 確定）

| 項目 | 決定 |
|---|---|
| **ゴール** | 利益重視 |
| **対象アセット** | 日本株（個別株 + ETF） |
| **メイン証券** | 三菱UFJ eスマート証券（旧auカブコム）— **これから口座開設** |
| **メインAPI** | kabu Station API |
| **メイン戦略** | **日米業種リードラグ × 部分空間正則化PCA** ([中川ほか 2026 JSAI SIG-FIN 036](https://doi.org/10.11517/jsaisigtwo.2026.FIN-036_76)) |
| **リスク許容度** | -30%（3万円）まで |
| **開発ペース** | Claude Code 主導の低関与進行 |
| **既存 crypto-trading-bot** | 独立プロジェクトとして並走 |

## 技術スタック

- Python 3.12 + uv
- API: **kabu Station API**（メイン）、立花証券e支店 API（将来候補）
- バックテスト: Backtesting.py + 自前実装（PCA戦略用）
- データ: yfinance / stooq（ヒストリカル） + kabu API（リアルタイム）
- データ蓄積: SQLite
- スケジューラ: APScheduler
- 通知: Discord Webhook

## ステータス

- [x] 調査 — [docs/research.md](docs/research.md)
- [x] 法律・税務調査 — [docs/legal-and-tax.md](docs/legal-and-tax.md)
- [x] 戦略文書化 — [docs/strategy-pca-leadlag.md](docs/strategy-pca-leadlag.md)
- [x] 設計書 — [docs/design.md](docs/design.md)
- [x] **Phase 0**: uvプロジェクト初期化、データ取得、戦略実装、ペーパーブローカー、Discord通知、GitHub Actions
- [⚠️] **Phase 1.1**: 論文戦略のバックテスト実装済み。**論文の数値を再現できていない（要追加デバッグ）**
- [x] **Phase 1.2**: ペーパートレードのend-to-endパイプライン動作確認済
- [ ] **進行中**: GitHub Actions による自動運用（要 Discord Webhook URL 設定）
- [ ] 三菱UFJ eスマート証券 口座開設（あなた側）
- [ ] Phase 2: 少額実弾（3万円）
- [ ] Phase 3: フル実弾（10万円）

## 使い方

### 開発・バックテスト

```bash
# 依存パッケージインストール
uv sync --extra dev

# バックテスト
uv run python scripts/backtest.py

# テスト
uv run pytest

# 朝の実行（手動）
uv run python scripts/morning_run.py

# 引けの実行（手動）
uv run python scripts/evening_run.py
```

### Discord 通知の設定

1. Discord でサーバー → チャンネル設定 → 連携サービス → ウェブフック → 新規作成
2. URL をコピー
3. ローカル: `cp .env.example .env` → `DISCORD_WEBHOOK_URL` に貼付
4. GitHub: リポジトリ Settings → Secrets and variables → Actions → New secret
   - 名前: `DISCORD_WEBHOOK_URL`
   - 値: コピーしたURL
5. （任意）`INSIDER_BLACKLIST` Secret も設定（例: `7203.T,9984.T`）

### GitHub Actions の有効化

リポジトリに push すれば自動で動き始める:
- 朝（23:53 UTC = 8:53 JST）: 米国前日引けからシグナル生成 → 仮想買付 → Discord通知
- 引け（06:35 UTC = 15:35 JST）: 全ポジションクローズ → 日次サマリ → Discord通知
- DBは自動コミット

手動実行も可能（Actions タブ → 各ワークフロー → Run workflow）。

## ⚠️ 既知の課題

**バックテストが論文の数値を再現していない。**
- 論文 (PCA SUB Long-Short, 2010-2025): AR=23.79%, R/R=2.22, MDD=-9.58%
- 本実装の現在値: AR=-34%, R/R=-3.11, MDD=-89%

考えられる原因（要追加調査）:
- 取引タイミング（open-to-close vs close-to-close）の解釈
- yfinance のOpen価格データ品質
- 共通エクスポージャー V₀ の構成（特に v₃ シクリカル/ディフェンシブ符号）
- シグナル方向の符号

**現状でも、シグナル生成 → 仮想取引 → 通知のパイプラインは動く**ため、ペーパートレードを開始しつつデバッグを並行する方針。

## ドキュメント

- [調査レポート](docs/research.md) — 国内証券会社のAPI状況、ライブラリ、10万円戦略の整理
- [法律・税務調査](docs/legal-and-tax.md) — 金商法・SESC事例・確定申告・NISA・副業扱い等の深掘り
- [戦略文書](docs/strategy-pca-leadlag.md) — 日米リードラグPCA戦略の詳細（論文ベース）
- [設計書](docs/design.md) — システム設計、アーキテクチャ、フェーズ計画

## メモ

- 論文の実証：年率23.79% / R/R 2.22 / MDD -9.58%（2010-2025、ロングショート版）
- 10万円・信用なし制約に合わせて**ロングオンリー版**を本実装
- まずは1〜2ヶ月のペーパートレードで戦略の有効性を検証してから実弾に移行
