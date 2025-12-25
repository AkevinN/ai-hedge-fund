from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.backend.database import get_db
from app.backend.repositories.flow_run_repository import FlowRunRepository
from app.backend.repositories.flow_repository import FlowRepository
from app.backend.models.schemas import (
    FlowRunCreateRequest,
    FlowRunUpdateRequest,
    FlowRunResponse,
    FlowRunSummaryResponse,
    FlowRunStatus,
    ErrorResponse
)

router = APIRouter(prefix="/flows/{flow_id}/runs", tags=["flow-runs"])


@router.post(
    "/",
    response_model=FlowRunResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Flow not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_flow_run(
    flow_id: int,
    request: FlowRunCreateRequest,
    db: Session = Depends(get_db)
):
    """为指定流程创建新的运行"""
    try:
        # 验证流程是否存在
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 创建流程运行
        run_repo = FlowRunRepository(db)
        flow_run = run_repo.create_flow_run(
            flow_id=flow_id,
            request_data=request.request_data
        )
        return FlowRunResponse.from_orm(flow_run)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建流程运行失败: {str(e)}")


@router.get(
    "/",
    response_model=List[FlowRunSummaryResponse],
    responses={
        404: {"model": ErrorResponse, "description": "Flow not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_flow_runs(
    flow_id: int,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip"),
    db: Session = Depends(get_db)
):
    """获取指定流程的所有运行"""
    try:
        # 验证流程是否存在
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 获取流程运行
        run_repo = FlowRunRepository(db)
        flow_runs = run_repo.get_flow_runs_by_flow_id(flow_id, limit=limit, offset=offset)
        return [FlowRunSummaryResponse.from_orm(run) for run in flow_runs]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索流程运行失败: {str(e)}")


@router.get(
    "/active",
    response_model=Optional[FlowRunResponse],
    responses={
        404: {"model": ErrorResponse, "description": "Flow not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_active_flow_run(flow_id: int, db: Session = Depends(get_db)):
    """获取指定流程的当前活动运行（进行中）"""
    try:
        # 验证流程是否存在
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 获取活动的流程运行
        run_repo = FlowRunRepository(db)
        active_run = run_repo.get_active_flow_run(flow_id)
        return FlowRunResponse.from_orm(active_run) if active_run else None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索活动流程运行失败: {str(e)}")


@router.get(
    "/latest",
    response_model=Optional[FlowRunResponse],
    responses={
        404: {"model": ErrorResponse, "description": "Flow not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_latest_flow_run(flow_id: int, db: Session = Depends(get_db)):
    """获取指定流程的最近运行"""
    try:
        # Verify flow exists
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 获取最新的流程运行
        run_repo = FlowRunRepository(db)
        latest_run = run_repo.get_latest_flow_run(flow_id)
        return FlowRunResponse.from_orm(latest_run) if latest_run else None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索最新流程运行失败: {str(e)}")


@router.get(
    "/{run_id}",
    response_model=FlowRunResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Flow or run not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_flow_run(flow_id: int, run_id: int, db: Session = Depends(get_db)):
    """根据ID获取特定的流程运行"""
    try:
        # Verify flow exists
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 获取流程运行
        run_repo = FlowRunRepository(db)
        flow_run = run_repo.get_flow_run_by_id(run_id)
        if not flow_run or flow_run.flow_id != flow_id:
            raise HTTPException(status_code=404, detail="流程运行未找到")

        return FlowRunResponse.from_orm(flow_run)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索流程运行失败: {str(e)}")


@router.put(
    "/{run_id}",
    response_model=FlowRunResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Flow or run not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_flow_run(
    flow_id: int,
    run_id: int,
    request: FlowRunUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新现有的流程运行"""
    try:
        # Verify flow exists
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 更新流程运行
        run_repo = FlowRunRepository(db)
        # 首先验证运行是否存在并属于此流程
        existing_run = run_repo.get_flow_run_by_id(run_id)
        if not existing_run or existing_run.flow_id != flow_id:
            raise HTTPException(status_code=404, detail="流程运行未找到")

        flow_run = run_repo.update_flow_run(
            run_id=run_id,
            status=request.status,
            results=request.results,
            error_message=request.error_message
        )

        if not flow_run:
            raise HTTPException(status_code=404, detail="流程运行未找到")

        return FlowRunResponse.from_orm(flow_run)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新流程运行失败: {str(e)}")


@router.delete(
    "/{run_id}",
    responses={
        204: {"description": "Flow run deleted successfully"},
        404: {"model": ErrorResponse, "description": "Flow or run not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_flow_run(flow_id: int, run_id: int, db: Session = Depends(get_db)):
    """删除流程运行"""
    try:
        # Verify flow exists
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 验证运行是否存在并属于此流程
        run_repo = FlowRunRepository(db)
        existing_run = run_repo.get_flow_run_by_id(run_id)
        if not existing_run or existing_run.flow_id != flow_id:
            raise HTTPException(status_code=404, detail="流程运行未找到")

        success = run_repo.delete_flow_run(run_id)
        if not success:
            raise HTTPException(status_code=404, detail="流程运行未找到")

        return {"message": "流程运行删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除流程运行失败: {str(e)}")


@router.delete(
    "/",
    responses={
        204: {"description": "All flow runs deleted successfully"},
        404: {"model": ErrorResponse, "description": "Flow not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_all_flow_runs(flow_id: int, db: Session = Depends(get_db)):
    """删除指定流程的所有运行"""
    try:
        # Verify flow exists
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 删除所有流程运行
        run_repo = FlowRunRepository(db)
        deleted_count = run_repo.delete_flow_runs_by_flow_id(flow_id)

        return {"message": f"成功删除 {deleted_count} 个流程运行"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除流程运行失败: {str(e)}")


@router.get(
    "/count",
    responses={
        200: {"description": "Flow run count"},
        404: {"model": ErrorResponse, "description": "Flow not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_flow_run_count(flow_id: int, db: Session = Depends(get_db)):
    """获取指定流程的运行总数"""
    try:
        # Verify flow exists
        flow_repo = FlowRepository(db)
        flow = flow_repo.get_flow_by_id(flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="流程未找到")

        # 获取运行计数
        run_repo = FlowRunRepository(db)
        count = run_repo.get_flow_run_count(flow_id)

        return {"flow_id": flow_id, "total_runs": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取流程运行计数失败: {str(e)}") 