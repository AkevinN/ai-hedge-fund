from __future__ import annotations

from .portfolio import Portfolio
from .types import ActionLiteral, Action


class TradeExecutor:
    """针对 Portfolio 执行交易，使用与 Backtester 相同的语义。"""

    def execute_trade(
        self,
        ticker: str,
        action: ActionLiteral,
        quantity: float,
        current_price: float,
        portfolio: Portfolio,
    ) -> int:
        if quantity is None or quantity <= 0:
            return 0

        # 如果提供了字符串，则强制转换为枚举
        try:
            action_enum = Action(action) if not isinstance(action, Action) else action
        except Exception:
            action_enum = Action.HOLD

        if action_enum == Action.BUY:
            return portfolio.apply_long_buy(ticker, int(quantity), float(current_price))
        if action_enum == Action.SELL:
            return portfolio.apply_long_sell(ticker, int(quantity), float(current_price))
        if action_enum == Action.SHORT:
            return portfolio.apply_short_open(ticker, int(quantity), float(current_price))
        if action_enum == Action.COVER:
            return portfolio.apply_short_cover(ticker, int(quantity), float(current_price))

        # 持有或未知操作
        return 0


