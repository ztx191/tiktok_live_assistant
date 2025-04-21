import logging
from copy import deepcopy
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime


from src.service.broadcast_assistant.assistant_prompt import get_template, ASSISTANT_PERSONALITY, ANSWER_BY_KNOWLEDGE, \
    MAIN_CLASSIFICATION_PROMPT
from src.service.knowledge_base_service import KnowledgeBaseService
from src.service.llm_service import LLMService
from src.service.result_service import get_json_data


logger = logging.getLogger(__name__)

class AssistantProcess:
    kb_service = KnowledgeBaseService()
    llm = LLMService().get_llm()

    @classmethod
    def answer_by_kb_or_bad_answer(cls, query: str, kb_name: Optional[str]= None, bad_answer: Optional[str] = None, response_rule: Optional[str] = None):
        if kb_name:
            documents, _ = cls.kb_service.search_document(query=query, database_name=kb_name)
            logger.info(f"{kb_name}检索结果：{documents}")
            if not response_rule:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(kb_content=documents,
                                                                        bad_answer=bad_answer,
                                                                        question=query)
            else:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(kb_content=documents,
                                                                        bad_answer=bad_answer,
                                                                        question=query,
                                                                        response_rule=response_rule)
        else:
            if not response_rule:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(bad_answer=bad_answer,
                                                                    question=query)
            else:
                input_prompt = get_template(ANSWER_BY_KNOWLEDGE).render(question=query,
                                                                    response_rule=response_rule)
        logger.info(f"answer_by_kb_or_bad_answer的提示语：{input_prompt}")
        return input_prompt

    @classmethod
    def classify_question(cls, question: str, industry: str, broadcast_topic: str, details: dict,
                          category: list, junior: Optional[str] = None):
        details = deepcopy(details)
        details.pop("description", None)
        details.pop("classify", None)
        details.pop("collect_cust_info", None)
        result = []
        for key, value in details.items():
            # if key == "通用":
            #     if not value.get("description", ""):
            #         description = f"除{all_classify}涵盖范围之外的所有问题。"
            #         value["description"] = description
            #     else:
            #         description = value.get('description', '')
            # else:
            description = value.get('description', '')
            result.append(f'- "{key}"：{description}')
        category_description = "\n".join(result)
        if junior:
            prompt = get_template(MAIN_CLASSIFICATION_PROMPT).render(industry=industry,
                                                                     broadcast_topic=broadcast_topic,
                                                                     category_description=category_description,
                                                                     category='、'.join(category),
                                                                     question=question,
                                                                     junior=junior)
        else:
            prompt = get_template(MAIN_CLASSIFICATION_PROMPT).render(industry=industry,
                                                                     broadcast_topic=broadcast_topic,
                                                                     category_description=category_description,
                                                                     category='、'.join(category),
                                                                     question=question)
        logger.info(f"intent_classify的提示语：{prompt}")
        msgs = [HumanMessage(content=prompt)]
        _res = cls.llm.invoke(msgs, stream=False)
        classify = get_json_data(_res)
        return classify

    @classmethod
    def begin_node(cls, state):
        recorder = dict()
        config = state["assistant_config"]
        recorder.update({"broadcast_topic": config["broadcast_topic"],
                         "industry": config["industry"]})
        assis_config = config["assistant_config"]
        if "details" not in assis_config:
            recorder.update({"first_continue": False,
                             "kb_name": assis_config["kb_name"],
                             "bad_answer": assis_config["bad_answer"]})
        else:
            recorder.update({"first_continue": True,
                             "bad_answer": assis_config["bad_answer"]})
        return {"flow_guide": recorder}

    @classmethod
    def judge_continue(cls, state):
        recorder = state["flow_guide"]
        if not recorder["first_continue"]:
            return "without_junior_classification"
        else:
            return "intent_classify"

    @classmethod
    def intent_classify(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        details_config = state["assistant_config"]["assistant_config"]["details"]
        category, details = details_config["classify"], details_config["details"]
        all_classify = deepcopy(category)
        all_classify.remove("通用")
        for key, value in details.items():
            if key == "通用":
                if not value.get("description", ""):
                    description = f"除{all_classify}涵盖范围之外的所有问题。"
                    value["description"] = description
        _res = cls.classify_question(question=query[-1].content, industry=recorder["industry"],
                                      broadcast_topic=recorder["broadcast_topic"],
                                      details=details, category=category)
        if _res["问题类型"] == "other":
            recorder.update({"first_category": "other"})
        else:
            first_category_details = details[_res["问题类型"]]
            recorder.update({"first_category": _res["问题类型"], "first_details": first_category_details})
        return {"flow_guide": recorder}

    @classmethod
    def parse_junior_other_classification(cls, state):
        recorder = state["flow_guide"]
        if "first_details" not in recorder:
            return "junior_classification_is_other"
        else:
            return "parse_junior_classification"

    @classmethod
    def parse_junior_classification(cls, state):
        recorder = state["flow_guide"]
        details = recorder["first_details"]
        if "kb_name" in details:
            bad_answer = f"用户想要询问的问题与{details['description']}相关，结合当前直播主题、用户需求和兜底话术：{recorder['bad_answer']}，回答用户问题"
            details.update({"bad_answer": bad_answer})
        else:
            description = f"用户想要询问的问题与{details['description']}相关"
            details["description"] = description
        return {"flow_guide": recorder}

    @classmethod
    def whether_secondary_classification(cls, state):
        recorder = state["flow_guide"]
        if "classify" not in recorder["first_details"]:
            return "answer_with_junior_classification"
        else:
            return "parse_secondary_classification"

    @classmethod
    def answer_with_junior_classification(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])
        logger.info(f"without_junior_classification的系统提示语：{system_prompt}")
        input_prompt = cls.answer_by_kb_or_bad_answer(query=query[-1].content,
                                                      kb_name=recorder["first_details"]["kb_name"],
                                                      bad_answer=recorder["first_details"]["bad_answer"])
        msgs = [HumanMessage(content=system_prompt + "\n" + input_prompt)]
        query[-1:] = msgs
        _res = cls.llm.invoke(query, stream=False)
        return {"messages": [_res]}

    @classmethod
    def parse_secondary_classification(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        _res = cls.classify_question(question=query[-1].content, industry=recorder["industry"],
                                     broadcast_topic=recorder["broadcast_topic"],
                                     details=recorder["first_details"], category=recorder["first_details"]["classify"],
                                     junior=recorder["first_details"]["description"])
        if _res["问题类型"] == "other":
            recorder.update({"second_category": "other"})
        else:
            second_details = recorder["first_details"][_res["问题类型"]]
            recorder.update({"second_category": _res["问题类型"], "second_details": second_details})
        return {"flow_guide": recorder}

    @classmethod
    def whether_secondary_classification_is_other(cls, state):
        recorder = state["flow_guide"]
        if "second_details" not in recorder:
            return "second_classification_is_other"
        else:
            return "answer_with_second_classification"

    @classmethod
    def second_classification_is_other(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])
        bad_answer = f"{recorder['first_details']['description']}，请结合用户意图和兜底话术：{recorder['bad_answer']}，回答用户问题"
        input_prompt = cls.answer_by_kb_or_bad_answer(query=query[-1].content,
                                                      bad_answer=bad_answer
                                                      )
        msgs = [HumanMessage(content=system_prompt + "\n" + input_prompt)]
        query[-1:] = msgs
        _res = cls.llm.invoke(query, stream=False)
        return {"messages": [_res]}

    @classmethod
    def answer_with_second_classification(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])
        if recorder["second_details"].get("kb_name"):
            input_prompt = cls.answer_by_kb_or_bad_answer(query=query[-1].content,
                                                          kb_name=recorder["second_details"]["kb_name"],
                                                          response_rule=recorder["second_details"]["response_rule"]
                                                          )
        else:
            input_prompt = cls.answer_by_kb_or_bad_answer(query=query[-1].content,
                                                          response_rule=recorder["second_details"]["response_rule"]
                                                          )
        msgs = [HumanMessage(content=system_prompt + "\n" + input_prompt)]
        query[-1:] = msgs
        _res = cls.llm.invoke(query, stream=False)
        return {"messages": [_res]}



    @classmethod
    def junior_classification_is_other(cls, state):
        query = state["messages"]
        recorder = state["flow_guide"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])
        logger.info(f"without_junior_classification的系统提示语：{system_prompt}")

        input_prompt = cls.answer_by_kb_or_bad_answer(query=query[-1].content,
                                                      bad_answer=recorder["bad_answer"])
        msgs = [HumanMessage(content=system_prompt + "\n" + input_prompt)]
        query[-1:] = msgs
        _res = cls.llm.invoke(query, stream=False)
        return {"messages": [_res]}


    @classmethod
    def without_junior_classification(cls, state):
        """
        :param state:query: [HumanMessage, ai_assistant]
        :return:
        """
        query = state["messages"]
        recorder = state["flow_guide"]
        system_prompt = get_template(ASSISTANT_PERSONALITY).render(industry=recorder["industry"],
                                                                   broadcast_topic=recorder["broadcast_topic"])
        logger.info(f"without_junior_classification的系统提示语：{system_prompt}")

        input_prompt = cls.answer_by_kb_or_bad_answer(query=query[-1].content, kb_name=recorder["kb_name"], bad_answer=recorder["bad_answer"])
        msgs = [HumanMessage(content=system_prompt + "\n" + input_prompt)]
        query[-1:] = msgs
        _res = cls.llm.invoke(query, stream=False)
        return {"messages": [_res]}

if __name__ == '__main__':
    from langgraph.graph import END, START, StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from src.service.broadcast_assistant.test import config
    import asyncio
    from src.service.broadcast_assistant.models import AgentState


    workflow = StateGraph(AgentState)
    workflow.add_node("begin_node", AssistantProcess.begin_node)
    workflow.add_node("without_junior_classification", AssistantProcess.without_junior_classification)
    workflow.add_node("answer_by_bad_answer", AssistantProcess.junior_classification_is_other)
    workflow.add_node("junior_classification_is_other", AssistantProcess.junior_classification_is_other)
    workflow.add_node("intent_classify", AssistantProcess.intent_classify)
    workflow.add_node("parse_junior_classification", AssistantProcess.parse_junior_classification)
    workflow.add_node("answer_with_junior_classification", AssistantProcess.answer_with_junior_classification)
    workflow.add_node("parse_secondary_classification", AssistantProcess.parse_secondary_classification)
    workflow.add_node("second_classification_is_other", AssistantProcess.second_classification_is_other)
    workflow.add_node("answer_with_second_classification", AssistantProcess.answer_with_second_classification)
    workflow.add_edge(START, "begin_node")
    workflow.add_conditional_edges(
        "begin_node",
        AssistantProcess.judge_continue,
        {
            "without_junior_classification": "without_junior_classification",
            "intent_classify": "intent_classify"
        }
    )

    workflow.add_conditional_edges(
        "intent_classify",
        AssistantProcess.parse_junior_other_classification,
        {
            "junior_classification_is_other": "junior_classification_is_other",
            "parse_junior_classification": "parse_junior_classification"
        }
    )

    workflow.add_conditional_edges(
        "parse_junior_classification",
        AssistantProcess.whether_secondary_classification,
        {
            "answer_with_junior_classification": "answer_with_junior_classification",
            "parse_secondary_classification": "parse_secondary_classification"
        }
    )

    workflow.add_conditional_edges(
        "parse_secondary_classification",
        AssistantProcess.whether_secondary_classification_is_other,
        {
            "second_classification_is_other": "second_classification_is_other",
            "answer_with_second_classification": "answer_with_second_classification"
        }
    )

    app = workflow.compile()

    while True:
        query = input("请输入问题：")
        res = app.invoke({"messages": [HumanMessage(content=query)], "assistant_config": config})
        print(res)


