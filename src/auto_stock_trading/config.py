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
PAPER_INITIAL_CAPITAL = float(os.getenv("PAPER_INITIAL_CAPITAL", "150000"))

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
