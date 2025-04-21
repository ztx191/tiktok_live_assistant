from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

class SubClassDetails(BaseModel):
    kb_name: Optional[str] = None
    description: str
    response_rule: str


class CategoryDetails(BaseModel):
    description: str
    kb_name: Optional[str] = None
    classify: Optional[List[str]] = None


class ClassifyDetails(BaseModel):
    classify: List[str]
    details: Dict[str, Union[CategoryDetails, Dict[str, Union[SubClassDetails, str, List[str]]]]]


class SimpleAssistantConfig(BaseModel):
    bad_answer: str
    kb_name: str


class AdvancedAssistantConfig(BaseModel):
    bad_answer: str
    details: ClassifyDetails


class BroadcastConfig(BaseModel):
    user_id: str
    broadcast_topic: str
    broadcast_room_id: str
    industry: str
    assistant_config: Optional[Union[SimpleAssistantConfig, AdvancedAssistantConfig]] = None

class ReviseConfig(BaseModel):
    room_id: str
    config_id: Optional[str] = None
    assistant_config: Optional[Union[SimpleAssistantConfig, AdvancedAssistantConfig]] = None

class InquireConfig(BaseModel):
    user_id: str
    room_id: Optional[str] = None

class RequestModel(BaseModel):
    room_id: str
    config_id: Optional[str] = None
    query: str
    

