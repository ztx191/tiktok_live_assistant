import logging
from copy import deepcopy
from typing import Optional
from src.service.assistant_data_process import AssistantDataProcess
from src.service.broadcast_assistant.process_graph import AssistantGraph

# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,  # 设置日志级别为INFO，这样INFO及以上级别的日志都会显示
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 设置日志格式
#     handlers=[
#         logging.StreamHandler()  # 添加StreamHandler将日志输出到终端
#     ]
# )

logger = logging.getLogger(__name__)

class AssistantService:
    # TODO: 增加多用户和历史保存
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.data_process = AssistantDataProcess("assistant")

    async def answer(self, query: str, config_id: Optional[str] = None):
        if not config_id:
            config_id = "0"
        config = self.data_process.assistant_list_by_broadcast_room_id(self.room_id)
        assistant_config = deepcopy(config["assistant_config"])
        config["assistant_config"] = assistant_config[config_id]
        res = await AssistantGraph(config).chat(query)
        return res

if __name__ == '__main__':
    import asyncio
    service = AssistantService("20752280755")
    res = asyncio.run(service.answer("为什么即使有社保，人们还需要购买医疗险？"))
    print(res)



