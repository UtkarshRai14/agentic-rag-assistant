"""Comparative (pairwise) experiment: heavy vs fast model on the same dataset.

Runs two experiments, then an LLM judge picks the better answer per example.
The result is a side-by-side comparison view in the LangSmith UI.

Run:  uv run python -m evals.run_pairwise
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langsmith import Client
from langsmith.evaluation import evaluate_comparative

from evals.create_dataset import DATASET_NAME
from rag_agent.agent import SYSTEM_PROMPT
from rag_agent.tools import build_tools

JUDGE_MODEL = "gpt-5.4-mini"


def _make_target(model_name: str):
    agent = create_agent(
        model=ChatOpenAI(model=model_name, streaming=False),
        tools=build_tools(),
        system_prompt=SYSTEM_PROMPT,
    )

    def target(inputs: dict) -> dict:
        result = agent.invoke({"messages": [{"role": "user", "content": inputs["question"]}]})
        answer = result["messages"][-1].text
        context = [
            m.content
            for m in result["messages"]
            if isinstance(m, ToolMessage) and m.name == "retrieve_documents"
        ]
        return {"answer": answer, "context": context}

    return target


_judge = ChatOpenAI(model=JUDGE_MODEL, temperature=0)


def ranked_preference(runs: list, example) -> dict:
    """LLM judge picks the better of two answers; returns per-run scores."""
    question = example.inputs.get("question", "")
    a = (runs[0].outputs or {}).get("answer", "")
    b = (runs[1].outputs or {}).get("answer", "")
    reference = (example.outputs or {}).get("answer", "")

    prompt = (
        "You are judging two assistant answers to the same question.\n"
        f"Question: {question}\n"
        f"Reference answer: {reference}\n\n"
        f"Answer A:\n{a}\n\nAnswer B:\n{b}\n\n"
        "Which answer is more correct, grounded, and well-cited? "
        "Reply with exactly one character: A or B."
    )
    verdict = _judge.invoke(prompt).text.strip().upper()
    a_wins = verdict.startswith("A")
    return {
        "key": "ranked_preference",
        "scores": {runs[0].id: int(a_wins), runs[1].id: int(not a_wins)},
    }


def main() -> None:
    client = Client()

    heavy = client.evaluate(
        _make_target("gpt-5.5"),
        data=DATASET_NAME,
        experiment_prefix="rag-agent-heavy",
        metadata={"model": "gpt-5.5"},
        max_concurrency=4,
    )
    fast = client.evaluate(
        _make_target("gpt-5.4-mini"),
        data=DATASET_NAME,
        experiment_prefix="rag-agent-fast",
        metadata={"model": "gpt-5.4-mini"},
        max_concurrency=4,
    )

    comparison = evaluate_comparative(
        (heavy.experiment_name, fast.experiment_name),
        evaluators=[ranked_preference],
        randomize_order=True,
        max_concurrency=4,
    )
    print(comparison)


if __name__ == "__main__":
    main()
