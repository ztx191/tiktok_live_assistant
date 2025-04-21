from fastapi import APIRouter
from src.service.knowledge_base_service import KnowledgeBaseService

router = APIRouter(prefix="/api/tiktok/kb_service", tags=["tiktok"], responses={404: {"message": "Not found"}})


@router.get("/list")
async def knowledge_list():
    service = KnowledgeBaseService()
    res, _ = service.get_exist_knowledge()
    return res