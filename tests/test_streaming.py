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
