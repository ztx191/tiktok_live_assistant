from fastapi import APIRouter

from src.service.assistant_service import AssistantService
from src.model.broadcast import BroadcastConfig, RequestModel, ReviseConfig, InquireConfig
from src.service.assistant_data_process import AssistantDataProcess

router = APIRouter(prefix="/tiktok/assistant", tags=["tiktok-assistant"], responses={404: {"message": "Not found"}})

@router.post("/create_config")
async def create_config(config: BroadcastConfig):
    """
    创建配置
    """
    service = AssistantDataProcess("assistant")
    try:
        if config.assistant_config:
            service.create_assistant_config(config.user_id, config.broadcast_topic, config.broadcast_room_id, config.industry, config.assistant_config)
        else:
            service.create_assistant_config(config.user_id, config.broadcast_topic, config.broadcast_room_id, config.industry)
        return {"message": "创建成功", "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}

@router.post("/submit_config")
async def submit_config(config: ReviseConfig):
    """
    修改已有配置
    """
    service = AssistantDataProcess("assistant")
    try:
        service.submit_config(config.room_id, config.assistant_config, config.config_id)
        return {"message": f"修改成功", "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}


@router.post("/delete_config")
async def delete_config(config: ReviseConfig):
    """
    删除配置
    """
    service = AssistantDataProcess("assistant")
    try:
        service.delete_config(config.room_id, config.config_id)
        return {"message": f"删除成功", "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}

@router.post("/list_config")
async def list_config(config: InquireConfig):
    """
    查看用户创建的所有直播间信息
    """
    service = AssistantDataProcess("assistant")
    try:
        res = service.assistant_list_by_user_id(config.user_id, config.room_id)
        return {"message": res, "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}

@router.post("/chat")
async def chat(request: RequestModel):
    """
    问答
    """
    assistant = AssistantService(request.room_id)
    try:
        res = await assistant.answer(request.query, request.config_id)
        return {"message": res, "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}
