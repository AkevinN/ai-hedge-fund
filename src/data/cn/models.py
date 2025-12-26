"""
国内金融数据模型定义
基于 Pydantic 实现数据验证和序列化
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class CNStockPrice(BaseModel):
    """A股股票价格数据模型"""
    symbol: str = Field(..., description="股票代码，如 '000001'")
    name: str = Field(default="", description="股票名称")
    date: str = Field(..., description="交易日期，格式 YYYY-MM-DD")
    open: float = Field(..., description="开盘价")
    close: float = Field(..., description="收盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    volume: float = Field(..., description="成交量（股）")
    amount: float = Field(default=0.0, description="成交额（元）")
    amplitude: Optional[float] = Field(default=None, description="振幅（%）")
    change_pct: Optional[float] = Field(default=None, description="涨跌幅（%）")
    change_amount: Optional[float] = Field(default=None, description="涨跌额")
    turnover_rate: Optional[float] = Field(default=None, description="换手率（%）")


class CNStockPriceResponse(BaseModel):
    """股票价格响应模型"""
    symbol: str
    prices: list[CNStockPrice]


class CNStockInfo(BaseModel):
    """A股股票基本信息模型"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(default=None, description="所属行业")
    sector: Optional[str] = Field(default=None, description="所属板块")
    market: str = Field(default="A股", description="市场类型：主板/创业板/科创板")
    list_date: Optional[str] = Field(default=None, description="上市日期")
    total_share: Optional[float] = Field(default=None, description="总股本（股）")
    float_share: Optional[float] = Field(default=None, description="流通股本（股）")
    total_market_cap: Optional[float] = Field(default=None, description="总市值（元）")
    float_market_cap: Optional[float] = Field(default=None, description="流通市值（元）")
    pe_ratio: Optional[float] = Field(default=None, description="市盈率（动态）")
    pb_ratio: Optional[float] = Field(default=None, description="市净率")


class CNStockBasic(BaseModel):
    """A股股票列表基础信息"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: str = Field(default="", description="市场类型")
    list_status: str = Field(default="L", description="上市状态：L上市 D退市 P暂停上市")


class CNFinancialData(BaseModel):
    """A股财务数据模型"""
    symbol: str = Field(..., description="股票代码")
    report_date: str = Field(..., description="报告期，如 '2024-09-30'")
    report_type: str = Field(default="", description="报告类型：年报/中报/一季报/三季报")
    
    # 盈利能力指标
    roe: Optional[float] = Field(default=None, description="净资产收益率（%）")
    roa: Optional[float] = Field(default=None, description="总资产收益率（%）")
    gross_margin: Optional[float] = Field(default=None, description="毛利率（%）")
    net_margin: Optional[float] = Field(default=None, description="净利率（%）")
    
    # 成长能力指标
    revenue_yoy: Optional[float] = Field(default=None, description="营收同比增长率（%）")
    profit_yoy: Optional[float] = Field(default=None, description="净利润同比增长率（%）")
    
    # 偿债能力指标
    current_ratio: Optional[float] = Field(default=None, description="流动比率")
    quick_ratio: Optional[float] = Field(default=None, description="速动比率")
    debt_ratio: Optional[float] = Field(default=None, description="资产负债率（%）")
    
    # 运营能力指标
    inventory_turnover: Optional[float] = Field(default=None, description="存货周转率")
    receivable_turnover: Optional[float] = Field(default=None, description="应收账款周转率")
    
    # 核心财务数据
    total_revenue: Optional[float] = Field(default=None, description="营业总收入（元）")
    operating_profit: Optional[float] = Field(default=None, description="营业利润（元）")
    net_profit: Optional[float] = Field(default=None, description="净利润（元）")
    total_assets: Optional[float] = Field(default=None, description="总资产（元）")
    total_liabilities: Optional[float] = Field(default=None, description="总负债（元）")
    shareholders_equity: Optional[float] = Field(default=None, description="股东权益（元）")
    
    # 每股指标
    eps: Optional[float] = Field(default=None, description="每股收益（元）")
    bps: Optional[float] = Field(default=None, description="每股净资产（元）")
    cfps: Optional[float] = Field(default=None, description="每股现金流（元）")


class CNFinancialDataResponse(BaseModel):
    """财务数据响应模型"""
    symbol: str
    financial_data: list[CNFinancialData]


class CNIndexPrice(BaseModel):
    """A股指数价格数据模型"""
    symbol: str = Field(..., description="指数代码，如 '000001' (上证指数)")
    name: str = Field(default="", description="指数名称")
    date: str = Field(..., description="交易日期，格式 YYYY-MM-DD")
    open: float = Field(..., description="开盘点位")
    close: float = Field(..., description="收盘点位")
    high: float = Field(..., description="最高点位")
    low: float = Field(..., description="最低点位")
    volume: float = Field(..., description="成交量（手）")
    amount: float = Field(default=0.0, description="成交额（元）")
    change_pct: Optional[float] = Field(default=None, description="涨跌幅（%）")


class CNIndexPriceResponse(BaseModel):
    """指数价格响应模型"""
    symbol: str
    prices: list[CNIndexPrice]


# 数据质量标记
class DataQualityFlag(BaseModel):
    """数据质量标记"""
    field: str = Field(..., description="字段名")
    issue: str = Field(..., description="问题类型：missing/invalid/outlier")
    original_value: Optional[str] = Field(default=None, description="原始值")
    corrected_value: Optional[str] = Field(default=None, description="修正值")
    confidence: float = Field(default=1.0, description="数据置信度 0-1")
