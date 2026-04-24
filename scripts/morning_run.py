"""寄付前の朝実行スクリプト

GitHub Actions の cron で 23:50 UTC（日本時間 8:50）に起動。
1. 米国前日終値（および日本も）まで yfinance で取得
2. PCA SUB 戦略でシグナル生成
3. 上位 N 銘柄を仮想買付（前日の引け価格で代用、当日寄付不明なため）
4. Discord 通知
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from auto_stock_trading.config import (
    JP_TICKERS,
    N_LONG_POSITIONS,
    QUANTILE,
    US_TICKERS,
)
from auto_stock_trading.data import close_to_close_returns, fetch_all
from auto_stock_trading.notify import (
    notify_error,
    notify_morning_signal,
    notify_orders_executed,
)
from auto_stock_trading.paper_broker import PaperBroker
from auto_stock_trading.strategy import generate_signal


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    try:
        logger.info("=== Morning run started ===")

        prices = fetch_all(start="2010-01-01", use_cache=False)
        logger.info(f"Fetched prices: shape={prices.shape}")

        rcc = close_to_close_returns(prices, US_TICKERS + JP_TICKERS)
        logger.info(f"Computed rcc: shape={rcc.shape}, last_date={rcc.dropna().index[-1]}")

        sig = generate_signal(rcc)
        if sig is None:
            notify_error("Signal生成失敗", "シグナルを生成できませんでした（データ不足か要確認）")
            return 1

        logger.info(f"Signal date: {sig.date}, top long candidates: {sig.long_tickers}")

        broker = PaperBroker()
        broker.record_signals(sig.date, sig.predicted_returns)

        existing = {p.symbol for p in broker.get_positions()}
        if existing:
            logger.warning(f"Positions exist from yesterday, expected to be closed: {existing}")

        cash = broker.get_cash()
        long_tickers = sig.long_tickers[:N_LONG_POSITIONS]
        budget_per_position = cash * 0.95 / len(long_tickers)

        latest_close = {t: prices[(t, "Close")].dropna().iloc[-1] for t in long_tickers if (t, "Close") in prices.columns}

        notify_morning_signal(
            signal_date=sig.date.strftime("%Y-%m-%d"),
            long_tickers=long_tickers,
            predicted_returns=sig.predicted_returns.to_dict(),
            target_value_per_position=budget_per_position,
            cash=cash,
        )

        executed = []
        for t in long_tickers:
            if t not in latest_close:
                logger.warning(f"No price for {t}, skipping")
                continue
            price = latest_close[t]
            qty = budget_per_position / price
            try:
                trade = broker.buy(t, qty=qty, price=price, note=f"signal={sig.predicted_returns[t]:+.4f}")
                executed.append({
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "qty": trade.qty,
                    "price": trade.price,
                })
            except Exception as e:
                logger.exception(f"Failed to buy {t}: {e}")

        if executed:
            notify_orders_executed(executed)

        logger.info(f"=== Morning run done. Executed {len(executed)} orders ===")
        return 0

    except Exception as e:
        logger.exception("Morning run failed")
        notify_error("朝の実行失敗", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
