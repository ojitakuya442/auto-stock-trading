# 自動株取引システム 設計書

> [!NOTE]
> 本システムは **段階的開発** を前提とする。
> Phase 1: ペーパートレード（実売買なし） → Phase 2: 少額実弾（〜3万円） → Phase 3: フル実弾（10万円）
> 各Phase間に必ず1〜2週間の評価期間を置く。

詳細な調査は [research.md](research.md) を参照。

---

## 1. プロジェクト概要

| 項目 | 内容 |
|------|------|
| プロジェクト名 | auto-stock-trading |
| 目的 | 個人資産10万円を元手に、日本株のルールベース＋AIアシストによる自動売買を行う |
| 利用者 | 個人（1名） |
| 初期予算 | **10万円**（Phase 3で全額投入） |
| カテゴリ | 趣味 + 学習プロジェクト |
| 想定運用期間 | 半年〜1年（1年後にKPI評価） |

---

## 2. ゴールと非ゴール

### ゴール
- 自動売買の基盤を「**自分のコードで全部見える状態**」で構築する
- バックテスト → ペーパートレード → 実弾 のパイプラインを通す
- 1年後の成果を**ベンチマーク（TOPIX/S&P500）と比較**して評価可能にする
- 既存の `crypto-trading-bot` と**戦略エンジン・バックテスト基盤を共有**

### 非ゴール
- HFT・スキャルピング（10万円スケールでは現実的でない）
- 多銘柄ポートフォリオの本格運用（2〜5銘柄に絞る）
- 利益の最大化を最優先にすること（学習価値・透明性を優先）
- 他人への販売（金商法上の助言業登録が必要になる）

---

## 3. 技術選定

> **方針更新**: ユーザーは三菱UFJ eスマート証券（旧auカブコム）口座をこれから開設するため、メインAPIを **kabu Station API** に変更。

| レイヤー | 選定 | 理由 |
|---|---|---|
| **証券会社/API** | **kabu Station API**（三菱UFJ eスマート証券） | 国内唯一のREST API、プチ株対応、NISA成長投資枠対応 |
| **サブ候補** | 立花証券e支店 API | 完全無料、将来的に併用 or 切替候補 |
| **言語** | Python 3.12 + uv | 既存プロジェクトと統一、ライブラリ豊富 |
| **HTTP/WS** | httpx + websockets | API直叩き |
| **バックテスト** | Backtesting.py | 軽量・可視化◎・学習目的に合う |
| **データ蓄積** | SQLite | ローカル完結、運用シンプル |
| **DataFrame** | pandas + polars（必要に応じて） | 標準 |
| **スケジューラ** | APScheduler（メイン）+ GitHub Actions（軽量タスク） | 場中監視はローカル常駐、夜間バッチはGHA |
| **ロギング** | loguru + JSON ログ | 後で集計・可視化しやすい |
| **可視化** | Streamlit | サクッとダッシュボード化 |
| **通知** | Discord Webhook | 既存 `discord-claude-bot` 資産を流用 |
| **テスト** | pytest | 標準 |
| **シークレット管理** | .env + direnv | コミット禁止、`.gitignore` 厳守 |

---

## 4. アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                     Scheduler (APScheduler)             │
│  ・場中: 5分ごとにシグナル評価   ・夜間: バッチ処理     │
└──────────┬──────────────────────────────────────────────┘
           │
   ┌───────┴───────┐
   ▼               ▼
┌────────────┐  ┌────────────┐
│  Market    │  │  Strategy  │
│  Data      │──▶  Engine    │
│  Fetcher   │  │ (rules+AI) │
└─────┬──────┘  └─────┬──────┘
      │               │
      ▼               ▼
┌────────────┐  ┌────────────┐    ┌──────────┐
│  SQLite    │  │  Order     │───▶│ Broker   │
│  (ticks/   │◀─│  Manager   │    │ Adapter  │
│  trades)   │  │            │    │ (e支店/  │
└─────┬──────┘  └─────┬──────┘    │  kabu)   │
      │               │           └────┬─────┘
      ▼               ▼                │
┌────────────┐  ┌────────────┐         │
│  Streamlit │  │  Discord   │◀────────┘
│  Dashboard │  │  Notifier  │   (約定/エラー通知)
└────────────┘  └────────────┘
```

### コンポーネント責務

| コンポーネント | 責務 |
|---|---|
| **Scheduler** | 取引時間（9:00-11:30 / 12:30-15:00）に合わせたジョブ起動 |
| **Market Data Fetcher** | 現物株の板/気配/約定データを取得しSQLiteへ |
| **Strategy Engine** | テクニカル指標計算 → シグナル生成。Phase別にロジック差し替え |
| **Order Manager** | ポジション管理、リスク管理（上限/ストップロス）、発注の最終ゲート |
| **Broker Adapter** | API差異を吸収するインターフェース（e支店/kabu/Mock を切替） |
| **Notifier** | 約定・エラー・日次サマリをDiscordへ |
| **Dashboard** | PnL、ポジション、シグナル履歴の可視化 |

---

## 5. ディレクトリ構成（予定）

```
auto-stock-trading/
├── README.md
├── pyproject.toml              # uv管理
├── .env.example                # APIキー類のテンプレート
├── .gitignore
├── docs/
│   ├── research.md             # 調査レポート
│   ├── design.md               # 本ファイル
│   └── runbook.md              # 運用手順（Phase 2以降で作成）
├── src/
│   └── auto_stock_trading/
│       ├── __init__.py
│       ├── config.py           # 設定読み込み
│       ├── brokers/            # Broker Adapter
│       │   ├── base.py         # 抽象IF
│       │   ├── eshiten.py      # 立花証券e支店
│       │   ├── kabustation.py  # kabuステーション
│       │   └── mock.py         # ペーパートレード用
│       ├── data/               # Market Data Fetcher
│       ├── strategies/         # 戦略
│       │   ├── base.py
│       │   ├── etf_rotation.py
│       │   └── sma_crossover.py
│       ├── engine/             # Strategy Engine 本体
│       ├── orders/             # Order Manager
│       ├── risk/               # リスク管理
│       ├── notify/             # Discord通知
│       └── dashboard/          # Streamlit
├── scripts/
│   ├── backtest.py
│   ├── paper_trade.py
│   └── live_trade.py
├── tests/
└── data/                       # SQLite等（gitignore）
    └── trades.db
```

---

## 6. 戦略設計

### メイン戦略: 日米業種リードラグ × 部分空間正則化PCA

> 詳細は [strategy-pca-leadlag.md](strategy-pca-leadlag.md) を参照。

- **出典**: 中川慧ほか（2026）JSAI SIG-FIN 036 査読論文
- **対象**: 米国 Select Sector SPDR ETF（11銘柄）→ 日本 NEXT FUNDS TOPIX-17 ETF（17銘柄）
- **論文実証結果**: 年率リターン 23.79%、R/R 2.22、MDD -9.58%（2010-2025、ロングショート）
- **本プロジェクトでの採用**: **ロングオンリー版**（10万円・信用なしの制約に合わせる）
- **取引頻度**: 日次1回（寄付発注 → 引けクローズ）

### サブ戦略（ベンチマーク用）

| 戦略 | 役割 |
|---|---|
| **MOM**（単純モメンタム） | 論文ベースラインの再現、戦略の優位性確認 |
| **TOPIX 1306 バイ&ホールド** | 市場全体に対するアウトパフォーマンス測定 |

### 将来拡張候補

- 論文 [18]（前エクスポージャー情報付き正則化PCA、FIN-035）の実装
- 欧州ETFを加えた3市場版
- LLM（Claude）によるニュースセンチメントフィルタ追加

---

## 7. リスク管理（最重要）

> 法的根拠とNGライン詳細は [legal-and-tax.md §A-2 / §E-2](legal-and-tax.md) を参照。

### 7.1 資金リスク管理

| 項目 | ルール |
|---|---|
| **1注文あたりの最大金額** | 総資産の30%まで（10万円なら3万円）|
| **同時保有銘柄数** | 最大3銘柄 |
| **1日あたりの最大取引回数** | 5回（過剰取引防止）|
| **ストップロス** | 含み損 -5% で自動損切り |
| **テイクプロフィット** | 含み益 +10% で半分利確 |
| **エマージェンシーストップ** | 1日の損失が総資産の -3% に達したら**当日全停止** |
| **キルスイッチ** | `data/EMERGENCY_STOP` ファイル存在で全発注停止 |
| **発注前ガード** | 直近30秒以内に同銘柄の注文が3回以上 = 異常で停止 |
| **注文タイプ制限** | Phase 1-2 は成行 + 指値のみ。逆指値は Phase 3 から |

### 7.2 法令遵守ガード（コード実装必須）

過去に**個人BOTで実際に課徴金処分事例あり**（2008年 159万円、2024年 オカムラ食品工業株 引け値関与）。
以下を Order Manager に**ハードコードのガード**として実装する。

| ガード | 実装 | 対応する金商法上の論点 |
|---|---|---|
| **見せ玉防止 (1)** | 注文後**60秒以内のキャンセル禁止**（ロジックレベルで遮断） | 159条2項1号 変動操作 |
| **見せ玉防止 (2)** | 1日のキャンセル率が**40%超**になったら自動停止 | 同上 |
| **仮装売買防止** | 同一銘柄に売り注文と買い注文を**同時に保持しない** | 159条1項 仮装売買 |
| **終値関与防止** | **14:55以降の新規発注を全面禁止**（取消/利確のみ可） | 終値関与・引け値操作 |
| **月末・四半期末の特別ガード** | 月末・四半期末は**14:30以降に新規発注禁止** | 特に監視が厳しい時期 |
| **板厚への配慮** | 注文サイズが**板の最良気配数量の20%超**ならワーニング、50%超なら拒否 | 変動操作の予防 |
| **インサイダー予防** | 所属企業・関連企業の銘柄は**設定で完全ブラックリスト化** | 166条 インサイダー取引 |
| **発注頻度上限** | 同一銘柄に対して**1分間に5注文まで**、**1秒に1注文まで** | 高頻度取引・規約違反予防 |
| **取引履歴保管** | 全注文の発注理由・シグナル根拠を JSON ログに保存、**最低1年保管** | 万一の調査対応 |

### 7.3 やってはいけないこと（レッドフラグ）

[legal-and-tax.md §E-2](legal-and-tax.md) より:

1. ❌ 約定意思のない注文を出して即キャンセル
2. ❌ 同一銘柄に売り注文・買い注文を同時に並べる
3. ❌ 引け前5分の意図的な大口発注
4. ❌ 他人にシグナル配信・BOT販売・運用代行（金商法登録必要）
5. ❌ 勤務先関連企業の銘柄を扱う
6. ❌ 雑所得（FX/暗号資産）と株式の損益計算を混ぜる

---

## 8. データモデル（SQLite）

```sql
-- 価格スナップショット（5分足/日足）
CREATE TABLE prices (
    symbol      TEXT NOT NULL,
    timestamp   INTEGER NOT NULL,    -- UNIX秒
    open        REAL, high REAL, low REAL, close REAL,
    volume      INTEGER,
    PRIMARY KEY (symbol, timestamp)
);

-- 自分が出した注文
CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    side            TEXT CHECK(side IN ('BUY','SELL')),
    order_type      TEXT,            -- MARKET/LIMIT
    qty             INTEGER,
    price           REAL,
    status          TEXT,            -- PENDING/FILLED/CANCELLED/REJECTED
    broker_order_id TEXT,
    strategy_name   TEXT,
    submitted_at    INTEGER,
    filled_at       INTEGER,
    fill_price      REAL,
    note            TEXT
);

-- 約定履歴
CREATE TABLE trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER REFERENCES orders(id),
    symbol      TEXT,
    side        TEXT,
    qty         INTEGER,
    price       REAL,
    fee         REAL,
    executed_at INTEGER
);

-- 戦略が出したシグナル（実発注しない場合も記録）
CREATE TABLE signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT,
    symbol        TEXT,
    signal_type   TEXT,             -- BUY/SELL/HOLD
    confidence    REAL,
    features      TEXT,             -- JSON
    created_at    INTEGER,
    acted         INTEGER DEFAULT 0  -- 0/1
);

-- ポジション（日次スナップショット）
CREATE TABLE positions (
    snapshot_at INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    qty         INTEGER,
    avg_cost    REAL,
    market_price REAL,
    unrealized_pnl REAL,
    PRIMARY KEY (snapshot_at, symbol)
);
```

---

## 9. Broker Adapter の抽象IF

```python
# brokers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

Side = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]

@dataclass
class Order:
    symbol: str
    side: Side
    qty: int
    order_type: OrderType
    limit_price: float | None = None

@dataclass
class OrderResult:
    broker_order_id: str
    status: str
    submitted_at: int

@dataclass
class Position:
    symbol: str
    qty: int
    avg_cost: float

class BrokerAdapter(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> dict: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def submit_order(self, order: Order) -> OrderResult: ...

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool: ...

    @abstractmethod
    def get_balance(self) -> float: ...
```

これで `eshiten.py` / `kabustation.py` / `mock.py` を差し替え可能にする。
**Phase 1 はすべて `mock.py`** で動かす。

---

## 10. フェーズ計画とKPI

### Phase 0: 環境構築 + 口座開設（並行・2週間）
**並列で進める**:
- [ ] **三菱UFJ eスマート証券（旧auカブコム）口座開設**（オンライン申込→1〜2週間）
- [ ] **口座種別「特定口座（源泉徴収あり）」を選択**（副業バレ対策で住民税は普通徴収）
- [ ] uv プロジェクト初期化、ディレクトリ作成
- [ ] yfinance / stooq から日米ETFのヒストリカル取得
- [ ] SQLiteスキーマ作成、Discord Webhook疎通
- [ ] **インサイダー対象銘柄リストの定義**（勤務先・関連企業）

### Phase 1.1: 論文戦略の再現バックテスト（2週間）
- [ ] [strategy-pca-leadlag.md](strategy-pca-leadlag.md) §3 の手法を Python 実装
- [ ] 米国11ETF（XLB等）+ 日本17ETF（1617.T〜1633.T）のロングショート版で論文 R/R 2.22 を再現
- [ ] **ロングオンリー版**（10万円対応）にアダプト、性能評価
- [ ] ベースライン（MOM・PCA PLAIN・TOPIXバイ&ホールド）と比較

**KPI**:
- ロングショート版で R/R > 1.5（論文の70%再現率）
- ロングオンリー版で年率リターン > 10%、シャープ > 0.8
- 取引コスト（往復0.2%）込みでも黒字

### Phase 1.2: アウトオブサンプル + ペーパートレード（4週間）
- [ ] kabuステーション API のクライアント開発、口座入金後にAPI接続確認
- [ ] Mock Broker と kabu Adapter を切替可能に実装
- [ ] 2024-2025 を walk-forward で検証
- [ ] ペーパートレードで1ヶ月運用、約定シミュレーション
- [ ] 発注フローを Discord 通知込みで完全自動化

**KPI**:
- 1ヶ月ペーパートレードで重大バグ・リスク管理発動の異常なし
- 発注タイミングが寄付前後5分以内に確実に実行

### Phase 2: 少額実弾（4週間、3万円）
- [ ] **3万円を投入**、ロングオンリー版で上位3-5銘柄を運用
- [ ] 約定通知、日次サマリ通知
- [ ] 1日の損失 -3% でキルスイッチ発動を確認

**KPI**:
- 4週間でシステム障害ゼロ
- リスク管理ルールが意図通り発動
- 損失は -10% 以内（学習コストとして許容）

### Phase 3: フル実弾（半年、10万円）
- [ ] 残額追加で計10万円
- [ ] 戦略追加検討（DOUBLE版、論文 [18] 手法、LLM フィルタ）
- [ ] Streamlit ダッシュボード仕上げ

**KPI**:
- 半年で **TOPIX に対するアウトパフォーム**
- 最大ドローダウン < -15%
- 自動売買だけで日々の運用判断が完結する状態

---

## 11. オペレーション

### 日次フロー（場中）
1. 8:50 — システム起動、前日残高/ポジションを照合
2. 9:00-11:30 — 5分ごとにシグナル評価、必要なら発注
3. 12:30-14:55 — 同上
4. 14:55-15:00 — 新規注文停止（終値関与防止）
5. 15:30 — 日次サマリをDiscord通知、SQLiteへスナップショット保存

### 週次フロー
- 土曜：バックテストの再実行、戦略パラメータの見直し検討
- 日曜：1週間のPnLレビュー、ブログ/ノートにメモ

### 月次フロー
- 月初：ETF ローテーション判定 + 全体レビュー
- パフォーマンス vs ベンチマークを記録

---

## 12. セキュリティ・コンプライアンス

> 法律・税務の詳細は [legal-and-tax.md](legal-and-tax.md) を参照。

### 12.1 セキュリティ

| 項目 | 対応 |
|---|---|
| **APIキー** | `.env`、git管理外。`.env.example` のみコミット |
| **本番/ペーパー切替** | `MODE=paper\|live` 環境変数。デフォルトは `paper` |
| **2要素認証** | 証券会社側で必ず有効化 |
| **発注ガード** | `MODE=live` への切替は明示的なフラグ + 確認プロンプト |
| **ログ** | 全注文を JSON ログで保存、**最低1年保管**（税務・トラブルシュート・調査対応用）|

### 12.2 税務（特定口座+源泉徴収あり が標準）

| 項目 | 対応 |
|---|---|
| **口座種別** | **特定口座（源泉徴収あり）**を利用 — 確定申告原則不要 |
| **損失時の対応** | 損失が出た年は**確定申告で損失繰越（3年）**を申請 |
| **配当との通算** | 損失年は配当を**申告分離課税**で申告して通算 |
| **副業バレ対策** | 確定申告するなら住民税を「**普通徴収**」に切替 |
| **NISA併用** | NISA口座はBOTと相性悪い。**特定口座のみ**で運用 |
| **海外証券** | Phase 4以降にAlpaca等を使うなら、一般口座扱い + 外国税額控除に注意 |
| **経費計上** | 上場株式譲渡所得は**取得費・手数料のみ経費可**。PC/サーバー代は不可 |

### 12.3 法令遵守

| 項目 | 対応 |
|---|---|
| **登録義務** | 自己資金・自己口座のみで運用 → 金商法上の登録不要を維持 |
| **シグナル配信禁止** | BOTのシグナル/ロジックを**他人に提供しない**（投資助言業に該当）|
| **コード公開** | GitHubでのコード公開はOK（具体的な売買助言を伴わない限り）|
| **不公正取引防止** | §7.2 のガードを Order Manager に実装 |
| **インサイダー予防** | 勤務先・関連企業の銘柄をブラックリスト化 |
| **過去事例参照** | [SESC 課徴金事例集](https://www.fsa.go.jp/sesc/jirei/index.html) を年1回チェック |

---

## 13. オープン課題・要検討事項

- [ ] **三菱UFJ eスマート証券 口座開設**（オンライン申込、1〜2週間）→ 並行で着手中
- [ ] **インサイダー対象銘柄リスト**を決める（勤務先・関連企業）
- [ ] **論文 [18]**（前エクスポージャー情報付き正則化PCA, FIN-035）も実装比較するか
- [ ] **Map氏の8-mon.com記事**: kabu API ペーパートレードの実装ノウハウ取得（記事URL未確認、要追加調査 or ユーザーから共有）
- [ ] **ベンチマーク選定**: TOPIX vs TOPIX-17 平均 vs 配当込みTOPIX
- [ ] **クラウド移行**: Phase 3 でAWS Lightsail等に移すか、ローカルPC常駐のままか

---

## 14. 次のアクション（決定済み方針に基づく）

1. **三菱UFJ eスマート証券 口座開設**（並行着手）
2. **Phase 0: 環境構築**: uv プロジェクト初期化、ディレクトリ作成、yfinance データ取得
3. **Phase 1.1 着手**: 論文 PCA SUB 戦略のバックテスト実装（[strategy-pca-leadlag.md](strategy-pca-leadlag.md) 参照）

低関与進行モードのため、Claude Code 主導で 1, 2 を並列で進め、進捗を Discord 等で共有する想定。
