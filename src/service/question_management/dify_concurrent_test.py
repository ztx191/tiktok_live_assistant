import random
import threading
import time
from copy import deepcopy


from src.service.knowledge_base_service import KnowledgeBaseService


def get_blocks_id():
    res = KnowledgeBaseService().get_documents_block_info("测试", "86a9cf43-853b-4711-8056-c1df399240dc")
    blocks = [ i["id"] for i in res["data"]]
    return blocks

def delete_thread(blocks):
    document_id = "86a9cf43-853b-4711-8056-c1df399240dc"
    blocks = deepcopy(blocks)
    service = KnowledgeBaseService()
    print("删除文本块")
    for i in range(5):
        time.sleep(0.2)
        block_id = random.choice(blocks)
        service.delete_segment("测试", document_id, block_id)
        blocks.remove(block_id)
        print(f"删除文本块{block_id}")
        time.sleep(2)


def get_thread():
    document_id = "86a9cf43-853b-4711-8056-c1df399240dc"
    service = KnowledgeBaseService()
    print("获取文本块")
    for i in range(15):
        blocks = service.get_documents_block_info("测试", document_id)
        time.sleep(0.3)
        print(blocks)


def main(blocks):
    delete = threading.Thread(target=delete_thread, args=(blocks,))
    reader = threading.Thread(target=get_thread)

    # 启动线程
    delete.start()
    reader.start()

    # 等待线程结束
    delete.join()
    reader.join()

    print("测试完成")

if __name__ == '__main__':
    blocks = get_blocks_id()
    main(blocks)


