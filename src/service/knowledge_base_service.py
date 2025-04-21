# 包装的dify知识库api 详细文档请参考dify：http://61.172.179.77:5083/datasets?category=api#create-by-file

import json
import os
from typing import ClassVar, Optional, Union, BinaryIO, List
import requests
import httpx
import logging
from httpx import Limits, Timeout
from src.connector.client import Clients
from semantic_kernel.kernel_pydantic import KernelBaseSettings

logger = logging.getLogger(__name__)

class KnowledgeSettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "DIFY_"

    url: str
    database_token: str
    database_id: str
    max_keepalive_connections: int = 5
    max_connections: int = 100


class KnowledgeBaseService:
    def __init__(self, database_settings: KnowledgeSettings = KnowledgeSettings):
        self.settings = database_settings.create()
        self.mongodb = Clients.get_mongo()
        self.base_url = self.settings.url + "/datasets"
        self.headers = {
            "Authorization": f"Bearer {self.settings.database_token}"
        }
        self.client = httpx.Client(base_url=self.base_url,
                                   headers=self.headers,
                                   limits=Limits(max_connections=self.settings.max_connections,
                                                 max_keepalive_connections=self.settings.max_keepalive_connections),
                                   timeout=Timeout(timeout=120.0))

    # def get_exist_knowledge(self):
    #     """
    #     获取已有知识库
    #     :return:知识库名称和名称对应的id
    #     """
    #     name_list = list()
    #     exist_db = self.mongodb.knowledge_database.find_one()
    #     if not exist_db:
    #         return name_list, []
    #     for k, y in exist_db.items():
    #         if k == "_id":
    #             continue
    #         name_list.append(k)
    #     exist_db.pop("_id")
    #     return name_list, exist_db

    def get_exist_knowledge(self):
        import requests
        url = r"http://61.172.179.77:5083/v1/datasets"
        name_list = list()
        exist_db = dict()
        datas = requests.get(url=url, headers=self.headers).json()
        for data in datas["data"]:
            name_list.append(data["name"])
            exist_db.update({data["name"]: data["id"]})
        return name_list, exist_db

    def get_knowledge_info(self, database_name: str):
        """
        获取知识库信息
        :param database_name:
        :return:
        """
        pass

    def get_knowledge_documents_info(self, database_name: str):
        """
        获取知识库文档信息
        :param database_name:
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        try:
            _req = self.client.build_request("GET", f"{database_id}/documents", timeout=600.0)
            _res = self.client.send(_req)
            if _res.status_code == 200:
                _results = _res.json()
                return _results
        except Exception as e:
            logger.error(f"获取知识库文档信息失败：{e}")

    def get_documents_block_info(self, database_name: str, document_id: Optional[str] = None):
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        if document_id:
            try:
                _req = self.client.build_request("GET", f"{database_id}/documents/{document_id}/segments", timeout=600.0)
                _res = self.client.send(_req)
                if _res.status_code == 200:
                    _results = _res.json()
                    return _results
            except Exception as e:
                logger.error(f"获取知识库文档块信息失败：{e}")
        else:
            all_info = list()
            info = self.get_knowledge_documents_info(database_name)
            datas = info["data"]
            try:
                for data in datas:
                    url = f"{database_id}/documents/{data['id']}/segments"
                    _req = self.client.build_request("GET", url, timeout=600.0)
                    _res = self.client.send(_req)
                    _results = _res.json()
                    all_info.append(_results)
                return all_info
            except Exception as e:
                logger.error(f"获取知识库文档块信息失败：{e}")





    def build_new_database(self, database_name: str, description: str = "", indexing_technique: str = "high_quality",
                           provider: str = "vendor", knowledge_api_id: Optional[str] = None,
                           knowledge_id: Optional[str] = None):
        """
        新建空知识库
        :param indexing_technique: 索引方式 high_quality or economy 默认为high_quality
        :param database_name: 知识库名字
        :param description: 知识库描述
        :param provider: external：上传外部知识库；vendor：上传文件
        :param knowledge_api_id:
        :param knowledge_id:
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        if database_name in exist_db:
            # TODO: 处理知识库重名问题
            return "知识库已存在"

        data = {
            "name": database_name,
            "description": description,
            "indexing_technique": indexing_technique,
            "permission": "all_team_members",
            "provider": provider
        }
        headers = self.headers
        headers.update({"Content-Type": "application/json"})
        if provider == "external":
            # TODO: 上传外部api
            pass
        try:
            _req = requests.post(url=self.base_url, headers=headers, data=json.dumps(data, ensure_ascii=False))
            if _req.status_code == 200:
                _results = _req.json()
                self.mongodb.knowledge_database.update_one({}, {"$set": {database_name: _results["id"]}}, upsert=True)
                logger.info(f"创建知识库完成！知识库名称：{database_name}，知识库id：{_results['id']}")
                return "创建成功"
        except Exception as e:
            logger.error(f"创建知识库失败：{e}")


    def delete_database(self, database_name: str):
        """
        删除知识库
        :param database_name: 知识库名称
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        try:
            _req = self.client.build_request("DELETE", f"{database_id}", timeout=600.0)
            _res = self.client.send(_req)
            if _res.status_code == 204:
                self.mongodb.knowledge_database.update_one({}, {"$unset": {database_name: 1}})
                logger.info(f"删除知识库完成！知识库名称：{database_name}，知识库id：{database_id}")
                return "删除成功"
            else:
                return "删除失败"
        except Exception as e:
            logger.error(f"删除知识库失败：{e}")

    # def create_documents_by_file(self, database_name: str, doc_form: str, file: dict[str, tuple], embedding_model: Optional[str] = None,
    #                              embedding_model_provider: Optional[str] = None,
    #                              original_document_id: Optional[str] = None, indexing_technique: str = "high_quality",
    #                              doc_language: Optional[str] = "Chinese", process_rule: str = "automatic",
    #                              rules: Optional[dict] = None, retrieval_model: Optional[dict] = None):
    #     """
    #     通过文件创建文档，只有存在知识库时才能使用
    #     :param database_name: 知识库名称
    #     :param doc_form: 索引内容的形式：
    #                 text_model text文档直接 embedding
    #                 hierarchical_model parent-child 模式
    #                 qa_model Q&A 模式：为分片文档生成 Q&A 对，然后对问题进行embedding
    #     :param file: 字典{"file": (filename, file)}
    #     :param embedding_model: Embedding 模型名称
    #     :param embedding_model_provider 模型供应商
    #     :param original_document_id: 源文档 ID,当传入 original_document_id时，process_rule为可填项目，否则process_rule必填
    #     :param indexing_technique: 索引方式 economy or high_quality 默认为high_quality高质量
    #     :param doc_language: 在 Q&A 模式下，指定文档的语言 e.g. English、Chinese 默认Chinese
    #     :param process_rule: 处理规则, automatic or custom。当为custom时，必须提交rules
    #     :param rules: 字典或者空
    #     :param retrieval_model:检索模式默认为空
    #     :return:
    #     """
    #     _, exist_db = self.get_exist_knowledge()
    #     database_id = exist_db.get(database_name)
    #     info = self.get_knowledge_documents_info(database_name)
    #     _process_rule = dict()
    #     if process_rule == "custom":
    #         _process_rule.update({"rules": rules})
    #     _process_rule.update({"mode": process_rule})
    #     url = f"{database_id}/document/create-by-file"
    #     data = {
    #         "indexing_technique": indexing_technique,
    #         "doc_form": doc_form,
    #         "process_rule": _process_rule,
    #     }
    #     if doc_form == "qa_model":
    #         data.update({"doc_language": doc_language})
    #     if not info["data"]:
    #         data.update({"retrieval_model": retrieval_model})
    #
    #     if embedding_model:
    #         data.update({"embedding_model": embedding_model})
    #     if embedding_model_provider:
    #         data.update({"embedding_model_provider": embedding_model_provider})
    #     try:
    #         response = self.client.build_request("POST", url, data={"data": json.dumps(data)},
    #                                                  files={"file": (file["filename"], file["data"])})
    #         _res = self.client.send(response)
    #         if _res.status_code == 200:
    #             _results = _res.json()
    #             logger.info(f"创建文档完成！知识库名称：{database_name}，知识库id：{database_id}")
    #             return "创建成功"
    #     except Exception as e:
    #         logger.error(f"创建文档失败：{e}")

    def create_documents_by_file(self, database_name: str, file: dict[str, tuple[str, BinaryIO]], doc_form: str = "text_model", retrieval_model: Optional[dict] = None,
                                 indexing_technique: str = "high_quality", doc_language: Optional[str] = "Chinese",
                                 process_rule: str = "automatic", custom_rules: Optional[dict] = None, original_document_id: Optional[str] = None,
                                 embedding_model: Optional[str] = None, embedding_model_provider: Optional[str] = None):
        """
        通过上传文件新建文档， 详细内容请参考http://61.172.179.77:5083/datasets?category=api中通过文件创建文档接口
        :param database_name: 知识库名称
        :param doc_form: 索引内容的形式 text_model、hierarchical_model、qa_model
        :param file: 上传的文件字典{"file": filename, file} file为open后文件
        :param retrieval_model: 当知识库未设置任何参数的时候，首次上传需要提供，未提供则使用默认选项
        :param indexing_technique: 索引方式
        :param doc_language: 当doc_form为qa_model需要提供，指定文档的语言 e.g:Chinese、English
        :param process_rule: 文件处理规则 automatic 自动处理 or custom自定义处理
        :param custom_rules: 如process_rule为automatic，需要上传的处理规则
        :param original_document_id: 源文档 ID，用于重新上传文档或修改文档清洗、分段配置，缺失的信息从源文档复制（具体还不知道什么意思）
        :param embedding_model: 嵌入模型名称
        :param embedding_model_provider: 嵌入模型来源
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        info = self.get_knowledge_documents_info(database_name)
        url = f"{database_id}/document/create-by-file"
        _process_rule = {"mode": process_rule}
        if process_rule == "custom":
            _process_rule.update({"rules": custom_rules})
        data = {
            "indexing_technique": indexing_technique,
            "doc_form": doc_form,
            "process_rule": _process_rule,
        }

        if original_document_id:
            # TODO: 待完善
            pass

        if doc_form == "qa_model":
            data.update({"doc_language": doc_language})

        if retrieval_model:
            data.update({"retrieval_model": retrieval_model})

        if embedding_model:
            data.update({"embedding_model": embedding_model})

        if embedding_model_provider:
            data.update({"embedding_model_provider": embedding_model_provider})

        try:
            response = self.client.build_request("POST", url, data={"data": json.dumps(data)}, files=file)
            _res = self.client.send(response)
            if _res.status_code == 200:
                _results = _res.json()
                logger.info(f"创建文档完成！知识库名称：{database_name}，知识库id：{database_id}")
                return "创建成功"
        except Exception as e:
            logger.error(f"创建文档失败：{e}")

    def update_documents_by_file(self, database_name: str, document_id: str, file: dict[str, tuple[str, BinaryIO]],
                                 indexing_technique: str = "high_quality", name: Optional[str] = None, process_rule: Optional[dict] = None):
        """
        通过文件更新文档，此接口基于已存在知识库，在此知识库的基础上通过文件更新文档的操作。
        :param database_name:
        :param document_id:
        :param file:
        :param indexing_technique:
        :param name:
        :param process_rule:
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        url = f"{database_id}/documents/{document_id}/update-by-file"

        data = {
            "indexing_technique": indexing_technique
        }

        if name:
            data.update({"name": name})

        if process_rule:
            data.update({"process_rule": process_rule})

        try:
            response = self.client.build_request("POST", url, data={"data": json.dumps(data)}, files=file)
            _res = self.client.send(response)
            if _res.status_code == 200:
                _results = _res.json()
                logger.info(f"更新文档完成！知识库名称：{database_name}，知识库id：{database_id}")
                return "更新成功"
        except Exception as e:
            logger.error(f"更新文档失败：{e}")

    def get_documents_statues(self, database_name: str, batch: str):
        """
        获取文档嵌入状态
        :param database_name:
        :param batch: 文档批次号
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        url = f"{database_id}/documents/{batch}/indexing-status"

        try:
            response = self.client.build_request("GET", url)
            _res = self.client.send(response)
            if _res.status_code == 200:
                _results = _res.json()
                logger.info(f"获取文档嵌入状态完成！知识库名称：{database_name}，知识库id：{database_id}")
                return _results
        except Exception as e:
            logger.error(f"获取文档嵌入状态失败：{e}")

    def delete_document(self, database_name: str, document_id: str):
        """
        删除文档
        :param database_name:
        :param document_id:
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        url = f"{database_id}/documents/{document_id}"
        try:
            response = self.client.build_request("DELETE", url)
            _res = self.client.send(response)
            if _res.status_code == 200 and _res.json()["result"] == "success":
                logger.info(f"删除文档完成！知识库名称：{database_name}，知识库id：{database_id}")
                return "删除成功"
        except Exception as e:
            logger.error(f"删除文档失败：{e}")

    def delete_segment(self, database_name: str, document_id: str, segment_id: str):
        """
        删除文档片段
        :param database_name:
        :param document_id:
        :param segment_id:
        :return:
        """
        all_info = self.get_documents_block_info(database_name, document_id=document_id)
        datas = all_info.get("data")
        for item in datas:
            if item.get('id') != segment_id:
                logger.info(f"删除文档片段失败，未找到文档片段：{segment_id}")
                return "删除失败"
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        url = f"{database_id}/documents/{document_id}/segments/{segment_id}"
        try:
            response = self.client.build_request("DELETE", url)
            _res = self.client.send(response)
            if _res.status_code == 200 and _res.json()["result"] == "success":
                logger.info(f"删除文档分段完成！知识库名称：{database_name}，文档id：{document_id}，分段id：{segment_id}")
                return "删除成功"
        except Exception as e:
            logger.error(f"删除文档失败：{e}")

    def add_segment(self, database_name: str, document_id: str, segments: List[dict]):
        """
        :param database_name:
        :param document_id:
        :param segments:[{"content": str, "answer": str | None, "keywords": list | None}]
        :return:
        """
        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        url = f"{database_id}/documents/{document_id}/segments"
        try:
            response = self.client.build_request("POST", url, json={"segments": segments})
            _res = self.client.send(response)
            if _res.status_code == 200:
                logger.info(f"添加文档分段完成！知识库名称：{database_name}，文档id：{document_id}")
                return "添加成功"
        except Exception as e:
            logger.error(f"添加文档失败：{e}")



    def search_document(self, query: str, database_name: str, retrieval_model: Optional[dict] = None):
        """
        向量库检索
        :param query:
        :param database_name:
        :param retrieval_model:
        :return:
        """

        _, exist_db = self.get_exist_knowledge()
        database_id = exist_db.get(database_name)
        data = {
            "query": query
        }

        if retrieval_model:
            data.update({"retrieval_model": retrieval_model})

        try:
            _req = self.client.build_request("POST", f"{database_id}/retrieve", json=data, timeout=600.0)
            _res = self.client.send(_req)
            _res.raise_for_status()
            if _res.status_code == 200:
                _results = _res.json()
                documents = list()
                for _res in _results["records"]:
                    document = dict()
                    document.update({"score": _res["score"], "child_chunks": _res["child_chunks"]})
                    document.update({"content": _res["segment"]["content"], "answer": _res["segment"]["answer"]})
                    documents.append(document)
                # logger.info(f"检索到的文档为：{documents}")
                return documents, _results["records"]
        except Exception as e:
            logger.error(f"搜索文档失败：{e}")

if __name__ == '__main__':
    # file_path = r"E:\tik_tok_live_assistant\datas\小海豚少儿百万全能保-问答.xlsx"
    service = KnowledgeBaseService()
    # res, result = service.search_document("几岁可以投保", "小海豚部分Q&A ")
    # print(res)
    # print()
    # print(result)
    # res = service.build_new_database("小海豚问答对", "Q&A检索")
    # print(res)
    # service.delete_database("测试1")
    # service.get_knowledge_documents_info("测试")
    # with open(file_path, "rb") as f:
    #     file = {"file": ("1.xlsx", f)}
    #     res = service.update_documents_by_file("测试1", "c5f6a2a2-27f3-4de2-af85-7e600c088c0c", file, name="1")
    #     print(res)
    # with open(file_path, "rb") as f:
    #     file = {"file": ("小海豚少儿百万全能保.xlsx", f)}
    #     _res = service.create_documents_by_file("小海豚问答对", file, doc_form="qa_model")
    # a, b = service.get_exist_knowledge()
    # print(a)
    # print()
    # print(b)
    # res = service.get_documents_block_info("小海豚问答对")
    # print(res)
    res = service.search_document("你好", "小海豚部分Q&A ")
    print(res)


