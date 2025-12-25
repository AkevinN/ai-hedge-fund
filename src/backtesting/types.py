from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence, TypedDict, Literal
from enum import Enum

import pandas as pd


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"
    HOLD = "hold"

# 向后兼容别名
ActionLiteral = Literal["buy", "sell", "short", "cover", "hold"]


class PositionState(TypedDict):
    """表示投资组合中每个股票的持仓状态。"""

    long: int
    short: int
    long_cost_basis: float
    short_cost_basis: float
    short_margin_used: float


class TickerRealizedGains(TypedDict):
    """单个股票每侧的已实现盈亏。"""

    long: float
    short: float


class PortfolioSnapshot(TypedDict):
    """投资组合状态快照。

    该结构镜像了当前 Backtester 使用的现有字典，
    以确保在增量重构期间的即插即用兼容性。
    """

    cash: float
    margin_used: float
    margin_requirement: float
    positions: Dict[str, PositionState]
    realized_gains: Dict[str, TickerRealizedGains]


# DataFrame 别名用于接口清晰
PriceDataFrame = pd.DataFrame


class AgentDecision(TypedDict):
    action: ActionLiteral
    quantity: float


AgentDecisions = Dict[str, AgentDecision]


# 分析师信号负载可能因 agent 而异；保持为松散字典
AnalystSignal = Dict[str, Any]
AgentSignals = Dict[str, Dict[str, AnalystSignal]]


class AgentOutput(TypedDict):
    decisions: AgentDecisions
    analyst_signals: AgentSignals


# 使用函数式风格允许带空格的键以镜像当前代码
PortfolioValuePoint = TypedDict(
    "PortfolioValuePoint",
    {
        "Date": datetime,
        "Portfolio Value": float,
        "Long Exposure": float,
        "Short Exposure": float,
        "Gross Exposure": float,
        "Net Exposure": float,
        "Long/Short Ratio": float,
    },
    total=False,
)


class PerformanceMetrics(TypedDict, total=False):
    """在权益曲线上计算的性能指标。

    键与 src/backtester.py 中的当前实现对齐。
    值是可选的，以支持随时间的渐进计算。
    """

    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    max_drawdown: Optional[float]
    max_drawdown_date: Optional[str]
    long_short_ratio: Optional[float]
    gross_exposure: Optional[float]
    net_exposure: Optional[float]


