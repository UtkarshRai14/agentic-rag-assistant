"""Create / refresh the LangSmith evaluation dataset.

Run:  uv run python -m evals.create_dataset
"""

from __future__ import annotations

from langsmith import Client

# Loads .env into os.environ so LANGSMITH_* is available.
from rag_agent.config import settings  # noqa: F401

DATASET_NAME = "resume-demo-rag-qa"

# Question / reference-answer pairs. Most are answerable from the sample Aurora
# docs (doc-RAG); a couple require general/world knowledge (web search).
EXAMPLES: list[dict] = [
    {
        "inputs": {"question": "What is the maximum event size Aurora accepts?"},
        "outputs": {"answer": "256 KB. Larger events are rejected at ingest."},
    },
    {
        "inputs": {"question": "How long are raw events retained by default in Aurora?"},
        "outputs": {"answer": "14 days by default, configurable up to 90 days."},
    },
    {
        "inputs": {"question": "How long are Aurora's daily (1d) rollups retained?"},
        "outputs": {"answer": "730 days, and that value is not configurable."},
    },
    {
        "inputs": {"question": "What authentication does Aurora use?"},
        "outputs": {"answer": "mTLS plus OIDC, with Helios SSO as the OIDC provider."},
    },
    {
        "inputs": {"question": "Which database backs Aurora's rollups?"},
        "outputs": {"answer": "A ClickHouse cluster named aurora_rollups."},
    },
    {
        "inputs": {"question": "Why would an Aurora query return HTTP 504?"},
        "outputs": {
            "answer": "It exceeded the default 30-second query-gateway timeout; "
            "narrow the time range or reduce group-by cardinality."
        },
    },
    {
        "inputs": {"question": "Does Aurora support cross-tenant joins?"},
        "outputs": {"answer": "No, cross-tenant joins are an explicit non-goal."},
    },
    {
        "inputs": {"question": "What is Aurora's dashboard p99 query latency SLO?"},
        "outputs": {"answer": "Less than 800 ms."},
    },
    {
        "inputs": {"question": "In which Aurora version was the max event size raised to 256 KB?"},
        "outputs": {"answer": "v3.2 (it was raised from 128 KB)."},
    },
    {
        "inputs": {"question": "How fresh are Aurora's 1-minute rollups?"},
        "outputs": {"answer": "Available within 5 seconds of the source event."},
    },
    # --- world-knowledge / web-search examples ---
    {
        "inputs": {"question": "What does the acronym mTLS stand for?"},
        "outputs": {"answer": "Mutual TLS (mutual Transport Layer Security)."},
    },
    {
        "inputs": {"question": "What kind of database is ClickHouse?"},
        "outputs": {
            "answer": "An open-source column-oriented OLAP database management "
            "system for real-time analytics."
        },
    },
]


def main() -> None:
    client = Client()

    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset already exists: {dataset.id}")
    else:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Q/reference-answer pairs for the agentic RAG + web-search demo.",
        )
        print(f"Created dataset: {dataset.id}")

    client.create_examples(dataset_id=dataset.id, examples=EXAMPLES)
    print(f"Added {len(EXAMPLES)} examples to '{DATASET_NAME}'.")


if __name__ == "__main__":
    main()
