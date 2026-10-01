from concurrent.futures import ThreadPoolExecutor

import pytest
from langchain_core.documents import Document

from rag_agent.config import settings
from rag_agent.tools import SourceCounter, _build_web_search_tool, retrieve_documents


class FakeStore:
    def as_retriever(self, search_kwargs: dict):
        return self

    def invoke(self, query: str) -> list[Document]:
        return [
            Document(page_content=f"Passage {i}", metadata={"source": f"doc{i}.md"})
            for i in (1, 2)
        ]


class FakeTavily:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def invoke(self, payload: dict) -> dict:
        return {
            "results": [
                {"title": f"Web {i}", "url": f"https://example.com/{i}", "content": "text"}
                for i in (1, 2)
            ]
        }


class BrokenSearch:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def invoke(self, *args, **kwargs):
        raise RuntimeError("api_key=SECRET-VALUE")


def use_tavily(monkeypatch, provider) -> None:
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
    monkeypatch.setattr("langchain_tavily.TavilySearch", provider)


def test_source_numbers_continue_across_tool_calls(monkeypatch):
    emitted: list[list[dict]] = []
    monkeypatch.setattr(
        "rag_agent.tools._emit_sources", lambda tool_name, sources: emitted.append(sources)
    )
    monkeypatch.setattr("rag_agent.tools.get_vectorstore", FakeStore)
    use_tavily(monkeypatch, FakeTavily)
    web_search = _build_web_search_tool()
    config = {"configurable": {"source_counter": SourceCounter()}}

    texts = [
        retrieve_documents.invoke({"query": "a"}, config=config),
        web_search.invoke({"query": "b"}, config=config),
        retrieve_documents.invoke({"query": "c"}, config=config),
    ]

    assert [[s["number"] for s in batch] for batch in emitted] == [[1, 2], [3, 4], [5, 6]]
    # The numbers the model reads must sit next to the same sources the UI shows.
    for text, batch in zip(texts, emitted, strict=True):
        for source in batch:
            label = f"[{source['number']}]"
            line = next(line for line in text.splitlines() if line.startswith(label))
            assert source["title"] in line


def test_tools_still_work_without_a_turn_counter(monkeypatch):
    monkeypatch.setattr("rag_agent.tools.get_vectorstore", FakeStore)
    assert retrieve_documents.invoke({"query": "a"}).startswith("[1]")


def test_source_counter_hands_out_unique_numbers_across_threads():
    counter = SourceCounter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        batches = list(pool.map(lambda _: counter.take(5), range(50)))
    assert sorted(n for batch in batches for n in batch) == list(range(1, 251))


@pytest.mark.parametrize("tavily_key", ["tvly-test", None])
def test_web_search_failure_does_not_leak_error_details(monkeypatch, tavily_key):
    monkeypatch.setattr(settings, "tavily_api_key", tavily_key)
    monkeypatch.setattr("langchain_tavily.TavilySearch", BrokenSearch)
    monkeypatch.setattr("langchain_community.tools.DuckDuckGoSearchResults", BrokenSearch)

    result = _build_web_search_tool().invoke({"query": "aurora"})

    assert result == "Web search is temporarily unavailable."
    assert "SECRET-VALUE" not in result
