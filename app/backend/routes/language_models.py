from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.backend.models.schemas import ErrorResponse
from app.backend.services.ollama_service import OllamaService
from src.llm.models import get_models_list

router = APIRouter(prefix="/language-models")

# 初始化Ollama服务
ollama_service = OllamaService()

@router.get(
    path="/",
    responses={
        200: {"description": "List of available language models"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_language_models():
    """获取可用的云端和Ollama语言模型列表"""
    try:
        # 从云端模型开始
        models = get_models_list()

        # 添加可用的Ollama模型（内部处理所有检查）
        ollama_models = await ollama_service.get_available_models()
        models.extend(ollama_models)

        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索模型失败: {str(e)}")

@router.get(
    path="/providers",
    responses={
        200: {"description": "List of available model providers"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_language_model_providers():
    """获取可用模型提供商列表及其模型分组"""
    try:
        models = get_models_list()

        # 按提供商分组模型
        providers = {}
        for model in models:
            provider_name = model["provider"]
            if provider_name not in providers:
                providers[provider_name] = {
                    "name": provider_name,
                    "models": []
                }
            providers[provider_name]["models"].append({
                "display_name": model["display_name"],
                "model_name": model["model_name"]
            })

        return {"providers": list(providers.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索提供商失败: {str(e)}") 