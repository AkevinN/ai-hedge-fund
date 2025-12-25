from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
from pydantic import BaseModel

from app.backend.models.schemas import ErrorResponse

router = APIRouter(prefix="/storage")

class SaveJsonRequest(BaseModel):
    filename: str
    data: dict

@router.post(
    path="/save-json",
    responses={
        200: {"description": "File saved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def save_json_file(request: SaveJsonRequest):
    """将JSON数据保存到项目的/outputs目录"""
    try:
        # 如果目录不存在则创建outputs目录
        project_root = Path(__file__).parent.parent.parent.parent  # 导航到项目根目录
        outputs_dir = project_root / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        # 构建文件路径
        file_path = outputs_dir / request.filename

        # 将JSON数据保存到文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(request.data, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "message": f"文件成功保存到 {file_path}",
            "filename": request.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}") 