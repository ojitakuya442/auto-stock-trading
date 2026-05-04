"""引け実行スクリプト：close-to-close 戦略の中核

GitHub Actions の cron で 06:35 UTC（日本時間 15:35）に起動。
1. 当日終値を yfinance で取得
2. 既存ポジションを当日引けでクローズ（前日エントリーの決済）
3. 当日シグナルに基づいて新規ポジションを当日引けで建てる
4. 日次サマリを Discord 通知

戦略: 前日米国引け情報 → 当日シグナル生成 → 当日引けで新規建て → 翌日引けで決済
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
from auto_stock_trading.market_calendar import is_jp_trading_day, today_jst_str
from auto_stock_trading.notify import (
    notify_daily_summary,
    notify_error,
    notify_holiday_skip,
    notify_orders_executed,
)
from auto_stock_trading.paper_broker import PaperBroker
from auto_stock_trading.strategy import generate_signal


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    try:
        logger.info("=== Evening run started ===")

        is_open, reason = is_jp_trading_day()
        if not is_open:
            logger.info(f"東証休場のためスキップ: {reason}")
            notify_holiday_skip(today_jst_str(), reason, "引けの売買")
            return 0

        prices = fetch_all(start="2010-01-01", use_cache=False)
        logger.info(f"Fetched prices: shape={prices.shape}")

        rcc = close_to_close_returns(prices, US_TICKERS + JP_TICKERS)

        # 当日終値（仮想取引で使用）
        latest_close = {}
        for t in JP_TICKERS + US_TICKERS:
            if (t, "Close") in prices.columns:
                series = prices[(t, "Close")].dropna()
                if not series.empty:
                    latest_close[t] = float(series.iloc[-1])

        latest_date = prices.index.max()
        broker = PaperBroker()

        # === Step 1: 既存ポジション（前日建て）を当日引けでクローズ ===
        positions_before = broker.get_positions()
        positions_detail = []
        for p in positions_before:
            current = latest_close.get(p.symbol, p.avg_cost)
            pnl_pct = (current - p.avg_cost) / p.avg_cost * 100
            positions_detail.append({
                "symbol": p.symbol,
                "qty": p.qty,
                "avg_cost": p.avg_cost,
                "current_price": current,
                "pnl_pct": pnl_pct,
            })

        if positions_before:
            logger.info(f"Closing {len(positions_before)} positions from previous session")
            broker.close_all(latest_close, note="end-of-day close")
        else:
            logger.info("No previous positions to close")

        # === Step 2: 当日シグナルで新規建て（当日引け価格、整数口数） ===
        # 実運用: NEXT FUNDS TOPIX-17 ETF は1口単位、kabu Station API でも整数口数
        sig = generate_signal(rcc)
        executed = []
        skipped = []
        if sig is not None:
            broker.record_signals(sig.date, sig.predicted_returns)

            long_tickers = sig.long_tickers[:N_LONG_POSITIONS]

            # 等ウェイト配分: 総資産 × 70% を N 銘柄で均等割り → 各銘柄の上限予算内で最大整数口数を購入
            # 論文の equal-weight top-N を整数口数制約で近似する
            total_capital = broker.total_value(latest_close)
            budget_per_ticker = total_capital * 0.70 / N_LONG_POSITIONS

            for t in long_tickers:
                if t not in latest_close:
                    logger.warning(f"No price for {t}, skipping")
                    skipped.append({"symbol": t, "reason": "価格データなし"})
                    continue
                price = latest_close[t]
                cash = broker.get_cash()

                # 等ウェイト上限内で最大口数。上限を超えても現金があれば最低1口は買う（バッファで吸収）
                max_qty = int(min(budget_per_ticker, cash) // price)
                if max_qty < 1:
                    if price <= cash:
                        max_qty = 1  # 上限オーバーだがバッファで吸収して1口購入
                    else:
                        logger.warning(f"Cannot afford {t}: price=¥{price:,.0f}, cash=¥{cash:,.0f}")
                        skipped.append({"symbol": t, "reason": f"現金不足 (¥{price:,.0f}/口)"})
                        continue

                try:
                    trade = broker.buy(t, qty=float(max_qty), price=price, note=f"signal={sig.predicted_returns[t]:+.4f} qty={max_qty}")
                    executed.append({
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "qty": trade.qty,
                        "price": trade.price,
                    })
                except Exception as e:
                    logger.exception(f"Failed to buy {t}: {e}")
                    skipped.append({"symbol": t, "reason": str(e)})
        else:
            logger.warning("No signal generated, skipping new positions")

        if executed or skipped:
            notify_orders_executed(executed, skipped)

        # === Step 3: 日次サマリ通知 ===
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
        notify_error("引け実行失敗", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
