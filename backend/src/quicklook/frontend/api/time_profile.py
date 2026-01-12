"""
タイムプロファイルダウンロード用APIエンドポイント
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from quicklook.object_storage import VisitObjectStorage
from quicklook.types import VisitName
from quicklook.utils.s3 import NoSuchKey

router = APIRouter(tags=["time-profile"])


@router.get("/api/time-profile/{visit_name}")
async def get_time_profile(visit_name: str) -> Response:
    """
    指定されたvisitのタイムプロファイルをJSON形式で返す
    
    Args:
        visit_name: Visit名（例: "raw:2025092100190"）
    
    Returns:
        JSON形式のタイムプロファイル
    """
    try:
        storage = VisitObjectStorage.from_visit(VisitName(visit_name))
        json_data = await storage.get_time_profile()
        return Response(
            content=json_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="time-profile-{visit_name.replace(":", "_").replace("/", "_")}.json"'
            }
        )
    except NoSuchKey:
        raise HTTPException(status_code=404, detail=f"Time profile not found for visit: {visit_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
