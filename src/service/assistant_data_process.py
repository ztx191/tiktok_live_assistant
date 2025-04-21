from datetime import datetime
from typing import Optional
import uuid
import base64
import logging

import shortuuid

from src.service.utils import message_to_list_dict
from src.connector.client import Clients

logger = logging.getLogger(__name__)

class AssistantDataProcess:
    def __init__(self, config_type: str):
        if config_type == "assistant":
            self.mongo_db = Clients.get_mongo().broadcast_assistans_config
        if config_type == "advisor":
            self.mongo_db = Clients.get_mongo().insurance_advisor_config
        self.db = Clients.get_mongo().chat_history


    def process_chat_state(self, state):
        collect_info = []
        recorder = state["flow_guide"]
        chat_history = message_to_list_dict(state["messages"])
        for k, v in recorder["collect_pace"].items():
            if k == "钝角":
                if v["qa_list"]:
                    collect_info.extend(v["qa_list"])
            else:
                if v["qa_list"]:
                    collect_info.append({k: v["qa_list"]})
        return chat_history, collect_info

    def save_info(self, history):
        history.update({"_id": shortuuid.random(16), "end_time": round(datetime.now().timestamp())})
        self.db.insert_one(history)

    def get_save_info(self, user_id: str, room_id: str):
        history = self.db.find({"uid": user_id, "room_id": room_id})
        if history:
            history = list(history)
        else:
            return []
        return history


            
    def assistant_list_by_user_id(self, user_id: str, room_id: str):
        """
        通过用户id获取配置的直播助手信息
        TODO: 查询
        :param user_id:
        :param room_id
        :return:
        """
        info = self.mongo_db.find({"user_id": user_id, "broadcast_room_id": room_id})
        return list(info)


    def assistant_list_by_broadcast_room_id(self, broadcast_room_id: str):
        """
        通过直播间id查询直播间配置了哪些直播助手，并返回直播助手配置信息
        :param broadcast_room_id:
        :return:
        """
        config = self.mongo_db.find_one({"broadcast_room_id": broadcast_room_id})
        return config

    def create_assistant_config(self, user_id: str, broadcast_topic: str, broadcast_room_id: str, industry: str, assistant_config = None):
        """
        保存直播助手配置信息
        :param user_id:
        :param broadcast_topic:
        :param broadcast_room_id:
        :param industry:
        :param assistant_config:
        :return:
        """
        
        config = {
            "_id": base64.b64encode(str(uuid.uuid4()).encode()).decode(),
            "user_id": user_id,
            "broadcast_topic": broadcast_topic,
            "broadcast_room_id": broadcast_room_id,
            "industry": industry,
            "UploadTime": round(datetime.now().timestamp())
        }
        if assistant_config:
            if not isinstance(assistant_config, dict):
                assistant_config = assistant_config.dict()
            assistant_config.update({"UploadTime": round(datetime.now().timestamp())})
            config["assistant_config"] = {"0": assistant_config}

        self.mongo_db.insert_one(config)


    def submit_config(self, room_id: str, assistant_config, config_id: Optional[str] = None):
        # TODO：修改配置信息
        if not config_id:
            config_id = "0"
        update_path = f"assistant_config.{config_id}"
        if not assistant_config:
            assistant_config = dict()
        if not isinstance(assistant_config, dict):
            assistant_config = assistant_config.dict()
        assistant_config.update({"UploadTime": round(datetime.now().timestamp())})

        result = self.mongo_db.update_one(
            {"broadcast_room_id": room_id},
            {"$set": {update_path: assistant_config}}
        )
        if result.modified_count > 0:
            logger.info(f"{room_id}配置{config_id}更新配置信息成功！")
            return True
        else:
            logger.error(f"{room_id}配置{config_id}更新配置信息失败！")
            return False

    def add_assistant_config(self, room_id: str, assistant_config):
        # TODO：新增直播间配置信息
        if not isinstance(assistant_config, dict):
            assistant_config = assistant_config.dict()
        assistant_config.update({"UploadTime": round(datetime.now().timestamp())})
        document = self.mongo_db.find_one({"broadcast_room_id": room_id})
        config = document.get("assistant_config", {})
        existing_keys = [int(key) for key in config.keys() if key.isdigit()]
        new_key = str(max(existing_keys) + 1) if existing_keys else "0"

        # 插入新配置
        update_path = f"assistant_config.{new_key}"
        result = self.mongo_db.update_one(
            {"broadcast_room_id": room_id},
            {"$set": {update_path: assistant_config}}
        )
        if result.modified_count > 0:
            logger.info(f"{room_id}新增配置信息成功！")
            return True
        else:
            logger.error(f"{room_id}新增配置信息失败！")
            return False

    def delete_config(self, room_id: str, config_id: Optional[str]):
        # TODO：删除直播间配置信息
        if not config_id:
            config_id = "0"

        if not config == "all":
            document = self.mongo_db.find_one({"broadcast_room_id": room_id})
            assistant_config = document.get("assistant_config", {})
            del assistant_config[config_id]
            sorted_keys = sorted([int(key) for key in assistant_config.keys() if key.isdigit()])
            reordered_config = {str(i): assistant_config[str(sorted_keys[i])] for i in range(len(sorted_keys))}

            # 更新文档
            result = self.mongo_db.update_one(
                {"broadcast_room_id": room_id},
                {"$set": {"assistant_config": reordered_config}}
            )

        else:
            result = self.mongo_db.delete_one({"broadcast_room_id": room_id})

        if result.modified_count > 0:
            logger.info(f"{room_id}删除{config_id}配置信息成功！")
            return True
        else:
            logger.error(f"{room_id}删除{config_id}配置信息失败！")
            return False


if __name__ == '__main__':
    service = AssistantDataProcess("assistant")
    # service.create_assistant_config("admin", "小海豚产品", "123", "9876543210", {
    #     "bad_answer": "我好像有点没太明白你的意思呢，能不能换个方式再和我说一说",
    #     "details": {
    #         "classify": ["通用", "投保问题", "理赔问题"],
    #         "details": {
    #             "通用": {
    #                 "description": "一般性询问、公司介绍、基础保险知识等非特定保险业务问题",
    #                 "kb_name": "小海豚产品背景资料.md..."
    #             },
    #             "投保问题": {
    #                 "description": "与保险产品选择、购买流程、保费计算、保单管理等相关的问题",
    #                 "classify": ["产品咨询", "投保流程"],
    #                 "产品咨询": {
    #                     "kb_name": "小海豚产品背景资料.md...",
    #                     "description": "关于保险产品特点、保障范围、适用人群、价格对比等咨询",
    #                     "response_rule": "回答时先简要介绍相关产品特点，然后根据用户情况给出个性化建议，最后提供产品对比参考"
    #                 },
    #                 "投保流程": {
    #                     "kb_name": "小海豚产品背景资料.md...",
    #                     "description": "关于保险购买步骤、所需材料、核保规则、缴费方式等流程性问题",
    #                     "response_rule": "回答时按照时间顺序清晰列出投保步骤，强调注意事项，并提供客服联系方式以便用户进一步咨询"
    #                 }
    #             },
    #             "理赔问题": {
    #                 "description": "与保险理赔流程、材料准备、理赔标准、理赔进度查询等相关的问题",
    #                 "classify": ["理赔申请", "理赔进度"],
    #                 "理赔申请": {
    #                     "kb_name": "小海豚产品背景资料.md...",
    #                     "description": "关于如何申请理赔、需要准备的材料、理赔条件和标准等问题",
    #                     "response_rule": "回答时详细列出理赔所需材料清单，解释理赔条件和标准，提供理赔申请的具体步骤，并说明可能的理赔时间"
    #                 },
    #                 "理赔进度": {
    #                     "kb_name": "小海豚产品背景资料.md...",
    #                     "description": "关于已提交理赔申请的进度查询、结果确认、异议处理等后续问题",
    #                     "response_rule": "回答时说明查询理赔进度的多种方式，解释各种理赔状态的含义，提供理赔结果异议的处理流程，并给出理赔专员的联系方式"
    #                 }
    #             }
    #         }
    #     }
    # })
    # res = service.assistant_list_by_broadcast_room_id("123")
    # print(res)
    config = {
    "bad_answer": "新的默认回答",
    "details": {
        "classify": ["新的分类"],
        "details": {
            "新的分类": {
                "description": "新的描述",
                "kb_name": "新的知识库文件.md"
            }
        }
    }
}
    res = service.delete_config("123", "1")
    print(res)









