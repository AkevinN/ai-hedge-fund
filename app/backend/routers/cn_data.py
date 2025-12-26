"""
国内金融数据查询 API 路由
提供 RESTful API 接口访问 A股数据
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal
from pydantic import BaseModel, Field
import logging

from src.data.cn.api import (
    get_cn_stock_prices,
    get_cn_stock_info,
    get_cn_financial_data,
    get_cn_stock_list,
    get_cn_index_prices,
    cn_prices_to_df,
)
from src.data.cn.models import (
    CNStockPrice,
    CNStockInfo,
    CNFinancialData,
    CNStockBasic,
    CNIndexPrice,
)
from src.data.cn.cleaner import CNDataCleaner, standardize_cn_symbol
from src.data.cn.cache import get_cn_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cn", tags=["国内金融数据"])


# ========== 响应模型 ==========

class StockPricesResponse(BaseModel):
    """股票价格响应"""
    symbol: str
    count: int
    prices: list[CNStockPrice]


class StockInfoResponse(BaseModel):
    """股票信息响应"""
    success: bool
    data: Optional[CNStockInfo] = None
    message: str = ""


class FinancialDataResponse(BaseModel):
    """财务数据响应"""
    symbol: str
    count: int
    financials: list[CNFinancialData]


class StockListResponse(BaseModel):
    """股票列表响应"""
    market: str
    count: int
    stocks: list[CNStockBasic]


class IndexPricesResponse(BaseModel):
    """指数价格响应"""
    symbol: str
    count: int
    prices: list[CNIndexPrice]


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    memory_cache: dict
    total_memory_items: int
    persistence_cache: Optional[dict] = None
    total_persistence_items: Optional[int] = None


# ========== API 路由 ==========

@router.get("/prices/{symbol}", response_model=StockPricesResponse)
async def get_stock_prices(
    symbol: str,
    start_date: str = Query(..., description="开始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式 YYYY-MM-DD"),
    adjust: Literal["qfq", "hfq", ""] = Query("qfq", description="复权类型：qfq前复权，hfq后复权，空字符串不复权"),
    clean: bool = Query(True, description="是否清洗数据"),
):
    """
    获取A股股票历史价格数据
    
    - **symbol**: 股票代码，如 000001
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **adjust**: 复权类型
    - **clean**: 是否清洗数据
    """
    try:
        # 标准化股票代码
        symbol = standardize_cn_symbol(symbol)
        
        # 验证日期
        cleaner = CNDataCleaner()
        start_date, end_date = cleaner.validate_date_range(start_date, end_date)
        
        # 获取数据
        prices = get_cn_stock_prices(symbol, start_date, end_date, adjust=adjust)
        
        if not prices:
            raise HTTPException(status_code=404, detail=f"未找到股票 {symbol} 的价格数据")
        
        # 清洗数据
        if clean:
            prices = cleaner.clean_price_data(prices)
        
        return StockPricesResponse(
            symbol=symbol,
            count=len(prices),
            prices=prices
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取股票价格失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/info/{symbol}", response_model=StockInfoResponse)
async def get_stock_info(symbol: str):
    """
    获取A股股票基本信息
    
    - **symbol**: 股票代码
    """
    try:
        symbol = standardize_cn_symbol(symbol)
        info = get_cn_stock_info(symbol)
        
        if info is None:
            return StockInfoResponse(
                success=False,
                message=f"未找到股票 {symbol} 的信息"
            )
        
        return StockInfoResponse(
            success=True,
            data=info,
            message="获取成功"
        )
        
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/financials/{symbol}", response_model=FinancialDataResponse)
async def get_financials(
    symbol: str,
    report_type: Literal["yearly", "quarterly"] = Query("quarterly", description="报告类型"),
    limit: int = Query(8, ge=1, le=20, description="返回记录数量"),
):
    """
    获取A股财务数据
    
    - **symbol**: 股票代码
    - **report_type**: 报告类型（yearly/quarterly）
    - **limit**: 返回记录数量
    """
    try:
        symbol = standardize_cn_symbol(symbol)
        financials = get_cn_financial_data(symbol, report_type=report_type, limit=limit)
        
        return FinancialDataResponse(
            symbol=symbol,
            count=len(financials),
            financials=financials
        )
        
    except Exception as e:
        logger.error(f"获取财务数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/stocks", response_model=StockListResponse)
async def get_stocks(
    market: Literal["all", "sh", "sz", "bj", "cyb", "kcb"] = Query("all", description="市场类型"),
):
    """
    获取A股股票列表
    
    - **market**: 市场类型
        - all: 全部
        - sh: 上海主板
        - sz: 深圳主板
        - bj: 北交所
        - cyb: 创业板
        - kcb: 科创板
    """
    try:
        stocks = get_cn_stock_list(market=market)
        
        return StockListResponse(
            market=market,
            count=len(stocks),
            stocks=stocks
        )
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/index/{symbol}", response_model=IndexPricesResponse)
async def get_index_prices(
    symbol: str,
    start_date: str = Query(..., description="开始日期"),
    end_date: str = Query(..., description="结束日期"),
):
    """
    获取A股指数历史数据
    
    - **symbol**: 指数代码
        - 000001: 上证指数
        - 399001: 深证成指
        - 399006: 创业板指
        - 000300: 沪深300
        - 000905: 中证500
    """
    try:
        cleaner = CNDataCleaner()
        start_date, end_date = cleaner.validate_date_range(start_date, end_date)
        
        prices = get_cn_index_prices(symbol, start_date, end_date)
        
        if not prices:
            raise HTTPException(status_code=404, detail=f"未找到指数 {symbol} 的数据")
        
        return IndexPricesResponse(
            symbol=symbol,
            count=len(prices),
            prices=prices
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取指数数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """获取缓存统计信息"""
    cache = get_cn_cache()
    stats = cache.get_cache_stats()
    return CacheStatsResponse(**stats)


@router.post("/cache/clear")
async def clear_cache(clear_persistence: bool = Query(False, description="是否清除持久化缓存")):
    """
    清除缓存
    
    - **clear_persistence**: 是否同时清除持久化缓存
    """
    cache = get_cn_cache()
    
    if clear_persistence:
        cache.clear_all_cache()
        return {"message": "已清除所有缓存（包括持久化缓存）"}
    else:
        cache.clear_memory_cache()
        return {"message": "已清除内存缓存"}
