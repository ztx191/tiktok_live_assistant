from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class Request(BaseModel):
    requestNo: Optional[str] = None
    requestTime: Optional[int] = None


class ChatRequest(Request):
    """
    用户对话请求
    """
    query: Optional[str] = None  # 用户查询请求
    files: Optional[list[str]] = None  # 用户上传的文件
    form: Optional[dict[str, str]] = None


class Result(BaseModel):
    data: Any = None
    message: str = 'ok'
    code: int = 0


# 用户操作行为
class DataAction(Enum):
    remove = 0
    add = 1
    update = 2


class File(BaseModel):
    type: str
    path: str
    ext: str  # 文件后缀
