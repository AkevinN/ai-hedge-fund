"""
国内金融数据清洗模块
提供数据验证、清洗、标准化功能
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Any
import logging

from src.data.cn.models import (
    CNStockPrice,
    CNFinancialData,
    DataQualityFlag,
)

logger = logging.getLogger(__name__)


class CNDataCleaner:
    """国内金融数据清洗器"""
    
    def __init__(self):
        self.quality_flags: list[DataQualityFlag] = []
    
    def clean_price_data(
        self,
        prices: list[CNStockPrice],
        fill_missing: bool = True,
        remove_outliers: bool = True,
        outlier_threshold: float = 0.2,
    ) -> list[CNStockPrice]:
        """
        清洗股票价格数据
        
        Args:
            prices: 原始价格数据
            fill_missing: 是否填充缺失值
            remove_outliers: 是否移除异常值
            outlier_threshold: 异常值阈值（涨跌幅超过此值视为异常）
        
        Returns:
            清洗后的价格数据
        """
        if not prices:
            return prices
        
        self.quality_flags.clear()
        cleaned = []
        
        # 转换为DataFrame便于处理
        df = pd.DataFrame([p.model_dump() for p in prices])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 1. 检查并处理缺失值
        for col in ['open', 'close', 'high', 'low', 'volume']:
            missing_mask = df[col].isna() | (df[col] == 0)
            if missing_mask.any():
                for idx in df[missing_mask].index:
                    self.quality_flags.append(DataQualityFlag(
                        field=col,
                        issue="missing",
                        original_value=str(df.loc[idx, col]),
                        confidence=0.8
                    ))
                
                if fill_missing:
                    # 使用前向填充
                    df[col] = df[col].replace(0, np.nan).ffill()
        
        # 2. 检查价格逻辑一致性 (high >= low, high >= open/close, low <= open/close)
        for idx, row in df.iterrows():
            if row['high'] < row['low']:
                self.quality_flags.append(DataQualityFlag(
                    field="high/low",
                    issue="invalid",
                    original_value=f"high={row['high']}, low={row['low']}",
                    confidence=0.5
                ))
                # 交换high和low
                df.loc[idx, 'high'], df.loc[idx, 'low'] = row['low'], row['high']
            
            if row['high'] < max(row['open'], row['close']):
                df.loc[idx, 'high'] = max(row['open'], row['close'])
            
            if row['low'] > min(row['open'], row['close']):
                df.loc[idx, 'low'] = min(row['open'], row['close'])
        
        # 3. 检测异常涨跌幅
        if remove_outliers and len(df) > 1:
            df['pct_change'] = df['close'].pct_change()
            
            for idx, row in df.iterrows():
                if pd.notna(row['pct_change']) and abs(row['pct_change']) > outlier_threshold:
                    # A股涨跌停限制通常为10%，科创板/创业板为20%
                    # 超过阈值可能是数据错误或特殊情况
                    self.quality_flags.append(DataQualityFlag(
                        field="close",
                        issue="outlier",
                        original_value=f"涨跌幅={row['pct_change']:.2%}",
                        confidence=0.6
                    ))
            
            df = df.drop(columns=['pct_change'])
        
        # 4. 转换回模型列表
        for _, row in df.iterrows():
            try:
                price = CNStockPrice(
                    symbol=row['symbol'],
                    name=row.get('name', ''),
                    date=row['date'].strftime('%Y-%m-%d'),
                    open=float(row['open']),
                    close=float(row['close']),
                    high=float(row['high']),
                    low=float(row['low']),
                    volume=float(row['volume']),
                    amount=float(row.get('amount', 0)),
                    amplitude=float(row['amplitude']) if pd.notna(row.get('amplitude')) else None,
                    change_pct=float(row['change_pct']) if pd.notna(row.get('change_pct')) else None,
                    change_amount=float(row['change_amount']) if pd.notna(row.get('change_amount')) else None,
                    turnover_rate=float(row['turnover_rate']) if pd.notna(row.get('turnover_rate')) else None,
                )
                cleaned.append(price)
            except Exception as e:
                logger.warning(f"数据转换失败: {e}")
                continue
        
        return cleaned
    
    def clean_financial_data(
        self,
        financials: list[CNFinancialData],
    ) -> list[CNFinancialData]:
        """
        清洗财务数据
        
        Args:
            financials: 原始财务数据
        
        Returns:
            清洗后的财务数据
        """
        if not financials:
            return financials
        
        self.quality_flags.clear()
        cleaned = []
        
        for fin in financials:
            fin_dict = fin.model_dump()
            
            # 1. 验证比率类指标范围
            ratio_fields = ['roe', 'roa', 'gross_margin', 'net_margin', 'debt_ratio']
            for field in ratio_fields:
                value = fin_dict.get(field)
                if value is not None:
                    # 极端值检查（如ROE超过100%或低于-100%可能有问题）
                    if abs(value) > 200:
                        self.quality_flags.append(DataQualityFlag(
                            field=field,
                            issue="outlier",
                            original_value=str(value),
                            confidence=0.7
                        ))
            
            # 2. 验证流动比率、速动比率
            if fin_dict.get('current_ratio') is not None:
                if fin_dict['current_ratio'] < 0:
                    self.quality_flags.append(DataQualityFlag(
                        field="current_ratio",
                        issue="invalid",
                        original_value=str(fin_dict['current_ratio']),
                        confidence=0.5
                    ))
                    fin_dict['current_ratio'] = None
            
            # 3. 验证资产负债率
            if fin_dict.get('debt_ratio') is not None:
                if fin_dict['debt_ratio'] < 0 or fin_dict['debt_ratio'] > 100:
                    self.quality_flags.append(DataQualityFlag(
                        field="debt_ratio",
                        issue="outlier",
                        original_value=str(fin_dict['debt_ratio']),
                        confidence=0.6
                    ))
            
            try:
                cleaned.append(CNFinancialData(**fin_dict))
            except Exception as e:
                logger.warning(f"财务数据清洗失败: {e}")
                continue
        
        return cleaned
    
    def standardize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码格式
        
        Args:
            symbol: 原始股票代码
        
        Returns:
            标准化后的6位数字代码
        """
        symbol = str(symbol).strip()
        
        # 移除常见前缀
        prefixes = ['sh', 'sz', 'bj', 'SH', 'SZ', 'BJ', '1', 'A']
        for prefix in prefixes:
            if symbol.startswith(prefix) and len(symbol) > 6:
                symbol = symbol[len(prefix):]
        
        # 移除后缀
        suffixes = ['.SH', '.SZ', '.BJ', '.SS', '.XSHG', '.XSHE']
        for suffix in suffixes:
            if symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
        
        # 补齐到6位
        symbol = symbol.zfill(6)
        
        return symbol
    
    def validate_date_range(
        self,
        start_date: str,
        end_date: str,
    ) -> tuple[str, str]:
        """
        验证并标准化日期范围
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            标准化后的(start_date, end_date)
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            # 尝试其他格式
            for fmt in ["%Y%m%d", "%Y/%m/%d", "%d-%m-%Y"]:
                try:
                    start = datetime.strptime(start_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"无法解析开始日期: {start_date}")
        
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            for fmt in ["%Y%m%d", "%Y/%m/%d", "%d-%m-%Y"]:
                try:
                    end = datetime.strptime(end_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"无法解析结束日期: {end_date}")
        
        # 确保start <= end
        if start > end:
            start, end = end, start
        
        # 确保不超过当前日期
        today = datetime.now()
        if end > today:
            end = today
        
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    
    def get_quality_report(self) -> dict:
        """
        获取数据质量报告
        
        Returns:
            质量报告字典
        """
        if not self.quality_flags:
            return {
                "total_issues": 0,
                "by_type": {},
                "by_field": {},
                "details": []
            }
        
        by_type = {}
        by_field = {}
        
        for flag in self.quality_flags:
            # 按问题类型统计
            by_type[flag.issue] = by_type.get(flag.issue, 0) + 1
            # 按字段统计
            by_field[flag.field] = by_field.get(flag.field, 0) + 1
        
        return {
            "total_issues": len(self.quality_flags),
            "by_type": by_type,
            "by_field": by_field,
            "details": [f.model_dump() for f in self.quality_flags]
        }


# 便捷函数
def clean_cn_prices(prices: list[CNStockPrice], **kwargs) -> list[CNStockPrice]:
    """清洗股票价格数据的便捷函数"""
    cleaner = CNDataCleaner()
    return cleaner.clean_price_data(prices, **kwargs)


def clean_cn_financials(financials: list[CNFinancialData]) -> list[CNFinancialData]:
    """清洗财务数据的便捷函数"""
    cleaner = CNDataCleaner()
    return cleaner.clean_financial_data(financials)


def standardize_cn_symbol(symbol: str) -> str:
    """标准化股票代码的便捷函数"""
    cleaner = CNDataCleaner()
    return cleaner.standardize_symbol(symbol)
