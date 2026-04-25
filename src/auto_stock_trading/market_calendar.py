"""東証（TSE）の取引日判定"""
from __future__ import annotations

from datetime import date

import jpholiday
import pandas as pd


def is_jp_trading_day(today: date | None = None) -> tuple[bool, str]:
    """東証が開いているかを判定。

    Returns:
        (is_trading_day, reason): 取引日でなければ理由を返す
    """
    if today is None:
        today = pd.Timestamp.now(tz="Asia/Tokyo").date()

    if today.weekday() == 5:
        return False, "土曜日"
    if today.weekday() == 6:
        return False, "日曜日"

    if jpholiday.is_holiday(today):
        holiday_name = jpholiday.is_holiday_name(today)
        return False, f"祝日 ({holiday_name})"

    if today.month == 12 and today.day == 31:
        return False, "大納会後の年末休場"
    if today.month == 1 and today.day in (1, 2, 3):
        return False, "正月休場 (大発会前)"

    return True, ""


def today_jst_str() -> str:
    return pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d (%a)")
