from src.service.knowledge_base_service import KnowledgeBaseService


class QuestionDataProcess:

    kb_service = KnowledgeBaseService()

    @classmethod
    def get_document_blocks(cls, database_name: str):
        """
        获取问答对向量数据库中所有文档块
        :param database_name: 数据库名称
        :return: 文档块列表
        """
        blocks = cls.kb_service.get_documents_block_info(database_name)
        qa_list = []
        for block in blocks:
            datas = block.get("data")
            for data in datas:
                qa_list.append({
                    "content": data.get("content"),
                    "answer": data.get("answer")
                })
        total = len(qa_list)
        return {"qa_list": qa_list, "total": total}


if __name__ == '__main__':
    res = QuestionDataProcess.get_document_blocks("小海豚问答对")
    print(res)