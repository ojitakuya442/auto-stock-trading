"""論文 PCA SUB 戦略のバックテスト（ロングショート + ロングオンリー比較）"""
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
from auto_stock_trading.data import close_to_close_returns, fetch_all, open_to_close_returns
from auto_stock_trading.strategy import (
    build_c0_raw,
    build_common_exposure,
    estimate_full_correlation,
    estimate_signals,
    long_only_weights,
    long_short_weights,
    normalize_c0,
)


def annualized_return(returns: pd.Series, periods: int = 252) -> float:
    return returns.mean() * periods * 100


def annualized_risk(returns: pd.Series, periods: int = 252) -> float:
    return returns.std(ddof=0) * np.sqrt(periods) * 100


def sharpe(returns: pd.Series, periods: int = 252) -> float:
    risk = returns.std(ddof=0) * np.sqrt(periods)
    if risk == 0:
        return 0.0
    return returns.mean() * periods / risk


def max_drawdown(returns: pd.Series) -> float:
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    return float(dd.min() * 100)


def evaluate(name: str, daily_returns: pd.Series) -> dict:
    daily_returns = daily_returns.dropna()
    return {
        "Strategy": name,
        "AR (%)": annualized_return(daily_returns),
        "RISK (%)": annualized_risk(daily_returns),
        "R/R": sharpe(daily_returns),
        "MDD (%)": max_drawdown(daily_returns),
        "N days": len(daily_returns),
    }


def run_backtest(
    rcc: pd.DataFrame,
    roc_jp: pd.DataFrame,
    cost: float = TRANSACTION_COST,
) -> pd.DataFrame:
    """両戦略をバックテスト"""
    init_window = rcc.loc[:"2014-12-31"]
    c_full = estimate_full_correlation(init_window, US_TICKERS + JP_TICKERS)

    V0 = build_common_exposure(US_TICKERS, JP_TICKERS, US_SECTOR_TYPE, JP_SECTOR_TYPE)
    c0_raw = build_c0_raw(V0, c_full)
    c0 = normalize_c0(c0_raw)

    test_period_rcc = rcc.loc["2015-01-01":]
    print(f"Test period: {test_period_rcc.index.min()} to {test_period_rcc.index.max()}")

    signals = estimate_signals(rcc, US_TICKERS, JP_TICKERS, c0)
    signals = signals.loc["2015-01-01":]
    print(f"Generated {len(signals)} daily signals")

    if signals.empty:
        return pd.DataFrame()

    valid_dates = signals.index.intersection(roc_jp.index)
    signals = signals.loc[valid_dates]
    roc_aligned = roc_jp.loc[valid_dates]

    ls_returns = []
    lo_returns = []
    for date in valid_dates:
        sig = signals.loc[date]
        roc_today = roc_aligned.loc[date].dropna()
        common = sig.index.intersection(roc_today.index)
        if len(common) < 6:
            continue

        ls_w = long_short_weights(sig.loc[common], quantile=QUANTILE)
        ls_ret = (ls_w * roc_today.loc[common]).sum() - cost * ls_w.abs().sum()
        ls_returns.append((date, ls_ret))

        lo_w = long_only_weights(sig.loc[common], n_positions=N_LONG_POSITIONS)
        lo_ret = (lo_w * roc_today.loc[common]).sum() - cost * lo_w.abs().sum()
        lo_returns.append((date, lo_ret))

    ls_series = pd.Series(dict(ls_returns))
    lo_series = pd.Series(dict(lo_returns))

    topix_proxy = roc_aligned[JP_TICKERS].mean(axis=1).loc[valid_dates]

    return pd.DataFrame([
        evaluate("PCA SUB Long-Short", ls_series),
        evaluate("PCA SUB Long-Only (top 5)", lo_series),
        evaluate("TOPIX-17 equal-weight (benchmark)", topix_proxy),
    ])


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("Fetching data...")
    prices = fetch_all(start="2010-01-01")
    print(f"Prices shape: {prices.shape}")

    rcc = close_to_close_returns(prices, US_TICKERS + JP_TICKERS)
    roc_jp = open_to_close_returns(prices, JP_TICKERS)

    print(f"\nrcc shape: {rcc.shape}")
    print(f"roc_jp shape: {roc_jp.shape}")
    print(f"\nWindow={ROLLING_WINDOW}, K={N_FACTORS}, lambda={LAMBDA}, q={QUANTILE}, cost={TRANSACTION_COST*100:.2f}%")
    print()

    results = run_backtest(rcc, roc_jp)
    print()
    print(results.to_string(index=False, float_format="%.2f"))
    print()
    print("論文 (PCA SUB Long-Short, 2010-2025): AR=23.79%, RISK=10.70%, R/R=2.22, MDD=-9.58%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
