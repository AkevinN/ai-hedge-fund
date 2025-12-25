from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.backend.database.models import ApiKey


class ApiKeyRepository:
    """API key 数据库操作的仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def create_or_update_api_key(
        self,
        provider: str,
        key_value: str,
        description: str = None,
        is_active: bool = True
    ) -> ApiKey:
        """创建新的 API key 或更新现有的"""
        # 检查此提供商是否已存在 API key
        existing_key = self.db.query(ApiKey).filter(ApiKey.provider == provider).first()

        if existing_key:
            # 更新现有 key
            existing_key.key_value = key_value
            existing_key.description = description
            existing_key.is_active = is_active
            existing_key.updated_at = func.now()
            self.db.commit()
            self.db.refresh(existing_key)
            return existing_key
        else:
            # 创建新 key
            api_key = ApiKey(
                provider=provider,
                key_value=key_value,
                description=description,
                is_active=is_active
            )
            self.db.add(api_key)
            self.db.commit()
            self.db.refresh(api_key)
            return api_key

    def get_api_key_by_provider(self, provider: str) -> Optional[ApiKey]:
        """根据提供商名称获取 API key"""
        return self.db.query(ApiKey).filter(
            ApiKey.provider == provider,
            ApiKey.is_active == True
        ).first()

    def get_all_api_keys(self, include_inactive: bool = False) -> List[ApiKey]:
        """获取所有 API keys"""
        query = self.db.query(ApiKey)
        if not include_inactive:
            query = query.filter(ApiKey.is_active == True)
        return query.order_by(ApiKey.provider).all()

    def update_api_key(
        self,
        provider: str,
        key_value: str = None,
        description: str = None,
        is_active: bool = None
    ) -> Optional[ApiKey]:
        """更新现有的 API key"""
        api_key = self.db.query(ApiKey).filter(ApiKey.provider == provider).first()
        if not api_key:
            return None

        if key_value is not None:
            api_key.key_value = key_value
        if description is not None:
            api_key.description = description
        if is_active is not None:
            api_key.is_active = is_active

        api_key.updated_at = func.now()
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def delete_api_key(self, provider: str) -> bool:
        """根据提供商删除 API key"""
        api_key = self.db.query(ApiKey).filter(ApiKey.provider == provider).first()
        if not api_key:
            return False

        self.db.delete(api_key)
        self.db.commit()
        return True

    def deactivate_api_key(self, provider: str) -> bool:
        """停用 API key 而不是删除它"""
        api_key = self.db.query(ApiKey).filter(ApiKey.provider == provider).first()
        if not api_key:
            return False

        api_key.is_active = False
        api_key.updated_at = func.now()
        self.db.commit()
        return True

    def update_last_used(self, provider: str) -> bool:
        """更新 API key 的 last_used 时间戳"""
        api_key = self.db.query(ApiKey).filter(
            ApiKey.provider == provider,
            ApiKey.is_active == True
        ).first()
        if not api_key:
            return False

        api_key.last_used = func.now()
        self.db.commit()
        return True

    def bulk_create_or_update(self, api_keys_data: List[dict]) -> List[ApiKey]:
        """批量创建或更新多个 API keys"""
        results = []
        for data in api_keys_data:
            api_key = self.create_or_update_api_key(
                provider=data['provider'],
                key_value=data['key_value'],
                description=data.get('description'),
                is_active=data.get('is_active', True)
            )
            results.append(api_key)
        return results 