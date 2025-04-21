from langchain_core.messages import HumanMessage, AIMessage


def message_to_list_dict(messages):
    history_list = []
    for message in messages:
        if isinstance(message, HumanMessage):
            history_list.append({"role": "user", "content": message.content})
        if isinstance(message, AIMessage):
            history_list.append({"role": "assistant", "content": message.content})
    return history_list




# if __name__ == '__main__':
#     state = {'messages': [HumanMessage(content='什么是幸福尊享终身寿险', additional_kwargs={}, response_metadata={}, id='ad0bb76b-b49b-430b-b5bf-d69d16de430c'), AIMessage(content='幸福尊享终身寿险是一款终身保障的保险产品，主要为投保人提供终身的身故保障。它的保险合同由保险条款、保险单、投保单等相关文件共同构成，确保在投保人去世时，受益人能够获得相应的保险金。\n\n您之前有购买过保险吗?', additional_kwargs={}, response_metadata={'token_usage': {'prompt_tokens': 851, 'completion_tokens': 80, 'total_tokens': 931}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_b376dfbbd5', 'finish_reason': 'stop'}, id='run-9e555297-8718-4c63-ad81-965f0ae5689f-0', usage_metadata={'input_tokens': 851, 'output_tokens': 80, 'total_tokens': 931, 'input_token_details': {}, 'output_token_details': {}})], 'assistant_config': {'_id': 'Y2U5NmYzNmYtNWYxNC00NDI4LWE5NGQtOWM0ZmQ3OWUzNzlm', 'user_id': 'admin', 'broadcast_topic': '直播分享各类终身寿险产品', 'broadcast_room_id': '7654321', 'industry': '保险', 'UploadTime': 1743581977, 'assistant_config': {'opening_remarks': '尊敬的客户您好，我是您的专属顾问，有任何问题都可以问我。', 'hot_issues': '小海豚部分Q&A ', 'update_issues': False, 'bad_answer': '我好像有点没太明白你的意思呢，能不能换个方式再和我说一说', 'details': {'classify': ['通用', '幸福尊享终身寿险', '百年好合终身寿险'], 'details': {'通用': {'description': "询问关于保险销售技巧、保险常识相关的问题以及除['幸福尊享终身寿险', '百年好合终身寿险']涵盖范围之外的所有问题。", 'kb_name': '销售技巧', 'response_rule': '按照【知识库】回答用户问题'}, '幸福尊享终身寿险': {'description': '询间幸福尊享终身寿险产品相关的问题', 'collect_cust_info': 'asking_questions_1', 'kb_name': '幸福尊享终身寿险.md...', 'response_rule': '按照【知识库】回答用户问题'}, '百年好合终身寿险': {'description': '询问百年好合终身寿险产品相关的问题', 'collect_cust_info': 'asking_questions_2', 'classify': ['投保年龄', '保险期间', '其他'], '投保年龄': {'description': '询问百年好合终身寿险产品的投保年龄相关问题', 'response_rule': '本合同接受的投保年龄为出生满 28 日至 69 周岁。'}, '保险期间': {'description': '询间百年好合终身寿险产品的保险期间相关问题', 'response_rule': '本合同的保险期间为终身，自本合同生效日起算。'}, '其他': {'description': '询问关于百年好合终身寿险产品的其他问题', 'kb_name': '百年好合终身寿险.md...', 'response_rule': '按照【知识库】回答用户问题'}}}}, 'UploadTime': 1743581977}}, 'flow_guide': {'broadcast_topic': '直播分享各类终身寿险产品', 'industry': '保险', 'classify_continue': True, 'hit_intent': ['幸福尊享终身寿险'], 'collect_pace': {'通用': 0, '幸福尊享终身寿险': 0, '百年好合终身寿险': 0}, 'now_intent': '幸福尊享终身寿险'}, 'former_question': {'content': '否'}}
#     messages = state["messages"]
#     history = message_to_list_dict(messages)
#     print(history)