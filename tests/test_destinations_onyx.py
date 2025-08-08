import pytest
import httpx

from backend.destinations.onyx import OnyxDestination


@pytest.mark.asyncio
async def test_onyx_success(monkeypatch):
    calls = []

    async def handler(request):
        calls.append(1)
        return httpx.Response(202)

    transport = httpx.MockTransport(handler)
    # Patch AsyncClient used inside module
    orig_ac = httpx.AsyncClient
    monkeypatch.setattr("backend.destinations.onyx.httpx.AsyncClient", lambda *a, **kw: orig_ac(transport=transport))

    dest = OnyxDestination()
    cfg = {"onyx": {"api_key": "token"}}
    await dest.send(payload=[{"id": "1", "raw_text": "hi"}], profile_config=cfg)

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_onyx_missing_api_key():
    dest = OnyxDestination()
    with pytest.raises(ValueError):
        await dest.send(payload=[{"id": "1"}], profile_config={}) 