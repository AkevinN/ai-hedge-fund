
from typing import Optional, List
from app.backend.models.schemas import PortfolioPosition


def create_portfolio(initial_cash: float, margin_requirement: float, tickers: list[str], portfolio_positions: Optional[List[PortfolioPosition]] = None) -> dict:
    # 初始化基础投资组合结构
    portfolio = {
        "cash": initial_cash,  # 初始现金金额
        "margin_requirement": margin_requirement,  # 初始保证金要求
        "margin_used": 0.0,  # 所有空头仓位的总保证金使用量
        "positions": {
            ticker: {
                "long": 0,  # 持有的多头股份数量
                "short": 0,  # 持有的空头股份数量
                "long_cost_basis": 0.0,  # 多头仓位的平均成本基础
                "short_cost_basis": 0.0,  # 卖空股份的平均价格
                "short_margin_used": 0.0,  # 该股票空头使用的保证金美元数
            }
            for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,  # 多头仓位的已实现收益
                "short": 0.0,  # 空头仓位的已实现收益
            }
            for ticker in tickers
        },
    }

    # 如果提供了投资组合仓位，则填充它们
    if portfolio_positions:
        for position in portfolio_positions:
            ticker = position.ticker
            quantity = position.quantity
            trade_price = position.trade_price

            # 确保股票代码存在于投资组合中（它应该来自股票代码列表）
            if ticker in portfolio["positions"]:
                if quantity > 0:
                    # 正数量表示多头仓位
                    portfolio["positions"][ticker]["long"] = quantity
                    portfolio["positions"][ticker]["long_cost_basis"] = trade_price
                elif quantity < 0:
                    # 负数量表示空头仓位
                    portfolio["positions"][ticker]["short"] = abs(quantity)
                    portfolio["positions"][ticker]["short_cost_basis"] = trade_price
                    # 计算空头仓位使用的保证金
                    portfolio["positions"][ticker]["short_margin_used"] = abs(quantity) * trade_price * margin_requirement
                    portfolio["margin_used"] += portfolio["positions"][ticker]["short_margin_used"]

    return portfolio