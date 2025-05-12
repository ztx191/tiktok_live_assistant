from typing import Union, Optional, Dict, ClassVar
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from openai import BaseModel
from semantic_kernel.kernel_pydantic import KernelBaseSettings


class ChatOpenAISettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "API_HUB_"

    endpoint: str
    token: str

    default_ai_model_id: str
    default_ai_issuer: str

    temperature: float = 0.1
    streaming: bool = False
    max_tokens: int = 5000

class ChatApiHub(ChatOpenAI):
    def _create_chat_result(
            self,
            response: Union[dict, BaseModel],
            generation_info: Optional[Dict] = None,
    ) -> ChatResult:
        response_dict = (
            response if isinstance(response, dict) else response.model_dump()
        )
        if response_dict['code'] != '1':
            raise ValueError(response_dict['desc'])

        return super()._create_chat_result(response_dict['data'], generation_info)

if __name__ == '__main__':
    t = ChatOpenAISettings.create()
    print(t.dict())