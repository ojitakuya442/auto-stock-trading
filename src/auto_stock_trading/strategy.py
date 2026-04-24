"""部分空間正則化付きPCA × 日米リードラグ戦略

論文: 中川慧ほか「部分空間正則化付き主成分分析を用いた日米業種リードラグ投資戦略」
JSAI SIG-FIN 036, 2026 / DOI: 10.11517/jsaisigtwo.2026.FIN-036_76

実装は論文 §3 に準拠。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from auto_stock_trading.config import (
    JP_SECTOR_TYPE,
    JP_TICKERS,
    LAMBDA,
    N_FACTORS,
    ROLLING_WINDOW,
    US_SECTOR_TYPE,
    US_TICKERS,
)


@dataclass
class Signal:
    """戦略が出すシグナル"""
    date: pd.Timestamp
    predicted_returns: pd.Series  # 日本ETFごとの予測リターン
    long_tickers: list[str]
    short_tickers: list[str]


def build_common_exposure(
    us_tickers: list[str],
    jp_tickers: list[str],
    us_sector_type: dict[str, int],
    jp_sector_type: dict[str, int],
) -> np.ndarray:
    """論文 §3.1 の共通エクスポージャー V0 を構築。

    3つの方向ベクトル:
      v1: グローバルファクター (全 +1)
      v2: 日米スプレッド (米国 +1, 日本 -1)
      v3: シクリカル/ディフェンシブ感応度

    Returns:
        V0: shape (N, 3) のグラム・シュミット直交化済み行列
    """
    n_us = len(us_tickers)
    n_jp = len(jp_tickers)
    n = n_us + n_jp

    v1 = np.ones(n)

    v2 = np.concatenate([np.ones(n_us), -np.ones(n_jp)])

    v3 = np.array(
        [us_sector_type.get(t, 0) for t in us_tickers]
        + [jp_sector_type.get(t, 0) for t in jp_tickers],
        dtype=float,
    )

    V = np.column_stack([v1, v2, v3]).astype(float)
    Q, _ = np.linalg.qr(V)
    return Q


def estimate_full_correlation(returns: pd.DataFrame, tickers_order: list[str]) -> np.ndarray:
    """共通エクスポージャー固有値推定用の全期間相関行列 Cfull

    XLC (2018年〜) や XLRE (2015年〜) のように上場時期が異なる銘柄が
    含まれるため、pairwise complete observations で相関を計算する。
    """
    df = returns[tickers_order]
    corr = df.corr(min_periods=20).values
    return np.nan_to_num(corr, nan=0.0)


def build_c0_raw(V0: np.ndarray, c_full: np.ndarray) -> np.ndarray:
    """論文 (10), (11): V0 上の固有値を Cfull から推定して C0_raw を作る"""
    D0_diag = np.diag(V0.T @ c_full @ V0)
    D0 = np.diag(D0_diag)
    return V0 @ D0 @ V0.T


def normalize_c0(c0_raw: np.ndarray) -> np.ndarray:
    """論文 (12): C0 を相関行列に正規化（diag → 1）"""
    delta = np.diag(c0_raw)
    delta_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(delta, 1e-12)))
    c0 = delta_inv_sqrt @ c0_raw @ delta_inv_sqrt
    np.fill_diagonal(c0, 1.0)
    return c0


def estimate_signals(
    rcc: pd.DataFrame,
    us_tickers: list[str],
    jp_tickers: list[str],
    c0: np.ndarray,
    window: int = ROLLING_WINDOW,
    lam: float = LAMBDA,
    k: int = N_FACTORS,
) -> pd.DataFrame:
    """論文 §3.2-3.3: 各日 t について bzJ_{t+1} = B_t z_U_t を計算。

    Args:
        rcc: 日次 close-to-close リターン DataFrame (index=日付, columns=tickers)
        us_tickers: 米国側ティッカーリスト
        jp_tickers: 日本側ティッカーリスト
        c0: 共通エクスポージャー C0 (N×N、論文 (12))
        window: ローリング推定ウィンドウ長 L
        lam: 正則化強度 λ
        k: 主成分数 K

    Returns:
        DataFrame: 各日付の予測シグナル bzJ_{t+1}
                   indexは「シグナルが使える日（=予測対象日）」
    """
    all_tickers = us_tickers + jp_tickers
    n_us = len(us_tickers)

    rcc_aligned = rcc[all_tickers].copy()

    signals = {}
    dates = rcc_aligned.dropna().index

    for i in range(window, len(dates) - 1):
        t = dates[i]
        next_t = dates[i + 1]

        wt_dates = dates[i - window : i]
        z_window = rcc_aligned.loc[wt_dates]

        mu = z_window.mean()
        sigma = z_window.std(ddof=0).replace(0, np.nan)
        if sigma.isna().any():
            continue

        zt_window = (z_window - mu) / sigma
        ct = zt_window.corr().values

        c_reg = (1 - lam) * ct + lam * c0

        eigvals, eigvecs = np.linalg.eigh(c_reg)
        idx = np.argsort(eigvals)[::-1][:k]
        v_top = eigvecs[:, idx]

        v_u = v_top[:n_us, :]
        v_j = v_top[n_us:, :]

        z_u_today = (rcc_aligned.loc[t, us_tickers].values - mu[us_tickers].values) / sigma[us_tickers].values

        if np.isnan(z_u_today).any():
            continue

        f_t = v_u.T @ z_u_today
        bz_j_next = v_j @ f_t

        signals[next_t] = pd.Series(bz_j_next, index=jp_tickers)

    if not signals:
        return pd.DataFrame(columns=jp_tickers)
    return pd.DataFrame(signals).T.sort_index()


def long_short_weights(
    signal: pd.Series,
    quantile: float = 0.3,
) -> pd.Series:
    """論文 §2.2: 上位 q ロング、下位 q ショート、等ウェイト。

    ネット中立 (sum=0)、グロス2 (sum|w|=2)
    """
    n = len(signal)
    n_long = max(1, int(np.floor(n * quantile)))
    sorted_signal = signal.sort_values(ascending=False)
    longs = sorted_signal.head(n_long).index
    shorts = sorted_signal.tail(n_long).index

    weights = pd.Series(0.0, index=signal.index)
    weights.loc[longs] = 1.0 / len(longs)
    weights.loc[shorts] = -1.0 / len(shorts)
    return weights


def long_only_weights(
    signal: pd.Series,
    n_positions: int = 5,
) -> pd.Series:
    """ロングオンリー版（10万円対応）: 上位 n_positions を等ウェイトロング"""
    sorted_signal = signal.sort_values(ascending=False)
    longs = sorted_signal.head(n_positions).index
    weights = pd.Series(0.0, index=signal.index)
    weights.loc[longs] = 1.0 / len(longs)
    return weights


def generate_signal(
    rcc: pd.DataFrame,
    asof_date: pd.Timestamp | None = None,
) -> Signal | None:
    """指定日のシグナルを生成（最新運用想定）。

    Args:
        rcc: close-to-close リターン
        asof_date: シグナル基準日。Noneなら最新日。
    """
    if asof_date is None:
        asof_date = rcc.dropna().index[-1]

    init_window = rcc.loc[:"2014-12-31"]
    if len(init_window) < ROLLING_WINDOW:
        return None
    c_full = estimate_full_correlation(init_window, US_TICKERS + JP_TICKERS)

    V0 = build_common_exposure(US_TICKERS, JP_TICKERS, US_SECTOR_TYPE, JP_SECTOR_TYPE)
    c0_raw = build_c0_raw(V0, c_full)
    c0 = normalize_c0(c0_raw)

    rcc_subset = rcc.loc[:asof_date]
    signals = estimate_signals(rcc_subset, US_TICKERS, JP_TICKERS, c0)

    if signals.empty:
        return None

    next_date_signal = signals.iloc[-1]
    next_date = signals.index[-1]

    sorted_signal = next_date_signal.sort_values(ascending=False)
    n = len(sorted_signal)
    n_q = max(1, int(np.floor(n * 0.3)))

    return Signal(
        date=next_date,
        predicted_returns=next_date_signal,
        long_tickers=sorted_signal.head(n_q).index.tolist(),
        short_tickers=sorted_signal.tail(n_q).index.tolist(),
    )
