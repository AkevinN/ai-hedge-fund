from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.backend.database.models import HedgeFundFlowRun
from app.backend.models.schemas import FlowRunStatus


class FlowRunRepository:
    """HedgeFundFlowRun CRUD 操作的仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def create_flow_run(self, flow_id: int, request_data: Dict[str, Any] = None) -> HedgeFundFlowRun:
        """创建新的 flow run"""
        # 获取此 flow 的下一个运行编号
        run_number = self._get_next_run_number(flow_id)

        flow_run = HedgeFundFlowRun(
            flow_id=flow_id,
            request_data=request_data,
            run_number=run_number,
            status=FlowRunStatus.IDLE.value
        )
        self.db.add(flow_run)
        self.db.commit()
        self.db.refresh(flow_run)
        return flow_run

    def get_flow_run_by_id(self, run_id: int) -> Optional[HedgeFundFlowRun]:
        """根据 ID 获取 flow run"""
        return self.db.query(HedgeFundFlowRun).filter(HedgeFundFlowRun.id == run_id).first()

    def get_flow_runs_by_flow_id(self, flow_id: int, limit: int = 50, offset: int = 0) -> List[HedgeFundFlowRun]:
        """获取特定 flow 的所有运行，按最新优先排序"""
        return (
            self.db.query(HedgeFundFlowRun)
            .filter(HedgeFundFlowRun.flow_id == flow_id)
            .order_by(desc(HedgeFundFlowRun.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_active_flow_run(self, flow_id: int) -> Optional[HedgeFundFlowRun]:
        """获取 flow 当前活跃的（IN_PROGRESS）运行"""
        return (
            self.db.query(HedgeFundFlowRun)
            .filter(
                HedgeFundFlowRun.flow_id == flow_id,
                HedgeFundFlowRun.status == FlowRunStatus.IN_PROGRESS.value
            )
            .first()
        )

    def get_latest_flow_run(self, flow_id: int) -> Optional[HedgeFundFlowRun]:
        """获取 flow 最近的一次运行"""
        return (
            self.db.query(HedgeFundFlowRun)
            .filter(HedgeFundFlowRun.flow_id == flow_id)
            .order_by(desc(HedgeFundFlowRun.created_at))
            .first()
        )

    def update_flow_run(
        self,
        run_id: int,
        status: Optional[FlowRunStatus] = None,
        results: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[HedgeFundFlowRun]:
        """更新现有的 flow run"""
        flow_run = self.get_flow_run_by_id(run_id)
        if not flow_run:
            return None

        # 更新状态和时间
        if status is not None:
            flow_run.status = status.value

            # 根据状态更新时间
            if status == FlowRunStatus.IN_PROGRESS and not flow_run.started_at:
                flow_run.started_at = datetime.utcnow()
            elif status in [FlowRunStatus.COMPLETE, FlowRunStatus.ERROR] and not flow_run.completed_at:
                flow_run.completed_at = datetime.utcnow()

        # 更新结果和错误消息
        if results is not None:
            flow_run.results = results
        if error_message is not None:
            flow_run.error_message = error_message

        self.db.commit()
        self.db.refresh(flow_run)
        return flow_run

    def delete_flow_run(self, run_id: int) -> bool:
        """根据 ID 删除 flow run"""
        flow_run = self.get_flow_run_by_id(run_id)
        if not flow_run:
            return False

        self.db.delete(flow_run)
        self.db.commit()
        return True

    def delete_flow_runs_by_flow_id(self, flow_id: int) -> int:
        """删除特定 flow 的所有运行。返回删除的运行数量。"""
        deleted_count = (
            self.db.query(HedgeFundFlowRun)
            .filter(HedgeFundFlowRun.flow_id == flow_id)
            .delete()
        )
        self.db.commit()
        return deleted_count

    def get_flow_run_count(self, flow_id: int) -> int:
        """获取 flow 的运行总数"""
        return (
            self.db.query(HedgeFundFlowRun)
            .filter(HedgeFundFlowRun.flow_id == flow_id)
            .count()
        )

    def _get_next_run_number(self, flow_id: int) -> int:
        """获取 flow 的下一个运行编号"""
        max_run_number = (
            self.db.query(func.max(HedgeFundFlowRun.run_number))
            .filter(HedgeFundFlowRun.flow_id == flow_id)
            .scalar()
        )
        return (max_run_number or 0) + 1 