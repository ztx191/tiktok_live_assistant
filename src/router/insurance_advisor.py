from fastapi import APIRouter
from pydantic import BaseModel

from service.insurance_advisor.workflow_service import InsuranceAdvisor
router = APIRouter(prefix="/api/tiktok/advisor", tags=["tiktok"], responses={404: {"message": "Not found"}})

class UserModel(BaseModel):
    account: str
    password: str

class RequestModel(BaseModel):
    query: str


insurance_advisor = None

@router.post("/init")
async def init(request: UserModel):
    global insurance_advisor
    thread_id = request.account + request.password
    insurance_advisor = InsuranceAdvisor(thread_id)
    return "登陆成功！", thread_id



@router.post("/chat")
async def chat(request: RequestModel):
    response = await insurance_advisor.chat(request.query)
    return response


