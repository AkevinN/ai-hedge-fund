from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.backend.database import get_db
from app.backend.repositories.api_key_repository import ApiKeyRepository
from app.backend.models.schemas import (
    ApiKeyCreateRequest,
    ApiKeyUpdateRequest,
    ApiKeyResponse,
    ApiKeySummaryResponse,
    ApiKeyBulkUpdateRequest,
    ErrorResponse
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post(
    "/",
    response_model=ApiKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_or_update_api_key(request: ApiKeyCreateRequest, db: Session = Depends(get_db)):
    """创建新的API密钥或更新现有密钥"""
    try:
        repo = ApiKeyRepository(db)
        api_key = repo.create_or_update_api_key(
            provider=request.provider,
            key_value=request.key_value,
            description=request.description,
            is_active=request.is_active
        )
        return ApiKeyResponse.from_orm(api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建/更新API密钥失败: {str(e)}")


@router.get(
    "/",
    response_model=List[ApiKeySummaryResponse],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_api_keys(include_inactive: bool = False, db: Session = Depends(get_db)):
    """获取所有API密钥（出于安全考虑不包含实际密钥值）"""
    try:
        repo = ApiKeyRepository(db)
        api_keys = repo.get_all_api_keys(include_inactive=include_inactive)
        return [ApiKeySummaryResponse.from_orm(key) for key in api_keys]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索API密钥失败: {str(e)}")


@router.get(
    "/{provider}",
    response_model=ApiKeyResponse,
    responses={
        404: {"model": ErrorResponse, "description": "API key not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_api_key(provider: str, db: Session = Depends(get_db)):
    """根据提供商获取特定的API密钥"""
    try:
        repo = ApiKeyRepository(db)
        api_key = repo.get_api_key_by_provider(provider)
        if not api_key:
            raise HTTPException(status_code=404, detail="API密钥未找到")
        return ApiKeyResponse.from_orm(api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索API密钥失败: {str(e)}")


@router.put(
    "/{provider}",
    response_model=ApiKeyResponse,
    responses={
        404: {"model": ErrorResponse, "description": "API key not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_api_key(provider: str, request: ApiKeyUpdateRequest, db: Session = Depends(get_db)):
    """更新现有的API密钥"""
    try:
        repo = ApiKeyRepository(db)
        api_key = repo.update_api_key(
            provider=provider,
            key_value=request.key_value,
            description=request.description,
            is_active=request.is_active
        )
        if not api_key:
            raise HTTPException(status_code=404, detail="API密钥未找到")
        return ApiKeyResponse.from_orm(api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新API密钥失败: {str(e)}")


@router.delete(
    "/{provider}",
    responses={
        204: {"description": "API key deleted successfully"},
        404: {"model": ErrorResponse, "description": "API key not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_api_key(provider: str, db: Session = Depends(get_db)):
    """删除API密钥"""
    try:
        repo = ApiKeyRepository(db)
        success = repo.delete_api_key(provider)
        if not success:
            raise HTTPException(status_code=404, detail="API密钥未找到")
        return {"message": "API密钥删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除API密钥失败: {str(e)}")


@router.patch(
    "/{provider}/deactivate",
    response_model=ApiKeySummaryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "API key not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def deactivate_api_key(provider: str, db: Session = Depends(get_db)):
    """停用API密钥而不删除它"""
    try:
        repo = ApiKeyRepository(db)
        success = repo.deactivate_api_key(provider)
        if not success:
            raise HTTPException(status_code=404, detail="API密钥未找到")

        # 返回更新后的密钥
        api_key = repo.get_api_key_by_provider(provider)
        return ApiKeySummaryResponse.from_orm(api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停用API密钥失败: {str(e)}")


@router.post(
    "/bulk",
    response_model=List[ApiKeyResponse],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def bulk_update_api_keys(request: ApiKeyBulkUpdateRequest, db: Session = Depends(get_db)):
    """批量创建或更新多个API密钥"""
    try:
        repo = ApiKeyRepository(db)
        api_keys_data = [
            {
                'provider': key.provider,
                'key_value': key.key_value,
                'description': key.description,
                'is_active': key.is_active
            }
            for key in request.api_keys
        ]
        api_keys = repo.bulk_create_or_update(api_keys_data)
        return [ApiKeyResponse.from_orm(key) for key in api_keys]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新API密钥失败: {str(e)}")


@router.patch(
    "/{provider}/last-used",
    responses={
        200: {"description": "Last used timestamp updated"},
        404: {"model": ErrorResponse, "description": "API key not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_last_used(provider: str, db: Session = Depends(get_db)):
    """更新API密钥的最后使用时间戳"""
    try:
        repo = ApiKeyRepository(db)
        success = repo.update_last_used(provider)
        if not success:
            raise HTTPException(status_code=404, detail="API密钥未找到")
        return {"message": "最后使用时间戳已更新"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新最后使用时间戳失败: {str(e)}") 