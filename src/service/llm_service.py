from langchain_core.messages import HumanMessage
from pydantic import SecretStr
from typing import Optional
from langchain_openai import ChatOpenAI
from src.connector.api_hub_chat_openai import ChatOpenAISettings, ChatApiHub

class LLMService:
    def __init__(self, model_name: Optional[str] = None):
        self.llm_settings = ChatOpenAISettings.create()
        if model_name:
            model = model_name
        else:
            model = self.llm_settings.default_ai_model_id
        # self.llm = ChatApiHub(model_name=model,
        #                       default_headers={"aimodel": provider},
        #                       openai_api_base=self.llm_settings.endpoint + "/api/v1",
        #                       openai_api_key=SecretStr(self.llm_settings.token),
        #                       temperature=self.llm_settings.temperature,
        #                       streaming=self.llm_settings.streaming,
        #                       max_tokens=self.llm_settings.max_tokens
        #                       )
        self.llm = ChatOpenAI(model_name=model,
                              openai_api_base=self.llm_settings.endpoint + "/v1",
                              openai_api_key=SecretStr(self.llm_settings.token),
                              temperature=self.llm_settings.temperature,
                              streaming=self.llm_settings.streaming,
                              max_tokens=self.llm_settings.max_tokens
                              )
    def get_llm(self):
        return self.llm


if __name__ == '__main__':
    service = LLMService()
    res = service.llm.invoke([HumanMessage(content="你好")])
    print(res)