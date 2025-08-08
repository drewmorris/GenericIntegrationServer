import pytest
import httpx

from backend.destinations.cleverbrag import CleverBragDestination


@pytest.mark.asyncio
async def test_cleverbrag_retry(monkeypatch):
    calls = []

    async def handler(request):  # noqa: D401
        calls.append(1)
        # first call fail, second succeed
        if len(calls) == 1:
            return httpx.Response(500)
        return httpx.Response(202)

    transport = httpx.MockTransport(handler)

    monkeypatch.setenv("CLEVERBRAG_BASE_URL", "https://dummy")

    dest = CleverBragDestination()

    async with httpx.AsyncClient(transport=transport) as _:
        orig_ac = httpx.AsyncClient
        monkeypatch.setattr("backend.destinations.cleverbrag.httpx.AsyncClient", lambda *args, **kw: orig_ac(transport=transport))
        await dest.send(payload=[{"id": "1", "raw_text": "hi"}], profile_config={"cleverbrag": {"api_key": "key"}})

    assert len(calls) == 2 