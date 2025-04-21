from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from src.service.get_newspaper_by_time import *

router = APIRouter(prefix="/get-news", tags=["get-news"], responses={404: {"message": "Not found"}})

class RequestModel(BaseModel):
    news_type: str
    top_k: int = 5
    time: Optional[str] = None

@router.post("/get_recent_newspaper")
async def get_recent(request: RequestModel):
    """
    获取最近新闻
    """
    return get_recent_newspaper(request.news_type, request.top_k)

@router.post("/get_news_by_time")
async def get_news(request: RequestModel):
    """
    获取指定时间段的新闻
    """
    time = request.time
    date_obj = datetime.strptime(time, "%Y-%m-%d")
    timestamp = round(date_obj.timestamp())
    return get_news_by_time(request.news_type, timestamp)