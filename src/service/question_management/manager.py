import json
import logging
from typing import  List
from tqdm import tqdm

from src.connector.client import Clients
from src.service.knowledge_base_service import KnowledgeBaseService

class QuestionManager:
    kb_service = KnowledgeBaseService()


    @classmethod
    def get_new_and_old_question(cls, new_question, database_name: str):
        _res = cls.show_documents_block_by_kb(database_name=database_name)
        blocks, total = _res["block"], _res["total"]
        new_question = new_question["qa_list"]
        return {"new_problems": new_question, "existing_problems": blocks}


    @classmethod
    def show_documents_block_by_kb(cls, database_name: str):
        """
        通过知识库名称获取所有文档文本块
        :param database_name:
        :return:
        """
        blocks = cls.kb_service.get_documents_block_info(database_name=database_name)
        block_list = []
        for block in blocks:
            datas = block["data"]
            for i, data in enumerate(datas):
                block_list.append({"id": f"2-{i + 1}", "document_id": data["document_id"], "segment_id": data['id'],
                                   "content": data["content"], "answer": data["answer"]})
        return {"block": block_list, "total": len(block_list)}


    @classmethod
    def similar_question(cls, question: dict, database_name: str, top_k: int = 2, similarity_threshold: float = 0.8,
                         replace: bool = False, document_id: str | None = None):
        """
        获取与新增问题相同的问题
        :param question:
        :param database_name:
        :param top_k:
        :param similarity_threshold:
        :param replace: 是否替换标志
        :param document_id:
        :return:
        """
        content = question["content"]
        retrieval_model = {
            "search_method": "semantic_search",
            "reranking_enable": False,
            "top_k": top_k,
            "score_threshold_enabled": True,
            "score_threshold": similarity_threshold
        }
        _, results = cls.kb_service.search_document(query=content, database_name=database_name, retrieval_model=retrieval_model)
        qa_list = []
        if results:
            for _res in results:
                segment = _res["segment"]
                qa_list.append({"document_id": segment["document_id"], "segment_id": segment["id"],
                                "content": segment["content"], "answer": segment["answer"], "replace": replace})
        else:
            question.update({"into_place": document_id})
        return {"source": question, "qa_list": qa_list, "total": len(qa_list)}

    @classmethod
    def auto_merge_question(cls, new_question: dict, database_name: str):
        """
        自动合并新增问题，若新增问题与已有问题相似度大于0.8，合并；否则直接添加
        :param new_question:
        :param database_name:
        :return:
        """
        document_info = cls.kb_service.get_knowledge_documents_info(database_name=database_name)
        document_id = document_info["data"][0]["id"]
        qa_list = new_question.get("qa_list")
        for qa in tqdm(qa_list):
            _res = cls.similar_question(question=qa, database_name=database_name, top_k=1, replace=True, document_id=document_id)
            if _res["total"] > 0:
                cls.kb_service.delete_segment(database_name=database_name, document_id=_res["qa_list"][0]["document_id"],
                                              segment_id=_res["qa_list"][0]["segment_id"])
                # [{"content": str, "answer": str | None, "keywords": list | None}]
            new_qa = [{"content": qa["content"], "answer": qa["answer"]}]
            cls.kb_service.add_segment(database_name=database_name, document_id=document_id, segments=new_qa)
        logging.info("自动合并问题成功")
        print("自动合并问题成功")

    @classmethod
    def manual_merge_question(cls, new_question: List, database_name: str, similar_question: List):
        """
        手动合并新增问题
        :param new_question: 未匹配到已有问题的新增问题 {}
        :param database_name: 知识库名称
        :param similar_question: 已匹配到已有问题的新增问题
        :return:
        """
        pass











if __name__ == '__main__':
    # res = QuestionManager.similar_question(question={"content": "门诊一年的额度是多少？"}, database_name="小海豚问答对", top_k=2, similarity_threshold=0.8)
    # res = QuestionManager.show_documents_block_by_kb("小海豚问答对")
    # print(res)
    qa_path = r"./datas/新增问题和答案.json"
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_list = json.load(f)
    # QuestionManager.auto_merge_question(qa_list, "问题合并测试")
    # res = QuestionManager.show_documents_block_by_kb("问题合并测试")
    # print(res)
    # res = QuestionManager.similar_question(question={"content": "门诊一年的额度是多少？"}, database_name="问题合并测试", top_k=2, similarity_threshold=0.8)
    # print(res)
    res = QuestionManager.get_new_and_old_question(qa_list, "问题合并测试")
    print(res)