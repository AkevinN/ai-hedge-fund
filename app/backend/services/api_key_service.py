from sqlalchemy.orm import Session
from typing import Dict, Optional
from app.backend.repositories.api_key_repository import ApiKeyRepository


class ApiKeyService:
    """用于为请求加载API密钥的简单服务"""

    def __init__(self, db: Session):
        self.repository = ApiKeyRepository(db)

    def get_api_keys_dict(self) -> Dict[str, str]:
        """
        从数据库加载所有活动的API密钥并作为字典返回
        适合注入到请求中
        """
        api_keys = self.repository.get_all_api_keys(include_inactive=False)
        return {key.provider: key.key_value for key in api_keys}

    def get_api_key(self, provider: str) -> Optional[str]:
        """根据提供商获取特定的API密钥"""
        api_key = self.repository.get_api_key_by_provider(provider)
        return api_key.key_value if api_key else None 