from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field

class SubClassDetails(BaseModel):
    kb_name: Optional[str] = None
    description: str
    response_rule: str

class CategoryDetails(BaseModel):
    description: str
    kb_name: Optional[str] = None
    collect_cust_info: Optional[List] = None
    classify: Optional[List[str]] = None

class ClassifyConfig(BaseModel):
    classify: List[str]
    details: Dict[str, Dict[str, Any]]

class SimpleAssistantConfig(BaseModel):
    opening_remarks: str
    hot_issues: str
    update_issues: bool
    bad_answer: str  # Note: there's a typo here, should be "bad_answer" but keeping as is
    kb_name: str
    collect_cust_info: Optional[List] = None

class AdvancedAssistantConfig(BaseModel):
    opening_remarks: str
    hot_issues: str
    update_issues: bool
    bad_answer: str  # Note: there's a typo here, should be "bad_answer" but keeping as is
    details: ClassifyConfig

class AdvisorConfig(BaseModel):
    user_id: str
    broadcast_topic: str
    broadcast_room_id: str
    industry: str
    assistant_config: Optional[Union[SimpleAssistantConfig, AdvancedAssistantConfig]] = None

class InitModel(BaseModel):
    room_id: str
    user_id: str

class ReviseConfig(BaseModel):
    room_id: str
    config_id: Optional[str] = None
    assistant_config: Optional[Union[SimpleAssistantConfig, AdvancedAssistantConfig]] = None

class InquireConfig(BaseModel):
    user_id: str
    room_id: Optional[str] = None

class RequestModel(BaseModel):
    query: str
    config_id: Optional[str] = None
    thread_id: str

