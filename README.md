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
- [x] **Phase 1.1**: バックテスト実装 + 取引タイミング最適化（close-to-close へ移行）
- [x] **Phase 1.2**: ペーパートレード自動運用（朝予告通知 + 引け売買 + 日次サマリ）
- [ ] 三菱UFJ eスマート証券 口座開設（あなた側、申込済み・開設待ち）
- [ ] Phase 2: kabu Station API 統合 + 少額実弾（3万円）
- [ ] Phase 3: フル実弾（10万円）

## バックテスト結果（2015-2026）

| 戦略 | 年率リターン | リスク | Sharpe | MDD |
|---|---|---|---|---|
| **PCA SUB Long-Only (top 3, 本実装メイン)** | **+39.11%** | 19.06% | **+2.05** | **-21.97%** |
| PCA SUB Long-Short | +50.21% | 16.51% | +3.04 | -12.68% |
| MOM Long-Short (baseline) | -20.79% | 14.96% | -1.39 | -90.94% |
| TOPIX-17 equal-weight (benchmark) | +9.16% | 18.01% | +0.51 | -31.91% |

- 取引コスト: 0%（kabu Station API は1日100万円まで無料）
- ロングショート版は信用取引が必要（10万円・現物のみでは不可）
- **本実装はロングオンリー (top 3) を採用** — 現物のみで運用可能、ベンチマーク比 シャープ 4倍

論文 (open-to-close, 2010-2025, 取引コスト不明): PCA SUB AR=23.79% R/R=2.22 MDD=-9.58%

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
   - 名前: `DISCORD_WEBHOOK_URL_AUTO_STOCK`
   - 値: コピーしたURL
5. （任意）`INSIDER_BLACKLIST` Secret も設定（例: `7203.T,9984.T`）— 勤務先や関連企業がある場合のみ。学生・該当なしならスキップ可

### GitHub Actions の有効化

リポジトリに push すれば自動で動き始める:
- **朝 8:53 JST**: シグナル生成 → 「今日の取引予告」を Discord 通知（実取引なし）
- **引け 15:35 JST**: 前日ポジション決済 → 当日新規ポジション建て → 日次サマリを Discord 通知
- DBは自動コミット

手動実行も可能（Actions タブ → 各ワークフロー → Run workflow）。

## 戦略の取引タイミング

- **シグナル生成**: 米国前日終値から日米共通因子を抽出 → 翌日（=本日）日本ETFリターン予測
- **取引**: 本日引けで新規買付 → 翌日引けで決済 (close-to-close)
- 論文は open-to-close を提案しているが、本実装では実証的に close-to-close の方が有意に優れていることを確認 ([backtest結果](#バックテスト結果2015-2026)参照)

## ドキュメント

- [調査レポート](docs/research.md) — 国内証券会社のAPI状況、ライブラリ、10万円戦略の整理
- [法律・税務調査](docs/legal-and-tax.md) — 金商法・SESC事例・確定申告・NISA・副業扱い等の深掘り
- [戦略文書](docs/strategy-pca-leadlag.md) — 日米リードラグPCA戦略の詳細（論文ベース）
- [設計書](docs/design.md) — システム設計、アーキテクチャ、フェーズ計画

## メモ

- 論文の実証：年率23.79% / R/R 2.22 / MDD -9.58%（2010-2025、ロングショート版）
- 10万円・信用なし制約に合わせて**ロングオンリー版**を本実装
- まずは1〜2ヶ月のペーパートレードで戦略の有効性を検証してから実弾に移行
