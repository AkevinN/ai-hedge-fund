from typing import Dict, Optional, Any, Literal
from pydantic import BaseModel


class BaseEvent(BaseModel):
    """所有 Server-Sent Event 事件的基类"""

    type: str

    def to_sse(self) -> str:
        """转换为 Server-Sent Event 格式"""
        event_type = self.type.lower()
        return f"event: {event_type}\ndata: {self.model_dump_json()}\n\n"


class StartEvent(BaseEvent):
    """表示处理开始的事件"""

    type: Literal["start"] = "start"
    timestamp: Optional[str] = None

class ProgressUpdateEvent(BaseEvent):
    """包含 agent 进度更新的事件"""

    type: Literal["progress"] = "progress"
    agent: str
    ticker: Optional[str] = None
    status: str
    timestamp: Optional[str] = None
    analysis: Optional[str] = None

class ErrorEvent(BaseEvent):
    """表示发生错误的事件"""

    type: Literal["error"] = "error"
    message: str
    timestamp: Optional[str] = None


class CompleteEvent(BaseEvent):
    """表示成功完成并带有结果的事件"""

    type: Literal["complete"] = "complete"
    data: Dict[str, Any]
    timestamp: Optional[str] = None
