"""ペーパートレード用ブローカー（仮想取引）"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from auto_stock_trading.config import (
    PAPER_DB_PATH,
    PAPER_INITIAL_CAPITAL,
    TRANSACTION_COST,
)

logger = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cash REAL NOT NULL,
    initial_capital REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    qty REAL NOT NULL,
    avg_cost REAL NOT NULL,
    opened_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    executed_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_date TEXT NOT NULL,
    target_symbol TEXT NOT NULL,
    predicted_return REAL NOT NULL,
    rank INTEGER NOT NULL,
    acted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    snapshot_date TEXT PRIMARY KEY,
    cash REAL NOT NULL,
    positions_value REAL NOT NULL,
    total_value REAL NOT NULL,
    pnl_today REAL NOT NULL,
    pnl_total REAL NOT NULL,
    note TEXT
);
"""


@dataclass
class Position:
    symbol: str
    qty: float
    avg_cost: float


@dataclass
class Trade:
    executed_at: datetime
    symbol: str
    side: str
    qty: float
    price: float
    fee: float


class PaperBroker:
    """SQLite を永続化層に持つペーパートレードブローカー"""

    def __init__(self, db_path: Path = PAPER_DB_PATH, initial_capital: float = PAPER_INITIAL_CAPITAL):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            cur = conn.execute("SELECT id FROM account WHERE id = 1")
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO account (id, cash, initial_capital, created_at) VALUES (1, ?, ?, ?)",
                    (self.initial_capital, self.initial_capital, datetime.utcnow().isoformat()),
                )
                logger.info(f"Initialized paper account with ¥{self.initial_capital:,.0f}")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get_cash(self) -> float:
        with self._conn() as conn:
            row = conn.execute("SELECT cash FROM account WHERE id = 1").fetchone()
            return row["cash"]

    def get_initial_capital(self) -> float:
        with self._conn() as conn:
            row = conn.execute("SELECT initial_capital FROM account WHERE id = 1").fetchone()
            return row["initial_capital"]

    def get_positions(self) -> list[Position]:
        with self._conn() as conn:
            rows = conn.execute("SELECT symbol, qty, avg_cost FROM positions").fetchall()
            return [Position(r["symbol"], r["qty"], r["avg_cost"]) for r in rows]

    def buy(self, symbol: str, qty: float, price: float, note: str = "") -> Trade:
        cost = qty * price
        fee = cost * TRANSACTION_COST
        total = cost + fee

        cash = self.get_cash()
        if total > cash:
            raise ValueError(f"Insufficient cash: need ¥{total:,.0f}, have ¥{cash:,.0f}")

        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute("UPDATE account SET cash = cash - ? WHERE id = 1", (total,))

            row = conn.execute("SELECT qty, avg_cost FROM positions WHERE symbol = ?", (symbol,)).fetchone()
            if row:
                new_qty = row["qty"] + qty
                new_cost = (row["qty"] * row["avg_cost"] + cost) / new_qty
                conn.execute(
                    "UPDATE positions SET qty = ?, avg_cost = ? WHERE symbol = ?",
                    (new_qty, new_cost, symbol),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (symbol, qty, avg_cost, opened_at) VALUES (?, ?, ?, ?)",
                    (symbol, qty, price, now),
                )

            conn.execute(
                "INSERT INTO trades (executed_at, symbol, side, qty, price, fee, note) VALUES (?, ?, 'BUY', ?, ?, ?, ?)",
                (now, symbol, qty, price, fee, note),
            )

        logger.info(f"BUY {symbol} qty={qty} @ ¥{price:,.2f} (fee=¥{fee:.2f})")
        return Trade(datetime.utcnow(), symbol, "BUY", qty, price, fee)

    def sell(self, symbol: str, qty: float, price: float, note: str = "") -> Trade:
        with self._conn() as conn:
            row = conn.execute("SELECT qty, avg_cost FROM positions WHERE symbol = ?", (symbol,)).fetchone()
            if row is None or row["qty"] < qty:
                have = row["qty"] if row else 0
                raise ValueError(f"Insufficient position: need {qty} of {symbol}, have {have}")

            proceeds = qty * price
            fee = proceeds * TRANSACTION_COST
            net = proceeds - fee

            now = datetime.utcnow().isoformat()
            conn.execute("UPDATE account SET cash = cash + ? WHERE id = 1", (net,))

            new_qty = row["qty"] - qty
            if new_qty < 1e-9:
                conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            else:
                conn.execute("UPDATE positions SET qty = ? WHERE symbol = ?", (new_qty, symbol))

            conn.execute(
                "INSERT INTO trades (executed_at, symbol, side, qty, price, fee, note) VALUES (?, ?, 'SELL', ?, ?, ?, ?)",
                (now, symbol, qty, price, fee, note),
            )

        logger.info(f"SELL {symbol} qty={qty} @ ¥{price:,.2f} (fee=¥{fee:.2f})")
        return Trade(datetime.utcnow(), symbol, "SELL", qty, price, fee)

    def close_all(self, prices: dict[str, float], note: str = "") -> list[Trade]:
        """全ポジションを指定価格でクローズ"""
        trades = []
        for pos in self.get_positions():
            if pos.symbol in prices:
                trades.append(self.sell(pos.symbol, pos.qty, prices[pos.symbol], note=note))
            else:
                logger.warning(f"No price for {pos.symbol}, skipping close")
        return trades

    def total_value(self, prices: dict[str, float]) -> float:
        cash = self.get_cash()
        positions_value = sum(p.qty * prices.get(p.symbol, p.avg_cost) for p in self.get_positions())
        return cash + positions_value

    def positions_value(self, prices: dict[str, float]) -> float:
        return sum(p.qty * prices.get(p.symbol, p.avg_cost) for p in self.get_positions())

    def record_signals(self, signal_date: pd.Timestamp, predicted_returns: pd.Series) -> None:
        sorted_returns = predicted_returns.sort_values(ascending=False)
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            for rank, (sym, val) in enumerate(sorted_returns.items(), start=1):
                conn.execute(
                    "INSERT INTO signals (signal_date, target_symbol, predicted_return, rank, acted, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                    (signal_date.strftime("%Y-%m-%d"), sym, float(val), rank, now),
                )

    def snapshot(self, date: pd.Timestamp, prices: dict[str, float], note: str = "") -> dict:
        cash = self.get_cash()
        pos_val = self.positions_value(prices)
        total = cash + pos_val
        initial = self.get_initial_capital()

        with self._conn() as conn:
            prev = conn.execute(
                "SELECT total_value FROM daily_snapshots ORDER BY snapshot_date DESC LIMIT 1"
            ).fetchone()
            prev_total = prev["total_value"] if prev else initial

            pnl_today = total - prev_total
            pnl_total = total - initial

            conn.execute(
                """INSERT OR REPLACE INTO daily_snapshots
                (snapshot_date, cash, positions_value, total_value, pnl_today, pnl_total, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (date.strftime("%Y-%m-%d"), cash, pos_val, total, pnl_today, pnl_total, note),
            )

        return {
            "date": date,
            "cash": cash,
            "positions_value": pos_val,
            "total_value": total,
            "pnl_today": pnl_today,
            "pnl_total": pnl_total,
            "pnl_pct": pnl_total / initial * 100,
        }

    def recent_trades(self, limit: int = 10) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT executed_at, symbol, side, qty, price, fee FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
