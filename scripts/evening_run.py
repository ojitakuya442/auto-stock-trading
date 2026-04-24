"""引け後の夕方実行スクリプト

GitHub Actions の cron で 06:35 UTC（日本時間 15:35）に起動。
1. 当日終値を yfinance で取得
2. 全ポジションをクローズ
3. 日次サマリを Discord 通知
"""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from auto_stock_trading.config import JP_TICKERS, US_TICKERS
from auto_stock_trading.data import fetch_all
from auto_stock_trading.notify import notify_daily_summary, notify_error
from auto_stock_trading.paper_broker import PaperBroker


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    try:
        logger.info("=== Evening run started ===")

        prices = fetch_all(start="2024-01-01", use_cache=False)
        logger.info(f"Fetched prices: shape={prices.shape}")

        latest_close = {}
        for t in JP_TICKERS + US_TICKERS:
            if (t, "Close") in prices.columns:
                series = prices[(t, "Close")].dropna()
                if not series.empty:
                    latest_close[t] = float(series.iloc[-1])

        broker = PaperBroker()

        positions = broker.get_positions()
        positions_detail = []
        for p in positions:
            current = latest_close.get(p.symbol, p.avg_cost)
            pnl_pct = (current - p.avg_cost) / p.avg_cost * 100
            positions_detail.append({
                "symbol": p.symbol,
                "qty": p.qty,
                "avg_cost": p.avg_cost,
                "current_price": current,
                "pnl_pct": pnl_pct,
            })

        if positions:
            logger.info(f"Closing {len(positions)} positions")
            broker.close_all(latest_close, note="end-of-day close")
        else:
            logger.info("No positions to close")

        latest_date = prices.index.max()
        snap = broker.snapshot(latest_date, latest_close, note="evening")
        logger.info(f"Snapshot: total=¥{snap['total_value']:,.0f}, pnl_today=¥{snap['pnl_today']:+,.0f}")

        notify_daily_summary(
            snapshot_date=latest_date.strftime("%Y-%m-%d"),
            cash=snap["cash"],
            positions_value=snap["positions_value"],
            total_value=snap["total_value"],
            pnl_today=snap["pnl_today"],
            pnl_total=snap["pnl_total"],
            pnl_pct=snap["pnl_pct"],
            initial_capital=broker.get_initial_capital(),
            positions_detail=positions_detail,
        )

        logger.info("=== Evening run done ===")
        return 0

    except Exception as e:
        logger.exception("Evening run failed")
        notify_error("夕方の実行失敗", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
