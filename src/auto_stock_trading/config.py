"""設定値とユニバース定義"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

PAPER_DB_PATH = DATA_DIR / "paper_trading.db"

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
MODE = os.getenv("MODE", "paper")
PAPER_INITIAL_CAPITAL = float(os.getenv("PAPER_INITIAL_CAPITAL", "300000"))
INVEST_RATIO = float(os.getenv("INVEST_RATIO", "0.80"))  # 投資比率: 総資産の80%を株に配分

# 米国 Select Sector SPDR ETF（11銘柄）
US_TICKERS: list[str] = [
    "XLB",  # Materials
    "XLC",  # Communication Services
    "XLE",  # Energy
    "XLF",  # Financials
    "XLI",  # Industrials
    "XLK",  # Information Technology
    "XLP",  # Consumer Staples
    "XLRE",  # Real Estate
    "XLU",  # Utilities
    "XLV",  # Health Care
    "XLY",  # Consumer Discretionary
]

# 日本 NEXT FUNDS TOPIX-17 業種別 ETF（17銘柄）
JP_TICKERS: list[str] = [
    "1617.T",  # 食品
    "1618.T",  # エネルギー資源
    "1619.T",  # 建設・資材
    "1620.T",  # 素材・化学
    "1621.T",  # 医薬品
    "1622.T",  # 自動車・輸送機
    "1623.T",  # 鉄鋼・非鉄
    "1624.T",  # 機械
    "1625.T",  # 電機・精密
    "1626.T",  # 情報通信・サービスその他
    "1627.T",  # 電力・ガス
    "1628.T",  # 運輸・物流
    "1629.T",  # 商社・卸売
    "1630.T",  # 小売
    "1631.T",  # 銀行
    "1632.T",  # 金融（除く銀行）
    "1633.T",  # 不動産
]

# 表示用: 銘柄コード → (セクター名, 主な構成銘柄リスト)
# Discord 通知などで「ETFが何を含んでいるか」を分かりやすく表示するために使用
TICKER_INFO: dict[str, tuple[str, str]] = {
    # 日本: NEXT FUNDS TOPIX-17 業種別 ETF (発行: 野村アセット)
    "1617.T": ("食品", "味の素 / キリンHD / アサヒ / サントリーBF / 明治HD"),
    "1618.T": ("エネルギー資源", "INPEX / ENEOS / 出光興産"),
    "1619.T": ("建設・資材", "大成建設 / 清水建設 / 住友大阪セメント"),
    "1620.T": ("素材・化学", "信越化学 / 三井化学 / 富士フイルム"),
    "1621.T": ("医薬品", "武田薬品 / 第一三共 / 中外製薬 / エーザイ"),
    "1622.T": ("自動車・輸送機", "トヨタ / ホンダ / デンソー / SUBARU"),
    "1623.T": ("鉄鋼・非鉄", "日本製鉄 / JFE / 住友金属鉱山"),
    "1624.T": ("機械", "ファナック / SMC / ダイキン / コマツ"),
    "1625.T": ("電機・精密", "ソニーG / キーエンス / 村田製作所 / TDK"),
    "1626.T": ("情報通信・サービス", "NTT / ソフトバンクG / KDDI / リクルート"),
    "1627.T": ("電力・ガス", "東京電力 / 関西電力 / 東京ガス"),
    "1628.T": ("運輸・物流", "JR東日本 / ANA / JAL / 日本郵船"),
    "1629.T": ("商社・卸売", "三菱商事 / 伊藤忠 / 三井物産 / 丸紅"),
    "1630.T": ("小売", "ファストリ / セブン&アイ / ニトリ"),
    "1631.T": ("銀行", "三菱UFJ / 三井住友 / みずほ"),
    "1632.T": ("金融（除く銀行）", "野村HD / 東京海上 / SBIHD"),
    "1633.T": ("不動産", "三井不動産 / 三菱地所 / 住友不動産"),
    # 米国: Select Sector SPDR ETF (発行: State Street)
    "XLB": ("素材", "Linde / Sherwin-Williams"),
    "XLC": ("通信サービス", "Meta / Alphabet"),
    "XLE": ("エネルギー", "ExxonMobil / Chevron"),
    "XLF": ("金融", "JPMorgan / Bank of America"),
    "XLI": ("資本財", "GE / Caterpillar"),
    "XLK": ("情報技術", "Apple / Microsoft / Nvidia"),
    "XLP": ("生活必需品", "P&G / Coca-Cola"),
    "XLRE": ("不動産", "Prologis / American Tower"),
    "XLU": ("公共事業", "NextEra / Duke Energy"),
    "XLV": ("ヘルスケア", "UnitedHealth / J&J"),
    "XLY": ("一般消費財", "Amazon / Tesla"),
}


def label(ticker: str, *, with_companies: bool = False) -> str:
    """銘柄コードを人間が読める形式に整形.

    Examples:
        label("1630.T") → "小売 (1630.T)"
        label("1630.T", with_companies=True) → "小売 (1630.T) — ファストリ / セブン&アイ / ニトリ"
    """
    info = TICKER_INFO.get(ticker)
    if info is None:
        return ticker
    sector, companies = info
    if with_companies:
        return f"{sector} ({ticker}) — {companies}"
    return f"{sector} ({ticker})"


# 日本ETFの業種分類（論文 §4.1 の定義に厳密に従う）
# 論文: 1618.T, 1625.T, 1629.T, 1631.T = シクリカル
#       1617.T, 1621.T, 1627.T, 1630.T = ディフェンシブ
#       上記以外は 0（中立）
JP_SECTOR_TYPE: dict[str, int] = {
    "1618.T": +1,  # エネルギー資源
    "1625.T": +1,  # 電機・精密
    "1629.T": +1,  # 商社・卸売
    "1631.T": +1,  # 銀行
    "1617.T": -1,  # 食品
    "1621.T": -1,  # 医薬品
    "1627.T": -1,  # 電力・ガス
    "1630.T": -1,  # 小売
}

# 米国ETFの業種分類（論文 §4.1 の定義に厳密に従う）
# 論文: XLB, XLE, XLF, XLRE = シクリカル
#       XLK, XLP, XLU, XLV = ディフェンシブ
#       上記以外（XLC, XLI, XLY）は 0
US_SECTOR_TYPE: dict[str, int] = {
    "XLB": +1,
    "XLE": +1,
    "XLF": +1,
    "XLRE": +1,
    "XLK": -1,
    "XLP": -1,
    "XLU": -1,
    "XLV": -1,
}

# 戦略パラメータ（論文 §4.3 のデフォルト）
ROLLING_WINDOW = 60  # L: ローリング推定ウィンドウ長
N_FACTORS = 3  # K: 主成分数
LAMBDA = 0.9  # 正則化強度
QUANTILE = 0.3  # ロング/ショート分位点

# ロングオンリー版（10万円対応）
# 実証: close-to-close (前日引け→翌日引け), top 3 が最良
# AR 39.11% / Sharpe 2.05 / MDD -21.97% (2015-2026, cost=0)
N_LONG_POSITIONS = 3
TRANSACTION_COST = 0.0  # kabu Station API: 1日100万円まで無料 → 実質ゼロ

# インサイダー対象銘柄ブラックリスト（環境変数で管理。コミット禁止）
# .env: INSIDER_BLACKLIST=7203.T,9984.T のようにカンマ区切りで指定
INSIDER_BLACKLIST: set[str] = {
    t.strip() for t in os.getenv("INSIDER_BLACKLIST", "").split(",") if t.strip()
}
