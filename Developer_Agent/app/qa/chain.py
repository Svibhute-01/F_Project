from app.llm import get_llm, structured_output_method
from app.qa.prompt import QA_PROMPT
from app.qa.schemas import QAPlan


def build_qa_chain():
    llm = get_llm(temperature=0.1)
    return QA_PROMPT | llm.with_structured_output(QAPlan, method=structured_output_method())


# Replaced by a scripted object in tests, exactly like the Developer chain.
qa_chain = build_qa_chain()
