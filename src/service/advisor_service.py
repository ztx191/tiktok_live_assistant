import logging
from copy import deepcopy
from typing import Optional
from datetime import datetime
from src.service.assistant_data_process import AssistantDataProcess
from src.service.insurance_advisor.process_graph import AdvisorGraph

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为INFO，这样INFO及以上级别的日志都会显示
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 设置日志格式
    handlers=[
        logging.StreamHandler()  # 添加StreamHandler将日志输出到终端
    ]
)

logger = logging.getLogger(__name__)

class AdvisorService:
    # TODO: 增加多用户和历史保存
    def __init__(self, user_id: str, room_id: str, memory: bool = True):
        self.user_id = user_id
        self.room_id = room_id
        self.memory = memory
        self.service = AdvisorGraph(self.memory)
        self.data_process = AssistantDataProcess("advisor")
        self.history = {"uid": self.user_id,
                        "room_id": self.room_id,
                        "chat_history": [],
                        "collect_info": [],
                        "start_time": round(datetime.now().timestamp())
                        }

    async def answer(self, query: str, thread_id, config_id: Optional[str] = None):
        if not config_id:
            config_id = "0"
        thread_id_config = {"configurable": {"thread_id": thread_id}}
        config = self.data_process.assistant_list_by_broadcast_room_id(self.room_id)
        assistant_config = deepcopy(config["assistant_config"])
        config["assistant_config"] = assistant_config[config_id]
        res, his = await self.service.chat(query, config, thread_id_config)
        logger.info(f"{query}的回答为：\n{res}")
        chat_history, collect_info = self.data_process.process_chat_state(his)
        self.history.update({"chat_history": chat_history, "collect_info": collect_info})
        # history = [{"content": query, "answer": res}]
        # self.history["history"] = history
        return res, his

    def save_info(self):
        self.data_process.save_info(self.history)
        logger.info("历史记录保存成功")


if __name__ == '__main__':
    import asyncio
    service = AdvisorService("大伟哥", "7654321")
    while True:
        query = input("请输入问题：")
        res, his = asyncio.run(service.answer(query, "1"))
        print(res)
        print("\n")
        print(his)
        if query == "q":
            service.save_info()