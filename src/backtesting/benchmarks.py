from __future__ import annotations

import pandas as pd

from src.tools.api import get_price_data


class BenchmarkCalculator:
    def get_return_pct(self, ticker: str, start_date: str, end_date: str) -> float | None:
        """计算从 start_date 到 end_date 的股票简单买入持有收益率 %。

        收益率为 (last_close / first_close - 1) * 100，如果不可用则返回 None。
        """
        try:
            df = get_price_data(ticker, start_date, end_date)
            if df.empty:
                return None
            first_close = df.iloc[0]["close"]
            last_close = df.iloc[-1]["close"]
            if first_close is None or pd.isna(first_close):
                return None
            if last_close is None or pd.isna(last_close):
                # 尝试最后一个有效收盘价
                last_valid = df["close"].dropna()
                if last_valid.empty:
                    return None
                last_close = float(last_valid.iloc[-1])
            return (float(last_close) / float(first_close) - 1.0) * 100.0
        except Exception:
            return None


