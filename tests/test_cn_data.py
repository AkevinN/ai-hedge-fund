"""
国内金融数据模块测试
测试数据获取、清洗、缓存功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from src.data.cn.models import (
    CNStockPrice,
    CNStockInfo,
    CNFinancialData,
    CNStockBasic,
    CNIndexPrice,
    DataQualityFlag,
)
from src.data.cn.cache import CNDataCache, get_cn_cache
from src.data.cn.cleaner import CNDataCleaner, standardize_cn_symbol


class TestCNDataModels:
    """测试数据模型"""
    
    def test_cn_stock_price_model(self):
        """测试股票价格模型"""
        price = CNStockPrice(
            symbol="000001",
            name="平安银行",
            date="2024-01-15",
            open=10.5,
            close=10.8,
            high=11.0,
            low=10.3,
            volume=1000000,
            amount=10800000,
            change_pct=2.86,
        )
        
        assert price.symbol == "000001"
        assert price.close == 10.8
        assert price.change_pct == 2.86
    
    def test_cn_stock_info_model(self):
        """测试股票信息模型"""
        info = CNStockInfo(
            symbol="000001",
            name="平安银行",
            industry="银行",
            market="主板",
            pe_ratio=8.5,
            pb_ratio=0.6,
        )
        
        assert info.symbol == "000001"
        assert info.industry == "银行"
        assert info.market == "主板"
    
    def test_cn_financial_data_model(self):
        """测试财务数据模型"""
        financial = CNFinancialData(
            symbol="000001",
            report_date="2024-09-30",
            report_type="三季报",
            roe=12.5,
            gross_margin=35.2,
            debt_ratio=45.0,
        )
        
        assert financial.symbol == "000001"
        assert financial.roe == 12.5
        assert financial.report_type == "三季报"


class TestCNDataCache:
    """测试缓存功能"""
    
    def setup_method(self):
        """每个测试前重置缓存"""
        self.cache = CNDataCache(enable_persistence=False)
    
    def test_price_cache(self):
        """测试价格缓存"""
        test_data = [
            {"symbol": "000001", "date": "2024-01-15", "close": 10.8}
        ]
        
        # 设置缓存
        self.cache.set_prices("000001", "2024-01-01", "2024-01-31", test_data)
        
        # 获取缓存
        cached = self.cache.get_prices("000001", "2024-01-01", "2024-01-31")
        
        assert cached is not None
        assert len(cached) == 1
        assert cached[0]["close"] == 10.8
    
    def test_stock_info_cache(self):
        """测试股票信息缓存"""
        test_data = {"symbol": "000001", "name": "平安银行", "industry": "银行"}
        
        self.cache.set_stock_info("000001", test_data)
        cached = self.cache.get_stock_info("000001")
        
        assert cached is not None
        assert cached["name"] == "平安银行"
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        cached = self.cache.get_prices("999999", "2024-01-01", "2024-01-31")
        assert cached is None
    
    def test_cache_stats(self):
        """测试缓存统计"""
        self.cache.set_prices("000001", "2024-01-01", "2024-01-31", [{}])
        self.cache.set_stock_info("000001", {})
        
        stats = self.cache.get_cache_stats()
        
        assert stats["total_memory_items"] == 2
        assert stats["memory_cache"]["prices"] == 1
        assert stats["memory_cache"]["stock_info"] == 1


class TestCNDataCleaner:
    """测试数据清洗功能"""
    
    def setup_method(self):
        """每个测试前创建清洗器"""
        self.cleaner = CNDataCleaner()
    
    def test_standardize_symbol(self):
        """测试股票代码标准化"""
        assert standardize_cn_symbol("000001") == "000001"
        assert standardize_cn_symbol("sh600000") == "600000"
        assert standardize_cn_symbol("SZ000001") == "000001"
        assert standardize_cn_symbol("600000.SH") == "600000"
        assert standardize_cn_symbol("1") == "000001"
    
    def test_clean_price_data_missing_values(self):
        """测试清洗缺失值"""
        prices = [
            CNStockPrice(
                symbol="000001", date="2024-01-15",
                open=10.5, close=10.8, high=11.0, low=10.3, volume=1000000
            ),
            CNStockPrice(
                symbol="000001", date="2024-01-16",
                open=0, close=10.9, high=11.1, low=10.5, volume=1200000
            ),
        ]
        
        cleaned = self.cleaner.clean_price_data(prices, fill_missing=True)
        
        assert len(cleaned) == 2
        # 缺失的open应该被填充
        assert cleaned[1].open != 0
    
    def test_clean_price_data_invalid_high_low(self):
        """测试清洗无效的高低价"""
        prices = [
            CNStockPrice(
                symbol="000001", date="2024-01-15",
                open=10.5, close=10.8, high=10.0, low=11.0,  # high < low，无效
                volume=1000000
            ),
        ]
        
        cleaned = self.cleaner.clean_price_data(prices)
        
        assert len(cleaned) == 1
        # high和low应该被交换
        assert cleaned[0].high >= cleaned[0].low
    
    def test_clean_financial_data(self):
        """测试清洗财务数据"""
        financials = [
            CNFinancialData(
                symbol="000001",
                report_date="2024-09-30",
                roe=12.5,
                current_ratio=-1.0,  # 无效值
                debt_ratio=45.0,
            ),
        ]
        
        cleaned = self.cleaner.clean_financial_data(financials)
        
        assert len(cleaned) == 1
        # 无效的current_ratio应该被设为None
        assert cleaned[0].current_ratio is None
    
    def test_validate_date_range(self):
        """测试日期范围验证"""
        # 正常日期
        start, end = self.cleaner.validate_date_range("2024-01-01", "2024-12-31")
        assert start == "2024-01-01"
        assert end == "2024-12-31"
        
        # 日期顺序颠倒
        start, end = self.cleaner.validate_date_range("2024-12-31", "2024-01-01")
        assert start == "2024-01-01"
        assert end == "2024-12-31"
    
    def test_quality_report(self):
        """测试质量报告"""
        prices = [
            CNStockPrice(
                symbol="000001", date="2024-01-15",
                open=10.5, close=10.8, high=10.0, low=11.0,  # 无效
                volume=0  # 缺失
            ),
        ]
        
        self.cleaner.clean_price_data(prices)
        report = self.cleaner.get_quality_report()
        
        assert report["total_issues"] > 0
        assert "invalid" in report["by_type"] or "missing" in report["by_type"]


class TestCNDataAPI:
    """测试API功能（需要网络连接时使用mock）"""
    
    @patch('src.data.cn.api.ak')
    def test_get_cn_stock_prices_mock(self, mock_ak):
        """测试获取股票价格（mock）"""
        # 准备mock数据
        mock_df = pd.DataFrame({
            '日期': ['2024-01-15', '2024-01-16'],
            '股票名称': ['平安银行', '平安银行'],
            '开盘': [10.5, 10.8],
            '收盘': [10.8, 11.0],
            '最高': [11.0, 11.2],
            '最低': [10.3, 10.7],
            '成交量': [1000000, 1200000],
            '成交额': [10800000, 13200000],
            '振幅': [6.8, 4.6],
            '涨跌幅': [2.86, 1.85],
            '涨跌额': [0.3, 0.2],
            '换手率': [0.5, 0.6],
        })
        mock_ak.stock_zh_a_hist.return_value = mock_df
        
        from src.data.cn.api import get_cn_stock_prices
        
        # 清除缓存以确保调用API
        from src.data.cn.cache import get_cn_cache
        cache = get_cn_cache()
        cache.clear_memory_cache()
        
        prices = get_cn_stock_prices("000001", "2024-01-01", "2024-01-31")
        
        assert len(prices) == 2
        assert prices[0].symbol == "000001"
        assert prices[0].close == 10.8


# 集成测试（需要网络连接）
class TestCNDataIntegration:
    """集成测试 - 需要网络连接"""
    
    def test_get_real_stock_prices(self):
        """测试获取真实股票价格"""
        from src.data.cn.api import get_cn_stock_prices
        
        # 测试输入
        symbol = "000001"
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        # 输出测试信息
        print("=== 测试函数: get_cn_stock_prices ===")
        print("输入参数:")
        print(f"  symbol: {symbol}")
        print(f"  start_date: {start_date}")
        print(f"  end_date: {end_date}")
        
        # 调用被测试函数
        prices = get_cn_stock_prices(symbol, start_date, end_date)
        
        print("输出结果:")
        print(f"  数据类型: {type(prices)}")
        print(f"  数据长度: {len(prices)}")
        
        if prices:
            print(f"  第一条记录: symbol={prices[0].symbol}, date={prices[0].date}, close={prices[0].close}")
            print(f"  最后一条记录: symbol={prices[-1].symbol}, date={prices[-1].date}, close={prices[-1].close}")
        
        assert len(prices) > 0
        assert all(p.symbol == "000001" for p in prices)
    
    def test_get_real_stock_list(self):
        """测试获取真实股票列表"""
        from src.data.cn.api import get_cn_stock_list
        
        # 测试输入
        market = "all"
        
        # 输出测试信息
        print("=== 测试函数: get_cn_stock_list ===")
        print("输入参数:")
        print(f"  market: {market}")
        
        # 调用被测试函数
        stocks = get_cn_stock_list(market=market)
        
        print("输出结果:")
        print(f"  数据类型: {type(stocks)}")
        print(f"  数据长度: {len(stocks)}")
        
        if stocks:
            print(f"  前5条记录:")
            for i, stock in enumerate(stocks[:5]):
                print(f"    [{i+1}] {stock.symbol} - {stock.name} ({stock.market})")
        
        assert len(stocks) > 0
