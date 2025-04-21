from typing import Optional, List, Any, Annotated, Union
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain.tools import tool

class SubClassifyConfig(TypedDict):
    pass

class CommonConfig(TypedDict):
    user_id: str
    broadcast_topic: str
    broadcast_room_id: str
    industry: str
    main_classify: Union[list, bool]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    assistant_config: dict[str, Any]
    flow_guide: dict
    # qa_knowledge: Optional[list[dict[int, Any]]]
    # classify_summary: Optional[list[dict[str, Any]]]