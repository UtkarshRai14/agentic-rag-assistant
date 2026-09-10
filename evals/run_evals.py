"""Run the offline evaluation experiment against the agent.

Run:  uv run python -m evals.run_evals

Evaluators:
  - correctness         (openevals LLM-as-judge, vs reference answer)
  - groundedness        (openevals RAG: answer supported by retrieved context)
  - retrieval_relevance (openevals RAG: retrieved context relevant to question)
  - cites_sources       (custom heuristic: did the answer cite anything)
"""

from __future__ import annotations

import re

from langchain_core.messages import ToolMessage
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import (
    CORRECTNESS_PROMPT,
    RAG_GROUNDEDNESS_PROMPT,
    RAG_RETRIEVAL_RELEVANCE_PROMPT,
)

from evals.create_dataset import DATASET_NAME
from rag_agent.agent import build_agent

JUDGE_MODEL = "openai:gpt-5.4-mini"

_agent = build_agent()  # no checkpointer: each example is independent


def target(inputs: dict) -> dict:
    """Invoke the agent and surface both the answer and the retrieved context."""
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": inputs["question"]}]}
    )
    answer = result["messages"][-1].text
    context = [
        m.content
        for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "retrieve_documents"
    ]
    return {"answer": answer, "context": context}


# --- evaluators ---------------------------------------------------------------

_correctness_judge = create_llm_as_judge(
    prompt=CORRECTNESS_PROMPT, model=JUDGE_MODEL, feedback_key="correctness"
)
_groundedness_judge = create_llm_as_judge(
    prompt=RAG_GROUNDEDNESS_PROMPT, model=JUDGE_MODEL, feedback_key="groundedness"
)
_relevance_judge = create_llm_as_judge(
    prompt=RAG_RETRIEVAL_RELEVANCE_PROMPT, model=JUDGE_MODEL, feedback_key="retrieval_relevance"
)


def correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    return _correctness_judge(
        inputs=inputs["question"],
        outputs=outputs["answer"],
        reference_outputs=reference_outputs["answer"],
    )


def groundedness(inputs: dict, outputs: dict) -> dict:
    context = outputs.get("context") or []
    if not context:
        return {"key": "groundedness", "score": None, "comment": "no retrieval context"}
    return _groundedness_judge(context="\n\n".join(context), outputs=outputs["answer"])


def retrieval_relevance(inputs: dict, outputs: dict) -> dict:
    context = outputs.get("context") or []
    if not context:
        return {"key": "retrieval_relevance", "score": None, "comment": "no retrieval context"}
    return _relevance_judge(inputs=inputs["question"], context="\n\n".join(context))


def cites_sources(inputs: dict, outputs: dict) -> dict:
    answer = outputs.get("answer", "")
    has_marker = bool(re.search(r"\[\d+\]|https?://|\(source:", answer, re.IGNORECASE))
    return {"key": "cites_sources", "score": bool(has_marker)}


def main() -> None:
    client = Client()
    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[correctness, groundedness, retrieval_relevance, cites_sources],
        experiment_prefix="rag-agent-baseline",
        metadata={"agent": "create_agent", "judge": JUDGE_MODEL},
        max_concurrency=4,
    )
    print(results)


if __name__ == "__main__":
    main()
