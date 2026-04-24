# 自動株取引 調査レポート

**対象**: 個人投資家、予算10万円スタート / **時点**: 2026年4月

---

## TL;DR（要約）

- **API付き証券会社の最有力2択**:
  - **立花証券e支店 API**（完全無料・公式・本格的な日本株自動売買が可能）
  - **kabuステーション API**（三菱UFJ eスマート証券、条件達成で無料）
- **10万円という予算ではデイトレ・HFT・信用取引はほぼ不可**。現実解は以下のいずれか:
  1. **ETF低頻度ローテーション**（kabuステーション or 立花e支店）
  2. **単元未満株（S株/プチ株）で値嵩株を1株ずつ自動買付**
  3. **仮想通貨BOTで経験値を稼いでから株に移行**（既存 crypto-trading-bot と統合可）
  4. **米国株fractional（Alpaca）で1ドル単位の自動売買**
- **個人の自動売買は合法**。ただし「見せ玉」「相場操縦」は厳禁。税務は特定口座（源泉徴収あり）で簡素化可。
- **第一歩はペーパートレード**。10万円を即投入せず、1〜2ヶ月の検証フェーズを置く。

---

## 1. 日本の証券会社 API 対応状況

### 1.1 比較表（2026年4月時点）

| 証券会社 | 公式API | 種別 | 料金 | 株式売買手数料 | 自動売買難易度 |
|---|---|---|---|---|---|
| **三菱UFJ eスマート証券**（旧auカブコム） | ✅ kabuステーションAPI | REST + WebSocket(PUSH) | 条件達成で無料 | 1日100万円まで0円 | ★ 最も現実的 |
| **立花証券e支店** | ✅ 公式API | HTTPS POST + WebSocket | **完全無料** | 約定毎/定額制 | ★★ 個人向け唯一の無料公式API |
| **SBIネオトレード証券** | ✅ ネオトレAPI for Excel | Excelアドイン専用 | 無料 | 1日100万円まで0円 | ★★ Excel/VBA前提 |
| **楽天証券** | △ MARKETSPEED II RSS | Excel RSS関数 + 発注 | 無料 | ゼロコース選択で0円 | ★★ Windows + Excel必須 |
| **SBI証券** | ❌ 非公式（HyperSBI2） | ローカルHTTP | 無料 | ゼロ革命で0円 | ★★★ 規約注意 |
| **マネックス証券** | △ 残高参照のみ | OpenAPI | — | 1日100万円まで0円 | × 個人発注API無し |
| **松井証券** | △ FXのみ | REST | — | 1日50万円まで0円 | × 株式は不可 |
| **PayPay証券** | ❌ | — | — | スプレッド方式 | × |

### 1.2 詳細

#### kabuステーション API（三菱UFJ eスマート証券）
- **方式**: ローカルPCで動く `kabuステーション` クライアントが localhost に REST + WebSocket(PUSH) を立てる
- **料金**: kabuステーション Professional プラン以上で無料（2024年6月から条件大幅緩和）
- **対応**: 国内株（現物・信用）、先物・オプション、NISA成長投資枠
- **レート制限**: 注文 5req/秒、情報系 10req/秒
- **板情報**: 売買各10本まで
- **公式**: https://kabucom.github.io/kabusapi/reference/index.html
- **Python**: https://github.com/kabucom/kabusapi / https://github.com/shirasublue/python-kabusapi

#### 立花証券e支店 API
- **料金**: **完全無料**（口座だけあれば追加費用ゼロ）
- **方式**: HTTPS POST(REQUEST I/F) + WebSocket(EVENT I/F)
- **対応**: 国内株（現物・信用）。先物・米国株は非対応
- **データ**: リアルタイム株価、板情報、20年分の日足ヒストリカル
- **2025年の動き**: 7/26 電話番号認証導入、11/4 v4r7 廃止 → v4r8 へ移行
- **公式**: https://www.e-shiten.jp/api/
- **GitHub**: https://github.com/e-shiten-jp

#### 楽天証券 MARKETSPEED II RSS
- 環境制約が厳しい：**Windows + Excel 必須**
- NISA口座でのアルゴ注文は不可
- 一部指数で10〜20分ラグあり

#### SBIネオトレード「ネオトレAPI for Excel」
- 2024年3月リリース、無料
- Excelアドインのみ。VBAでアルゴを書く前提

---

## 2. ライブラリ・フレームワーク

### 国内証券API用
- **kabucom/kabusapi** — kabuステーション 公式 Python サンプル
- **shirasublue/python-kabusapi** — Python 非公式ラッパ
- **e-shiten-jp** — 立花証券e支店 公式 GitHub サンプル

### バックテスト
| ライブラリ | 強み | 弱み |
|---|---|---|
| **Backtesting.py** | 軽量、可視化◎ | 単一銘柄向き |
| **Backtrader** | 多銘柄、ポートフォリオ系 | 学習コスト高め |
| **vectorbt** | NumPy/pandas で爆速 | PRO版は有料 |
| **Zipline (Reloaded)** | 米国流の本格設計 | 日本株データ準備が手間 |

### 仮想通貨・汎用
- **pybotters**（日本発・国内BOTterの事実上の標準）
- **ccxt**（海外取引所統合）

### 海外プラットフォーム
- **Alpaca** — 米国株 fractional shares ($1〜)、手数料無料、Paper Trading完備、2026年1月から日本で米国株24時間取引API
- **IBKR** — `ib_insync` で本格的、50か国18市場
- **QuantConnect / LEAN** — オープンソース、商用利用可

---

## 3. 10万円スタートでの現実

### 大前提：日本株は100株単位
- 例：トヨタ3,000円 = 1単元30万円必要 → 10万円では多くの銘柄が買えない
- 東証は2025年に「**最低投資金額10万円程度**に」と全上場企業へ要請（移行途上）

### できること
1. **単元未満株（S株/プチ株/かぶミニ/ワン株）で複数銘柄に分散**（1株〜）
2. **国内ETF**（1306 TOPIX 約3,000円台、1321 日経225 約4万円台 等）
3. **米国株 fractional**（Alpaca/Woodstock）で$1〜
4. **国内仮想通貨BOT**（bitFlyer/bitbank/GMO）で数百円〜
5. **ペーパートレード・バックテストでの戦略検証**

### 現実的に厳しい
- デイトレ・スキャルピング（手数料・スプレッド負け）
- 信用取引（最低保証金30万円）
- HFT
- 多銘柄分散の本格運用

### 単元未満株サービス比較

| 証券会社 | サービス | 買付手数料 | 売却手数料 | スプレッド | 約定タイミング | API連携 |
|---|---|---|---|---|---|---|
| **SBI証券** | S株 | 0円 | 0円 | なし | 1日3回 | ❌ |
| **楽天証券** | かぶミニ | 0円（寄付） | 0円（寄付） | リアルタイム時 0.22% | 寄付/リアルタイム | △ |
| **マネックス** | ワン株 | 0円 | 0.55%（最低52円） | なし | 後場始値 | ❌ |
| **三菱UFJ eスマート** | プチ株 | 0.55%（最低52円） | 同左 | なし | 寄前/前場引/後場引 | ✅ kabuAPI |

→ **コスト最強は SBI S株**だがAPI連携不可。**自動化前提なら kabuステーション（プチ株）か 立花e支店（単元100株）**。

---

## 4. 法律・規制・税務

> 詳細は [legal-and-tax.md](legal-and-tax.md) を参照。ここでは要点のみ。

### 自動売買の合法性
- 個人が**自分の資金・自分の口座**で自動売買する分には**金商法上の登録不要**
- 他人へのシグナル配信・BOT販売・運用代行をすると**投資助言業/投資運用業の登録が必要**
- 不公正取引（**仮装売買・見せ玉・引け値関与・相場操縦・インサイダー**）は厳禁。**個人BOTでも課徴金事例あり**（2008年 159万円、2024-2025年 引け値関与）
- HFT規制は通常の自宅PC・通常API利用なら対象外

### 税務
- 上場株式譲渡益・配当 = **20.315%**（所得税15% + 復興0.315% + 住民5%）
- **特定口座（源泉徴収あり）** が標準。確定申告原則不要、損失繰越したい年だけ申告
- 損益通算・3年繰越控除あり（要申告）
- **BOT運用は事業所得認定されない**判例多数 → PC代/サーバー代/書籍代等は譲渡所得の経費にできない
- 暗号資産は**雑所得（最大55%）**で扱いが異なる。株式と損益通算不可
- NISAはBOT（短期売買）と相性悪い（損益通算不可・回転売買で枠消費）→ 10万円規模ならまず特定口座
- 副業禁止のサラリーマンでも**株式投資は通説で副業に該当しない**。バレ対策は住民税の普通徴収切替

---

## 5. 海外オプション

### 米国株
- **Alpaca**: API完備、fractional、手数料無料、Paper Trading環境あり
- **IBKR**: 多市場対応、`ib_insync` で本格運用

### 国内仮想通貨

| 取引所 | 特徴 |
|---|---|
| **bitFlyer Lightning** | 流動性高い、IFD/OCO |
| **bitbank** | 40通貨APIフル対応、メイカー -0.02% リベート |
| **GMOコイン** | 取引所板取引のメイカー -0.01〜0.03% |

→ 24/365 稼働、無料公式API、最低取引額が小さい → **学習用途には圧倒的有利**

---

## 6. 2025〜2026年の最新トピック

- **新NISA × 自動売買**:
  - kabuステーションAPI: NISA成長投資枠は対応、つみたて枠は不可
  - 楽天 MARKETSPEED II RSS: NISA口座でのアルゴ注文は**不可**
  - 現実解は「成長投資枠での個別株/ETFローテーション」
- **LLM/AI活用**:
  - ChatGPT/Claude に戦略を伝えて Python コード生成 → Backtesting.py で検証 が定着
  - 「ニュース取得 → センチメント解析 → 売買判断 → 発注」のエージェント化
  - **重要**: LLMが直接証券口座にログインして発注する公式機能は存在しない。実発注は自前プログラム経由
- **国内サービス動向**:
  - 三菱UFJ eスマート証券（旧auカブコム）社名変更後も kabuAPI は継続強化
  - SBIネオトレード「ネオトレAPI for Excel」（2024年3月）登場
  - Alpaca が2026年1月、日本で**米国株24時間取引API**を業界初実装

---

## 7. 技術選定クイックガイド

| 目的 | 推奨スタック |
|---|---|
| 本格的に日本株自動売買、月額数万OK | kabuステーション API + Python (`python-kabusapi`) + Backtesting.py |
| **完全無料で日本株自動売買** | **立花証券e支店 API + Python + 自前実装** |
| Excelで非エンジニアも巻き込む | SBIネオトレード「ネオトレAPI for Excel」 or 楽天 MARKETSPEED II RSS |
| 10万円で学習＋実弾少額 | bitbank API + pybotters → 慣れたら立花e支店APIで日本株 |
| 米国株fractional 自動売買 | Alpaca API + Python (`alpaca-py`) |
| マルチアセット本格 | IBKR + `ib_insync` |

---

## 8. このプロジェクトでの選定（推奨）

| 観点 | 結論 |
|---|---|
| **メインAPI** | **立花証券e支店 API**（完全無料・公式） |
| **サブ候補** | kabuステーション API（NISA成長投資枠を使うなら） |
| **言語** | Python 3.12 + uv |
| **バックテスト** | Backtesting.py |
| **戦略の出発点** | ETF（1306, 1321, 1655 など）の月次〜週次ローテーション |
| **実弾前の検証** | ペーパートレード 1〜2ヶ月 |
| **将来統合** | 既存 `crypto-trading-bot` とコア部分（戦略エンジン・バックテスト基盤）を共有 |

---

## 9. 主要参考URL

- [kabuステーション API 公式](https://kabu.com/item/kabustation_api/default.html)
- [kabuステーション APIリファレンス](https://kabucom.github.io/kabusapi/reference/index.html)
- [立花証券e支店 API 公式](https://www.e-shiten.jp/api/)
- [楽天 MARKETSPEED II RSS](https://marketspeed.jp/ms2_rss/)
- [SBIネオトレード ネオトレAPI for Excel](https://www.sbineotrade.jp/tool/api/)
- [Alpaca Broker API 日本](https://alpaca.markets/jp/broker-api.html)
- [pybotters](https://pybotters.readthedocs.io/ja/stable/)
- [日本取引所グループ：相場操縦規制](https://www.jpx.co.jp/regulation/preventing/manipulation/index.html)
- [国税庁：上場株式の譲渡所得 申告特集](https://www.nta.go.jp/taxes/shiraberu/shinkoku/tokushu/keisubetsu/kabu-haitou-shinkoku.htm)
- [立花証券e支店とKabuステーションどちらで自動売買すべきか（Zenn）](https://zenn.dev/morim34/articles/955e7a6a18fe52)
