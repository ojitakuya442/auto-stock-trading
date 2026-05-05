# Auto Stock Trading（自動株取引Bot）

予算 **¥300,000** で日本株ETFを自動売買する個人プロジェクト。論文ベースの戦略をペーパートレードで検証中。

## 戦略

**日米業種リードラグ × 部分空間正則化PCA** ([中川ほか 2026 JSAI SIG-FIN 036](https://doi.org/10.11517/jsaisigtwo.2026.FIN-036_76))

- 米国 Select Sector SPDR 11銘柄の前日終値 → 日本 NEXT FUNDS TOPIX-17 ETF 17銘柄の翌日リターンを予測
- Long-Only top 3 を等ウェイトで保有（close-to-close: 当日引け買付 → 翌日引け決済）
- 取引コスト0（kabu Station API は1日100万円まで無料）

## バックテスト結果（2015-2026）

| 戦略 | 年率リターン | Sharpe | MDD |
|---|---|---|---|
| **本実装: PCA SUB Long-Only top3** | **+39.11%** | **2.05** | **-21.97%** |
| PCA SUB Long-Short（参考） | +50.21% | 3.04 | -12.68% |
| TOPIX-17 等ウェイト（ベンチマーク） | +9.16% | 0.51 | -31.91% |

論文値（2010-2025、ロングショート）: AR=23.79% / Sharpe=2.22 / MDD=-9.58%

> ロングショート版は信用取引が必要なため、現物のみ運用可能なロングオンリー版を採用。

## ポジションサイジング

| 項目 | 設定 |
|---|---|
| 予算 | ¥300,000 |
| 投資比率 | 80%（¥240,000 を株式、¥60,000 をバッファ） |
| 1銘柄上限 | ¥80,000（等ウェイト近似） |
| 売買単位 | 1口（1629.T のみ 10口） |
| 上限超の高額銘柄 | バッファを使って最低1口購入 |

## 自動運用（GitHub Actions）

| 時刻（JST） | 内容 |
|---|---|
| 平日 8:53 | シグナル生成 → 当日の取引予告を Discord 通知 |
| 平日 15:35 | 前日ポジション決済 → 新規ポジション建て → 日次サマリ通知 |

DBは `data/paper_trading.db` に SQLite で永続化し、Actions が自動コミット。

## フェーズ

- [x] Phase 0: データ取得・戦略実装・ペーパーブローカー・Discord通知・GitHub Actions
- [x] Phase 1: バックテスト最適化（close-to-close 採用）・ペーパートレード自動運用中
- [ ] Phase 2: kabu Station API 統合 + 少額実弾（¥30,000）※口座開設待ち
- [ ] Phase 3: フル実弾（¥300,000）

## セットアップ

```bash
uv sync --extra dev

# バックテスト
uv run python scripts/backtest.py

# 手動実行
uv run python scripts/morning_run.py
uv run python scripts/evening_run.py

# テスト
uv run pytest
```

### Discord 通知の設定

1. Discord でウェブフック URL を作成
2. ローカル: `cp .env.example .env` → `DISCORD_WEBHOOK_URL` に設定
3. GitHub: Settings → Secrets → `DISCORD_WEBHOOK_URL_AUTO_STOCK` に設定
4. （任意）インサイダー規制対象企業がある場合: `INSIDER_BLACKLIST=7203.T,9984.T` 形式で設定

## 技術スタック

- Python 3.12 + uv
- データ: yfinance（ヒストリカル）/ kabu Station API（Phase 2〜、リアルタイム）
- DB: SQLite
- 通知: Discord Webhook
- スケジューラ: GitHub Actions（Phase 1）→ Windows Task Scheduler（Phase 2〜）

## ドキュメント

- [調査レポート](docs/research.md)
- [法律・税務調査](docs/legal-and-tax.md)
- [戦略詳細](docs/strategy-pca-leadlag.md)
- [設計書](docs/design.md)