"""論文 PCA SUB 戦略のバックテスト

本実装の方針:
- 取引タイミング: close-to-close (前日引け→当日引け)
- 論文の open-to-close より高い性能 + 日中の不利な値動きを回避
- 取引コスト: kabu Station API 想定で 0.0 をデフォルト (1日100万円まで無料)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from auto_stock_trading.config import (
    JP_SECTOR_TYPE,
    JP_TICKERS,
    LAMBDA,
    N_FACTORS,
    N_LONG_POSITIONS,
    QUANTILE,
    ROLLING_WINDOW,
    TRANSACTION_COST,
    US_SECTOR_TYPE,
    US_TICKERS,
)
from auto_stock_trading.data import close_to_close_returns, fetch_all
from auto_stock_trading.strategy import (
    build_c0_raw,
    build_common_exposure,
    estimate_full_correlation,
    estimate_signals,
    long_only_weights,
    long_short_weights,
    normalize_c0,
)


def metrics(returns: pd.Series) -> dict:
    r = returns.dropna()
    if len(r) == 0:
        return {"AR (%)": 0, "RISK (%)": 0, "Sharpe": 0, "MDD (%)": 0, "N": 0}
    risk = r.std(ddof=0) * np.sqrt(252)
    sharpe = r.mean() * 252 / risk if risk > 0 else 0
    cum = (1 + r).cumprod()
    mdd = ((cum - cum.cummax()) / cum.cummax()).min() * 100
    return {
        "AR (%)": r.mean() * 252 * 100,
        "RISK (%)": risk * 100,
        "Sharpe": sharpe,
        "MDD (%)": mdd,
        "N": len(r),
    }


def evaluate_strategy(
    signals: pd.DataFrame,
    target_returns: pd.DataFrame,
    weight_fn,
    cost: float = TRANSACTION_COST,
    min_assets: int = 6,
) -> pd.Series:
    valid = signals.index.intersection(target_returns.index)
    rs = []
    for date in valid:
        s = signals.loc[date].dropna()
        r = target_returns.loc[date].dropna()
        common = s.index.intersection(r.index)
        if len(common) < min_assets:
            continue
        w = weight_fn(s.loc[common])
        rs.append((date, (w * r.loc[common]).sum() - cost * w.abs().sum()))
    return pd.Series(dict(rs))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("Fetching data...")
    prices = fetch_all(start="2010-01-01")

    rcc = close_to_close_returns(prices, US_TICKERS + JP_TICKERS)
    ccc_jp = close_to_close_returns(prices, JP_TICKERS)

    print(f"\nData period: {rcc.index.min().date()} to {rcc.index.max().date()}")
    print(f"Window={ROLLING_WINDOW}, K={N_FACTORS}, lambda={LAMBDA}, q={QUANTILE}, n_long={N_LONG_POSITIONS}, cost={TRANSACTION_COST*100:.3f}%")

    init_window = rcc.loc[:"2014-12-31"]
    c_full = estimate_full_correlation(init_window, US_TICKERS + JP_TICKERS)
    V0 = build_common_exposure(US_TICKERS, JP_TICKERS, US_SECTOR_TYPE, JP_SECTOR_TYPE)
    c0 = normalize_c0(build_c0_raw(V0, c_full))

    print("\nGenerating signals...")
    signals = estimate_signals(rcc, US_TICKERS, JP_TICKERS, c0).loc["2015-01-01":]
    print(f"  {len(signals)} daily signals")

    # MOM baseline (paper expects: AR=5.63%, R/R=0.53)
    mom_signal = ccc_jp.rolling(ROLLING_WINDOW).mean().shift(1).loc["2015-01-01":]

    print("\n=== Backtest results (2015-2026, close-to-close, cost=%.3f%%) ===" % (TRANSACTION_COST * 100))
    print(f"{'Strategy':40s} {'AR%':>8s} {'RISK%':>8s} {'Sharpe':>8s} {'MDD%':>8s} {'N':>6s}")
    print("-" * 85)

    results = []
    results.append((
        "MOM Long-Short (baseline)",
        evaluate_strategy(mom_signal, ccc_jp, lambda s: long_short_weights(s, QUANTILE)),
    ))
    results.append((
        "PCA SUB Long-Short",
        evaluate_strategy(signals, ccc_jp, lambda s: long_short_weights(s, QUANTILE)),
    ))
    results.append((
        f"PCA SUB Long-Only (top {N_LONG_POSITIONS})",
        evaluate_strategy(signals, ccc_jp, lambda s: long_only_weights(s, N_LONG_POSITIONS)),
    ))

    benchmark_dates = signals.index.intersection(ccc_jp.index)
    benchmark = ccc_jp.loc[benchmark_dates].mean(axis=1)
    results.append(("TOPIX-17 equal-weight (benchmark)", benchmark))

    for name, series in results:
        m = metrics(series)
        print(f"{name:40s} {m['AR (%)']:+8.2f} {m['RISK (%)']:+8.2f} {m['Sharpe']:+8.2f} {m['MDD (%)']:+8.2f} {m['N']:>6d}")

    print()
    print("論文 (open-to-close, 2010-2025): MOM AR=5.63% R/R=0.53, PCA SUB AR=23.79% R/R=2.22 MDD=-9.58%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
