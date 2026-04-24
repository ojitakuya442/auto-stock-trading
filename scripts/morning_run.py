"""朝の予告通知スクリプト（実取引なし）

GitHub Actions の cron で 23:53 UTC（日本時間 8:53）に起動。
1. 米国前日終値まで yfinance で取得
2. PCA SUB 戦略でシグナル生成
3. 当日引けで仮想取引する候補銘柄を Discord に予告通知

実際の取引は引け実行 (evening_run.py) で行う (close-to-close strategy)。
本スクリプトはユーザーが「今日の取引内容」を引け前に確認できるようにするためのもの。
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auto_stock_trading.config import (
    JP_TICKERS,
    N_LONG_POSITIONS,
    US_TICKERS,
)
from auto_stock_trading.data import close_to_close_returns, fetch_all
from auto_stock_trading.notify import notify_error, notify_morning_signal
from auto_stock_trading.paper_broker import PaperBroker
from auto_stock_trading.strategy import generate_signal


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    try:
        logger.info("=== Morning preview started ===")

        prices = fetch_all(start="2010-01-01", use_cache=False)
        logger.info(f"Fetched prices: shape={prices.shape}")

        rcc = close_to_close_returns(prices, US_TICKERS + JP_TICKERS)
        logger.info(f"Computed rcc: shape={rcc.shape}, last_date={rcc.dropna().index[-1]}")

        sig = generate_signal(rcc)
        if sig is None:
            notify_error("Signal生成失敗", "シグナルを生成できませんでした")
            return 1

        long_tickers = sig.long_tickers[:N_LONG_POSITIONS]
        logger.info(f"Signal date: {sig.date}, top long candidates: {long_tickers}")

        broker = PaperBroker()
        broker.record_signals(sig.date, sig.predicted_returns)

        cash = broker.get_cash()
        budget_per_position = cash * 0.95 / max(len(long_tickers), 1)

        notify_morning_signal(
            signal_date=sig.date.strftime("%Y-%m-%d"),
            long_tickers=long_tickers,
            predicted_returns=sig.predicted_returns.to_dict(),
            target_value_per_position=budget_per_position,
            cash=cash,
        )

        logger.info("=== Morning preview done (notification only, no trades) ===")
        return 0

    except Exception as e:
        logger.exception("Morning preview failed")
        notify_error("朝の予告通知失敗", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
