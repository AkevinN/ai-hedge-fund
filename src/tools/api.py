import datetime
import os
import pandas as pd
import requests
import time

from src.data.cache import get_cache
from src.data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
    CompanyFactsResponse,
)

# 全局缓存实例
_cache = get_cache()


def _make_api_request(url: str, headers: dict, method: str = "GET", json_data: dict = None, max_retries: int = 3) -> requests.Response:
    """
    使用速率限制处理和适度退避进行 API 请求

    参数:
        url: 请求的 URL
        headers: 请求中包含的头部
        method: HTTP 方法 (GET 或 POST)
        json_data: POST 请求的 JSON 数据
        max_retries: 最大重试次数 (默认: 3)

    返回:
        requests.Response: 响应对象

    异常:
        Exception: 如果请求因非 429 错误失败
    """
    for attempt in range(max_retries + 1):  # +1 为初始尝试
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        else:
            response = requests.get(url, headers=headers)
        
        if response.status_code == 429 and attempt < max_retries:
            # 线性退避: 60秒, 90秒, 120秒, 150秒...
            delay = 60 + (30 * attempt)
            print(f"速率受限 (429). 尝试 {attempt + 1}/{max_retries + 1}. 等待 {delay}秒后重试...")
            time.sleep(delay)
            continue

        # 返回响应（无论成功、其他错误还是最终的 429）
        return response


def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> list[Price]:
    """从缓存或 API 获取价格数据"""
    # 创建包含所有参数的缓存键以确保精确匹配
    cache_key = f"{ticker}_{start_date}_{end_date}"

    # 首先检查缓存 - 简单精确匹配
    if cached_data := _cache.get_prices(cache_key):
        return [Price(**price) for price in cached_data]

    # 如果不在缓存中，则从 API 获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&interval_multiplier=1&start_date={start_date}&end_date={end_date}"
    response = _make_api_request(url, headers)
    if response.status_code != 200:
        return []

    # Parse response with Pydantic model
    try:
        price_response = PriceResponse(**response.json())
        prices = price_response.prices
    except:
        return []

    if not prices:
        return []

    # 使用全面的缓存键缓存结果
    _cache.set_prices(cache_key, [p.model_dump() for p in prices])
    return prices


def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[FinancialMetrics]:
    """从缓存或 API 获取财务指标"""
    # 创建包含所有参数的缓存键以确保精确匹配
    cache_key = f"{ticker}_{period}_{end_date}_{limit}"

    # 首先检查缓存 - 简单精确匹配
    if cached_data := _cache.get_financial_metrics(cache_key):
        return [FinancialMetrics(**metric) for metric in cached_data]

    # 如果不在缓存中，则从 API 获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = f"https://api.financialdatasets.ai/financial-metrics/?ticker={ticker}&report_period_lte={end_date}&limit={limit}&period={period}"
    response = _make_api_request(url, headers)
    if response.status_code != 200:
        return []

    # Parse response with Pydantic model
    try:
        metrics_response = FinancialMetricsResponse(**response.json())
        financial_metrics = metrics_response.financial_metrics
    except:
        return []

    if not financial_metrics:
        return []

    # 使用全面的缓存键将结果作为字典缓存
    _cache.set_financial_metrics(cache_key, [m.model_dump() for m in financial_metrics])
    return financial_metrics


def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[LineItem]:
    """从 API 获取行项目"""
    # 如果不在缓存中或数据不足，则从 API 获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = "https://api.financialdatasets.ai/financials/search/line-items"

    body = {
        "tickers": [ticker],
        "line_items": line_items,
        "end_date": end_date,
        "period": period,
        "limit": limit,
    }
    response = _make_api_request(url, headers, method="POST", json_data=body)
    if response.status_code != 200:
        return []
    
    try:
        data = response.json()
        response_model = LineItemResponse(**data)
        search_results = response_model.search_results
    except:
        return []
    if not search_results:
        return []

    # 缓存结果
    return search_results[:limit]


def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[InsiderTrade]:
    """从缓存或 API 获取内部交易"""
    # 创建包含所有参数的缓存键以确保精确匹配
    cache_key = f"{ticker}_{start_date or 'none'}_{end_date}_{limit}"

    # 首先检查缓存 - 简单精确匹配
    if cached_data := _cache.get_insider_trades(cache_key):
        return [InsiderTrade(**trade) for trade in cached_data]

    # 如果不在缓存中，则从 API 获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    all_trades = []
    current_end_date = end_date

    while True:
        url = f"https://api.financialdatasets.ai/insider-trades/?ticker={ticker}&filing_date_lte={current_end_date}"
        if start_date:
            url += f"&filing_date_gte={start_date}"
        url += f"&limit={limit}"

        response = _make_api_request(url, headers)
        if response.status_code != 200:
            break

        try:
            data = response.json()
            response_model = InsiderTradeResponse(**data)
            insider_trades = response_model.insider_trades
        except:
            break  # Parsing error, exit loop

        if not insider_trades:
            break

        all_trades.extend(insider_trades)

        # 只有在有 start_date 且得到完整页面时才继续分页
        if not start_date or len(insider_trades) < limit:
            break

        # 将 end_date 更新为当前批次中最旧的申报日期以进行下一次迭代
        current_end_date = min(trade.filing_date for trade in insider_trades).split("T")[0]

        # 如果我们已经达到或超过 start_date，可以停止
        if current_end_date <= start_date:
            break

    if not all_trades:
        return []

    # 使用全面的缓存键缓存结果
    _cache.set_insider_trades(cache_key, [trade.model_dump() for trade in all_trades])
    return all_trades


def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[CompanyNews]:
    """从缓存或 API 获取公司新闻"""
    # 创建包含所有参数的缓存键以确保精确匹配
    cache_key = f"{ticker}_{start_date or 'none'}_{end_date}_{limit}"

    # 首先检查缓存 - 简单精确匹配
    if cached_data := _cache.get_company_news(cache_key):
        return [CompanyNews(**news) for news in cached_data]

    # 如果不在缓存中，则从 API 获取
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    all_news = []
    current_end_date = end_date

    while True:
        url = f"https://api.financialdatasets.ai/news/?ticker={ticker}&end_date={current_end_date}"
        if start_date:
            url += f"&start_date={start_date}"
        url += f"&limit={limit}"

        response = _make_api_request(url, headers)
        if response.status_code != 200:
            break

        try:
            data = response.json()
            response_model = CompanyNewsResponse(**data)
            company_news = response_model.news
        except:
            break  # Parsing error, exit loop

        if not company_news:
            break

        all_news.extend(company_news)

        # 只有在有 start_date 且得到完整页面时才继续分页
        if not start_date or len(company_news) < limit:
            break

        # 将 end_date 更新为当前批次中最旧的日期以进行下一次迭代
        current_end_date = min(news.date for news in company_news).split("T")[0]

        # 如果我们已经达到或超过 start_date，可以停止
        if current_end_date <= start_date:
            break

    if not all_news:
        return []

    # 使用全面的缓存键缓存结果
    _cache.set_company_news(cache_key, [news.model_dump() for news in all_news])
    return all_news


def get_market_cap(
    ticker: str,
    end_date: str,
    api_key: str = None,
) -> float | None:
    """从 API 获取市值"""
    # 检查 end_date 是否为今天
    if end_date == datetime.datetime.now().strftime("%Y-%m-%d"):
        # 从公司事实 API 获取市值
        headers = {}
        financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if financial_api_key:
            headers["X-API-KEY"] = financial_api_key

        url = f"https://api.financialdatasets.ai/company/facts/?ticker={ticker}"
        response = _make_api_request(url, headers)
        if response.status_code != 200:
            print(f"获取公司事实时出错: {ticker} - {response.status_code}")
            return None

        data = response.json()
        response_model = CompanyFactsResponse(**data)
        return response_model.company_facts.market_cap

    financial_metrics = get_financial_metrics(ticker, end_date, api_key=api_key)
    if not financial_metrics:
        return None

    market_cap = financial_metrics[0].market_cap

    if not market_cap:
        return None

    return market_cap


def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    """将价格转换为 DataFrame"""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df


# 更新 get_price_data 函数以使用新函数
def get_price_data(ticker: str, start_date: str, end_date: str, api_key: str = None) -> pd.DataFrame:
    prices = get_prices(ticker, start_date, end_date, api_key=api_key)
    return prices_to_df(prices)
