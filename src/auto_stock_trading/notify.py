"""Discord Webhook 通知"""
from __future__ import annotations

import logging
from typing import Any

import requests

from auto_stock_trading.config import DISCORD_WEBHOOK_URL, label

logger = logging.getLogger(__name__)


COLOR_INFO = 0x3498DB
COLOR_SUCCESS = 0x2ECC71
COLOR_WARNING = 0xF39C12
COLOR_ERROR = 0xE74C3C


def send_message(content: str | None = None, embeds: list[dict] | None = None) -> bool:
    """Discord Webhook に送信。Webhook 未設定なら警告だけ出して握りつぶす。"""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set, skipping notification")
        if content:
            logger.info(f"Would have sent: {content[:200]}")
        return False

    payload: dict[str, Any] = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Discord notification failed: {e}")
        return False


def notify_morning_signal(
    signal_date: str,
    long_tickers: list[str],
    predicted_returns: dict[str, float],
    target_value_per_position: float,
    cash: float,
) -> bool:
    """寄付前: 当日のロング銘柄シグナルを通知"""
    rank_lines = []
    for i, t in enumerate(long_tickers, start=1):
        pred = predicted_returns.get(t, 0.0)
        rank_lines.append(f"`{i}.` **{label(t, with_companies=True)}**\n　　 予測: {pred:+.4f}")

    fields = [
        {"name": "ロング対象銘柄", "value": "\n".join(rank_lines) if rank_lines else "（なし）", "inline": False},
        {"name": "想定平均価格/口", "value": f"¥{target_value_per_position:,.0f}", "inline": True},
        {"name": "現在の総キャッシュ", "value": f"¥{cash:,.0f}", "inline": True},
    ]

    embed = {
        "title": "📈 朝のシグナル予告",
        "description": f"**{signal_date}** の予測に基づき、本日引けで以下を1口ずつ仮想買付予定。",
        "color": COLOR_INFO,
        "fields": fields,
        "footer": {"text": "auto-stock-trading / PCA SUB strategy"},
    }
    return send_message(embeds=[embed])


def notify_orders_executed(trades: list[dict], skipped: list[dict] | None = None) -> bool:
    """引け後: 約定報告"""
    if not trades and not skipped:
        return False
    lines = []
    for t in trades:
        emoji = "🟢" if t["side"] == "BUY" else "🔴"
        qty_str = f"{int(t['qty'])}口" if t['qty'] == int(t['qty']) else f"{t['qty']:.2f}口"
        lines.append(f"{emoji} {t['side']} **{label(t['symbol'])}** {qty_str} @ ¥{t['price']:,.0f}")

    if skipped:
        lines.append("")
        lines.append("**⏭️ スキップ:**")
        for s in skipped:
            lines.append(f"・{label(s['symbol'])}: {s['reason']}")

    embed = {
        "title": "✅ 仮想約定",
        "description": "\n".join(lines),
        "color": COLOR_SUCCESS,
    }
    return send_message(embeds=[embed])


def notify_daily_summary(
    snapshot_date: str,
    cash: float,
    positions_value: float,
    total_value: float,
    pnl_today: float,
    pnl_total: float,
    pnl_pct: float,
    initial_capital: float,
    positions_detail: list[dict] | None = None,
) -> bool:
    """引け後: 日次サマリ"""
    today_emoji = "📈" if pnl_today >= 0 else "📉"
    total_emoji = "🟢" if pnl_total >= 0 else "🔴"

    fields = [
        {"name": "現金", "value": f"¥{cash:,.0f}", "inline": True},
        {"name": "ポジション評価額", "value": f"¥{positions_value:,.0f}", "inline": True},
        {"name": "総資産", "value": f"¥{total_value:,.0f}", "inline": True},
        {"name": f"{today_emoji} 当日損益", "value": f"¥{pnl_today:+,.0f}", "inline": True},
        {"name": f"{total_emoji} 累積損益", "value": f"¥{pnl_total:+,.0f} ({pnl_pct:+.2f}%)", "inline": True},
        {"name": "初期資産", "value": f"¥{initial_capital:,.0f}", "inline": True},
    ]

    if positions_detail:
        pos_lines = []
        for p in positions_detail[:10]:
            qty_str = f"{int(p['qty'])}口" if p['qty'] == int(p['qty']) else f"{p['qty']:.2f}口"
            pos_lines.append(f"**{label(p['symbol'])}** {qty_str} (取得¥{p['avg_cost']:,.0f} → 現¥{p['current_price']:,.0f}, {p['pnl_pct']:+.2f}%)")
        if pos_lines:
            fields.append({"name": "保有ポジション", "value": "\n".join(pos_lines), "inline": False})

    color = COLOR_SUCCESS if pnl_today >= 0 else COLOR_WARNING

    embed = {
        "title": f"📊 日次サマリ ({snapshot_date})",
        "color": color,
        "fields": fields,
        "footer": {"text": "auto-stock-trading / paper trading"},
    }
    return send_message(embeds=[embed])


def notify_error(title: str, message: str) -> bool:
    """エラー通知"""
    embed = {
        "title": f"⚠️ {title}",
        "description": f"```\n{message[:1500]}\n```",
        "color": COLOR_ERROR,
    }
    return send_message(embeds=[embed])
