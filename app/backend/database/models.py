from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from .connection import Base


class HedgeFundFlow(Base):
    """存储 React Flow 配置的表（节点、边、视口）"""
    __tablename__ = "hedge_fund_flows"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Flow 元数据
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # React Flow 状态
    nodes = Column(JSON, nullable=False)  # 以 JSON 格式存储 React Flow 节点
    edges = Column(JSON, nullable=False)  # 以 JSON 格式存储 React Flow 边
    viewport = Column(JSON, nullable=True)  # 存储视口状态（缩放、x、y）
    data = Column(JSON, nullable=True)  # 存储节点内部状态（股票代码、模型等）

    # 附加元数据
    is_template = Column(Boolean, default=False)  # 标记为模板以供重用
    tags = Column(JSON, nullable=True)  # 存储标签用于分类


class HedgeFundFlowRun(Base):
    """跟踪对冲基金 flow 单次执行运行的表"""
    __tablename__ = "hedge_fund_flow_runs"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("hedge_fund_flows.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 运行执行跟踪
    status = Column(String(50), nullable=False, default="IDLE")  # IDLE, IN_PROGRESS, COMPLETE, ERROR
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 运行配置
    trading_mode = Column(String(50), nullable=False, default="one-time")  # one-time, continuous, advisory
    schedule = Column(String(50), nullable=True)  # hourly, daily, weekly（用于连续模式）
    duration = Column(String(50), nullable=True)  # 1day, 1week, 1month（用于连续模式）

    # 运行数据
    request_data = Column(JSON, nullable=True)  # 存储请求参数（股票代码、agents、模型等）
    initial_portfolio = Column(JSON, nullable=True)  # 存储初始投资组合状态
    final_portfolio = Column(JSON, nullable=True)  # 存储最终投资组合状态
    results = Column(JSON, nullable=True)  # 存储运行的输出/结果
    error_message = Column(Text, nullable=True)  # 如果运行失败，存储错误详情

    # 元数据
    run_number = Column(Integer, nullable=False, default=1)  # 此 flow 的顺序运行编号


class HedgeFundFlowRunCycle(Base):
    """交易会话中的单个分析周期"""
    __tablename__ = "hedge_fund_flow_run_cycles"

    id = Column(Integer, primary_key=True, index=True)
    flow_run_id = Column(Integer, ForeignKey("hedge_fund_flow_runs.id"), nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False)  # 运行中的第 1, 2, 3 等周期

    # 时间记录
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 分析结果
    analyst_signals = Column(JSON, nullable=True)  # 所有 agent 的决策/信号
    trading_decisions = Column(JSON, nullable=True)  # 投资组合管理者的决策
    executed_trades = Column(JSON, nullable=True)  # 实际执行的交易（纸面交易）

    # 此周期后的投资组合状态
    portfolio_snapshot = Column(JSON, nullable=True)  # 现金、持仓、绩效指标

    # 此周期的绩效指标
    performance_metrics = Column(JSON, nullable=True)  # 收益率、夏普比率等

    # 执行跟踪
    status = Column(String(50), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, ERROR
    error_message = Column(Text, nullable=True)  # 如果周期失败，存储错误详情

    # 成本跟踪
    llm_calls_count = Column(Integer, nullable=True, default=0)  # LLM 调用次数
    api_calls_count = Column(Integer, nullable=True, default=0)  # 金融 API 调用次数
    estimated_cost = Column(String(20), nullable=True)  # 估计成本（美元）

    # 元数据
    trigger_reason = Column(String(100), nullable=True)  # scheduled, manual, market_event 等
    market_conditions = Column(JSON, nullable=True)  # 周期开始时的市场数据快照


class ApiKey(Base):
    """存储各种服务的 API 密钥的表"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # API key 详情
    provider = Column(String(100), nullable=False, unique=True, index=True)  # 例如："ANTHROPIC_API_KEY"
    key_value = Column(Text, nullable=False)  # 实际的 API key（生产环境中加密）
    is_active = Column(Boolean, default=True)  # 启用/禁用而不删除

    # 可选元数据
    description = Column(Text, nullable=True)  # 人类可读的描述
    last_used = Column(DateTime(timezone=True), nullable=True)  # 跟踪使用情况


 