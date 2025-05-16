import logging
from copy import deepcopy
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.service.insurance_advisor_v2.advisor_prompt import get_template, ASSISTANT_PERSONALITY, ANSWER_BY_KNOWLEDGE, \
    MAIN_CLASSIFICATION_PROMPT, COLLECT_PROMPT, ANSWER_WITH_FORMER_QUESTION, COLLECT_ANSWER_PROMPT, \
    SECONDARY_MAIN_CLASSIFICATION_PROMPT
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
                      response_rule: Optional[str] = None):

        if kb_name:
            documents, _ = cls.kb_service.search_document(query=query, database_name=kb_name)
            logger.info(f"{query}从关联知识库中检索内容：\n{documents}")
            if not response_rule:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(kb_content=documents,
                                                                        bad_answer=bad_answer,
                                                                        question=query
                                                                        )
            else:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(kb_content=documents,
                                                                        bad_answer=bad_answer,
                                                                        question=query,
                                                                        response_rule=response_rule
                                                                        )
        else:
            if not response_rule:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(bad_answer=bad_answer,
                                                                        question=query
                                                                        )
            else:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(question=query,
                                                                        bad_answer=bad_answer,
                                                                        response_rule=response_rule
                                                                        )
        return input_prompt

    @classmethod
    async def classify_user_question(cls, query, industry: str, broadcast_topic: str, details: dict,
                                     category: str, junior: Optional[str] = None):
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
            # TODO：添加次级分类，提示词
            prompt = get_template(SECONDARY_MAIN_CLASSIFICATION_PROMPT).render(industry=industry,
                                                                               broadcast_topic=broadcast_topic,
                                                                               category_description=category_description,
                                                                               category='、'.join(category),
                                                                               junior=junior
                                                                               )
        else:
            prompt = get_template(MAIN_CLASSIFICATION_PROMPT).render(industry=industry,
                                                                     broadcast_topic=broadcast_topic,
                                                                     category_description=category_description,
                                                                     category='、'.join(category)
                                                                     )
        logger.info(f"意图分类的提示语：{prompt}")
        system = [SystemMessage(content=prompt)]
        user_prompt = f"客户输入：{query[-1].content}，分析客户的意图"
        msgs = [HumanMessage(content=user_prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        logger.info(f"意图分类模型返回结果：{_res.content}")
        classify = get_json_data(_res)
        return classify

    @classmethod
    async def collect_user_info(cls, state, previous_collect_intent = None):
        recorder = state["flow_guide"]
        if not previous_collect_intent:
            now_intent = recorder["now_intent"]
        else:
            now_intent = previous_collect_intent
        if recorder["classify_continue"]:
            _history = recorder["collect_pace"][f"{now_intent}"]["history"]
        else:
            _history = message_to_list_dict(state["messages"])
        config = state["assistant_config"]["assistant_config"]
        if "details" in config:
            details = config["details"]["details"][f"{now_intent}"]
            question = details["collect_cust_info"]
            q_len = len(question)
        else:
            question = config["collect_cust_info"]
            q_len = len(question)
        collect_prompt = get_template(COLLECT_PROMPT).render(questionlist=question)
        logger.info(f"collect_user_info的提示语：{collect_prompt}")
        system = [SystemMessage(content=collect_prompt)]
        msgs = [HumanMessage(content=f"<历史记录>\n{_history}，按照输出格式输入")]
        msgs.insert(0, *system)
        _res = await cls.llm.ainvoke(msgs, stream=False)
        logger.info(f"收集问题模型返回结果：{_res.content}")
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
    async def additional_questions(cls, state, unfinished_collect):
        recorder = state["flow_guide"]
        # recorder["hit_intent"].append(unfinished_collect[0])
        # recorder["now_intent"] = unfinished_collect[0]
        # if recorder.get("scend_intent"):
        #     del recorder["scend_intent"]
        _, collect, _ = await cls.collect_user_info(state, unfinished_collect[0])
        return collect, unfinished_collect[0], state


    @classmethod
    async def generate_collect_and_answer_prompt(cls, recorder, config, query, state, second_intent = None):
        werther_answer = ""
        details = config["details"]["details"]
        if len(recorder["now_intent"].split("||")) > 1:
            intent_now = recorder["now_intent"].replace("answer||", "")
            top = len(recorder["hit_intent"])
            if intent_now == recorder["hit_intent"][top - 2]:
                # xxx, answer||xxx
                collect_intent = intent_now
                if second_intent:
                    collect_details = details[collect_intent][second_intent]
                else:
                    collect_details = details[collect_intent]
                recorder, collect_prompt = await cls.collect_info(collect_intent, state)
                answer_prompt = cls.answer_prompt(query=query[-1].content,
                                                  bad_answer=config["bad_answer"],
                                                  kb_name=collect_details.get("kb_name"),
                                                  response_rule=collect_details.get("response_rule")
                                                  )
            else:
                # xx, answer||xxx
                collect_intent = intent_now
                if second_intent:
                    collect_details = details[collect_intent][second_intent]
                else:
                    collect_details = details[collect_intent]
                previous_collect_intent = recorder["hit_intent"][-2]
                werther_answer = previous_collect_intent
                recorder, collect_prompt = await cls.collect_info(collect_intent, state)
                if recorder["collect_pace"][collect_intent]["flag"] == 0:
                    flag, _, _ = await cls.collect_user_info(state, previous_collect_intent)
                    recorder["collect_pace"][f"{previous_collect_intent}"]["flag"] = flag
                answer_prompt = cls.answer_prompt(query=query[-1].content,
                                                  bad_answer=config["bad_answer"],
                                                  kb_name=collect_details.get("kb_name"),
                                                  response_rule=collect_details.get("response_rule")
                                                  )
        else:
            collect_intent = recorder["now_intent"]
            if second_intent:
                collect_details = details[collect_intent][second_intent]
            else:
                collect_details = details[collect_intent]
            recorder, collect_prompt = await cls.collect_info(collect_intent, state)
            answer_prompt = cls.answer_prompt(query=query[-1].content,
                                              bad_answer=config["bad_answer"],
                                              kb_name=collect_details.get("kb_name"),
                                              response_rule=collect_details.get("response_rule")
                                              )
        return collect_prompt, answer_prompt, collect_intent, werther_answer

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
            recorder["collect_pace"] = {"钝角": {"flag": 0,
                                                 "qa_list": []}}
        else:
            recorder.update({"classify_continue": True})
            recorder.update({"classify": assis_config["details"]["classify"]})
            if not recorder.get("hit_intent", None):
                recorder.update({"hit_intent": []})
            if not recorder.get("collect_pace", None):
                recorder["collect_pace"] = dict()
                for i in assis_config["details"]["classify"]:
                    if not assis_config["details"]["details"][i].get("collect_cust_info", None):
                        item = {i: {"flag": 1, "history": [], "qa_list": []}}
                    else:
                        item = {i: {"flag": 0, "history": [], "qa_list": []}}
                    recorder["collect_pace"].update(item)
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
        recorder = state["flow_guide"]
        system = get_template(ASSISTANT_PERSONALITY).render(industry=config["industry"],
                                                            broadcast_topic=config["broadcast_topic"],
                                                            elements="、".join(recorder["classify"])
                                                            )

        answer_prompt = get_template(ANSWER_WITH_FORMER_QUESTION).render(context=state["former_question"],
                                                                         query=query[-1].content)
        input_prompt = answer_prompt

        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{input_prompt}")
        system = [SystemMessage(content=system)]
        msgs = [HumanMessage(content=input_prompt)]
        copy_query.insert(0, *system)
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
                                                                   broadcast_topic=recorder["broadcast_topic"],
                                                                   elements="、".join(recorder["classify"])
                                                                   )

        if recorder["collect_pace"][recorder["now_intent"]]["flag"] == 0:
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
                                          bad_answer=config["bad_answer"]
                                          )

        prompt = answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        system = [SystemMessage(content=system_prompt)]
        msgs = [HumanMessage(content=prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        return {"messages": [_res]}

    @classmethod
    async def classify_question(cls, state):
        """
        初级意图分类
        """
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

        _res = await cls.classify_user_question(query=query,
                                                industry=config["industry"],
                                                broadcast_topic=config["broadcast_topic"],
                                                details=details,
                                                category=category
                                                )
        logger.info(f"{query[-1].content}初级分类结果：\n{_res}")

        # Save the current message to intent-specific history
        current_message = {
            "role": "user",
            "content": query[-1].content
        }

        intent_for_history = _res["问题类型"]
        if intent_for_history == "other":
            # 当问题类别为other时，不进行操作
            pass
        elif len(intent_for_history.split("||")) <= 1:
            # 当问题类别为answer or 命中的问题类型时
            if intent_for_history == "answer" and recorder.get("hit_intent"):
                intent_for_history = recorder["hit_intent"][-1]
            recorder["collect_pace"][intent_for_history]["history"].append(current_message)
        else:
            # 当问题类别为answer||命中的问题类型时
            intent_now = intent_for_history.split("||")[-1]
            if intent_now != recorder["hit_intent"][-1]:
                item = recorder["hit_intent"][-1]
                recorder["collect_pace"][item]["history"].append(current_message)
            recorder["collect_pace"][intent_now]["history"].append(current_message)

        if _res["问题类型"] == "other" or _res["问题类型"] == "answer":
            recorder["now_intent"] = _res["问题类型"]
            return {"flow_guide": recorder}
        else:
            recorder.update({"now_intent": _res["问题类型"]})
            if not recorder["hit_intent"]:
                recorder["hit_intent"].append(_res["问题类型"].replace("answer||", ""))
            else:
                if _res["问题类型"].replace("answer||", "") != recorder["hit_intent"][-1]:
                    recorder["hit_intent"].append(_res["问题类型"].replace("answer||", ""))
            return {"flow_guide": recorder}

    @classmethod
    def process_now_intent(cls, state):
        recorder = state["flow_guide"]
        if recorder.get("now_intent") == "other":
            return "junior_classify_is_other"
        elif recorder.get("now_intent") == "answer":
            return "answer_above_question"
        else:
            return "parse_junior_classify"

    @classmethod
    async def junior_classify_is_other(cls, state):
        """
        处理初级分类为other时的情况，即什么都没命中的情况
        """
        query = state["messages"]
        config = state["assistant_config"]["assistant_config"]
        copy_query = deepcopy(query)
        recorder = state["flow_guide"]

        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"],
                                                                   elements="、".join(recorder["classify"])
                                                                   )

        # TODO: 当初级意图没有命中我们规定的意图时，需求没有收集客户信息。
        answer_prompt = cls.answer_prompt(
            query=query[-1].content,
            bad_answer=config["bad_answer"]
        )
        prompt = answer_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        system = [SystemMessage(content=system_prompt)]
        msgs = [HumanMessage(content=prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)

        return {"messages": [_res]}


    @classmethod
    async def collect_info(cls, collect_intent, state):
        config = state["assistant_config"]["assistant_config"]
        recorder = state["flow_guide"]
        details = config["details"]["details"][collect_intent]
        collect_dict = dict()
        again_flag = 0
        if recorder["collect_pace"].get(f"{collect_intent}")["flag"] == 0:
            flag, collect, answer = await cls.collect_user_info(state, collect_intent)
            recorder["collect_pace"][f"{collect_intent}"]["flag"] = flag
            collect_dict.update({"collect": collect})
            again_flag = flag
        else:
            again_flag = -1

        # flag从0变成1，说明当前命中意图已经收集完，开始遍历命中意图列表中没有收集完的意图
        # 当again_flag为1或-1时，向前检索命中意图列表，获取为收集完的最近的意图；
        # 当again_flag为-1时，即当前意图收集在之前都已经收集完了，不需要返回cls.conclusion；
        # 当again_flag为1时，表示是经过历史记录提取后才变为1的，则需要返回cls.conclusion；
        # 当again_flag为0时，则表示当前命中意图没有收集完，收集该意图

        if again_flag == 0:
            collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(collect=collect_dict.get("collect"))
        else:
            pending_intent = recorder["hit_intent"][:-1]
            unfinished_collect = list()
            if pending_intent:
                for i in pending_intent[::-1]:
                    if recorder["collect_pace"][f"{i}"].get("flag", None) == 0:
                        unfinished_collect.append(i)
            else:
                pass
            if unfinished_collect:
                collect, previous, state = await cls.additional_questions(state, unfinished_collect)
                collect_dict = {"collect": collect, "previous": previous, "asking": True}
            else:
                collect_dict = dict()

            if again_flag == 1:
                collect_dict.update({"conclusion": cls.conclusion})

            if again_flag == -1 and not collect_dict:
                collect_dict = dict()

            if collect_dict:
                collect_prompt = get_template(COLLECT_ANSWER_PROMPT).render(
                    conclusion=collect_dict.get("conclusion"),
                    collect=collect_dict.get("collect"),
                    previous=collect_dict.get("previous"),
                    asking=collect_dict.get("asking")
                ).replace("None", "")
            else:
                collect_prompt = ""

        return recorder, collect_prompt

    @classmethod
    async def answer_above_question(cls, state):
        """
        处理初级分类为answer，即类别为只回答上下文的情况
        """
        query = state["messages"]
        copy_query = deepcopy(query)
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"],
                                                                   elements="、".join(recorder["classify"])
                                                                   )
        collect_intent = recorder["hit_intent"][-1]
        details = config["details"]["details"][collect_intent]
        recorder, collect_prompt = await cls.collect_info(collect_intent, state)
        answer_prompt = cls.answer_prompt(query=query[-1].content,
                                          bad_answer=config["bad_answer"],
                                          kb_name=details.get("kb_name"),
                                          response_rule=details.get("response_rule")
                                          )
        prompt = answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        system = [SystemMessage(content=system_prompt)]
        msgs = [HumanMessage(content=prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        assistant_message = {
            "role": "assistant",
            "content": _res.content
        }
        recorder["collect_pace"][collect_intent]["history"].append(assistant_message)
        return {"messages": [_res], "flow_guide": recorder}

    @classmethod
    def parse_junior_classify(cls, state):
        config = state["assistant_config"]["assistant_config"]
        recorder = state["flow_guide"]
        if "classify" not in config["details"]["details"][recorder["now_intent"].replace("answer||", "")]:
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
        werther_answer = ""
        query = state["messages"]
        copy_query = deepcopy(query)
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"],
                                                                   elements="、".join(recorder["classify"])
                                                                   )
        collect_prompt, answer_prompt, collect_intent, werther_answer = await cls.generate_collect_and_answer_prompt(recorder, config, query, state)
        prompt = answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        system = [SystemMessage(content=system_prompt)]
        msgs = [HumanMessage(content=prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        assistant_message = {
            "role": "assistant",
            "content": _res.content
        }
        recorder["collect_pace"][collect_intent]["history"].append(assistant_message)
        if werther_answer:
            recorder["collect_pace"][werther_answer]["history"].append(assistant_message)
        return {"messages": [_res], "flow_guide": recorder}


    @classmethod
    async def parse_scend_classify(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        junior_intent = recorder["now_intent"].replace("answer||", "")
        details = config["details"]["details"][junior_intent]
        second_intent = await cls.classify_user_question(query=query,
                                                         industry=recorder["industry"],
                                                         broadcast_topic=recorder["broadcast_topic"],
                                                         details=details,
                                                         category=details["classify"],
                                                         junior=f"{junior_intent}：{details['description']}"
                                                         )
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
        copy_query = deepcopy(query)
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"],
                                                                   elements="、".join(recorder["classify"])
                                                                   )
        collect_prompt, _, collect_intent, werther_answer = await cls.generate_collect_and_answer_prompt(
            recorder, config,
            query, state, recorder["scend_intent"])
        answer_prompt = cls.answer_prompt(
            query=query[-1].content,
            bad_answer=config["bad_answer"]
        )
        prompt = answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        system = [SystemMessage(content=system_prompt)]
        msgs = [HumanMessage(content=prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        assistant_message = {
            "role": "assistant",
            "content": _res.content
        }
        recorder["collect_pace"][collect_intent]["history"].append(assistant_message)
        if werther_answer:
            recorder["collect_pace"][werther_answer]["history"].append(assistant_message)
        return {"messages": [_res], "flow_guide": recorder}

    @classmethod
    async def answer_with_scend_intent(cls, state):
        query = state["messages"]
        copy_query = deepcopy(query)
        recorder = state["flow_guide"]
        config = state["assistant_config"]["assistant_config"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"],
                                                                   elements="、".join(recorder["classify"])
                                                                   )

        collect_prompt, answer_prompt, collect_intent, werther_answer = await cls.generate_collect_and_answer_prompt(
            recorder, config,
            query, state, recorder["scend_intent"])

        prompt = answer_prompt + "\n\n" + collect_prompt
        logger.info(f"用户输入：{query[-1].content}的提示词为：\n{prompt}")
        system = [SystemMessage(content=system_prompt)]
        msgs = [HumanMessage(content=prompt)]
        copy_query.insert(0, *system)
        copy_query[-1:] = msgs
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        _res = await cls.llm.ainvoke(copy_query, stream=False)
        assistant_message = {
            "role": "assistant",
            "content": _res.content
        }
        recorder["collect_pace"][collect_intent]["history"].append(assistant_message)
        if werther_answer:
            recorder["collect_pace"][werther_answer]["history"].append(assistant_message)
        return {"messages": [_res], "flow_guide": recorder}



