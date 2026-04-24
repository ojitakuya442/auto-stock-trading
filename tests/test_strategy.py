"""戦略実装の最小スモークテスト"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from auto_stock_trading.config import JP_SECTOR_TYPE, JP_TICKERS, US_SECTOR_TYPE, US_TICKERS
from auto_stock_trading.strategy import (
    build_c0_raw,
    build_common_exposure,
    estimate_signals,
    long_only_weights,
    long_short_weights,
    normalize_c0,
)


def test_common_exposure_shape():
    V0 = build_common_exposure(US_TICKERS, JP_TICKERS, US_SECTOR_TYPE, JP_SECTOR_TYPE)
    assert V0.shape == (len(US_TICKERS) + len(JP_TICKERS), 3)
    np.testing.assert_allclose(V0.T @ V0, np.eye(3), atol=1e-9)


def test_normalize_c0_diag():
    n = 28
    rng = np.random.default_rng(42)
    A = rng.standard_normal((n, n))
    cov = A @ A.T
    c0 = normalize_c0(cov)
    np.testing.assert_allclose(np.diag(c0), np.ones(n), atol=1e-9)


def test_long_short_weights_neutral():
    sig = pd.Series([0.1, 0.05, 0.0, -0.05, -0.1, 0.2, -0.2, 0.15, -0.15, 0.08])
    w = long_short_weights(sig, quantile=0.3)
    assert abs(w.sum()) < 1e-9
    np.testing.assert_allclose(w.abs().sum(), 2.0, atol=1e-9)


def test_long_only_weights_sum():
    sig = pd.Series(np.arange(17, dtype=float), index=JP_TICKERS)
    w = long_only_weights(sig, n_positions=5)
    np.testing.assert_allclose(w.sum(), 1.0)
    assert (w > 0).sum() == 5


def test_estimate_signals_smoke():
    rng = np.random.default_rng(0)
    n_us, n_jp = len(US_TICKERS), len(JP_TICKERS)
    n_days = 200
    dates = pd.date_range("2020-01-01", periods=n_days, freq="B")
    data = rng.standard_normal((n_days, n_us + n_jp)) * 0.01
    rcc = pd.DataFrame(data, index=dates, columns=US_TICKERS + JP_TICKERS)

    V0 = build_common_exposure(US_TICKERS, JP_TICKERS, US_SECTOR_TYPE, JP_SECTOR_TYPE)
    cov = rcc.corr().values
    c0_raw = build_c0_raw(V0, cov)
    c0 = normalize_c0(c0_raw)

    signals = estimate_signals(rcc, US_TICKERS, JP_TICKERS, c0, window=60)
    assert not signals.empty
    assert signals.shape[1] == n_jp
    assert signals.index.is_monotonic_increasing
