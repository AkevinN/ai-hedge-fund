"""
国内金融数据缓存模块
提供内存缓存和可选的持久化缓存支持
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any


class CNDataCache:
    """国内金融数据缓存管理器"""
    
    def __init__(self, cache_dir: Optional[str] = None, enable_persistence: bool = True):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 持久化缓存目录，默认为项目根目录下的 .cache/cn_data
            enable_persistence: 是否启用持久化缓存
        """
        self._memory_cache: dict[str, dict[str, Any]] = {
            "prices": {},
            "stock_info": {},
            "financial_data": {},
            "stock_list": {},
            "index_prices": {},
        }
        self._cache_timestamps: dict[str, datetime] = {}
        self._enable_persistence = enable_persistence
        
        if enable_persistence:
            if cache_dir:
                self._cache_dir = Path(cache_dir)
            else:
                self._cache_dir = Path(__file__).parent.parent.parent.parent / ".cache" / "cn_data"
            self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_cache_key(self, *args) -> str:
        """生成缓存键"""
        key_str = "_".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def _is_cache_valid(self, cache_key: str, max_age_hours: int = 24) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache_timestamps:
            return False
        age = datetime.now() - self._cache_timestamps[cache_key]
        return age < timedelta(hours=max_age_hours)
    
    def _get_persistence_path(self, cache_type: str, cache_key: str) -> Path:
        """获取持久化文件路径"""
        return self._cache_dir / cache_type / f"{cache_key}.json"
    
    def _load_from_persistence(self, cache_type: str, cache_key: str) -> Optional[Any]:
        """从持久化存储加载数据"""
        if not self._enable_persistence:
            return None
        
        file_path = self._get_persistence_path(cache_type, cache_key)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 检查缓存时间
                cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at > timedelta(hours=24):
                    return None
                return data.get("data")
        except (json.JSONDecodeError, IOError):
            return None
    
    def _save_to_persistence(self, cache_type: str, cache_key: str, data: Any) -> None:
        """保存数据到持久化存储"""
        if not self._enable_persistence:
            return
        
        file_path = self._get_persistence_path(cache_type, cache_key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "cached_at": datetime.now().isoformat(),
                    "data": data
                }, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"缓存写入失败: {e}")
    
    # ========== 股票价格缓存 ==========
    
    def get_prices(self, symbol: str, start_date: str, end_date: str) -> Optional[list[dict]]:
        """获取缓存的股票价格数据"""
        cache_key = self._generate_cache_key(symbol, start_date, end_date)
        
        # 优先从内存缓存获取
        if cache_key in self._memory_cache["prices"]:
            if self._is_cache_valid(f"prices_{cache_key}"):
                return self._memory_cache["prices"][cache_key]
        
        # 尝试从持久化缓存加载
        data = self._load_from_persistence("prices", cache_key)
        if data:
            self._memory_cache["prices"][cache_key] = data
            self._cache_timestamps[f"prices_{cache_key}"] = datetime.now()
            return data
        
        return None
    
    def set_prices(self, symbol: str, start_date: str, end_date: str, data: list[dict]) -> None:
        """缓存股票价格数据"""
        cache_key = self._generate_cache_key(symbol, start_date, end_date)
        self._memory_cache["prices"][cache_key] = data
        self._cache_timestamps[f"prices_{cache_key}"] = datetime.now()
        self._save_to_persistence("prices", cache_key, data)
    
    # ========== 股票信息缓存 ==========
    
    def get_stock_info(self, symbol: str) -> Optional[dict]:
        """获取缓存的股票信息"""
        cache_key = symbol
        
        if cache_key in self._memory_cache["stock_info"]:
            if self._is_cache_valid(f"stock_info_{cache_key}", max_age_hours=168):  # 7天
                return self._memory_cache["stock_info"][cache_key]
        
        data = self._load_from_persistence("stock_info", cache_key)
        if data:
            self._memory_cache["stock_info"][cache_key] = data
            self._cache_timestamps[f"stock_info_{cache_key}"] = datetime.now()
            return data
        
        return None
    
    def set_stock_info(self, symbol: str, data: dict) -> None:
        """缓存股票信息"""
        self._memory_cache["stock_info"][symbol] = data
        self._cache_timestamps[f"stock_info_{symbol}"] = datetime.now()
        self._save_to_persistence("stock_info", symbol, data)
    
    # ========== 财务数据缓存 ==========
    
    def get_financial_data(self, symbol: str, report_date: Optional[str] = None) -> Optional[list[dict]]:
        """获取缓存的财务数据"""
        cache_key = self._generate_cache_key(symbol, report_date or "latest")
        
        if cache_key in self._memory_cache["financial_data"]:
            if self._is_cache_valid(f"financial_data_{cache_key}", max_age_hours=72):  # 3天
                return self._memory_cache["financial_data"][cache_key]
        
        data = self._load_from_persistence("financial_data", cache_key)
        if data:
            self._memory_cache["financial_data"][cache_key] = data
            self._cache_timestamps[f"financial_data_{cache_key}"] = datetime.now()
            return data
        
        return None
    
    def set_financial_data(self, symbol: str, data: list[dict], report_date: Optional[str] = None) -> None:
        """缓存财务数据"""
        cache_key = self._generate_cache_key(symbol, report_date or "latest")
        self._memory_cache["financial_data"][cache_key] = data
        self._cache_timestamps[f"financial_data_{cache_key}"] = datetime.now()
        self._save_to_persistence("financial_data", cache_key, data)
    
    # ========== 股票列表缓存 ==========
    
    def get_stock_list(self, market: str = "all") -> Optional[list[dict]]:
        """获取缓存的股票列表"""
        cache_key = f"stock_list_{market}"
        
        if cache_key in self._memory_cache["stock_list"]:
            if self._is_cache_valid(cache_key, max_age_hours=24):
                return self._memory_cache["stock_list"][cache_key]
        
        data = self._load_from_persistence("stock_list", market)
        if data:
            self._memory_cache["stock_list"][cache_key] = data
            self._cache_timestamps[cache_key] = datetime.now()
            return data
        
        return None
    
    def set_stock_list(self, data: list[dict], market: str = "all") -> None:
        """缓存股票列表"""
        cache_key = f"stock_list_{market}"
        self._memory_cache["stock_list"][cache_key] = data
        self._cache_timestamps[cache_key] = datetime.now()
        self._save_to_persistence("stock_list", market, data)
    
    # ========== 指数价格缓存 ==========
    
    def get_index_prices(self, symbol: str, start_date: str, end_date: str) -> Optional[list[dict]]:
        """获取缓存的指数价格数据"""
        cache_key = self._generate_cache_key(symbol, start_date, end_date)
        
        if cache_key in self._memory_cache["index_prices"]:
            if self._is_cache_valid(f"index_prices_{cache_key}"):
                return self._memory_cache["index_prices"][cache_key]
        
        data = self._load_from_persistence("index_prices", cache_key)
        if data:
            self._memory_cache["index_prices"][cache_key] = data
            self._cache_timestamps[f"index_prices_{cache_key}"] = datetime.now()
            return data
        
        return None
    
    def set_index_prices(self, symbol: str, start_date: str, end_date: str, data: list[dict]) -> None:
        """缓存指数价格数据"""
        cache_key = self._generate_cache_key(symbol, start_date, end_date)
        self._memory_cache["index_prices"][cache_key] = data
        self._cache_timestamps[f"index_prices_{cache_key}"] = datetime.now()
        self._save_to_persistence("index_prices", cache_key, data)
    
    # ========== 缓存管理 ==========
    
    def clear_memory_cache(self) -> None:
        """清空内存缓存"""
        for cache_type in self._memory_cache:
            self._memory_cache[cache_type].clear()
        self._cache_timestamps.clear()
    
    def clear_all_cache(self) -> None:
        """清空所有缓存（包括持久化缓存）"""
        self.clear_memory_cache()
        if self._enable_persistence and self._cache_dir.exists():
            import shutil
            shutil.rmtree(self._cache_dir)
            self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        stats = {
            "memory_cache": {
                cache_type: len(cache_data)
                for cache_type, cache_data in self._memory_cache.items()
            },
            "total_memory_items": sum(len(c) for c in self._memory_cache.values()),
        }
        
        if self._enable_persistence and self._cache_dir.exists():
            persistence_stats = {}
            for cache_type_dir in self._cache_dir.iterdir():
                if cache_type_dir.is_dir():
                    persistence_stats[cache_type_dir.name] = len(list(cache_type_dir.glob("*.json")))
            stats["persistence_cache"] = persistence_stats
            stats["total_persistence_items"] = sum(persistence_stats.values())
        
        return stats


# 全局缓存实例
_cn_cache: Optional[CNDataCache] = None


def get_cn_cache() -> CNDataCache:
    """获取全局国内数据缓存实例"""
    global _cn_cache
    if _cn_cache is None:
        _cn_cache = CNDataCache()
    return _cn_cache
