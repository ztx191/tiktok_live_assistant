from typing import Optional, List, Any, Annotated
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain.tools import tool

class InputState(BaseModel):
    kb_name: dict[str, str] = {"初级分类": "小海豚部分Q&A ", "次级分类": "小海豚产品背景资料.md..."}
    intention_list: list = []


# class AgentState(TypedDict):
#     input: str
#     step_median_value: Optional[List[dict[str, Any]]]
#     input_state: InputState
#     messages: Annotated[list, add_messages]
#     qa_knowledge: Optional[list[dict[int, Any]]]
#     db_knowledge: Optional[list[dict[int, Any]]]
#     classify_summary: Optional[list[dict[str, Any]]]

class AgentState(TypedDict):
    input: str
    messages: Annotated[list, add_messages]
    assistant_config: dict[str, Any]
    flow_guide: dict
    former_question: dict


class QuestionQuerySummary(BaseModel):
    customer_questions: str = Field(description="客户提出的问题")
    question_in_list: str = Field(description="问题列表问题")
    is_matches: str = Field(description="是否匹配，是/否中的一个")
    question_answers: str = Field(description="问题对应的答案")

@tool("classify_question", args_schema=QuestionQuerySummary)
def classify_question(customer_questions: str, question_in_list: str, is_matches: str, question_answers: str):
    """从数据中提取出客户问题、问题列表问题、是否匹配、问题对应的答案对应的值"""
    return {
        "customer_questions": customer_questions,
        "question_in_list": question_in_list,
        "is_matches": is_matches,
        "question_answers": question_answers
    }

if __name__ == '__main__':
    test = InputState()
    # a = AgentState(input_state=test)
    # b = a["input_state"].kb_name
    # print(a["input_state"])
