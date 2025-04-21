from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import logging

from src.service.broadcast_assistant.process_nodes import AssistantProcess
from src.service.broadcast_assistant.models import AgentState

logger = logging.getLogger(__name__)



class AssistantGraph:
    def __init__(self, assistant_config, memory_saver: bool = False):
        if memory_saver:
            self.memory = MemorySaver()
        else:
            self.memory = None

        self.assistant_config = assistant_config
        self.workflow = self.init_workflow()


    def init_workflow(self):
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
        if self.memory:
            app = workflow.compile(checkpointer=self.memory)
        else:
            app = workflow.compile()
        return app

    async def chat(self, query, thread_id = None) -> str:
        logger.info("用户的问题为: {}".format(query))
        input_message = HumanMessage(content=query)
        if self.memory:
            res = await self.workflow.ainvoke({"messages": [input_message], "assistant_config": self.assistant_config}, config=thread_id)
        else:
            res = await self.workflow.ainvoke({"messages": [input_message], "assistant_config": self.assistant_config})
        res = res["messages"][-1].content
        logger.info(f"用户{query}的回答为: \n{res}")
        return res


if __name__ == '__main__':
    from src.service.broadcast_assistant.test import config1
    workflow = AssistantGraph(config1)
    while True:
        query = input("请输入问题：")
        res = asyncio.run(workflow.chat(query))
        print(res)
