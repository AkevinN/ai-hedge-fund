from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

from app.backend.models.schemas import ErrorResponse
from app.backend.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ollama")

class ModelRequest(BaseModel):
    model_name: str

class OllamaStatusResponse(BaseModel):
    installed: bool
    running: bool
    available_models: List[str]
    server_url: str
    error: str | None = None

class ActionResponse(BaseModel):
    success: bool
    message: str

class RecommendedModel(BaseModel):
    display_name: str
    model_name: str
    provider: str

class ProgressResponse(BaseModel):
    status: str
    percentage: float | None = None
    message: str | None = None
    phase: str | None = None
    bytes_downloaded: int | None = None
    total_bytes: int | None = None

@router.get(
    "/status",
    response_model=OllamaStatusResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_ollama_status():
    """获取Ollama安装和服务器状态"""
    try:
        status = await ollama_service.check_ollama_status()
        return OllamaStatusResponse(**status)
    except Exception as e:
        logger.error(f"检查Ollama状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查Ollama状态失败: {str(e)}")

@router.post(
    "/start",
    response_model=ActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def start_ollama_server():
    """启动Ollama服务器"""
    try:
        # 首先检查是否已经运行
        status = await ollama_service.check_ollama_status()
        if not status["installed"]:
            raise HTTPException(status_code=400, detail="此系统未安装Ollama")

        if status["running"]:
            return ActionResponse(success=True, message="Ollama服务器已在运行")

        result = await ollama_service.start_server()

        if not result["success"]:
            logger.error(f"启动Ollama服务器失败: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])

        return ActionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动Ollama服务器时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"启动Ollama服务器失败: {str(e)}")

@router.post(
    "/stop",
    response_model=ActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def stop_ollama_server():
    """停止Ollama服务器"""
    try:
        # 首先检查是否已安装
        status = await ollama_service.check_ollama_status()
        if not status["installed"]:
            raise HTTPException(status_code=400, detail="此系统未安装Ollama")

        if not status["running"]:
            return ActionResponse(success=True, message="Ollama服务器已停止")

        result = await ollama_service.stop_server()

        if not result["success"]:
            logger.error(f"停止Ollama服务器失败: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])

        return ActionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止Ollama服务器时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"停止Ollama服务器失败: {str(e)}")

@router.post(
    "/models/download",
    response_model=ActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def download_model(request: ModelRequest):
    """下载Ollama模型（旧版端点）"""
    try:
        logger.info(f"模型下载请求: {request.model_name}")

        # 检查当前状态
        status = await ollama_service.check_ollama_status()
        logger.debug(f"当前Ollama状态: installed={status['installed']}, running={status['running']}")

        if not status["installed"]:
            raise HTTPException(status_code=400, detail="此系统未安装Ollama")

        if not status["running"]:
            raise HTTPException(status_code=400, detail="Ollama服务器未运行。请先启动它。")

        result = await ollama_service.download_model(request.model_name)

        if not result["success"]:
            logger.error(f"下载模型 {request.model_name} 失败: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])

        logger.info(f"成功下载模型: {request.model_name}")
        return ActionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载模型 {request.model_name} 时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"下载模型失败: {str(e)}")

@router.post(
    "/models/download/progress",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def download_model_with_progress(request: ModelRequest):
    """通过服务器发送事件实时下载Ollama模型并显示进度"""
    try:
        logger.info(f"进度下载请求模型: {request.model_name}")

        # 检查当前状态
        status = await ollama_service.check_ollama_status()
        logger.debug(f"当前Ollama状态: installed={status['installed']}, running={status['running']}")

        if not status["installed"]:
            raise HTTPException(status_code=400, detail="此系统未安装Ollama")

        if not status["running"]:
            raise HTTPException(status_code=400, detail="Ollama服务器未运行。请先启动它。")

        # 返回服务器发送事件流
        return StreamingResponse(
            ollama_service.download_model_with_progress(request.model_name),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"为 {request.model_name} 设置进度下载时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"启动进度下载失败: {str(e)}")

@router.get(
    "/models/download/progress/{model_name}",
    response_model=ProgressResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Model download not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_download_progress(model_name: str):
    """获取特定模型的当前下载进度"""
    try:
        progress = ollama_service.get_download_progress(model_name)
        if progress is None:
            raise HTTPException(status_code=404, detail=f"未找到模型的活动下载: {model_name}")

        return ProgressResponse(**progress)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {model_name} 下载进度时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取下载进度失败: {str(e)}")

@router.get(
    "/models/downloads/active",
    response_model=Dict[str, ProgressResponse],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_active_downloads():
    """获取所有当前活动的模型下载"""
    try:
        active_downloads = {}
        all_progress = ollama_service.get_all_download_progress()

        # 仅返回实际活动的下载（非已完成、错误或已取消）
        for model_name, progress in all_progress.items():
            if progress.get("status") in ["starting", "downloading"]:
                active_downloads[model_name] = ProgressResponse(**progress)

        return active_downloads
    except Exception as e:
        logger.error(f"获取活动下载时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取活动下载失败: {str(e)}")

@router.delete(
    "/models/{model_name}",
    response_model=ActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_model(model_name: str):
    """删除Ollama模型"""
    try:
        logger.info(f"模型删除请求: {model_name}")

        # 检查当前状态
        status = await ollama_service.check_ollama_status()
        logger.debug(f"当前Ollama状态: installed={status['installed']}, running={status['running']}")

        if not status["installed"]:
            raise HTTPException(status_code=400, detail="此系统未安装Ollama")

        if not status["running"]:
            raise HTTPException(status_code=400, detail="Ollama服务器未运行。请先启动它。")

        result = await ollama_service.delete_model(model_name)

        if not result["success"]:
            logger.error(f"删除模型 {model_name} 失败: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])

        logger.info(f"成功删除模型: {model_name}")
        return ActionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型 {model_name} 时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除模型失败: {str(e)}")

@router.get(
    "/models/recommended",
    response_model=List[RecommendedModel],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_recommended_models():
    """获取推荐的Ollama模型列表"""
    try:
        models = await ollama_service.get_recommended_models()
        return [RecommendedModel(**model) for model in models]
    except Exception as e:
        logger.error(f"获取推荐模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取推荐模型失败: {str(e)}")

@router.delete(
    "/models/download/{model_name}",
    response_model=ActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Download not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def cancel_download(model_name: str):
    """取消活动的模型下载"""
    try:
        logger.info(f"取消下载请求模型: {model_name}")

        success = ollama_service.cancel_download(model_name)

        if success:
            return ActionResponse(success=True, message=f"已取消 {model_name} 的下载")
        else:
            raise HTTPException(status_code=404, detail=f"未找到模型的活动下载: {model_name}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消 {model_name} 下载时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"取消下载失败: {str(e)}") 