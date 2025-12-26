"""
国内金融数据 API 封装模块
基于 akshare 实现A股数据获取，提供统一的数据接口
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Literal
import logging

# 将akshare导入移到模块级别，方便测试mock
try:
    import akshare as ak
    _akshare_available = True
except ImportError:
    _akshare_available = False
    ak = None

from src.data.cn.cache import get_cn_cache
from src.data.cn.models import (
    CNStockPrice,
    CNStockInfo,
    CNFinancialData,
    CNStockBasic,
    CNIndexPrice,
)

logger = logging.getLogger(__name__)

# 全局缓存实例
_cache = get_cn_cache()


def _safe_float(value, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if pd.isna(value) or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """安全转换为整数"""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _format_symbol(symbol: str, market: str = "auto") -> str:
    """
    格式化股票代码
    
    Args:
        symbol: 股票代码，如 '000001' 或 '600000'
        market: 市场类型，'sh'/'sz'/'auto'
    
    Returns:
        格式化后的代码
    """
    symbol = symbol.strip().replace(" ", "")
    
    # 移除可能的前缀
    if symbol.startswith(("sh", "sz", "SH", "SZ")):
        symbol = symbol[2:]
    
    return symbol


def _get_market_prefix(symbol: str) -> str:
    """根据股票代码判断市场前缀"""
    if symbol.startswith(("6", "5", "9")):
        return "sh"
    elif symbol.startswith(("0", "1", "2", "3")):
        return "sz"
    elif symbol.startswith("4") or symbol.startswith("8"):
        return "bj"  # 北交所
    return "sz"


def get_cn_stock_prices(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: Literal["qfq", "hfq", ""] = "qfq",
) -> list[CNStockPrice]:
    """
    获取A股股票历史价格数据
    
    Args:
        symbol: 股票代码，如 '000001'
        start_date: 开始日期，格式 'YYYY-MM-DD'
        end_date: 结束日期，格式 'YYYY-MM-DD'
        adjust: 复权类型，'qfq'前复权，'hfq'后复权，''不复权
    
    Returns:
        股票价格数据列表
    
    Example:
        >>> prices = get_cn_stock_prices("000001", "2024-01-01", "2024-12-01")
    """
    symbol = _format_symbol(symbol)
    cache_key_suffix = f"_{adjust}" if adjust else ""
    
    # 尝试从缓存获取
    cached_data = _cache.get_prices(f"{symbol}{cache_key_suffix}", start_date, end_date)
    if cached_data:
        return [CNStockPrice(**item) for item in cached_data]
    
    if not _akshare_available:
        logger.error("akshare 未安装，请运行: pip install akshare")
        return []
    
    try:
        # 使用东方财富数据源
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust=adjust,
        )
        
        if df is None or df.empty:
            logger.warning(f"未获取到股票 {symbol} 的价格数据")
            return []
        
        prices = []
        for _, row in df.iterrows():
            try:
                price = CNStockPrice(
                    symbol=symbol,
                    name=str(row.get("股票名称", "")),
                    date=str(row["日期"]) if "日期" in row else str(row.name),
                    open=_safe_float(row.get("开盘", row.get("open"))),
                    close=_safe_float(row.get("收盘", row.get("close"))),
                    high=_safe_float(row.get("最高", row.get("high"))),
                    low=_safe_float(row.get("最低", row.get("low"))),
                    volume=_safe_float(row.get("成交量", row.get("volume", 0))),
                    amount=_safe_float(row.get("成交额", row.get("amount", 0))),
                    amplitude=_safe_float(row.get("振幅", None)),
                    change_pct=_safe_float(row.get("涨跌幅", None)),
                    change_amount=_safe_float(row.get("涨跌额", None)),
                    turnover_rate=_safe_float(row.get("换手率", None)),
                )
                prices.append(price)
            except Exception as e:
                logger.warning(f"解析价格数据失败: {e}")
                continue
        
        # 缓存结果
        if prices:
            _cache.set_prices(
                f"{symbol}{cache_key_suffix}",
                start_date,
                end_date,
                [p.model_dump() for p in prices]
            )
        
        return prices
        
    except Exception as e:
        logger.error(f"获取股票价格数据失败: {e}")
        return []


def get_cn_stock_info(symbol: str) -> Optional[CNStockInfo]:
    """
    获取A股股票基本信息
    
    Args:
        symbol: 股票代码
    
    Returns:
        股票基本信息，获取失败返回 None
    """
    symbol = _format_symbol(symbol)
    
    # 尝试从缓存获取
    cached_data = _cache.get_stock_info(symbol)
    if cached_data:
        return CNStockInfo(**cached_data)
    
    if not _akshare_available:
        logger.error("akshare 未安装，请运行: pip install akshare")
        return None
    
    try:
        # 获取个股信息
        df = ak.stock_individual_info_em(symbol=symbol)
        
        if df is None or df.empty:
            logger.warning(f"未获取到股票 {symbol} 的基本信息")
            return None
        
        # 将DataFrame转换为字典
        info_dict = {}
        for _, row in df.iterrows():
            key = str(row.iloc[0]) if len(row) > 0 else ""
            value = row.iloc[1] if len(row) > 1 else None
            info_dict[key] = value
        
        # 判断市场类型
        market = "主板"
        if symbol.startswith("3"):
            market = "创业板"
        elif symbol.startswith("68"):
            market = "科创板"
        elif symbol.startswith(("4", "8")):
            market = "北交所"
        
        stock_info = CNStockInfo(
            symbol=symbol,
            name=str(info_dict.get("股票简称", "")),
            industry=str(info_dict.get("行业", "")) if info_dict.get("行业") else None,
            sector=str(info_dict.get("板块", "")) if info_dict.get("板块") else None,
            market=market,
            list_date=str(info_dict.get("上市时间", "")) if info_dict.get("上市时间") else None,
            total_share=_safe_float(info_dict.get("总股本", None)),
            float_share=_safe_float(info_dict.get("流通股", None)),
            total_market_cap=_safe_float(info_dict.get("总市值", None)),
            float_market_cap=_safe_float(info_dict.get("流通市值", None)),
            pe_ratio=_safe_float(info_dict.get("市盈率(动态)", None)),
            pb_ratio=_safe_float(info_dict.get("市净率", None)),
        )
        
        # 缓存结果
        _cache.set_stock_info(symbol, stock_info.model_dump())
        
        return stock_info
        
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        return None


def get_cn_financial_data(
    symbol: str,
    report_type: Literal["yearly", "quarterly"] = "quarterly",
    limit: int = 8,
) -> list[CNFinancialData]:
    """
    获取A股财务数据
    
    Args:
        symbol: 股票代码
        report_type: 报告类型，'yearly'年报，'quarterly'季报
        limit: 返回记录数量限制
    
    Returns:
        财务数据列表
    """
    symbol = _format_symbol(symbol)
    
    # 尝试从缓存获取
    cached_data = _cache.get_financial_data(symbol, report_type)
    if cached_data:
        return [CNFinancialData(**item) for item in cached_data[:limit]]
    
    if not _akshare_available:
        logger.error("akshare 未安装，请运行: pip install akshare")
        return []
    
    try:
        financial_list = []
        
        # 获取主要财务指标
        try:
            df_indicator = ak.stock_financial_analysis_indicator(symbol=symbol)
            if df_indicator is not None and not df_indicator.empty:
                for _, row in df_indicator.head(limit).iterrows():
                    try:
                        report_date = str(row.get("日期", ""))
                        
                        # 判断报告类型
                        rt = ""
                        if report_date.endswith("-12-31"):
                            rt = "年报"
                        elif report_date.endswith("-06-30"):
                            rt = "中报"
                        elif report_date.endswith("-03-31"):
                            rt = "一季报"
                        elif report_date.endswith("-09-30"):
                            rt = "三季报"
                        
                        financial = CNFinancialData(
                            symbol=symbol,
                            report_date=report_date,
                            report_type=rt,
                            roe=_safe_float(row.get("净资产收益率(%)", None)),
                            gross_margin=_safe_float(row.get("销售毛利率(%)", None)),
                            net_margin=_safe_float(row.get("销售净利率(%)", None)),
                            current_ratio=_safe_float(row.get("流动比率", None)),
                            quick_ratio=_safe_float(row.get("速动比率", None)),
                            debt_ratio=_safe_float(row.get("资产负债率(%)", None)),
                            inventory_turnover=_safe_float(row.get("存货周转率(次)", None)),
                            receivable_turnover=_safe_float(row.get("应收账款周转率(次)", None)),
                            eps=_safe_float(row.get("摊薄每股收益(元)", None)),
                            bps=_safe_float(row.get("每股净资产(元)", None)),
                            cfps=_safe_float(row.get("每股现金流量净额(元)", None)),
                        )
                        financial_list.append(financial)
                    except Exception as e:
                        logger.warning(f"解析财务数据失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"获取财务指标失败: {e}")
        
        # 尝试补充利润表数据
        try:
            df_profit = ak.stock_profit_sheet_by_report_em(symbol=symbol)
            if df_profit is not None and not df_profit.empty:
                # 按报告期匹配补充数据
                profit_dict = {}
                for _, row in df_profit.iterrows():
                    report_date = str(row.get("REPORT_DATE", ""))[:10]
                    profit_dict[report_date] = row
                
                for financial in financial_list:
                    if financial.report_date in profit_dict:
                        row = profit_dict[financial.report_date]
                        if financial.total_revenue is None:
                            financial.total_revenue = _safe_float(row.get("TOTAL_OPERATE_INCOME", None))
                        if financial.operating_profit is None:
                            financial.operating_profit = _safe_float(row.get("OPERATE_PROFIT", None))
                        if financial.net_profit is None:
                            financial.net_profit = _safe_float(row.get("NETPROFIT", None))
        except Exception as e:
            logger.debug(f"获取利润表数据失败（非必要）: {e}")
        
        # 缓存结果
        if financial_list:
            _cache.set_financial_data(
                symbol,
                [f.model_dump() for f in financial_list],
                report_type
            )
        
        return financial_list[:limit]
        
    except Exception as e:
        logger.error(f"获取财务数据失败: {e}")
        return []


def get_cn_stock_list(
    market: Literal["all", "sh", "sz", "bj", "cyb", "kcb"] = "all"
) -> list[CNStockBasic]:
    """
    获取A股股票列表
    
    Args:
        market: 市场类型
            - 'all': 全部A股
            - 'sh': 上海主板
            - 'sz': 深圳主板
            - 'bj': 北交所
            - 'cyb': 创业板
            - 'kcb': 科创板
    
    Returns:
        股票基础信息列表
    """
    # 尝试从缓存获取
    cached_data = _cache.get_stock_list(market)
    if cached_data:
        return [CNStockBasic(**item) for item in cached_data]
    
    if not _akshare_available:
        logger.error("akshare 未安装，请运行: pip install akshare")
        return []
    
    try:
        # 获取实时行情数据（包含股票列表）
        df = ak.stock_zh_a_spot_em()
        
        if df is None or df.empty:
            logger.warning("未获取到股票列表数据")
            return []
        
        stock_list = []
        for _, row in df.iterrows():
            try:
                symbol = str(row.get("代码", ""))
                name = str(row.get("名称", ""))
                
                # 根据代码判断市场
                if symbol.startswith("6"):
                    stock_market = "sh"
                elif symbol.startswith("0") or symbol.startswith("3"):
                    stock_market = "sz"
                elif symbol.startswith(("4", "8")):
                    stock_market = "bj"
                else:
                    stock_market = "other"
                
                # 细分市场
                if symbol.startswith("3"):
                    detailed_market = "cyb"  # 创业板
                elif symbol.startswith("68"):
                    detailed_market = "kcb"  # 科创板
                else:
                    detailed_market = stock_market
                
                # 市场筛选
                if market != "all":
                    if market == "cyb" and not symbol.startswith("3"):
                        continue
                    elif market == "kcb" and not symbol.startswith("68"):
                        continue
                    elif market == "sh" and not symbol.startswith("6"):
                        continue
                    elif market == "sz" and not (symbol.startswith("0") or symbol.startswith("3")):
                        continue
                    elif market == "bj" and not symbol.startswith(("4", "8")):
                        continue
                
                stock = CNStockBasic(
                    symbol=symbol,
                    name=name,
                    market=detailed_market,
                    list_status="L",  # 默认上市状态
                )
                stock_list.append(stock)
            except Exception as e:
                logger.warning(f"解析股票信息失败: {e}")
                continue
        
        # 缓存结果
        if stock_list:
            _cache.set_stock_list([s.model_dump() for s in stock_list], market)
        
        return stock_list
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return []


def get_cn_index_prices(
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[CNIndexPrice]:
    """
    获取A股指数历史数据
    
    Args:
        symbol: 指数代码
            - '000001': 上证指数
            - '399001': 深证成指
            - '399006': 创业板指
            - '000300': 沪深300
            - '000905': 中证500
        start_date: 开始日期，格式 'YYYY-MM-DD'
        end_date: 结束日期，格式 'YYYY-MM-DD'
    
    Returns:
        指数价格数据列表
    """
    symbol = _format_symbol(symbol)
    
    # 尝试从缓存获取
    cached_data = _cache.get_index_prices(symbol, start_date, end_date)
    if cached_data:
        return [CNIndexPrice(**item) for item in cached_data]
    
    if not _akshare_available:
        logger.error("akshare 未安装，请运行: pip install akshare")
        return []
    
    try:
        # 根据指数代码选择数据源
        if symbol.startswith("0"):
            # 上证指数
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
        elif symbol.startswith("3"):
            # 深证指数
            df = ak.stock_zh_index_daily(symbol=f"sz{symbol}")
        else:
            # 尝试两个市场
            try:
                df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
            except:
                df = ak.stock_zh_index_daily(symbol=f"sz{symbol}")
        
        if df is None or df.empty:
            logger.warning(f"未获取到指数 {symbol} 的数据")
            return []
        
        # 日期筛选
        df.index = pd.to_datetime(df.index)
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df.index >= start_dt) & (df.index <= end_dt)]
        
        prices = []
        for idx, row in df.iterrows():
            try:
                price = CNIndexPrice(
                    symbol=symbol,
                    name="",
                    date=idx.strftime("%Y-%m-%d"),
                    open=_safe_float(row.get("open")),
                    close=_safe_float(row.get("close")),
                    high=_safe_float(row.get("high")),
                    low=_safe_float(row.get("low")),
                    volume=_safe_float(row.get("volume", 0)),
                    amount=_safe_float(row.get("amount", 0)),
                )
                prices.append(price)
            except Exception as e:
                logger.warning(f"解析指数数据失败: {e}")
                continue
        
        # 缓存结果
        if prices:
            _cache.set_index_prices(
                symbol,
                start_date,
                end_date,
                [p.model_dump() for p in prices]
            )
        
        return prices
        
    except Exception as e:
        logger.error(f"获取指数数据失败: {e}")
        return []


# ========== 辅助函数 ==========

def cn_prices_to_df(prices: list[CNStockPrice]) -> pd.DataFrame:
    """将股票价格列表转换为 DataFrame"""
    if not prices:
        return pd.DataFrame()
    
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["date"])
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)
    return df


def cn_index_prices_to_df(prices: list[CNIndexPrice]) -> pd.DataFrame:
    """将指数价格列表转换为 DataFrame"""
    if not prices:
        return pd.DataFrame()
    
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["date"])
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)
    return df


def get_cn_price_data(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "qfq"
) -> pd.DataFrame:
    """
    获取股票价格数据并返回 DataFrame
    
    与现有系统的 get_price_data 函数保持接口一致
    """
    prices = get_cn_stock_prices(symbol, start_date, end_date, adjust=adjust)
    return cn_prices_to_df(prices)
