import json

import pytest

from rag_agent.streaming import agent_event_stream


class FailingAgent:
    async def astream(self, *args, **kwargs):
        raise RuntimeError("database password=/secret")
        yield


@pytest.mark.asyncio
async def test_stream_errors_are_safe_for_clients():
    events = [event async for event in agent_event_stream(FailingAgent(), "hi", "thread")]
    error = next(event for event in events if event["event"] == "error")
    payload = json.loads(error["data"])
    assert payload["message"] == "The assistant could not complete this request. Please try again."
    assert "database password" not in payload["message"]


class RecordingAgent:
    def __init__(self) -> None:
        self.configs: list[dict] = []

    async def astream(self, *args, config, **kwargs):
        self.configs.append(config)
        return
        yield


@pytest.mark.asyncio
async def test_each_turn_gets_its_own_source_counter():
    agent = RecordingAgent()
    for _ in range(2):
        _ = [event async for event in agent_event_stream(agent, "hi", "thread")]
    first, second = (config["configurable"]["source_counter"] for config in agent.configs)
    assert first is not second
    assert agent.configs[0]["configurable"]["thread_id"] == "thread"
