"""yfinance を使った日米ETFのヒストリカルデータ取得"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from auto_stock_trading.config import DATA_DIR, JP_TICKERS, US_TICKERS

logger = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def _missing_tickers(out: pd.DataFrame, tickers: list[str]) -> list[str]:
    """価格データが取得できていないティッカーを返す。"""
    missing = []
    for t in tickers:
        if (t, "Close") not in out.columns:
            missing.append(t)
        elif out[(t, "Close")].dropna().empty:
            missing.append(t)
    return missing


def fetch_prices(
    tickers: list[str],
    start: str = "2010-01-01",
    end: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """指定ティッカーのOHLCV (Close + Open) を取得。

    Returns:
        DataFrame with MultiIndex columns (ticker, field) where field in {'Open', 'Close'}.
    """
    if end is None:
        end = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    cache_path = CACHE_DIR / f"prices_{start}_{end}_{hash(tuple(tickers)) & 0xFFFF:x}.pkl"
    if use_cache and cache_path.exists():
        logger.info(f"Loading cached prices: {cache_path.name}")
        return pd.read_pickle(cache_path)

    logger.info(f"Fetching {len(tickers)} tickers from yfinance ({start} to {end})")
    # threads=False: yfinance 内部の TzCache (SQLite) ロック競合を避ける
    df = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=False,
    )

    if isinstance(df.columns, pd.MultiIndex):
        out = df.loc[:, pd.IndexSlice[:, ["Open", "Close"]]].copy()
    else:
        out = df[["Open", "Close"]].copy()
        out.columns = pd.MultiIndex.from_product([[tickers[0]], out.columns])

    # 欠損銘柄を個別ダウンロードでリトライ（一過性のロック対策）
    for attempt in range(2):
        missing = _missing_tickers(out, tickers)
        if not missing:
            break
        logger.warning(f"Retrying missing tickers (attempt {attempt + 1}): {missing}")
        for t in missing:
            time.sleep(1)
            try:
                retry = yf.download(
                    t,
                    start=start,
                    end=end,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                )
                if retry is None or retry.empty:
                    continue
                if isinstance(retry.columns, pd.MultiIndex):
                    for field in ("Open", "Close"):
                        if (t, field) in retry.columns:
                            out[(t, field)] = retry[(t, field)]
                else:
                    for field in ("Open", "Close"):
                        if field in retry.columns:
                            out[(t, field)] = retry[field]
            except Exception as e:
                logger.warning(f"Retry failed for {t}: {e}")

    still_missing = _missing_tickers(out, tickers)
    if still_missing:
        logger.error(f"Tickers still missing after retries: {still_missing}")

    out = out.dropna(how="all")
    if use_cache:
        out.to_pickle(cache_path)
        logger.info(f"Cached to {cache_path.name}")
    return out


def fetch_all(start: str = "2010-01-01", end: str | None = None, use_cache: bool = True) -> pd.DataFrame:
    """日米全ETFを一括取得"""
    all_tickers = US_TICKERS + JP_TICKERS
    return fetch_prices(all_tickers, start=start, end=end, use_cache=use_cache)


def close_to_close_returns(prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """指定ティッカーのClose-to-Closeリターン (rcc)"""
    closes = pd.DataFrame({t: prices[(t, "Close")] for t in tickers if (t, "Close") in prices.columns})
    return closes.pct_change().dropna(how="all")


def open_to_close_returns(prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """指定ティッカーのOpen-to-Closeリターン (roc)"""
    out = {}
    for t in tickers:
        if (t, "Open") in prices.columns and (t, "Close") in prices.columns:
            out[t] = prices[(t, "Close")] / prices[(t, "Open")] - 1
    return pd.DataFrame(out).dropna(how="all")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    prices = fetch_all(start="2010-01-01")
    print(f"Shape: {prices.shape}")
    print(f"Date range: {prices.index.min()} to {prices.index.max()}")
    print(f"Tickers: {sorted(set(prices.columns.get_level_values(0)))}")
