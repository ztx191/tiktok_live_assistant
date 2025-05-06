import logging
from copy import deepcopy
from typing import Optional

from langchain_core.messages import HumanMessage

from src.service.insurance_advisor.advisor_prompt import get_template, ASSISTANT_PERSONALITY, ANSWER_BY_KNOWLEDGE, \
    MAIN_CLASSIFICATION_PROMPT, COLLECT_PROMPT, ANSWER_WITH_FORMER_QUESTION, COLLECT_ANSWER_PROMPT
from src.service.utils import message_to_list_dict
from src.service.knowledge_base_service import KnowledgeBaseService
from src.service.llm_service import LLMService
from src.service.result_service import get_json_data

logger = logging.getLogger(__name__)




class AdvisorProcess:
    kb_service = KnowledgeBaseService()
    llm = LLMService().get_llm()
    conclusion = r"如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"

    @classmethod
    def answer_prompt(cls, query: str, kb_name: Optional[str]= None, bad_answer: Optional[str] = None,
                      response_rule: Optional[str] = None, customer_intent: Optional[str] = None):
        if not customer_intent:
            customer_intent = ""
        if kb_name:
            documents, _ = cls.kb_service.search_document(query=query, database_name=kb_name)
            logger.info(f"{query}从关联知识库中检索内容：\n{documents}")
            if not response_rule:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(kb_content=documents,
                                                                        bad_answer=bad_answer,
                                                                        question=query,
                                                                        # customer_intent=customer_intent
                                                                        )
            else:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(kb_content=documents,
                                                                        bad_answer=bad_answer,
                                                                        question=query,
                                                                        response_rule=response_rule,
                                                                        # customer_intent=customer_intent
                                                                        )
        else:
            if not response_rule:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(bad_answer=bad_answer,
                                                                        question=query,
                                                                        # customer_intent=customer_intent
                                                                        )
            else:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(question=query,
                                                                        response_rule=response_rule,
                                                                        # customer_intent=customer_intent
                                                                        )
        return input_prompt

    @classmethod
    async def classify_user_question(cls, query, industry: str, broadcast_topic: str, details: dict,
                                     category: str, junior: Optional[str] = None, last_intent: Optional[str] = None):
        question = query[-1].content
        copy_query = deepcopy(query)
        details = deepcopy(details)
        details.pop("description", None)
        details.pop("classify", None)
        details.pop("collect_cust_info", None)
        result = []
        for key, value in details.items():
            description = value.get('description', '')
            result.append(f'- "{key}"：{description}')
        category_description = "\n".join(result)
        if junior:
            prompt = get_template(MAIN_CLASSIFICATION_PROMPT).render(industry=industry,
                                                                     broadcast_topic=broadcast_topic,
                                                                     category_description=category_description,
                                                                     category='、'.join(category),
                                                                     question=question,
                                                                     junior=junior,
                                                                     last_intent=last_intent)
        else:
            prompt = get_template(MAIN_CLASSIFICATION_PROMPT).render(industry=industry,
                                                                     broadcast_topic=broadcast_topic,
                                                                     category_description=category_description,
                                                                     category='、'.join(category),
                                                                     question=question,
                                                                     last_intent=last_intent)
        logger.info(f"intent_classify的提示语：{prompt}")
        msgs = [HumanMessage(content=prompt)]
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        classify = get_json_data(_res)
        # logger.info(f"返回结果：{classify}")
        return classify

    @classmethod
    async def collect_user_info(cls, state):
        # query = state["messages"]
        # history = message_to_list_dict(query)
        recorder = state["flow_guide"]
        now_intent = recorder["now_intent"].split("||")[-1]
        if recorder["classify_continue"]:
            _history = recorder["collect_pace"][f"{now_intent}"]["history"]
        else:
            _history = message_to_list_dict(state["messages"])
        config = state["assistant_config"]["assistant_config"]
        if "details" in config:
            details = config["details"]["details"][f"{now_intent}"]
            question = details["collect_cust_info"]
            # questions_db = details["collect_cust_info"]
            # question = Clients.get_mongo()[questions_db].find_one()
            # question = question["question_list"]
            q_len = len(question)
        else:
            question = config["collect_cust_info"]
            # questions_db = config["collect_cust_info"]
            # question = Clients.get_mongo()[questions_db].find_one()
            # question = question["question_list"]
            q_len = len(question)
        # list_qa = recorder["collect_pace"][f"{now_intent}"]["qa_list"]
        # if list_qa:
        #     q_list = [qa["q"] for qa in list_qa if qa["a"] != ""]
        #     collect_prompt = get_template(COLLECT_PROMPT).render(questionlist=question, history=history, qa_list=q_list)
        # else:
        collect_prompt = get_template(COLLECT_PROMPT).render(questionlist=question, history=_history)
        logger.info(f"collect_user_info的提示语：{collect_prompt}")
        msgs = [HumanMessage(content=collect_prompt)]
        _res = await cls.llm.ainvoke(msgs, stream=False)
        _res = get_json_data(_res)
        recorder["collect_pace"][f"{now_intent}"]["qa_list"] = _res["问答"]
        qa_list = _res["问答"]
        cnt = 0
        if qa_list:
            for qa in qa_list:
                if qa["a"] or qa["a"] != "无":
                    cnt += 1
        if cnt == q_len:
            _res["终止"] = 1
        logger.info(f"收集问题的返回结果：{_res}")
        return _res["终止"], _res["问题"], _res["问答"]

    @classmethod
    def get_every_intent_answer(cls, recorder, _res):
        if "other||" in recorder["now_intent"]:
            current_intent = recorder["now_intent"].split("||")[-1]
        else:
            current_intent = recorder["now_intent"]
        if "history" not in recorder["collect_pace"][current_intent]:
            recorder["collect_pace"][current_intent]["history"] = []
        assistant_message = {
            "role": "assistant",
            "content": _res.content
        }
        recorder["collect_pace"][current_intent]["history"].append(assistant_message)
        return recorder

    @classmethod
    def begin_node(cls, state):
        """
        获取配置，是否进行用户分类
        :param state:
        :return:
        """
        if not state.get("flow_guide", None):
            recorder = dict()
        else:
            recorder = state["flow_guide"]
        config = state["assistant_config"]
        recorder.update({"broadcast_topic": config["broadcast_topic"],
                         "industry": config["industry"]})
        assis_config = config["assistant_config"]
        if "details" not in assis_config:
            recorder.update({"classify_continue": False})
            recorder.update({"now_intent": "钝角"})
            recorder["collect_pace"] = {"钝角": {"flag":0,
                                                 "qa_list": []}}
        else:
            recorder.update({"classify_continue": True})
            if not recorder.get("hit_intent", None):
                recorder.update({"hit_intent": []})
            if not recorder.get("collect_pace", None):
                recorder["collect_pace"] = dict()
                for i in assis_config["details"]["classify"]:
                    recorder["collect_pace"].update({i: {"flag":0,
                                                         "history": [],
                                                         "qa_list": []}})
        return {"flow_guide": recorder}

    @classmethod
    async def judge_former_question(cls, state):
        """
        向量库检索用户当前输入，模型判断已有问题是否能回答用户
        :param state:
        :return:
        """
        query = state["messages"]
        # query = state["input"]
        config = state["assistant_config"]["assistant_config"]
        retrieval_model = {
            "search_method": "hybrid_search",
            "score_threshold_enabled": True,
            "reranking_enable": True,
            "reranking_mode": {
                "reranking_provider_name": "Newtouch Apihub",
                "reranking_model_name": "bge-reranker-large"
            },
            "top_k": 2,
            "score_threshold": 0.9
        }
        kb_content, _ = cls.kb_service.search_document(query=query[-1].content, database_name=config["hot_issues"],
                                                       retrieval_model=retrieval_model)
        if not kb_content:
            _res = {"content": "否"}
        else:
            answers = list()
            for content in kb_content:
                if not content["answer"]:
                    answers.append(content["content"])
                else:
                    ans = {"content": content["content"], "answer": content["answer"]}
                    answers.append(ans)
            _res = {"content": answers}
        logger.info(f"{query[-1].content}从热点问题检索内容为：\n{kb_content}")
        # input_prompt = get_template(JUDGMENT_FORMER_QUESTION).render(context=kb_content, query=query[-1].content)
        # msgs = [HumanMessage(content=input_prompt)]
        # _res = await cls.llm.ainvoke(msgs, stream=False)
        # _res = get_json_data(_res)
        # logger.info(f"{query[-1].content}匹配已有问题结果为：\n{_res}")
        return {"former_question": _res}

    @classmethod
    def judge_former_continue(cls, state):
        """
        判断是否用已有问题回答
        :param state:
        :return:
        """
        res = state["former_question"]
        if res["content"] != "否":
            return "answer_with_former_question"
        else:
            return "process_classify"

    @classmethod
    async def answer_with_former_question(cls, state):
        """
        用已有问题回答
        :param state:
        :return:
        """
        query = state["messages"]
        copy_query = deepcopy(query)
        config = state["assistant_config"]
        system = get_template(ASSISTANT_PERSONALITY).render(industry=config["industry"],
                                                            broadcast_topic=config["broadcast_topic"])
        # TODO: 目前没有考虑用已知问题回答客户问题后是否收集信息
        if config.get("collect_cust_info", None):
            flag, collect, answer = await cls.collect_user_info(state)
            if answer != "无":
                pass
            if flag == 1:
                collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(conclusion=cls.conclusion)
            else:
                collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(collect=collect)
        else:
            collect_prompt = ""

        answer_prompt = get_template(ANSWER_WITH_FORMER_QUESTION).render(context=state["former_question"],
                                                                  query=query[-1].content)
        input_prompt = system + "\n\n" + answer_prompt + "\n\n" + collect_prompt

        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{input_prompt}")
        msgs = [HumanMessage(content=input_prompt)]
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        return {"messages": [_res]}

    @classmethod
    def process_classify(cls, state):
        return {"flow_guide": state["flow_guide"]}

    @classmethod
    def werther_classify_continue(cls, state):
        """
        判断是否进行用户意图分类，走哪个分支
        :param state:
        :return:
        """
        condition = state["flow_guide"]
        if not condition["classify_continue"]:
            return "without_classify"
        else:
            return "classify_question"

    @classmethod
    async def without_classify(cls, state):
        """
        不需要用户意图分类
        :param state:
        :return:
        """
        query = state["messages"]
        copy_query = deepcopy(query)
        config = state["assistant_config"]["assistant_config"]
        recorder = state["flow_guide"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])

        if config.get("collect_cust_info", None) and recorder["collect_pace"][recorder["now_intent"]]["flag"] == 0:
            flag, collect, answer = await cls.collect_user_info(state)
            recorder["collect_pace"][recorder["now_intent"]]["flag"] = flag
            if flag == 1:
                collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(conclusion=cls.conclusion)
            else:
                collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(collect=collect)
        else:
            collect_prompt = ""

        answer_prompt = cls.answer_prompt(query=query[-1].content,
                                          kb_name=config["kb_name"],
                                          bad_answer=config["bad_answer"])

        prompt = system_prompt + "\n\n" + answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        msgs = [HumanMessage(content=prompt)]
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        return {"messages": [_res]}

    @classmethod
    async def classify_question(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        config = state["assistant_config"]
        details_config = config["assistant_config"]["details"]
        category, details = details_config["classify"], details_config["details"]
        all_classify = deepcopy(category)
        all_classify.remove("通用")
        for key, value in details.items():
            if key == "通用":
                if not value.get("description", ""):
                    description = f"除{all_classify}涵盖范围之外的所有问题。"
                else:
                    description = f'{value["description"]}' + f"以及除{all_classify}涵盖范围之外的所有问题。"
                value["description"] = description
        if recorder.get("hit_intent"):
            _res = await cls.classify_user_question(query=query,
                                                    industry=config["industry"],
                                                    broadcast_topic=config["broadcast_topic"],
                                                    details=details,
                                                    category=category,
                                                    # last_intent=recorder["hit_intent"][-1]
                                                    )
        else:
            _res = await cls.classify_user_question(query=query,
                                                    industry=config["industry"],
                                                    broadcast_topic=config["broadcast_topic"],
                                                    details=details,
                                                    category=category)
        logger.info(f"{query[-1].content}初级分类结果：\n{_res}")

        # Save the current message to intent-specific history
        current_message = {
            "role": "user",
            "content": query[-1].content
        }

        # Determine which intent to use for history tracking
        intent_for_history = _res["问题类型"]
        if intent_for_history == "other" and recorder.get("hit_intent"):
            intent_for_history = recorder["hit_intent"][-1]

        # Save message to the appropriate intent history
        if intent_for_history in recorder["collect_pace"]:
            if "history" not in recorder["collect_pace"][intent_for_history]:
                recorder["collect_pace"][intent_for_history]["history"] = []
            recorder["collect_pace"][intent_for_history]["history"].append(current_message)

        # Update the current intent
        if _res["问题类型"] != "other":
            recorder.update({"now_intent": _res["问题类型"]})
            if not recorder["hit_intent"]:
                recorder["hit_intent"].append(_res["问题类型"])
            elif _res["问题类型"] not in recorder["hit_intent"][-1]:
                recorder["hit_intent"].append(_res["问题类型"])
            else:
                pass
            return {"flow_guide": recorder}
        else:
            recorder["now_intent"] = _res["问题类型"]
            return {"flow_guide": recorder}

    @classmethod
    def process_now_intent(cls, state):
        recorder = state["flow_guide"]
        if not recorder.get("hit_intent", None):
            return "junior_classify_is_other"
        elif recorder["now_intent"] == "other":
            recorder["now_intent"] = f'other||{recorder["hit_intent"][-1]}'
            return "junior_classify_is_other"
        else:
            return "parse_junior_classify"


    @classmethod
    async def additional_questions(cls, state, unfinished_collect):
        recorder = state["flow_guide"]
        recorder["hit_intent"].append(unfinished_collect[0])
        recorder["now_intent"] = unfinished_collect[0]
        if recorder.get("scend_intent"):
            del recorder["scend_intent"]
        _, collect, _ = await cls.collect_user_info(state)
        return collect, state


    @classmethod
    async def junior_classify_is_other(cls, state):
        query = state["messages"]
        config = state["assistant_config"]["assistant_config"]
        copy_query = deepcopy(query)
        recorder = state["flow_guide"]

        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])

        if recorder.get("now_intent") == "other":
            # TODO: 当初级意图没有命中我们规定的意图时，需求没有收集客户信息。目前是按照收集客户信息，但是下面代码不可能触发，collect_prompt为空。
            if recorder.get("collect_cust_info", None):
                flag, collect, answer = await cls.collect_user_info(state)
                if flag == 1:
                    collect = "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
                collect_prompt = f"# 回答客户问题后你需要通过问答收集客户信息，\n## 待问问题尽量原文转述。\n待问内容：{collect}"
            else:
                collect_prompt = ""
            answer_prompt = cls.answer_prompt(
                query=query[-1].content,
                bad_answer=config["bad_answer"]
            )
            prompt = system_prompt + "\n\n" + answer_prompt + "\n\n" + collect_prompt
        else:
            now_intent = recorder["now_intent"].split("||")[-1]
            details = config["details"]["details"][f"{now_intent}"]
            if details.get("collect_cust_info", None) and recorder["collect_pace"].get(f"{now_intent}")["flag"] == 0:
                flag, collect, answer = await cls.collect_user_info(state)
                collect = {"collect": collect}
                recorder["collect_pace"][f"{now_intent}"]["flag"] = flag
                if flag == 1:
                    pending_intent = recorder["hit_intent"][:-1]
                    if pending_intent:
                        unfinished_collect = list()
                        for i in pending_intent[::-1]:
                            if recorder["collect_pace"][f"{i}"].get("flag", None) == 0:
                                unfinished_collect.append(i)
                        if unfinished_collect:
                            collect, state = await cls.additional_questions(state, unfinished_collect)
                            recorder = state["flow_guide"]
                            collect = {"conclusion": cls.conclusion, "collect": collect, "asking": True}
                                # ("如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com" +
                                #        "\n" + f"对于上一次提问您的问题：{collect}能否回答一下？")
                        else:
                            collect = {"conclusion": cls.conclusion}
                                # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
                    else:
                        collect = {"conclusion": cls.conclusion}
                            # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
                collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(
                    conclusion=collect.get("conclusion"),
                    collect=collect.get("collect"),
                    asking=collect.get("asking")
                ).replace("None", "")
                    # f"# 回答客户问题后你需要通过问答收集客户信息，\n## 待问问题尽量原文转述。\n待问内容：{collect}"
                answer_prompt = cls.answer_prompt(query=query[-1].content,
                                                  bad_answer=config["bad_answer"],
                                                  customer_intent=details["description"]
                                                  )

            else:
                collect_prompt = ""
                answer_prompt = cls.answer_prompt(query=query[-1].content,
                                                  bad_answer=config["bad_answer"],
                                                  kb_name=details["kb_name"],
                                                  customer_intent=details["description"]
                                              )
            prompt = system_prompt + "\n\n" + answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        msgs = [HumanMessage(content=prompt)]
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)

        # 保存助手回复到相应的意图历史
        if recorder["now_intent"] != "other":
            recorders = cls.get_every_intent_answer(recorder, _res)
        else:
            recorders = recorder
        # current_intent = recorder["now_intent"]
        # if recorder["now_intent"] != "other":
        #     current_intent = recorder["now_intent"].split("||")[-1]

        # if current_intent in recorder["collect_pace"]:
        #     if "history" not in recorder["collect_pace"][current_intent]:
        #         recorder["collect_pace"][current_intent]["history"] = []
        #     assistant_message = {
        #         "role": "assistant",
        #         "content": _res.content
        #     }
        #     recorder["collect_pace"][current_intent]["history"].append(assistant_message)

        return {"messages": [_res], "flow_guide": recorders}
    @classmethod
    def parse_junior_classify(cls, state):
        config = state["assistant_config"]["assistant_config"]
        recorder = state["flow_guide"]
        if "classify" not in config["details"]["details"][recorder["now_intent"]]:
            if recorder.get("scend_intent"):
                del recorder["scend_intent"]
            return {"flow_guide": recorder}
        else:
            recorder["scend_intent"] = "钝角"
            return {"flow_guide": recorder}

    @classmethod
    def werther_scend_classify(cls, state):
        recorder = state["flow_guide"]
        if recorder.get("scend_intent", None):
            return "parse_scend_classify"
        else:
            return "answer_with_junior_intent"

    @classmethod
    async def answer_with_junior_intent(cls, state):
        query = state["messages"]
        copy_query = deepcopy(query)
        config = state["assistant_config"]["assistant_config"]
        recorder = state["flow_guide"]
        details = config["details"]["details"][recorder["now_intent"]]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])
        if details.get("collect_cust_info", None) and recorder["collect_pace"].get(recorder["now_intent"])["flag"] == 0:
            flag, collect, answer = await cls.collect_user_info(state)
            collect = {"collect": collect}
            recorder["collect_pace"][recorder["now_intent"]]["flag"] = flag
            if flag == 1:
                pending_intent = recorder["hit_intent"][:-1]
                if pending_intent:
                    unfinished_collect = list()
                    for i in pending_intent[::-1]:
                        if recorder["collect_pace"][f"{i}"].get("flag", None) == 0:
                            unfinished_collect.append(i)
                    if unfinished_collect:
                        collect, state = await cls.additional_questions(state, unfinished_collect)
                        recorder = state["flow_guide"]
                        collect = {"conclusion": cls.conclusion, "collect": collect, "asking": True}
                            # ("如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com" +
                            #        "\n" + f"对于上一次提问您的问题：{collect}能否回答一下？")
                    else:
                        collect = {"conclusion": cls.conclusion}
                            # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
                else:
                    collect = {"conclusion": cls.conclusion}
                        # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
            collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(
                conclusion=collect.get("conclusion"),
                collect=collect.get("collect"),
                asking=collect.get("asking")
            ).replace("None", "")
                # f"# 回答客户问题后你需要通过问答收集客户信息，\n## 待问问题尽量原文转述。\n待问内容：{collect}"
        else:
            collect_prompt = ""
        answer_prompt = cls.answer_prompt(query=query[-1].content,
                                   kb_name=details.get("kb_name"),
                                   response_rule=details.get("response_rule"),
                                   bad_answer=config["bad_answer"],
                                   customer_intent=details["description"])
        # prompt = system_prompt + "\n" + collect_prompt + "\n" + answer
        prompt = system_prompt + "\n\n" + answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        msgs = [HumanMessage(content=prompt)]
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        # 保存助手回复到相应的意图历史
        recorders = cls.get_every_intent_answer(recorder, _res)
        return {"messages": [_res], "flow_guide": recorders}

    @classmethod
    async def parse_scend_classify(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        details = config["details"]["details"][recorder["now_intent"]]
        if recorder.get("hit_intent"):
            second_intent = await cls.classify_user_question(query=query,
                                                             industry=recorder["industry"],
                                                             broadcast_topic=recorder["broadcast_topic"],
                                                             details=details,
                                                             category=details["classify"],
                                                             junior=details["description"],
                                                             # last_intent=recorder["hit_intent"][-1]
                                                             )
        else:
            second_intent = await cls.classify_user_question(query=query,
                                                       industry=recorder["industry"],
                                                       broadcast_topic=recorder["broadcast_topic"],
                                                       details=details,
                                                       category=details["classify"],
                                                       junior=details["description"])
        logger.info(f"用户输入：{query[-1].content}的次级分类为：\n{second_intent}")
        recorder.update({"scend_intent": second_intent["问题类型"]})
        return {"flow_guide": recorder}

    @classmethod
    def werther_second_intent(cls, state):
        recorder = state["flow_guide"]
        if recorder.get("scend_intent") == "other":
            return "answer_with_scend_intent_is_other"
        else:
            return "answer_with_scend_intent"

    @classmethod
    async def answer_with_scend_intent_is_other(cls, state):
        query = state["messages"]
        deep_query = deepcopy(query)
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])

        details = config["details"]["details"][recorder["now_intent"]]
        if details.get("collect_cust_info", None) and recorder["collect_pace"].get(recorder["now_intent"])["flag"] == 0:
            flag, collect, answer = await cls.collect_user_info(state)
            collect = {"collect": collect}
            recorder["collect_pace"][recorder["now_intent"]]["flag"] = flag
            if flag == 1:
                pending_intent = recorder["hit_intent"][:-1]
                if pending_intent:
                    unfinished_collect = list()
                    for i in pending_intent[::-1]:
                        if recorder["collect_pace"][f"{i}"].get("flag", None) == 0:
                            unfinished_collect.append(i)
                    if unfinished_collect:
                        collect, state = await cls.additional_questions(state, unfinished_collect)
                        recorder = state["flow_guide"]
                        collect = {"conclusion": cls.conclusion, "collect": collect, "asking": True}
                            # ("如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com" +
                            #        "\n" + f"对于上一次提问您的问题：{collect}能否回答一下？")
                    else:
                        collect = {"conclusion": cls.conclusion}
                            # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
                else:
                    collect = {"conclusion": cls.conclusion}
                        # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
            collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(
                conclusion=collect.get("conclusion"),
                collect=collect.get("collect"),
                asking=collect.get("asking")
            ).replace("None", "")
                # f"# 回答客户问题后你需要通过问答收集客户信息，\n## 待问问题尽量原文转述。\n待问内容：{collect}"
        else:
            collect_prompt = ""

        answer_prompt = cls.answer_prompt(query=query[-1].content,
                                          bad_answer=config["bad_answer"],
                                          customer_intent=details["description"])
        prompt = system_prompt + "\n\n" + answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        msgs = [HumanMessage(content=prompt)]
        deep_query[-1:] = msgs
        _res = await cls.llm.ainvoke(deep_query, stream=False)
        # 保存助手回复到相应的意图历史
        recorders = cls.get_every_intent_answer(recorder, _res)

        return {"messages": [_res], "flow_guide": recorders}

    @classmethod
    async def answer_with_scend_intent(cls, state):
        query = state["messages"]
        deep_query = deepcopy(query)
        recorder = state["flow_guide"]
        second_intent = recorder["scend_intent"]
        config = state["assistant_config"]["assistant_config"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])

        details = config["details"]["details"][recorder["now_intent"]]
        scend_details = details[recorder["scend_intent"]]
        customer_intent = f"{details['description']}中的{scend_details['description']}"
        if details.get("collect_cust_info", None) and recorder["collect_pace"].get(recorder["now_intent"])["flag"] == 0:
            flag, collect, answer = await cls.collect_user_info(state)
            collect = {"collect": collect}
            recorder["collect_pace"][recorder["now_intent"]]["flag"] = flag
            if flag == 1:
                pending_intent = recorder["hit_intent"][:-1]
                if pending_intent:
                    unfinished_collect = list()
                    for i in pending_intent[::-1]:
                        if recorder["collect_pace"][f"{i}"].get("flag", None) == 0:
                            unfinished_collect.append(i)
                    if unfinished_collect:
                        collect, state = await cls.additional_questions(state, unfinished_collect)
                        recorder = state["flow_guide"]
                        collect = {"conclusion": cls.conclusion, "collect": collect, "asking": True}
                            # ("如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com" +
                            #        "\n" + f"对于上一次提问您的问题：{collect}能否回答一下？")
                    else:
                        collect = {"conclusion": cls.conclusion}
                            # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
                else:
                    collect = {"conclusion": cls.conclusion}
                        # "如果可以请留下你的电话号码，有意向请访问链接：https://www.baidu.com"
            collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(
                conclusion=collect.get("conclusion"),
                collect=collect.get("collect"),
                asking=collect.get("asking")
            ).replace("None", "")
                # f"# 回答客户问题后你需要通过问答收集客户信息，\n## 待问问题尽量原文转述。\n待问内容：{collect}"
        else:
            collect_prompt = ""
        if details[second_intent].get("kb_name", None):
            answer_prompt = cls.answer_prompt(query=query[-1].content,
                                              kb_name=details[second_intent].get("kb_name"),
                                              response_rule=details[second_intent].get("response_rule"),
                                              bad_answer=config["bad_answer"],
                                              customer_intent=customer_intent)
        else:
            answer_prompt = cls.answer_prompt(query=query[-1].content,
                                              bad_answer=config["bad_answer"],
                                              customer_intent=customer_intent,
                                              response_rule=details[second_intent].get("response_rule"))
        prompt = system_prompt + "\n\n" + answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        msgs = [HumanMessage(content=prompt)]
        deep_query[-1:] = msgs
        _res = await cls.llm.ainvoke(deep_query, stream=False)
        # 保存助手回复到相应的意图历史
        recorders = cls.get_every_intent_answer(recorder, _res)

        return {"messages": [_res], "flow_guide": recorders}





