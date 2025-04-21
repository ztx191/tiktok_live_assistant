import json
import logging
from src.service.knowledge_base_service import KnowledgeBaseService
from tqdm import tqdm

logger = logging.getLogger(__name__)




def index_question(questions: list):
    index_question_dict = dict()
    for i, question in enumerate(questions):
        index_question_dict.update({i: question})
    return index_question_dict

def retrieval_relevancy(questions_idx: dict, questions_base: str, top_k = 2, similarity_threshold = 0.8):
    service = KnowledgeBaseService()
    retrieval_model = {
        "search_method": "semantic_search",
        "reranking_enable": False,
        "top_k": top_k,
        "score_threshold_enabled": True,
        "score_threshold": similarity_threshold
    }
    q_to_q = dict()
    for i, question in tqdm(questions_idx.items()):
        result, _ = service.search_document(query=question, database_name=questions_base, retrieval_model=retrieval_model)
        if result:
            _res = set()
            for item in result:
                _res.add(item["content"])
            _res = list(_res)
            q_to_q.update({i: _res})
        else:
            q_to_q.update({i: result})
    return q_to_q



if __name__ == '__main__':
    data_path = r"./datas/新增问题.json"
    output_path = r"./datas/对比结果.json"
    datas = json.load(open(data_path, "r", encoding="utf-8"))
    res = retrieval_relevancy(datas, "小海豚问答对", top_k=2, similarity_threshold=0.8)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
    print(res)

