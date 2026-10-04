import json

import pytest

from rag_agent.streaming import agent_event_stream

USER = "a" * 32


class FailingAgent:
    async def astream(self, *args, **kwargs):
        raise RuntimeError("database password=/secret")
        yield


@pytest.mark.asyncio
async def test_stream_errors_are_safe_for_clients():
    events = [event async for event in agent_event_stream(FailingAgent(), "hi", "thread", USER)]
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
        _ = [event async for event in agent_event_stream(agent, "hi", "thread", USER)]
    first, second = (config["configurable"]["source_counter"] for config in agent.configs)
    assert first is not second


@pytest.mark.asyncio
async def test_turns_are_scoped_to_the_user():
    agent = RecordingAgent()
    events = [event async for event in agent_event_stream(agent, "hi", "thread", USER)]
    configurable = agent.configs[0]["configurable"]
    assert configurable["user_id"] == USER
    assert configurable["thread_id"] == f"{USER}:thread"
    # Clients only ever see their own thread id.
    assert all(json.loads(event["data"])["thread_id"] == "thread" for event in events)


@pytest.mark.asyncio
async def test_a_turn_without_a_user_is_refused():
    agent = RecordingAgent()
    with pytest.raises(ValueError):
        _ = [event async for event in agent_event_stream(agent, "hi", "thread", "")]
    assert agent.configs == []
