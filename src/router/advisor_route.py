from fastapi import APIRouter
import uuid
from src.service.advisor_service import AdvisorService
from src.model.advisor import AdvisorConfig, RequestModel, InitModel, ReviseConfig, InquireConfig
from src.service.assistant_data_process import AssistantDataProcess


router = APIRouter(prefix="/tiktok/advisor", tags=["tiktok-advisor"], responses={404: {"message": "Not found"}})
advisor = None
@router.post("/init")
async def init(request: InitModel):
    global advisor
    advisor = AdvisorService(request.user_id, request.room_id)
    user_code = str(uuid.uuid4())
    return {"message": "登陆成功！", "user_code": user_code, "code": 200}

@router.post("/create_config")
async def create_config(config: AdvisorConfig):
    """
    创建配置
    """
    service = AssistantDataProcess("advisor")
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
    service = AssistantDataProcess("advisor")
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
    service = AssistantDataProcess("advisor")
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
    service = AssistantDataProcess("advisor")
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
    try:
        res, _ = await advisor.answer(request.query, request.thread_id, request.config_id)
        return {"message": res, "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}

@router.get("/save_info")
async def save_info():
    """
    保存信息
    """
    try:
        advisor.save_info()
        return {"message": "保存成功", "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}

@router.post("/get_save_info")
async def get_save_info(request: InitModel):
    """
    获取保存的信息
    """
    service = AssistantDataProcess("advisor")
    try:
        res = service.get_save_info(request.user_id, request.room_id)
        return {"message": res, "code": 200}
    except Exception as e:
        return {"message": str(e), "code": 500}

