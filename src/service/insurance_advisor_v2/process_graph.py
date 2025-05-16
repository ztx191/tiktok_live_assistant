from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import logging

from src.service.insurance_advisor_v2.process_nodes import AdvisorProcess
from src.service.insurance_advisor_v2.models import AgentState

logger = logging.getLogger(__name__)



class AdvisorGraph:
    def __init__(self, memory_saver: bool = False):
        if memory_saver:
            self.memory = MemorySaver()
        else:
            self.memory = None
        self.workflow = self.init_workflow()


    def init_workflow(self):
        workflow = StateGraph(AgentState)

        # nodes
        workflow.add_node("begin_node", AdvisorProcess.begin_node)
        workflow.add_node("judge_former_question", AdvisorProcess.judge_former_question)
        workflow.add_node("answer_with_former_question", AdvisorProcess.answer_with_former_question)
        workflow.add_node("process_classify", AdvisorProcess.process_classify)
        workflow.add_node("without_classify", AdvisorProcess.without_classify)
        workflow.add_node("classify_question", AdvisorProcess.classify_question)
        workflow.add_node("junior_classify_is_other", AdvisorProcess.junior_classify_is_other)
        workflow.add_node("answer_above_question", AdvisorProcess.answer_above_question)
        workflow.add_node("parse_junior_classify", AdvisorProcess.parse_junior_classify)
        workflow.add_node("answer_with_junior_intent", AdvisorProcess.answer_with_junior_intent)
        workflow.add_node("parse_scend_classify", AdvisorProcess.parse_scend_classify)
        workflow.add_node("answer_with_scend_intent_is_other", AdvisorProcess.answer_with_scend_intent_is_other)
        workflow.add_node("answer_with_scend_intent", AdvisorProcess.answer_with_scend_intent)
        # edges
        workflow.add_edge(START, "begin_node")
        workflow.add_edge("begin_node", "judge_former_question")
        workflow.add_edge("answer_with_former_question", END)
        workflow.add_edge("without_classify", END)
        workflow.add_edge("answer_above_question", END)
        workflow.add_edge("answer_with_junior_intent", END)
        workflow.add_edge("answer_with_scend_intent_is_other", END)
        workflow.add_edge("answer_with_scend_intent", END)

        workflow.add_conditional_edges(
            "judge_former_question",
            AdvisorProcess.judge_former_continue,
            {
                "answer_with_former_question": "answer_with_former_question",
                "process_classify": "process_classify"
            }
        )

        workflow.add_conditional_edges(
            "process_classify",
            AdvisorProcess.werther_classify_continue,
            {
                "without_classify": "without_classify",
                "classify_question": "classify_question"
            }
        )

        workflow.add_conditional_edges(
            "classify_question",
            AdvisorProcess.process_now_intent,
            {
                "junior_classify_is_other": "junior_classify_is_other",
                "answer_above_question": "answer_above_question",
                "parse_junior_classify": "parse_junior_classify"
            }
        )

        workflow.add_conditional_edges(
            "parse_junior_classify",
            AdvisorProcess.werther_scend_classify,
            {
                "parse_scend_classify": "parse_scend_classify",
                "answer_with_junior_intent": "answer_with_junior_intent"
            }
        )

        workflow.add_conditional_edges(
            "parse_scend_classify",
            AdvisorProcess.werther_second_intent,
            {
                "answer_with_scend_intent": "answer_with_scend_intent",
                "answer_with_scend_intent_is_other": "answer_with_scend_intent_is_other"
            }
        )

        if self.memory:
            app = workflow.compile(checkpointer=self.memory)
        else:
            app = workflow.compile()
        return app

    def get_graph_png(self, output_path):
        from PIL import Image
        import io
        graph = self.workflow
        mermaid_code = graph.get_graph().draw_mermaid_png()
        image = Image.open(io.BytesIO(mermaid_code))
        image.save(output_path)

    async def chat(self, query, advisor_config, thread_id):
        logger.info("用户的问题为: {}".format(query))
        input_message = HumanMessage(content=query)
        if self.memory:
            res = await self.workflow.ainvoke({"messages": [input_message], "assistant_config": advisor_config},
                                              config=thread_id)
        else:
            res = await self.workflow.ainvoke({"input": query, "assistant_config": advisor_config})
        return res["messages"][-1].content, res
